# CODEX HANDOFF — MSME RECEIVABLES DECISION LAB

## 0. Purpose of this file

You are taking over an active research and engineering project. Do not treat this as a greenfield request.

This file is the handoff from the planning/research conversation. You have enough context here to continue the work without asking the user to paste the previous conversation.

Your job is to:
1. Inspect the current repository and code.
2. Run the existing tests.
3. Run the current MVP experiment.
4. Check whether the financial calculations are mathematically and financially correct.
5. Identify defects or invalid assumptions.
6. Fix the smallest responsible layer.
7. Add regression tests.
8. Re-run the tests.
9. Run controlled experiments.
10. Decide whether the current formula/model is adequate, should be reformulated, or should be replaced.
11. Document the evidence and continue to the next milestone.

Do not change models simply because a result "looks wrong". First determine whether the issue is implementation, data, formula, business assumption, objective function, or model choice.

Do not hide surprising results. Unexpected results are research evidence.

---

# 1. Project identity

Repository:
SandulaVinay/CashFlow-QA

Active product:
MSME Receivables Decision Lab

The repository name is historical. Do not rename it unless explicitly instructed.

Current implementation branch:
feature/msme-decision-lab-mvp

Current implementation PR:
PR #4 — feat: prototype MSME receivables decision lab

Implementation issue:
Issue #3 — Build MVP: MSME Receivables Decision Lab prototype

---

# 2. Business problem

The project addresses the Indian MSME delayed-payment problem.

A March 11, 2026 PIB release reported that the Economic Survey 2025-26 estimates approximately ₹8.1 lakh crore locked in delayed payments to MSMEs.

Official Government source:
https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238242&lang=1&reg=1

TReDS is the existing RBI-regulated mechanism for financing/discounting MSME trade receivables through financiers.

Official RBI source:
https://www.rbi.org.in/scripts/FAQView.aspx/FAQView.aspx/FAQView.aspx?Id=132

The Government of India has also moved to require operating CPSEs to route settlement of MSME invoices through authorised TReDS platforms.

Official PIB:
https://www.pib.gov.in/PressReleasePage.aspx?PRID=2283195&lang=1&reg=20

Important:
We are NOT building TReDS.

Our application is a decision-support and research environment around the delayed-receivables problem.

Core question:
"When receivables may be delayed, what action best protects the MSME's minimum cash position at the lowest reasonable cost?"

Potential actions:
- WAIT
- FOLLOW_UP / collection action
- FINANCE_TREDS
- FINANCE_OTHER

The product is not:
- a lender
- a TReDS operator
- a financing marketplace
- a production credit decision engine
- a generic working-capital SaaS clone

---

# 3. Research history

The project initially started from a financial forecast reliability / cash-flow QA idea.

Research showed that:
- cash-flow forecasting is already a mature software category;
- forecast audit, bias monitoring, stress testing, and payment prediction are already covered by commercial products and research;
- therefore the original broad idea was not sufficiently differentiated.

We then researched the MSME delayed-payment problem and TReDS.

We investigated:
- invoice financing
- TReDS
- supply-chain finance
- working-capital optimisation
- invoice pooling
- receivables financing
- portfolio financing
- collection prioritisation
- financing-versus-wait decisions

Commercial ecosystem researched included:
- SAP Taulia
- Kyriba
- Clear
- CashFlo
- CredAble
- CrediOpt
- OpenMax
- Vayana
- C2FO
- existing TReDS platforms
- open-source working-capital projects

Conclusion:
The broad market for "which receivable should I finance?" or "optimize working capital/TReDS" is already crowded.

Therefore do NOT claim:
- first TReDS optimizer
- first vendor-neutral financing optimizer
- first working-capital AI
- no existing software does this

The narrower surviving contribution is:
An open, reproducible environment for measuring which receivables-management policy protects MSME liquidity under payment-delay uncertainty.

