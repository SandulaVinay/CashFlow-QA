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

## Phase 2 — MVP simulation engine ✅ implementation complete; research gate open

- Canonical Python models
- Synthetic dataset generator
- Daily cash simulator
- Payment-delay baseline
- Six comparison policies
- Cash-flow metrics and daily cash curve
- Automated regression tests
- Reproducible single-scenario experiment
- 500-scenario synthetic benchmark and failure-case analysis
- Cost-aware objective comparison using expected cash-buffer deficit amount-days

The implemented optimizer has been benchmarked against simple baselines on synthetic scenarios. Expected timing reflects the modeled late probability, and financing cost uses the same expected timing. On the timing-aligned 500-seed run, the optimizer had more realized shortfall days than the best baseline in 24 cases, while cases where it cost more than a comparable baseline fell to 60. The research gate remains open to reassess the objective and liquidity/cost trade-off. These results are not evidence of performance on real SMEs.

## Phase 3 — API + web prototype 🔄 API implemented; web UI planned

- FastAPI health, demo-generation, and policy-comparison routes are implemented.
- A structured scenario API is implemented; file upload/import is not.
- React + Tailwind UI is planned.
- Receivables table, cash calendar, policy comparison screen, and evidence view are planned.

## Phase 4 — Realistic datasets 🔄 contract and first backtest baseline implemented

- Timestamp-aware historical-data contract: invoices, partial payments, obligation versions, cash-balance snapshots, and financing-offer history.
- Event-time vs recorded-time separation and a source completeness watermark.
- Rolling-origin payment-timing backtest with buyer median, global median, and cold-start baselines.
- Censored receivables and payments settled before a cutoff but recorded later are reported separately.
- Comparison against a due-date-only baseline with MAE, median absolute error, amount-weighted MAE, signed error, and Brier score.

### Exit gate

The prototype has a contract and unit-tested backtest on synthetic fixtures; no real historical dataset has been loaded or validated yet. The initial training set uses only fully settled receivables known by each cutoff, which can introduce selection bias. Before using results for decisions, connect a source-owned extract, validate the watermark and event recording semantics, inspect partial settlements and credit notes, and consider survival analysis for censored invoices. Full daily cash-ledger reconciliation and actual historical policy replay are still pending.

## Phase 5 — Advanced payment timing

Only after baseline experiments: survival analysis, quantile/interval predictions, ML models, uncertainty calibration.

## Phase 6 — Advanced decision research

- Optimization formulation
- Sensitivity analysis
- Portfolio constraints
- Financing-source comparisons
- Small-invoice aggregation as a scenario

## Phase 7 — AI explanation

- Grounded explanation over verified outputs
- Natural-language query
- Traceability
- Hallucination tests

## Phase 8 — Production hardening

- Docker Compose
- CI/CD
- Security
- Observability
- Reproducibility test from clean environment
- Documentation
- Release

## Phase 9 — Research communication

- GitHub case study
- Benchmark results
- LinkedIn build-in-public posts
- Final technical write-up
