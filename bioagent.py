#!/usr/bin/env python3
"""
bioagent — Bioinformatics Agent Studio CLI
==========================================
End-to-end RNA-seq differential expression analysis with AI-generated reporting.

Workflow:
  1. Validate inputs (files exist, columns present, sample IDs match)
  2. Run DESeq2 differential expression
  3. Run pathway enrichment (g:Profiler)
  4. Run QC agent and Report Writer agent (Claude API)
  5. Render Quarto HTML report

Every run writes a timestamped log to <output>/run.log for audit and debugging.

Usage:
  python bioagent.py --counts <path> --metadata <path> \\
      --condition <col> --reference <level> [--batch <col1,col2>] \\
      --output <dir>
"""

import argparse
import csv
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ============================================
# Resolve repository paths
# ============================================
REPO_ROOT = Path(__file__).parent.resolve()
DEMO_PROJ = REPO_ROOT / "projects" / "01-airway-deseq2"
SCRIPTS_DIR = DEMO_PROJ / "scripts"
AGENTS_DIR = REPO_ROOT / "agents"
REPORT_TEMPLATE = DEMO_PROJ / "report" / "report.qmd"

DESEQ_SCRIPT = SCRIPTS_DIR / "01_deseq2_analysis.R"
ENRICH_SCRIPT = SCRIPTS_DIR / "02_pathway_enrichment.R"
QC_AGENT = AGENTS_DIR / "qc_agent.py"
REPORT_AGENT = AGENTS_DIR / "report_writer_agent.py"
METHODS_AGENT = AGENTS_DIR / "methods_agent.py"


# ============================================
# Logging setup
# ============================================
logger = logging.getLogger("bioagent")
logger.setLevel(logging.DEBUG)


def setup_console_logging():
    """Console handler — clean output, no timestamps (added immediately)."""
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)


def add_file_handler(log_path):
    """File handler — full timestamped audit log (added once output dir exists)."""
    fh = logging.FileHandler(log_path, mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)
    logger.debug(f"File logging started: {log_path}")


# ============================================
# Helpers
# ============================================
def fail(msg, code=1):
    logger.error(f"ERROR: {msg}")
    logger.error(f"Run aborted with exit code {code}")
    sys.exit(code)


def step(num, total, title):
    logger.info(f"\n[{num}/{total}] {title}")


def check_file(path, label):
    if not Path(path).exists():
        fail(f"{label} not found: {path}")


def validate_inputs(args):
    """Pre-flight validation: files exist, columns match, no obvious problems."""
    check_file(args.counts, "Counts CSV")
    check_file(args.metadata, "Metadata CSV")

    # Validate the metadata has the expected columns
    try:
        with open(args.metadata) as f:
            header = next(csv.reader(f))
    except Exception as e:
        fail(f"Could not read metadata: {e}")

    if "sample_id" not in header:
        fail(f"Metadata must have a 'sample_id' column. Found: {header}")
    if args.condition not in header:
        fail(f"Condition column '{args.condition}' not in metadata. "
             f"Available: {[c for c in header if c != 'sample_id']}")
    if args.batch:
        for b in args.batch.split(","):
            if b.strip() and b.strip() not in header:
                fail(f"Batch column '{b}' not in metadata.")

    # Validate counts CSV has matching samples
    try:
        with open(args.counts) as f:
            counts_header = next(csv.reader(f))
    except Exception as e:
        fail(f"Could not read counts CSV: {e}")

    counts_samples = set(counts_header[1:])  # 1st col is gene_id
    if len(counts_samples) < 2:
        fail(f"Counts file has fewer than 2 sample columns.")

    # Check reference level exists in metadata
    try:
        with open(args.metadata) as f:
            f.readline()  # skip header
            cond_idx = header.index(args.condition)
            levels = set()
            for line in f:
                parts = line.strip().split(",")
                if len(parts) > cond_idx:
                    levels.add(parts[cond_idx].strip(chr(34)))
    except Exception as e:
        fail(f"Could not scan condition levels: {e}")

    if args.reference not in levels:
        fail(f"Reference level '{args.reference}' not found in column '{args.condition}'. "
             f"Available levels: {sorted(levels)}")

    # --- Sample ID consistency check (strict) ---
    metadata_sample_ids = set()
    try:
        with open(args.metadata) as f:
            reader = csv.reader(f)
            md_header = next(reader)
            sid_idx = md_header.index("sample_id")
            for parts in reader:
                if len(parts) > sid_idx:
                    metadata_sample_ids.add(parts[sid_idx])
    except Exception as e:
        fail(f"Could not parse sample IDs from metadata: {e}")

    counts_sample_ids = set(counts_header[1:])
    in_counts_only = counts_sample_ids - metadata_sample_ids
    in_metadata_only = metadata_sample_ids - counts_sample_ids

    if in_counts_only or in_metadata_only:
        msg = "Sample ID mismatch between counts and metadata:"
        if in_counts_only:
            msg += f"\n  In counts but missing from metadata: {sorted(in_counts_only)}"
        if in_metadata_only:
            msg += f"\n  In metadata but missing from counts: {sorted(in_metadata_only)}"
        fail(msg)

    logger.info(f"  Counts file:  {args.counts}")
    logger.info(f"  Metadata:     {args.metadata}")
    logger.info(f"  Condition:    {args.condition} (ref: {args.reference})")
    logger.info(f"  Batch:        {args.batch or '(none)'}")
    logger.info(f"  Levels found: {sorted(levels)}")
    logger.debug(f"Validation passed: {len(counts_sample_ids)} samples, "
                 f"condition levels {sorted(levels)}")