Research documents:
- research/final-research-conclusion-2026-09-29.md
- research/deep-dive-narrow-msme-gaps-2026-09-29.md
- research/financing-decision-market-scan-2026-09-29.md
- research/problem-statement.md

---

# 4. Current product definition

Name:
MSME Receivables Decision Lab

Primary user:
MSME owner / finance manager

Question:
"If my receivables are delayed, should I wait, follow up, use TReDS, or use another funding option, and what will each choice do to my future cash position?"

The system should eventually show:
- current cash;
- receivables;
- expected payment timing;
- delay risk;
- upcoming obligations;
- minimum cash requirement;
- action alternatives;
- financing cost;
- minimum cash after each action;
- cash-shortfall days;
- assumptions;
- uncertainty;
- evidence for the decision.

The active research contribution is simulation and benchmarking, not financing execution.

---

# 5. Current product design

Full design document:
docs/product-design.md

Core flow:

Upload data
→ validate
→ build receivables and cash schedule
→ estimate payment timing
→ set minimum cash buffer
→ set financing assumptions
→ run counterfactual simulation
→ compare policies
→ inspect cash impact
→ inspect evidence

Primary planned screens:
1. Overview
2. Receivables
3. Cash calendar
4. Decision Lab
5. Policy comparison
6. Decision evidence

Do not spend significant time on UI polish until the financial engine is validated.

---

# 6. Current architecture

Full architecture:
docs/architecture.md

Current logical flow:

Web/API
→ FastAPI
→ validation
→ canonical finance model
→ payment behaviour model
→ policy engine
→ cash simulator
→ metrics
→ experiment runner
→ evidence report

React + Tailwind should come later.

The first priority is deterministic correctness.

---

# 7. Current source tree

Current MVP implementation:

api/
  __init__.py
  main.py

src/decision_lab/
  __init__.py
  models.py
  behaviour.py
  simulator.py
  policies.py
  data.py
  engine.py

experiments/
  run_mvp.py

tests/
  test_simulator.py

docs/
  product-design.md
  architecture.md
  project-roadmap.md
  mvp-experiment.md

research/
  problem-statement.md
  existing-solutions.md
  research-log.md
  final-research-conclusion-2026-09-29.md
  deep-dive-narrow-msme-gaps-2026-09-29.md
  financing-decision-market-scan-2026-09-29.md

Python package configuration:
pyproject.toml

CI:
.github/workflows/ci.yml

---

# 8. Current domain model

File:
src/decision_lab/models.py

Invoice:
- invoice_id
- buyer_id
- invoice_date
- due_date
- amount
- historical_avg_delay_days
- historical_delay_std_days
- historical_late_rate
- eligible_for_treds

Obligation:
- date
- category
- amount

FinancingOffer:
- source
- annual_rate
- fee_rate
- advance_rate
- max_amount

Scenario:
- as_of_date
- opening_cash
- minimum_cash_buffer
- horizon_days
- follow_up_acceleration_days
- payment_delay_shock_days
- seed
- financing_offers

ActionDecision:
- invoice_id
- action
- financing_source

Allowed actions:
- WAIT
- FOLLOW_UP
- FINANCE_TREDS
- FINANCE_OTHER

SimulationMetrics:
- minimum_cash
- maximum_cash
- ending_cash
- cash_shortfall_days
- financing_cost
- financed_amount
- accelerated_receivables
- financed_invoice_count
- follow_up_invoice_count

---

# 9. Current synthetic scenario

File:
src/decision_lab/data.py

The demo scenario currently generates:
- 12 invoices
- 6 buyer profiles
- different buyer delay behaviour
- different invoice amounts
- future supplier/payroll/tax/rent/EMI obligations
- opening cash = ₹12 lakh
- minimum cash buffer = ₹10 lakh
- 91-day horizon
- follow-up acceleration assumption = 10 days
- payment-delay shock = 5 days
- TReDS annual rate assumption = 12%
- OD annual rate assumption = 14%
- seed = 42

