# CashFlow QA

## Financial Forecast Reliability & Stress Testing Engine

> **Note:** The original CashFlow-QA hypothesis is retained as research history. The active project direction is now the MSME Receivables Decision Lab described below.

## Current project direction — 2026-09-29

The original **Financial Forecast Reliability & Stress Testing** thesis has been superseded by research.

### Current research project

**MSME Receivables Decision Lab**

The active MVP is a research-grade simulator for comparing receivables actions under future cash-flow constraints:

- waiting for payment;
- collection/follow-up actions;
- TReDS financing; and
- alternative working-capital financing

against future cash requirements and a minimum liquidity buffer.

This is **not** a new TReDS marketplace, lender, invoice-financing platform, or generic working-capital optimizer. Existing commercial products already cover substantial parts of those categories.

The research goal is to measure which decision policy actually reduces liquidity shortfalls and financing cost under realistic payment-delay uncertainty.

Design and implementation references:

- [Product design](docs/product-design.md)
- [System architecture](docs/architecture.md)
- [Project roadmap](docs/project-roadmap.md)

See:

- [Final research conclusion](research/final-research-conclusion-2026-09-29.md)
- [Deep research on the three candidate gaps](research/deep-dive-narrow-msme-gaps-2026-09-29.md)
- [Financing decision market scan](research/financing-decision-market-scan-2026-09-29.md)
- [MSME delayed-payment problem statement](research/problem-statement.md)

---


CashFlow QA is an open-source finance analytics project designed to answer a question that ordinary cash-flow dashboards do not answer well:

> **Can a business trust its cash-flow forecast, why might the forecast be wrong, and what happens when realistic financial risks occur?**

The project is intentionally being built as a **research-first, production-oriented application** rather than as a simple dashboard or chatbot.

---

## Why this project exists

Cash-flow forecasting is already a mature software category. Businesses can buy tools that forecast collections, payments and future cash balances.

Our project does **not** aim to recreate another forecasting dashboard.

Instead, CashFlow QA investigates the reliability layer around financial forecasts:

- Is the underlying financial data good enough for forecasting?
- Does the forecast work on this company's historical behaviour?
- Is the forecast systematically optimistic or pessimistic?
- At what forecast horizon does accuracy deteriorate?
- What business behaviours cause forecast errors?
- How sensitive is the forecast to realistic financial shocks?
- Which forecasting approach is most appropriate for this business?
- When should the system refuse to provide a high-confidence prediction?

The goal is to turn forecasting from a black-box number into an **auditable financial decision-support process**.

---

## Core problem statement

A cash-flow forecast can look precise while still being systematically wrong because of:

- poor or incomplete financial data;
- incorrect assumptions about payment timing;
- customer or supplier behaviour changing over time;
- seasonality and structural changes;
- forecast bias;
- insufficient historical observations;
- data leakage during model development; and
- model performance degrading as the forecast horizon increases.

CashFlow QA will independently evaluate these factors before presenting a business with a confidence level for its forecast.

---

## Proposed solution

The system will accept historical finance data such as:

- customer invoices / accounts receivable;
- customer payments;
- vendor bills / accounts payable;
- vendor payments;
- bank or cash transactions; and
- an optional existing company forecast.

The pipeline will then:

1. Validate and normalize the data.
2. Calculate core financial metrics.
3. Build multiple forecasting baselines/models.
4. Backtest them against historical periods.
5. Measure accuracy, bias and deterioration over time.
6. Diagnose the major sources of forecast error.
7. Stress-test the forecast under realistic scenarios.
8. Produce a forecast reliability assessment.
9. Expose the results through an application and reports.
10. Add an AI explanation layer that explains measured results rather than inventing financial figures.

---

## What the application should answer

### Forecast

- How much cash is expected in 30 / 60 / 90 days?
- When could the business fall below its minimum cash threshold?
- What is the expected range of future cash balances?

### Reliability

- How accurate is the forecast historically?
- How does accuracy change with forecast horizon?
- Is the business systematically over-forecasting collections or under-forecasting outflows?

### Diagnosis

- Why did previous forecasts miss?
- Which customers, suppliers or transaction types contribute most to forecast error?
- Is the problem data quality, behaviour change, seasonality, or model weakness?

