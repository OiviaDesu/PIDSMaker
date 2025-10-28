#!/usr/bin/env python3
"""
Generate a Markdown summary from the results/batch2_metrics.csv and append to result.md.

Usage:
  python scripts/python/generate_markdown_summary.py [csv_path]

Writes/updates:
  - results/batch2_summary.md (full table)
  - result.md (appended section with timestamp and compact table)
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
CSV_PATH = RESULTS_DIR / "batch2_metrics.csv"
SUMMARY_MD = RESULTS_DIR / "batch2_summary.md"
RESULT_MD = REPO_ROOT / "result.md"


def to_markdown_table(rows, columns):
    # Header
    header = "| " + " | ".join(columns) + " |\n"
    sep = "|" + "|".join([" --- "] * len(columns)) + "|\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |\n" for r in rows)
    return header + sep + body


def main(argv):
    csv_path = Path(argv[1]) if len(argv) > 1 else CSV_PATH
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 2

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Sort by dataset, model, config for readability
    rows.sort(key=lambda r: (r.get("dataset", ""), r.get("model", ""), r.get("config", "")))

    # Full table columns
    full_cols = [
        "jobid", "jobname", "state", "elapsed", "model", "dataset", "config",
        "precision", "recall", "f1", "auc", "tp", "fp", "tn", "fn", "threshold", "log_file"
    ]
    full_md = to_markdown_table(rows, full_cols)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text(full_md)
    print(f"Wrote summary table to {SUMMARY_MD}")

    # Compact table for result.md
    compact_cols = ["dataset", "model", "config", "state", "elapsed", "precision", "recall", "f1", "auc", "tp", "fp"]
    compact_md = to_markdown_table(rows, compact_cols)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section = (
        f"\n\n## Batch 2 Results (auto-generated) — {ts}\n\n"
        f"Source CSV: results/batch2_metrics.csv\n\n"
        f"{compact_md}\n"
    )

    prev = RESULT_MD.read_text() if RESULT_MD.exists() else ""
    RESULT_MD.write_text(prev + section)
    print(f"Appended compact summary to {RESULT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
