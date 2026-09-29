# Research Market Scan — 2026-09-29

## Status

**Result: Current hypothesis is not sufficiently differentiated yet.**

The initial project hypothesis was:

> Build a vendor-agnostic financial forecast reliability and stress-testing engine.

The research below shows that several commercial products and public research projects already cover substantial portions of this concept. Therefore we will not claim novelty or start full implementation until a narrower gap is validated.

---

## 1. Existing commercial capability

### Oracle Predictive Cash Forecasting

Oracle provides rolling cash forecasting for short and medium horizons, integrates AR/AP/Cash Management, supports multiple forecasting methods, scenario planning, variance analysis and transaction drill-through. It also supports ML-based receivables payment forecasting.

Source: https://docs.oracle.com/en/cloud/saas/financials/26b/fappp/overview-of-predictive-cash-forecasting.html

### Fathom

Fathom provides forecast audit capabilities covering P&L, balance sheet, cash flow statement, microforecasts and driver values. Its audit workflow is explicitly designed to inspect how forecast numbers are produced.

Sources:
- https://support.fathomhq.com/en/articles/4616520-audit-your-forecast
- https://www.fathomhq.com/blog/cash-flow-forecasting-audit-knowing-your-numbers

### Float

Float provides actual-vs-forecast tracking, cash-flow forecasting, AR/AP visibility, early warnings, and what-if scenario planning.

Source: https://floatapp.com/quickbooks-cash-flow-forecast

### Transformance CashPulse

CashPulse advertises per-horizon accuracy, forecast bias, per-customer hit rate, confidence ranges, automated retraining and scenario-based cash curves.

Source: https://www.transformance.ai/solutions/cash-flow-forecasting

### DecisionLedger AI

DecisionLedger advertises forecast-bias monitoring, cash runway forecasting, stress testing, Monte Carlo confidence intervals and forecast-accuracy tracking.

Source: https://decisionledgerai.com/solutions/finance

### Forecast audit services / products

RoadMap Technologies offers a forecast-audit process covering accuracy, bias and stability and produces a forecast-health scorecard and action plan.

Source: https://roadmap-tech.com/forecast-audit/

### Additional products found

Other products reviewed include CashAnalytics, DualEntry, Akili Edge, CFO Radar, Dryrun, Clockwork, Flowtaris and Predict.ai. Their public descriptions show substantial overlap in forecasting, scenario analysis, variance analysis, cash-risk detection and AI explanations.

---

## 2. Existing academic / open-source capability

### Corporate cash-flow forecast debiasing

A peer-reviewed study using forecasts from 34 subsidiaries of a multinational corporation found systematic forecast bias and showed that statistical debiasing can materially improve forecast accuracy.

Source:
https://www.sciencedirect.com/science/article/abs/pii/S0377221714010534

### 2025 SME cash-flow prediction deployment

A 2025 paper describes a deployed SME financial-management system combining invoice payment prediction and cash-flow forecasting, including handling of incomplete/limited historical data.

Source:
https://arxiv.org/abs/2511.03631

### 2026 authentic-data cash-flow forecasting research

A 2026 study evaluates corporate cash-flow forecasting using authentic SEC-reported data, pseudo-real-time evaluation and regime-aware models, and explicitly studies optimistic bias introduced by estimated data.

Source:
https://www.mdpi.com/1911-8074/19/5/333

### Public model-selection research

The public repository aliNzLami/cashFlow-forecasting-ML reports leakage-free time-series evaluation, model selection, external validation and interpretability across multiple datasets.

Source:
https://github.com/aliNzLami/cashFlow-forecasting-ML

### Earlier invoice-payment prediction reference

The public repository arthurflor23/invoice-payment-prediction provides multi-stage invoice late-payment classification and days-late regression with historical customer behaviour features.

Source:
https://github.com/arthurflor23/invoice-payment-prediction

---

## 3. What this means

The following ideas are already sufficiently covered that we should NOT make them our main claimed contribution:

- generic cash-flow forecasting;
- forecast-vs-actual variance tracking;
- forecast bias monitoring;
- forecast audit;
- basic stress testing;
- confidence ranges;
- AR payment prediction;
- automatic model selection;
- AI explanations of financial forecasts.

---

## 4. Potential remaining gap to investigate

A possible research direction remains:

> An open, vendor-neutral, reproducible financial forecasting challenge framework that can take a company's existing forecast or raw finance history, benchmark multiple forecasting approaches using leakage-safe rolling backtests, quantify uncertainty and bias, stress-test the forecast, and produce a machine-readable evidence package that another analyst can independently reproduce.

Important: this is only a candidate gap, not a novelty claim.

The next research round must test whether a product already offers this exact end-to-end workflow for SMEs / finance teams.

---

## 5. Why this is still potentially valuable

If the exact workflow is not already available as an accessible product, the project could demonstrate:

- finance domain understanding;
- time-series methodology;
- leakage-safe evaluation;
- model comparison;
- data engineering;
- reproducibility;
- model governance;
- explainable AI;
- production engineering.

The project would be positioned as forecast verification / benchmarking infrastructure, not as another forecasting engine.

---

## 6. Decision rule

We will only proceed to production implementation if the next research round can establish all of the following:

1. A specific user has a recurring, expensive problem.
2. Existing products solve adjacent pieces but not the complete proposed workflow.
3. Public research does not already provide an end-to-end implementation that makes the proposed contribution trivial.
4. We can obtain or construct multiple independent evaluation datasets.
5. We can define measurable success criteria.
6. The resulting system can be reproduced by another user.

Otherwise, we will pivot to another finance problem while retaining this research as a documented learning outcome.
