from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from decision_lab.historical import (
    CashBalanceSnapshot,
    HistoricalDataBundle,
    HistoricalInvoice,
    HistoricalPayment,
)
from decision_lab.rolling_backtest import (
    RollingBacktestConfig,
    generate_rolling_origins,
    run_rolling_origin_backtest,
    _actual_settlement_by_watermark,
)

TZ = ZoneInfo("Asia/Kolkata")


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def invoice(
    invoice_id: str,
    buyer_id: str,
    invoice_date: str,
    due_date: str,
    amount: float,
    recorded_at: str,
    version: int = 1,
) -> HistoricalInvoice:
    return HistoricalInvoice(
        invoice_id=invoice_id,
        version=version,
        buyer_id=buyer_id,
        invoice_date=date.fromisoformat(invoice_date),
        due_date=date.fromisoformat(due_date),
        amount=amount,
        recorded_at=dt(recorded_at),
    )


def sample_bundle() -> HistoricalDataBundle:
    return HistoricalDataBundle(
        dataset_id="rolling-backtest-test",
        currency="INR",
        timezone="Asia/Kolkata",
        source_data_complete_through=dt("2026-06-30T23:59:59+05:30"),
        invoices=[
            invoice("OLD-A1", "BUYER-A", "2026-01-01", "2026-01-10", 100, "2026-01-01T10:00:00+05:30"),
            invoice("OLD-A2", "BUYER-A", "2026-02-01", "2026-02-10", 100, "2026-02-01T10:00:00+05:30"),
            invoice("OLD-B1", "BUYER-B", "2026-03-01", "2026-03-10", 100, "2026-03-01T10:00:00+05:30"),
            invoice("TEST-A", "BUYER-A", "2026-04-01", "2026-04-20", 100, "2026-04-01T10:00:00+05:30", version=1),
            invoice("TEST-A", "BUYER-A", "2026-04-01", "2026-04-25", 100, "2026-04-18T10:00:00+05:30", version=2),
            invoice("CENSORED-B", "BUYER-B", "2026-04-01", "2026-04-10", 100, "2026-04-01T10:00:00+05:30"),
            invoice("LATE-REC-A", "BUYER-A", "2026-04-01", "2026-04-12", 100, "2026-04-01T10:00:00+05:30"),
            invoice("NOT-YET-RECORDED", "BUYER-C", "2026-04-20", "2026-05-10", 100, "2026-04-20T10:00:00+05:30"),
        ],
        payments=[
            HistoricalPayment(
                payment_id="P-OLD-A1", invoice_id="OLD-A1",
                payment_at=dt("2026-01-15T10:00:00+05:30"),
                recorded_at=dt("2026-01-15T10:05:00+05:30"), amount=100,
            ),
            HistoricalPayment(
                payment_id="P-OLD-A2", invoice_id="OLD-A2",
                payment_at=dt("2026-02-25T10:00:00+05:30"),
                recorded_at=dt("2026-02-25T10:05:00+05:30"), amount=100,
            ),
            HistoricalPayment(
                payment_id="P-OLD-B1", invoice_id="OLD-B1",
                payment_at=dt("2026-03-10T10:00:00+05:30"),
                recorded_at=dt("2026-03-10T10:05:00+05:30"), amount=100,
            ),
            HistoricalPayment(
                payment_id="P-TEST-A", invoice_id="TEST-A",
                payment_at=dt("2026-04-30T10:00:00+05:30"),
                recorded_at=dt("2026-04-30T11:00:00+05:30"), amount=100,
            ),
            HistoricalPayment(
                payment_id="P-LATE-REC-A", invoice_id="LATE-REC-A",
                payment_at=dt("2026-04-14T10:00:00+05:30"),
                recorded_at=dt("2026-04-30T11:00:00+05:30"), amount=100,
            ),
        ],
        cash_balances=[
            CashBalanceSnapshot(
                snapshot_id="CASH-KNOWN",
                as_of_at=dt("2026-04-14T18:00:00+05:30"),
                recorded_at=dt("2026-04-14T18:05:00+05:30"),
                balance=750_000,
            ),
            CashBalanceSnapshot(
                snapshot_id="CASH-RECORDED-LATE",
                as_of_at=dt("2026-04-15T17:00:00+05:30"),
                recorded_at=dt("2026-04-16T10:00:00+05:30"),
                balance=700_000,
            ),
        ],
    )


