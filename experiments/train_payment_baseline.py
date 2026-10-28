"""Train and evaluate leakage-aware late-payment baselines on invoice CSV data.

Expected input columns match the public IBM Finance Factoring dataset:
countryCode, customerID, InvoiceDate, DueDate, InvoiceAmount, SettledDate.

The script intentionally excludes post-outcome or ambiguously timed columns such
as SettledDate, DaysToSettle, DaysLate, Disputed, PaperlessDate and PaperlessBill
from model features. It is a research baseline, not a production credit model.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from collections import defaultdict


REQUIRED_COLUMNS = {
    "countryCode",
    "customerID",
    "InvoiceDate",
    "DueDate",
    "InvoiceAmount",
    "SettledDate",
}
FEATURE_POLICY = {
    "allowed_at_invoice_issue": [
        "InvoiceAmount",
        "countryCode",
        "customerID (used only for aggregates of invoices settled before this invoice's issue date)",
        "InvoiceDate",
        "DueDate",
    ],
    "excluded_to_prevent_leakage_or_ambiguous_availability": [
        "SettledDate",
        "DaysToSettle",
        "DaysLate",
        "Disputed",
        "PaperlessDate",
        "PaperlessBill",
        "invoiceNumber",
    ],
    "history_assumption": (
        "Settlement information is assumed available on the settlement calendar "
        "date because the source has no recorded_at timestamp. Same-day invoice "
        "history is excluded to avoid ambiguous within-day ordering."
    ),
}


def parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value or value.lower() in {"na", "n/a", "null", "none"}:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date value: {value!r}")


def read_invoice_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        header = {name.strip() for name in reader.fieldnames if name}
        missing = sorted(REQUIRED_COLUMNS - header)
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")

        records = []
        for row_number, raw in enumerate(reader, start=2):
            row = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
            try:
                invoice_date = parse_date(row.get("InvoiceDate"))
                due_date = parse_date(row.get("DueDate"))
                settled_date = parse_date(row.get("SettledDate"))
                amount = float(row["InvoiceAmount"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Invalid required value on CSV row {row_number}: {exc}") from exc

            if invoice_date is None or due_date is None:
                raise ValueError(
                    f"InvoiceDate and DueDate are required on CSV row {row_number}"
                )
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError(
                    f"InvoiceAmount must be positive and finite on CSV row {row_number}"
                )
            customer_id = str(row.get("customerID", "")).strip()
            country_code = str(row.get("countryCode", "")).strip()
            if not customer_id:
                customer_id = "__MISSING_CUSTOMER__"
            if not country_code:
                country_code = "__MISSING_COUNTRY__"

            days_late = (
                max(0, (settled_date - due_date).days)
                if settled_date is not None
                else None
            )
            days_to_settle = (
                (settled_date - invoice_date).days
                if settled_date is not None
                else None
            )
            row_id = str(row.get("invoiceNumber", "")).strip() or f"row-{row_number}"
            records.append(
                {
                    "row_number": row_number,
                    "invoice_id": row_id,
                    "customer_id": customer_id,
                    "country_code": country_code,
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "settled_date": settled_date,
                    "amount": amount,
                    "days_late": days_late,
                    "days_to_settle": days_to_settle,
                    "late": (
                        int(settled_date > due_date)
                        if settled_date is not None
                        else None
                    ),
                    "raw_days_late": (
                        int(float(row["DaysLate"]))
                        if row.get("DaysLate", "") not in ("", None)
                        else None
                    ),
                    "raw_days_to_settle": (
                        int(float(row["DaysToSettle"]))
                        if row.get("DaysToSettle", "") not in ("", None)
                        else None
                    ),
                    "disputed": row.get("Disputed", ""),
                    "paperless_date": parse_date(row.get("PaperlessDate")),
                    "paperless_bill": row.get("PaperlessBill", ""),
                }
            )

    # Stable sorting is important for reproducibility. Same-day rows do not
    # see one another in their history features.
    records.sort(key=lambda r: (r["invoice_date"], r["invoice_id"], r["row_number"]))
    return records


def add_as_of_features(records: list[dict]) -> list[dict]:
    """Build invoice-issue-time features using only already settled history.

    An earlier invoice becomes available to a later invoice only when both
    conditions hold: its issue date is strictly earlier, and its settlement
    date is no later than the later invoice's issue date. Records from the same
    issue date are deliberately not used because the source lacks timestamps.
    """
    events = []
    for row in records:
        if row["settled_date"] is None:
            continue
        available_date = max(
            row["invoice_date"] + timedelta(days=1),
            row["settled_date"],
        )
        events.append((available_date, row))
    events.sort(
        key=lambda item: (
            item[0],
            item[1]["invoice_date"],
            item[1]["invoice_id"],
            item[1]["row_number"],
        )
    )

    global_count = 0
    global_late_count = 0
    global_days_late_sum = 0.0
    customer_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0, "late_count": 0, "days_late_sum": 0.0}
    )
    event_index = 0
    output = []
    index = 0

    while index < len(records):
        current_date = records[index]["invoice_date"]
        while event_index < len(events) and events[event_index][0] <= current_date:
            prior = events[event_index][1]
            stats = customer_stats[prior["customer_id"]]
            stats["count"] += 1
            stats["late_count"] += int(prior["late"] or 0)
            stats["days_late_sum"] += float(prior["days_late"] or 0)
            global_count += 1
            global_late_count += int(prior["late"] or 0)
            global_days_late_sum += float(prior["days_late"] or 0)
            event_index += 1

        end = index
        while end < len(records) and records[end]["invoice_date"] == current_date:
            end += 1

        global_late_rate = (
            global_late_count / global_count if global_count else 0.5
        )
        global_mean_days_late = (
            global_days_late_sum / global_count if global_count else 0.0
        )
        for row in records[index:end]:
            customer = customer_stats[row["customer_id"]]
            customer_count = int(customer["count"])
            smoothing = 5.0
            prior_late_rate = (
                customer["late_count"] + smoothing * global_late_rate
            ) / (customer_count + smoothing)
            prior_mean_days_late = (
                customer["days_late_sum"] + smoothing * global_mean_days_late
            ) / (customer_count + smoothing)
            copy = dict(row)
            copy["prior_invoice_count"] = customer_count
            copy["prior_late_rate"] = prior_late_rate
            copy["prior_mean_days_late"] = prior_mean_days_late
            copy["global_prior_invoice_count"] = global_count
            copy["global_prior_late_rate"] = global_late_rate
            copy["features_raw"] = [
                math.log1p(row["amount"]),
                math.log1p(customer_count),
                prior_late_rate,
                prior_mean_days_late / 10.0,
            ]
            output.append(copy)
        index = end

    return output


def chronological_split(records: list[dict], train_fraction: float = 0.8):
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0.5 and 1.0")
    unique_dates = sorted({row["invoice_date"] for row in records})
    if len(unique_dates) < 3:
        raise ValueError("At least three distinct invoice dates are required")
    split_index = min(
        len(unique_dates) - 1,
        max(1, int(math.floor(len(unique_dates) * train_fraction))),
    )
    split_date = unique_dates[split_index]
    train = [row for row in records if row["invoice_date"] < split_date]
    test = [row for row in records if row["invoice_date"] >= split_date]
    if not train or not test:
        raise ValueError("Chronological split produced an empty train or test set")
    return train, test, split_date


def encode_features(rows: list[dict], country_columns: list[str]) -> list[list[float]]:
    matrix = []
    for row in rows:
        matrix.append(
            [
                row["features_raw"][0],
                *[1.0 if row["country_code"] == country else 0.0 for country in country_columns],
                row["features_raw"][1],
                row["features_raw"][2],
                row["features_raw"][3],
            ]
        )
    return matrix


def standardize_train_test(train_x: list[list[float]], test_x: list[list[float]]):
    width = len(train_x[0])
    means = [
        sum(row[col] for row in train_x) / len(train_x)
        for col in range(width)
    ]
    stds = []
    for col in range(width):
        variance = sum((row[col] - means[col]) ** 2 for row in train_x) / len(train_x)
        stds.append(math.sqrt(variance) or 1.0)

    def transform(matrix):
        return [
            [(row[col] - means[col]) / stds[col] for col in range(width)]
            for row in matrix
        ]

    return transform(train_x), transform(test_x), means, stds


def fit_logistic_regression(
    x: list[list[float]],
    y: list[int],
    iterations: int = 12000,
    learning_rate: float = 0.035,
    l2: float = 0.015,
):
    width = len(x[0])
    weights = [0.0] * width
    bias = 0.0

    def sigmoid(value: float) -> float:
        if value > 30:
            return 1.0 - 1e-13
        if value < -30:
            return 1e-13
        return 1.0 / (1.0 + math.exp(-value))

    for _ in range(iterations):
        gradients = [0.0] * width
        bias_gradient = 0.0
        for row, target in zip(x, y):
            probability = sigmoid(bias + sum(a * b for a, b in zip(row, weights)))
            error = probability - target
            bias_gradient += error
            for col, value in enumerate(row):
                gradients[col] += error * value
        bias -= learning_rate * bias_gradient / len(x)
        for col in range(width):
            weights[col] -= learning_rate * (
                gradients[col] / len(x) + l2 * weights[col]
            )

    return {"bias": bias, "weights": weights, "iterations": iterations, "l2": l2}


def logistic_probability(model: dict, row: list[float]) -> float:
    score = model["bias"] + sum(
        value * weight for value, weight in zip(row, model["weights"])
    )
    if score > 30:
        return 1.0 - 1e-13
    if score < -30:
        return 1e-13
    return 1.0 / (1.0 + math.exp(-score))


def fit_ridge_regression(
    x: list[list[float]],
    y: list[float],
    iterations: int = 12000,
    learning_rate: float = 0.02,
    l2: float = 0.01,
):
    width = len(x[0])
    weights = [0.0] * width
    bias = sum(y) / len(y)

    for _ in range(iterations):
        gradients = [0.0] * width
        bias_gradient = 0.0
        for row, target in zip(x, y):
            prediction = bias + sum(a * b for a, b in zip(row, weights))
            error = prediction - target
            bias_gradient += error
            for col, value in enumerate(row):
                gradients[col] += error * value
        bias -= learning_rate * bias_gradient / len(x)
        for col in range(width):
            weights[col] -= learning_rate * (
                gradients[col] / len(x) + l2 * weights[col]
            )
    return {"bias": bias, "weights": weights, "iterations": iterations, "l2": l2}


def ridge_prediction(model: dict, row: list[float]) -> float:
    prediction = model["bias"] + sum(
        value * weight for value, weight in zip(row, model["weights"])
    )
    return max(0.0, prediction)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _brier(probabilities: list[float], targets: list[int]) -> float:
    return _mean([(p - y) ** 2 for p, y in zip(probabilities, targets)])


def _log_loss(probabilities: list[float], targets: list[int]) -> float:
    losses = []
    for p, y in zip(probabilities, targets):
        p = max(1e-12, min(1 - 1e-12, p))
        losses.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
    return _mean(losses)


def _auc(probabilities: list[float], targets: list[int]) -> float | None:
    positives = sum(targets)
    negatives = len(targets) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(zip(probabilities, targets), key=lambda row: row[0])
    rank_sum = 0.0
    rank = 1
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        average_rank = (rank + (rank + (j - i) - 1)) / 2
        rank_sum += average_rank * sum(target for _, target in ordered[i:j])
        rank += j - i
        i = j
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _average_precision(probabilities: list[float], targets: list[int]) -> float | None:
    positives = sum(targets)
    if positives == 0:
        return None
    ordered = sorted(zip(probabilities, targets), key=lambda row: row[0], reverse=True)
    true_positives = 0
    false_positives = 0
    precision_at_positive = 0.0
    for _, target in ordered:
        if target:
            true_positives += 1
            precision_at_positive += true_positives / (true_positives + false_positives)
        else:
            false_positives += 1
    return precision_at_positive / positives


def regression_metrics(predictions: list[float], targets: list[float]) -> dict:
    errors = [prediction - target for prediction, target in zip(predictions, targets)]
    abs_errors = [abs(value) for value in errors]
    return {
        "mae_days": _mean(abs_errors),
        "rmse_days": math.sqrt(_mean([value * value for value in errors])),
        "mean_signed_error_days": _mean(errors),
        "median_absolute_error_days": statistics.median(abs_errors) if abs_errors else None,
    }


def classification_metrics(probabilities: list[float], targets: list[int]) -> dict:
    predictions = [int(value >= 0.5) for value in probabilities]
    tp = sum(p == 1 and y == 1 for p, y in zip(predictions, targets))
    fp = sum(p == 1 and y == 0 for p, y in zip(predictions, targets))
    tn = sum(p == 0 and y == 0 for p, y in zip(predictions, targets))
    fn = sum(p == 0 and y == 1 for p, y in zip(predictions, targets))
    return {
        "roc_auc": _auc(probabilities, targets),
        "average_precision": _average_precision(probabilities, targets),
        "brier_score": _brier(probabilities, targets),
        "log_loss": _log_loss(probabilities, targets),
        "accuracy_at_0_5": (tp + tn) / len(targets) if targets else None,
        "precision_at_0_5": tp / (tp + fp) if tp + fp else 0.0,
        "recall_at_0_5": tp / (tp + fn) if tp + fn else 0.0,
        "confusion_matrix_at_0_5": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
        "positive_count": sum(targets),
        "negative_count": len(targets) - sum(targets),
    }


def build_report(records: list[dict], train_fraction: float = 0.8) -> tuple[dict, dict]:
    feature_records = add_as_of_features(records)
    labeled = [row for row in feature_records if row["settled_date"] is not None]
    train, test, split_date = chronological_split(labeled, train_fraction)
    if len({row["late"] for row in train}) < 2:
        raise ValueError("Training split must contain both on-time and late invoices")

    countries = sorted({row["country_code"] for row in train})
    country_columns = countries[:-1]
    baseline_country = countries[-1] if countries else None
    feature_names = [
        "log1p_invoice_amount",
        *[f"country_is_{country}" for country in country_columns],
        "log1p_prior_settled_invoice_count",
        "smoothed_prior_customer_late_rate",
        "smoothed_prior_customer_mean_days_late_div_10",
    ]
    train_raw = encode_features(train, country_columns)
    test_raw = encode_features(test, country_columns)
    train_x, test_x, means, stds = standardize_train_test(train_raw, test_raw)
    y_train_late = [int(row["late"]) for row in train]
    y_test_late = [int(row["late"]) for row in test]
    y_train_days = [float(row["days_late"]) for row in train]
    y_test_days = [float(row["days_late"]) for row in test]

    classifier = fit_logistic_regression(train_x, y_train_late)
    probabilities = [logistic_probability(classifier, row) for row in test_x]
    train_rate = _mean([float(value) for value in y_train_late])
    rate_baseline = [train_rate] * len(y_test_late)
    classification = classification_metrics(probabilities, y_test_late)
    classification["constant_training_late_rate_baseline"] = {
        "brier_score": _brier(rate_baseline, y_test_late),
        "log_loss": _log_loss(rate_baseline, y_test_late),
        "roc_auc": 0.5 if len(set(y_test_late)) > 1 else None,
        "description": "Same training late-payment rate for every test invoice.",
    }

    regressor = fit_ridge_regression(train_x, y_train_days)
    predicted_days = [ridge_prediction(regressor, row) for row in test_x]
    baseline_delay = statistics.median(y_train_days)
    regression = regression_metrics(predicted_days, y_test_days)
    regression["training_median_days_late_baseline"] = {
        **regression_metrics([baseline_delay] * len(y_test_days), y_test_days),
        "predicted_days_late": baseline_delay,
    }

    source_late_mismatch = sum(
        row["raw_days_late"] is not None
        and row["raw_days_late"] != row["days_late"]
        for row in records
        if row["settled_date"] is not None
    )
    source_dts_mismatch = sum(
        row["raw_days_to_settle"] is not None
        and row["raw_days_to_settle"] != row["days_to_settle"]
        for row in records
        if row["settled_date"] is not None
    )
    terms_days = [
        (row["due_date"] - row["invoice_date"]).days for row in records
    ]
    amounts = [row["amount"] for row in records]
    amount_sorted = sorted(amounts)
    late_days = sorted(row["days_late"] for row in labeled)
    unique_dates = sorted({row["invoice_date"] for row in labeled})
    dispute_known = [row for row in records if row["disputed"] in {"Yes", "No"}]
    all_invoice_ids = [row["invoice_id"] for row in records]

    summary = {
        "dataset": {
            "row_count": len(records),
            "settled_invoice_count": len(labeled),
            "open_invoice_count": len(records) - len(labeled),
            "distinct_customer_count": len({row["customer_id"] for row in records}),
            "duplicate_invoice_id_count": len(records) - len(set(all_invoice_ids)),
            "invoice_date_min": min(row["invoice_date"] for row in records).isoformat(),
            "invoice_date_max": max(row["invoice_date"] for row in records).isoformat(),
            "country_codes": sorted({row["country_code"] for row in records}),
            "on_time_invoice_count": sum(1 for row in labeled if row["late"] == 0),
            "late_invoice_count": sum(1 for row in labeled if row["late"] == 1),
            "late_invoice_rate": _mean([float(row["late"]) for row in labeled]),
            "disputed_invoice_count": sum(row["disputed"] == "Yes" for row in dispute_known),
            "dispute_flag_coverage": len(dispute_known) / len(records) if records else 0.0,
            "invoice_amount_min": min(amounts),
            "invoice_amount_median": statistics.median(amounts),
            "invoice_amount_mean": _mean(amounts),
            "invoice_amount_max": max(amounts),
            "invoice_terms_days_min": min(terms_days),
            "invoice_terms_days_median": statistics.median(terms_days),
            "invoice_terms_days_max": max(terms_days),
            "unique_invoice_terms_days": sorted(set(terms_days)),
            "days_late_median": statistics.median(late_days),
            "days_late_p90": late_days[min(len(late_days) - 1, int(math.floor(0.9 * (len(late_days) - 1))))],
            "source_days_late_mismatch_count": source_late_mismatch,
            "source_days_to_settle_mismatch_count": source_dts_mismatch,
            "paperless_bill_counts": {
                value: sum(row["paperless_bill"] == value for row in records)
                for value in sorted({row["paperless_bill"] for row in records})
            },
            "paperless_date_coverage": sum(row["paperless_date"] is not None for row in records) / len(records),
        },
        "split": {
            "method": "chronological invoice-date holdout; never random shuffling",
            "train_fraction_requested": train_fraction,
            "split_date": split_date.isoformat(),
            "train_row_count": len(train),
            "test_row_count": len(test),
            "train_late_rate": train_rate,
            "test_late_rate": _mean([float(value) for value in y_test_late]),
            "distinct_invoice_dates": len(unique_dates),
        },
        "features": FEATURE_POLICY,
        "model": {
            "classification": "logistic regression with L2 regularization and deterministic gradient descent",
            "regression": "ridge linear regression with non-negative clipped predictions",
            "feature_names": feature_names,
            "country_one_hot_columns": country_columns,
            "country_reference_category": baseline_country,
            "standardization_means": means,
            "standardization_standard_deviations": stds,
            "classification_iterations": classifier["iterations"],
            "classification_l2": classifier["l2"],
            "regression_iterations": regressor["iterations"],
            "regression_l2": regressor["l2"],
        },
        "evaluation": {
            "target_late_definition": "settled_date > due_date",
            "prediction_timing": "at invoice issue date, using only history that had settled by then",
            "classification": classification,
            "days_late_regression": regression,
        },
        "limitations": [
            "The source does not expose recorded_at timestamps; historical settlement is assumed observable on its settlement date.",
            "The dataset copy inspected for this project contains only settled invoices. Missing/open invoice outcomes cannot be evaluated from this source copy.",
            "Dispute and paperless columns are excluded because their availability at invoice issue time cannot be proven from this schema.",
            "A chronological invoice-date split is used; customer histories update as prior settlements become observable. The underlying source has no history of edits or data-entry delay.",
            "This benchmark is for model workflow validation, not credit approval, lending, collections execution, or production cash-flow decisions.",
            "Public source terms should be verified before redistribution. The raw dataset is not embedded in this repository.",
        ],
    }
    model_artifact = {
        "artifact_version": "1",
        "model_type": "invoice_late_payment_baseline",
        "split_date": split_date.isoformat(),
        "features": feature_names,
        "country_one_hot_columns": country_columns,
        "country_reference_category": baseline_country,
        "standardization_means": means,
        "standardization_standard_deviations": stds,
        "late_payment_classifier": {
            "bias": classifier["bias"],
            "weights": classifier["weights"],
            "iterations": classifier["iterations"],
            "l2": classifier["l2"],
        },
        "days_late_regressor": {
            "bias": regressor["bias"],
            "weights": regressor["weights"],
            "iterations": regressor["iterations"],
            "l2": regressor["l2"],
        },
        "training_late_rate": train_rate,
        "notes": "Apply only to feature vectors constructed with the documented as-of feature policy. No raw customer records are stored in this model artifact.",
    }
    return summary, model_artifact


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train an invoice late-payment baseline using a chronological holdout."
    )
    parser.add_argument("--data", required=True, type=Path, help="Path to downloaded invoice-payment CSV")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--train-fraction", type=float, default=0.8)
    args = parser.parse_args()

    if not args.data.is_file():
        parser.error(f"CSV file not found: {args.data}")
    try:
        raw_records = read_invoice_csv(args.data)
        records = add_as_of_features(raw_records)
        summary, model_artifact = build_report(raw_records, args.train_fraction)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    summary["source"] = {
        "filename": args.data.name,
        "sha256": sha256_file(args.data),
        "raw_dataset_included": False,
    }
    summary_path = output_dir / f"payment-model-report-{stamp}.json"
    model_path = output_dir / f"payment-model-artifact-{stamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    model_path.write_text(json.dumps(model_artifact, indent=2), encoding="utf-8")

    print("Invoice payment baseline training complete")
    print(f"Rows: {summary['dataset']['row_count']:,}")
    print(f"Customers: {summary['dataset']['distinct_customer_count']:,}")
    print(f"Train/test: {summary['split']['train_row_count']:,} / {summary['split']['test_row_count']:,}")
    print(f"Split date: {summary['split']['split_date']}")
    classification = summary["evaluation"]["classification"]
    print(
        "Late classifier: "
        f"ROC-AUC={classification['roc_auc']:.3f} "
        f"AP={classification['average_precision']:.3f} "
        f"Brier={classification['brier_score']:.3f} "
        f"accuracy={classification['accuracy_at_0_5']:.3f}"
    )
    regression = summary["evaluation"]["days_late_regression"]
    print(
        "Days-late regression: "
        f"MAE={regression['mae_days']:.3f} days "
        f"(median baseline={regression['training_median_days_late_baseline']['mae_days']:.3f})"
    )
    print(f"Report: {summary_path}")
    print(f"Model artifact: {model_path}")


if __name__ == "__main__":
    main()
