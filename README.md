# MSME Receivables Decision Lab

This repository is historically named **CashFlow-QA**. Its active project is the MSME Receivables Decision Lab, a research-grade simulator for comparing receivables decisions under cash-flow constraints.

## What the project does

The project helps answer:

> When customer payments may be delayed, how do waiting, follow-up, or assumed financing terms affect an SME's cash balance and minimum cash buffer?

It models invoices, operating obligations, opening cash, a minimum cash buffer, payment timing, and assumed financing offers. It is a decision-support and research tool; it does not lend money, apply for financing, move money, or connect to TReDS or bank systems.

## Current implementation

- Typed Pydantic finance and simulation models.
- Seeded synthetic demo and benchmark scenario generation.
- Daily cash-flow simulator with financing advances, modeled interest/fees, reserve releases, and cash metrics.
- Six comparison policies: wait, largest-first, earliest-due-first, highest-delay-risk-first, cash-threshold, and optimizer.
- FastAPI health, demo-generation, and policy-comparison endpoints.
- Reproducible benchmarks, failure-case analysis, objective sensitivity experiments, and automated regression tests.
- A timestamp-aware historical-data contract with versioned invoices, payment event/record timestamps, obligation versions, cash-balance snapshots, and financing-offer history.
- A rolling-origin payment-timing backtest that filters features by the recorded-at cutoff and reports censored and late-recorded outcomes separately.

Expected payment timing now reflects the modeled late probability, and financing duration uses the same expected-day function. Cost-aware experiments expose a trade-off between financing cost and realized liquidity risk. All demo and benchmark scenarios are synthetic; they do not establish real-world performance.

The historical backtest validates payment timing only. Its first baseline uses fully settled historical invoices, so selection bias remains a limitation. It does not yet replay historical financing decisions or estimate counterfactual cash balances.

There is no web UI, spreadsheet upload/import adapter, database, or live financing integration yet. The JSON historical-data contract and CLI exist, but source-specific CSV/Excel/database ingestion has not been implemented. `FOLLOW_UP` and `FINANCE_OTHER` are represented in the domain and simulator, but the registered policies do not currently produce them.

## Run the prototype

Install the project and test dependencies:

    python -m pip install -e ".[test]"

Run the synthetic demo, benchmark, objective comparison, and tests:

    python experiments/run_mvp.py
    python experiments/run_benchmark.py --scenario-count 500 --seed 20260930
    python experiments/run_objective_comparison.py --scenario-count 500 --seed 20260930
    pytest -q

Run a historical timing backtest against an approved JSON extract that follows [Historical Data Contract v1](docs/historical-data-contract.md):

    python experiments/run_historical_backtest.py --data path/to/historical-data.json --origin-start 2025-01-31 --origin-end 2025-12-31 --frequency monthly

The extract must include an owner-approved event-time completeness watermark and timezone-aware event/record timestamps. Use real business dates and appropriate follow-up time. The prototype reports censored cases and receipts recorded after the actual cash date separately. Do not use synthetic fixtures to claim predictive accuracy.

Start the API locally with:

    uvicorn api.main:app --reload

Implemented routes:

| Route | Purpose |
|---|---|
| `GET /health` | Check service status. |
| `GET /generate-demo` | Get a reproducible synthetic demo scenario. |
| `POST /compare` | Submit a structured scenario and compare selected policies. |

The API does not accept file uploads. Its `/docs` page is generated API reference, not a product web interface.

## Repository guide

- `api/main.py` — FastAPI application and routes.
- `src/decision_lab/models.py` — domain and simulation result contracts.
- `src/decision_lab/data.py` — synthetic demo and benchmark generators.
- `src/decision_lab/behaviour.py` — payment-timing and risk heuristics.
- `src/decision_lab/policies.py` — baseline policies and liquidity-cost optimizer.
- `src/decision_lab/simulator.py` — financing calculations and daily cash ledger.
- `src/decision_lab/historical.py` — timestamp-aware historical data contract.
- `src/decision_lab/rolling_backtest.py` — leakage-aware rolling-origin baseline.
- `experiments/run_historical_backtest.py` — historical backtest CLI.
- `experiments/run_benchmark.py` — multi-scenario policy benchmark.
- `experiments/run_objective_comparison.py` — cost-aware objective sensitivity.
- `experiments/analyze_benchmark.py` — benchmark failure-case analysis.
- `tests/test_simulator.py` and `tests/test_historical_backtest.py` — finance invariants, schema validation, and leakage regression tests.
- `docs/` — architecture, product design, roadmap, calculation validation, and data contract.
- `research/` — problem statement, market scan, and research conclusions.

## Project documentation

- [System architecture and implementation status](docs/architecture.md)
- [Product design and proposed workflow](docs/product-design.md)
- [Project roadmap](docs/project-roadmap.md)
- [Calculation validation and benchmark findings](docs/calculation-validation-report.md)
- [Historical data contract and rolling backtest](docs/historical-data-contract.md)
- [Research conclusion](research/final-research-conclusion-2026-09-29.md)
- [Delayed-payment problem statement](research/problem-statement.md)

The original financial-forecast-reliability idea remains part of the project's research history, but it is not the active product direction. The project does not claim commercial novelty or validated performance on real SME portfolios.
