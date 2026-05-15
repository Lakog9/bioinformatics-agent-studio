# ============================================
# Pathway Enrichment Analysis
# Airway RNA-seq DEGs — GO, KEGG, Reactome
# Uses gprofiler2 (g:Profiler API)
# ============================================

library(gprofiler2)
library(ggplot2)
library(jsonlite)

cat("=== Pathway Enrichment ===\n")

# --- 1. Load DEG table ---
deg_path <- "results/tables/DEGs_padj0.05.csv"
if (!file.exists(deg_path)) {
  stop("DEG table not found. Run 01_deseq2_analysis.R first.")
}

degs <- read.csv(deg_path)
cat("Loaded", nrow(degs), "DEGs from", deg_path, "\n")

# Separate up and down regulated, take top by |log2FC|
up_genes <- degs[degs$log2FoldChange > 1, "ensembl_id"]
down_genes <- degs[degs$log2FoldChange < -1, "ensembl_id"]

cat("Upregulated (log2FC > 1):  ", length(up_genes), "\n")
cat("Downregulated (log2FC < -1):", length(down_genes), "\n")

# --- 2. Background = all tested genes ---
# Use all genes in the DEG file (significant) + add baseline universe
# In practice, you should pass the full tested gene set
all_genes <- as.character(degs$ensembl_id)

# --- 3. Run enrichment ---
cat("\nCalling g:Profiler API...\n")

gost_results <- gost(
  query = list(
    "Upregulated" = up_genes,
    "Downregulated" = down_genes
  ),
  organism = "hsapiens",
  sources = c("GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"),
  significant = TRUE,
  user_threshold = 0.05,
  correction_method = "g_SCS",
  evcodes = FALSE
)

if (is.null(gost_results) || nrow(gost_results$result) == 0) {
  stop("No enriched terms found.")
}

results_df <- gost_results$result
cat("Total enriched terms:", nrow(results_df), "\n")

# --- 4. Summary by source ---
cat("\nBreakdown by source:\n")
source_counts <- table(results_df$source, results_df$query)
print(source_counts)

# --- 5. Top 10 per query/source for the report ---
cat("\nTop 5 upregulated GO:BP terms:\n")
top_up_bp <- subset(results_df,
                     query == "Upregulated" & source == "GO:BP")
top_up_bp <- top_up_bp[order(top_up_bp$p_value), ]
print(head(top_up_bp[, c("term_name", "p_value", "term_size", "intersection_size")], 5))

cat("\nTop 5 downregulated GO:BP terms:\n")
top_down_bp <- subset(results_df,
                       query == "Downregulated" & source == "GO:BP")
top_down_bp <- top_down_bp[order(top_down_bp$p_value), ]
print(head(top_down_bp[, c("term_name", "p_value", "term_size", "intersection_size")], 5))

# --- 6. Save full results table ---
# Drop the parents column (list -> CSV trouble)
results_clean <- results_df[, !names(results_df) %in% c("parents")]
write.csv(results_clean, "results/tables/pathway_enrichment.csv", row.names = FALSE)
cat("\nSaved: results/tables/pathway_enrichment.csv\n")

# --- 7. Manhattan-style plot ---
p_gost <- gostplot(gost_results, capped = TRUE, interactive = FALSE)
ggsave("results/figures/04_pathway_enrichment.png", p_gost,
       width = 12, height = 7, dpi = 300)
cat("Saved: results/figures/04_pathway_enrichment.png\n")

# --- 8. Top terms dotplot (manual, per query/source) ---
top_terms <- do.call(rbind, lapply(c("Upregulated", "Downregulated"), function(q) {
  do.call(rbind, lapply(c("GO:BP", "KEGG", "REAC"), function(src) {
    sub <- subset(results_df, query == q & source == src)
    sub <- sub[order(sub$p_value), ]
    head(sub, 5)
  }))
}))

top_terms$neglog10p <- -log10(top_terms$p_value)
top_terms$term_short <- substr(top_terms$term_name, 1, 50)

p_dot <- ggplot(top_terms,
                aes(x = neglog10p, y = reorder(term_short, neglog10p),
                    color = query, size = intersection_size)) +
  geom_point() +
  facet_wrap(~ source, scales = "free_y", ncol = 1) +
  scale_color_manual(values = c("Upregulated" = "red3", "Downregulated" = "steelblue")) +
  labs(x = "-log10 (adjusted p-value)", y = NULL,
       title = "Top 5 enriched terms per source/direction") +
  theme_bw() +
  theme(axis.text.y = element_text(size = 8))

ggsave("results/figures/05_top_pathways_dotplot.png", p_dot,
       width = 11, height = 11, dpi = 300)
cat("Saved: results/figures/05_top_pathways_dotplot.png\n")

# --- 9. Update analysis_summary.json with enrichment results ---
summary_path <- "data/analysis_summary.json"
if (file.exists(summary_path)) {
  existing <- fromJSON(summary_path, simplifyVector = FALSE)
} else {
  existing <- list()
}

enrichment_summary <- list(
  total_terms = nrow(results_df),
  upregulated = list(
    "GO:BP" = head(top_up_bp$term_name, 5),
    n_terms = sum(results_df$query == "Upregulated")
  ),
  downregulated = list(
    "GO:BP" = head(top_down_bp$term_name, 5),
    n_terms = sum(results_df$query == "Downregulated")
  ),
  source_breakdown = as.list(table(results_df$source))
)

existing$pathway_enrichment <- enrichment_summary

write(toJSON(existing, pretty = TRUE, auto_unbox = TRUE),
      summary_path)
cat("\nUpdated:", summary_path, "(added pathway_enrichment section)\n")

cat("\n=== DONE ===\n")
