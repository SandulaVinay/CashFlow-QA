from __future__ import annotations

from itertools import combinations

from .behaviour import expected_payment_day, payment_delay_risk
from .models import ActionDecision, Invoice, Obligation, Scenario
from .simulator import financing_terms


def _wait_actions(invoices: list[Invoice]) -> list[ActionDecision]:
    return [ActionDecision(invoice_id=i.invoice_id, action="WAIT") for i in invoices]


def _expected_gap(invoices: list[Invoice], obligations: list[Obligation], scenario: Scenario) -> float:
    daily_collections: dict[int, float] = {}
    daily_obligations: dict[int, float] = {}

    for invoice in invoices:
        day = expected_payment_day(invoice, scenario)
        daily_collections[day] = daily_collections.get(day, 0.0) + invoice.amount

    for obligation in obligations:
        day = (obligation.date - scenario.as_of_date).days
        if 0 <= day <= scenario.horizon_days:
            daily_obligations[day] = daily_obligations.get(day, 0.0) + obligation.amount

    cash = scenario.opening_cash
    min_cash = cash
    for day in range(scenario.horizon_days + 1):
        cash += daily_collections.get(day, 0.0)
        cash -= daily_obligations.get(day, 0.0)
        min_cash = min(min_cash, cash)
    return max(0.0, scenario.minimum_cash_buffer - min_cash)


def _finance_ranked(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    ranked: list[Invoice],
) -> list[ActionDecision]:
    gap = _expected_gap(invoices, obligations, scenario)
    actions = _wait_actions(invoices)
    if gap <= 0:
        return actions

    covered = 0.0
    action_by_id = {action.invoice_id: action for action in actions}
    for invoice in ranked:
        if not invoice.eligible_for_treds:
            continue
        financed_amount = financing_terms(invoice, scenario, "TReDS").advance_amount
        action_by_id[invoice.invoice_id] = ActionDecision(
            invoice_id=invoice.invoice_id,
            action="FINANCE_TREDS",
            financing_source="TReDS",
        )
        covered += financed_amount
        if covered >= gap:
            break
    return [action_by_id[invoice.invoice_id] for invoice in invoices]


def largest_first(invoices, obligations, scenario):
    return _finance_ranked(
        invoices, obligations, scenario,
        sorted(invoices, key=lambda x: x.amount, reverse=True),
    )


def earliest_due_first(invoices, obligations, scenario):
    return _finance_ranked(
        invoices, obligations, scenario,
        sorted(invoices, key=lambda x: x.due_date),
    )


def highest_delay_risk_first(invoices, obligations, scenario):
    return _finance_ranked(
        invoices, obligations, scenario,
        sorted(invoices, key=payment_delay_risk, reverse=True),
    )


def cash_threshold(invoices, obligations, scenario):
    if _expected_gap(invoices, obligations, scenario) <= 0:
        return _wait_actions(invoices)
    return largest_first(invoices, obligations, scenario)


def _subset_actions(invoices: list[Invoice], selected_ids: set[str]) -> list[ActionDecision]:
    return [
        ActionDecision(
            invoice_id=invoice.invoice_id,
            action="FINANCE_TREDS" if invoice.invoice_id in selected_ids else "WAIT",
            financing_source="TReDS" if invoice.invoice_id in selected_ids else None,
        )
        for invoice in invoices
    ]


def _expected_candidate_score(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    selected_ids: set[str],
    expected_payment_days: dict[str, int],
) -> tuple[int, float, int]:
    """Score an expected-timing candidate without building API result objects."""
    daily_net = [0.0] * (scenario.horizon_days + 1)
    for invoice in invoices:
        day = expected_payment_days[invoice.invoice_id]
        if 0 <= day <= scenario.horizon_days:
            daily_net[day] += invoice.amount
    for obligation in obligations:
        day = (obligation.date - scenario.as_of_date).days
        if 0 <= day <= scenario.horizon_days:
            daily_net[day] -= obligation.amount

    total_cost = 0.0
    for invoice in invoices:
        if invoice.invoice_id not in selected_ids:
            continue
        terms = financing_terms(invoice, scenario, "TReDS")
        total_cost += terms.total_cost
        daily_net[0] += terms.advance_amount - terms.total_cost
        payment_day = expected_payment_days[invoice.invoice_id]
        if 0 <= payment_day <= scenario.horizon_days:
            daily_net[payment_day] -= terms.advance_amount

    cash = scenario.opening_cash
    shortfall_days = 0
    for change in daily_net:
        cash += change
        if cash < scenario.minimum_cash_buffer:
            shortfall_days += 1
    return shortfall_days, total_cost, len(selected_ids)


def liquidity_cost_optimizer(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    max_exact_invoices: int = 14,
) -> list[ActionDecision]:
    """Select a TReDS subset using an expected scenario, not hindsight."""
    eligible = [invoice for invoice in invoices if invoice.eligible_for_treds]
    if not eligible:
        return _wait_actions(invoices)

    expected_payment_days = {
        invoice.invoice_id: expected_payment_day(invoice, scenario)
        for invoice in invoices
    }

    if len(eligible) <= max_exact_invoices:
        best_ids: set[str] = set()
        best_score = _expected_candidate_score(
            invoices, obligations, scenario, best_ids, expected_payment_days
        )
        for size in range(1, len(eligible) + 1):
            for subset in combinations(eligible, size):
                candidate_ids = {invoice.invoice_id for invoice in subset}
                candidate_score = _expected_candidate_score(
                    invoices,
                    obligations,
                    scenario,
                    candidate_ids,
                    expected_payment_days,
                )
                if candidate_score < best_score:
                    best_ids, best_score = candidate_ids, candidate_score
        return _subset_actions(invoices, best_ids)

    ranked = sorted(
        eligible,
        key=lambda invoice: financing_terms(invoice, scenario, "TReDS").total_cost
        / max(invoice.amount, 1.0),
    )
    gap = _expected_gap(invoices, obligations, scenario)
    covered = 0.0
    action_by_id = {action.invoice_id: action for action in _wait_actions(invoices)}
    for invoice in ranked:
        financed_amount = financing_terms(invoice, scenario, "TReDS").advance_amount
        action_by_id[invoice.invoice_id] = ActionDecision(
            invoice_id=invoice.invoice_id,
            action="FINANCE_TREDS",
            financing_source="TReDS",
        )
        covered += financed_amount
        if covered >= gap:
            break
    return [action_by_id[invoice.invoice_id] for invoice in invoices]


POLICIES = {
    "wait": lambda i, o, s: _wait_actions(i),
    "largest_first": largest_first,
    "earliest_due_first": earliest_due_first,
    "highest_delay_risk_first": highest_delay_risk_first,
    "cash_threshold": cash_threshold,
    "optimizer": liquidity_cost_optimizer,
}
