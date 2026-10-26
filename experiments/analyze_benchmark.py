from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from decision_lab.behaviour import expected_payment_day
from decision_lab.data import generate_benchmark_case
from decision_lab.policies import (
    POLICIES,
    _expected_candidate_score,
    _subset_actions,
)
from decision_lab.simulator import build_realized_payment_days, simulate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct and diagnose saved benchmark tradeoff cases."
    )
    parser.add_argument("failure_cases", type=Path)
    parser.add_argument("--output-stem", default="benchmark-failure-analysis")
    parser.add_argument("--base-seed", type=int, default=20260930)
    parser.add_argument("--scenario-count", type=int, default=500)
    args = parser.parse_args()
    if args.scenario_count < 1:
        parser.error("--scenario-count must be at least 1")

    failures = json.loads(args.failure_cases.read_text(encoding="utf-8"))
    details: list[dict] = []
    counts: Counter[str] = Counter()
    lag_all: list[int] = []
    lag_financed: list[int] = []
    early_financed: list[bool] = []
    optimizer_selected_costs: list[float] = []
    hindsight_cost_gaps: list[float] = []

    campaign_timing: Counter[str] = Counter()
    campaign_invoice_count = 0
    campaign_timing_deltas: list[int] = []
    for offset in range(args.scenario_count):
        invoices, _, scenario = generate_benchmark_case(args.base_seed + offset)
        realized_days = build_realized_payment_days(invoices, scenario)
        for invoice in invoices:
            due_day = max(0, (invoice.due_date - scenario.as_of_date).days)
            actual_day = realized_days[invoice.invoice_id]
            expected_day = expected_payment_day(invoice, scenario)
            campaign_invoice_count += 1
            campaign_timing["before_due"] += actual_day < due_day
            campaign_timing["on_due"] += actual_day == due_day
            campaign_timing["after_due"] += actual_day > due_day
            campaign_timing["earlier_than_expected"] += actual_day < expected_day
            campaign_timing_deltas.append(actual_day - expected_day)

    for failure in failures:
        seed = failure["scenario_seed"]
        invoices, obligations, scenario = generate_benchmark_case(seed)
        realized_days = build_realized_payment_days(invoices, scenario)
        expected_days = {
            invoice.invoice_id: expected_payment_day(invoice, scenario)
            for invoice in invoices
        }
        optimizer_actions = POLICIES["optimizer"](invoices, obligations, scenario)
        selected = {
            action.invoice_id
            for action in optimizer_actions
            if action.action == "FINANCE_TREDS"
        }
        exact = sum(invoice.eligible_for_treds for invoice in invoices) <= 14

        expected_result = simulate(
            invoices, obligations, scenario, optimizer_actions, "optimizer_expected",
            payment_days=expected_days,
        )
        realized_result = simulate(
            invoices, obligations, scenario, optimizer_actions, "optimizer_realized",
            payment_days=realized_days,
        )
        case_lags = [realized_days[key] - expected_days[key] for key in expected_days]
        financed_lags = [
            realized_days[key] - expected_days[key] for key in selected
        ]
        early_financed.extend(
            realized_days[key] < expected_days[key] for key in selected
        )
        lag_all.extend(case_lags)
        lag_financed.extend(financed_lags)
        optimizer_selected_costs.append(realized_result.metrics.financing_cost)

        hindsight: dict | None = None
        if exact:
            eligible = [invoice for invoice in invoices if invoice.eligible_for_treds]
            best_score = _expected_candidate_score(
                invoices, obligations, scenario, set(), realized_days
            )
            best_ids: set[str] = set()
            for size in range(1, len(eligible) + 1):
                for subset in combinations(eligible, size):
                    candidate_ids = {invoice.invoice_id for invoice in subset}
                    score = _expected_candidate_score(
                        invoices, obligations, scenario, candidate_ids, realized_days
                    )
                    if score < best_score:
                        best_score, best_ids = score, candidate_ids
            hindsight_result = simulate(
                invoices, obligations, scenario, _subset_actions(invoices, best_ids),
                "hindsight_oracle", payment_days=realized_days,
            )
            hindsight = {
                "score": {
                    "cash_shortfall_days": best_score[0],
                    "financing_cost": best_score[1],
                    "financed_invoice_count": best_score[2],
                },
                "selected_invoice_ids": sorted(best_ids),
                "metrics": hindsight_result.metrics.model_dump(),
                "optimizer_shortfall_gap": (
                    realized_result.metrics.cash_shortfall_days
                    - hindsight_result.metrics.cash_shortfall_days
                ),
            }
            hindsight_cost_gaps.append(
                realized_result.metrics.financing_cost
                - hindsight_result.metrics.financing_cost
            )

        best_comparable = failure["best_baseline_cost_at_equal_or_better_shortfall"]
        shortfall_regression = (
            failure["optimizer"]["cash_shortfall_days"]
            > failure["best_baseline_shortfall_days"]
        )
        avoidable_financing = (
            best_comparable is not None
            and failure["optimizer"]["financing_cost"] > best_comparable
            and failure["baseline_metrics"]["wait"]["cash_shortfall_days"]
            <= failure["optimizer"]["cash_shortfall_days"]
        )
        if shortfall_regression and avoidable_financing:
            label = "both_shortfall_regression_and_costly_vs_wait"
        elif shortfall_regression:
            label = "shortfall_regression"
        elif avoidable_financing:
            label = "costly_financing_vs_wait"
        else:
            label = "costlier_than_some_comparable_baseline"
        counts[f"{label}:{'exact' if exact else 'greedy'}"] += 1

        invoice_timing = [
            {
                "invoice_id": invoice.invoice_id,
                "expected_day": expected_days[invoice.invoice_id],
                "realized_day": realized_days[invoice.invoice_id],
                "realized_minus_expected_days": (
                    realized_days[invoice.invoice_id] - expected_days[invoice.invoice_id]
                ),
                "financed": invoice.invoice_id in selected,
                "amount": invoice.amount,
            }
            for invoice in invoices
        ]
        details.append(
            {
                "scenario_seed": seed,
                "search_mode": "exact" if exact else "greedy_fallback",
                "eligible_invoice_count": sum(
                    invoice.eligible_for_treds for invoice in invoices
                ),
                "classification": label,
                "best_baseline_shortfall_days": failure["best_baseline_shortfall_days"],
                "optimizer_selected_invoice_ids": sorted(selected),
                "expected_metrics": expected_result.metrics.model_dump(),
                "realized_metrics": realized_result.metrics.model_dump(),
                "expected_vs_realized_shortfall_days": (
                    realized_result.metrics.cash_shortfall_days
                    - expected_result.metrics.cash_shortfall_days
                ),
                "average_realized_minus_expected_payment_days": (
                    statistics.fmean(case_lags) if case_lags else 0
                ),
                "average_financed_realized_minus_expected_payment_days": (
                    statistics.fmean(financed_lags) if financed_lags else None
                ),
                "invoice_timing": invoice_timing,
                "best_comparable_baseline_cost": best_comparable,
                "hindsight_oracle": hindsight,
            }
        )

    by_mode: dict[str, Counter[str]] = {
        "exact": Counter(), "greedy_fallback": Counter()
    }
    for item in details:
        by_mode[item["search_mode"]][item["classification"]] += 1
    timing_outcomes = Counter(
        "worse" if item["realized_metrics"]["cash_shortfall_days"] > item["expected_metrics"]["cash_shortfall_days"]
        else "better" if item["realized_metrics"]["cash_shortfall_days"] < item["expected_metrics"]["cash_shortfall_days"]
        else "same"
        for item in details
    )
    shortfall_regressions_by_mode = {
        mode: sum(
            item["search_mode"] == mode
            and item["realized_metrics"]["cash_shortfall_days"] > item["best_baseline_shortfall_days"]
            for item in details
        )
        for mode in ("exact", "greedy_fallback")
    }
    expected_zero_actual_shortfall = sum(
        item["expected_metrics"]["cash_shortfall_days"] == 0
        and item["realized_metrics"]["cash_shortfall_days"] > 0
        for item in details
    )

    report_lines = [
        "# Benchmark tradeoff case analysis",
        "",
        f"Source failure cases: `{args.failure_cases.name}`",
        f"Total reconstructed cases: {len(details)}",
        "",
        "## Classification",
        "",
        "Categories can overlap conceptually; each case is assigned the first matching label below.",
        "",
        "| Search path | Shortfall regression and costlier than wait | Shortfall regression | Costly financing vs wait | Costlier than another comparable baseline | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    labels = [
        "both_shortfall_regression_and_costly_vs_wait",
        "shortfall_regression",
        "costly_financing_vs_wait",
        "costlier_than_some_comparable_baseline",
    ]
    for mode in ("exact", "greedy_fallback"):
        report_lines.append(
            "| " + mode + " | " + " | ".join(str(by_mode[mode][label]) for label in labels)
            + f" | {sum(by_mode[mode].values())} |"
        )
    report_lines.extend(
        [
            "",
            "## Timing and hindsight diagnostics",
            "",
            f"Across all {len(details)} flagged cases, the average realized-minus-expected payment timing was {statistics.fmean(lag_all):.1f} days per invoice (median {statistics.median(lag_all):.1f}).",
            f"Across optimizer-financed invoices, it was {statistics.fmean(lag_financed):.1f} days (median {statistics.median(lag_financed):.1f}).",
            f"Across the full {args.scenario_count}-scenario campaign ({campaign_invoice_count} invoices), {campaign_timing['before_due']} payments occurred before the contractual due date, {campaign_timing['on_due']} on the due date, and {campaign_timing['after_due']} after it. {campaign_timing['earlier_than_expected']} ({campaign_timing['earlier_than_expected'] / campaign_invoice_count:.1%}) arrived before the model's expected collection day.",
            f"Among optimizer-financed invoices in the flagged cases, {sum(early_financed)} of {len(early_financed)} ({sum(early_financed) / len(early_financed):.1%}) arrived before the expected day.",
            "For exact-search cases, a hindsight-only subset was enumerated against the realized dates. It is an upper-bound diagnostic because the policy cannot know those dates when choosing invoices.",
            f"In exact cases, optimizer realized shortfall exceeded that hindsight subset in {sum(1 for x in details if x['hindsight_oracle'] and x['hindsight_oracle']['optimizer_shortfall_gap'] > 0)} cases; the mean optimizer-minus-hindsight financing cost was ₹{statistics.fmean(hindsight_cost_gaps):,.0f}.",
            "",
            "The synthetic payment generator samples on-time versus late payment from the invoice late-rate, then samples a late delay around its historical average. Realizations are stable per invoice and shared across policies. The benchmark uses no fees; financing cost is interest estimated from expected payment duration.",
            "",
            f"Optimizer shortfall was worse on the realized schedule than on its expected schedule in {timing_outcomes['worse']} flagged cases, better in {timing_outcomes['better']}, and unchanged in {timing_outcomes['same']}. In {expected_zero_actual_shortfall} flagged cases, the optimizer predicted no shortfall but the realized run had one.",
            f"Of the {sum(shortfall_regressions_by_mode.values())} cases where optimizer shortfall exceeded the best baseline, {shortfall_regressions_by_mode['exact']} used exact subset search and {shortfall_regressions_by_mode['greedy_fallback']} used greedy fallback. These are realized outcome regressions: exact search can be optimal for the expected schedule and still choose a subset that performs worse on a different realized schedule.",
            "",
            "## Limits",
            "",
            "The hindsight result is not an implementable policy and does not prove how a real MSME portfolio would perform. These cases diagnose behavior under the current synthetic assumptions; they are not calibration or validation against actual buyer payment histories.",
            "",
        ]
    )
    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stem = f"{args.output_stem}-{stamp}"
    report_path = output_dir / f"{stem}.md"
    data_path = output_dir / f"{stem}.json"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    data_path.write_text(
        json.dumps(
            {
                "source_failure_cases": str(args.failure_cases),
                "case_count": len(details),
                "campaign_timing": {
                    "base_seed": args.base_seed,
                    "scenario_count": args.scenario_count,
                    "invoice_count": campaign_invoice_count,
                    "payments_before_contractual_due_date": campaign_timing["before_due"],
                    "payments_on_contractual_due_date": campaign_timing["on_due"],
                    "payments_after_contractual_due_date": campaign_timing["after_due"],
                    "payments_earlier_than_expected_day": campaign_timing["earlier_than_expected"],
                    "payment_earlier_than_expected_rate": campaign_timing["earlier_than_expected"] / campaign_invoice_count,
                    "mean_realized_minus_expected_days": statistics.fmean(campaign_timing_deltas),
                },
                "flagged_optimizer_financed_timing": {
                    "invoice_count": len(early_financed),
                    "payments_earlier_than_expected_day": sum(early_financed),
                    "rate_earlier_than_expected_day": sum(early_financed) / len(early_financed),
                    "mean_realized_minus_expected_days": statistics.fmean(lag_financed),
                    "median_realized_minus_expected_days": statistics.median(lag_financed),
                },
                "classification_counts": {
                    mode: dict(counter) for mode, counter in by_mode.items()
                },
                "realized_vs_expected_shortfall_outcomes": dict(timing_outcomes),
                "optimizer_expected_zero_but_realized_shortfall_cases": expected_zero_actual_shortfall,
                "shortfall_regressions_by_search_mode": shortfall_regressions_by_mode,
                "mean_all_invoice_timing_delta_days": statistics.fmean(lag_all),
                "median_all_invoice_timing_delta_days": statistics.median(lag_all),
                "mean_financed_invoice_timing_delta_days": statistics.fmean(lag_financed),
                "median_financed_invoice_timing_delta_days": statistics.median(lag_financed),
                "exact_case_mean_optimizer_minus_hindsight_cost": statistics.fmean(
                    hindsight_cost_gaps
                ) if hindsight_cost_gaps else None,
                "cases": details,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Report: {report_path}")
    print(f"Details: {data_path}")


if __name__ == "__main__":
    main()
