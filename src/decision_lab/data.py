from __future__ import annotations

import random
from datetime import date, timedelta

from .models import FinancingOffer, Invoice, Obligation, Scenario


def generate_demo(seed: int = 42) -> tuple[list[Invoice], list[Obligation], Scenario]:
    rng = random.Random(seed)
    as_of = date(2026, 10, 1)

    buyers = [
        ("BUYER-A", 0.15, 4.0, 8.0, 0.35),
        ("BUYER-B", 0.65, 18.0, 9.0, 0.45),
        ("BUYER-C", 0.80, 32.0, 15.0, 0.55),
        ("BUYER-D", 0.35, 10.0, 6.0, 0.40),
        ("BUYER-E", 0.90, 24.0, 12.0, 0.65),
        ("BUYER-F", 0.20, 6.0, 5.0, 0.30),
    ]

    invoices: list[Invoice] = []
    for idx in range(12):
        buyer_id, late_rate, avg_delay, std_delay, _ = buyers[idx % len(buyers)]
        due_in = rng.randint(5, 60)
        amount = float(rng.randint(5, 20) * 100_000)
        invoice_date = as_of - timedelta(days=rng.randint(7, 45))
        invoices.append(
            Invoice(
                invoice_id=f"INV-{idx + 1:03d}",
                buyer_id=buyer_id,
                invoice_date=invoice_date,
                due_date=as_of + timedelta(days=due_in),
                amount=amount,
                historical_avg_delay_days=avg_delay,
                historical_delay_std_days=std_delay,
                historical_late_rate=late_rate,
                eligible_for_treds=(idx != 5),
            )
        )

    obligations: list[Obligation] = [
        Obligation(date=as_of + timedelta(days=2), category="Supplier", amount=600_000),
        Obligation(date=as_of + timedelta(days=7), category="Payroll", amount=800_000),
        Obligation(date=as_of + timedelta(days=14), category="Supplier", amount=700_000),
        Obligation(date=as_of + timedelta(days=21), category="Supplier", amount=650_000),
        Obligation(date=as_of + timedelta(days=30), category="Payroll", amount=800_000),
        Obligation(date=as_of + timedelta(days=30), category="Rent", amount=150_000),
        Obligation(date=as_of + timedelta(days=35), category="Tax", amount=900_000),
        Obligation(date=as_of + timedelta(days=45), category="Supplier", amount=750_000),
        Obligation(date=as_of + timedelta(days=60), category="Payroll", amount=800_000),
        Obligation(date=as_of + timedelta(days=65), category="Supplier", amount=750_000),
        Obligation(date=as_of + timedelta(days=75), category="Loan/EMI", amount=500_000),
        Obligation(date=as_of + timedelta(days=90), category="Payroll", amount=800_000),
    ]

    offers = [
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
    ]

    scenario = Scenario(
        as_of_date=as_of,
        opening_cash=1_200_000,
        minimum_cash_buffer=1_000_000,
        horizon_days=91,
        follow_up_acceleration_days=10,
        payment_delay_shock_days=5,
        seed=seed,
        financing_offers=offers,
    )

    return invoices, obligations, scenario


def generate_benchmark_case(
    seed: int,
) -> tuple[list[Invoice], list[Obligation], Scenario]:
    """Generate one reproducible synthetic case for controlled policy tests."""
    rng = random.Random(seed)
    as_of = date(2026, 10, 1)
    buyer_count = rng.randint(2, 6)
    buyers = {
        f"BUYER-{index + 1:02d}": (
            rng.uniform(0.05, 0.95),
            rng.uniform(0.0, 45.0),
            rng.uniform(1.0, 24.0),
        )
        for index in range(buyer_count)
    }

    invoices: list[Invoice] = []
    for index in range(rng.randint(3, 16)):
        buyer_id = rng.choice(list(buyers))
        late_rate, avg_delay, delay_std = buyers[buyer_id]
        invoices.append(
            Invoice(
                invoice_id=f"S{seed}-INV-{index + 1:02d}",
                buyer_id=buyer_id,
                invoice_date=as_of - timedelta(days=rng.randint(5, 90)),
                due_date=as_of + timedelta(days=rng.randint(-5, 80)),
                amount=float(rng.randint(50_000, 1_500_000)),
                historical_avg_delay_days=round(avg_delay, 2),
                historical_delay_std_days=round(delay_std, 2),
                historical_late_rate=round(late_rate, 3),
                eligible_for_treds=rng.random() >= 0.1,
            )
        )

    categories = ["Supplier", "Payroll", "Tax", "Rent", "Loan/EMI"]
    obligations = [
        Obligation(
            date=as_of + timedelta(days=rng.randint(0, 91)),
            category=rng.choice(categories),
            amount=float(rng.randint(50_000, 700_000)),
        )
        for _ in range(rng.randint(4, 12))
    ]

    offers = [
        FinancingOffer(
            source="TReDS",
            annual_rate=round(rng.uniform(0.08, 0.24), 4),
            fee_rate=0.0,
            advance_rate=round(rng.uniform(0.9, 1.0), 4),
            max_amount=float(rng.randint(500_000, 3_000_000)),
        ),
        FinancingOffer(
            source="OD",
            annual_rate=round(rng.uniform(0.1, 0.3), 4),
            fee_rate=0.0,
            advance_rate=1.0,
            max_amount=float(rng.randint(500_000, 3_000_000)),
        ),
    ]
    opening_cash = float(rng.randint(200_000, 5_000_000))
    scenario = Scenario(
        as_of_date=as_of,
        opening_cash=opening_cash,
        minimum_cash_buffer=round(opening_cash * rng.uniform(0.2, 0.8), 2),
        horizon_days=91,
        follow_up_acceleration_days=rng.choice([0, 3, 7, 10, 14]),
        payment_delay_shock_days=rng.choice([0, 7, 15, 30]),
        seed=seed,
        financing_offers=offers,
    )
    return invoices, obligations, scenario
