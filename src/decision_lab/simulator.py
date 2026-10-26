from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from .behaviour import expected_payment_day, realized_payment_day
from .models import (
    ActionDecision,
    DailyCashPoint,
    FinancingOffer,
    Invoice,
    Obligation,
    Scenario,
    SimulationMetrics,
    SimulationResult,
)


def offer_for_source(scenario: Scenario, source: str) -> FinancingOffer:
    for offer in scenario.financing_offers:
        if offer.source == source:
            return offer
    raise ValueError(f"No financing offer configured for source={source}")


@dataclass(frozen=True)
class FinancingTerms:
    advance_amount: float
    interest_cost: float
    fee_cost: float
    residual_receivable: float

    @property
    def total_cost(self) -> float:
        return self.interest_cost + self.fee_cost


def financing_terms(
    invoice: Invoice,
    scenario: Scenario,
    source: str,
) -> FinancingTerms:
    offer = offer_for_source(scenario, source)
    expected_days = max(1, expected_payment_day(invoice, scenario))
    financed_amount = min(invoice.amount * offer.advance_rate, offer.max_amount)
    interest = financed_amount * offer.annual_rate * expected_days / 365.0
    fees = invoice.amount * offer.fee_rate
    return FinancingTerms(
        advance_amount=financed_amount,
        interest_cost=interest,
        fee_cost=fees,
        residual_receivable=invoice.amount - financed_amount,
    )


def build_realized_payment_days(
    invoices: list[Invoice],
    scenario: Scenario,
) -> dict[str, int]:
    """Create one common payment-timing realization for all policies."""
    realized: dict[str, int] = {}
    for invoice in invoices:
        stable_offset = int.from_bytes(
            hashlib.sha256(invoice.invoice_id.encode("utf-8")).digest()[:8],
            byteorder="big",
        )
        invoice_rng = random.Random(scenario.seed + stable_offset)
        realized[invoice.invoice_id] = realized_payment_day(
            invoice, scenario, invoice_rng, follow_up=False
        )
    return realized


def simulate(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    actions: list[ActionDecision],
    policy_name: str,
    payment_days: dict[str, int] | None = None,
) -> SimulationResult:
    """Run one deterministic counterfactual using fixed payment realizations."""
    payment_days = payment_days or build_realized_payment_days(invoices, scenario)
    invoice_by_id = {invoice.invoice_id: invoice for invoice in invoices}
    action_map = {}
    for action in actions:
        if action.invoice_id not in invoice_by_id:
            raise ValueError(f"Action references unknown invoice: {action.invoice_id}")
        if action.invoice_id in action_map:
            raise ValueError(f"Duplicate action for invoice: {action.invoice_id}")
        if (
            action.action == "FINANCE_TREDS"
            and not invoice_by_id[action.invoice_id].eligible_for_treds
        ):
            raise ValueError(
                f"Invoice is not eligible for TReDS: {action.invoice_id}"
            )
        if action.action == "FINANCE_TREDS" and action.financing_source not in (
            None,
            "TReDS",
        ):
            raise ValueError("FINANCE_TREDS action must use the TReDS source")
        if action.action == "FINANCE_OTHER" and action.financing_source not in (
            None,
            "OD",
            "OTHER",
        ):
            raise ValueError("FINANCE_OTHER action must use OD or OTHER financing")
        action_map[action.invoice_id] = action

    collections: dict[int, float] = defaultdict(float)
    residual_releases: dict[int, float] = defaultdict(float)
    financing_inflows: dict[int, float] = defaultdict(float)
    financing_costs: dict[int, float] = defaultdict(float)
    obligation_map: dict[int, float] = defaultdict(float)

    total_financed = 0.0
    total_financing_cost = 0.0
    total_financing_interest = 0.0
    total_financing_fees = 0.0
    total_residual_receivable = 0.0
    financed_count = 0
    follow_up_count = 0
    accelerated = 0.0

    for obligation in obligations:
        day = (obligation.date - scenario.as_of_date).days
        if 0 <= day <= scenario.horizon_days:
            obligation_map[day] += obligation.amount

    for invoice in invoices:
        action = action_map.get(
            invoice.invoice_id,
            ActionDecision(invoice_id=invoice.invoice_id, action="WAIT"),
        )

        if action.action == "FINANCE_TREDS":
            terms = financing_terms(invoice, scenario, "TReDS")
            payment_day = payment_days[invoice.invoice_id]
            financing_inflows[0] += terms.advance_amount
            financing_costs[0] += terms.total_cost
            residual_releases[payment_day] += terms.residual_receivable
            total_financed += terms.advance_amount
            total_financing_cost += terms.total_cost
            total_financing_interest += terms.interest_cost
            total_financing_fees += terms.fee_cost
            total_residual_receivable += terms.residual_receivable
            accelerated += terms.advance_amount
            financed_count += 1
            continue

        if action.action == "FINANCE_OTHER":
            source = action.financing_source or "OD"
            terms = financing_terms(invoice, scenario, source)
            payment_day = payment_days[invoice.invoice_id]
            financing_inflows[0] += terms.advance_amount
            financing_costs[0] += terms.total_cost
            residual_releases[payment_day] += terms.residual_receivable
            total_financed += terms.advance_amount
            total_financing_cost += terms.total_cost
            total_financing_interest += terms.interest_cost
            total_financing_fees += terms.fee_cost
            total_residual_receivable += terms.residual_receivable
            accelerated += terms.advance_amount
            financed_count += 1
            continue

        base_payment_day = payment_days[invoice.invoice_id]
        if action.action == "FOLLOW_UP":
            payment_day = max(0, base_payment_day - scenario.follow_up_acceleration_days)
            if payment_day < base_payment_day:
                accelerated += invoice.amount
                follow_up_count += 1
        else:
            payment_day = base_payment_day
        collections[payment_day] += invoice.amount

    cash = scenario.opening_cash
    points: list[DailyCashPoint] = []

    for day in range(0, scenario.horizon_days + 1):
        opening = cash
        inflow = collections[day] + residual_releases[day] + financing_inflows[day]
        outflow = obligation_map[day] + financing_costs[day]
        cash = opening + inflow - outflow
        points.append(
            DailyCashPoint(
                day=day,
                date=scenario.as_of_date + timedelta(days=day),
                opening_cash=opening,
                collections=collections[day],
                residual_release=residual_releases[day],
                financing_inflow=financing_inflows[day],
                obligations=obligation_map[day],
                financing_cost=financing_costs[day],
                closing_cash=cash,
            )
        )

    balances = [point.closing_cash for point in points]
    shortfall_days = sum(
        1 for value in balances if value < scenario.minimum_cash_buffer
    )
    shortfall_amount_days = sum(
        max(0.0, scenario.minimum_cash_buffer - value) for value in balances
    )

    metrics = SimulationMetrics(
        minimum_cash=min(balances),
        maximum_cash=max(balances),
        ending_cash=balances[-1],
        cash_shortfall_days=shortfall_days,
        cash_shortfall_amount_days=shortfall_amount_days,
        financing_cost=total_financing_cost,
        financing_interest=total_financing_interest,
        financing_fees=total_financing_fees,
        financed_amount=total_financed,
        residual_receivable=total_residual_receivable,
        accelerated_receivables=accelerated,
        financed_invoice_count=financed_count,
        follow_up_invoice_count=follow_up_count,
    )

    return SimulationResult(
        policy=policy_name,
        actions=actions,
        metrics=metrics,
        cash_curve=points,
        scenario_seed=scenario.seed,
    )
