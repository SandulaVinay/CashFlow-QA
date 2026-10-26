from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from decision_lab.behaviour import expected_payment_day
from decision_lab.data import generate_benchmark_case
from decision_lab.objective_variants import (
    DEFAULT_REMAINING_RISK_FRACTIONS,
    cost_guarded_objectives,
    risk_budget_policy_name,
)
from decision_lab.policies import POLICIES
from decision_lab.simulator import build_realized_payment_days, simulate


BASELINE_POLICIES = [
    "wait",
    "largest_first",
    "earliest_due_first",
    "highest_delay_risk_first",
    "cash_threshold",
    "optimizer",
]
METRICS = [
    "minimum_cash",
    "cash_shortfall_days",
    "cash_shortfall_amount_days",
    "financing_cost",
    "financed_amount",
    "financed_invoice_count",
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {key: 0.0 for key in ("min", "p10", "median", "mean", "p90", "max")}
    return {
        "min": min(values),
        "p10": percentile(values, 0.10),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "p90": percentile(values, 0.90),
        "max": max(values),
    }


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    source_paths = sorted((ROOT / "src").rglob("*.py")) + sorted(
        (ROOT / "experiments").rglob("*.py")
    )
    for path in source_paths:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def git_worktree_dirty() -> bool | None:
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        )
        return bool(status.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def obligation_burden_band(ratio: float) -> str:
    if ratio < 0.5:
        return "under 0.5x"
    if ratio < 1.0:
        return "0.5x to under 1x"
    if ratio < 2.0:
        return "1x to under 2x"
    return "2x or higher"


def opening_cash_band(opening_cash: float) -> str:
    if opening_cash < 1_000_000:
        return "under INR 10 lakh"
    if opening_cash < 2_000_000:
        return "INR 10-20 lakh"
    if opening_cash < 3_500_000:
        return "INR 20-35 lakh"
    return "INR 35 lakh or more"


def metric_values(rows: list[dict], policy: str, timing: str, metric: str) -> list[float]:
    return [
        float(row["policies"][policy][timing][metric])
        for row in rows
    ]


def summarize_policy(rows: list[dict], policy: str) -> dict:
    realized = {
        metric: summarize(metric_values(rows, policy, "realized", metric))
        for metric in METRICS
    }
    expected = {
        metric: summarize(metric_values(rows, policy, "expected", metric))
        for metric in METRICS
    }
    risk_limit_values = [
        row["policies"][policy]["risk_limit_met"]
        for row in rows
        if row["policies"][policy]["risk_limit_met"] is not None
    ]
    shortfall_count = sum(
        value > 0 for value in metric_values(rows, policy, "realized", "cash_shortfall_days")
    )
    return {
        "expected_schedule": expected,
        "realized_schedule": realized,
        "realized_scenarios_with_any_shortfall": shortfall_count,
        "realized_shortfall_scenario_rate": shortfall_count / len(rows),
        "risk_limit_met_scenarios": sum(risk_limit_values),
        "risk_limit_scenario_count": len(risk_limit_values),
        "risk_limit_met_rate": (
            sum(risk_limit_values) / len(risk_limit_values)
            if risk_limit_values
            else None
        ),
    }


def summarize_stratum(rows: list[dict], policy: str) -> dict:
    shortfall_days = metric_values(rows, policy, "realized", "cash_shortfall_days")
    shortfall_amount_days = metric_values(
        rows, policy, "realized", "cash_shortfall_amount_days"
    )
    financing_cost = metric_values(rows, policy, "realized", "financing_cost")
    expected_risk = metric_values(
        rows, policy, "expected", "cash_shortfall_amount_days"
    )
    limit_values = [
        row["policies"][policy]["risk_limit_met"]
        for row in rows
        if row["policies"][policy]["risk_limit_met"] is not None
    ]
    return {
        "scenario_count": len(rows),
        "realized_shortfall_scenarios": sum(value > 0 for value in shortfall_days),
        "realized_shortfall_scenario_rate": sum(value > 0 for value in shortfall_days)
        / len(rows),
        "realized_shortfall_days_p90": percentile(shortfall_days, 0.90),
        "realized_shortfall_amount_days_p90": percentile(shortfall_amount_days, 0.90),
        "financing_cost_median": statistics.median(financing_cost),
        "expected_shortfall_amount_days_median": statistics.median(expected_risk),
        "risk_limit_met_rate": (
            sum(limit_values) / len(limit_values) if limit_values else None
        ),
    }


def candidate_comparisons(rows: list[dict], candidate_names: list[str]) -> dict:
    baseline = "optimizer"
    comparisons = {}
    for candidate in candidate_names:
        days_delta = [
            float(row["policies"][candidate]["realized"]["cash_shortfall_days"])
            - float(row["policies"][baseline]["realized"]["cash_shortfall_days"])
            for row in rows
        ]
        amount_days_delta = [
            float(
                row["policies"][candidate]["realized"]["cash_shortfall_amount_days"]
            )
            - float(
                row["policies"][baseline]["realized"]["cash_shortfall_amount_days"]
            )
            for row in rows
        ]
        cost_delta = [
            float(row["policies"][candidate]["realized"]["financing_cost"])
            - float(row["policies"][baseline]["realized"]["financing_cost"])
            for row in rows
        ]
        selections = [
            row["policies"][candidate]["selection"] for row in rows
        ]
        comparisons[candidate] = {
            "realized_shortfall_days": {
                "better_scenarios": sum(value < 0 for value in days_delta),
                "same_scenarios": sum(value == 0 for value in days_delta),
                "worse_scenarios": sum(value > 0 for value in days_delta),
            },
            "realized_shortfall_amount_days": {
                "better_scenarios": sum(value < -1e-6 for value in amount_days_delta),
                "same_scenarios": sum(abs(value) <= 1e-6 for value in amount_days_delta),
                "worse_scenarios": sum(value > 1e-6 for value in amount_days_delta),
                "median_delta": statistics.median(amount_days_delta),
                "mean_delta": statistics.fmean(amount_days_delta),
            },
            "financing_cost_delta": {
                "median": statistics.median(cost_delta),
                "mean": statistics.fmean(cost_delta),
                "scenarios_costlier_than_current_optimizer": sum(
                    value > 1e-6 for value in cost_delta
                ),
            },
            "risk_limit_met_scenarios": sum(
                bool(selection["risk_limit_met"]) for selection in selections
            ),
            "search_methods": {
                method: sum(selection["search_method"] == method for selection in selections)
                for method in sorted({selection["search_method"] for selection in selections})
            },
        }
    return comparisons


def markdown_report(summary: dict, rows: list[dict], policy_names: list[str]) -> str:
    lines = [
        "# Cost-aware objective comparison",
        "",
        f"- Experiment: `{summary['experiment_id']}`",
        f"- Commit: `{summary['commit_sha'] or 'unknown'}`",
        f"- Scenarios: {summary['scenario_count']}",
        f"- Base seed: {summary['base_seed']}",
        "- Data: synthetic scenarios; not company histories",
        "- Payment timing: common realized dates for every policy within a scenario",
        "- Selection timing: expected payment dates only; no realized-date hindsight",
        "",
        "## Predeclared comparison rule",
        "",
        "For each cost-aware policy, allow expected cash-buffer deficit amount-days up to a stated fraction of the WAIT policy's expected deficit. Among subsets within that limit, select the lowest financing cost. If the limit is unreachable, select the lowest-risk achievable subset and report the limit miss. Amount-days sum the daily rupee gap below the cash buffer, so they capture both depth and duration.",
        "",
        "The fractions are a sensitivity curve, not recommended company settings. No single winner is declared without a business-specific liquidity-risk tolerance. Exact subset search is used through 14 eligible invoices; larger portfolios use a greedy risk-reduction path.",
        "",
        "## Portfolio-level results",
        "",
        "Realized metrics evaluate the sampled payment path. Expected metrics describe the schedule visible to the policy when it selects actions. Currency values are INR; deficit amount-days are INR-days.",
        "",
        "| Policy | Realized shortfall scenarios | Realized shortfall days p90 | Realized deficit amount-days p90 | Financing cost median / p90 | Expected deficit amount-days median / p90 | Risk limit met |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in policy_names:
        result = summary["policies"][policy]
        realized = result["realized_schedule"]
        expected = result["expected_schedule"]
        limit_rate = result["risk_limit_met_rate"]
        limit_text = "—" if limit_rate is None else f"{limit_rate:.0%}"
        lines.append(
            f"| {policy} | {result['realized_scenarios_with_any_shortfall']} / {summary['scenario_count']} "
            f"| {realized['cash_shortfall_days']['p90']:.1f} "
            f"| {realized['cash_shortfall_amount_days']['p90']:,.0f} "
            f"| {realized['financing_cost']['median']:,.0f} / {realized['financing_cost']['p90']:,.0f} "
            f"| {expected['cash_shortfall_amount_days']['median']:,.0f} / {expected['cash_shortfall_amount_days']['p90']:,.0f} "
            f"| {limit_text} |"
        )

    lines.extend(["", "## Cost-aware policies versus the current optimizer", ""])
    lines.extend(
        [
            "| Policy | Scenarios with fewer / same / more realized shortfall days | Scenarios with lower / same / higher realized deficit amount-days | Median financing-cost change | Risk limit met |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for policy, comparison in summary["comparisons_vs_optimizer"].items():
        days = comparison["realized_shortfall_days"]
        amount = comparison["realized_shortfall_amount_days"]
        lines.append(
            f"| {policy} | {days['better_scenarios']} / {days['same_scenarios']} / {days['worse_scenarios']} "
            f"| {amount['better_scenarios']} / {amount['same_scenarios']} / {amount['worse_scenarios']} "
            f"| {comparison['financing_cost_delta']['median']:+,.0f} "
            f"| {comparison['risk_limit_met_scenarios']} / {summary['scenario_count']} |"
        )

    focus_policies = [
        "wait",
        "optimizer",
        *[
            policy
            for policy in policy_names
            if policy.startswith("risk_limit_")
        ],
    ]
    for stratum_name, title in (
        ("obligation_to_opening_cash", "Obligation burden / opening cash"),
        ("opening_cash", "Opening cash bands"),
    ):
        lines.extend(["", f"## Results by {title.lower()}", ""])
        lines.extend(
            [
                "| Band | Policy | N | Realized shortfall rate | Realized deficit amount-days p90 | Financing cost median | Expected deficit amount-days median |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        bands = summary["stratified_results"][stratum_name]
        for band, band_data in bands.items():
            for policy in focus_policies:
                result = band_data["policies"][policy]
                lines.append(
                    f"| {band} | {policy} | {result['scenario_count']} "
                    f"| {result['realized_shortfall_scenario_rate']:.0%} "
                    f"| {result['realized_shortfall_amount_days_p90']:,.0f} "
                    f"| {result['financing_cost_median']:,.0f} "
                    f"| {result['expected_shortfall_amount_days_median']:,.0f} |"
                )

    lines.extend(
        [
            "",
            "## Limits",
            "",
            "This compares objective behavior under synthetic assumptions and one shared payment realization per scenario. It does not estimate a real firm's cash buffer or establish real-world performance. The cash-risk limits must be calibrated with company data and business preferences before decision-facing use.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare cost-aware liquidity objectives on common synthetic scenarios."
    )
    parser.add_argument("--scenario-count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument(
        "--remaining-risk-fractions",
        type=float,
        nargs="+",
        default=list(DEFAULT_REMAINING_RISK_FRACTIONS),
        help="Allowed expected deficit amount-days as a fraction of WAIT risk.",
    )
    args = parser.parse_args()
    if args.scenario_count < 1:
        parser.error("--scenario-count must be at least 1")
    if any(not 0 <= fraction <= 1 for fraction in args.remaining_risk_fractions):
        parser.error("risk fractions must be between 0 and 1")
    if len(set(args.remaining_risk_fractions)) != len(args.remaining_risk_fractions):
        parser.error("risk fractions must be unique")
    if len(
        {risk_budget_policy_name(fraction) for fraction in args.remaining_risk_fractions}
    ) != len(args.remaining_risk_fractions):
        parser.error("risk fractions must map to distinct policy names")

    budget_names = [
        risk_budget_policy_name(fraction)
        for fraction in args.remaining_risk_fractions
    ]
    policy_names = [*BASELINE_POLICIES, *budget_names]
    rows: list[dict] = []

    for offset in range(args.scenario_count):
        seed = args.seed + offset
        invoices, obligations, scenario = generate_benchmark_case(seed)
        expected_days = {
            invoice.invoice_id: expected_payment_day(invoice, scenario)
            for invoice in invoices
        }
        realized_days = build_realized_payment_days(invoices, scenario)

        actions_by_policy = {
            policy: POLICIES[policy](invoices, obligations, scenario)
            for policy in BASELINE_POLICIES
        }
        selections = cost_guarded_objectives(
            invoices,
            obligations,
            scenario,
            tuple(args.remaining_risk_fractions),
        )
        selection_metadata = {}
        for policy, selection in selections.items():
            actions_by_policy[policy] = selection.actions
            selection_metadata[policy] = {
                "expected_shortfall_days": selection.expected_shortfall_days,
                "expected_shortfall_amount_days": selection.expected_shortfall_amount_days,
                "expected_financing_cost": selection.expected_financing_cost,
                "risk_limit_amount_days": selection.risk_limit_amount_days,
                "risk_limit_met": selection.risk_limit_met,
                "search_method": selection.search_method,
            }

        outcomes = {}
        for policy, actions in actions_by_policy.items():
            realized = simulate(
                invoices,
                obligations,
                scenario,
                actions,
                policy_name=policy,
                payment_days=realized_days,
            )
            expected = simulate(
                invoices,
                obligations,
                scenario,
                actions,
                policy_name=f"{policy}_expected",
                payment_days=expected_days,
            )
            selection = selection_metadata.get(policy)
            outcomes[policy] = {
                "expected": expected.metrics.model_dump(),
                "realized": realized.metrics.model_dump(),
                "risk_limit_met": (
                    selection["risk_limit_met"] if selection is not None else None
                ),
                "selection": selection,
            }

        obligation_total = sum(obligation.amount for obligation in obligations)
        burden_ratio = (
            obligation_total / scenario.opening_cash
            if scenario.opening_cash > 0
            else float("inf")
        )
        rows.append(
            {
                "scenario_seed": seed,
                "invoice_count": len(invoices),
                "eligible_invoice_count": sum(
                    invoice.eligible_for_treds for invoice in invoices
                ),
                "obligation_count": len(obligations),
                "obligation_total": obligation_total,
                "opening_cash": scenario.opening_cash,
                "obligation_to_opening_cash_ratio": burden_ratio,
                "obligation_burden_band": obligation_burden_band(burden_ratio),
                "opening_cash_band": opening_cash_band(scenario.opening_cash),
                "payment_delay_shock_days": scenario.payment_delay_shock_days,
                "policies": outcomes,
            }
        )

    policy_summaries = {
        policy: summarize_policy(rows, policy) for policy in policy_names
    }
    candidate_names = [policy for policy in budget_names if policy != "optimizer"]
    comparisons = candidate_comparisons(rows, candidate_names)
    stratified = {}
    for key, row_field in (
        ("obligation_to_opening_cash", "obligation_burden_band"),
        ("opening_cash", "opening_cash_band"),
    ):
        bands = sorted({row[row_field] for row in rows})
        stratified[key] = {
            band: {
                "scenario_count": sum(row[row_field] == band for row in rows),
                "policies": {
                    policy: summarize_stratum(
                        [row for row in rows if row[row_field] == band], policy
                    )
                    for policy in policy_names
                },
            }
            for band in bands
        }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    experiment_id = f"objective-comparison-{args.scenario_count}-seed-{args.seed}-{timestamp}"
    summary = {
        "experiment_id": experiment_id,
        "commit_sha": git_commit(),
        "working_tree_dirty": git_worktree_dirty(),
        "source_sha256": source_fingerprint(),
        "dataset_version": "synthetic-benchmark-v1",
        "scenario_count": args.scenario_count,
        "base_seed": args.seed,
        "risk_limit_fractions_of_wait_expected_deficit": args.remaining_risk_fractions,
        "policy_names": policy_names,
        "assumptions": {
            "horizon_days": 91,
            "fee_assumption": "no financing fees in this synthetic benchmark",
            "payment_realization": "common across all policies within each scenario",
            "decision_timing": "all policies select actions using expected payment days",
            "risk_measure": "sum of daily cash-buffer deficits in INR-days",
            "cost_aware_rule": "minimize financing cost subject to expected deficit amount-days being within the selected fraction of WAIT risk",
            "unmet_risk_limit": "choose the lowest expected-risk achievable subset and mark the limit as unmet",
            "exact_search_limit": 14,
            "large_portfolio_method": "greedy risk-reduction path above 14 eligible invoices",
        },
        "policies": policy_summaries,
        "comparisons_vs_optimizer": comparisons,
        "stratified_results": stratified,
    }

    changed_cases = []
    for row in rows:
        baseline = row["policies"]["optimizer"]
        candidate_changes = {}
        for candidate in candidate_names:
            result = row["policies"][candidate]
            realized_delta_days = (
                result["realized"]["cash_shortfall_days"]
                - baseline["realized"]["cash_shortfall_days"]
            )
            realized_delta_amount_days = (
                result["realized"]["cash_shortfall_amount_days"]
                - baseline["realized"]["cash_shortfall_amount_days"]
            )
            financing_cost_delta = (
                result["realized"]["financing_cost"]
                - baseline["realized"]["financing_cost"]
            )
            if (
                realized_delta_days != 0
                or abs(realized_delta_amount_days) > 1e-6
                or abs(financing_cost_delta) > 1e-6
            ):
                candidate_changes[candidate] = {
                    "realized_shortfall_days_delta": realized_delta_days,
                    "realized_shortfall_amount_days_delta": realized_delta_amount_days,
                    "financing_cost_delta": financing_cost_delta,
                    "expected_metrics": result["expected"],
                    "realized_metrics": result["realized"],
                    "selection": result["selection"],
                }
        if candidate_changes:
            changed_cases.append(
                {
                    "scenario_seed": row["scenario_seed"],
                    "invoice_count": row["invoice_count"],
                    "eligible_invoice_count": row["eligible_invoice_count"],
                    "opening_cash": row["opening_cash"],
                    "obligation_total": row["obligation_total"],
                    "obligation_to_opening_cash_ratio": row[
                        "obligation_to_opening_cash_ratio"
                    ],
                    "obligation_burden_band": row["obligation_burden_band"],
                    "opening_cash_band": row["opening_cash_band"],
                    "payment_delay_shock_days": row["payment_delay_shock_days"],
                    "current_optimizer": baseline,
                    "candidate_changes": candidate_changes,
                }
            )
    summary["changed_scenario_count"] = len(changed_cases)

    report_path = ROOT / "reports" / f"objective-comparison-report-{experiment_id}.md"
    summary_path = ROOT / "reports" / f"objective-comparison-summary-{experiment_id}.json"
    cases_path = ROOT / "reports" / f"objective-comparison-cases-{experiment_id}.json"
    report_path.parent.mkdir(exist_ok=True)
    summary["report_file"] = report_path.name
    summary["cases_file"] = cases_path.name
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    cases_path.write_text(json.dumps(changed_cases, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report(summary, rows, policy_names), encoding="utf-8")

    print(f"Experiment: {experiment_id}")
    print(f"Report: {report_path}")
    print(f"Summary: {summary_path}")
    print(f"Changed scenario cases: {cases_path} ({len(changed_cases)})")


if __name__ == "__main__":
    main()