def test_historical_payment_requires_timezone_aware_timestamps():
    with pytest.raises(ValidationError, match="timezone offset"):
        HistoricalPayment(
            payment_id="P1",
            invoice_id="INV1",
            payment_at=datetime(2026, 1, 1, 12, 0),
            recorded_at=dt("2026-01-01T12:05:00+05:30"),
            amount=10,
        )


def test_historical_payment_record_time_cannot_precede_event_time():
    with pytest.raises(ValidationError, match="cannot be earlier"):
        HistoricalPayment(
            payment_id="P1",
            invoice_id="INV1",
            payment_at=dt("2026-01-01T12:00:00+05:30"),
            recorded_at=dt("2026-01-01T11:59:00+05:30"),
            amount=10,
        )


def test_unknown_payment_invoice_reference_is_rejected():
    with pytest.raises(ValidationError, match="unknown invoice IDs"):
        HistoricalDataBundle(
            dataset_id="invalid",
            source_data_complete_through=dt("2026-06-30T23:59:59+05:30"),
            invoices=[invoice("KNOWN", "B", "2026-01-01", "2026-01-10", 10, "2026-01-01T10:00:00+05:30")],
            payments=[HistoricalPayment(
                payment_id="P1", invoice_id="MISSING",
                payment_at=dt("2026-01-11T10:00:00+05:30"),
                recorded_at=dt("2026-01-11T10:05:00+05:30"), amount=10,
            )],
        )


def test_rolling_origin_uses_only_invoice_versions_known_at_cutoff():
    dataset = sample_bundle()
    origin = dt("2026-04-15T23:59:59+05:30")
    report = run_rolling_origin_backtest(
        dataset, [origin], RollingBacktestConfig(min_buyer_history=2)
    )
    result = report.origins[0]
    by_id = {item.invoice_id: item for item in result.predictions}

    assert "NOT-YET-RECORDED" not in by_id
    assert by_id["TEST-A"].due_date == date(2026, 4, 20)
    assert by_id["TEST-A"].predicted_delay_days == 10
    assert by_id["TEST-A"].predicted_payment_date == date(2026, 4, 30)
    assert result.training_invoice_count == 3
    assert result.open_invoice_count == 3


def test_rolling_origin_separates_scored_censored_and_late_recorded_cases():
    dataset = sample_bundle()
    origin = dt("2026-04-15T23:59:59+05:30")
    result = run_rolling_origin_backtest(
        dataset, [origin], RollingBacktestConfig(min_buyer_history=2)
    ).origins[0]

    assert result.scored_invoice_count == 1
    assert result.censored_invoice_count == 1
    assert result.settled_before_origin_but_recorded_late_count == 1
    assert result.payment_mae_days == pytest.approx(0.0)
    assert result.due_date_baseline_mae_days == pytest.approx(10.0)
    assert result.late_brier_score == pytest.approx(0.0)
    assert result.cash_snapshot_available is True
    assert result.cash_snapshot_balance == 750_000
    assert run_rolling_origin_backtest(
        dataset, [origin], RollingBacktestConfig(min_buyer_history=2)
    ).summary.scored_invoice_count == 1


