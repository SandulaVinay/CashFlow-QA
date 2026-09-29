# Deep Research — Three Narrow MSME Receivables Decision Gaps
## 2026-09-29

## Research objective

Test three narrower versions of the MSME delayed-payment / TReDS problem:

1. Small-invoice portfolio aggregation / prioritization
2. Financing vs. collection vs. wait optimization under a minimum-cash constraint
3. Independent, reproducible benchmarking of receivables-financing decisions

The objective is to determine whether any of these is sufficiently differentiated, technically buildable, India-relevant and useful enough to become the core application.

---

# 1. Small-invoice portfolio aggregation / prioritization

## Hypothesis

Many individually small MSME receivables may be unattractive to financiers. A decision engine could identify, prioritize or aggregate them into a financially meaningful pool.

## Evidence that the problem is real

A May 2026 report stated that the government was examining a framework for TReDS receivables securitisation because many invoices below ₹5 lakh did not attract enough financiers. The report also said TReDS did not then permit pooling invoices for sale to institutional investors.

Source:
https://www.moneycontrol.com/news/business/banking-panel-eyes-treds-invoice-securitisation-to-improve-msme-cash-flow-13913123.html

The Union Budget 2026-27 proposed introducing TReDS receivables as asset-backed securities to help develop a secondary market and improve liquidity.

Official source:
https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc202621775901.pdf

## Existing capability discovered

This gap is not empty:

- Vayana already describes Trade Receivables Securitisation in which accepted invoices are pooled into a diversified receivables portfolio and funded through securitised instruments. It explicitly describes portfolio-level funding and replenishing structures.
- CredAble markets a portfolio receivables purchase platform in which banks finance a dynamically computed pool of eligible receivables instead of approving invoices one-by-one.
- Indus Equity Partners describes a proprietary multi-anchor, multi-lender invoice-discounting and securitisation engine with pool selection, including diversified pools of 900+ invoices from 25+ buyers and AI-driven pool selection.

Sources:
https://www.vayana.com/supply-chain-finance-solutions/
https://credable.in/receivables-purchase-platform-for-banks/
https://www.indusequitypartners.com/areas-of-interest/fintech/msme-trade-finance-platform/

## Regulatory context

The RBI's current 2026 TReDS draft/master-direction material defines the TReDS platform around uploading, accepting, discounting and settlement of factoring units. It also allows further discounting/re-discounting of discounted factoring units by financiers. The current RBI material does not establish that general pooling for institutional investors is already a standard TReDS function.

Source:
https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4976

The important point is that **the market and policy ecosystem are already actively solving the pooling/securitisation problem**.

## Assessment

**Status: REJECT as our main product gap.**

Why:
- The underlying problem is real.
- India-specific relevance is extremely high.
- But the infrastructure solution is already being built/commercialized by specialist platforms.
- A project that merely implements invoice pooling would duplicate a live industry direction and would require substantial regulatory/financing infrastructure to be realistic.

Potential use in our project:
- Could remain a **scenario / research module** inside a broader simulator.
- Should not be the headline product.

---

# 2. Financing vs. collection vs. wait optimization under a minimum-cash constraint

## Hypothesis

Given a future liquidity gap, the system should decide for each receivable whether to:

- follow up / collect;
- wait;
- negotiate;
- finance through TReDS;
- use another financing source;

while minimizing cost and maintaining a minimum cash buffer.

Example:

> Cash gap in 45 days = ₹25 lakh; receivables = ₹1.2 crore; choose the smallest/lowest-cost set of actions and financed invoices needed to preserve the cash floor.

## Existing capability discovered

The market already covers most of this decision space.

### SAP Taulia

SAP Taulia's Working Capital Agent dynamically analyzes open AR and AP to isolate, recommend and execute cash-gap strategies.

Source:
https://taulia.com/platform/enterprises/working-capital-optimization/

SAP also announced the Working Capital Agent in May 2026 as part of a working-capital suite spanning payables, receivables and supply-chain finance.

Source:
https://taulia.com/company/news/press-releases/sap-taulia-announces-ai-powered-working-capital-innovations-at-sap-sapphire/