These are synthetic engineering assumptions only.
Do not present them as live market rates.

---

# 10. Current payment-delay model

File:
src/decision_lab/behaviour.py

No ML is currently used.

The current heuristic uses:
- historical late rate
- historical average delay
- historical delay standard deviation

Current risk score is approximately:
risk =
  0.55 * late_rate
  + 0.30 * normalized average delay
  + 0.15 * normalized delay volatility

This is a ranking heuristic, not a production probability model.

The payment realization is reproducible through the scenario seed.

Do not make predictive accuracy claims from this synthetic heuristic.

---

# 11. Current cash-flow simulation

File:
src/decision_lab/simulator.py

The MVP uses a daily 91-day horizon.

Core roll-forward:

closing_cash[t] =
  opening_cash[t]
  + collections[t]
  + financing_inflows[t]
  - obligations[t]
  - financing_costs[t]

Current simulator:
- applies obligations by day;
- applies collections by day;
- applies financing inflow at day 0;
- applies financing cost at day 0;
- calculates daily closing cash;
- calculates minimum cash;
- counts days below minimum cash;
- calculates ending cash.

IMPORTANT:
The financing economics have not yet been fully validated.

Current code approximately uses:
financed_amount = min(invoice.amount * advance_rate, offer.max_amount)
haircut = invoice.amount - financed_amount
interest = financed_amount * annual_rate * expected_days / 365
fees = invoice.amount * fee_rate
total_cost = haircut + interest + fees

This may be mathematically wrong depending on what advance_rate represents.

For example, if an invoice of ₹10 lakh has a 98% advance and the MSME receives ₹9.8 lakh now, the retained ₹20,000 may be a reserve/holdback rather than an economic financing cost. The eventual settlement mechanics matter.

Codex MUST:
1. confirm the intended economics;
2. create a hand-calculated test;
3. distinguish:
   - upfront cash received;
   - financing/discount interest;
   - fees;
   - residual receivable;
   - final settlement;
4. correct the model if necessary.

Do not keep the current formula simply because it is already coded.

---

# 12. Critical benchmark methodology already fixed

A previous reproducibility problem was discovered and corrected.

Every competing policy must receive the same underlying payment-delay realization.

Current compare flow:
engine.compare_policies()
→ generate common payment realization
→ generate actions separately for each policy
→ evaluate every policy on the same realized payment path

This prevents a false result such as:
Policy A gets easy payment timing
Policy B gets difficult payment timing

Do not remove this property.

---

# 13. Current decision policies

File:
src/decision_lab/policies.py

Policies:
1. wait
2. largest_first
3. earliest_due_first
4. highest_delay_risk_first
5. cash_threshold
6. optimizer

Largest-first:
finance largest eligible TReDS invoices until expected gap is covered.

Earliest-due-first:
finance invoices with earliest due dates.

Highest-delay-risk-first:
finance invoices with highest heuristic risk.

Cash-threshold:
currently detects expected gap and falls back to largest-first.

Optimizer:
- enumerates TReDS invoice subsets when <=14 eligible invoices;
- uses a greedy fallback for larger portfolios;
- currently uses expected payment timing for candidate selection;
- MUST NOT use future realized payment dates to decide.

The optimizer is currently a research baseline, not a validated algorithm.

---

# 14. Important current limitations

These need to be investigated, not hidden.

A. Financing economics
Validate whether haircut/advance-rate treatment is correct.

B. Facility limits
Current max_amount is applied at invoice level.
Decide whether scenario modeling needs:
- portfolio cap;
- daily cap;
- per-source cap;
- per-buyer cap.

Do not invent regulatory rules. Keep them configurable if they are hypothetical.

C. FOLLOW_UP
The action exists in the data model and simulator but is not yet a fully independent benchmark policy.

D. OTHER_FINANCING
The action exists but the optimizer currently focuses primarily on TReDS.

