#!/usr/bin/env python3
"""
Report Writer Agent (generic)
=============================
Reads any analysis_summary.json (RNA-seq differential expression style)
and generates scientific narrative using the Claude API.

Generic: no hardcoded gene names or dataset assumptions.
All context comes from the JSON input.

Usage:
    python agents/report_writer_agent.py [path-to-summary.json]

If no path is given, defaults to projects/01-airway-deseq2/data/analysis_summary.json
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

DEFAULT_SUMMARY = Path(__file__).parent.parent / "projects" / "01-airway-deseq2" / "data" / "analysis_summary.json"

SYSTEM_PROMPT = """You are a scientific writer specializing in computational biology and RNA-seq analysis.
Your task is to write clear, precise scientific narrative for a differential expression analysis report.

STRICT SCIENTIFIC RULES:
- Use 'differentially expressed' or 'associated with treatment', NOT 'causes' or 'proves'
- Do not overinterpret: high log2FC does not imply biological importance without functional context
- Distinguish between statistical significance (padj) and biological significance (effect size)
- Do not claim causality from observational transcriptomic data
- When discussing specific genes, use gene_symbol fields from the input (not Ensembl IDs)
- Apply your knowledge of gene function for interpretation, but never invent data not in the input
- Write in past tense, third person, formal scientific register
- Be concise: 2-3 paragraphs per section, no bullet points, prose only

OUTPUT FORMAT — write exactly these three sections:
## Executive Summary
## Results Interpretation
## Limitations"""


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Summary not found at: {path}")
    with open(path) as f:
        return json.load(f)


def generate_narrative(summary: dict) -> tuple[str, int, int]:
    user_message = f"""Generate scientific narrative for this differential expression analysis.

ANALYSIS SUMMARY:
{json.dumps(summary, indent=2)}

INSTRUCTIONS:
- All facts must come from the JSON above
- When mentioning genes, prefer gene_symbol over ensembl_id
- Use your scientific knowledge to interpret findings, but do not invent numbers
- If pathway_enrichment is present, integrate it into Results Interpretation

Write the three narrative sections now."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    return (response.content[0].text,
            response.usage.input_tokens,
            response.usage.output_tokens)


def main():
    # Allow custom JSON path via CLI
    if len(sys.argv) > 1:
        summary_path = Path(sys.argv[1]).resolve()
    else:
        summary_path = DEFAULT_SUMMARY

    print("=" * 40)
    print("  Report Writer Agent (generic)")
    print("=" * 40)

    print(f"\n[1/3] Loading: {summary_path}")
    try:
        summary = load_summary(summary_path)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Invalid JSON in {summary_path}: {e}")
        sys.exit(1)

    print(f"  Dataset:    {summary.get('dataset', 'unknown')}")
    print(f"  Comparison: {summary.get('comparison', 'unknown')}")
    if 'significant_degs' in summary:
        print(f"  DEGs:       {summary['significant_degs']} total")

    print(f"\n[2/3] Calling Claude API...")
    try:
        narrative, t_in, t_out = generate_narrative(summary)
    except Exception as e:
        print(f"\nERROR: API call failed: {e}")
        sys.exit(1)

    cost = (t_in * 3 + t_out * 15) / 1_000_000
    print(f"  Tokens: {t_in} in / {t_out} out")
    print(f"  Cost:   ${cost:.4f}")

    # Output goes next to the input JSON
    output_path = summary_path.parent.parent / "report" / "narrative.md"
    print(f"\n[3/3] Saving to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(narrative)

    print(f"\n{'=' * 40}")
    print(f"  DONE  |  Output: {output_path}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
