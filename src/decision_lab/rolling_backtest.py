"""Leakage-aware rolling-origin evaluation for historical payment timing.

This first backtest validates payment-timing baselines only. It does not yet
claim to replay actual historical policy actions or infer counterfactual cash
balances, which require trusted cash-ledger and decision-time snapshots.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
import calendar
import statistics
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field

from .historical import (
    CashBalanceSnapshot,
    HistoricalDataBundle,
    HistoricalInvoice,
    HistoricalPayment,
    local_date,
)


class RollingBacktestConfig(BaseModel):
    grace_days: int = Field(default=0, ge=0, le=90)
    min_buyer_history: int = Field(default=3, ge=1)
    cold_start_late_probability: float = Field(default=0.5, ge=0, le=1)
    cold_start_delay_days: int = Field(default=0, ge=0, le=365)


class PaymentTimingPrediction(BaseModel):
    origin_at: AwareDatetime
    invoice_id: str
    buyer_id: str
    amount: float
    due_date: date
    predicted_delay_days: int
    predicted_late_probability: float
    predicted_payment_date: date
    due_date_baseline_prediction: date
    prediction_source: Literal["buyer_history", "global_history", "cold_start"]
    buyer_training_count: int
    global_training_count: int
    actual_payment_date: date | None = None
    actual_delay_days: int | None = None
    absolute_error_days: int | None = None
    due_date_baseline_absolute_error_days: int | None = None
    brier_score: float | None = None
    outcome_status: Literal["scored", "censored", "settled_before_origin_but_recorded_late"]


class RollingOriginResult(BaseModel):
    origin_at: AwareDatetime
    training_invoice_count: int
    open_invoice_count: int
    scored_invoice_count: int
    censored_invoice_count: int
    settled_before_origin_but_recorded_late_count: int
    cash_snapshot_available: bool
    cash_snapshot_balance: float | None = None
    payment_mae_days: float | None = None
    payment_median_absolute_error_days: float | None = None
    due_date_baseline_mae_days: float | None = None
    payment_mean_signed_error_days: float | None = None
    amount_weighted_payment_mae_days: float | None = None
    late_brier_score: float | None = None
    actual_late_rate: float | None = None
    cold_start_prediction_count: int
    global_history_prediction_count: int
    buyer_history_prediction_count: int
    predictions: list[PaymentTimingPrediction]


class RollingBacktestSummary(BaseModel):
    # Metrics aggregate all origin/invoice forecast instances. An invoice may
    # appear at more than one origin, so rows are not independent observations.
    origin_count: int
    open_invoice_prediction_count: int
    scored_invoice_count: int
    censored_invoice_count: int
    settled_before_origin_but_recorded_late_count: int
    payment_mae_days: float | None = None
    payment_median_absolute_error_days: float | None = None
    due_date_baseline_mae_days: float | None = None
    payment_mean_signed_error_days: float | None = None
    amount_weighted_payment_mae_days: float | None = None
    late_brier_score: float | None = None
    actual_late_rate: float | None = None
    cold_start_prediction_count: int
    global_history_prediction_count: int
    buyer_history_prediction_count: int


class RollingBacktestReport(BaseModel):
    dataset_id: str
    currency: str
    timezone: str
    source_data_complete_through: AwareDatetime
    config: RollingBacktestConfig
    summary: RollingBacktestSummary
    origins: list[RollingOriginResult]


def _payments_by_invoice(payments: list[HistoricalPayment]) -> dict[str, list[HistoricalPayment]]:
    by_invoice: dict[str, list[HistoricalPayment]] = defaultdict(list)
    for payment in payments:
        by_invoice[payment.invoice_id].append(payment)
    for values in by_invoice.values():
        values.sort(key=lambda item: (item.payment_at, item.recorded_at, item.payment_id))
    return dict(by_invoice)


def _settlement_date(
    invoice: HistoricalInvoice,
    payments: list[HistoricalPayment],
    timezone_name: str,
    as_of: datetime,
    require_recorded_by_as_of: bool,
    source_complete_through: datetime,
) -> date | None:
    """Return the date the invoice became fully paid under an explicit view.

    For feature construction, only payment events already recorded by the
    decision cutoff are visible. For labels, all events through the declared
    source watermark are available to evaluate the outcome retrospectively.
    """
    total = 0.0
    for payment in payments:
        if payment.payment_at > source_complete_through:
            continue
        if payment.payment_at > as_of:
            continue
        if require_recorded_by_as_of and payment.recorded_at > as_of:
            continue
        total += payment.amount
        if total + 1e-6 >= invoice.amount:
            return local_date(payment.payment_at, timezone_name)
    return None


def _actual_settlement_by_watermark(
    invoice: HistoricalInvoice,
    payments: list[HistoricalPayment],
    timezone_name: str,
    source_complete_through: datetime,
) -> date | None:
    total = 0.0
    for payment in payments:
        if payment.payment_at > source_complete_through:
            continue
        total += payment.amount
        if total + 1e-6 >= invoice.amount:
            return local_date(payment.payment_at, timezone_name)
    return None


def _latest_invoice_versions(
    invoices: list[HistoricalInvoice], cutoff: datetime
) -> list[HistoricalInvoice]:
    latest: dict[str, HistoricalInvoice] = {}
    for invoice in invoices:
        if invoice.recorded_at > cutoff:
            continue
        current = latest.get(invoice.invoice_id)
        if current is None or (invoice.recorded_at, invoice.version) > (
            current.recorded_at,
            current.version,
        ):
            latest[invoice.invoice_id] = invoice
    return list(latest.values())


def _known_cash_snapshot(
    snapshots: list[CashBalanceSnapshot], cutoff: datetime
) -> CashBalanceSnapshot | None:
    eligible = [
        item for item in snapshots
        if item.as_of_at <= cutoff and item.recorded_at <= cutoff
    ]
    return max(eligible, key=lambda item: (item.as_of_at, item.recorded_at)) if eligible else None


def _history_delay(settlement_date: date, invoice: HistoricalInvoice) -> int:
    return max(0, (settlement_date - invoice.due_date).days)


def run_rolling_origin_backtest(
    dataset: HistoricalDataBundle,
    origins: list[datetime],
    config: RollingBacktestConfig | None = None,
) -> RollingBacktestReport:
    """Evaluate a simple historical-median delay baseline at each origin.

    Leakage controls:
    * Invoice versions and payment events used for features must be recorded by
      the origin; due dates and amounts are taken from the latest visible version.
    * Training invoices must be fully settled using payments visible by origin.
    * Future payment dates are used only to score predictions, never to create
      the training set, calculate history statistics, or choose predictions.
    * A test invoice is open according to information visible at the origin.
    * If the true settlement occurred before origin but was recorded only later,
      the case is flagged as a data-timeliness issue and not scored as a future
      timing forecast.
    """
    config = config or RollingBacktestConfig()
    if not origins:
        raise ValueError("At least one rolling origin is required")

    zone = ZoneInfo(dataset.timezone)
    normalized_origins: list[datetime] = []
    for origin in origins:
        if origin.tzinfo is None or origin.utcoffset() is None:
            raise ValueError("Every rolling origin must be timezone-aware")
        local_origin = origin.astimezone(zone)
        if local_origin > dataset.source_data_complete_through.astimezone(zone):
            raise ValueError("Rolling origins cannot exceed source_data_complete_through")
        normalized_origins.append(local_origin)
    if len(set(normalized_origins)) != len(normalized_origins):
        raise ValueError("Rolling origins must be unique")
    normalized_origins.sort()

    payments_by_invoice = _payments_by_invoice(dataset.payments)
    result_rows: list[RollingOriginResult] = []

    for origin in normalized_origins:
        origin_date = origin.date()
        visible_invoices = [
            invoice for invoice in _latest_invoice_versions(dataset.invoices, origin)
            if invoice.invoice_date <= origin_date
        ]

        training_delays_by_buyer: dict[str, list[int]] = defaultdict(list)
        global_delays: list[int] = []
        for invoice in visible_invoices:
            visible_payments = payments_by_invoice.get(invoice.invoice_id, [])
            visible_settlement = _settlement_date(
                invoice,
                visible_payments,
                dataset.timezone,
                origin,
                require_recorded_by_as_of=True,
                source_complete_through=dataset.source_data_complete_through,
            )
            # Settlement date <= origin is not enough on its own: require that
            # all payment records needed to prove full settlement were visible.
            if visible_settlement is None or visible_settlement > origin_date:
                continue
            delay = _history_delay(visible_settlement, invoice)
            training_delays_by_buyer[invoice.buyer_id].append(delay)
            global_delays.append(delay)

        global_median_delay = (
            int(round(statistics.median(global_delays))) if global_delays else None
        )
        global_late_rate = (
            sum(1 for value in global_delays if value > config.grace_days) / len(global_delays)
            if global_delays else None
        )

        predictions: list[PaymentTimingPrediction] = []
        actual_errors: list[int] = []
        baseline_errors: list[int] = []
        signed_errors: list[int] = []
        weighted_errors: list[tuple[int, float]] = []
        brier_scores: list[float] = []
        actual_late_labels: list[int] = []
        censored_count = 0
        late_recorded_count = 0
        source_counts = {"cold_start": 0, "global_history": 0, "buyer_history": 0}

        for invoice in sorted(visible_invoices, key=lambda item: item.invoice_id):
            visible_payments = payments_by_invoice.get(invoice.invoice_id, [])
            visible_settlement = _settlement_date(
                invoice,
                visible_payments,
                dataset.timezone,
                origin,
                require_recorded_by_as_of=True,
                source_complete_through=dataset.source_data_complete_through,
            )
            if visible_settlement is not None and visible_settlement <= origin_date:
                continue  # already known settled: it is not a forecast candidate

            buyer_delays = training_delays_by_buyer.get(invoice.buyer_id, [])
            if len(buyer_delays) >= config.min_buyer_history:
                delay_prediction = int(round(statistics.median(buyer_delays)))
                late_probability = sum(1 for value in buyer_delays if value > config.grace_days) / len(buyer_delays)
                prediction_source: Literal["buyer_history", "global_history", "cold_start"] = "buyer_history"
            elif global_delays:
                delay_prediction = global_median_delay or 0
                late_probability = global_late_rate if global_late_rate is not None else config.cold_start_late_probability
                prediction_source = "global_history"
            else:
                delay_prediction = config.cold_start_delay_days
                late_probability = config.cold_start_late_probability
                prediction_source = "cold_start"

            predicted_date = max(origin_date, invoice.due_date + timedelta(days=delay_prediction))
            due_baseline_date = max(origin_date, invoice.due_date)
            actual_settlement = _actual_settlement_by_watermark(
                invoice,
                visible_payments,
                dataset.timezone,
                dataset.source_data_complete_through,
            )

            actual_payment_date: date | None = None
            actual_delay: int | None = None
            absolute_error: int | None = None
            baseline_error: int | None = None
            brier_score: float | None = None
            if actual_settlement is None:
                status: Literal["scored", "censored", "settled_before_origin_but_recorded_late"] = "censored"
                censored_count += 1
            elif actual_settlement <= origin_date:
                # Retrospective evidence says the invoice had already been paid,
                # but the system had not recorded enough receipts to know that.
                status = "settled_before_origin_but_recorded_late"
                late_recorded_count += 1
            else:
                status = "scored"
                actual_payment_date = actual_settlement
                actual_delay = max(0, (actual_settlement - invoice.due_date).days)
                absolute_error = abs((actual_settlement - predicted_date).days)
                baseline_error = abs((actual_settlement - due_baseline_date).days)
                target_late = int(actual_settlement > invoice.due_date + timedelta(days=config.grace_days))
                brier_score = (late_probability - target_late) ** 2
                actual_errors.append(absolute_error)
                baseline_errors.append(baseline_error)
                signed_errors.append((predicted_date - actual_settlement).days)
                weighted_errors.append((absolute_error, invoice.amount))
                brier_scores.append(brier_score)
                actual_late_labels.append(target_late)

            predictions.append(
                PaymentTimingPrediction(
                    origin_at=origin,
                    invoice_id=invoice.invoice_id,
                    buyer_id=invoice.buyer_id,
                    amount=invoice.amount,
                    due_date=invoice.due_date,
                    predicted_delay_days=delay_prediction,
                    predicted_late_probability=late_probability,
                    predicted_payment_date=predicted_date,
                    due_date_baseline_prediction=due_baseline_date,
                    prediction_source=prediction_source,
                    buyer_training_count=len(buyer_delays),
                    global_training_count=len(global_delays),
                    actual_payment_date=actual_payment_date,
                    actual_delay_days=actual_delay,
                    absolute_error_days=absolute_error,
                    due_date_baseline_absolute_error_days=baseline_error,
                    brier_score=brier_score,
                    outcome_status=status,
                )
            )
            source_counts[prediction_source] += 1

        cash_snapshot = _known_cash_snapshot(dataset.cash_balances, origin)
        amount_weighted_mae = (
            sum(error * amount for error, amount in weighted_errors)
            / sum(amount for _, amount in weighted_errors)
            if weighted_errors and sum(amount for _, amount in weighted_errors) > 0
            else None
        )
        result_rows.append(
            RollingOriginResult(
                origin_at=origin,
                training_invoice_count=len(global_delays),
                open_invoice_count=len(predictions),
                scored_invoice_count=len(actual_errors),
                censored_invoice_count=censored_count,
                settled_before_origin_but_recorded_late_count=late_recorded_count,
                cash_snapshot_available=cash_snapshot is not None,
                cash_snapshot_balance=cash_snapshot.balance if cash_snapshot else None,
                payment_mae_days=statistics.fmean(actual_errors) if actual_errors else None,
                payment_median_absolute_error_days=statistics.median(actual_errors) if actual_errors else None,
                due_date_baseline_mae_days=statistics.fmean(baseline_errors) if baseline_errors else None,
                payment_mean_signed_error_days=statistics.fmean(signed_errors) if signed_errors else None,
                amount_weighted_payment_mae_days=amount_weighted_mae,
                late_brier_score=statistics.fmean(brier_scores) if brier_scores else None,
                actual_late_rate=statistics.fmean(actual_late_labels) if actual_late_labels else None,
                cold_start_prediction_count=source_counts["cold_start"],
                global_history_prediction_count=source_counts["global_history"],
                buyer_history_prediction_count=source_counts["buyer_history"],
                predictions=predictions,
            )
        )

    all_predictions = [prediction for row in result_rows for prediction in row.predictions]
    scored_predictions = [
        prediction for prediction in all_predictions
        if prediction.outcome_status == "scored"
        and prediction.absolute_error_days is not None
        and prediction.actual_payment_date is not None
    ]
    abs_errors = [prediction.absolute_error_days for prediction in scored_predictions]
    baseline_errors = [
        prediction.due_date_baseline_absolute_error_days
        for prediction in scored_predictions
        if prediction.due_date_baseline_absolute_error_days is not None
    ]
    signed_errors = [
        (prediction.predicted_payment_date - prediction.actual_payment_date).days
        for prediction in scored_predictions
        if prediction.actual_payment_date is not None
    ]
    brier_scores = [
        prediction.brier_score for prediction in scored_predictions
        if prediction.brier_score is not None
    ]
    late_labels = [
        int(prediction.actual_payment_date > prediction.due_date + timedelta(days=config.grace_days))
        for prediction in scored_predictions
        if prediction.actual_payment_date is not None
    ]
    amount_weighted_abs = [
        (prediction.absolute_error_days, prediction.amount)
        for prediction in scored_predictions
        if prediction.absolute_error_days is not None
    ]
    weight_total = sum(amount for _, amount in amount_weighted_abs)
    aggregate_summary = RollingBacktestSummary(
        origin_count=len(result_rows),
        open_invoice_prediction_count=len(all_predictions),
        scored_invoice_count=len(scored_predictions),
        censored_invoice_count=sum(row.censored_invoice_count for row in result_rows),
        settled_before_origin_but_recorded_late_count=sum(
            row.settled_before_origin_but_recorded_late_count for row in result_rows
        ),
        payment_mae_days=statistics.fmean(abs_errors) if abs_errors else None,
        payment_median_absolute_error_days=statistics.median(abs_errors) if abs_errors else None,
        due_date_baseline_mae_days=statistics.fmean(baseline_errors) if baseline_errors else None,
        payment_mean_signed_error_days=statistics.fmean(signed_errors) if signed_errors else None,
        amount_weighted_payment_mae_days=(
            sum(error * amount for error, amount in amount_weighted_abs) / weight_total
            if weight_total else None
        ),
        late_brier_score=statistics.fmean(brier_scores) if brier_scores else None,
        actual_late_rate=statistics.fmean(late_labels) if late_labels else None,
        cold_start_prediction_count=sum(row.cold_start_prediction_count for row in result_rows),
        global_history_prediction_count=sum(row.global_history_prediction_count for row in result_rows),
        buyer_history_prediction_count=sum(row.buyer_history_prediction_count for row in result_rows),
    )
    return RollingBacktestReport(
        dataset_id=dataset.dataset_id,
        currency=dataset.currency,
        timezone=dataset.timezone,
        source_data_complete_through=dataset.source_data_complete_through,
        config=config,
        summary=aggregate_summary,
        origins=result_rows,
    )


def generate_rolling_origins(
    start_date: date,
    end_date: date,
    timezone_name: str = "Asia/Kolkata",
    frequency: Literal["monthly", "weekly", "daily"] = "monthly",
) -> list[datetime]:
    """Generate local end-of-day cutoffs for a reproducible backtest schedule."""
    if end_date < start_date:
        raise ValueError("end_date cannot precede start_date")
    if frequency not in {"monthly", "weekly", "daily"}:
        raise ValueError("frequency must be monthly, weekly, or daily")
    zone = ZoneInfo(timezone_name)
    dates: list[date] = []
    current = start_date
    anchor_day = start_date.day
    anchor_is_month_end = anchor_day == calendar.monthrange(start_date.year, start_date.month)[1]
    while current <= end_date:
        dates.append(current)
        if frequency == "daily":
            current += timedelta(days=1)
        elif frequency == "weekly":
            current += timedelta(days=7)
        else:
            month_index = current.month  # zero-based next-month calculation
            year = current.year + month_index // 12
            month = month_index % 12 + 1
            last_day = calendar.monthrange(year, month)[1]
            next_day = last_day if anchor_is_month_end else min(anchor_day, last_day)
            current = date(year, month, next_day)
    return [datetime.combine(item, time(23, 59, 59, 999999), tzinfo=zone) for item in dates]
