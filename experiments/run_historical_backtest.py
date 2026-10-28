from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from decision_lab.historical import HistoricalDataBundle
from decision_lab.rolling_backtest import (
    RollingBacktestConfig,
    generate_rolling_origins,
    run_rolling_origin_backtest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a leakage-aware rolling-origin payment-timing backtest."
    )
    parser.add_argument("--data", required=True, type=Path, help="Historical data contract JSON")
    parser.add_argument("--origin-start", required=True, type=date.fromisoformat)
    parser.add_argument("--origin-end", required=True, type=date.fromisoformat)
    parser.add_argument("--frequency", choices=["monthly", "weekly", "daily"], default="monthly")
    parser.add_argument("--grace-days", type=int, default=0)
    parser.add_argument("--min-buyer-history", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()

    if not args.data.is_file():
        parser.error(f"Historical data file does not exist: {args.data}")

    try:
        dataset = HistoricalDataBundle.model_validate_json(
            args.data.read_text(encoding="utf-8")
        )
    except Exception as exc:
        parser.error(f"Historical data contract validation failed: {exc}")

    origins = generate_rolling_origins(
        args.origin_start,
        args.origin_end,
        timezone_name=dataset.timezone,
        frequency=args.frequency,
    )
    config = RollingBacktestConfig(
        grace_days=args.grace_days,
        min_buyer_history=args.min_buyer_history,
    )
    try:
        report = run_rolling_origin_backtest(dataset, origins, config)
    except ValueError as exc:
        parser.error(str(exc))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_dataset_id = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in dataset.dataset_id
    )
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"historical-backtest-{safe_dataset_id}-{stamp}.json"
    output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"Dataset: {dataset.dataset_id}")
    print(f"Origins: {len(report.origins)}")
    print(f"Currency: {dataset.currency}")
    print(
        "Aggregate: "
        f"scored={report.summary.scored_invoice_count} "
        f"censored={report.summary.censored_invoice_count} "
        f"late-recorded={report.summary.settled_before_origin_but_recorded_late_count} "
        f"MAE={report.summary.payment_mae_days if report.summary.payment_mae_days is not None else 'n/a'}d "
        f"due-baseline-MAE={report.summary.due_date_baseline_mae_days if report.summary.due_date_baseline_mae_days is not None else 'n/a'}d"
    )
    for row in report.origins:
        mae = "n/a" if row.payment_mae_days is None else f"{row.payment_mae_days:.2f}"
        baseline = "n/a" if row.due_date_baseline_mae_days is None else f"{row.due_date_baseline_mae_days:.2f}"
        print(
            f"{row.origin_at.date()} train={row.training_invoice_count:4d} "
            f"open={row.open_invoice_count:4d} scored={row.scored_invoice_count:4d} "
            f"censored={row.censored_invoice_count:4d} MAE={mae}d due-baseline={baseline}d"
        )
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