### Kyriba

Kyriba's Receivables Finance integrates multiple financial institutions, automates invoice eligibility and funding requests, and combines receivables financing with its Working Capital platform and AI-powered payment forecasting.

Source:
https://www.kyriba.com/resources/fact-sheets/kyriba-receivables-finance

### Clear

Clear explicitly offers multiple supply options — Treasury, TReDS and Bank/NBFCs — and dynamic bidding at invoice level. Its buyer-side product says buyers can choose Treasury, banks or TReDS to fund early payment.

Sources:
https://www.clear.in/invoice-discounting
https://www.clear.in/invoice-discounting-for-buyers

### CashFlo

CashFlo markets a multi-lender, multi-TReDS working-capital platform. It connects buyers to TReDS platforms, banks and NBFCs and says users can choose the most cost-effective or convenient payment source based on real-time cash position or vendor needs.

Sources:
https://www.cashflo.io/working-cap
https://www.cashflo.io/payments-and-recon/enterprise-payments-platform

CashFlo also states that dynamic rules can select which invoices to finance.

Source:
https://www.cashflo.io/magazine/how-cashflo-enhances-treds-for-faster-msme-financing

### OpenMax

OpenMax provides:
- customer payment-behaviour prediction;
- AR behavioural segmentation;
- collections prioritization;
- cash-flow scenario modelling;
- minimum-liquidity/revolving-credit optimization;
- quantified cash-flow impact.

Source:
https://openmax.com/docs/use-cases/role/finance

### CrediOpt

CrediOpt is India/MSME-focused and combines receivables visibility, payment-behaviour intelligence, invoice financing, reminders and credit intelligence. Its public website explicitly describes buyer scores as helping users understand who to push and who to finance.

Source:
https://www.crediopt.com/

### Other evidence

Vayana offers flexible/selective invoice discounting and receivables securitisation, showing that invoice selection and portfolio-level funding are established capabilities.

Source:
https://www.vayana.com/supply-chain-finance-solutions/

## Assessment

**Status: REJECT as a broad product gap.**

The exact optimization objective may not be publicly documented by every vendor, but the surrounding capability is already commercially strong.

We should not claim:

> "Existing software does not optimize which receivables should be financed."

The research does not support that statement.

---

# 3. Independent, reproducible benchmarking of receivables-financing decisions

## Hypothesis

Instead of competing with financing platforms, build an open evaluation layer that answers:

> "Given the same receivables, payment history, cash obligations and financing offers, how good was a financing/collection policy?"

A benchmark could compare:

- wait policy;
- collection-first policy;
- TReDS-first policy;
- bank/OD policy;
- heuristic policies;
- optimization algorithms;
- ML-assisted policies.

Metrics could include:

- minimum cash maintained;
- financing cost;
- days of liquidity gained;
- amount of invoices unnecessarily financed;
- amount of cash-shortfall avoided;
- collection effort;
- decision robustness under delayed-payment scenarios;
- calibration of delay predictions;
- cost of wrong decisions.

## Existing research / open-source overlap

There is substantial research in:
- invoice-payment prediction;
- working-capital optimization;
- factoring portfolio optimization;
- time-series forecasting;
- receivables risk modelling.

Examples include:
- a peer-reviewed factoring-portfolio optimization paper;
- SME receivables-finance AI risk modelling;
- an open-source working-capital optimizer;
- invoice-payment prediction repositories;
- a recent invoice-payment prediction thesis using survival analysis and extensive experiments.

Sources:
https://ibimapublishing.com/articles/IBIMABR/2019/278890/
https://doi.org/10.1109/BigData66926.2025.11402439
https://github.com/Cubiczan/working-capital-optimizer
https://github.com/anneryeo/invoice-payment-prediction-thesis

However, these sources are primarily models, prototypes or specific systems. We did not find a clearly dominant open benchmark specifically for **India/MSME receivables financing decision policies** with a reproducible cash-gap objective.

## Assessment

**Status: PARTIALLY SURVIVES, but not as a standalone MSME product.**

