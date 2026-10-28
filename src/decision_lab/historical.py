"""Versioned, timestamp-aware contracts for imported historical finance data.

The contracts distinguish business event time from the time a system learned
about the event. Rolling backtests must filter on recorded_at at decision
cutoffs; payment timestamps are outcomes and may only be used for scoring a
past decision after the fact.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.functional_validators import field_validator


class HistoricalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _require_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


class HistoricalInvoice(HistoricalRecord):
    """An invoice version as it was known to the source system at record time."""

    invoice_id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    buyer_id: str = Field(min_length=1)
    invoice_date: date
    due_date: date
    amount: float = Field(gt=0, allow_inf_nan=False)
    recorded_at: datetime
    eligible_for_treds: bool = False

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "recorded_at")


class HistoricalPayment(HistoricalRecord):
    """A receipt event, including both bank/business time and record time."""

    payment_id: str = Field(min_length=1)
    invoice_id: str = Field(min_length=1)
    payment_at: datetime
    recorded_at: datetime
    amount: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("payment_at", "recorded_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime, info) -> datetime:
        return _require_aware(value, info.field_name)

    @model_validator(mode="after")
    def record_does_not_precede_payment(self) -> "HistoricalPayment":
        if self.recorded_at < self.payment_at:
            raise ValueError("recorded_at cannot be earlier than payment_at")
        return self


class HistoricalObligation(HistoricalRecord):
    """A future cash obligation, versioned by the time its details were known."""

    obligation_id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    category: str = Field(min_length=1)
    due_date: date
    amount: float = Field(gt=0, allow_inf_nan=False)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "recorded_at")


class CashBalanceSnapshot(HistoricalRecord):
    """A cash balance observation; it is usable only after record time."""

    snapshot_id: str = Field(min_length=1)
    as_of_at: datetime
    recorded_at: datetime
    balance: float = Field(allow_inf_nan=False)

    @field_validator("as_of_at", "recorded_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime, info) -> datetime:
        return _require_aware(value, info.field_name)

    @model_validator(mode="after")
    def record_is_not_before_snapshot(self) -> "CashBalanceSnapshot":
        if self.recorded_at < self.as_of_at:
            raise ValueError("recorded_at cannot be earlier than as_of_at")
        return self


class HistoricalFinancingOffer(HistoricalRecord):
    """A financing offer and the period during which it was available."""

    offer_id: str = Field(min_length=1)
    source: Literal["TReDS", "OD", "OTHER"]
    annual_rate: float = Field(ge=0, allow_inf_nan=False)
    fee_rate: float = Field(ge=0, allow_inf_nan=False)
    advance_rate: float = Field(gt=0, le=1, allow_inf_nan=False)
    max_amount: float = Field(gt=0, allow_inf_nan=False)
    available_from: datetime
    available_until: datetime | None = None
    recorded_at: datetime

    @field_validator("available_from", "available_until", "recorded_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None, info):
        if value is None:
            return None
        return _require_aware(value, info.field_name)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "HistoricalFinancingOffer":
        if self.available_until is not None and self.available_until < self.available_from:
            raise ValueError("available_until cannot precede available_from")
        return self


class HistoricalDataBundle(HistoricalRecord):
    """All v1 inputs required to evaluate historical payment-timing baselines."""

    dataset_id: str = Field(min_length=1)
    contract_version: Literal["1"] = "1"
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    timezone: str = "Asia/Kolkata"
    # Event-time watermark: the source owner asserts that payment events whose
    # payment_at is at or before this timestamp are complete in this extract.
    source_data_complete_through: datetime
    invoices: list[HistoricalInvoice] = Field(min_length=1)
    payments: list[HistoricalPayment] = Field(default_factory=list)
    obligations: list[HistoricalObligation] = Field(default_factory=list)
    cash_balances: list[CashBalanceSnapshot] = Field(default_factory=list)
    financing_offers: list[HistoricalFinancingOffer] = Field(default_factory=list)

    @field_validator("source_data_complete_through")
    @classmethod
    def watermark_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "source_data_complete_through")

    @field_validator("timezone")
    @classmethod
    def timezone_is_valid(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone: {value}") from exc
        return value

    @model_validator(mode="after")
    def identifiers_and_references_are_valid(self) -> "HistoricalDataBundle":
        invoice_keys = [(item.invoice_id, item.version) for item in self.invoices]
        if len(invoice_keys) != len(set(invoice_keys)):
            raise ValueError("invoice (invoice_id, version) pairs must be unique")
        invoice_record_times = [(item.invoice_id, item.recorded_at) for item in self.invoices]
        if len(invoice_record_times) != len(set(invoice_record_times)):
            raise ValueError("invoice (invoice_id, recorded_at) pairs must be unique")
        payment_ids = [item.payment_id for item in self.payments]
        if len(payment_ids) != len(set(payment_ids)):
            raise ValueError("payment_id values must be unique")
        obligation_keys = [(item.obligation_id, item.version) for item in self.obligations]
        if len(obligation_keys) != len(set(obligation_keys)):
            raise ValueError("obligation (obligation_id, version) pairs must be unique")
        # Offer records may be versioned; only exact duplicate identifier/time
        # pairs are invalid.
        offer_keys = [(item.offer_id, item.recorded_at) for item in self.financing_offers]
        if len(offer_keys) != len(set(offer_keys)):
            raise ValueError("financing offer (offer_id, recorded_at) pairs must be unique")
        snapshot_ids = [item.snapshot_id for item in self.cash_balances]
        if len(snapshot_ids) != len(set(snapshot_ids)):
            raise ValueError("snapshot_id values must be unique")
        known_invoice_ids = {item.invoice_id for item in self.invoices}
        unknown = sorted({item.invoice_id for item in self.payments} - known_invoice_ids)
        if unknown:
            raise ValueError(f"payments reference unknown invoice IDs: {unknown}")
        return self


def local_date(value: datetime, timezone_name: str) -> date:
    """Return the business date in the dataset's configured timezone."""
    return value.astimezone(ZoneInfo(timezone_name)).date()