def setup_output_dir(output_dir, counts_path, metadata_path):
    """Create output structure and copy inputs."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    (out / "data").mkdir(exist_ok=True)
    (out / "results" / "figures").mkdir(parents=True, exist_ok=True)
    (out / "results" / "tables").mkdir(parents=True, exist_ok=True)
    (out / "report").mkdir(exist_ok=True)

    shutil.copy(counts_path, out / "data" / "counts.csv")
    shutil.copy(metadata_path, out / "data" / "metadata.csv")

    return out


def run_subprocess(cmd, cwd, label):
    """Run a subprocess with error handling and logging."""
    logger.debug(f"{label}: running {' '.join(str(c) for c in cmd)} (cwd={cwd})")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, capture_output=True, text=True
        )
        # Log subprocess output to file only (debug level — not shown on console)
        if result.stdout:
            logger.debug(f"{label} stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"{label} stderr:\n{result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"  {label} FAILED")
        logger.error(f"  Command: {' '.join(str(c) for c in cmd)}")
        logger.error(f"  stdout:\n{e.stdout[-2000:] if e.stdout else '(empty)'}")
        logger.error(f"  stderr:\n{e.stderr[-2000:] if e.stderr else '(empty)'}")
        fail(f"{label} failed (exit code {e.returncode})")
    except FileNotFoundError:
        fail(f"Command not found: {cmd[0]}. Is it installed and in PATH?")


def run_deseq(out_dir, args):
    """Step 2: DESeq2 differential expression."""
    cmd = ["Rscript", str(DESEQ_SCRIPT),
           "data/counts.csv", "data/metadata.csv",
           args.condition, args.reference]
    if args.batch:
        cmd.append(args.batch)

    t0 = time.time()
    run_subprocess(cmd, cwd=out_dir, label="DESeq2")
    dt = time.time() - t0

    deg_file = out_dir / "results" / "tables" / "DEGs_padj0.05.csv"
    n_degs = sum(1 for _ in open(deg_file)) - 1 if deg_file.exists() else 0
    logger.info(f"  Done in {dt:.1f}s — {n_degs} significant DEGs")
    logger.debug(f"DESeq2 completed: {n_degs} DEGs in {dt:.1f}s")


def run_enrichment(out_dir):
    """Step 3: Pathway enrichment (optional — only if human)."""
    deg_file = out_dir / "results" / "tables" / "DEGs_padj0.05.csv"
    if not deg_file.exists():
        logger.info("  Skipped (no DEG table)")
        return

    with open(deg_file) as f:
        reader = csv.DictReader(f)
        if "gene_symbol" not in reader.fieldnames:
            logger.info("  Skipped (non-human dataset)")
            logger.debug("Enrichment skipped: no gene_symbol column")
            return
        rows = list(reader)
        mapped = sum(1 for r in rows if r["gene_symbol"] and r["gene_symbol"] != "NA")
        if not rows or mapped / len(rows) < 0.3:
            logger.info("  Skipped (insufficient gene symbols)")
            logger.debug(f"Enrichment skipped: only {mapped}/{len(rows)} symbols mapped")
            return

    t0 = time.time()
    run_subprocess(["Rscript", str(ENRICH_SCRIPT)],
                   cwd=out_dir, label="Pathway enrichment")
    dt = time.time() - t0
    logger.info(f"  Done in {dt:.1f}s")
    logger.debug(f"Enrichment completed in {dt:.1f}s")


def run_agents(out_dir):
    """Step 4: AI agents — QC + report writer."""
    summary_json = out_dir / "data" / "analysis_summary.json"
    qc_json = out_dir / "data" / "qc_metrics.json"

    if qc_json.exists():
        t0 = time.time()
        run_subprocess([sys.executable, str(QC_AGENT), str(qc_json)],
                       cwd=REPO_ROOT, label="QC agent")
        logger.info(f"  QC agent done in {time.time() - t0:.1f}s")
    else:
        logger.info("  QC agent skipped (no qc_metrics.json)")

    if summary_json.exists():
        t0 = time.time()
        run_subprocess([sys.executable, str(REPORT_AGENT), str(summary_json)],
                       cwd=REPO_ROOT, label="Report writer agent")
        logger.info(f"  Report writer done in {time.time() - t0:.1f}s")

        t0 = time.time()
        run_subprocess([sys.executable, str(METHODS_AGENT), str(summary_json)],
                       cwd=REPO_ROOT, label="Methods agent")
        logger.info(f"  Methods agent done in {time.time() - t0:.1f}s")
    else:
        fail("analysis_summary.json missing — DESeq2 step did not produce it")


def render_report(out_dir):
    """Step 5: Quarto render."""
    if not REPORT_TEMPLATE.exists():
        fail(f"Report template not found: {REPORT_TEMPLATE}")
    shutil.copy(REPORT_TEMPLATE, out_dir / "report" / "report.qmd")

    t0 = time.time()
    run_subprocess(["quarto", "render", "report/report.qmd"],
                   cwd=out_dir, label="Quarto render")
    logger.info(f"  Done in {time.time() - t0:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        prog="bioagent",
        description="RNA-seq differential expression with AI-generated reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python bioagent.py \\
    --counts patient_data/counts.csv \\
    --metadata patient_data/metadata.csv \\
    --condition treatment \\
    --reference control \\
    --batch batch_id \\
    --output ./client_run/
"""
    )
    parser.add_argument("--counts", required=True,
                        help="Path to counts CSV (gene_id, sample1, sample2, ...)")
    parser.add_argument("--metadata", required=True,
                        help="Path to metadata CSV (must have 'sample_id' column)")
    parser.add_argument("--condition", required=True,
                        help="Name of the condition column in metadata")
    parser.add_argument("--reference", required=True,
                        help="Reference (control) level of the condition column")
    parser.add_argument("--batch", default=None,
                        help="Optional batch covariate columns (comma-separated)")
    parser.add_argument("--output", required=True,
                        help="Output directory (created if it doesn't exist)")

    args = parser.parse_args()

    # Console logging starts immediately
    setup_console_logging()

    logger.info("=" * 60)
    logger.info("  bioagent — Bioinformatics Agent Studio")
    logger.info("=" * 60)

    run_start = time.time()

    # Create output dir early so the log file captures everything,
    # including any validation failure.
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    add_file_handler(log_path)

    # Record run parameters in the audit log
    logger.debug("=" * 50)
    logger.debug(f"RUN START: {datetime.now().isoformat()}")
    logger.debug(f"  counts    = {args.counts}")
    logger.debug(f"  metadata  = {args.metadata}")
    logger.debug(f"  condition = {args.condition}")
    logger.debug(f"  reference = {args.reference}")
    logger.debug(f"  batch     = {args.batch}")
    logger.debug(f"  output    = {out_dir}")
    logger.debug(f"  python    = {sys.executable}")
    logger.debug("=" * 50)

    # Step 1: validate
    step(1, 5, "Validating inputs...")
    validate_inputs(args)

    # Setup output (structure + copy inputs)
    setup_output_dir(args.output, args.counts, args.metadata)
    logger.info(f"  Output dir:   {out_dir}")

    # Step 2: DESeq2
    step(2, 5, "Running DESeq2 differential expression...")
    run_deseq(out_dir, args)

    # Step 3: enrichment
    step(3, 5, "Running pathway enrichment...")
    run_enrichment(out_dir)

    # Step 4: agents
    step(4, 5, "Running AI agents (QC + narrative)...")
    run_agents(out_dir)

    # Step 5: Quarto
    step(5, 5, "Rendering HTML report...")
    render_report(out_dir)

    # Done
    total = time.time() - run_start
    html_path = out_dir / "report" / "report.html"
    logger.info("\n" + "=" * 60)
    logger.info(f"  DONE in {total:.1f}s")
    logger.info(f"  Report: {html_path}")
    logger.info(f"  Log:    {log_path}")
    logger.info("=" * 60)
    logger.debug(f"RUN COMPLETE: total wall time {total:.1f}s")


if __name__ == "__main__":
    main()
