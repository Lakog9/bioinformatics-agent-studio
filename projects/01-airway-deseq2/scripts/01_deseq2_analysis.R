library(DESeq2)
library(airway)
library(ggplot2)
library(pheatmap)

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

# --- 5. PCA ---
vsd <- vst(dds, blind = FALSE)
pca_data <- plotPCA(vsd, intgroup = c("dex", "cell"), returnData = TRUE)
pv <- round(100 * attr(pca_data, "percentVar"))

p_pca <- ggplot(pca_data, aes(PC1, PC2, color = dex, shape = cell)) +
  geom_point(size = 4) +
  xlab(paste0("PC1: ", pv[1], "%")) +
  ylab(paste0("PC2: ", pv[2], "%")) +
  theme_bw() + ggtitle("PCA: Airway samples")
ggsave("results/figures/01_pca.png", p_pca, width = 7, height = 5, dpi = 300)

# --- 6. Volcano ---
res_df <- as.data.frame(res)
res_df$gene <- rownames(res_df)
res_df$significant <- with(res_df,
    !is.na(padj) & padj < 0.05 & abs(log2FoldChange) > 1)

p_volcano <- ggplot(res_df, aes(log2FoldChange, -log10(padj), color = significant)) +
  geom_point(alpha = 0.6, size = 1) +
  scale_color_manual(values = c("grey70", "red3")) +
  geom_vline(xintercept = c(-1, 1), linetype = "dashed") +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  theme_bw() +
  labs(title = "Volcano: trt vs untrt",
       x = "log2 fold change", y = "-log10 padj")
ggsave("results/figures/02_volcano.png", p_volcano, width = 7, height = 5, dpi = 300)

# --- 7. DEG table ---
res_sig <- res_df[!is.na(res_df$padj) & res_df$padj < 0.05, ]
res_sig <- res_sig[order(res_sig$padj), ]
write.csv(res_sig, "results/tables/DEGs_padj0.05.csv", row.names = FALSE)
cat("Significant DEGs (padj < 0.05):", nrow(res_sig), "\n")

# --- 8. Heatmap top 30 ---
top_genes <- head(rownames(res_sig), 30)
mat <- assay(vsd)[top_genes, ]
mat <- mat - rowMeans(mat)
anno <- as.data.frame(colData(vsd)[, c("dex", "cell")])

png("results/figures/03_heatmap_top30.png",
    width = 8, height = 8, units = "in", res = 300)
pheatmap(mat, annotation_col = anno, show_rownames = TRUE)
dev.off()

# --- 9. Save ---
saveRDS(dds, "data/dds.rds")
saveRDS(res, "data/results.rds")
cat("\n=== DONE ===\n")
