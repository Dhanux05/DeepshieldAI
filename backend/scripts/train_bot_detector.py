"""
Train the Phase 10 bot-vs-human account classifier.

Usage (run from backend/, with requirements/ml.txt installed):
    python -m scripts.train_bot_detector --csv path/to/training_data_2_csv_UTF.csv

Dataset: `training_data_2_csv_UTF.csv` (2,797 labelled Twitter accounts,
balanced: 1,476 human / 1,321 bot), a well-known account-metadata dataset
used across multiple public bot-detection tutorials/projects. Source
verified account-by-account before use: see the accompanying handoff
notes for provenance and why the dataset's own `test_data_4_students.csv`
was NOT used (that file's `bot` column is entirely blank — it was set up
as an unlabelled class-assignment file, not a real held-out test set — so
this script draws its own train/val/test split from the labelled file
instead).

What this script does, in order:
1. Load the CSV (utf-8-sig — the file ships with a UTF-8 BOM).
2. Drop duplicate accounts (365 of 2,797 rows are exact `id_str` repeats).
3. Run every row through `app.ml.bot_preprocessing.extract_features` — the
   EXACT SAME function `bot_detector.py` calls at serve time.
4. Stratified 70/15/15 train/val/test split (fixed random_state — the split
   is reproducible, not cherry-picked).
5. Train an XGBoost classifier with early stopping on the validation set.
6. Evaluate once, on the held-out test set only, and write the real numbers
   (accuracy/precision/recall/F1/ROC-AUC/confusion matrix) to
   `training_report.md` next to the model — never hand-typed into a report.
7. Save the model (`bot_xgb_model.json`, XGBoost's native JSON format — no
   pickle) and `feature_schema.json` (feature order + imputation constants
   `bot_detector.py` needs at serve time).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# Allow `from app.ml... import ...` when this script is run directly
# (`python scripts/train_bot_detector.py`) rather than as a module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.bot_preprocessing import (  # noqa: E402
    FEATURE_ORDER,
    extract_features,
    parse_account_datetime,
)

LABEL_NAMES = {0: "Human", 1: "Bot"}


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig", on_bad_lines="skip")

    before = len(df)
    df = df.drop_duplicates(subset="id_str", keep="first").reset_index(drop=True)
    dropped = before - len(df)
    print(f"Loaded {before} rows, dropped {dropped} duplicate accounts -> {len(df)} rows.")

    df = df.dropna(subset=["bot"]).reset_index(drop=True)
    df["bot"] = df["bot"].astype(int)

    return df


def compute_reference_date(df: pd.DataFrame) -> datetime:
    """
    "Now", for training purposes: the latest successfully-parsed
    `created_at` in the dataset, standing in for roughly when this dataset
    was collected. See bot_preprocessing.py's module docstring, decision
    (1), for why this must NOT be a hardcoded date.
    """
    parsed = df["created_at"].apply(parse_account_datetime).dropna()
    if parsed.empty:
        raise ValueError("Could not parse a single created_at value — check the CSV format.")
    return max(parsed.tolist())


def build_feature_matrix(
    df: pd.DataFrame,
    reference_date: datetime,
    age_fallback_days: float,
) -> pd.DataFrame:
    records = [
        extract_features(
            row.to_dict(),
            reference_date=reference_date,
            account_age_fallback_days=age_fallback_days,
        )
        for _, row in df.iterrows()
    ]
    return pd.DataFrame.from_records(records, columns=FEATURE_ORDER)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to training_data_2_csv_UTF.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "models" / "bot",
        help="Where to write bot_xgb_model.json + feature_schema.json",
    )
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(args.csv)
    reference_date = compute_reference_date(df)
    print(f"Reference date for training-time account age: {reference_date.isoformat()}")

    # Median age computed on rows with a PARSEABLE created_at, so the
    # fallback used for the unparseable ones isn't itself contaminated by
    # them defaulting to 0 (see extract_features's account_age_fallback_days).
    parsed_ages_days = (
        df["created_at"]
        .apply(parse_account_datetime)
        .dropna()
        .apply(lambda dt: max((reference_date - dt).total_seconds() / 86400.0, 0.0))
    )
    age_fallback_days = float(parsed_ages_days.median())

    X = build_feature_matrix(df, reference_date, age_fallback_days)
    y = df["bot"].to_numpy()

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=args.random_state
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=args.random_state
    )
    print(
        f"Split -> train={len(X_train)} val={len(X_val)} test={len(X_test)} "
        f"(train bot-rate={y_train.mean():.3f}, test bot-rate={y_test.mean():.3f})"
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        early_stopping_rounds=20,
        random_state=args.random_state,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }
    cm = confusion_matrix(y_test, y_pred).tolist()

    print("\n--- Test-set metrics (n=%d, never seen during training) ---" % len(y_test))
    for name, value in metrics.items():
        print(f"  {name:>10}: {value:.4f}")
    print(f"  confusion matrix [[TN, FP], [FN, TP]]: {cm}")

    model_path = args.output_dir / "bot_xgb_model.json"
    model.save_model(str(model_path))

    schema = {
        "feature_order": FEATURE_ORDER,
        "label_names": LABEL_NAMES,
        "decision_threshold": 0.5,
        "account_age_fallback_days": age_fallback_days,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_source": str(args.csv.name),
        "dataset_rows_used": len(df),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
        "test_metrics": metrics,
        "test_confusion_matrix": cm,
    }
    schema_path = args.output_dir / "feature_schema.json"
    schema_path.write_text(json.dumps(schema, indent=2))

    report_lines = [
        "# Bot Detector Training Report",
        "",
        f"Trained: {schema['trained_at']}",
        f"Dataset: `{schema['dataset_source']}` ({schema['dataset_rows_used']} rows after de-duplication)",
        f"Split: train={schema['train_rows']} / val={schema['val_rows']} / test={schema['test_rows']}",
        "",
        "## Test-set metrics (held out, never used for training or early stopping)",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for name, value in metrics.items():
        report_lines.append(f"| {name} | {value:.4f} |")
    report_lines += [
        "",
        f"Confusion matrix `[[TN, FP], [FN, TP]]`: `{cm}`",
        "",
        "## Known limitations",
        "",
        "- \"Sentiment\" is bio (profile description) sentiment via VADER, not "
        "tweet sentiment — the dataset's per-tweet `status` field is too "
        "inconsistently formatted across rows to parse reliably (see "
        "app/ml/bot_preprocessing.py's module docstring).",
        "- Account age is computed relative to a training-time reference "
        "date derived from this dataset's own timestamps (~the dataset's "
        "collection time), not a hardcoded date — see the same docstring, "
        "decision (1), for why that matters at serve time.",
        f"- {(df['created_at'].apply(parse_account_datetime).isna()).sum()} of "
        f"{len(df)} accounts had an unparseable `created_at` and fall back to "
        f"the training set's median age ({age_fallback_days:.1f} days).",
    ]
    (args.output_dir / "training_report.md").write_text("\n".join(report_lines))

    print(f"\nSaved model -> {model_path}")
    print(f"Saved feature schema -> {schema_path}")
    print(f"Saved report -> {args.output_dir / 'training_report.md'}")


if __name__ == "__main__":
    main()
