# Bioinformatics Agent Studio

> Production-grade bioinformatics pipelines with AI-assisted reporting — RNA-seq differential expression, ML classification, and automated literature review.

[![Docker](https://img.shields.io/badge/docker-bioagent--studio-blue?logo=docker)](Dockerfile)
[![R](https://img.shields.io/badge/R-4.4-blue?logo=r)](https://www.r-project.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)

## What this is

A self-contained service that takes raw bioinformatics data and produces a fully-formatted HTML scientific report — with statistical analysis, figures, pathway enrichment, AI-generated narrative, and sample-level QC flags — in **under 2 minutes** with a single command.

The pipeline combines established bioinformatics tools (DESeq2, scikit-learn, g:Profiler) with constrained LLM agents (Claude Sonnet) that automate narrative writing, QC review, and literature synthesis — while keeping human review at every critical decision point.

## Quickstart

```bash
docker build -t bioagent-studio .

docker run --rm \
    -v $(pwd)/your_data:/data \
    -v $(pwd)/your_output:/output \
    --env-file .env \
    bioagent-studio \
    --counts /data/counts.csv \
    --metadata /data/metadata.csv \
    --condition treatment \
    --reference control \
    --output /output/
```

That's it. The pipeline runs DESeq2 → pathway enrichment → AI QC agent → AI report writer → Quarto HTML rendering, end-to-end. Output: `your_output/report/report.html`.

## What you get

Each pipeline run produces:

- **Statistical results**: filtered DEG table (padj < 0.05), full DESeq2 RDS objects
- **Publication-quality figures**: PCA, volcano plot, top-DEG heatmap
- **Pathway enrichment**: GO, KEGG, Reactome (415+ terms typical), with Manhattan and dotplot visualizations
- **AI-generated QC report**: per-sample 🟢🟡🔴 flags based on library size, gene detection, PCA outlier status
- **AI-generated scientific narrative**: Executive Summary, Results Interpretation, Limitations — written by a constrained agent that uses only the input JSON, applies standard biological knowledge for interpretation, and never invents data
- **Quarto HTML report**: everything composed into one shareable document

Total agent cost: **~$0.05 per run** (Claude Sonnet API).

## Architecture

```
┌──────────────────┐         ┌──────────────────┐
│  Client inputs   │         │   AI agents      │
│                  │         │ (Claude Sonnet)  │
│  counts.csv      │────┐    │                  │
│  metadata.csv    │    │    │  • QC review     │
└──────────────────┘    │    │  • Narrative gen │
                        ▼    │  • Lit. review   │
              ┌──────────────────┐               │
              │  bioagent CLI    │◄──────────────┘
              │  (Python)        │
              └──────────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
    ┌────────────┐ ┌──────────┐ ┌────────────┐
    │   DESeq2   │ │g:Profiler│ │   Quarto   │
    │ (R / Bioc) │ │   (R)    │ │  (HTML)    │
    └────────────┘ └──────────┘ └────────────┘
                        │
                        ▼
                ┌───────────────┐
                │  HTML report  │
                └───────────────┘
```

**Design principles:**
- AI agents are *constrained specialists*, not autonomous decision-makers
- Agent inputs are explicit JSON — agents never make derived calculations from aggregate metrics
- Scientific conclusions require human validation before delivery
- Every analysis is fully reproducible via Docker

## Demo projects

The repository ships with three demonstration projects:

### Project 01 — Airway RNA-seq Differential Expression
Bulk RNA-seq comparing dexamethasone-treated vs untreated human airway smooth muscle cells (Himes et al. 2014). **Result**: 4,099 DEGs at padj < 0.05, with 415 enriched pathways — cytokine signaling ↓, ECM remodeling ↑ (textbook glucocorticoid response).

→ [`projects/01-airway-deseq2/`](projects/01-airway-deseq2/)

### Project 02 — Breast Cancer Classification
Binary classification (LR vs RF) on Wisconsin Breast Cancer dataset. **Result**: 96.5% accuracy, AUC = 0.996, 3 false negatives on 114-sample holdout. ML agent generates clinically-aware narrative about precision-recall trade-offs.

→ [`projects/02-breast-cancer-ml/`](projects/02-breast-cancer-ml/)

### Project 03 — Literature Review Agent
Given a biological topic, the agent searches PubMed, fetches abstracts, and produces a structured 5-section review (Overview, Key Findings, Methods, Gaps, Next Steps).

→ [`projects/03-literature-review/`](projects/03-literature-review/)

## Agents (4)

| Agent | Generic? | Input | Output | Cost/run |
|---|---|---|---|---|
| QC Agent | ✓ | `qc_metrics.json` | Per-sample 🟢🟡🔴 flags + recommendations | ~$0.02 |
| Report Writer | ✓ | `analysis_summary.json` | Executive Summary, Results, Limitations | ~$0.02 |
| ML Results | ✓ | `model_summary.json` | Methods, Comparison, Feature Interpretation, Limitations | ~$0.03 |
| Literature Review | ✓ | PubMed query | Structured 5-section review of 8 abstracts | ~$0.05 |

All agents are dataset-agnostic: input context flows through JSON, never hardcoded in prompts.

## Running natively (without Docker)

```bash
# Setup
conda env create -f environment.yml
conda activate bioagent-r
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Full pipeline via CLI
python bioagent.py \
    --counts data/counts.csv \
    --metadata data/metadata.csv \
    --condition treatment \
    --reference control \
    --output ./run_output/
```

## Stack

- **R 4.4** + DESeq2, gprofiler2, org.Hs.eg.db, pheatmap, ggplot2
- **Python 3.11+** + Anthropic SDK, scikit-learn, pandas, matplotlib, seaborn
- **Quarto 1.5** for HTML report rendering
- **Claude Sonnet** (via Anthropic API) for all agent outputs
- **Docker** + Bioconductor base image for portable deployment

## Input format

**`counts.csv`** — gene counts matrix:
```
gene_id,SRR1039508,SRR1039509,SRR1039512,...
ENSG00000000003,679,448,873,...
ENSG00000000419,467,515,621,...
```

**`metadata.csv`** — sample annotations:
```
sample_id,condition,batch
SRR1039508,control,N61311
SRR1039509,treated,N61311
SRR1039512,control,N052611
```

The pipeline validates inputs (file existence, column presence, sample ID matching, reference level) before any analysis runs and exits with clear error messages on failure.

## Limitations

- Gene symbol annotation requires human Ensembl IDs (auto-skips for other organisms)
- LLM-generated narratives are subject to standard limitations of large language models — outputs are designed for *first-draft acceleration*, not unreviewed delivery
- Single-condition contrasts only (multi-factor designs supported via batch covariates)
- Clinical or regulatory applications require additional validation and compliance work beyond what this repo provides

## Author

**Petros Kogios** — MSc Bioinformatics, University of Crete  
[github.com/Lakog9](https://github.com/Lakog9)
