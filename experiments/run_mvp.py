from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from decision_lab.data import generate_demo
from decision_lab.engine import compare_policies


def main() -> None:
    invoices, obligations, scenario = generate_demo(seed=42)
    results = compare_policies(invoices, obligations, scenario)

    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        working_tree_dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        commit_sha = None
        working_tree_dirty = None

    report = {
        "experiment_id": "mvp-baseline-seed-42",
        "commit_sha": commit_sha,
        "working_tree_dirty": working_tree_dirty,
        "dataset_version": "synthetic-demo-v1",
        "scenario_count": 1,
        "seed": scenario.seed,
        "policy_version": "mvp-v2",
        "model_version": "heuristic-payment-timing-v2",
        "scenario": scenario.model_dump(),
        "results": [
            {
                "policy": result.policy,
                "metrics": result.metrics.model_dump(),
                "actions": [action.model_dump() for action in result.actions],
            }
            for result in results
        ],
    }

    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "mvp-baseline.json"
    if output_file.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output_file = output_dir / f"mvp-baseline-{timestamp}.json"
    with output_file.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, default=str))

    print("MSME Receivables Decision Lab — MVP")
    print("=" * 50)
    for result in results:
        metrics = result.metrics
        print(
            f"{result.policy:24s} "
            f"min_cash={metrics.minimum_cash:,.0f} "
            f"shortfall_days={metrics.cash_shortfall_days:2d} "
            f"financing_cost={metrics.financing_cost:,.0f} "
            f"financed={metrics.financed_amount:,.0f}"
        )
    print(f"Report written to {output_file}")


if __name__ == "__main__":
    main()
