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

from decision_lab.data import generate_benchmark_case
from decision_lab.engine import compare_policies


POLICIES = [
    "wait",
    "largest_first",
    "earliest_due_first",
    "highest_delay_risk_first",
    "cash_threshold",
    "optimizer",
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible policy benchmarks.")
    parser.add_argument("--scenario-count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260930)
    args = parser.parse_args()
    if args.scenario_count < 1:
        parser.error("--scenario-count must be at least 1")

    policy_metrics: dict[str, dict[str, list[float]]] = {
        policy: {
            "minimum_cash": [],
            "cash_shortfall_days": [],
            "financing_cost": [],
            "financed_amount": [],
            "financed_invoice_count": [],
        }
        for policy in POLICIES
    }
    shortfall_scenario_count = {policy: 0 for policy in POLICIES}
    failure_cases: list[dict] = []
    optimizer_more_shortfall_count = 0
    optimizer_higher_cost_count = 0
    optimizer_exact_search_scenario_count = 0
    optimizer_greedy_fallback_scenario_count = 0

    for offset in range(args.scenario_count):
        scenario_seed = args.seed + offset
        invoices, obligations, scenario = generate_benchmark_case(scenario_seed)
        if sum(invoice.eligible_for_treds for invoice in invoices) <= 14:
            optimizer_exact_search_scenario_count += 1
        else:
            optimizer_greedy_fallback_scenario_count += 1
        results = compare_policies(invoices, obligations, scenario, POLICIES)
        by_policy = {result.policy: result for result in results}

        for policy, result in by_policy.items():
            metrics = result.metrics
            values = policy_metrics[policy]
            values["minimum_cash"].append(metrics.minimum_cash)
            values["cash_shortfall_days"].append(metrics.cash_shortfall_days)
            values["financing_cost"].append(metrics.financing_cost)
            values["financed_amount"].append(metrics.financed_amount)
            values["financed_invoice_count"].append(
                float(metrics.financed_invoice_count)
            )
            if metrics.cash_shortfall_days > 0:
                shortfall_scenario_count[policy] += 1

        optimizer = by_policy["optimizer"].metrics
        non_optimizer = [
            result.metrics
            for policy, result in by_policy.items()
            if policy != "optimizer"
        ]
        best_baseline_shortfall = min(
            metric.cash_shortfall_days for metric in non_optimizer
        )
        same_shortfall_costs = [
            metric.financing_cost
            for metric in non_optimizer
            if metric.cash_shortfall_days <= optimizer.cash_shortfall_days
        ]
        best_comparable_cost = min(same_shortfall_costs, default=None)
        if optimizer.cash_shortfall_days > best_baseline_shortfall:
            optimizer_more_shortfall_count += 1
        if (
            best_comparable_cost is not None
            and optimizer.financing_cost > best_comparable_cost
        ):
            optimizer_higher_cost_count += 1
        if (
            optimizer.cash_shortfall_days > best_baseline_shortfall
            or (
                best_comparable_cost is not None
                and optimizer.financing_cost > best_comparable_cost
            )
        ):
            failure_cases.append(
                {
                    "scenario_seed": scenario_seed,
                    "invoice_count": len(invoices),
                    "obligation_count": len(obligations),
                    "optimizer": optimizer.model_dump(),
                    "best_baseline_shortfall_days": best_baseline_shortfall,
                    "best_baseline_cost_at_equal_or_better_shortfall": best_comparable_cost,
                    "baseline_metrics": {
                        policy: result.metrics.model_dump()
                        for policy, result in by_policy.items()
                        if policy != "optimizer"
                    },
                }
            )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    experiment_id = f"benchmark-{args.scenario_count}-seed-{args.seed}-{timestamp}"
    summary = {
        "experiment_id": experiment_id,
        "commit_sha": git_commit(),
        "working_tree_dirty": git_worktree_dirty(),
        "source_sha256": source_fingerprint(),
        "dataset_version": "synthetic-benchmark-v1",
        "scenario_count": args.scenario_count,
        "base_seed": args.seed,
        "policy_version": "mvp-v2",
        "model_version": "heuristic-payment-timing-v2",
        "assumptions": {
            "horizon_days": 91,
            "invoice_count_range": [3, 16],
            "delay_shocks_days": [0, 7, 15, 30],
            "treds_annual_rate_range": [0.08, 0.24],
            "fee_assumption": "no financing fees in this benchmark, per user clarification",
            "treds_advance_rate_range": [0.9, 1.0],
            "financing_caps": "per invoice in this prototype",
            "payment_realization": "common across policies within each scenario",
            "decision_timing": "policies use expected timing, not realized future dates",
            "optimizer_search": "exact subset search through 14 eligible invoices; greedy fallback above 14",
            "optimizer_objective_order": [
                "cash-shortfall days",
                "financing cost",
                "financed invoice count",
            ],
        },
        "policies": {
            policy: {
                **{
                    metric: summarize(values)
                    for metric, values in metrics.items()
                },
                "scenarios_with_any_cash_shortfall": shortfall_scenario_count[policy],
                "cash_shortfall_scenario_rate": shortfall_scenario_count[policy]
                / args.scenario_count,
            }
            for policy, metrics in policy_metrics.items()
        },
        "scenarios_with_optimizer_tradeoff_or_regression": len(failure_cases),
        "optimizer_more_shortfall_than_best_baseline_scenarios": optimizer_more_shortfall_count,
        "optimizer_higher_cost_at_equal_or_better_shortfall_scenarios": optimizer_higher_cost_count,
        "optimizer_exact_search_scenarios": optimizer_exact_search_scenario_count,
        "optimizer_greedy_fallback_scenarios": optimizer_greedy_fallback_scenario_count,
        "failure_cases_file": f"failure-cases-{experiment_id}.json",
    }
    report_lines = [
        "# MSME Receivables Decision Lab — Benchmark Report",
        "",
        f"- Experiment: `{experiment_id}`",
        f"- Commit: `{summary['commit_sha'] or 'unknown'}`",
        f"- Scenarios: {args.scenario_count}",
        f"- Base seed: {args.seed}",
        "- Data: generated synthetic cases; not production payment histories",
        "- Comparison: each policy received the same realized payment timing per scenario",
        "",
        "## Summary",
        "",
        "Values below are median / p90 across scenarios. Amounts are rupees.",
        "",
        "| Policy | Min cash (median / p90) | Shortfall days (median / p90) | Scenarios with any shortfall | Financing cost (median / p90) | Amount financed (median / p90) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for policy, metrics in summary["policies"].items():
        report_lines.append(
            f"| {policy} | {metrics['minimum_cash']['median']:,.0f} / {metrics['minimum_cash']['p90']:,.0f} "
            f"| {metrics['cash_shortfall_days']['median']:.1f} / {metrics['cash_shortfall_days']['p90']:.1f} "
            f"| {metrics['scenarios_with_any_cash_shortfall']} / {args.scenario_count} "
            f"| {metrics['financing_cost']['median']:,.0f} / {metrics['financing_cost']['p90']:,.0f} "
            f"| {metrics['financed_amount']['median']:,.0f} / {metrics['financed_amount']['p90']:,.0f} |"
        )
    report_lines.extend(
        [
            "",
            "## Optimizer cases to inspect",
            "",
            f"The failure-case artifact contains {len(failure_cases)} cases where the optimizer had more shortfall days than the best baseline, or higher financing cost than a baseline with equal or fewer shortfall days.",
            "This label identifies cases for inspection; it does not by itself mean the objective is invalid.",
            "",
            "## Limits",
            "",
            "These results measure behavior on synthetic assumptions only. They do not establish calibrated payment probabilities, market financing terms, or real-world policy performance.",
            "",
        ]
    )

    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    summary_path = output_dir / f"benchmark-summary-{experiment_id}.json"
    report_path = output_dir / f"benchmark-report-{experiment_id}.md"
    failures_path = output_dir / f"failure-cases-{experiment_id}.json"
    summary["report_file"] = report_path.name
    summary["failure_cases_file"] = failures_path.name
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    failures_path.write_text(json.dumps(failure_cases, indent=2), encoding="utf-8")

    print(f"Experiment: {experiment_id}")
    print(f"Summary: {summary_path}")
    print(f"Report: {report_path}")
    print(f"Failure cases: {failures_path} ({len(failure_cases)})")


if __name__ == "__main__":
    main()
