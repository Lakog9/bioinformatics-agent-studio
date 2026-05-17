# ============================================
# Generic DESeq2 Differential Expression Pipeline
# ============================================
# Usage:
#   Rscript 01_deseq2_analysis.R <counts.csv> <metadata.csv> <condition_col> <ref_level> [batch_cols]
#
# Args:
#   counts.csv      : gene counts, 1st col = gene_id, other cols = sample IDs
#   metadata.csv    : sample metadata, 1st col = sample_id, other cols = covariates
#   condition_col   : name of the column in metadata that defines the comparison
#   ref_level       : the reference (control) level of the condition column
#   batch_cols      : (optional) comma-separated names of covariates to control for
#                     (e.g. "cell" or "cell,batch")
#
# Example:
#   Rscript 01_deseq2_analysis.R data/counts.csv data/metadata.csv dex untrt cell
# ============================================

suppressPackageStartupMessages({
  library(DESeq2)
  library(ggplot2)
  library(pheatmap)
  library(jsonlite)
})

# ----- Parse arguments -----
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 4) {
  stop("Usage: Rscript 01_deseq2_analysis.R <counts.csv> <metadata.csv> <condition_col> <ref_level> [batch_cols]")
}
counts_path  <- args[1]
metadata_path <- args[2]
condition_col <- args[3]
ref_level    <- args[4]
batch_cols   <- if (length(args) >= 5) strsplit(args[5], ",")[[1]] else character(0)

cat("=== DESeq2 Pipeline ===\n")
cat("Counts:    ", counts_path, "\n")
cat("Metadata:  ", metadata_path, "\n")
cat("Condition: ", condition_col, "(ref =", ref_level, ")\n")
cat("Batch:     ", if (length(batch_cols) > 0) paste(batch_cols, collapse=", ") else "(none)", "\n\n")

# ----- Validate inputs exist -----
for (p in c(counts_path, metadata_path)) {
  if (!file.exists(p)) stop("File not found: ", p)
}

# ----- Load data -----
counts_df <- read.csv(counts_path, check.names = FALSE, stringsAsFactors = FALSE)
metadata  <- read.csv(metadata_path, stringsAsFactors = FALSE)

# Gene IDs as rownames
gene_id_col <- colnames(counts_df)[1]
rownames(counts_df) <- counts_df[[gene_id_col]]
counts_mat <- as.matrix(counts_df[, -1, drop = FALSE])
storage.mode(counts_mat) <- "integer"

# Sample IDs as rownames
if (!"sample_id" %in% colnames(metadata)) {
  stop("Metadata must have a 'sample_id' column.")
}
rownames(metadata) <- metadata$sample_id

# ----- Validate consistency -----
samples_in_counts   <- colnames(counts_mat)
samples_in_metadata <- rownames(metadata)
common <- intersect(samples_in_counts, samples_in_metadata)

if (length(common) == 0) {
  stop("No sample IDs match between counts and metadata.\n",
       "  counts:   ", paste(head(samples_in_counts), collapse=", "), "...\n",
       "  metadata: ", paste(head(samples_in_metadata), collapse=", "), "...")
}
if (length(common) < length(samples_in_counts)) {
  cat("WARNING: dropping", length(samples_in_counts) - length(common),
      "samples not present in metadata\n")
}

counts_mat <- counts_mat[, common, drop = FALSE]
metadata   <- metadata[common, , drop = FALSE]

cat("Samples after matching:", ncol(counts_mat), "\n")
cat("Genes:                ", nrow(counts_mat), "\n")

# ----- Validate condition column -----
if (!condition_col %in% colnames(metadata)) {
  stop("Condition column '", condition_col, "' not found in metadata.\n",
       "Available columns: ", paste(colnames(metadata), collapse=", "))
}
metadata[[condition_col]] <- factor(metadata[[condition_col]])
if (!ref_level %in% levels(metadata[[condition_col]])) {
  stop("Reference level '", ref_level, "' not found in '", condition_col, "'.\n",
       "Available levels: ", paste(levels(metadata[[condition_col]]), collapse=", "))
}
metadata[[condition_col]] <- relevel(metadata[[condition_col]], ref = ref_level)

# Set up batch covariates
for (b in batch_cols) {
  if (!b %in% colnames(metadata)) {
    stop("Batch column '", b, "' not found in metadata.")
  }
  metadata[[b]] <- factor(metadata[[b]])
}

