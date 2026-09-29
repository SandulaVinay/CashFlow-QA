# System Architecture

## 1. Design principles

1. Deterministic finance calculations come before LLM explanations.
2. Every prediction must have an evaluation path.
3. The system should measure data sufficiency before high-confidence prediction.
4. Historical backtesting is mandatory for forecast claims.
5. Stress scenarios must be reproducible.
6. Every model output should have traceable source metrics.

## 2. Logical components

### Data ingestion
Accept CSV / Excel inputs and normalize them into a canonical finance schema.

### Data quality engine
Validate schema, completeness, duplicates, date integrity, amount integrity, historical depth, and leakage risk.

### Financial model
Normalize invoices, payments, payables and cash movements into a consistent analytical model.

### Forecasting engine
Start with transparent baselines. Add more advanced models only when experiments justify them.

### Backtesting engine
Simulate historical forecasting points and compare predictions against actual outcomes.

### Diagnostics engine
Measure accuracy, bias, horizon degradation and segment-level error.

### Stress engine
Apply explicit business shocks and recompute cash positions.

### Reliability engine
Combine data quality, validation performance, model stability and other measured signals into a transparent reliability assessment.

### AI explanation layer
Translate verified structured results into natural language. The LLM is not the source of truth for financial numbers.

## 3. Deployment target

Initial development: Docker Compose.

Possible production path:
- React frontend;
- FastAPI backend;
- PostgreSQL;
- object storage for uploaded files;
- background job worker for larger analyses;
- model artifact storage;
- CI/CD through GitHub Actions.
