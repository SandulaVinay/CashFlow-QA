# Historical Data Contract — v1

## Purpose and scope

This contract specifies the minimum history needed to evaluate payment-timing forecasts without using information that was unavailable at a historical decision date. It is an ingestion contract for a research backtest; a live data connector or production-grade historical policy replay is not yet implemented.

The v1 rolling backtest measures invoice-payment timing only. It does not yet replay actual historical financing actions or claim counterfactual cash balances. Those require complete, timestamped cash ledgers and decision-time snapshots.

## Non-negotiable time semantics

Every event must distinguish:

- **Event time** — when the business event occurred, for example payment_at.
- **Recorded/available time** — when the source system first exposed the fact, for example recorded_at.
- **Decision cutoff** — the latest information a forecast or policy could have used.
- **Source completeness watermark** — the timestamp through which the data owner asserts the event history is complete.

For a decision at cutoff t, invoice versions, payment events, obligation versions, cash snapshots, and financing offers may be used as features only when recorded_at is no later than t. A payment date after t is only an outcome label; it must never be read by the predictor. A payment that occurred before t but was recorded after t is a late-recorded fact, not a feature that may be retroactively made visible.

All event timestamps must include an explicit UTC offset. The timezone field is an IANA timezone used to convert timestamps to local accounting dates. Do not infer timezone from the server or workstation. The example dataset uses Asia/Kolkata.

The declared source_data_complete_through watermark must be supplied by the data owner. If completeness cannot be established, keep the outcome censored/unknown rather than interpreting a missing payment as non-payment.

## Required and optional records

| Record | Required fields | Purpose |
|---|---|---|
| Invoices | invoice_id, version, buyer_id, invoice_date, due_date, amount, recorded_at | One version per invoice state as known by the source. A due-date or amount amendment must be a new version with its own recorded_at. |
| Payments | payment_id, invoice_id, payment_at, recorded_at, amount | Actual cash receipt events, including partial receipts. One receipt event per row. |
| Obligations | obligation_id, version, category, due_date, amount, recorded_at | Future obligations and the versions known at each cutoff. |
| Cash balance snapshots | snapshot_id, as_of_at, recorded_at, balance | Observed balance snapshots. A snapshot may be used only after its recorded_at. |
| Financing offers | offer_id, source, rates, advance/cap, availability window, recorded_at | Terms that were available and known at a cutoff. |

Amounts are positive magnitudes in the declared currency; cash balances may be negative. Rates are fractions, not percentages: 0.12 means 12% per annum. Financing records describe assumptions/observations and do not imply that a real TReDS offer was available to a particular supplier.

Duplicate payment IDs, duplicate invoice (invoice_id, version) pairs, duplicate obligation (obligation_id, version) pairs, unknown invoice references, non-positive receipt/invoice amounts, and timestamps without offsets are rejected by the Pydantic contract.

## JSON shape

The accepted input is a UTF-8 JSON object compatible with HistoricalDataBundle in src/decision_lab/historical.py. A minimal example:

    {
      "dataset_id": "demo-history-v1",
      "contract_version": "1",
      "currency": "INR",
      "timezone": "Asia/Kolkata",
      "source_data_complete_through": "2026-06-30T23:59:59+05:30",
      "invoices": [{
        "invoice_id": "INV-001",
        "version": 1,
        "buyer_id": "BUYER-A",
        "invoice_date": "2026-01-01",
        "due_date": "2026-01-31",
        "amount": 125000.0,
        "recorded_at": "2026-01-01T10:00:00+05:30",
        "eligible_for_treds": false
      }],
      "payments": [{
        "payment_id": "RCPT-001",
        "invoice_id": "INV-001",
        "payment_at": "2026-02-05T15:30:00+05:30",
        "recorded_at": "2026-02-05T16:00:00+05:30",
        "amount": 125000.0
      }],
      "obligations": [],
      "cash_balances": [],
      "financing_offers": []
    }

This is illustrative only, not customer or market data. Real company exports normally contain many invoices, partial receipts, dated obligation versions, regular cash snapshots, and financing terms known at historical cutoffs.

## Data-quality checks before backtesting

1. Confirm invoice/payment identifiers and versioning rules with the data owner.
2. Reconcile receipt totals and partial receipts to invoice amounts. Identify credit notes, reversals, write-offs, disputes, and overpayments rather than treating them as ordinary receipts.
3. Check invoice date, due date, event timestamps, recorded timestamps, and source watermark for plausible ordering.
4. Confirm whether amount is gross or net of tax/credit notes, and define one currency/precision rule.
5. Measure late-recording latency. A payment credited to the bank before a cutoff but entered into the source after it creates an observability issue.
6. Confirm snapshots represent bank cash, book cash, or another balance definition. Do not combine these without reconciliation.
7. Version source extracts and remove unnecessary customer identifiers from research fixtures.

## Rolling-origin evaluation rules

At each cutoff, the prototype:

1. selects the latest invoice version with recorded_at no later than the cutoff;
2. builds training history only from invoices whose full settlement can be established using payments recorded by the cutoff;
3. learns a transparent buyer-level median delay if the buyer has enough settled history, otherwise falls back to global history, otherwise uses an explicit cold-start default;
4. predicts payment timing for invoices still open according to information visible at the cutoff;
5. uses subsequent settled payment dates only to score predictions;
6. reports censored invoices and invoices settled before the cutoff but recorded later separately;
7. compares the prediction with a due-date-only baseline using MAE, median absolute error, amount-weighted MAE, signed error, and a Brier score for late-payment probability.

The current baseline uses fully settled historical invoices only. This is a transparent first baseline and may be biased toward invoices that settle sooner. Censored cases are reported rather than silently treated as on-time. A survival/time-to-event method may be warranted after the real history and censoring patterns are understood.

Use several rolling origins, not a random train/test split. Origins must precede the source completeness watermark when future outcomes are to be scored. Adding future payment rows must not change a prediction made at an earlier origin; a regression test enforces this invariant.

## Run

    python -m pip install -e ".[test]"
    pytest -q
    python experiments/run_historical_backtest.py --data tests/fixtures/historical-sample.json --origin-start 2026-04-15 --origin-end 2026-04-15 --frequency monthly

The script writes a timestamped JSON report to reports/. Use the real source completeness watermark and cutoffs with sufficient follow-up time. Do not run against production data until the contract has been reviewed with the source owner and privacy/security requirements are satisfied.

## Not yet implemented

- Source-specific CSV/Excel/database adapters and idempotent ingestion.
- Full as-of snapshots for changing customer/collection covariates beyond versioned invoice and obligation records.
- A survival model for unsettled/censored invoices.
- Full daily cash-ledger reconciliation and historical replay of policy decisions.
- Credible counterfactual evaluation for financing actions that were not actually taken.
- Model calibration or real-world acceptance thresholds.