This looks stronger as a **research methodology / evaluation layer** than as the entire customer-facing application.

The value proposition would be:

> "Do not just recommend financing. Prove, using historical and simulated data, that a decision policy actually reduces liquidity shortfalls and financing cost."

That is a credible research contribution, but it needs a real decision problem above it.

---

# 4. Important new discovery: the strongest combined opportunity

The three gaps point toward a narrower product than our original "TReDS Decision Engine".

The better hypothesis is:

## MSME Receivables Decision Simulator

Instead of only asking:

> "Which invoice should I finance?"

the system asks:

> **"What is the cheapest and safest way to keep my business above its minimum cash level when receivables do not arrive as planned?"**

For each receivable, the system can evaluate counterfactual actions:

### WAIT

Expected collection:
₹10L in 12 days

### FOLLOW UP

Expected collection:
₹10L in 5 days

Collection effort:
2 hours

### TReDS

Advance:
₹9.85L

Financing cost:
₹15,000

### BANK / OD

Liquidity:
₹10L

Interest cost:
₹X

Then the engine can compare these actions in the context of the **whole cash schedule**.

The important unit becomes the **action**, not the invoice.

---

# 5. Why this is more interesting

Existing products often optimize one or more parts:

- collections;
- invoice financing;
- TReDS access;
- cash forecasting;
- working-capital optimization.

Our research opportunity is to investigate whether an open/self-hosted MSME tool can combine those into an **explicit counterfactual decision table**:

| Receivable | Wait | Follow up | TReDS | OD | Effect on minimum cash |
|---|---:|---:|---:|---:|---:|
| A | ₹0 | -₹0 | -₹X | -₹Y | +₹10L |
| B | ₹0 | +₹0 | -₹X | -₹Y | +₹15L |
| C | ₹0 | +₹0 | -₹X | -₹Y | +₹5L |

Then optimize for:

**minimum liquidity breach risk + financing cost + collection effort + relationship constraints**

This combined objective is **not proven to be a market gap yet**.

---

# 6. Research conclusion

### Gap 1 — Small-invoice aggregation

**Rejected as the main project gap.**

The problem is real, but securitisation/pooling infrastructure already exists or is actively being developed by specialist platforms and policymakers.

### Gap 2 — Financing vs. collection vs. wait optimization

**Rejected as a broad market gap.**

SAP Taulia, Clear, CashFlo, OpenMax, Kyriba and others already cover substantial pieces of this decision space.

### Gap 3 — Independent reproducible benchmarking

**Survives partially.**

There is room for an open, India-specific benchmark/evaluation framework, but it is not sufficient on its own as the end-user product.

### New refined hypothesis

**MSME Receivables Decision Simulator**

A self-hosted, evidence-driven application that:

1. learns/estimates payment timing from historical receivables;
2. models the MSME's future cash requirements;
3. simulates actions for individual receivables;
4. compares wait vs collection vs TReDS vs other funding;
5. finds the lowest-cost action set that maintains a user-defined minimum cash buffer;
6. reports the financial trade-offs and uncertainty;
7. evaluates the decision policy with reproducible historical backtests and stress scenarios.

**Status: RESEARCH CANDIDATE — NOT YET VALIDATED AS NOVEL.**

---

# 7. Next research gate

Before implementation, test four questions:

### A. Existing-product test
Can we obtain demos/trials of Clear, CashFlo, CrediOpt, OpenMax and, where possible, SAP Taulia/Kyriba and determine whether they already expose this exact counterfactual decision workflow?

### B. Data test
Can we build a realistic public/synthetic dataset containing:
- invoices;
- due dates;
- actual payment dates;
- buyer history;
- cash obligations;
- financing offers?

### C. Decision-quality test
Can a transparent optimization policy outperform simple baselines such as:
- finance oldest invoices;
- finance largest invoices;
- finance highest delay-risk invoices;
- finance everything once cash falls below a threshold?

### D. Impact test
Can we measure:
- cash-shortfall reduction;
- financing-cost reduction;
- unnecessary-financing reduction;
- decision stability under stress?

**Only if these tests produce a measurable result should this become the implementation project.**
