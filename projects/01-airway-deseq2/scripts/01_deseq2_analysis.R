# ============================================
# Project: Airway RNA-seq Differential Expression
# Goal: Untreated vs Dexamethasone-treated
#        airway smooth muscle cells (Himes et al. 2014)
# v2: Added gene symbol annotation
# ============================================

library(DESeq2)
library(airway)
library(ggplot2)
library(pheatmap)
library(org.Hs.eg.db)
library(jsonlite)

# --- 1. Load data ---
data("airway")
se <- airway

cat("Samples:", ncol(se), "\n")
cat("Genes:", nrow(se), "\n")
print(colData(se))

# --- 2. Build DESeq2 dataset ---
se$dex <- relevel(se$dex, ref = "untrt")
dds <- DESeqDataSet(se, design = ~ cell + dex)

# --- 3. Filter low counts ---
keep <- rowSums(counts(dds) >= 10) >= 3
dds <- dds[keep, ]
cat("Genes after filtering:", nrow(dds), "\n")

# --- 4. Run DESeq2 ---
dds <- DESeq(dds)
res <- results(dds, contrast = c("dex", "trt", "untrt"), alpha = 0.05)
summary(res)

# --- 5. Gene symbol annotation ---
cat("Mapping Ensembl IDs to gene symbols...\n")

gene_symbols <- mapIds(
  org.Hs.eg.db,
  keys = rownames(res),
  column = "SYMBOL",
  keytype = "ENSEMBL",
  multiVals = "first"
)

# --- 6. Build annotated results dataframe ---
res_df <- as.data.frame(res)
res_df$ensembl_id <- rownames(res_df)
res_df$gene_symbol <- gene_symbols[rownames(res_df)]
res_df$label <- ifelse(is.na(res_df$gene_symbol),
                       res_df$ensembl_id,
                       res_df$gene_symbol)
res_df$significant <- with(res_df,
    !is.na(padj) & padj < 0.05 & abs(log2FoldChange) > 1)

# Significant DEGs sorted by padj
res_sig <- res_df[!is.na(res_df$padj) & res_df$padj < 0.05, ]
res_sig <- res_sig[order(res_sig$padj), ]

cat("Significant DEGs (padj < 0.05):", nrow(res_sig), "\n")
cat("Top 5 genes:\n")
print(head(res_sig[, c("gene_symbol", "log2FoldChange", "padj")], 5))

# --- 7. PCA plot ---
vsd <- vst(dds, blind = FALSE)
pca_data <- plotPCA(vsd, intgroup = c("dex", "cell"), returnData = TRUE)
pv <- round(100 * attr(pca_data, "percentVar"))

p_pca <- ggplot(pca_data, aes(PC1, PC2, color = dex, shape = cell)) +
  geom_point(size = 4) +
  xlab(paste0("PC1: ", pv[1], "%")) +
  ylab(paste0("PC2: ", pv[2], "%")) +
  theme_bw() +
  ggtitle("PCA: Airway samples")

ggsave("results/figures/01_pca.png", p_pca, width = 7, height = 5, dpi = 300)

# --- 8. Volcano plot with gene symbol labels ---
# Label top 15 most significant genes
top_labels <- head(res_sig, 15)

p_volcano <- ggplot(res_df, aes(log2FoldChange, -log10(padj), color = significant)) +
  geom_point(alpha = 0.6, size = 1) +
  scale_color_manual(values = c("grey70", "red3")) +
  geom_vline(xintercept = c(-1, 1), linetype = "dashed") +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  geom_text(
    data = top_labels,
    aes(label = gene_symbol),
    size = 2.5,
    hjust = -0.1,
    color = "black"
  ) +
  theme_bw() +
  labs(title = "Volcano: trt vs untrt",
       x = "log2 fold change", y = "-log10 padj")

ggsave("results/figures/02_volcano.png", p_volcano, width = 8, height = 6, dpi = 300)

# --- 9. Heatmap with gene symbol labels ---
top_genes <- head(rownames(res_sig), 30)
mat <- assay(vsd)[top_genes, ]
mat <- mat - rowMeans(mat)
anno <- as.data.frame(colData(vsd)[, c("dex", "cell")])

# Replace rownames with gene symbols
row_labels <- res_sig[top_genes, "label"]
rownames(mat) <- row_labels

png("results/figures/03_heatmap_top30.png",
    width = 8, height = 9, units = "in", res = 300)
pheatmap(mat, annotation_col = anno, show_rownames = TRUE,
         main = "Top 30 DEGs (gene symbols)")
dev.off()

# --- 10. DEG table with gene symbols ---
output_cols <- c("ensembl_id", "gene_symbol", "log2FoldChange",
                 "padj", "baseMean", "lfcSE", "stat", "pvalue")
write.csv(res_sig[, output_cols],
          "results/tables/DEGs_padj0.05.csv",
          row.names = FALSE)

# --- 11. Save R objects ---
saveRDS(dds, "data/dds.rds")
saveRDS(res, "data/results.rds")

# --- 12. Export summary for Report Writer Agent ---
top5 <- head(res_sig[, c("ensembl_id", "gene_symbol",
                          "log2FoldChange", "padj", "baseMean")], 5)

summary_list <- list(
  dataset = "airway",
  comparison = "trt vs untrt",
  organism = "Homo sapiens",
  total_genes_tested = sum(!is.na(res$padj)),
  genes_after_filter = nrow(dds),
  significant_degs = nrow(res_sig),
  upregulated = sum(res_sig$log2FoldChange > 0),
  downregulated = sum(res_sig$log2FoldChange < 0),
  pca_pc1_variance = pv[1],
  pca_pc2_variance = pv[2],
  top5_genes = top5
)

write(toJSON(summary_list, pretty = TRUE, auto_unbox = TRUE),
      "data/analysis_summary.json")
cat("Summary exported to data/analysis_summary.json\n")
# --- 13. Export QC metrics for QC Agent ---
library_sizes <- colSums(counts(dds))
pct_genes_detected <- colMeans(counts(dds) > 0) * 100
mean_counts <- colMeans(counts(dds))

qc_metrics <- list(
  samples = lapply(colnames(dds), function(s) {
    list(
      sample_id = s,
      condition = as.character(colData(dds)[s, "dex"]),
      cell_line = as.character(colData(dds)[s, "cell"]),
      library_size = library_sizes[[s]],
      pct_genes_detected = round(pct_genes_detected[[s]], 2),
      mean_count = round(mean_counts[[s]], 2),
      pca_pc1 = round(pca_data[pca_data$name == s, "PC1"], 3),
      pca_pc2 = round(pca_data[pca_data$name == s, "PC2"], 3)
    )
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
cat("QC metrics exported to data/qc_metrics.json\n")
cat("\n=== DONE ===\n")