E. Optimizer objective
Current optimizer scoring is approximately:
1. shortfall days
2. financing cost
3. invoice count

This is a research baseline, not the final objective.

The final objective may need:
liquidity shortfall penalty
+ financing cost
+ unnecessary financing penalty
+ collection/action cost

Do not choose arbitrary weights without experiments.

F. Expected vs realized timing
The decision must use only information available at decision time.
Realized future payment dates are for evaluation only.

G. Metrics
Validate all metrics with hand calculations and invariants.

---

# 15. HOW TO TEST NOW

Start from repository root.

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest -q

Then:

python experiments/run_mvp.py

The experiment writes:
reports/mvp-baseline.json

If tests fail:
- do not immediately rewrite everything;
- read the traceback;
- isolate the failing rule;
- reproduce it with a minimal test.

If the environment fails:
- fix packaging/dependency/environment issues first;
- keep those fixes separate from mathematical changes.

---

# 16. Testing hierarchy

Do this in order.

## Level 1 — Unit tests

Test:
- data validation
- date calculations
- expected payment day
- payment realization
- financing formula
- daily cash roll-forward
- minimum cash
- shortfall days
- policy action validity

## Level 2 — Hand-calculated cases

Create tiny examples whose answers can be calculated manually.

Examples:
- opening cash with no transactions;
- one collection;
- one obligation;
- one collection plus one obligation;
- one TReDS financing transaction;
- one follow-up acceleration;
- one alternate financing transaction.

If Python disagrees with manual arithmetic, the manual case wins until the discrepancy is explained.

## Level 3 — Financial invariants

Examples:
- no inflows/outflows => ending cash = opening cash
- collection increases cash by the collection amount
- obligation decreases cash by the obligation amount
- financing inflow cannot exceed configured advance
- financing cost cannot be negative
- minimum cash <= maximum cash
- shortfall days is between 0 and horizon + 1
- same seed => same simulation
- same scenario comparison => same realized payment path

## Level 4 — Differential tests

Compare policies on deliberately constructed cases where the expected ordering is obvious.

## Level 5 — Scenario tests

Run dozens/hundreds of controlled scenarios.

## Level 6 — Benchmark / Monte Carlo campaign

Only after levels 1-5 are clean.

---

# 17. HOW TO DECIDE WHETHER TO CHANGE THE MODEL

This is extremely important.

When a calculation/result fails, use this decision tree:

FAIL
→ reproduce
→ minimal test
→ inspect implementation
→ inspect data contract
→ verify formula
→ verify business assumption
→ test alternative formulation
→ only then consider changing model family

Never jump directly from "bad output" to "use XGBoost".

---

# 18. Failure type A — implementation bug

Examples:
- wrong sign;
- duplicate transaction;
- wrong day;
- amount counted twice;
- wrong max cap;
- wrong source mapped to action.

Action:
- fix code;
- add regression test;
- rerun all tests;
- document the cause.

---

# 19. Failure type B — data contract problem

Examples:
- rate stored as 12 instead of 0.12;
- due date parsed in wrong format;
- amount includes/excludes tax unexpectedly;
- actual_payment_date missing;
- historical data contains impossible negative amounts.

Action:
- fix schema/validation/conversion;
- add validation test;
- do not change the prediction model.

---

# 20. Failure type C — mathematical formula problem

Examples:
- financing interest annualized incorrectly;
- discounting formula wrong;
- advance/holdback treated incorrectly;
- daily cash balance uses wrong sign;
- shortfall count includes day 0 unexpectedly.

Action:
- create a hand-calculated example;
- correct formula;
- document formula;
- add exact regression test.

---

# 21. Failure type D — model assumption problem

Examples:
- mean delay too sensitive to outliers;
- fixed 10-day follow-up acceleration is unrealistic;
- a single risk score is treated as a calibrated probability.

First try changing the formulation without changing model family.

Examples:
- mean → median
- mean → trimmed mean
- point estimate → interval
- fixed acceleration → scenario distribution
- ranking score → ranking only, not probability

