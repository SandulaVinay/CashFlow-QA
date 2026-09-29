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
