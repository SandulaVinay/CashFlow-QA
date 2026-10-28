# Product Design — MSME Receivables Decision Lab

## 1. Product goal

Build a self-hosted, reproducible decision-support application for Indian MSMEs that answers:

> **When receivables may be delayed, what action best protects the business's minimum cash position at the lowest reasonable cost?**

The first release is an experiment platform, not a production lending system.

## 2. Primary user

### MSME owner / finance manager

The user is responsible for receivables, collections, cash planning, supplier/payroll/tax/loan obligations, and working-capital decisions.

## 3. Core user journey

~~~text
Upload data
    ↓
Validate data
    ↓
Build receivables + cash schedule
    ↓
Estimate payment timing
    ↓
Define minimum cash buffer
    ↓
Choose financing assumptions
    ↓
Run counterfactual simulation
    ↓
Compare policies/actions
    ↓
Review cash-flow impact
    ↓
Inspect evidence + assumptions
~~~

## 4. Inputs

### Receivables

Required: invoice_id, buyer_id, invoice_date, due_date, amount, actual_payment_date (historical rows only).

Derived: days_to_due, historical_average_delay, historical_delay_std, delay_probability/risk score, expected_payment_date, payment-confidence indicator.

### Cash obligations

Required: date, category, amount.

Typical categories: payroll, supplier payments, tax, rent, loan/EMI, operating expenses.

### Cash position

- opening_cash
- minimum_cash_buffer

### Financing assumptions

For each source: source_name, annual_rate, fee_rate, advance_rate, maximum_available_amount.

Initial sources: TReDS and OD / working-capital line.

These are scenario inputs. They are not live rates.

## 5. Decision actions

### WAIT

Do nothing. Cash arrives according to the selected payment scenario.

### FOLLOW_UP

Assume a user-configurable acceleration effect on collection, subject to an uncertainty range.

### TReDS

Finance an eligible receivable immediately for an assumed advance percentage.

Cost = financed_amount × annual_rate × days_outstanding / 365 + fees.

### OTHER_FINANCING

Model a generic working-capital facility with configurable rate/fee assumptions.

## 6. Cash-flow simulation model

The MVP uses a daily 13-week horizon (91 days).

~~~text
closing_cash[t] =
    opening_cash[t]
  + collections[t]
  + financing_inflows[t]
  - obligations[t]
  - financing_costs[t]
~~~

Key outputs: minimum cash, cash-shortfall days, maximum cash, ending cash, financing cost, amount of receivables accelerated, number/value of invoices financed, and number/value of invoices followed up.

## 7. Payment-delay model

For the MVP, do not train an ML model.

Use a transparent behavioural model based on historical buyer payment performance: expected delay from mean/median delay, plus a risk score based on delay frequency, variance and history length.

Later experiments can compare mean delay, median delay, quantile models, survival analysis, gradient boosting and probabilistic models.

## 8. Decision policies

### Baseline A — Largest invoice first

Finance largest eligible receivables until the cash requirement is covered.

### Baseline B — Earliest due first

Prioritize receivables with the earliest due dates.

### Baseline C — Highest delay risk

Prioritize invoices with the greatest estimated delay risk.

### Baseline D — Cash-threshold rule

Only act when projected cash falls below the minimum buffer.

### Candidate policy — Liquidity-cost optimizer

Select actions to minimize financing cost + liquidity-shortfall penalty + unnecessary-financing penalty + action/collection cost, subject to the minimum-cash constraint where possible.

The optimizer must show the objective values and constraints it used.

## 9. Counterfactual comparison

Every policy produces the same scenario metrics:

| Policy | Min cash | Shortfall days | Financing cost | Receivables accelerated |
|---|---:|---:|---:|---:|
| Wait | calculated | calculated | calculated | calculated |
| Largest first | calculated | calculated | calculated | calculated |
| Highest-risk first | calculated | calculated | calculated | calculated |
| Optimizer | calculated | calculated | calculated | calculated |

## 10. UI design

### Screen 1 — Overview

Current cash, minimum buffer, receivables, projected cash-gap date, top receivables needing attention, latest simulation result.

### Screen 2 — Receivables

Table of invoice, buyer, amount, due date, expected payment, delay risk, days overdue, and available action.

### Screen 3 — Cash calendar

Daily/weekly cash curve showing opening cash, expected collections, obligations, minimum cash line, and simulated cash balance.

### Screen 4 — Decision lab

User selects scenario, financing assumptions, minimum buffer, and policy, then runs simulation.

### Screen 5 — Policy comparison

Compare policies on minimum cash, shortfall days, financing cost, accelerated receivables, and number of actions.

### Screen 6 — Decision evidence

For each selected action show what was selected, why it was selected, assumptions, source metrics, counterfactual alternatives, and confidence/data-sufficiency.

## 11. AI scope

AI is not part of MVP decision logic. Later it may explain simulation results, answer questions over verified outputs, and summarize assumptions/failure modes.

The LLM must not create financial values that do not exist in the simulation output.

## 12. MVP boundaries

Exclude live TReDS APIs, live financing applications, bank-account connections, payment initiation, authentication/authorization, multi-tenant production infrastructure, LLM integration, and real lender credit decisions.

## 13. MVP success criteria

1. The same dataset produces the same result reproducibly.
2. At least four baseline policies run successfully.
3. A candidate optimizer can be compared against those baselines.
4. Results include minimum cash, shortfall days and financing cost.
5. The experiment identifies cases where different policies produce materially different outcomes.
6. Tests cover core financial invariants.

This is the first research gate before building the full web application.