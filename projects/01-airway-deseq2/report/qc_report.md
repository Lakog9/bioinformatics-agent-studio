## QC Report

### Overview
All 8 samples passed quality control across every assessed metric, with no red or yellow flags raised. Library sizes are uniformly high (ranging from 15.1 M to 30.8 M reads), gene detection rates are near-complete across all samples, and no PCA outliers were identified. This dataset is in excellent condition for downstream differential expression analysis.

### Per-Sample Flags

| Sample | Condition | Library Size | % Genes Detected | PCA Status | Overall Flag |
|---|---|---|---|---|---|
| SRR1039508 | untrt (N61311) | 20,614,946 | 99.90% | Within range (PC1 = −16.62) | 🟢 GREEN |
| SRR1039509 | trt (N61311) | 18,788,624 | 99.84% | Within range (PC1 = 8.78) | 🟢 GREEN |
| SRR1039512 | untrt (N052611) | 25,318,862 | 99.94% | Within range (PC1 = −10.07) | 🟢 GREEN |
| SRR1039513 | trt (N052611) | 15,148,260 | 99.84% | Within range (PC1 = 16.94) | 🟢 GREEN |
| SRR1039516 | untrt (N080611) | 24,419,686 | 99.88% | Within range (PC1 = −14.09) | 🟢 GREEN |
| SRR1039517 | trt (N080611) | 30,784,808 | 99.92% | Within range (PC1 = 10.32) | 🟢 GREEN |
| SRR1039520 | untrt (N061011) | 19,100,122 | 99.89% | Within range (PC1 = −12.25) | 🟢 GREEN |
| SRR1039521 | trt (N061011) | 21,140,857 | 99.82% | Within range (PC1 = 16.99) | 🟢 GREEN |

### Interpretation

**Library size** was assessed against two thresholds: samples below 1,000,000 reads would be flagged 🔴 RED, and those below 5,000,000 reads would be flagged 🟡 YELLOW. All 8 samples clear these thresholds comfortably, with the lowest library size being SRR1039513 at 15,148,260 reads — roughly 3× above the yellow threshold. The highest, SRR1039517, reached 30,784,808 reads. There is some variability in sequencing depth across samples (roughly 2-fold range), but all values fall well within an acceptable range for robust differential expression analysis.

**Gene detection rate** was evaluated against a 🔴 RED threshold of less than 20% of the 16,596 tested genes. Every sample detected between 99.82% and 99.94% of genes, indicating comprehensive transcriptome coverage with no evidence of degradation, poor library preparation, or sample contamination that might selectively suppress gene detection.

**PCA outlier status** was determined using a ±2 standard deviation threshold on PC1 (mean = 0.0, SD = 13.624), meaning any sample with |PC1| > 27.25 would be flagged. The most extreme PC1 values observed were SRR1039521 (PC1 = 16.99) and SRR1039513 (PC1 = 16.94), both well within the acceptable range. The spread of PC1 values appears to reflect the expected treatment effect rather than technical artifacts, which is a reassuring finding. Notably, SRR1039516 and SRR1039517 (cell line N080611) show elevated PC2 values (13.73 and 18.09, respectively), which may reflect a cell-line-specific transcriptional signature; this is worth keeping in mind during downstream interpretation but does not constitute a QC failure under the current flagging scheme.

### Recommendation

Proceed with downstream analysis: all 8 samples passed every QC threshold and are suitable for differential expression analysis without exclusion or special treatment.