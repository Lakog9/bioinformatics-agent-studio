#!/usr/bin/env python3
"""
Report Writer Agent
===================
Reads analysis_summary.json produced by the R pipeline and generates
scientific narrative for the Quarto report using the Claude API.

Usage:
    python agents/report_writer_agent.py

Output:
    projects/01-airway-deseq2/report/narrative.md
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# Load API key from .env in project root
load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

# Paths (relative to project root)
BASE_DIR = Path(__file__).parent.parent / "projects" / "01-airway-deseq2"
SUMMARY_PATH = BASE_DIR / "data" / "analysis_summary.json"
OUTPUT_PATH = BASE_DIR / "report" / "narrative.md"

SYSTEM_PROMPT = """You are a scientific writer specializing in computational biology and RNA-seq analysis.
Your task is to write clear, precise scientific narrative for a differential expression analysis report.

STRICT SCIENTIFIC RULES:
- Use 'differentially expressed' or 'associated with treatment', NOT 'causes' or 'proves'
- Do not overinterpret: high log2FC does not imply biological importance without functional context
- Distinguish between statistical significance (padj) and biological significance (effect size)
- Do not claim causality from observational transcriptomic data
- Write in past tense, third person, formal scientific register
- Be concise: 2-3 paragraphs per section, no bullet points, prose only

OUTPUT FORMAT:
Write exactly three sections with these exact markdown headers:
## Executive Summary
## Results Interpretation
## Limitations"""


def load_summary(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def generate_narrative(summary: dict) -> str:
    """Call Claude to generate scientific narrative from analysis summary."""

    user_message = f"""Generate scientific narrative for this RNA-seq differential expression analysis.

ANALYSIS SUMMARY:
{json.dumps(summary, indent=2)}

ADDITIONAL CONTEXT (for interpretation):
- Dataset: airway Bioconductor package (Himes et al. 2014, PMID 24926665)
- Treatment: dexamethasone (synthetic glucocorticoid, 1 µM, 18h)
- Cell type: primary human airway smooth muscle cells
- Design: paired (4 cell lines x 2 conditions, balanced)
- Top gene ENSG00000152583 = SPARCL1 (secreted protein, extracellular matrix)
- Top gene ENSG00000165995 = CACNB2 (voltage-gated calcium channel subunit)
- Top gene ENSG00000120129 = DUSP1 (dual specificity phosphatase 1, known glucocorticoid-induced gene)
- Top gene ENSG00000101347 = SAMHD1 (SAM and HD domain-containing deoxynucleoside triphosphohydrolase)
- Top gene ENSG00000189221 = MAOA (monoamine oxidase A)

Write the three narrative sections (Executive Summary, Results Interpretation, Limitations).
Follow the scientific rules strictly. Do not invent data not present in the summary."""

    print("  Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    print(f"  Tokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    estimated_cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000
    print(f"  Estimated cost: ${estimated_cost:.4f}")

    return response.content[0].text


def save_narrative(narrative: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(narrative)
    print(f"  Saved to: {path}")


def main():
    print("=" * 40)
    print("  Report Writer Agent")
    print("=" * 40)

    # Check input
    if not SUMMARY_PATH.exists():
        print(f"\nERROR: analysis_summary.json not found at:\n  {SUMMARY_PATH}")
        print("Run the R pipeline first: Rscript scripts/01_deseq2_analysis.R")
        return

    # Load summary
    print(f"\n[1/3] Loading analysis summary...")
    summary = load_summary(SUMMARY_PATH)
    print(f"  Dataset:    {summary['dataset']}")
    print(f"  Comparison: {summary['comparison']}")
    print(f"  DEGs:       {summary['significant_degs']} total "
          f"({summary['upregulated']} up / {summary['downregulated']} down)")

    # Generate narrative
    print(f"\n[2/3] Generating narrative...")
    narrative = generate_narrative(summary)

    # Save output
    print(f"\n[3/3] Saving narrative...")
    save_narrative(narrative, OUTPUT_PATH)

    print(f"\n{'=' * 40}")
    print(f"  DONE")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"{'=' * 40}")
    print("\nNext step: review narrative.md, then re-render the Quarto report.")


if __name__ == "__main__":
    main()
