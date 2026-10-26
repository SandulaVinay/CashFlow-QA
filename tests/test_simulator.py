import random
from datetime import date, timedelta

import pytest

from decision_lab.behaviour import expected_payment_day, realized_payment_day
from decision_lab.data import generate_benchmark_case
from decision_lab.engine import compare_policies
from decision_lab.models import (
    ActionDecision,
    FinancingOffer,
    Invoice,
    Obligation,
    Scenario,
)
from decision_lab.policies import _expected_candidate_score, liquidity_cost_optimizer
from decision_lab.simulator import build_realized_payment_days, simulate


def scenario() -> Scenario:
    as_of = date(2026, 10, 1)
    return Scenario(
        as_of_date=as_of,
        opening_cash=1_000_000,
        minimum_cash_buffer=500_000,
        horizon_days=30,
        follow_up_acceleration_days=10,
        payment_delay_shock_days=0,
        seed=7,
        financing_offers=[
            FinancingOffer(
                source="TReDS",
                annual_rate=0.12,
                fee_rate=0.0,
                advance_rate=0.98,
                max_amount=10_000_000,
            ),
            FinancingOffer(
                source="OD",
                annual_rate=0.14,
                fee_rate=0.0,
                advance_rate=1.0,
                max_amount=10_000_000,
            ),
        ],
    )


def test_simulation_never_changes_opening_cash_before_day_zero_inputs():
    s = scenario()
    invoice = Invoice(
        invoice_id="INV-1",
        buyer_id="B1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 10),
        amount=1_000_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=2,
        historical_late_rate=0.8,
    )
    obligations = [
        Obligation(date=s.as_of_date + timedelta(days=5), category="supplier", amount=100_000)
    ]

    actions = []
    result = simulate([invoice], obligations, s, actions, policy_name="wait")

    assert result.cash_curve[0].closing_cash == s.opening_cash


def test_optimizer_returns_only_valid_actions():
    s = scenario()
    invoice = Invoice(
        invoice_id="INV-1",
        buyer_id="B1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 5),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
    )
    actions = liquidity_cost_optimizer([invoice], [], s)
    assert actions[0].invoice_id == "INV-1"
    assert actions[0].action in {"WAIT", "FINANCE_TREDS"}


def test_reproducibility_with_same_seed():
    s = scenario()
    invoice = Invoice(
        invoice_id="INV-1",
        buyer_id="B1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 5),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
    )

    result1 = simulate([invoice], [], s, [], policy_name="wait")
    result2 = simulate([invoice], [], s, [], policy_name="wait")

    assert result1.metrics == result2.metrics
    assert result1.cash_curve == result2.cash_curve


def test_hand_calculation_pure_collection():
    s = scenario()
    s.opening_cash = 1_000
    invoice = Invoice(
        invoice_id="COLLECTION",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=5),
        amount=200,
        historical_avg_delay_days=0,
        historical_delay_std_days=0,
        historical_late_rate=0,
    )

    result = simulate(
        [invoice], [], s, [], "wait", payment_days={invoice.invoice_id: 5}
    )

    assert result.cash_curve[5].closing_cash == 1_200
    assert result.metrics.minimum_cash == 1_000
    assert result.metrics.ending_cash == 1_200


def test_hand_calculation_pure_obligation():
    s = scenario()
    s.opening_cash = 1_000
    obligation = Obligation(
        date=s.as_of_date + timedelta(days=5), category="supplier", amount=200
    )

    result = simulate([], [obligation], s, [], "wait")

    assert result.cash_curve[5].closing_cash == 800
    assert result.metrics.minimum_cash == 800
    assert result.metrics.ending_cash == 800


def test_hand_calculation_wait_with_collection_and_obligation():
    s = scenario()
    s.opening_cash = 1_000
    invoice = Invoice(
        invoice_id="WAIT",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=10),
        amount=600,
        historical_avg_delay_days=0,
        historical_delay_std_days=0,
        historical_late_rate=0,
    )
    obligation = Obligation(
        date=s.as_of_date + timedelta(days=5), category="supplier", amount=300
    )

    result = simulate(
        [invoice], [obligation], s, [], "wait", payment_days={invoice.invoice_id: 10}
    )

    assert result.cash_curve[5].closing_cash == 700
    assert result.cash_curve[10].closing_cash == 1_300
    assert result.metrics.minimum_cash == 700
    assert result.metrics.ending_cash == 1_300


def test_payment_after_horizon_is_not_pulled_forward():
    s = scenario()
    s.horizon_days = 30
    invoice = Invoice(
        invoice_id="LATE",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=40),
        amount=600,
        historical_avg_delay_days=0,
        historical_delay_std_days=0,
        historical_late_rate=0,
    )

    assert expected_payment_day(invoice, s) == 40
    assert realized_payment_day(invoice, s, random.Random(1)) == 40
    result = simulate([invoice], [], s, [], "wait", payment_days={invoice.invoice_id: 40})
    assert result.metrics.ending_cash == s.opening_cash


def test_negative_payment_delay_shock_is_rejected():
    data = scenario().model_dump()
    data["payment_delay_shock_days"] = -1

    with pytest.raises(ValueError):
        Scenario(**data)


