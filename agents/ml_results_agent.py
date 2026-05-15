#!/usr/bin/env python3
"""
ML Results Agent (generic)
==========================
Reads any classifier model_summary.json and generates scientific narrative
using the Claude API.

Generic: no hardcoded dataset descriptions. All context comes from JSON.
For best results, the JSON should include `dataset_description` and `task`.

Usage:
    python agents/ml_results_agent.py [path-to-model_summary.json]
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

DEFAULT_SUMMARY = Path(__file__).parent.parent / "projects" / "02-breast-cancer-ml" / "data" / "model_summary.json"

SYSTEM_PROMPT = """You are a data science writer specializing in machine learning for biomedical and clinical applications.
Your task is to write clear, precise narrative for a binary classification analysis.

STRICT RULES:
- All facts must come from the JSON input — do not invent metrics
- Do not claim clinical readiness without external validation across cohorts
- Distinguish performance on this specific dataset vs generalizability
- Acknowledge limitations of the approach (single dataset, no external validation, etc.)
- For feature interpretation, use your domain knowledge but stay grounded in the input
- Write in past tense, third person, formal register
- Prose only — no bullet points in narrative sections
- 2-3 paragraphs per section

OUTPUT FORMAT — write exactly these four sections:
## Methods Summary
## Model Comparison
## Feature Interpretation
## Limitations"""


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Summary not found at: {path}")
    with open(path) as f:
        return json.load(f)


def generate_narrative(summary: dict) -> tuple[str, int, int]:
    user_message = f"""Generate a scientific narrative for this binary classification analysis.

MODEL SUMMARY:
{json.dumps(summary, indent=2)}

INSTRUCTIONS:
- Reference actual metrics from the JSON
- If `dataset_description` or `task` fields are present, use them for context
- If `top10_features_random_forest` or similar is present, interpret the features
  using your domain knowledge but stay grounded in what the data shows
- If confusion_matrix is present, reference FN/FP counts directly

Write the four narrative sections now."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
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
    print("  ML Results Agent (generic)")
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

    if 'best_model' in summary:
        best = summary['best_model']
        if 'test_set_performance' in summary and best in summary['test_set_performance']:
            auc = summary['test_set_performance'][best].get('auc', '?')
            print(f"  Best model: {best} (AUC = {auc})")
    print(f"  Task: {summary.get('task', 'unknown')}")

    print(f"\n[2/3] Calling Claude API...")
    try:
        narrative, t_in, t_out = generate_narrative(summary)
    except Exception as e:
        print(f"\nERROR: API call failed: {e}")
        sys.exit(1)

    cost = (t_in * 3 + t_out * 15) / 1_000_000
    print(f"  Tokens: {t_in} in / {t_out} out")
    print(f"  Cost:   ${cost:.4f}")

    output_path = summary_path.parent.parent / "report" / "ml_narrative.md"
    print(f"\n[3/3] Saving to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(narrative)

    print(f"\n{'=' * 40}")
    print(f"  DONE  |  Output: {output_path}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
