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

The implemented optimizer has been benchmarked against simple baselines on synthetic scenarios. Expected timing reflects the modeled late probability, and financing cost uses the same expected timing. On the timing-aligned 500-seed run, the optimizer had more realized shortfall days than the best baseline in 24 cases, while cases where it cost more than a comparable baseline fell to 60. These results are not evidence of performance on real SMEs.

## Phase 3 — API + web prototype 🔄 API implemented; web UI planned

- FastAPI health, demo-generation, and policy-comparison routes are implemented.
- A structured scenario API is implemented; file upload/import is not.
- React + Tailwind UI is planned.
- Receivables table, cash calendar, policy comparison screen, and evidence view are planned.

## Phase 4 — Realistic datasets 🔄 initial public dataset and modeling pipeline added

- Timestamp-aware historical-data contract: invoices, partial payments, obligation versions, cash-balance snapshots, and financing-offer history.
- Event time vs recorded time and source completeness watermark.
- Rolling-origin payment-timing backtest that reports censored receivables and late-recorded payments separately.
- Public IBM Finance Factoring late-payment CSV inspected: 2,466 invoice rows and 100 pseudonymous customer IDs.
- Deterministic training script added for a late-payment classifier and days-late regressor using a chronological split.
- Post-outcome/ambiguous columns (`SettledDate`, `DaysToSettle`, `DaysLate`, `Disputed`, `PaperlessDate`, `PaperlessBill`) excluded from predictor features.
- Source CSV is not committed; the training report records its SHA-256.

### Current public-data limitation

The inspected CSV copy contains only settled invoices and no record-time timestamps, partial receipt ledger, cash balances, obligations, or financing offers. The amount range and fixed 30-day terms are constrained, and real-world provenance/license conditions have not been independently verified. An exploratory chronological holdout showed promise for the late classifier and a marginal improvement for days-late regression, but those metrics must be reproduced from the exact downloadable file before publication. This dataset validates pipeline shape, not liquidity-policy performance.

### Exit gate

Before using a model for decisions, obtain owner-approved company histories with event timestamps and record-availability timestamps; validate partial settlements, credit notes, disputes, amendments and open-invoice censoring; then replay multiple rolling origins. The current settlement-history feature assumes a receipt becomes observable on its settlement date because the sample source lacks `recorded_at`. Full daily cash-ledger reconciliation and policy replay are still pending.

## Phase 5 — Advanced payment timing

After validating the data contract and rolling baselines:
- Compare global/customer history heuristics with simple statistical baselines.
- Address open invoices and censoring; evaluate survival/time-to-event methods if appropriate.
- Evaluate uncertainty intervals and calibration.
- Only then compare more complex ML models under the same temporal splits.

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

- CSV/Excel/database adapters with source data validation
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
