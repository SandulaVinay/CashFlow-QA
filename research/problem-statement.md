# Problem Statement

## Project direction

**Current research focus: MSME Receivables & Financing Decision Intelligence**

Working titles:

- **MSME Financing Decision Intelligence**
- **TReDS Decision Engine** (working name for the financing-decision layer)

This project is focused on the **MSME delayed-payment problem** in India and on the decision layer around receivables, cash-flow impact and financing.

---

## The problem: delayed MSME payments

A major financial problem for Indian MSMEs is that money owed by customers can remain unpaid or be paid significantly later than expected.

The scale is material. A **March 11, 2026 Press Information Bureau (PIB) release**, summarising the Department-Related Parliamentary Standing Committee on Industry's report, states that the **Economic Survey 2025-26 estimates approximately ₹8.1 lakh crore locked in delayed payments to MSMEs**.

> **₹8.1 lakh crore is estimated to be locked in delayed payments to MSMEs.**

### Official Government source

[PIB — ₹8.1 lakh crore locked in delayed payments to MSMEs](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238242&lang=1&reg=1)

The PIB release also distinguishes this broader estimated delayed-payment pool from the smaller amount represented by applications on the **MSME Samadhaan Portal**.

---

## Why delayed payments matter to an MSME

An unpaid invoice is not only an accounting or collections issue. The timing of the receivable affects the business's available cash.

For example, an MSME may have:

- customer invoices worth ₹50 lakh outstanding;
- salaries due in 15 days;
- supplier payments due in 20 days;
- taxes, rent and loan obligations due before major customers are expected to pay.

The business may therefore have positive sales and receivables while still facing a **near-term liquidity gap**.

The practical question is not simply:

> "Which invoices are overdue?"

The more useful question is:

> **"Which receivables are likely to be delayed, how will that delay affect my cash position, and what action should I take?"**

---

## Existing policy / financing mechanism: TReDS

The **Trade Receivables Discounting System (TReDS)** is an RBI-regulated electronic platform designed to facilitate the financing / discounting of MSME trade receivables through multiple financiers.

According to the RBI's TReDS FAQ:

1. The MSME seller or buyer creates a **Factoring Unit** representing the invoice / receivable.
2. The counterparty accepts the Factoring Unit.
3. Financiers bid to finance / discount the receivable.
4. The selected bid is accepted.
5. The financier pays the agreed financed amount to the MSME seller at the agreed financing / discounting rate.
6. The buyer pays the financier on the due date.

TReDS transactions are designed to be **without recourse to the MSME seller** in the event of buyer default, subject to the applicable TReDS framework.

### Official RBI source