# ----- Build design formula -----
design_terms <- c(batch_cols, condition_col)
design_formula <- as.formula(paste("~", paste(design_terms, collapse = " + ")))
cat("Design formula:", deparse(design_formula), "\n\n")

# ----- DESeq2 -----
dds <- DESeqDataSetFromMatrix(countData = counts_mat,
                               colData   = metadata,
                               design    = design_formula)

# Filter low counts
keep <- rowSums(counts(dds) >= 10) >= 3
dds <- dds[keep, ]
cat("Genes after filtering:", nrow(dds), "\n")

# Run analysis
dds <- DESeq(dds)
non_ref_levels <- setdiff(levels(metadata[[condition_col]]), ref_level)
contrast_level <- non_ref_levels[1]
res <- results(dds, contrast = c(condition_col, contrast_level, ref_level), alpha = 0.05)
summary(res)

# ----- Gene annotation (best-effort, human only) -----
res_df <- as.data.frame(res)
res_df$ensembl_id <- rownames(res_df)
res_df$gene_symbol <- NA_character_

# Try human annotation if available
human_annotated <- FALSE
if (requireNamespace("org.Hs.eg.db", quietly = TRUE)) {
  ensembl_clean <- sub("\\..*", "", rownames(res_df))  # strip version suffix
  syms <- tryCatch(
    AnnotationDbi::mapIds(org.Hs.eg.db::org.Hs.eg.db,
                          keys = ensembl_clean,
                          column = "SYMBOL", keytype = "ENSEMBL",
                          multiVals = "first"),
    error = function(e) NULL
  )
  if (!is.null(syms)) {
    res_df$gene_symbol <- as.character(syms)
    n_mapped <- sum(!is.na(res_df$gene_symbol))
    if (n_mapped > nrow(res_df) * 0.5) {
      human_annotated <- TRUE
      cat("Gene symbol annotation: ", n_mapped, "/", nrow(res_df), " mapped (human)\n", sep="")
    }
  }
}
if (!human_annotated) {
  cat("Gene symbol annotation: skipped (non-human or unavailable)\n")
}

res_df$label <- ifelse(is.na(res_df$gene_symbol), res_df$ensembl_id, res_df$gene_symbol)
res_df$significant <- with(res_df,
    !is.na(padj) & padj < 0.05 & abs(log2FoldChange) > 1)

res_sig <- res_df[!is.na(res_df$padj) & res_df$padj < 0.05, ]
res_sig <- res_sig[order(res_sig$padj), ]
cat("Significant DEGs (padj < 0.05):", nrow(res_sig), "\n")

# ----- Create output directories -----
dir.create("results/figures", recursive = TRUE, showWarnings = FALSE)
dir.create("results/tables",  recursive = TRUE, showWarnings = FALSE)
dir.create("data",            recursive = TRUE, showWarnings = FALSE)

# ----- PCA -----
vsd <- tryCatch(
  vst(dds, blind = FALSE),
  error = function(e) {
    cat("  vst() unavailable (likely too few genes); using varianceStabilizingTransformation()\n")
    varianceStabilizingTransformation(dds, blind = FALSE)
  }
)
intgroup_vars <- c(condition_col, batch_cols)
pca_data <- plotPCA(vsd, intgroup = intgroup_vars, returnData = TRUE)
pv <- round(100 * attr(pca_data, "percentVar"))

if (length(batch_cols) > 0) {
  pca_aes <- aes(x = .data[["PC1"]], y = .data[["PC2"]],
                 color = .data[[condition_col]], shape = .data[[batch_cols[1]]])
} else {
  pca_aes <- aes(x = .data[["PC1"]], y = .data[["PC2"]],
                 color = .data[[condition_col]])
}
p_pca <- ggplot(pca_data, pca_aes) +
  geom_point(size = 4) +
  xlab(paste0("PC1: ", pv[1], "%")) +
  ylab(paste0("PC2: ", pv[2], "%")) +
  theme_bw() + ggtitle("PCA")
ggsave("results/figures/01_pca.png", p_pca, width = 7, height = 5, dpi = 300)

# ----- Volcano -----
top_labels <- head(res_sig, 15)
p_volcano <- ggplot(res_df, aes(log2FoldChange, -log10(padj), color = significant)) +
  geom_point(alpha = 0.6, size = 1) +
  scale_color_manual(values = c("grey70", "red3")) +
  geom_vline(xintercept = c(-1, 1), linetype = "dashed") +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  geom_text(data = top_labels, aes(label = label),
            size = 2.5, hjust = -0.1, color = "black") +
  theme_bw() +
  labs(title = paste("Volcano:", contrast_level, "vs", ref_level),
       x = "log2 fold change", y = "-log10 padj")