Then evaluate.

---

# 22. Failure type E — model family problem

Only replace the model family after evidence shows the formulation is inadequate.

Recommended sequence:

Transparent heuristic
→ statistical baseline
→ survival/time-to-event model
→ tree-based ML
→ probabilistic/calibrated model

Do not use complexity as a goal.

A better model must be justified by:
- appropriate metrics;
- leakage-safe evaluation;
- stability;
- explainability;
- business usefulness.

---

# 23. What if the result is correct?

If hand calculations pass and tests pass:

1. Run the demo.
2. Inspect policy outputs.
3. Build a scenario generator.
4. Run 500-1,000 scenarios.
5. Compare policies.
6. Record where each policy wins/loses.
7. Inspect optimizer failure cases.
8. Only then refine the optimizer.
9. Only after engine validation build the UI.

---

# 24. What counts as a good experiment

Not:
"The optimizer gave sensible results."

A valid experiment requires:
- correct arithmetic;
- deterministic reproducibility;
- equal payment realizations for policy comparison;
- no hindsight leakage;
- correct financing economics;
- measurable policy differences;
- repeated scenarios;
- documented assumptions and failures.

The optimizer does not need to win every scenario.

A result such as:
"The optimizer reduces financing cost but increases shortfall risk"
is valid evidence and must be reported honestly.

---

# 25. Benchmark campaign

After correctness is established, generate at least 500-1,000 scenarios.

Vary:
Receivables:
- number
- amount
- due dates
- buyer concentration

Payment behaviour:
- late rate
- average delay
- delay volatility
- behaviour regime changes

Liquidity:
- opening cash
- minimum buffer
- obligation timing
- obligation concentration

Financing:
- TReDS rate
- OD rate
- fees
- advance rate
- facility limits

Stress:
- +7 day delay
- +15 day delay
- +30 day delay
- major buyer shock
- unexpected expense shock

Every run must use explicit seeds.

---

# 26. Benchmark policies

At minimum:
1. WAIT
2. largest invoice first
3. earliest due first
4. highest delay risk first
5. cash threshold
6. optimizer

Later:
7. follow-up first
8. cheapest financing first
9. TReDS first
10. OD first
11. hybrid policy

Do not compare an optimizer only against weak baselines.

---

# 27. Evaluation metrics

Liquidity:
- minimum cash
- cash-shortfall days
- ending cash

Financing:
- financing cost
- amount financed
- number of invoices financed

Collections:
- amount accelerated
- number of follow-ups

Decision efficiency:
- cost per ₹ of liquidity gained
- unnecessary financing
- shortfall avoided

Later:
- robustness to perturbation
- regret versus a hindsight optimum
- sensitivity to model misspecification

---

# 28. Strict decision/evaluation separation

This is mandatory.

When a policy chooses an action, it may use:
- invoice details
- historical payment behaviour
- current cash
- known future obligations
- configured financing assumptions

It may NOT use future realized payment dates.

During evaluation:
- apply the selected policy to a realized scenario;
- calculate the outcome;
- compare outcomes fairly.

This prevents hindsight bias.

---

# 29. Experiment artifacts

Save:
- experiment ID
- commit SHA
- dataset version
- scenario count
- seed
- policy version
- model version
- assumptions
- financing parameters
- metrics
- summary statistics
- failure cases

Recommended:
reports/mvp-baseline.json
reports/benchmark-summary.json
reports/benchmark-report.md
reports/failure-cases.json

Never silently replace important reports. Version or timestamp them.

---

# 30. UI policy

The UI comes after engine validation.

Planned:
- Overview
- Receivables
- Cash calendar
- Decision Lab
- Policy comparison
- Decision evidence

The frontend must consume verified API outputs.

Do not duplicate financial calculation logic inside React.

---

# 31. AI policy

AI is NOT part of the MVP decision logic.

