# Breast Cancer Classification — Logistic Regression vs Random Forest

Binary classification of breast tumors (malignant vs benign) from digitized
fine needle aspirate measurements, comparing Logistic Regression and Random Forest.

## Dataset

Wisconsin Breast Cancer Dataset (UCI / sklearn built-in):

- **Samples**: 569 (212 malignant, 357 benign)
- **Features**: 30 numerical (mean, SE, and worst values for 10 cell nucleus measurements)
- **Task**: binary classification — malignant (1) vs benign (0)
- **Split**: 80/20 stratified train/test

## Methods

Both models wrapped in sklearn pipelines with StandardScaler preprocessing.

- **Logistic Regression**: L2 penalty, max_iter=5000
- **Random Forest**: 200 estimators, n_jobs=-1
- **Validation**: stratified 5-fold cross-validation (ROC AUC)
- **Final evaluation**: holdout test set (20%)

## Results

### Cross-validation (train set, 5-fold, ROC AUC)

| Model | Mean AUC | Std |
|---|---|---|
| Logistic Regression | **0.9958** | ±0.0047 |
| Random Forest | 0.9889 | ±0.0070 |

### Test set performance

| Model | AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | **0.9960** | 0.9649 | 0.975 | 0.929 | 0.951 |
| Random Forest | 0.9942 | 0.9649 | 0.950 | 0.905 | 0.927 |

### Confusion matrices (test set, n=114)

**Logistic Regression**

|  | Predicted Benign | Predicted Malignant |
|---|---|---|
| Actual Benign | 71 | 1 |
| Actual Malignant | **3** | 39 |

**Random Forest**

|  | Predicted Benign | Predicted Malignant |
|---|---|---|
| Actual Benign | 72 | 0 |
| Actual Malignant | **4** | 38 |

In a screening context, false negatives (missed malignancies) are more costly than
false positives. Logistic Regression misses 3 malignancies vs 4 for Random Forest,
making it the preferred model here despite identical overall accuracy.

### ROC Curves

![ROC](results/figures/01_roc_curves.png)

### Feature Importance (Random Forest)

![Feature Importance](results/figures/03_feature_importance.png)

Top predictors — `worst perimeter`, `worst area`, `worst concave points` — are
consistent with known cytopathological criteria for malignancy: larger, more
irregular nuclei with concave contours.

## Key takeaways

- Logistic Regression outperforms Random Forest on this dataset despite being simpler
- "Worst" (most extreme) measurements are more predictive than mean measurements
- Cell nucleus size and shape irregularity (concave points) are the dominant features
- Both models achieve AUC > 0.99 — suitable as a decision support tool

## Reproducibility

```bash
conda activate bioagent-r
python projects/02-breast-cancer-ml/scripts/01_train_classifier.py
```

## Reference

Street WN, Wolberg WH, Mangasarian OL. *Nuclear feature extraction for breast
tumor diagnosis.* IS&T/SPIE Int Symp Electronic Imaging. 1993;1905:861-870.
