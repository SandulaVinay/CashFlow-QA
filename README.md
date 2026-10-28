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
- Reproducible benchmarks, failure-case analysis, objective sensitivity experiments, and regression tests.
- Timestamp-aware historical-data contract and rolling-origin payment-timing backtest.
- A reproducible invoice-lateness classifier and days-late regressor using a chronological holdout.

The first public invoice data experiment uses the educational IBM Finance Factoring late-payment history listing. It has 2,466 invoice rows, 100 anonymized customer IDs and settlement outcomes, but it has no open invoices, cash balances, partial-payment history, record-time timestamps, obligations or financing offers. Treat it as a learning benchmark only; the data's provenance and redistribution terms have not been independently verified. The raw file is not included in the repository. Details and exploratory metrics are in [Public Invoice Data Experiment](docs/public-invoice-data-experiment.md).

The first exploratory classifier achieved ROC-AUC 0.854 on a chronological holdout; a days-late regressor achieved 2.19 days MAE versus a 2.29-day median baseline. These figures require reproduction from the exact downloaded CSV before publication and are not evidence of real-world generalization. The model excludes post-outcome columns and only uses prior invoices settled by each prediction date, but it assumes settlement information became observable on the settlement date because the source lacks recorded-at timestamps.

The historical backtest validates payment timing only. It does not yet replay historical financing decisions or estimate counterfactual cash balances. The JSON contract and rolling-origin CLI exist, but source-specific CSV/Excel/database ingestion adapters, full cash-ledger reconciliation and production UI are still future work.

## Run the prototype

Install the project and test dependencies:

    python -m pip install -e ".[test]"

Run the synthetic demo, benchmark, objective comparison and tests:

    python experiments/run_mvp.py
    python experiments/run_benchmark.py --scenario-count 500 --seed 20260930
    python experiments/run_objective_comparison.py --scenario-count 500 --seed 20260930
    pytest -q

Download the IBM Finance Factoring CSV from the [original Kaggle dataset page](https://www.kaggle.com/datasets/hhenry/finance-factoring-ibm-late-payment-histories), check its license/terms, and keep the raw file outside Git. Train the baseline and save a timestamped evaluation report plus model artifact:

    python experiments/train_payment_baseline.py --data path/to/Finance-Factoring-IBM-Late-Payment-Histories.csv

The script uses a chronological split and writes the source file's SHA-256 to the report for traceability. It deliberately excludes `SettledDate`, `DaysToSettle`, `DaysLate`, `Disputed`, `PaperlessDate`, and `PaperlessBill` from predictor features because they are outcomes or their historical availability cannot be established. More details: [Public Invoice Data Experiment](docs/public-invoice-data-experiment.md).

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
- `src/decision_lab/rolling_backtest.py` — leakage-aware rolling-origin backtest.
- `experiments/train_payment_baseline.py` — chronological invoice-payment model training.
- `experiments/run_historical_backtest.py` — historical backtest CLI.
- `experiments/run_benchmark.py` — multi-scenario policy benchmark.
- `experiments/run_objective_comparison.py` — cost-aware objective sensitivity.
- `experiments/analyze_benchmark.py` — benchmark failure-case analysis.
- `tests/test_simulator.py`, `tests/test_historical_backtest.py`, and `tests/test_payment_training.py` — finance, schema, leakage, and model-training tests.
- `docs/` — architecture, product design, roadmap, calculation validation and data documentation.
- `research/` — problem statement, market scan, and research conclusions.

## Project documentation

- [System architecture and implementation status](docs/architecture.md)
- [Product design and proposed workflow](docs/product-design.md)
- [Project roadmap](docs/project-roadmap.md)
- [Calculation validation and benchmark findings](docs/calculation-validation-report.md)
- [Historical data contract and rolling backtest](docs/historical-data-contract.md)
- [Public invoice dataset experiment and model metrics](docs/public-invoice-data-experiment.md)
- [Research conclusion](research/final-research-conclusion-2026-09-29.md)
- [Delayed-payment problem statement](research/problem-statement.md)

The original financial-forecast-reliability idea remains part of the project's research history, but it is not the active product direction. The project does not claim commercial novelty or validated performance on real SME portfolios.
