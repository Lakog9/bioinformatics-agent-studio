# Bioinformatics Agent Studio

AI-assisted bioinformatics and data analysis workflows with automated report generation.

Each project combines established bioinformatics pipelines (R/Bioconductor, Python/sklearn)
with LLM-powered agents that automate narrative generation, QC review, and
scientific reporting — while keeping human review at every critical decision point.

## What this is

A portfolio of reproducible analysis workflows where:

- **R/Python pipelines** handle the statistical analysis
- **AI agents** automate narrative writing, QC flagging, and report generation
- **Quarto** produces publication-ready HTML/PDF reports
- **Human review** remains mandatory before any delivery

## Projects

### 01 — Airway RNA-seq Differential Expression

Bulk RNA-seq analysis comparing dexamethasone-treated vs untreated human airway
smooth muscle cells (Himes et al. 2014).

**Pipeline**: count matrix → DESeq2 → gene symbols → PCA + volcano + heatmap → report

**Results**: 4,099 DEGs at padj < 0.05 | Top genes: SPARCL1, CACNB2, DUSP1, SAMHD1, MAOA

**Agents**: QC Agent (sample flagging) + Report Writer Agent (narrative generation)

→ [`projects/01-airway-deseq2/`](projects/01-airway-deseq2/)

---

### 02 — Breast Cancer Classification

Binary classification of breast tumors (malignant vs benign) from digitized cell
nucleus measurements, comparing Logistic Regression and Random Forest.

**Pipeline**: Wisconsin dataset → StandardScaler → 5-fold CV → holdout evaluation → feature importance

**Results**: LR test AUC = 0.996, accuracy = 96.5% | Top features: worst perimeter, worst area, worst concave points

**Key finding**: Logistic Regression outperforms Random Forest despite lower complexity —
"worst" (most extreme) nucleus measurements dominate over mean measurements.

→ [`projects/02-breast-cancer-ml/`](projects/02-breast-cancer-ml/)

## Agents

| Agent | Input | Output | What it does | Cost/run |
|---|---|---|---|---|
| QC Agent | `qc_metrics.json` | `qc_report.md` | Flags each sample 🟢🟡🔴 based on library size, gene detection, PCA outlier status | ~$0.02 |
| Report Writer | `analysis_summary.json` | `narrative.md` | Generates executive summary, results interpretation, limitations | ~$0.02 |

*More agents in development: ML Results Agent, Literature Review Agent*

## How to run

```bash
# Setup
conda env create -f environment.yml
conda activate bioagent-r
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Project 01: RNA-seq
cd projects/01-airway-deseq2
Rscript scripts/01_deseq2_analysis.R     # ~2 min
cd ../..
python agents/qc_agent.py               # ~10 sec, ~$0.02
python agents/report_writer_agent.py    # ~10 sec, ~$0.02
cd projects/01-airway-deseq2
quarto render report/report.qmd         # ~1 min

# Project 02: ML classifier
python projects/02-breast-cancer-ml/scripts/01_train_classifier.py  # ~30 sec
```

## Stack

- **R 4.4** + DESeq2, ggplot2, pheatmap, org.Hs.eg.db, Quarto
- **Python 3.14** + anthropic SDK, scikit-learn, pandas, matplotlib, seaborn
- **Claude Sonnet** (via Anthropic API) for report and QC narrative generation
- **conda** for environment management

## Design principles

- Agents are **specialists with constrained outputs**, not autonomous decision-makers
- Scientific conclusions require **human validation** before delivery
- Every analysis is **fully reproducible** from raw inputs
- QC runs **before** analysis — bad samples are flagged, not silently analyzed
- Narrative generation enforces **scientific writing guardrails**
  (no causality claims, distinguishes statistical from biological significance)

## Author

Petros Kogios — MSc Bioinformatics, University of Crete  
[github.com/Lakog9](https://github.com/Lakog9)