[RBI — Trade Receivables Discounting System (TReDS) FAQ](https://www.rbi.org.in/scripts/FAQView.aspx/FAQView.aspx/FAQView.aspx?Id=132)

TReDS therefore provides an important **financing mechanism for accelerating receivables**, but it does not by itself answer every operational decision an MSME owner faces before financing an invoice.

---

## What our project is trying to solve

We are **not building another TReDS marketplace**.

We are researching and designing a **decision-intelligence layer around MSME receivables**.

The application should help an MSME business owner / finance person answer questions such as:

### 1. Which receivables need attention?

- Which customers consistently pay late?
- Which invoices are approaching or past due dates?
- Which apparently small overdue amounts are becoming important because of the timing of other cash obligations?
- Which receivables have changed behaviour compared with the customer's historical payment pattern?

### 2. Which payments may become delayed?

The system may estimate:

- expected payment timing;
- probability / risk of delay;
- expected days of delay;
- customer-specific payment behaviour;
- confidence / data sufficiency for the estimate.

The system should be able to say **"insufficient evidence"** when the available history is not strong enough for a reliable estimate.

### 3. How does a delayed receivable affect business cash flow?

The engine should translate receivable timing into business consequences.

For example:

```text
Outstanding receivable
        ↓
Expected payment date
        ↓
Cash-flow forecast
        ↓
Upcoming obligations
        ↓
Liquidity gap / surplus
        ↓
Potential financial impact
```

A ₹2 lakh delay may be immaterial for one company and important for another depending on cash balance, payroll, supplier commitments, debt payments and other obligations.

### 4. Which receivables should be financed?

The engine should evaluate whether a receivable may be better handled by:

- follow-up / collection action;
- waiting for normal settlement;
- negotiating earlier payment;
- financing / discounting through TReDS;
- another available working-capital option.

The objective is **not** to finance every overdue invoice.

The objective is to compare the expected **liquidity benefit, timing, financing cost and business constraints** before recommending an action.

---

## Example decision scenario

Suppose an MSME has:

- Current cash: **₹12 lakh**
- Upcoming obligations in 30 days: **₹30 lakh**
- Receivables outstanding: **₹80 lakh**

One ₹20 lakh receivable is historically paid 35-45 days late.

The application should not stop at:

> "Invoice is overdue."

It should investigate:

> "What happens to the business if this ₹20 lakh arrives 30 days later than planned?"

Then it can compare scenarios such as:

```text
Option A — Wait for payment
→ Higher cash-flow risk but no financing cost

Option B — Intensify collection / follow-up
→ Potentially faster collection without financing cost

Option C — Consider TReDS financing
→ Earlier liquidity, less receivable exposure,
   but financing / discounting cost applies

Option D — Other working-capital funding
→ Compare cost and liquidity impact
```

The output should show the **financial impact, assumptions and evidence behind the decision**.

---

## Core research question

> **Can we build a vendor-neutral, data-driven decision engine that helps an MSME determine which receivables require attention, how payment delays affect liquidity, and when financing through TReDS or another funding source may be economically and operationally justified?**

This is a **research hypothesis**, not a claim that the problem is unsolved by existing software.

---

## What we are NOT building

We are not trying to build:

- another invoice tracker;
- another payment reminder application;
- another TReDS marketplace;
- another TReDS eligibility checker;
- another invoice-discounting calculator;
- another generic cash-flow forecasting dashboard.

The research objective is to identify a **specific, testable decision gap** that existing products do not adequately address.

---

## Proposed intelligence layers

```text
Receivables Data
      ↓
Data Quality & Validation
      ↓
Payment Behaviour Analysis
      ↓
Delay / Timing Intelligence
      ↓
Cash-flow Impact Analysis
      ↓
Financing & Action Comparison
      ↓
Decision Engine
      ↓
Evidence-backed Recommendation
```

An AI explanation layer may later explain verified outputs, assumptions and scenarios, but the underlying financial calculations should remain deterministic and auditable.

---

## Research-first approach

Before implementation, we will compare:

- government policy and official TReDS rules;
- existing TReDS platforms;
- supply-chain finance and invoice-financing products;
- receivables / collections software;
- academic research;
- open-source implementations;
- available datasets; and
- documented limitations and failure modes.

The repository should preserve the path:

**Problem → Existing solutions → Gap → Hypothesis → Data → Baseline → Implementation → Evaluation → Failure analysis → Improvement**

If research shows that a proposed capability is already adequately solved, we will document that finding and revise the scope instead of claiming novelty.

---

## Non-goal

This project is a **decision-support and financial analytics system**.

It is not intended to:

- replace a CFO, accountant, auditor, lender or financial adviser;
- act as a regulated lender or TReDS operator;
- guarantee that a receivable will be paid on a predicted date;
- guarantee financing approval or financing rates;
- make decisions from insufficient evidence.

---

## Current status

**Stage: Research / gap validation**

The ₹8.1 lakh crore delayed-payment figure establishes the scale of the problem. TReDS establishes an important existing financing mechanism.

Our current research task is to determine **what decision-intelligence layer can add measurable value around these existing mechanisms** and to prove that value with reproducible experiments before building the full application.
