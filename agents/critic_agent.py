#!/usr/bin/env python3
"""
Critic Agent
============
Reviews the text produced by the other agents (narrative, methods, QC report)
against the underlying analysis JSON, and flags factual inconsistencies,
overclaiming, unhedged statements, and internal contradictions.

The Critic does NOT rewrite text. It produces a structured critique that a
human analyst uses during review, before delivery.

This agent operationalizes the "human-in-the-loop" review step as a
second-pass check — a constrained reviewer, not an autonomous editor.

Usage:
    python agents/critic_agent.py [path-to-analysis_summary.json]
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

SYSTEM_PROMPT = """You are a scientific reviewer performing a second-pass check on a
draft RNA-seq analysis report. The report's text sections were drafted by other
agents. Your job is to catch problems BEFORE a human analyst signs off.

You are given (a) the draft text sections and (b) the analysis JSON, which is the
ground truth — the actual numbers and parameters from the run.

WHAT TO CHECK:
1. Factual consistency — every number, gene name, threshold, and direction
   stated in the text must match the JSON. Flag any mismatch.
2. Causal overreach — flag causal language ("causes", "drives", "proves",
   "demonstrates that X leads to Y") that observational differential-expression
   data cannot support.
3. Unhedged claims — flag strong statements that lack appropriate scientific
   hedging, and note where the existing hedging is adequate.
4. Scope creep — flag conclusions that go beyond what the data supports
   (e.g. clinical claims from in-vitro data, mechanistic claims from correlation).
5. Internal contradictions — flag any place where the narrative, methods, and
   QC sections disagree with each other.

REVIEWER DISCIPLINE:
- Be specific: quote the exact phrase you are flagging.
- Be fair: do not invent problems. If a section is sound, say so plainly.
- Do not nitpick stylistic choices — focus on accuracy and scientific validity.
- Do NOT rewrite the text. You flag and explain; the human revises.
- Assign each flagged item a severity:
    🔴 must fix — factual error, or a claim the data cannot support
    🟡 should review — borderline, could be hedged better, minor imprecision
    🟢 note — minor observation, no action strictly required

OUTPUT FORMAT — write exactly these sections:
## Verdict
[One of: "Clean — no blocking issues", "Minor revisions advised",
 "Revision required before delivery". Then 1-2 sentences explaining.]

## Factual Consistency Check
[Did the text's numbers match the JSON? State what you verified. Flag mismatches.]

## Flagged Passages
[For each issue: the severity emoji, the quoted phrase, which document it is in,
 and a one-line explanation. If none, say "No passages flagged."]

## Reviewer Notes
[Brief closing notes for the human analyst — what to prioritize.]"""


def load_text(path: Path) -> str:
    if path.exists():
        return path.read_text()
    return ""


def main():
    if len(sys.argv) > 1:
        summary_path = Path(sys.argv[1]).resolve()
    else:
        summary_path = DEFAULT_SUMMARY

    print("=" * 40)
    print("  Critic Agent")
    print("=" * 40)

    print(f"\n[1/3] Loading documents...")
    if not summary_path.exists():
        print(f"\nERROR: analysis JSON not found: {summary_path}")
        sys.exit(1)

    try:
        summary = json.loads(summary_path.read_text())
    except json.JSONDecodeError as e:
        print(f"\nERROR: invalid JSON: {e}")
        sys.exit(1)

    report_dir = summary_path.parent.parent / "report"
    narrative = load_text(report_dir / "narrative.md")
    methods = load_text(report_dir / "methods.md")
    qc_report = load_text(report_dir / "qc_report.md")

    docs_found = []
    if narrative: docs_found.append("narrative")
    if methods: docs_found.append("methods")
    if qc_report: docs_found.append("qc_report")

    if not docs_found:
        print(f"\nERROR: no draft documents found in {report_dir}")
        print("Run the other agents first (report writer, methods, QC).")
        sys.exit(1)

    print(f"  Documents to review: {', '.join(docs_found)}")
    print(f"  Ground truth:        {summary_path.name}")

    # --- Build the review payload ---
    parts = [f"GROUND-TRUTH ANALYSIS JSON:\n{json.dumps(summary, indent=2)}\n"]
    if narrative:
        parts.append(f"--- DRAFT: NARRATIVE ---\n{narrative}\n")
    if methods:
        parts.append(f"--- DRAFT: METHODS ---\n{methods}\n")
    if qc_report:
        parts.append(f"--- DRAFT: QC REPORT ---\n{qc_report}\n")

    user_message = (
        "Review the following draft report sections against the ground-truth JSON. "
        "Produce the structured critique as instructed.\n\n" + "\n".join(parts)
    )

    print(f"\n[2/3] Calling Claude API...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
    except Exception as e:
        print(f"\nERROR: API call failed: {e}")
        sys.exit(1)

    critique = response.content[0].text
    t_in = response.usage.input_tokens
    t_out = response.usage.output_tokens
    cost = (t_in * 3 + t_out * 15) / 1_000_000
    print(f"  Tokens: {t_in} in / {t_out} out")
    print(f"  Cost:   ${cost:.4f}")

    output_path = report_dir / "critique_report.md"
    print(f"\n[3/3] Saving to: {output_path}")
    with open(output_path, "w") as f:
        f.write("# Critique Report\n\n")
        f.write("*Second-pass review — generated by the Critic Agent. "
                "For human analyst use during review.*\n\n")
        f.write("---\n\n")
        f.write(critique)

    print(f"\n{'=' * 40}")
    print(f"  DONE  |  Output: {output_path}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
