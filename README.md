# Bioinformatics Agent Studio

AI-assisted bioinformatics and data analysis workflows with automated report generation.

Each project combines established bioinformatics pipelines (R/Bioconductor, Python/sklearn)
with LLM-powered agents that automate narrative generation, QC review, literature synthesis,
and scientific reporting — while keeping human review at every critical decision point.

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

**Agents**: QC Agent + Report Writer Agent

→ [`projects/01-airway-deseq2/`](projects/01-airway-deseq2/)

---

### 02 — Breast Cancer Classification

Binary classification of breast tumors from digitized cell nucleus measurements,
comparing Logistic Regression and Random Forest.

**Pipeline**: Wisconsin dataset → StandardScaler → 5-fold CV → holdout evaluation → feature importance

**Results**: LR test AUC = 0.996, accuracy = 96.5% | Top features: worst perimeter, worst area, worst concave points

→ [`projects/02-breast-cancer-ml/`](projects/02-breast-cancer-ml/)

---

### 03 — Literature Review: Dexamethasone & Airway Smooth Muscle

Automated PubMed search and structured synthesis of transcriptomic studies on
glucocorticoid action in human airway smooth muscle cells.

**Pipeline**: PubMed search → abstract fetch → Claude synthesis

**Results**: 8 papers (1995–2025) | Key themes: KLF15, CRISPLD2, steroid resistance, lncRNAs, ChIP-Seq

→ [`projects/03-literature-review/`](projects/03-literature-review/)

## Agents

| Agent | Input | Output | What it does | Cost/run |
|---|---|---|---|---|
| QC Agent | `qc_metrics.json` | `qc_report.md` | Flags each sample 🟢🟡🔴 (library size, gene detection, PCA) | ~$0.02 |
| Report Writer | `analysis_summary.json` | `narrative.md` | Executive summary, results interpretation, limitations | ~$0.02 |
| ML Results | `model_summary.json` | `ml_narrative.md` | Model comparison, feature interpretation, limitations | ~$0.02 |
| Literature Review | PubMed query | `literature_review.md` | Searches PubMed, fetches abstracts, structured synthesis | ~$0.05 |

## How to run

```bash
# Setup
conda env create -f environment.yml
conda activate bioagent-r
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Project 01: RNA-seq
cd projects/01-airway-deseq2
Rscript scripts/01_deseq2_analysis.R
cd ../..
python agents/qc_agent.py
python agents/report_writer_agent.py
cd projects/01-airway-deseq2 && quarto render report/report.qmd

# Project 02: ML classifier
python projects/02-breast-cancer-ml/scripts/01_train_classifier.py
python agents/ml_results_agent.py
cd projects/02-breast-cancer-ml && quarto render report/report.qmd

# Project 03: Literature review
python agents/literature_agent.py
```

## Stack

- **R 4.4** + DESeq2, ggplot2, pheatmap, org.Hs.eg.db, Quarto
- **Python 3.14** + anthropic SDK, scikit-learn, pandas, matplotlib, seaborn, requests
- **Claude Sonnet** (via Anthropic API) for all agent outputs
- **conda** for environment management

## Design principles

- Agents are **specialists with constrained outputs**, not autonomous decision-makers
- Scientific conclusions require **human validation** before delivery
- Every analysis is **fully reproducible** from raw inputs
- QC runs **before** analysis — bad samples are flagged, not silently analyzed
- Agent inputs must be **explicit and complete** — no derived calculations from aggregate metrics

## Author

Petros Kogios — MSc Bioinformatics, University of Crete  
[github.com/Lakog9](https://github.com/Lakog9)
