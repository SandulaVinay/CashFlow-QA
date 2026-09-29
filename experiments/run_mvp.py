from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from decision_lab.data import generate_demo
from decision_lab.engine import compare_policies


def main() -> None:
    invoices, obligations, scenario = generate_demo(seed=42)
    results = compare_policies(invoices, obligations, scenario)

    report = {
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
    output_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

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
