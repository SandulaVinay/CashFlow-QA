from __future__ import annotations

import random
from datetime import date
from math import erf, exp, pi, sqrt

from .models import Invoice, Scenario


def expected_payment_day(invoice: Invoice, scenario: Scenario) -> int:
    """Expected collection day relative to the scenario start.

    The synthetic realization first samples whether an invoice is late, then
    draws a normally distributed delay for late invoices and clips negative
    delays to zero. Use the late rate times the clipped-normal expected delay
    so the policy schedule follows the same lateness rule. The continuous
    clipped-normal mean approximates the rounded draw; payment days are
    rounded to whole days.
    """
    days_to_due = max(0, (invoice.due_date - scenario.as_of_date).days)
    mean = invoice.historical_avg_delay_days
    sigma = max(invoice.historical_delay_std_days, 1.0)
    z = mean / sigma
    normal_cdf = 0.5 * (1.0 + erf(z / sqrt(2.0)))
    normal_pdf = exp(-0.5 * z * z) / sqrt(2.0 * pi)
    expected_delay_if_late = max(0.0, sigma * normal_pdf + mean * normal_cdf)
    expected_delay = invoice.historical_late_rate * expected_delay_if_late
    return (
        days_to_due
        + round(expected_delay)
        + scenario.payment_delay_shock_days
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

    return days_to_due + delay
