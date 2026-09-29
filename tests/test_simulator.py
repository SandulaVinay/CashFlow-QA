from datetime import date, timedelta

from decision_lab.models import FinancingOffer, Invoice, Obligation, Scenario
from decision_lab.policies import liquidity_cost_optimizer
from decision_lab.simulator import simulate


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
                fee_rate=0.001,
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