@pytest.mark.parametrize(
    "action_ids, message",
    [
        (["UNKNOWN"], "unknown invoice"),
        (["KNOWN", "KNOWN"], "Duplicate action"),
    ],
)
def test_invalid_action_references_are_rejected(action_ids, message):
    invoice = Invoice(
        invoice_id="KNOWN",
        buyer_id="B1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 5),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
        eligible_for_treds=False,
    )
    parsed_actions = [
        ActionDecision(invoice_id=invoice_id, action="WAIT")
        for invoice_id in action_ids
    ]

    with pytest.raises(ValueError, match=message):
        simulate([invoice], [], scenario(), parsed_actions, "invalid")


def test_ineligible_invoice_cannot_be_financed_through_treds():
    invoice = Invoice(
        invoice_id="INELIGIBLE",
        buyer_id="B1",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 5),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
        eligible_for_treds=False,
    )
    action = ActionDecision(invoice_id=invoice.invoice_id, action="FINANCE_TREDS")

    with pytest.raises(ValueError, match="not eligible for TReDS"):
        simulate([invoice], [], scenario(), [action], "invalid")


def test_hand_calculated_treds_advance_cost_and_residual_settlement():
    s = scenario()
    s.opening_cash = 1_000_000
    s.horizon_days = 45
    invoice = Invoice(
        invoice_id="FINANCE-MANUAL",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=10),
        due_date=s.as_of_date + timedelta(days=30),
        amount=1_000_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=0,
        historical_late_rate=1,
    )
    action = ActionDecision(invoice_id=invoice.invoice_id, action="FINANCE_TREDS")

    result = simulate(
        [invoice],
        [],
        s,
        [action],
        "finance",
        payment_days={invoice.invoice_id: 40},
    )

    advance = 980_000
    interest = advance * 0.12 * 40 / 365
    fees = 0.0
    residual = 20_000
    expected_day_zero_cash = 1_000_000 + advance - interest - fees
    expected_ending_cash = expected_day_zero_cash + residual

    assert result.cash_curve[0].financing_inflow == advance
    assert result.cash_curve[0].financing_cost == pytest.approx(interest + fees)
    assert result.cash_curve[0].closing_cash == pytest.approx(expected_day_zero_cash)
    assert result.cash_curve[40].collections == 0
    assert result.cash_curve[40].residual_release == residual
    assert result.metrics.financed_amount == advance
    assert result.metrics.financing_interest == pytest.approx(interest)
    assert result.metrics.financing_fees == pytest.approx(fees)
    assert result.metrics.financing_cost == pytest.approx(interest + fees)
    assert result.metrics.residual_receivable == residual
    assert result.metrics.accelerated_receivables == advance
    assert result.metrics.ending_cash == pytest.approx(expected_ending_cash)


def test_policy_comparison_passes_one_common_payment_realization(monkeypatch):
    import decision_lab.engine as engine

    s = scenario()
    invoice = Invoice(
        invoice_id="COMMON",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=20),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
    )
    received_payment_days = []
    original_simulate = engine.simulate

    def capture_payment_days(*args, **kwargs):
        received_payment_days.append(kwargs["payment_days"])
        return original_simulate(*args, **kwargs)

    monkeypatch.setattr(engine, "simulate", capture_payment_days)
    compare_policies([invoice], [], s, ["wait", "largest_first"])

    assert len(received_payment_days) == 2
    assert received_payment_days[0] is received_payment_days[1]
    assert received_payment_days[0] == build_realized_payment_days([invoice], s)


def test_optimizer_scores_using_expected_payment_timing(monkeypatch):
    import decision_lab.policies as policies

    s = scenario()
    invoice = Invoice(
        invoice_id="NO-HINDSIGHT",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=20),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
    )
    scored_payment_days = []
    original_score = policies._expected_candidate_score

    def capture_payment_days(*args, **kwargs):
        scored_payment_days.append(args[4])
        return original_score(*args, **kwargs)

    monkeypatch.setattr(policies, "_expected_candidate_score", capture_payment_days)
    liquidity_cost_optimizer([invoice], [], s)

    expected = {invoice.invoice_id: expected_payment_day(invoice, s)}
    assert scored_payment_days
    assert all(payment_days == expected for payment_days in scored_payment_days)


def test_fast_optimizer_score_matches_full_simulator():
    s = scenario()
    invoice = Invoice(
        invoice_id="SCORE-MATCH",
        buyer_id="B1",
        invoice_date=s.as_of_date - timedelta(days=1),
        due_date=s.as_of_date + timedelta(days=20),
        amount=800_000,
        historical_avg_delay_days=10,
        historical_delay_std_days=3,
        historical_late_rate=0.9,
    )
    payment_days = {invoice.invoice_id: expected_payment_day(invoice, s)}
    action = ActionDecision(invoice_id=invoice.invoice_id, action="FINANCE_TREDS")

    result = simulate([invoice], [], s, [action], "candidate", payment_days)
    fast_score = _expected_candidate_score(
        [invoice], [], s, {invoice.invoice_id}, payment_days
    )

    assert fast_score == (
        result.metrics.cash_shortfall_days,
        pytest.approx(result.metrics.financing_cost),
        result.metrics.financed_invoice_count,
    )


def test_benchmark_case_generation_is_reproducible():
    first = generate_benchmark_case(20260930)
    second = generate_benchmark_case(20260930)

    assert [item.model_dump() for item in first[0]] == [
        item.model_dump() for item in second[0]
    ]
    assert [item.model_dump() for item in first[1]] == [
        item.model_dump() for item in second[1]
    ]
    assert first[2].model_dump() == second[2].model_dump()
    assert all(offer.fee_rate == 0 for offer in first[2].financing_offers)
