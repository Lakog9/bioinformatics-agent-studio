# Client Guide — RNA-seq Differential Expression Analysis

A practical guide to commissioning an RNA-seq differential expression analysis
through Bioinformatics Agent Studio: what you provide, what you receive, how
the process works, and how your data is handled.

---

## 1. What this service does

You provide a gene count matrix from a bulk RNA-seq experiment. You receive a
complete, formatted analysis report — differential expression results, quality
control, figures, pathway enrichment, and a written scientific narrative.

The analysis is performed with established, peer-reviewed tools (DESeq2,
g:Profiler). The written sections are drafted by AI agents operating under
strict constraints and are reviewed by a human analyst before delivery.

This service is suited to standard two-group bulk RNA-seq comparisons (e.g.
treated vs control). It is **not** a substitute for a dedicated bioinformatics
core for complex experimental designs — see Section 6.

---

## 2. What you receive

A single self-contained HTML report containing:

- **Executive summary** — the headline findings in plain scientific language
- **Methods** — a precise, publication-ready methods paragraph with exact tool
  versions, statistical model, thresholds, and filtering criteria
- **Quality control** — a per-sample assessment flagging any problematic libraries
- **Differential expression results** — number of significant genes, direction,
  effect sizes; PCA, volcano plot, and a heatmap of top genes
- **Pathway enrichment** — enriched GO, KEGG, and Reactome terms (human datasets)
- **Results interpretation** — what the findings mean, with appropriate caveats
- **Limitations** — an honest statement of what the analysis can and cannot support

You also receive the underlying data tables (the full differentially expressed
gene list as CSV) and all figures as separate files.

---

## 3. What you provide

Two files, in plain CSV format.

### 3.1 Count matrix — `counts.csv`

Raw gene counts. First column is the gene identifier; every other column is one
sample.

```
gene_id,sample_A1,sample_A2,sample_B1,sample_B2
ENSG00000000003,679,448,873,512
ENSG00000000419,467,515,621,488
ENSG00000000457,260,211,304,279
```

Requirements:
- **Raw integer counts** — not normalized values (no TPM, FPKM, CPM), not
  log-transformed data. This is essential; normalized data produces invalid results.
- Gene identifiers should be consistent (Ensembl IDs preferred for human data,
  which enables gene-symbol annotation and pathway enrichment).
- At least 2 samples per group; 3 or more per group is strongly recommended.

### 3.2 Sample metadata — `metadata.csv`

One row per sample. Must include a `sample_id` column matching the sample column
names in the count matrix exactly.

```
sample_id,condition,batch
sample_A1,control,run1
sample_A2,control,run2
sample_B1,treated,run1
sample_B2,treated,run2
```

Requirements:
- A `sample_id` column whose values match the count matrix columns one-to-one.
- A column defining the comparison (e.g. `condition`).
- Optionally, columns for known batch effects (e.g. `batch`, `cell_line`) — these
  are used as covariates to control for unwanted variation.

### 3.3 What you tell us

Alongside the files, three pieces of information:
- Which metadata column defines the comparison.
- Which value of that column is the reference (control) group.
- Which columns, if any, are batch covariates.

---

## 4. The process

1. **Intake** — you send the two files and the three details above. We confirm
   the data passes validation (correct format, matching sample IDs, sufficient
   replicates). If something is off, we tell you exactly what, before any work begins.
2. **Analysis** — the pipeline runs differential expression, quality control,
   pathway enrichment, and report generation. Compute time is minutes.
3. **Human review** — a qualified analyst reviews every generated section for
   accuracy and appropriate interpretation. The AI-generated narrative is treated
   as a first draft, never as final unreviewed output.
4. **Delivery** — you receive the HTML report and data files, plus a short
   summary of any analyst notes or recommendations.
5. **Follow-up** — one round of clarification or minor adjustment is included.

Typical turnaround is short — the bottleneck is review and communication, not
computation.

---

## 5. How your data is handled

This section is deliberately specific, because it matters.

- **The count matrix and metadata are processed locally** (in a containerized
  environment). Raw counts are not transmitted to any third-party API.
- **Aggregate results are processed by an AI service.** To generate the written
  narrative, summary statistics — gene counts, gene symbols of top hits, fold
  changes, enrichment terms, QC metrics — are sent to the Anthropic Claude API.
  This is *derived, aggregate information*, not your raw data.
- **De-identified data is strongly recommended.** Sample identifiers should not
  contain patient names, medical record numbers, or other personal identifiers.
  Use coded sample labels (e.g. `sample_A1`).
- **If your data is subject to specific regulatory requirements** (clinical data,
  GDPR special-category data, institutional data agreements), tell us at intake.
  Some constraints can be accommodated; some cannot. We will be honest about which.
- Project files are retained only as long as needed for delivery and the
  included follow-up, then removed on request.

If formal data-processing guarantees are required for your institution, that
should be discussed and agreed in writing before any data is sent.

---

## 6. Scope and limitations

**Well suited to:**
- Standard bulk RNA-seq, two-group comparisons
- Designs with a small number of known batch covariates
- Human, mouse, and other organisms (gene annotation and pathway enrichment
  are currently optimized for human data)

**Not covered by this service:**
- Single-cell RNA-seq, spatial transcriptomics
- Complex designs: time-course, interaction effects, multi-factor models beyond
  simple covariates
- Experimental design consulting, sample-size planning, or wet-lab guidance
- Clinical or diagnostic use — results are for research purposes only
- Data generation, sequencing, or upstream read alignment and quantification

**On the AI-generated narrative:** the written sections are produced by language
models and reviewed by a human. They accelerate reporting; they do not replace
domain expertise. Scientific conclusions remain the responsibility of the
commissioning researcher.

---

## 7. Getting started

To commission an analysis, prepare your two CSV files per Section 3 and the three
details in Section 3.3. Initial validation feedback is provided before any
billable work begins, so you know early if the data is analysis-ready.

Pricing is agreed per project, based on the number of samples, the complexity of
the design, and the turnaround required.

---

*Bioinformatics Agent Studio — Petros Kogios, MSc Bioinformatics, University of Crete.*
*Repository and live demonstration reports: github.com/Lakog9/bioinformatics-agent-studio*
