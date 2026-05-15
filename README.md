# Bioinformatics Agent Studio

AI-assisted bioinformatics and data analysis workflows with automated report generation.

Each project combines established bioinformatics pipelines (R/Bioconductor, Python)
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

**Pipeline**: count matrix → DESeq2 → PCA + volcano + heatmap → report

**Results**: 4,099 DEGs at padj < 0.05 (2,201 up / 1,898 down)

**Top genes**: SPARCL1, CACNB2, DUSP1, SAMHD1, MAOA

**Agents used**:
- QC Agent → automated sample flagging before analysis
- Report Writer Agent → auto-generated scientific narrative

→ [`projects/01-airway-deseq2/`](projects/01-airway-deseq2/)

## Agents

| Agent | Input | Output | What it does | Cost/run |
|---|---|---|---|---|
| QC Agent | `qc_metrics.json` | `qc_report.md` | Flags each sample 🟢🟡🔴 based on library size, gene detection, PCA outlier status | ~$0.02 |
| Report Writer | `analysis_summary.json` | `narrative.md` | Generates executive summary, results interpretation, limitations | ~$0.02 |

*More agents in development: ML Classifier Agent, Literature Review Agent*

## How to run

```bash
# 1. Set up environment
conda env create -f environment.yml
conda activate bioagent-r

# 2. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# 3. Run a project (example: airway DESeq2)
cd projects/01-airway-deseq2
Rscript scripts/01_deseq2_analysis.R     # ~2 min — analysis + QC metrics + summary JSON

cd ../..
python agents/qc_agent.py               # ~10 sec, ~$0.02 — QC flags per sample
python agents/report_writer_agent.py    # ~10 sec, ~$0.02 — scientific narrative

cd projects/01-airway-deseq2
quarto render report/report.qmd         # ~1 min — final HTML report
```

Output: `projects/01-airway-deseq2/report/report.html`

## Stack

- **R 4.4** + DESeq2, ggplot2, pheatmap, org.Hs.eg.db, Quarto
- **Python 3.14** + anthropic SDK, python-dotenv
- **Claude Sonnet** (via Anthropic API) for narrative and QC report generation
- **conda** for environment management
- **git** for version control

## Design principles

- Agents are **specialists with constrained outputs**, not autonomous decision-makers
- Scientific conclusions require **human validation** before delivery
- Every analysis is **fully reproducible** from raw inputs
- Narrative generation enforces **scientific writing guardrails**
  (no causality claims, distinguishes statistical from biological significance)
- QC runs **before** analysis — bad samples are flagged, not silently analyzed

## Author

Petros Kogios — MSc Bioinformatics, University of Crete  
[github.com/Lakog9](https://github.com/Lakog9)
