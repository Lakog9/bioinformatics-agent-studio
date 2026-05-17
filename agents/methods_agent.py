#!/usr/bin/env python3
"""
Methods Agent
=============
Reads an analysis_summary.json and writes a precise, publication-style
Methods section for an RNA-seq differential expression analysis.

The agent is a constrained specialist: it states ONLY the methodological
parameters present in the JSON. It does not invent steps, versions, or
thresholds that were not actually used.

Usage:
    python agents/methods_agent.py [path-to-analysis_summary.json]
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

DEFAULT_SUMMARY = (Path(__file__).parent.parent / "projects" /
                   "01-airway-deseq2" / "data" / "analysis_summary.json")

SYSTEM_PROMPT = """You are a scientific writer producing the Methods section of an
RNA-seq differential expression analysis for a peer-reviewed publication or technical report.

STRICT RULES:
- State ONLY methodological details present in the input JSON
- Do NOT invent tool versions, parameter values, thresholds, or steps
- If a detail is not in the JSON, do not mention it
- Use the exact tool versions, thresholds and criteria given
- Write in past tense, third person, passive voice — standard Methods register
  (e.g. "Counts were filtered...", "Differential expression was assessed...")
- Be precise and complete but concise: a single well-structured paragraph,
  or at most two
- Do not editorialize, interpret results, or add limitations — this is Methods only
- Report numbers exactly as given (gene counts, thresholds)
- Mention the multiple-testing correction, the statistical test, the model,
  the filtering criterion, the design formula, and the significance threshold
- If a pathway_enrichment section is present, add one sentence describing the
  enrichment method and its sources

OUTPUT FORMAT:
Write exactly one section:
## Methods
[the methods prose — no bullet points, no subheadings]"""


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Summary not found at: {path}")
    with open(path) as f:
        return json.load(f)


def generate_methods(summary: dict) -> tuple[str, int, int]:
    user_message = f"""Write the Methods section for this RNA-seq differential
expression analysis, using only the details in the JSON below.

ANALYSIS SUMMARY:
{json.dumps(summary, indent=2)}

INSTRUCTIONS:
- Draw tool, version, model, test, correction, thresholds and filtering
  criterion from the `methods` block
- Draw the design formula, comparison, organism and gene counts from the
  top-level fields
- If `pathway_enrichment` is present, add one sentence on the enrichment method
- Output only the Methods section."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return (response.content[0].text,
            response.usage.input_tokens,
            response.usage.output_tokens)


def main():
    if len(sys.argv) > 1:
        summary_path = Path(sys.argv[1]).resolve()
    else:
        summary_path = DEFAULT_SUMMARY

    print("=" * 40)
    print("  Methods Agent")
    print("=" * 40)

    print(f"\n[1/3] Loading: {summary_path}")
    try:
        summary = load_summary(summary_path)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Invalid JSON: {e}")
        sys.exit(1)

    if "methods" not in summary:
        print("\nWARNING: no 'methods' block in JSON — the analysis was produced")
        print("by an older pipeline version. The Methods section will be limited.")
    else:
        m = summary["methods"]
        print(f"  Tool: {m.get('tool')} {m.get('tool_version', '')}")

    print(f"\n[2/3] Calling Claude API...")
    try:
        methods, t_in, t_out = generate_methods(summary)
    except Exception as e:
        print(f"\nERROR: API call failed: {e}")
        sys.exit(1)

    cost = (t_in * 3 + t_out * 15) / 1_000_000
    print(f"  Tokens: {t_in} in / {t_out} out")
    print(f"  Cost:   ${cost:.4f}")

    output_path = summary_path.parent.parent / "report" / "methods.md"
    print(f"\n[3/3] Saving to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(methods)

    print(f"\n{'=' * 40}")
    print(f"  DONE  |  Output: {output_path}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
