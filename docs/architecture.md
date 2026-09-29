# System Architecture — MSME Receivables Decision Lab

## 1. Design principles

1. Deterministic financial calculations come before AI.
2. Every simulation must be reproducible from explicit inputs and a random seed.
3. All policy decisions must be explainable from measurable inputs.
4. No live financing transaction is performed by the prototype.
5. Prediction uncertainty must be visible.
6. Historical/synthetic evaluation is required before making performance claims.
7. The same scenario must be replayable for policy comparison.

## 2. Logical architecture

~~~text
                     Web / API Client
                           |
                           v
                    FastAPI Application
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
   Data Validation                    Simulation API
          |                                 |
          v                                 v
 Canonical Finance Model         Decision / Policy Engine
          |                                 |
          |                    +------------+-------------+
          |                    |            |             |
          v                    v            v             v
 Receivables Behaviour     WAIT       FOLLOW-UP       FINANCE
       Model                                  \\       /      \\
          |                                    \\     /        \\
          +-------------------------------------\\---/---------+
                                                 \\
                                                  v
                                           Cash Simulator
                                                  |
                                                  v
                                         Policy Metrics
                                                  |
                                  +---------------+---------------+
                                  |                               |
                                  v                               v
                          Experiment Runner               Evidence Report
~~~

## 3. Modules

### `decision_lab.models`

Typed domain models for invoices, obligations, financing offers, scenarios, actions, daily cash positions, and policy results.

### `decision_lab.simulator`

Pure deterministic cash-flow simulation.

### `decision_lab.behaviour`

Payment timing estimation from historical invoice behaviour.

### `decision_lab.policies`

Decision policies: largest-first, earliest-due-first, highest-risk-first, cash-threshold, optimizer.

### `decision_lab.metrics`

Common evaluation metrics.

### `decision_lab.data`

Synthetic/reference data generation and CSV loading.

### `api`

FastAPI endpoints for health, scenario simulation, policy comparison and demo generation.

### `experiments`

Reproducible experiments and benchmark reports.

## 4. Canonical data contracts

### Invoice

invoice_id, buyer_id, invoice_date, due_date, amount, historical_avg_delay_days, historical_delay_std_days, historical_late_rate, eligible_for_treds.

### Obligation

date, category, amount.

### FinancingOffer

source, annual_rate, fee_rate, advance_rate, max_amount.

### Scenario

opening_cash, minimum_cash_buffer, horizon_days, payment_delay_shock, follow_up_acceleration_days, financing_offers, seed.

## 5. API design

### `GET /health`

Returns service health.

### `POST /simulate`

Runs one policy against one scenario.

### `POST /compare`

Runs multiple policies against the same scenario.

### `POST /generate-demo`

Returns a reproducible demo dataset and scenario.

Later: `POST /upload`, `POST /validate`, `POST /experiments/run`.

## 6. Reproducibility

Every experiment receives a dataset version, scenario parameters, policy name, algorithm version, and random seed. The output should include these identifiers.

## 7. Future production architecture

The MVP stays intentionally simple. A later deployment may add React + Tailwind, PostgreSQL, background jobs, object storage, experiment/model artifacts, CI/CD and audit logs.

No component should be introduced before its need is demonstrated.