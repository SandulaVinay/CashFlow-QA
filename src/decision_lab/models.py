from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal["WAIT", "FOLLOW_UP", "FINANCE_TREDS", "FINANCE_OTHER"]


class Invoice(BaseModel):
    invoice_id: str
    buyer_id: str
    invoice_date: date
    due_date: date
    amount: float = Field(gt=0)
    historical_avg_delay_days: float = Field(ge=0)
    historical_delay_std_days: float = Field(ge=0)
    historical_late_rate: float = Field(ge=0, le=1)
    eligible_for_treds: bool = True


class Obligation(BaseModel):
    date: date
    category: str
    amount: float = Field(gt=0)


class FinancingOffer(BaseModel):
    source: Literal["TReDS", "OD", "OTHER"]
    annual_rate: float = Field(ge=0)
    fee_rate: float = Field(ge=0)
    advance_rate: float = Field(gt=0, le=1)
    max_amount: float = Field(gt=0)


class Scenario(BaseModel):
    as_of_date: date
    opening_cash: float
    minimum_cash_buffer: float = Field(ge=0)
    horizon_days: int = Field(default=91, ge=1, le=365)
    follow_up_acceleration_days: int = Field(default=10, ge=0)
    payment_delay_shock_days: int = 0
    seed: int = 42
    financing_offers: list[FinancingOffer]


class ActionDecision(BaseModel):
    invoice_id: str
    action: ActionType
    financing_source: str | None = None


class DailyCashPoint(BaseModel):
    day: int
    date: date
    opening_cash: float
    collections: float
    financing_inflow: float
    obligations: float
    financing_cost: float
    closing_cash: float


class SimulationMetrics(BaseModel):
    minimum_cash: float
    maximum_cash: float
    ending_cash: float
    cash_shortfall_days: int
    financing_cost: float
    financed_amount: float
    accelerated_receivables: float
    financed_invoice_count: int
    follow_up_invoice_count: int


class SimulationResult(BaseModel):
    policy: str
    actions: list[ActionDecision]
    metrics: SimulationMetrics
    cash_curve: list[DailyCashPoint]
    scenario_seed: int
