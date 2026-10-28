from __future__ import annotations

from .models import Invoice, Obligation, Scenario, SimulationResult
from .policies import POLICIES
from .simulator import build_realized_payment_days, simulate


def compare_policies(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    policy_names: list[str] | None = None,
) -> list[SimulationResult]:
    names = policy_names or list(POLICIES.keys())
    common_payment_days = build_realized_payment_days(invoices, scenario)
    results: list[SimulationResult] = []

    for name in names:
        if name not in POLICIES:
            raise ValueError(f"Unknown policy: {name}")
        actions = POLICIES[name](invoices, obligations, scenario)
        results.append(
            simulate(
                invoices,
                obligations,
                scenario,
                actions,
                policy_name=name,
                payment_days=common_payment_days,
            )
        )
    return results
