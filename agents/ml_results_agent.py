#!/usr/bin/env python3
"""
ML Results Agent
================
Reads model_summary.json from the breast cancer classifier pipeline
and generates scientific narrative using the Claude API.

Usage:
    python agents/ml_results_agent.py

Output:
    projects/02-breast-cancer-ml/report/ml_narrative.md
"""

import json
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

BASE_DIR = Path(__file__).parent.parent / "projects" / "02-breast-cancer-ml"
SUMMARY_PATH = BASE_DIR / "data" / "model_summary.json"
OUTPUT_PATH = BASE_DIR / "report" / "ml_narrative.md"

SYSTEM_PROMPT = """You are a data science writer specializing in machine learning for biomedical applications.
Your task is to write a clear, precise narrative for a binary classification analysis report.

STRICT RULES:
- Be factual: reference actual numbers from the input
- Do not claim the model is ready for clinical use without proper validation
- Distinguish between model performance on this specific dataset vs generalizability
- Acknowledge limitations of the approach (single dataset, no external validation, etc.)
- Write in past tense, third person, formal register
- No bullet points in prose sections — prose only
- 2-3 paragraphs per section

OUTPUT FORMAT — write exactly these four sections with these headers:
## Methods Summary
## Model Comparison
## Feature Interpretation
## Limitations"""


def load_summary(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def generate_narrative(summary: dict) -> str:
    user_message = f"""Generate a scientific narrative for this binary classification analysis.

MODEL SUMMARY:
{json.dumps(summary, indent=2)}

ADDITIONAL CONTEXT:
- Wisconsin Breast Cancer Dataset: digitized fine needle aspirate images from breast masses
- Features are computed from cell nucleus measurements (radius, texture, perimeter, area, smoothness, compactness, concavity, concave points, symmetry, fractal dimension)
- Each feature has three variants: mean, standard error (SE), and worst (largest/most extreme value)
- Positive class (1) = malignant, negative class (0) = benign
- In screening contexts, recall (sensitivity) for malignant class is prioritized over precision
- Logistic Regression with StandardScaler is interpretable and often competitive on tabular medical data
- Random Forest provides feature importance via Gini impurity but is less interpretable

Write the four narrative sections now. Be specific about numbers."""

    print("  Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    print(f"  Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000
    print(f"  Cost: ${cost:.4f}")
    return response.content[0].text


def main():
    print("=" * 40)
    print("  ML Results Agent")
    print("=" * 40)

    if not SUMMARY_PATH.exists():
        print(f"\nERROR: model_summary.json not found at:\n  {SUMMARY_PATH}")
        print("Run the classifier first: python projects/02-breast-cancer-ml/scripts/01_train_classifier.py")
        return

    print(f"\n[1/3] Loading model summary...")
    summary = load_summary(SUMMARY_PATH)
    best = summary["best_model"]
    best_auc = summary["test_set_performance"][best]["auc"]
    print(f"  Task:       {summary['task']}")
    print(f"  Samples:    {summary['n_samples_total']}")
    print(f"  Best model: {best} (AUC = {best_auc:.4f})")

    print(f"\n[2/3] Generating narrative...")
    narrative = generate_narrative(summary)

    print(f"\n[3/3] Saving...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(narrative)
    print(f"  Saved to: {OUTPUT_PATH}")

    print(f"\n{'=' * 40}")
    print(f"  DONE  |  Output: {OUTPUT_PATH}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
