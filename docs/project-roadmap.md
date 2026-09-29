# Project Roadmap — MSME Receivables Decision Lab

## Phase 0 — Research ✅

- Problem definition
- Existing market scan
- Commercial/open-source research
- Gap validation
- Final project direction

## Phase 1 — Product design ✅

- User journey
- Domain model
- Simulation model
- Policy definitions
- UI information architecture
- MVP success criteria

## Phase 2 — MVP simulation engine 🔄

- Canonical Python models
- Synthetic dataset generator
- Daily cash simulator
- Payment-delay baseline
- Four benchmark policies
- First liquidity-cost optimizer
- Metrics
- Automated tests
- Reproducible experiment

### Exit gate

The optimizer must be benchmarked against simple baselines. If it does not produce a measurable advantage on realistic scenarios, revise or stop the optimization hypothesis.

## Phase 3 — API + web prototype

- FastAPI
- Scenario API
- React + Tailwind UI
- Receivables table
- Cash calendar
- Policy comparison
- Evidence view

## Phase 4 — Realistic datasets

- Public/reference data investigation
- Import contract
- Synthetic-data calibration
- Historical backtesting design
- Scenario library

## Phase 5 — Advanced payment timing

Only after baseline experiments: survival analysis, quantile/interval predictions, ML models, uncertainty calibration.

## Phase 6 — Advanced decision research

- optimization formulation
- sensitivity analysis
- portfolio constraints
- financing-source comparisons
- small-invoice aggregation as a scenario

## Phase 7 — AI explanation

- grounded explanation over verified outputs
- natural-language query
- traceability
- hallucination tests

## Phase 8 — Production hardening

- Docker Compose
- CI/CD
- security
- observability
- reproducibility test from clean environment
- documentation
- release

## Phase 9 — Research communication

- GitHub case study
- benchmark results
- LinkedIn build-in-public posts
- final technical write-up