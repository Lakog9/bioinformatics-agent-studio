#!/usr/bin/env python3
"""
Breast Cancer Classification — Logistic Regression vs Random Forest
====================================================================
Trains and evaluates two classifiers on the Wisconsin Breast Cancer dataset
(569 samples, 30 features, binary classification: malignant vs benign).

Includes:
- Stratified 5-fold cross-validation
- Train/test holdout for final evaluation
- ROC curves, confusion matrices, feature importance
- Summary JSON for the ML Agent

Usage:
    python projects/02-breast-cancer-ml/scripts/01_train_classifier.py
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, roc_auc_score, roc_curve, confusion_matrix,
    classification_report, precision_score, recall_score, f1_score
)

# ============================================
# Paths
# ============================================
BASE = Path(__file__).parent.parent
FIG_DIR = BASE / "results" / "figures"
METRICS_DIR = BASE / "results" / "metrics"
DATA_DIR = BASE / "data"

for d in [FIG_DIR, METRICS_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# ============================================
# 1. Load data
# ============================================
print("=" * 50)
print("  Breast Cancer Classification")
print("=" * 50)

print("\n[1/6] Loading Wisconsin Breast Cancer dataset...")
data = load_breast_cancer()
X = pd.DataFrame(data.data, columns=data.feature_names)
y = pd.Series(data.target, name="diagnosis")

# Note: in sklearn convention, target=1 means BENIGN, target=0 means MALIGNANT
# We invert so 1 = malignant (positive class = disease)
y = 1 - y

print(f"  Samples:       {X.shape[0]}")
print(f"  Features:      {X.shape[1]}")
print(f"  Class balance: {sum(y == 1)} malignant / {sum(y == 0)} benign")

# ============================================
# 2. Train/test split (80/20, stratified)
# ============================================
print("\n[2/6] Train/test split (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
)
print(f"  Train: {X_train.shape[0]} samples")
print(f"  Test:  {X_test.shape[0]} samples")

# ============================================
# 3. Define models (pipelines with scaling)
# ============================================
models = {
    "logistic_regression": Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=5000, random_state=RANDOM_STATE))
    ]),
    "random_forest": Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
        ))
    ])
}

# ============================================
# 4. 5-fold stratified cross-validation
# ============================================
print("\n[3/6] 5-fold stratified cross-validation...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
cv_results = {}

for name, model in models.items():
    scores = cross_val_score(model, X_train, y_train, cv=cv,
                              scoring="roc_auc", n_jobs=-1)
    cv_results[name] = {
        "mean_auc": float(scores.mean()),
        "std_auc": float(scores.std()),
        "fold_aucs": [float(s) for s in scores]
    }
    print(f"  {name:25s}  AUC = {scores.mean():.4f} ± {scores.std():.4f}")

# ============================================
# 5. Train final models, evaluate on holdout
# ============================================
print("\n[4/6] Training final models on full train set...")
test_results = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    test_results[name] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "auc": float(roc_auc_score(y_test, y_proba)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "y_pred": y_pred.tolist(),
        "y_proba": y_proba.tolist()
    }

    print(f"  {name:25s}  test AUC={test_results[name]['auc']:.4f}  "
          f"accuracy={test_results[name]['accuracy']:.4f}")

# ============================================
# 6. Figures
# ============================================
print("\n[5/6] Generating figures...")

# --- ROC curves ---
fig, ax = plt.subplots(figsize=(7, 6))
for name in models:
    fpr, tpr, _ = roc_curve(y_test, test_results[name]["y_proba"])
    auc = test_results[name]["auc"]
    ax.plot(fpr, tpr, label=f"{name} (AUC = {auc:.3f})", linewidth=2)

ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves — Test Set")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG_DIR / "01_roc_curves.png", dpi=300)
plt.close()

# --- Confusion matrices ---
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, (name, _) in zip(axes, models.items()):
    cm = np.array(test_results[name]["confusion_matrix"])
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["Benign", "Malignant"],
                yticklabels=["Benign", "Malignant"], cbar=False)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"{name}\nAccuracy = {test_results[name]['accuracy']:.3f}")
plt.tight_layout()
plt.savefig(FIG_DIR / "02_confusion_matrices.png", dpi=300)
plt.close()

# --- Feature importance (Random Forest) ---
rf_model = models["random_forest"].named_steps["clf"]
importances = pd.Series(rf_model.feature_importances_, index=X.columns)
top15 = importances.sort_values(ascending=True).tail(15)

fig, ax = plt.subplots(figsize=(8, 7))
top15.plot(kind="barh", ax=ax, color="steelblue")
ax.set_xlabel("Feature Importance (Gini)")
ax.set_title("Top 15 Features — Random Forest")
plt.tight_layout()
plt.savefig(FIG_DIR / "03_feature_importance.png", dpi=300)
plt.close()

print(f"  Saved: {FIG_DIR}/")

# ============================================
# 7. Save metrics & JSON summary
# ============================================
print("\n[6/6] Saving metrics and summary...")

# Full classification reports as JSON
reports = {}
for name, model in models.items():
    y_pred = model.predict(X_test)
    reports[name] = classification_report(y_test, y_pred,
        target_names=["benign", "malignant"], output_dict=True)

with open(METRICS_DIR / "classification_reports.json", "w") as f:
    json.dump(reports, f, indent=2)

# Top features for the agent context
top10_features = importances.sort_values(ascending=False).head(10)

# Summary JSON for the ML Agent
summary = {
    "dataset": "Wisconsin Breast Cancer (sklearn)",
    "task": "Binary classification: malignant vs benign",
    "n_samples_total": int(X.shape[0]),
    "n_samples_train": int(X_train.shape[0]),
    "n_samples_test": int(X_test.shape[0]),
    "n_features": int(X.shape[1]),
    "class_distribution": {
        "malignant": int(sum(y == 1)),
        "benign": int(sum(y == 0))
    },
    "cross_validation": {
        "method": "Stratified 5-fold",
        "metric": "ROC AUC",
        "results": cv_results
    },
    "test_set_performance": {
        name: {
            "accuracy": test_results[name]["accuracy"],
            "auc": test_results[name]["auc"],
            "precision": test_results[name]["precision"],
            "recall": test_results[name]["recall"],
            "f1": test_results[name]["f1"]
        }
        for name in models
    },
    "top10_features_random_forest": {
        name: float(imp) for name, imp in top10_features.items()
    },
    "best_model": max(test_results, key=lambda k: test_results[k]["auc"]),
    "random_state": RANDOM_STATE
}

with open(DATA_DIR / "model_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"  Saved: {DATA_DIR}/model_summary.json")
print(f"  Saved: {METRICS_DIR}/classification_reports.json")

print("\n" + "=" * 50)
print(f"  DONE  |  Best model: {summary['best_model']}")
print("=" * 50)
