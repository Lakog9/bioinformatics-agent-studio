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

**Agent used**: Report Writer Agent → auto-generated executive summary,
results interpretation, and limitations section

→ [`projects/01-airway-deseq2/`](projects/01-airway-deseq2/)

## Agents

| Agent | Input | Output | Cost/run |
|---|---|---|---|
| Report Writer | `analysis_summary.json` | `narrative.md` | ~$0.02 |

*More agents in development: QC Agent, ML Classifier Agent, Literature Review Agent*

## How to run

```bash
# 1. Set up environment
conda env create -f environment.yml
conda activate bioagent-r

# 2. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# 3. Run a project (example: airway DESeq2)
cd projects/01-airway-deseq2
Rscript scripts/01_deseq2_analysis.R     # ~2 min
cd ../..
python agents/report_writer_agent.py     # ~10 sec, ~$0.02
cd projects/01-airway-deseq2
quarto render report/report.qmd          # ~1 min
```

Output: `projects/01-airway-deseq2/report/report.html`

## Stack

- **R 4.4** + DESeq2, ggplot2, pheatmap, Quarto
- **Python 3.14** + anthropic SDK, python-dotenv
- **Claude Sonnet** (via Anthropic API) for narrative generation
- **conda** for environment management
- **git** for version control

## Design principles

- Agents are **specialists with constrained outputs**, not autonomous decision-makers
- Scientific conclusions require **human validation** before delivery
- Every analysis is **fully reproducible** from raw inputs
- Narrative generation enforces **scientific writing guardrails**
  (no causality claims, distinguishes statistical from biological significance)

## Author

Petros Kogios — MSc Bioinformatics, University of Crete  
[github.com/Lakog9](https://github.com/Lakog9)