Later AI can:
- explain verified results;
- summarize assumptions;
- answer questions over verified outputs;
- explain why policies differ.

LLM must never be the source of truth for:
- cash balances;
- invoice amounts;
- financing costs;
- payment dates;
- rates;
- shortfall days.

All numbers must come from the deterministic engine.

The system should be able to say:
"Insufficient evidence."

---

# 32. Git rules

Use:
- feature branches
- Conventional Commits
- pull requests
- no force push

For material model/formula changes:
- update tests;
- update documentation;
- record why the change was made.

Current branch:
feature/msme-decision-lab-mvp

Current PR:
#4

Do not casually merge to main.

---

# 33. Immediate task for Codex

Do not start with React.

Do this exact sequence:

1. Inspect the repository and confirm branch.
2. Install the project.
3. Run pytest.
4. Run python experiments/run_mvp.py.
5. Inspect reports/mvp-baseline.json.
6. Independently hand-calculate at least 4 tiny scenarios:
   - pure collection
   - pure obligation
   - wait scenario
   - financing scenario
7. Verify the cash roll-forward.
8. Verify financing economics and decide whether the current formula is correct.
9. Verify common payment realization across policies.
10. Add missing regression tests.
11. Run the full test suite.
12. Produce a written calculation-validation report.
13. Only after that, build the 500-1,000 scenario benchmark generator.

When a defect appears, explicitly classify it as:
- implementation
- data
- formula
- business assumption
- objective function
- model family

Then fix the responsible layer.

---

# 34. Next milestone after validation

If the current engine passes correctness tests:

Build:
- scenario generator;
- benchmark runner;
- policy comparison;
- summary statistics;
- failure-case extraction.

Then determine:
- whether optimizer adds measurable value;
- whether the objective should change;
- whether a different payment-timing model is needed.

Only after benchmark evidence:
- implement a stronger collection/follow-up policy;
- implement true alternative financing comparison;
- refine optimizer;
- expose the API;
- build React UI.

---

# 35. Definition of done for first research milestone

All must be true:

[ ] environment installs
[ ] tests pass
[ ] demo experiment runs
[ ] financing formula has a hand-calculated validation
[ ] cash roll-forward has exact tests
[ ] common payment realization is verified
[ ] optimizer has no hindsight leakage
[ ] 500+ benchmark scenarios run reproducibly
[ ] baseline comparison report exists
[ ] failure cases are documented
[ ] every model/formula change has a written reason

---

# 36. Important mindset

This is a research project, not a demo.

Do not optimize for:
- fancy UI
- AI buzzwords
- maximum model complexity
- making the optimizer "win"
- pretending a known capability is novel

Optimize for:
- correctness
- reproducibility
- financial reasoning
- fair experiments
- transparent assumptions
- measurable improvement
- honest failure analysis

The correct outcome can be:
"the current optimizer is not better."

That is useful because it tells us what to improve next.

---

# 37. Key repository references

Read first:
1. research/final-research-conclusion-2026-09-29.md
2. docs/product-design.md
3. docs/architecture.md
4. docs/mvp-experiment.md
5. research/problem-statement.md
6. src/decision_lab/
7. tests/

---

# 38. Final summary

The project evolved from:
generic cash-flow forecast QA

to:
MSME delayed-payment intelligence

to:
broad TReDS financing decision intelligence

and research showed those broad categories were already crowded.

The current project is now:

# MSME Receivables Decision Lab

The project asks:

> Given uncertain receivable timing and future cash obligations, which action policy best protects MSME liquidity at acceptable cost?

The first job is NOT AI.
The first job is NOT the UI.

The first job is:
1. prove the financial simulation is correct;
2. prove policy comparisons are fair;
3. prove the optimizer has no hindsight leakage;
4. run a reproducible benchmark;
5. then decide whether the model, formula, or objective needs to change.

Work from evidence.
Do not manufacture novelty.
Do not hide failures.
Do not ask the user to reconstruct context from the previous conversation.