ggsave("results/figures/02_volcano.png", p_volcano, width = 8, height = 6, dpi = 300)

# ----- Heatmap -----
top_genes <- head(rownames(res_sig), 30)
if (length(top_genes) >= 2) {
  mat <- assay(vsd)[top_genes, ]
  mat <- mat - rowMeans(mat)
  anno <- as.data.frame(colData(vsd)[, intgroup_vars, drop = FALSE])
  rownames(mat) <- res_sig[top_genes, "label"]

  png("results/figures/03_heatmap_top30.png", width = 8, height = 9, units = "in", res = 300)
  pheatmap(mat, annotation_col = anno, show_rownames = TRUE,
           main = "Top 30 DEGs (row-centered VST)")
  dev.off()
}

# ----- DEG table -----
output_cols <- intersect(
  c("ensembl_id", "gene_symbol", "log2FoldChange", "padj", "baseMean", "lfcSE", "stat", "pvalue"),
  colnames(res_sig)
)
write.csv(res_sig[, output_cols],
          "results/tables/DEGs_padj0.05.csv", row.names = FALSE)

# ----- Save R objects -----
saveRDS(dds, "data/dds.rds")
saveRDS(res, "data/results.rds")

# ----- Summary JSON for agents -----
top5 <- head(res_sig[, output_cols], 5)

summary_list <- list(
  dataset = tools::file_path_sans_ext(basename(counts_path)),
  comparison = paste(contrast_level, "vs", ref_level),
  organism = if (human_annotated) "Homo sapiens" else "unknown",
  total_genes_tested = sum(!is.na(res$padj)),
  genes_after_filter = nrow(dds),
  significant_degs = nrow(res_sig),
  upregulated = sum(res_sig$log2FoldChange > 0),
  downregulated = sum(res_sig$log2FoldChange < 0),
  pca_pc1_variance = pv[1],
  pca_pc2_variance = pv[2],
  design_formula = deparse(design_formula),
  methods = list(
    tool = "DESeq2",
    tool_version = as.character(packageVersion("DESeq2")),
    r_version = R.version.string,
    model = "negative binomial generalized linear model",
    test = "Wald test",
    multiple_testing_correction = "Benjamini-Hochberg",
    significance_threshold = 0.05,
    filtering_criterion = "genes with at least 10 reads in at least 3 samples",
    normalization = "DESeq2 median-of-ratios size factors",
    fold_change_threshold_for_enrichment = 1
  ),
  top5_genes = top5
)
write(toJSON(summary_list, pretty = TRUE, auto_unbox = TRUE),
      "data/analysis_summary.json")

# ----- QC metrics JSON -----
library_sizes <- colSums(counts(dds))
pct_genes_detected <- colMeans(counts(dds) > 0) * 100
mean_counts <- colMeans(counts(dds))

qc_metrics <- list(
  samples = lapply(colnames(dds), function(s) {
    base <- list(
      sample_id = s,
      condition = as.character(colData(dds)[s, condition_col]),
      library_size = library_sizes[[s]],
      pct_genes_detected = round(pct_genes_detected[[s]], 2),
      mean_count = round(mean_counts[[s]], 2),
      pca_pc1 = round(pca_data[pca_data$name == s, "PC1"], 3),
      pca_pc2 = round(pca_data[pca_data$name == s, "PC2"], 3)
    )
    for (b in batch_cols) {
      base[[b]] <- as.character(colData(dds)[s, b])
    }
    base
  }),
  thresholds = list(
    library_size_red = 1000000,
    library_size_yellow = 5000000,
    pct_genes_detected_red = 20,
    pca_outlier_sd = 2.0
  ),
  n_samples = ncol(dds),
  n_genes_tested = nrow(dds)
)
write(toJSON(qc_metrics, pretty = TRUE, auto_unbox = TRUE),
      "data/qc_metrics.json")

cat("\n=== DONE ===\n")
cat("Outputs:\n")
cat("  results/figures/  - PCA, volcano, heatmap\n")
cat("  results/tables/   - DEG table\n")
cat("  data/             - dds.rds, results.rds, analysis_summary.json, qc_metrics.json\n")
