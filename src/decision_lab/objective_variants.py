from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .behaviour import expected_payment_day
from .models import ActionDecision, Invoice, Obligation, Scenario
from .simulator import financing_terms


DEFAULT_REMAINING_RISK_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class CandidateScore:
    selected_ids: frozenset[str]
    expected_shortfall_days: int
    expected_shortfall_amount_days: float
    financing_cost: float
    financed_invoice_count: int


@dataclass(frozen=True)
class ObjectiveSelection:
    actions: list[ActionDecision]
    expected_shortfall_days: int
    expected_shortfall_amount_days: float
    expected_financing_cost: float
    risk_limit_amount_days: float
    risk_limit_met: bool
    search_method: str


def risk_budget_policy_name(remaining_fraction: float) -> str:
    percent = round(remaining_fraction * 100)
    return f"risk_limit_{percent:03d}pct_of_wait"


def _score_candidate(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    selected_ids: frozenset[str],
    expected_payment_days: dict[str, int],
) -> CandidateScore:
    """Score a financing subset on the expected schedule, never realized dates."""
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
    shortfall_amount_days = 0.0
    for change in daily_net:
        cash += change
        deficit = max(0.0, scenario.minimum_cash_buffer - cash)
        if deficit > 0:
            shortfall_days += 1
            shortfall_amount_days += deficit

    return CandidateScore(
        selected_ids=selected_ids,
        expected_shortfall_days=shortfall_days,
        expected_shortfall_amount_days=shortfall_amount_days,
        financing_cost=total_cost,
        financed_invoice_count=len(selected_ids),
    )


def _score_key(score: CandidateScore) -> tuple:
    return (
        score.expected_shortfall_amount_days,
        score.financing_cost,
        score.expected_shortfall_days,
        score.financed_invoice_count,
        tuple(sorted(score.selected_ids)),
    )


def _exact_candidate_scores(
    eligible: list[Invoice],
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    expected_payment_days: dict[str, int],
) -> list[CandidateScore]:
    scores = [
        _score_candidate(
            invoices, obligations, scenario, frozenset(), expected_payment_days
        )
    ]
    for size in range(1, len(eligible) + 1):
        for subset in combinations(eligible, size):
            selected_ids = frozenset(invoice.invoice_id for invoice in subset)
            scores.append(
                _score_candidate(
                    invoices,
                    obligations,
                    scenario,
                    selected_ids,
                    expected_payment_days,
                )
            )
    return scores


def _greedy_candidate_scores(
    eligible: list[Invoice],
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    expected_payment_days: dict[str, int],
) -> list[CandidateScore]:
    """Build an improving risk-reduction path for portfolios above exact limit."""
    selected_ids: frozenset[str] = frozenset()
    current = _score_candidate(
        invoices, obligations, scenario, selected_ids, expected_payment_days
    )
    path = [current]
    remaining = {invoice.invoice_id: invoice for invoice in eligible}

    while remaining and current.expected_shortfall_amount_days > 0:
        choices: list[tuple[tuple, Invoice, CandidateScore]] = []
        for invoice in remaining.values():
            candidate = _score_candidate(
                invoices,
                obligations,
                scenario,
                selected_ids | {invoice.invoice_id},
                expected_payment_days,
            )
            reduction = (
                current.expected_shortfall_amount_days
                - candidate.expected_shortfall_amount_days
            )
            if reduction <= 0:
                continue
            incremental_cost = candidate.financing_cost - current.financing_cost
            cost_per_risk_reduction = (
                incremental_cost / reduction if reduction > 0 else float("inf")
            )
            choices.append(
                (
                    (
                        cost_per_risk_reduction,
                        -reduction,
                        incremental_cost,
                        invoice.invoice_id,
                    ),
                    invoice,
                    candidate,
                )
            )

        if not choices:
            break
        _, chosen, current = min(choices, key=lambda item: item[0])
        selected_ids = current.selected_ids
        remaining.pop(chosen.invoice_id)
        path.append(current)

    return path


def _actions_for(score: CandidateScore, invoices: list[Invoice]) -> list[ActionDecision]:
    return [
        ActionDecision(
            invoice_id=invoice.invoice_id,
            action=(
                "FINANCE_TREDS"
                if invoice.invoice_id in score.selected_ids
                else "WAIT"
            ),
            financing_source=(
                "TReDS" if invoice.invoice_id in score.selected_ids else None
            ),
        )
        for invoice in invoices
    ]


def cost_guarded_objectives(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    remaining_risk_fractions: tuple[float, ...] = DEFAULT_REMAINING_RISK_FRACTIONS,
    max_exact_invoices: int = 14,
) -> dict[str, ObjectiveSelection]:
    """Return least-cost financing sets under expected deficit-risk limits.

    Each fraction limits expected cash-buffer deficit amount-days to that share
    of the WAIT policy's expected deficit. Within the limit, financing cost is
    minimized. If the requested limit cannot be reached, the best achievable
    expected-risk candidate is returned and marked as unmet.
    """
    if not remaining_risk_fractions:
        raise ValueError("At least one remaining-risk fraction is required")
    if any(not 0 <= fraction <= 1 for fraction in remaining_risk_fractions):
        raise ValueError("Remaining-risk fractions must be between 0 and 1")

    eligible = [invoice for invoice in invoices if invoice.eligible_for_treds]
    expected_payment_days = {
        invoice.invoice_id: expected_payment_day(invoice, scenario)
        for invoice in invoices
    }
    if len(eligible) <= max_exact_invoices:
        scores = _exact_candidate_scores(
            eligible, invoices, obligations, scenario, expected_payment_days
        )
        search_method = "exact_subset_search"
    else:
        scores = _greedy_candidate_scores(
            eligible, invoices, obligations, scenario, expected_payment_days
        )
        search_method = "greedy_risk_reduction"

    wait_score = next(score for score in scores if not score.selected_ids)
    results: dict[str, ObjectiveSelection] = {}
    for fraction in remaining_risk_fractions:
        risk_limit = wait_score.expected_shortfall_amount_days * fraction
        feasible = [
            score
            for score in scores
            if score.expected_shortfall_amount_days <= risk_limit + 1e-6
        ]
        if feasible:
            chosen = min(
                feasible,
                key=lambda score: (
                    score.financing_cost,
                    score.expected_shortfall_amount_days,
                    score.expected_shortfall_days,
                    score.financed_invoice_count,
                    tuple(sorted(score.selected_ids)),
                ),
            )
            limit_met = True
        else:
            chosen = min(scores, key=_score_key)
            limit_met = False

        results[risk_budget_policy_name(fraction)] = ObjectiveSelection(
            actions=_actions_for(chosen, invoices),
            expected_shortfall_days=chosen.expected_shortfall_days,
            expected_shortfall_amount_days=chosen.expected_shortfall_amount_days,
            expected_financing_cost=chosen.financing_cost,
            risk_limit_amount_days=risk_limit,
            risk_limit_met=limit_met,
            search_method=search_method,
        )

    return results
