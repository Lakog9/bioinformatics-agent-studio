# ============================================
# Prepare demo data: export airway dataset as CSVs
# These CSVs are then consumed by the generic 01_deseq2_analysis.R
# ============================================

library(airway)
library(SummarizedExperiment)

data("airway")

# Counts: rows = Ensembl IDs, cols = sample IDs
counts <- assay(airway)
counts_df <- data.frame(gene_id = rownames(counts), counts, check.names = FALSE)
write.csv(counts_df, "data/counts.csv", row.names = FALSE)
cat("Saved:", "data/counts.csv  (", nrow(counts), "genes x", ncol(counts), "samples )\n")

# Metadata: rows = sample IDs, cols = covariates
metadata <- as.data.frame(colData(airway))
metadata$sample_id <- rownames(metadata)
metadata <- metadata[, c("sample_id", setdiff(colnames(metadata), "sample_id"))]
write.csv(metadata, "data/metadata.csv", row.names = FALSE)
cat("Saved:", "data/metadata.csv (", nrow(metadata), "samples )\n")

cat("\nDone. Now run:\n")
cat("  Rscript scripts/01_deseq2_analysis.R data/counts.csv data/metadata.csv dex untrt cell\n")
