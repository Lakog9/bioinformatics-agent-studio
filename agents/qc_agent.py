#!/usr/bin/env python3
"""
QC Agent
========
Reads qc_metrics.json produced by the R pipeline, evaluates each sample
against QC thresholds, and generates a flagged QC report using Claude API.

Usage:
    python agents/qc_agent.py

Output:
    projects/01-airway-deseq2/report/qc_report.md
"""

import json
import math
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

BASE_DIR = Path(__file__).parent.parent / "projects" / "01-airway-deseq2"
QC_PATH = BASE_DIR / "data" / "qc_metrics.json"
OUTPUT_PATH = BASE_DIR / "report" / "qc_report.md"

SYSTEM_PROMPT = """You are a bioinformatics QC specialist reviewing RNA-seq sample quality.
Your task is to write a clear, concise QC report based on pre-computed metrics and flags.

RULES:
- Be factual and specific: reference actual numbers from the metrics
- Use 🟢 GREEN, 🟡 YELLOW, 🔴 RED emoji for flags
- Do not invent problems that are not supported by the data
- Explain WHY each flag was assigned (what threshold was crossed)
- Give a clear overall verdict at the end
- Write in professional but accessible language (a wet-lab scientist should understand it)
- No bullet points in prose sections; use them only in the per-sample summary table

OUTPUT FORMAT:
## QC Report

### Overview
[2-3 sentences summarizing the overall quality]

### Per-Sample Flags
[markdown table with columns: Sample | Condition | Library Size | % Genes Detected | PCA Status | Overall Flag]

### Interpretation
[prose: what the flags mean and what to do]

### Recommendation
[one clear sentence: proceed / proceed with caution / do not proceed]"""


def load_metrics(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_flags(metrics: dict) -> list:
    """Apply thresholds and assign GREEN/YELLOW/RED flags to each sample."""
    thresholds = metrics["thresholds"]
    samples = metrics["samples"]

    # Compute PCA outlier threshold (mean ± 2 SD on PC1)
    pc1_values = [s["pca_pc1"] for s in samples]
    pc1_mean = sum(pc1_values) / len(pc1_values)
    pc1_sd = math.sqrt(sum((x - pc1_mean) ** 2 for x in pc1_values) / len(pc1_values))
    pc1_threshold = thresholds["pca_outlier_sd"] * pc1_sd

    flagged = []
    for s in samples:
        flags = []
        details = []

        # Library size
        lib = s["library_size"]
        if lib < thresholds["library_size_red"]:
            flags.append("RED")
            details.append(f"library size {lib:,} < {thresholds['library_size_red']:,} (RED threshold)")
        elif lib < thresholds["library_size_yellow"]:
            flags.append("YELLOW")
            details.append(f"library size {lib:,} < {thresholds['library_size_yellow']:,} (YELLOW threshold)")
        else:
            flags.append("GREEN")
            details.append(f"library size {lib:,} (OK)")

        # % genes detected
        pct = s["pct_genes_detected"]
        if pct < thresholds["pct_genes_detected_red"]:
            flags.append("RED")
            details.append(f"{pct}% genes detected < {thresholds['pct_genes_detected_red']}% (RED threshold)")
        else:
            flags.append("GREEN")
            details.append(f"{pct}% genes detected (OK)")

        # PCA outlier (PC1 only)
        pc1_dist = abs(s["pca_pc1"] - pc1_mean)
        if pc1_dist > pc1_threshold and pc1_sd > 0:
            flags.append("YELLOW")
            details.append(f"PC1={s['pca_pc1']:.2f} is {pc1_dist/pc1_sd:.1f} SD from mean (potential outlier)")
        else:
            flags.append("GREEN")
            details.append(f"PC1={s['pca_pc1']:.2f} within normal range")

        # Overall flag: worst of all flags
        overall = "GREEN"
        if "RED" in flags:
            overall = "RED"
        elif "YELLOW" in flags:
            overall = "YELLOW"

        flagged.append({
            **s,
            "flags": flags,
            "flag_details": details,
            "overall_flag": overall,
            "pc1_mean": round(pc1_mean, 3),
            "pc1_sd": round(pc1_sd, 3)
        })

    return flagged


def generate_qc_report(metrics: dict, flagged_samples: list) -> str:
    """Call Claude to generate QC narrative from flagged metrics."""

    summary = {
        "n_samples": metrics["n_samples"],
        "n_genes_tested": metrics["n_genes_tested"],
        "thresholds": metrics["thresholds"],
        "flagged_samples": flagged_samples
    }

    user_message = f"""Generate a QC report for this RNA-seq dataset.

QC METRICS AND FLAGS:
{json.dumps(summary, indent=2)}

Write the QC report following the format specified. Be specific about numbers."""

    print("  Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    print(f"  Tokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000
    print(f"  Estimated cost: ${cost:.4f}")

    return response.content[0].text


def print_flag_summary(flagged_samples: list):
    """Print a quick flag summary to terminal."""
    print("\n  Sample flags:")
    for s in flagged_samples:
        icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(s["overall_flag"], "?")
        print(f"    {icon} {s['sample_id']} ({s['condition']}) — lib: {s['library_size']:,}")


def main():
    print("=" * 40)
    print("  QC Agent")
    print("=" * 40)

    if not QC_PATH.exists():
        print(f"\nERROR: qc_metrics.json not found at:\n  {QC_PATH}")
        print("Run the R pipeline first.")
        return

    print(f"\n[1/4] Loading QC metrics...")
    metrics = load_metrics(QC_PATH)
    print(f"  Samples: {metrics['n_samples']}")
    print(f"  Genes:   {metrics['n_genes_tested']}")

    print(f"\n[2/4] Computing flags...")
    flagged = compute_flags(metrics)
    print_flag_summary(flagged)

    n_red = sum(1 for s in flagged if s["overall_flag"] == "RED")
    n_yellow = sum(1 for s in flagged if s["overall_flag"] == "YELLOW")
    n_green = sum(1 for s in flagged if s["overall_flag"] == "GREEN")
    print(f"\n  Summary: 🟢 {n_green}  🟡 {n_yellow}  🔴 {n_red}")

    print(f"\n[3/4] Generating QC report...")
    report = generate_qc_report(metrics, flagged)

    print(f"\n[4/4] Saving report...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(report)
    print(f"  Saved to: {OUTPUT_PATH}")

    print(f"\n{'=' * 40}")
    print(f"  DONE")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
