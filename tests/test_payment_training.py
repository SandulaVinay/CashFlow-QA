from __future__ import annotations

import csv
from datetime import date, timedelta

from experiments.train_payment_baseline import (
    add_as_of_features,
    build_report,
    read_invoice_csv,
)


def format_us_date(value: date) -> str:
    return f"{value.month}/{value.day}/{value.year}"


def write_synthetic_invoice_csv(path, row_count: int = 40):
    headers = [
        "countryCode", "customerID", "PaperlessDate", "invoiceNumber",
        "InvoiceDate", "DueDate", "InvoiceAmount", "Disputed", "SettledDate",
        "PaperlessBill", "DaysToSettle", "DaysLate",
    ]
    start = date(2020, 1, 1)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for index in range(row_count):
            issued = start + timedelta(days=30 * index)
            due = issued + timedelta(days=30)
            late = index % 4 in (0, 1)
            settled = due + timedelta(days=(5 + index % 3) if late else -2)
            writer.writerow({
                "countryCode": ["391", "406", "770", "818"][index % 4],
                "customerID": f"CUST-{index % 5}",
                "PaperlessDate": format_us_date(issued),
                "invoiceNumber": f"INV-{index:04d}",
                "InvoiceDate": format_us_date(issued),
                "DueDate": format_us_date(due),
                "InvoiceAmount": f"{30 + (index % 9) * 12.5:.2f}",
                "Disputed": "Yes" if index % 7 == 0 else "No",
                "SettledDate": format_us_date(settled),
                "PaperlessBill": "Electronic" if index % 2 else "Paper",
                "DaysToSettle": (settled - issued).days,
                "DaysLate": max(0, (settled - due).days),
            })


def test_future_settlement_cannot_be_used_in_invoice_issue_history(tmp_path):
    source = tmp_path / "invoice-history.csv"
    write_synthetic_invoice_csv(source)
    records = read_invoice_csv(source)
    features = add_as_of_features(records)

    # The first invoice is paid after the second invoice is issued. Its future
    # settlement is not available as history for the second invoice.
    assert records[0]["settled_date"] > records[1]["invoice_date"]
    assert features[1]["prior_invoice_count"] == 0
    assert features[1]["prior_late_rate"] == 0.5


def test_payment_model_trains_on_chronological_holdout(tmp_path):
    source = tmp_path / "invoice-history.csv"
    write_synthetic_invoice_csv(source)
    records = read_invoice_csv(source)

    summary, artifact = build_report(records, train_fraction=0.8)

    assert summary["dataset"]["row_count"] == 40
    assert summary["dataset"]["settled_invoice_count"] == 40
    assert summary["split"]["train_row_count"] == 32
    assert summary["split"]["test_row_count"] == 8
    assert summary["split"]["method"].startswith("chronological")
    assert summary["evaluation"]["classification"]["roc_auc"] is not None
    assert "SettledDate" in summary["features"]["excluded_to_prevent_leakage_or_ambiguous_availability"]
    assert len(artifact["late_payment_classifier"]["weights"]) == len(artifact["features"])


def test_post_outcome_columns_are_not_features(tmp_path):
    source = tmp_path / "invoice-history.csv"
    write_synthetic_invoice_csv(source)
    records = read_invoice_csv(source)
    features = add_as_of_features(records)

    assert all("days_late" not in row["features_raw"] for row in features)
    assert all("settled_date" not in row["features_raw"] for row in features)
    assert all("disputed" not in row["features_raw"] for row in features)
