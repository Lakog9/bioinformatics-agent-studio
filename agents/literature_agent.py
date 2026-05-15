#!/usr/bin/env python3
"""
Literature Review Agent
=======================
Searches PubMed for a biological topic, fetches abstracts,
and generates a structured literature review using Claude API.

Usage:
    python agents/literature_agent.py

Output:
    projects/03-literature-review/data/papers.json
    projects/03-literature-review/report/literature_review.md
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv
import requests
from anthropic import Anthropic

load_dotenv(Path(__file__).parent.parent / ".env")
client = Anthropic()

# ============================================
# Config — change TOPIC to run on any subject
# ============================================
TOPIC = "dexamethasone airway smooth muscle transcriptomics"
MAX_PAPERS = 8

BASE_DIR = Path(__file__).parent.parent / "projects" / "03-literature-review"
PAPERS_PATH = BASE_DIR / "data" / "papers.json"
OUTPUT_PATH = BASE_DIR / "report" / "literature_review.md"

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

SYSTEM_PROMPT = """You are an expert bioinformatics researcher writing a structured literature review.
Your task is to synthesize a set of PubMed abstracts into a concise, structured review.

STRICT RULES:
- Only report findings that are supported by the provided abstracts
- Do not invent citations or findings not present in the input
- Use hedged language when appropriate: "studies suggest", "evidence indicates"
- Distinguish between well-replicated findings and single-study observations
- Write in past tense, third person, formal scientific register
- Prose only — no bullet points within sections

OUTPUT FORMAT — write exactly these five sections:
## Overview
[3-4 sentences: what is the topic, how many studies, general landscape]

## Key Findings
[key biological findings across the studies — 3-4 paragraphs]

## Common Methods
[what experimental/computational approaches are used — 2 paragraphs]

## Gaps and Open Questions
[what is not yet known or contested — 2 paragraphs]

## Suggested Next Steps
[concrete research directions that emerge from the gaps — 1-2 paragraphs]"""


def search_pubmed(topic: str, max_results: int = 8) -> list[str]:
    """Search PubMed and return a list of PMIDs."""
    url = f"{PUBMED_BASE}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": topic,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    pmids = data["esearchresult"]["idlist"]
    return pmids


def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch abstracts for a list of PMIDs via eFetch."""
    url = f"{PUBMED_BASE}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml"
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    papers = []
    root = ET.fromstring(response.content)

    for article in root.findall(".//PubmedArticle"):
        try:
            # Title
            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else "No title"

            # Abstract
            abstract_texts = article.findall(".//AbstractText")
            abstract = " ".join("".join(el.itertext()) for el in abstract_texts)
            if not abstract:
                abstract = "No abstract available."

            # Authors
            authors = []
            for author in article.findall(".//Author")[:3]:
                last = author.findtext("LastName", "")
                initials = author.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {initials}".strip())
            author_str = ", ".join(authors)
            if len(article.findall(".//Author")) > 3:
                author_str += " et al."

            # Year
            year = article.findtext(".//PubDate/Year") or \
                   article.findtext(".//PubDate/MedlineDate", "")[:4]

            # PMID
            pmid = article.findtext(".//PMID", "")

            # Journal
            journal = article.findtext(".//Journal/Title") or \
                      article.findtext(".//MedlineTA", "")

            papers.append({
                "pmid": pmid,
                "title": title,
                "authors": author_str,
                "year": year,
                "journal": journal,
                "abstract": abstract[:2000]  # cap at 2000 chars
            })
        except Exception as e:
            print(f"  Warning: could not parse one article ({e})")
            continue

    return papers


def generate_review(papers: list[dict], topic: str) -> str:
    """Call Claude to generate structured literature review."""

    # Format papers for the prompt
    papers_text = ""
    for i, p in enumerate(papers, 1):
        papers_text += f"\n[{i}] {p['authors']} ({p['year']}). {p['title']}. {p['journal']}. PMID: {p['pmid']}\n"
        papers_text += f"Abstract: {p['abstract']}\n"

    user_message = f"""Write a structured literature review on the topic: "{topic}"

Based on the following {len(papers)} PubMed abstracts:
{papers_text}

Write the five sections specified in your instructions."""

    print("  Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cost = (tokens_in * 3 + tokens_out * 15) / 1_000_000
    print(f"  Tokens: {tokens_in} in / {tokens_out} out")
    print(f"  Cost:   ${cost:.4f}")

    return response.content[0].text


def main():
    print("=" * 50)
    print("  Literature Review Agent")
    print("=" * 50)
    print(f"\n  Topic: {TOPIC}")
    print(f"  Max papers: {MAX_PAPERS}")

    # Step 1: Search PubMed
    print(f"\n[1/4] Searching PubMed...")
    pmids = search_pubmed(TOPIC, MAX_PAPERS)
    print(f"  Found {len(pmids)} papers: {', '.join(pmids)}")

    if not pmids:
        print("  No papers found. Try a different topic.")
        return

    # Step 2: Fetch abstracts
    print(f"\n[2/4] Fetching abstracts...")
    time.sleep(0.5)  # be polite to NCBI
    papers = fetch_abstracts(pmids)
    print(f"  Retrieved {len(papers)} abstracts")
    for p in papers:
        print(f"    [{p['pmid']}] {p['authors']} ({p['year']}) — {p['title'][:60]}...")

    # Step 3: Save papers JSON
    print(f"\n[3/4] Saving papers...")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PAPERS_PATH, "w") as f:
        json.dump({"topic": TOPIC, "n_papers": len(papers), "papers": papers}, f, indent=2)
    print(f"  Saved: {PAPERS_PATH}")

    # Step 4: Generate review
    print(f"\n[4/4] Generating literature review...")
    review = generate_review(papers, TOPIC)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(f"# Literature Review: {TOPIC}\n\n")
        f.write(f"*{len(papers)} papers retrieved from PubMed | Generated by Literature Review Agent*\n\n")
        f.write("---\n\n")
        f.write(review)
        f.write("\n\n---\n\n## Papers Reviewed\n\n")
        for i, p in enumerate(papers, 1):
            f.write(f"{i}. {p['authors']} ({p['year']}). {p['title']}. "
                    f"*{p['journal']}*. PMID: [{p['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/)\n\n")

    print(f"\n{'=' * 50}")
    print(f"  DONE")
    print(f"  Papers: {PAPERS_PATH}")
    print(f"  Review: {OUTPUT_PATH}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
