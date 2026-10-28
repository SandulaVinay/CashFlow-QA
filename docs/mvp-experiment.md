# MVP Experiment Specification

## Research question

Does a transparent liquidity-cost policy produce better outcomes than simple receivables-financing rules when payment timing is uncertain?

## Experimental setup

Each scenario contains:

- receivables;
- historical payment-behaviour summaries;
- future cash obligations;
- opening cash;
- minimum cash buffer;
- TReDS financing assumptions;
- a fixed random seed.

The same payment-delay realization is supplied to every policy in a comparison.

## Policies

- wait
- largest-first
- earliest-due-first
- highest-delay-risk-first
- cash-threshold
- liquidity-cost optimizer

## Primary metrics

1. Minimum cash
2. Cash-shortfall days
3. Financing cost
4. Amount of receivables accelerated
5. Number of financed invoices

## Fairness rules

- Policies cannot see realized future payment dates when selecting actions.
- Optimizer candidates are scored on the expected payment schedule.
- Actual realized payment timing is used only for final evaluation.
- The same realized payment path is used for all policies.
- Synthetic data is for engineering validation, not evidence of real-world prediction accuracy.

## Success gate

The optimizer moves forward to the web application only if repeated scenarios show a meaningful and stable trade-off improvement against simple baselines.

The exact threshold will be defined before the experiment campaign so the result is not selected after seeing the outcomes.

## Non-goals

- No live TReDS connection.
- No lender decisioning.
- No real financing transaction.
- No claim that synthetic experiments prove business performance.
