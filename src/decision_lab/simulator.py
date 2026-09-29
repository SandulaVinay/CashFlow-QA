from __future__ import annotations

import random
from collections import defaultdict
from datetime import timedelta

from .behaviour import realized_payment_day
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


def financing_terms(
    invoice: Invoice,
    scenario: Scenario,
    source: str,
) -> tuple[float, float]:
    offer = offer_for_source(scenario, source)
    expected_days = max(1, round(
        max(0, (invoice.due_date - scenario.as_of_date).days)
        + invoice.historical_avg_delay_days
        + scenario.payment_delay_shock_days
    ))

    financed_amount = invoice.amount * offer.advance_rate
    haircut = invoice.amount - financed_amount
    interest = financed_amount * offer.annual_rate * expected_days / 365.0
    fees = invoice.amount * offer.fee_rate
    total_cost = haircut + interest + fees
    return financed_amount, total_cost


def simulate(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    actions: list[ActionDecision],
    policy_name: str,
    rng: random.Random | None = None,
) -> SimulationResult:
    """Run one deterministic counterfactual.

    The caller should use the same RNG seed for competing policies so each
    policy experiences the same underlying payment-delay realization.
    """
    rng = rng or random.Random(scenario.seed)
    action_map = {a.invoice_id: a for a in actions}

    collections: dict[int, float] = defaultdict(float)
    financing_inflows: dict[int, float] = defaultdict(float)
    financing_costs: dict[int, float] = defaultdict(float)
    obligation_map: dict[int, float] = defaultdict(float)

    total_financed = 0.0
    total_financing_cost = 0.0
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
            financed_amount, cost = financing_terms(invoice, scenario, "TReDS")
            financing_inflows[0] += financed_amount
            financing_costs[0] += cost
            total_financed += financed_amount
            total_financing_cost += cost
            financed_count += 1
            continue

        if action.action == "FINANCE_OTHER":
            financed_amount, cost = financing_terms(invoice, scenario, "OD")
            financing_inflows[0] += financed_amount
            financing_costs[0] += cost
            total_financed += financed_amount
            total_financing_cost += cost
            financed_count += 1
            continue

        delay_rng = rng
        payment_day = realized_payment_day(
            invoice,
            scenario,
            delay_rng,
            follow_up=action.action == "FOLLOW_UP",
        )
        collections[payment_day] += invoice.amount

        if action.action == "FOLLOW_UP":
            baseline_day = realized_payment_day(
                invoice,
                scenario,
                random.Random(scenario.seed + sum(ord(c) for c in invoice.invoice_id)),
                follow_up=False,
            )
            if payment_day < baseline_day:
                accelerated += invoice.amount
                follow_up_count += 1

    cash = scenario.opening_cash
    points: list[DailyCashPoint] = []

    for day in range(0, scenario.horizon_days + 1):
        opening = cash
        inflow = collections[day] + financing_inflows[day]
        outflow = obligation_map[day] + financing_costs[day]
        cash = opening + inflow - outflow
        points.append(
            DailyCashPoint(
                day=day,
                date=scenario.as_of_date + timedelta(days=day),
                opening_cash=opening,
                collections=collections[day],
                financing_inflow=financing_inflows[day],
                obligations=obligation_map[day],
                financing_cost=financing_costs[day],
                closing_cash=cash,
            )
        )

    balances = [p.closing_cash for p in points]
    shortfall_days = sum(1 for value in balances if value < scenario.minimum_cash_buffer)

    metrics = SimulationMetrics(
        minimum_cash=min(balances),
        maximum_cash=max(balances),
        ending_cash=balances[-1],
        cash_shortfall_days=shortfall_days,
        financing_cost=total_financing_cost,
        financed_amount=total_financed,
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
