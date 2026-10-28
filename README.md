# MSME Receivables Decision Lab

This repository is historically named **CashFlow-QA**. Its active project is the MSME Receivables Decision Lab, a research-grade simulator for comparing receivables decisions under cash-flow constraints.

## What the project does

The project helps answer:

> When customer payments may be delayed, how do waiting, follow-up, or assumed financing terms affect an SME's cash balance and minimum cash buffer?

It models invoices, operating obligations, opening cash, a minimum cash buffer, payment timing, and assumed financing offers. It compares policy outputs such as daily cash, minimum cash, shortfall days, and financing cost. It is a decision-support and research tool; it does not lend money, apply for financing, move money, or connect to TReDS or bank systems.

The [end-to-end architecture](docs/architecture.md) explains the purpose, Mermaid diagrams, workflow, data flow, component behavior, stakeholder value, and which features are implemented, in progress, or planned.

## Current implementation

- Typed Pydantic finance and simulation models.
- Seeded synthetic demo and benchmark scenario generation.
- Heuristic payment timing and risk score, plus reproducible synthetic payment realizations.
- Daily cash-flow simulator with financing advances, modeled interest and fees, reserve releases, and cash metrics.
- Shortfall severity metric that sums the daily gap below the configured cash buffer (INR-days).
- Six comparison policies: wait, largest-first, earliest-due-first, highest-delay-risk-first, cash-threshold, and optimizer.
- FastAPI endpoints for health, demo generation, and policy comparison.
- Reproducible experiment scripts, benchmark artifacts, failure-case analysis, regression tests, and GitHub Actions CI.

Expected payment timing now accounts for the modeled late probability, and financing duration uses that same expected-day function. A follow-up objective comparison adds cost-minimizing policies under several expected cash-buffer risk limits. The results show a cost-versus-realized-liquidity trade-off and do not select one risk limit as universally correct. All scenarios and payment behavior are synthetic; results do not establish real-world performance. See the [calculation validation report](docs/calculation-validation-report.md) for findings and artifacts.

There is no web UI, spreadsheet upload/import, database, historical customer dataset loader, or live financing integration in the current implementation. `FOLLOW_UP` and `FINANCE_OTHER` are represented in the domain and simulator, but the registered policies do not currently produce them.

## Run the prototype

From the repository root, install the package and test dependencies:

```powershell
python -m pip install -e ".[test]"
```

Run a one-scenario seed-42 demo comparison or the default 500-scenario synthetic benchmark:

```powershell
python experiments/run_mvp.py
python experiments/run_benchmark.py --scenario-count 500 --seed 20260930
python experiments/run_objective_comparison.py --scenario-count 500 --seed 20260930
```

The scripts write JSON and/or Markdown artifacts to `reports/`; benchmark and analysis outputs are timestamped. To start the API locally:

```powershell
uvicorn api.main:app --reload
```

Implemented routes:

| Route | Purpose |
|---|---|
| `GET /health` | Check service status. |
| `GET /generate-demo` | Get a reproducible synthetic demo scenario. |
| `POST /compare` | Submit a structured scenario and compare selected policies. |

The API expects JSON records that match the contracts in `docs/architecture.md`; it does not accept file uploads. Its `/docs` page is generated API reference, not a product web interface.

## Repository guide

```text
api/main.py                     FastAPI application and routes
src/decision_lab/models.py      Domain and result contracts
src/decision_lab/data.py        Synthetic demo and benchmark generators
src/decision_lab/behaviour.py   Payment timing and risk heuristics
src/decision_lab/policies.py    Policy rules and liquidity-cost optimizer
src/decision_lab/objective_variants.py Cost-guarded liquidity objective variants
src/decision_lab/engine.py      Shared-path policy comparison
src/decision_lab/simulator.py   Financing calculations and daily cash ledger
experiments/run_mvp.py          Reproducible demo experiment
experiments/run_benchmark.py    Multi-scenario policy benchmark
experiments/run_objective_comparison.py Cost-aware objective sensitivity campaign
experiments/analyze_benchmark.py Failure-case and timing analysis
reports/                        Generated experiment artifacts
tests/test_simulator.py         Financial invariants and regression tests
docs/                            Architecture, product design, roadmap, validation
research/                        Problem definition and market research
```

## Project documentation

- [System architecture and implementation status](docs/architecture.md)
- [Product design and proposed workflow](docs/product-design.md)
- [Project roadmap](docs/project-roadmap.md)
- [Calculation validation and benchmark findings](docs/calculation-validation-report.md)
- [Research conclusion](research/final-research-conclusion-2026-09-29.md)
- [Delayed-payment problem statement](research/problem-statement.md)

The original financial-forecast-reliability idea remains part of the project's research history, but it is not the active product direction. The project does not claim to be the first TReDS optimizer or to have validated performance on real SME portfolios.
