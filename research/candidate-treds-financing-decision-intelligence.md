# Candidate Research — MSME TReDS Financing Decision Intelligence

## Why this candidate matters

Delayed MSME payments remain a major liquidity issue in India. In July 2026, the Government of India announced that operating Central Public Sector Enterprises must route settlement of invoices for goods and services procured from MSMEs through RBI-authorised TReDS platforms.

Sources:

- Government of India / PIB: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2283195&lang=1&reg=20
- RBI TReDS FAQ: https://www.rbi.org.in/scripts/FAQView.aspx/FAQView.aspx/FAQView.aspx?Id=132

## Existing ecosystem

TReDS itself is already established. RBI describes it as an electronic platform for financing/discounting MSME trade receivables through multiple financiers.

Public platforms and related products include:

- M1xchange
- RXIL
- Invoicemart / C2F
- KredX / DTX
- C2TReDS
- Clear Invoice Discounting
- CashFlo supply-chain finance
- Invoice financing marketplaces

Therefore we must NOT build:

- another TReDS marketplace;
- a basic invoice-discounting calculator;
- a basic eligibility checker;
- a basic invoice upload / financing application.

## Candidate problem

Investigate a vendor-neutral **MSME Financing Decision Engine**.

Input:

- outstanding invoices;
- buyer identity and eligibility;
- due dates;
- customer payment history;
- projected cash position;
- TReDS offers / indicative rates;
- bank CC/OD cost;
- early-payment discount opportunities;
- minimum cash requirement.

Output:

- which invoices are candidates for financing;
- which invoices should likely be left to maturity;
- estimated all-in financing cost;
- projected liquidity improvement;
- alternative funding comparison;
- assumptions and confidence;
- reasons an invoice should NOT be financed.

Example question:

> I expect a ₹25 lakh cash gap in 45 days. I have ₹1.2 crore of receivables. Which invoices should I finance, and what is the cheapest way to close the gap while preserving a minimum cash buffer?

This is a decision-support problem, not a lending or financing marketplace.

## Existing software overlap

M1xchange already provides a TReDS cost calculator and transaction workflows.

Clear Invoice Discounting already lets enterprises/suppliers choose early-payment options and can use treasury cash, bank capital or TReDS financing.

Various public tools provide TReDS eligibility and financing-cost calculators.

Therefore the remaining gap is not basic financing calculation.

## Gap hypothesis

A possible gap is **portfolio-level, vendor-neutral financing choice optimization** across multiple funding alternatives and liquidity constraints.

This remains a hypothesis.

We need to test whether existing enterprise treasury / supply-chain-finance products already provide this exact capability.

## Technical research questions

- Can invoice-level cash-flow timing be predicted well enough to optimize financing?
- How should financing cost be annualized and compared across different instruments?
- How should a minimum liquidity floor be represented?
- Can an optimization algorithm select a subset of invoices rather than financing everything?
- How should uncertainty in payment dates affect the decision?
- Can the system explain why it chose invoice A instead of invoice B?
- Can a benchmark dataset reproduce the decision and its financial outcome?

## Potential end product

A finance application with:

1. Receivables portfolio view.
2. Cash-gap forecast.
3. Funding-option comparison.
4. Invoice financing recommendation engine.
5. Scenario simulator.
6. Cost / liquidity trade-off analysis.
7. Explainable decision report.
8. Reproducible evaluation harness.

## Current assessment

Real-world pain: HIGH

India relevance: VERY HIGH

Technical depth: HIGH

Finance relevance: VERY HIGH

Existing software overlap: HIGH

Unverified gap: Portfolio-level vendor-neutral funding optimization

Status: RESEARCH ONLY
