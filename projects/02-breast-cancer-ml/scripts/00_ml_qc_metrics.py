#!/usr/bin/env python3
"""
ML QC Metrics Generator
=======================
Computes pre-training quality-control metrics for a classification dataset
and writes them to JSON for the ML QC Agent to interpret.

Checks performed:
  - Class balance / imbalance ratio
  - Missing values (per-feature and total)
  - Feature scale disparity
  - Constant / near-constant features
  - Highly correlated feature pairs
  - Outlier prevalence (IQR-based)
  - Potential data leakage (features near-perfectly correlated with target)

Usage:
    python 00_ml_qc_metrics.py [--output <path>]

By default, runs on the sklearn Wisconsin Breast Cancer dataset (the demo).
To use your own data, edit the load_dataset() function.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_dataset():
    """Load the demo dataset. Returns (X dataframe, y series, target_name)."""
    from sklearn.datasets import load_breast_cancer
    data = load_breast_cancer(as_frame=True)
    X = data.data
    y = data.target  # 0 = malignant, 1 = benign
    return X, y, "diagnosis"


def compute_class_balance(y):
    counts = y.value_counts().sort_index()
    total = len(y)
    classes = {str(k): int(v) for k, v in counts.items()}
    minority = int(counts.min())
    majority = int(counts.max())
    imbalance_ratio = round(majority / minority, 2) if minority > 0 else None
    return {
        "n_samples": int(total),
        "n_classes": int(y.nunique()),
        "class_counts": classes,
        "minority_class_size": minority,
        "majority_class_size": majority,
        "imbalance_ratio": imbalance_ratio,
        "minority_pct": round(100 * minority / total, 2)
    }


def compute_missing(X):
    missing_per_col = X.isna().sum()
    cols_with_missing = missing_per_col[missing_per_col > 0]
    total_cells = X.shape[0] * X.shape[1]
    total_missing = int(missing_per_col.sum())
    return {
        "total_missing_cells": total_missing,
        "pct_missing": round(100 * total_missing / total_cells, 4) if total_cells else 0,
        "n_features_with_missing": int((missing_per_col > 0).sum()),
        "features_with_missing": {k: int(v) for k, v in cols_with_missing.items()}
    }


def compute_scale_disparity(X):
    numeric = X.select_dtypes(include=[np.number])
    ranges = numeric.max() - numeric.min()
    ranges = ranges[ranges > 0]
    if len(ranges) == 0:
        return {"max_range": 0, "min_range": 0, "scale_ratio": None}
    max_range = float(ranges.max())
    min_range = float(ranges.min())
    return {
        "max_feature_range": round(max_range, 2),
        "min_feature_range": round(min_range, 4),
        "scale_ratio": round(max_range / min_range, 1) if min_range > 0 else None,
        "largest_range_feature": str(ranges.idxmax()),
        "smallest_range_feature": str(ranges.idxmin())
    }


def compute_constant_features(X):
    numeric = X.select_dtypes(include=[np.number])
    nunique = numeric.nunique()
    constant = nunique[nunique <= 1].index.tolist()
    # near-constant: one value dominates >99% of rows
    near_constant = []
    for col in numeric.columns:
        top_freq = numeric[col].value_counts(normalize=True, dropna=True)
        if len(top_freq) > 0 and top_freq.iloc[0] > 0.99 and col not in constant:
            near_constant.append(col)
    return {
        "n_constant": len(constant),
        "constant_features": constant,
        "n_near_constant": len(near_constant),
        "near_constant_features": near_constant
    }


def compute_correlated_pairs(X, threshold=0.95):
    numeric = X.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {"n_high_corr_pairs": 0, "high_corr_pairs": []}
    corr = numeric.corr().abs()
    pairs = []
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = corr.iloc[i, j]
            if c >= threshold:
                pairs.append({
                    "feature_a": str(cols[i]),
                    "feature_b": str(cols[j]),
                    "correlation": round(float(c), 3)
                })
    pairs.sort(key=lambda p: -p["correlation"])
    return {
        "threshold": threshold,
        "n_high_corr_pairs": len(pairs),
        "high_corr_pairs": pairs[:15]  # cap for readability
    }


def compute_outliers(X):
    numeric = X.select_dtypes(include=[np.number])
    outlier_summary = {}
    total_outlier_cells = 0
    for col in numeric.columns:
        q1, q3 = numeric[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((numeric[col] < lower) | (numeric[col] > upper)).sum())
        if n_out > 0:
            outlier_summary[col] = n_out
            total_outlier_cells += n_out
    # features with the most outliers
    top = dict(sorted(outlier_summary.items(), key=lambda kv: -kv[1])[:10])
    return {
        "total_outlier_cells": total_outlier_cells,
        "pct_outlier_cells": round(100 * total_outlier_cells /
                                   (numeric.shape[0] * numeric.shape[1]), 3),
        "n_features_with_outliers": len(outlier_summary),
        "top_outlier_features": {k: int(v) for k, v in top.items()}
    }


def compute_leakage_risk(X, y, threshold=0.98):
    """Flag features near-perfectly correlated with the target."""
    numeric = X.select_dtypes(include=[np.number])
    suspicious = []
    y_numeric = pd.to_numeric(y, errors="coerce")
    for col in numeric.columns:
        c = numeric[col].corr(y_numeric)
        if pd.notna(c) and abs(c) >= threshold:
            suspicious.append({"feature": str(col), "correlation_with_target": round(float(c), 4)})
    return {
        "threshold": threshold,
        "n_suspicious_features": len(suspicious),
        "suspicious_features": suspicious
    }


def main():
    parser = argparse.ArgumentParser(description="Generate ML QC metrics JSON")
    parser.add_argument("--output", default="data/ml_qc_metrics.json",
                        help="Output JSON path")
    args = parser.parse_args()

    print("=" * 40)
    print("  ML QC Metrics Generator")
    print("=" * 40)

    print("\n[1/3] Loading dataset...")
    X, y, target_name = load_dataset()
    print(f"  Shape: {X.shape[0]} samples x {X.shape[1]} features")
    print(f"  Target: {target_name}")

    print("\n[2/3] Computing QC metrics...")
    metrics = {
        "dataset_shape": {"n_samples": int(X.shape[0]), "n_features": int(X.shape[1])},
        "target_name": target_name,
        "class_balance": compute_class_balance(y),
        "missing_values": compute_missing(X),
        "scale_disparity": compute_scale_disparity(X),
        "constant_features": compute_constant_features(X),
        "correlated_features": compute_correlated_pairs(X),
        "outliers": compute_outliers(X),
        "leakage_risk": compute_leakage_risk(X, y),
    }
    print(f"  Class imbalance ratio: {metrics['class_balance']['imbalance_ratio']}")
    print(f"  Missing cells:         {metrics['missing_values']['total_missing_cells']}")
    print(f"  Constant features:     {metrics['constant_features']['n_constant']}")
    print(f"  High-corr pairs:       {metrics['correlated_features']['n_high_corr_pairs']}")
    print(f"  Leakage-risk features: {metrics['leakage_risk']['n_suspicious_features']}")

    print("\n[3/3] Writing JSON...")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Saved: {out_path}")

    print(f"\n{'=' * 40}")
    print("  DONE")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