def test_future_payment_rows_do_not_change_earlier_predictions():
    original = sample_bundle()
    extended = sample_bundle()
    extended.payments.append(
        HistoricalPayment(
            payment_id="P-CENSORED-FUTURE",
            invoice_id="CENSORED-B",
            payment_at=dt("2026-05-15T10:00:00+05:30"),
            recorded_at=dt("2026-05-15T11:00:00+05:30"),
            amount=100,
        )
    )
    origin = dt("2026-04-15T23:59:59+05:30")
    config = RollingBacktestConfig(min_buyer_history=2)
    original_result = run_rolling_origin_backtest(original, [origin], config).origins[0]
    extended_result = run_rolling_origin_backtest(extended, [origin], config).origins[0]

    def feature_view(result):
        return [
            (
                item.invoice_id,
                item.due_date,
                item.predicted_delay_days,
                item.predicted_late_probability,
                item.predicted_payment_date,
                item.prediction_source,
                item.buyer_training_count,
                item.global_training_count,
            )
            for item in result.predictions
        ]

    assert feature_view(original_result) == feature_view(extended_result)
    assert extended_result.censored_invoice_count == 0
    assert extended_result.scored_invoice_count == 2


def test_later_invoice_version_and_payment_history_are_visible_at_later_origin():
    dataset = sample_bundle()
    origins = [
        dt("2026-04-15T23:59:59+05:30"),
        dt("2026-05-31T23:59:59+05:30"),
    ]
    report = run_rolling_origin_backtest(
        dataset, origins, RollingBacktestConfig(min_buyer_history=2)
    )
    first_predictions = {item.invoice_id: item for item in report.origins[0].predictions}
    second_predictions = {item.invoice_id: item for item in report.origins[1].predictions}

    assert first_predictions["TEST-A"].due_date == date(2026, 4, 20)
    assert "TEST-A" not in second_predictions
    assert "NOT-YET-RECORDED" in second_predictions
    assert report.origins[1].training_invoice_count == 5


def test_naive_cutoff_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        run_rolling_origin_backtest(sample_bundle(), [datetime(2026, 4, 15)])


def test_origin_beyond_source_completeness_watermark_is_rejected():
    with pytest.raises(ValueError, match="cannot exceed"):
        run_rolling_origin_backtest(
            sample_bundle(), [dt("2026-07-01T00:00:00+05:30")]
        )


def test_monthly_origin_generation_preserves_month_end_anchor():
    origins = generate_rolling_origins(
        date(2026, 1, 31), date(2026, 4, 30), frequency="monthly"
    )
    assert [item.date() for item in origins] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]


def test_data_bundle_rejects_duplicate_invoice_versions():
    first = invoice("DUP", "B", "2026-01-01", "2026-01-10", 10, "2026-01-01T10:00:00+05:30")
    with pytest.raises(ValidationError, match="pairs must be unique"):
        HistoricalDataBundle(
            dataset_id="duplicate-version",
            source_data_complete_through=dt("2026-06-30T23:59:59+05:30"),
            invoices=[first, first.model_copy()],
        )


def test_partial_receipts_settle_only_when_cumulative_amount_reaches_invoice_total():
    inv = invoice(
        "PARTIAL-INV", "BUYER-P", "2026-01-01", "2026-01-20", 100,
        "2026-01-01T10:00:00+05:30",
    )
    payment_rows = [
        HistoricalPayment(
            payment_id="PARTIAL-1", invoice_id=inv.invoice_id,
            payment_at=dt("2026-01-25T10:00:00+05:30"),
            recorded_at=dt("2026-01-25T10:05:00+05:30"), amount=40,
        ),
        HistoricalPayment(
            payment_id="PARTIAL-2", invoice_id=inv.invoice_id,
            payment_at=dt("2026-02-05T10:00:00+05:30"),
            recorded_at=dt("2026-02-05T10:05:00+05:30"), amount=60,
        ),
    ]
    settled = _actual_settlement_by_watermark(
        inv, payment_rows, "Asia/Kolkata", dt("2026-06-30T23:59:59+05:30")
    )
    assert settled == date(2026, 2, 5)


def test_grace_period_is_used_consistently_for_probability_and_outcome_label():
    dataset = sample_bundle()
    result = run_rolling_origin_backtest(
        dataset,
        [dt("2026-04-15T23:59:59+05:30")],
        RollingBacktestConfig(min_buyer_history=2, grace_days=7),
    ).origins[0]
    prediction = next(item for item in result.predictions if item.invoice_id == "TEST-A")
    assert prediction.predicted_late_probability == pytest.approx(0.5)
    assert prediction.brier_score == pytest.approx(0.25)
