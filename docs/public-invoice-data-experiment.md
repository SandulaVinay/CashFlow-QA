# Public Invoice-Payment Dataset: First Model Experiment

## Purpose

The purpose of this experiment is to learn the structure of invoice receivables data and establish a small, reproducible payment-timing baseline before claiming that the Decision Lab can support real cash-flow decisions.

It uses a publicly listed research dataset named **Finance Factoring — IBM Late Payment Histories**. The original Kaggle page is:

https://www.kaggle.com/datasets/hhenry/finance-factoring-ibm-late-payment-histories

The CSV inspected for this experiment was available through a public GitHub mirror:

https://github.com/prateek2131-netizen/o2c-accounts-receivable-sql-analysis

The source file is named `Finance Factoring  IBM Late Payment Histories.csv`. The raw file is deliberately not included in this repository. The current public pages do not provide enough independently verified license/provenance detail for us to redistribute the CSV or assert that every record represents a real business transaction. Treat this as an anonymized educational benchmark, not as verified live commercial ledger data. Review original Kaggle terms before use or redistribution.

## What the file contains

The retrieved copy has 2,466 invoice rows and 12 columns:

| Column | Meaning | Intended use |
|---|---|---|
| `countryCode` | Source-provided categorical code | Feature, if known when invoice is issued |
| `customerID` | Pseudonymous customer identifier | Group key for prior-customer history; never a numeric feature |
| `PaperlessDate` | Date associated with paperless delivery | Excluded because its availability relative to invoice issue is unclear |
| `invoiceNumber` | Invoice identifier | Traceability/data-quality checking only |
| `InvoiceDate` | Invoice issue date | Chronological feature cutoff |
| `DueDate` | Contractual due date | Target definition and payment-timing reference |
| `InvoiceAmount` | Invoice amount | Feature |
| `Disputed` | Dispute flag | Excluded because no dispute event/record timestamp is provided |
| `SettledDate` | Observed settlement date | Outcome only; never a direct feature |
| `PaperlessBill` | Paper/electronic category | Excluded because when it became known is not established |
| `DaysToSettle` | Settlement duration | Outcome/derived field; never a feature |
| `DaysLate` | Late days | Outcome/derived field; never a feature |

Observed profile of this copy:

- 2,466 invoices; 2,466 have settlement dates.
- 100 distinct customer IDs and five values of `countryCode`.
- Invoice dates range from 3 January 2012 to 2 December 2013.
- 877 invoices (35.56%) settled after their due dates.
- 561 rows (22.75%) are marked disputed, but the dispute timing is not provided.
- Every invoice has a 30-day gap between issue and due date in this copy.
- Invoice amounts range from 5.26 to 128.28 source units, with a median around 60.56. The file has no currency column, so the units must not be presented as INR or USD.
- There are no open invoices, no partial-payment event ledger, no payment-recording timestamps, no daily cash balances, no scheduled obligations, and no financing offers.

The fixed payment terms, unusually narrow amount range and lack of open invoices constrain the lessons we can draw. This dataset is useful for testing payment-lateness model code; it is not adequate for validating our cash-shortfall or financing-policy simulator.

## Initial training design

The executable entry point is `experiments/train_payment_baseline.py`. It accepts the downloaded CSV without committing the raw data.

1. Sort invoices by issue date and use an 80% chronological training split, rather than random shuffling.
2. Build debtor history at each invoice issue date. A prior invoice contributes only if its issue date is earlier and it was settled by the current invoice's issue date.
3. Use invoice amount, the source categorical code, prior settled invoice count, smoothed prior debtor late rate, and smoothed prior average days late.
4. Do **not** feed settlement date, days to settle, days late, dispute flag, paperless date, paperless billing field, or invoice number into the predictors. Some of those fields are known only after the decision, or their availability cannot be verified.
5. Train a logistic-regression classifier for late vs on-time settlement and a ridge-regression baseline for days late.
6. Compare against a constant training late-rate model and a training-median days-late model.

The source has no `recorded_at` timestamp. The experiment therefore has to assume that a payment is observable on its settlement date. This is a declared limitation: a production backtest must model both when the cash arrived and when the finance/ERP system recorded that fact. If an earlier invoice is still unpaid at the time a later invoice is issued, it is not included in the later invoice's history.

## Exploratory result

An exploratory deterministic training pass over the retrieved 2,466-row file used 1,974 training invoices and 492 later invoices for testing, with a split date of 13 July 2013. The model used the features and leakage restrictions described above.

| Metric | Late-payment classifier | Baseline |
|---|---:|---:|
| ROC-AUC | 0.854 | 0.500 for a constant probability |
| Average precision | 0.694 | Depends on the test late-payment rate |
| Brier score | 0.136 | 0.211 for the training late-rate probability |
| Log loss | 0.422 | 0.613 for the training late-rate probability |
| Accuracy at probability 0.5 | 80.7% | 72.0% for always predicting the training-majority class |

For predicting days late, the regularized linear regression's exploratory test MAE was 2.19 days, compared with 2.29 days for a baseline that always predicts the training median (0 days late).

These are promising results for exercising the pipeline, but **they are not yet a validated model result**. They come from one short historical period, one chronological split and an educational dataset whose provenance and recording-time semantics have not been independently verified. The metrics should be regenerated by the repository CLI against the exact downloaded file and version before publication. They must not be presented as expected production performance.

## Run it yourself

Download the CSV through the original dataset page and inspect its license/terms. Keep the raw file outside Git:

    python experiments/train_payment_baseline.py --data path/to/Finance-Factoring-IBM-Late-Payment-Histories.csv

The command produces a timestamped evaluation report and model artifact in `reports/`. The report records the input file SHA-256 and the split configuration. Do not commit raw customer data, even if its customer IDs are pseudonymous.

## What is next after this baseline

1. Re-run the committed training script against the exact file and reconcile any metric differences.
2. Obtain a second dataset that includes unpaid/open invoices and ideally installment/partial receipts; validate source provenance and license.
3. Validate how payment timestamps and source-recording timestamps differ.
4. Add features only after confirming they would be available at the decision cutoff.
5. Build an evaluation around censoring/open invoices, then consider survival analysis if the data supports it.
6. Separately obtain historical cash balances and due obligations before measuring whether improved payment predictions translate into fewer liquidity-shortfall days.
7. Only after those steps should we train a model on business data and test decisions against counterfactual policies.

## Sources

- Original Kaggle dataset listing: https://www.kaggle.com/datasets/hhenry/finance-factoring-ibm-late-payment-histories
- Public CSV mirror used for inspection: https://github.com/prateek2131-netizen/o2c-accounts-receivable-sql-analysis
- Background research on invoice-payment prediction: https://arxiv.org/abs/2008.07363
