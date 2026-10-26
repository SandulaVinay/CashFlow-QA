# Calculation Validation Report — MVP

## Scope and status

This report records deterministic checks for the MSME Receivables Decision Lab snapshot. Demo inputs, payment timing, and financing offers are synthetic engineering assumptions. No results below establish real-world forecast accuracy or financing performance.

The project has a daily cash roll-forward, shared payment realizations for policy comparison, a transparent expected-payment baseline, and regression tests. A local validation run before the historical-data work began passed all 16 tests in the simulation suite.

## Hand-calculated cases

| Case | Hand calculation | Expected result |
|---|---|---:|
| Pure collection | Opening cash ₹1,000 + ₹200 collection | Ending ₹1,200; minimum ₹1,000 |
| Pure obligation | Opening cash ₹1,000 − ₹200 obligation | Ending ₹800; minimum ₹800 |
| Wait | ₹1,000 opening − ₹300 obligation + ₹600 collection | ₹700 after the obligation; ₹1,300 after collection |
| Financing reserve | ₹10,00,000 invoice; 98% advance; 12% annual rate; 40 expected days; no fee | Advance ₹9,80,000; interest ₹12,887.67; reserve ₹20,000 |

For the financing case, day-zero cash is ₹10,00,000 + ₹9,80,000 − ₹12,887.67 = ₹19,67,112.33. When the buyer pays on day 40, the ₹20,000 reserve is released, and ending cash is ₹19,87,112.33. The reserve is not counted as financing cost. The model assumes the unadvanced balance remains a receivable and is released when the buyer pays; actual financing agreements may differ.

## Corrections embodied in the code

- **Financing formula / business assumption:** the unadvanced balance is a residual receivable rather than a financing fee. Interest and explicit fees are modeled separately.
- **Payment timing:** expected payment day reflects the modeled late probability and non-negative conditional delay distribution; financing duration uses the same expected-day function.
- **Horizon handling:** a payment after the simulation horizon is not moved forward to the last day of the horizon.
- **Reproducibility:** invoice-specific random streams use a stable SHA-256-derived seed.
- **Action validation:** unknown or duplicate invoice actions, invalid financing sources, and TReDS actions for ineligible invoices are rejected.
- **Leakage prevention:** policy comparisons pass the same realized payment path to every policy. The optimizer scores actions with expected timing, not future realized payment dates.

## Current seed-42 synthetic demo

Values below were produced by running `python experiments/run_mvp.py` on the current code snapshot.

| Policy | Minimum cash | Shortfall days | Financing cost | Amount financed |
|---|---:|---:|---:|---:|
| Wait | -₹9,00,000 | 20 | ₹0 | ₹0 |
| Largest first | ₹16,18,683 | 0 | ₹31,317 | ₹32,34,000 |
| Earliest due first | ₹16,18,683 | 0 | ₹31,317 | ₹32,34,000 |
| Highest delay risk first | ₹17,95,897 | 0 | ₹48,103 | ₹27,44,000 |
| Cash threshold | ₹16,18,683 | 0 | ₹31,317 | ₹32,34,000 |
| Optimizer | ₹16,18,068 | 0 | ₹29,932 | ₹25,48,000 |

This is one synthetic scenario. It does not show that the optimizer generally outperforms the baselines.

## Previously recorded 500-scenario benchmark

The current working copy contains a timing-aligned benchmark across 500 synthetic scenarios (seeds 20260930–20261429), with a common realized payment path shared across policies in each scenario and no financing fees. The recorded summary was:

| Policy | Scenarios with any shortfall | Shortfall days (median / p90) | Financing cost (median / p90) |
|---|---:|---:|---:|
| Wait | 203 / 500 | 0 / 53 | ₹0 / ₹0 |
| Largest first | 61 / 500 | 0 / 6 | ₹18,426 / ₹76,591 |
| Earliest due first | 83 / 500 | 0 / 13 | ₹8,657 / ₹64,384 |
| Highest delay risk first | 59 / 500 | 0 / 3 | ₹16,561 / ₹81,208 |
| Cash threshold | 61 / 500 | 0 / 6 | ₹18,426 / ₹76,591 |
| Optimizer | 77 / 500 | 0 / 8 | ₹0 / ₹45,590 |

The optimizer had more realized shortfall days than the best baseline in 24 scenarios and higher cost than a baseline with equal or fewer shortfall days in 60 scenarios. The timing-aligned calculation reduced average timing bias, but the optimizer's realized shortfall frequency increased relative to the earlier run. This is evidence of a cost/liquidity trade-off in the synthetic setup, not a production recommendation. Timestamped report artifacts are generated locally by the experiment scripts and are not all included in this PR.

## Remaining research limits

- The payment-delay heuristic is not a calibrated probability model.
- Benchmark data is synthetic; no company history has been validated.
- Financing caps are applied per invoice rather than as a portfolio-wide facility constraint.
- `FOLLOW_UP` is a deterministic acceleration assumption and is not yet a separately benchmarked collection policy.
- `FINANCE_OTHER` is not a complete alternative facility repayment/covenant model.
- Exact subset search is limited to 14 eligible invoices, with greedy fallback for larger portfolios.
- Full historical policy replay, data-source validation, and counterfactual evaluation of financing actions remain future work.

Reproduce the current demo and synthetic benchmark with:

```powershell
python experiments/run_mvp.py
python experiments/run_benchmark.py --scenario-count 500 --seed 20260930
python -m pytest -q
```
