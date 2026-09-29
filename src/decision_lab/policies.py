from __future__ import annotations

from itertools import combinations

from .behaviour import expected_payment_day, payment_delay_risk
from .models import ActionDecision, Invoice, Obligation, Scenario
from .simulator import financing_terms, simulate


def _wait_actions(invoices: list[Invoice]) -> list[ActionDecision]:
    return [
        ActionDecision(invoice_id=invoice.invoice_id, action="WAIT")
        for invoice in invoices
    ]


def _expected_gap(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
) -> float:
    """Estimate required cash at the worst point under expected wait timing."""
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
    action_by_id = {a.invoice_id: a for a in actions}

    for invoice in ranked:
        if not invoice.eligible_for_treds:
            continue
        financed_amount, _ = financing_terms(invoice, scenario, "TReDS")
        action_by_id[invoice.invoice_id] = ActionDecision(
            invoice_id=invoice.invoice_id,
            action="FINANCE_TREDS",
            financing_source="TReDS",
        )
        covered += financed_amount
        if covered >= gap:
            break

    return [action_by_id[invoice.invoice_id] for invoice in invoices]


def largest_first(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
) -> list[ActionDecision]:
    ranked = sorted(invoices, key=lambda x: x.amount, reverse=True)
    return _finance_ranked(invoices, obligations, scenario, ranked)


def earliest_due_first(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
) -> list[ActionDecision]:
    ranked = sorted(invoices, key=lambda x: x.due_date)
    return _finance_ranked(invoices, obligations, scenario, ranked)


def highest_delay_risk_first(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
) -> list[ActionDecision]:
    ranked = sorted(invoices, key=payment_delay_risk, reverse=True)
    return _finance_ranked(invoices, obligations, scenario, ranked)


def cash_threshold(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
) -> list[ActionDecision]:
    gap = _expected_gap(invoices, obligations, scenario)
    if gap <= 0:
        return _wait_actions(invoices)
    return largest_first(invoices, obligations, scenario)


def _subset_actions(
    invoices: list[Invoice],
    selected_ids: set[str],
) -> list[ActionDecision]:
    return [
        ActionDecision(
            invoice_id=invoice.invoice_id,
            action="FINANCE_TREDS" if invoice.invoice_id in selected_ids else "WAIT",
            financing_source="TReDS" if invoice.invoice_id in selected_ids else None,
        )
        for invoice in invoices
    ]


def liquidity_cost_optimizer(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    max_exact_invoices: int = 14,
) -> list[ActionDecision]:
    """Find a low-cost TReDS subset that removes expected cash shortfall.

    For <= max_exact_invoices eligible invoices, enumerate subsets exactly.
    For larger portfolios, fall back to cost-effectiveness greedy selection.
    """
    eligible = [i for i in invoices if i.eligible_for_treds]
    if not eligible:
        return _wait_actions(invoices)

    def score(actions: list[ActionDecision]) -> tuple[int, float]:
        result = simulate(
            invoices,
            obligations,
            scenario,
            actions,
            policy_name="optimizer_candidate",
        )
        shortfall = result.metrics.cash_shortfall_days
        cost = result.metrics.financing_cost
        return shortfall, cost

    if len(eligible) <= max_exact_invoices:
        best_actions = _wait_actions(invoices)
        best_score = score(best_actions)
        for r in range(1, len(eligible) + 1):
            for subset in combinations(eligible, r):
                candidate_ids = {invoice.invoice_id for invoice in subset}
                candidate_actions = _subset_actions(invoices, candidate_ids)
                candidate_score = score(candidate_actions)
                if candidate_score < best_score:
                    best_actions = candidate_actions
                    best_score = candidate_score
                    if best_score[0] == 0:
                        return best_actions
        return best_actions

    ranked = sorted(
        eligible,
        key=lambda invoice: financing_terms(invoice, scenario, "TReDS")[1]
        / max(invoice.amount, 1.0),
    )
    actions = _wait_actions(invoices)
    gap = _expected_gap(invoices, obligations, scenario)
    covered = 0.0
    action_by_id = {a.invoice_id: a for a in actions}

    for invoice in ranked:
        financed_amount, _ = financing_terms(invoice, scenario, "TReDS")
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
