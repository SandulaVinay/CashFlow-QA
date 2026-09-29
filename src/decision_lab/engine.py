from __future__ import annotations

import random

from .models import Invoice, Obligation, Scenario, SimulationResult
from .policies import POLICIES
from .simulator import simulate


def compare_policies(
    invoices: list[Invoice],
    obligations: list[Obligation],
    scenario: Scenario,
    policy_names: list[str] | None = None,
) -> list[SimulationResult]:
    names = policy_names or list(POLICIES.keys())
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
                rng=random.Random(scenario.seed),
            )
        )

    return results