### Stress testing

- What happens if a major customer pays 30 days late?
- What happens if receivables are 15% lower than expected?
- What happens if supplier outflows rise by 10%?
- What happens if operating expenses increase unexpectedly?

### Model selection

- Which forecasting method works best for this company?
- Is the available history sufficient for customer-level modelling?
- When is the model too uncertain to be trusted?

---

## What makes this different from a normal AI finance project

This project will be evaluated on evidence, not on UI appearance.

### We will NOT claim

> "Our AI works for every company."

### We WILL measure

- performance on reference datasets;
- performance on unseen data;
- performance under synthetic edge cases;
- data sufficiency requirements;
- forecast bias;
- uncertainty / confidence;
- model failure modes; and
- reproducibility from a clean environment.

The application should be able to say **"insufficient evidence"** instead of producing a misleading prediction.

---

## Research-first approach

Before implementing major features, we will review:

- academic research;
- existing open-source projects;
- commercial products;
- available datasets; and
- documented limitations and failure cases.

The repository will preserve this research so that the final product shows:

**Problem → Existing solutions → Gap → Hypothesis → Baseline → Implementation → Evaluation → Failure analysis → Improvements**

---

## Initial architecture

```text
User / Finance Team
        |
        v
React Web Application
        |
        v
FastAPI Backend
        |
        +-------------------------+
        |                         |
        v                         v
Data Ingestion               Analysis APIs
        |                         |
        v                         v
Data Quality Engine       Forecasting Engines
        |                         |
        +-------------+-----------+
                      |
                      v
             Canonical Finance Model
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      Backtesting  Stress Test  Diagnostics
          |           |           |
          +-----------+-----------+
                      |
                      v
              Reliability Engine
                      |
          +-----------+-----------+
          |                       |
          v                       v
    Dashboard / Reports      AI Explanation Layer
```

### Planned technology stack

| Layer | Initial choice |
|---|---|
| Frontend | React + Tailwind CSS |
| API | Python + FastAPI |
| Data processing | pandas / NumPy |
| Database | PostgreSQL |
| ML | scikit-learn / XGBoost |
| BI | Power BI for analytical reporting where useful |
| Testing | pytest + data validation tests |
| Packaging | Docker |
| CI/CD | GitHub Actions |
| AI | LLM API for explanation / Q&A over verified results |

These are working choices and may change after implementation evidence.

---

## V1 scope

The first production-oriented milestone is intentionally narrow:

### V1 — Forecast Validation Core

- CSV / Excel ingestion;
- standard data contract;
- schema and data-quality validation;
- basic AR/AP cash-flow model;
- one transparent baseline forecast;
- historical backtesting;
- MAE / RMSE / WAPE where appropriate;
- forecast bias measurement;
- reliability report;
- reproducible test dataset.

We will add ML, stress testing, decision support and AI explanation only after V1 has measurable evidence.

---

## Repository structure

```text
cashflow-qa/
├── README.md
├── docs/
│   ├── architecture.md
│   └── project-roadmap.md
├── research/
│   ├── problem-statement.md
│   ├── existing-solutions.md
│   └── research-log.md
├── src/
├── tests/
├── data/
│   ├── sample/
│   └── synthetic/
└── .gitignore
```

---

## Reproducibility goal

A new user should eventually be able to:

```bash
git clone <repository>
cd cashflow-qa
docker compose up
```

Then upload a dataset conforming to the documented data contract and independently reproduce the evaluation.

No private company data will be required for the public reference implementation.

---

## Project status

**Current stage: Research decision complete — prototype experiment pending**

The active direction is the **MSME Receivables Decision Lab**. No performance claims have been made yet.

Metrics, model selection, benchmark datasets and final product scope will be established through experiments and documented in this repository.

---

## Research principle

We will not treat an existing project as something to copy.

We will study existing solutions to understand:

- what is already solved;
- which assumptions they make;
- where they fail;
- what evidence supports them; and
- where a meaningful, testable improvement may exist.

If research shows that a proposed feature is already adequately solved, we will document that finding and reconsider the scope rather than pretending it is novel.

---

## License

TBD after the project architecture and dependencies are finalized.
