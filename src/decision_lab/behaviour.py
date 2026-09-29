from __future__ import annotations

import random
from datetime import date

from .models import Invoice, Scenario


def expected_payment_day(invoice: Invoice, scenario: Scenario) -> int:
    """Expected collection day relative to the scenario start."""
    days_to_due = max(0, (invoice.due_date - scenario.as_of_date).days)
    return min(
        scenario.horizon_days,
        days_to_due + round(invoice.historical_avg_delay_days) + scenario.payment_delay_shock_days,
    )


def payment_delay_risk(invoice: Invoice) -> float:
    """Transparent risk score from historical payment behaviour.

    This is intentionally heuristic for MVP. It is not an ML prediction.
    """
    lateness_component = invoice.historical_late_rate
    delay_component = min(invoice.historical_avg_delay_days / 60.0, 1.0)
    volatility_component = min(invoice.historical_delay_std_days / 45.0, 1.0)
    history_risk = 0.55 * lateness_component + 0.30 * delay_component + 0.15 * volatility_component
    return max(0.0, min(1.0, history_risk))


def realized_payment_day(
    invoice: Invoice,
    scenario: Scenario,
    rng: random.Random,
    follow_up: bool = False,
) -> int:
    """Generate one reproducible payment-timing realization.

    A late-payment indicator is sampled first; late days are then sampled
    around the historical average. Synthetic only: do not treat as a
    production probability model.
    """
    days_to_due = max(0, (invoice.due_date - scenario.as_of_date).days)

    if rng.random() > invoice.historical_late_rate:
        delay = 0
    else:
        sigma = max(invoice.historical_delay_std_days, 1.0)
        delay = max(0, round(rng.gauss(invoice.historical_avg_delay_days, sigma)))

    delay += scenario.payment_delay_shock_days
    if follow_up:
        delay = max(0, delay - scenario.follow_up_acceleration_days)

    return min(scenario.horizon_days, days_to_due + delay)
