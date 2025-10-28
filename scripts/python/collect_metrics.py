#!/usr/bin/env python3
"""
Collect metrics from Slurm job logs for a list of job IDs.

- Discovers log files under ~/slurm-logs matching *_ctn_<JOBID>.out or *<JOBID>*.out
- Falls back to sacct to retrieve JobName when available
- Parses key metrics from logs: threshold, TP/FP/TN/FN, precision, recall, F1, AUC,
  tps_if_all_attacks_detected, fps_if_all_attacks_detected, discrimination
- Infers model/dataset/config from JobName when possible
- Writes CSV to results/batch2_metrics.csv

Usage:
  python scripts/python/collect_metrics.py 6531376 6531380 ...
"""
import csv
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

HOME = Path.home()
SLURM_LOG_DIR = HOME / "slurm-logs"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = RESULTS_DIR / "batch2_metrics.csv"

METRIC_PATTERNS = {
    "threshold": re.compile(r"threshold\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
    "tp": re.compile(r"\bTP\s*[:=]\s*(\d+)", re.I),
    "fp": re.compile(r"\bFP\s*[:=]\s*(\d+)", re.I),
    "tn": re.compile(r"\bTN\s*[:=]\s*(\d+)", re.I),
    "fn": re.compile(r"\bFN\s*[:=]\s*(\d+)", re.I),
    "precision": re.compile(r"precision\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
    "recall": re.compile(r"recall\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
    "f1": re.compile(r"f1\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
    "auc": re.compile(r"auc\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
    "tps_if_all_attacks_detected": re.compile(r"tps_if_all_attacks_detected\s*[:=]\s*(\d+)", re.I),
    "fps_if_all_attacks_detected": re.compile(r"fps_if_all_attacks_detected\s*[:=]\s*(\d+)", re.I),
    "discrimination": re.compile(r"discrimination\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I),
}

JOBNAME_CACHE: Dict[str, str] = {}


def get_jobname(jobid: str) -> Optional[str]:
    if jobid in JOBNAME_CACHE:
        return JOBNAME_CACHE[jobid]
    try:
        out = subprocess.check_output(
            [
                "sacct",
                "-j",
                jobid,
                "--format=JobName",
                "-n",
            ],
            text=True,
        ).strip().splitlines()
        name = out[0].strip() if out else None
        if name:
            JOBNAME_CACHE[jobid] = name
            return name
    except Exception:
        return None
    return None


def find_log(jobid: str) -> Optional[Path]:
    # Preferred pattern: *_ctn_<JOBID>.out
    patt = list(SLURM_LOG_DIR.glob(f"*_ctn_{jobid}.out"))
    if patt:
        return patt[0]
    # Fallback: *<JOBID>.out
    patt = list(SLURM_LOG_DIR.glob(f"*{jobid}*.out"))
    if patt:
        return patt[0]
    return None


def infer_fields_from_jobname(jobname: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    # Expected patterns like: orthrus_default_cadets_e3, magic_tuned_theia_e3, kairos_default_clearscope_e3
    name = jobname.lower()
    model = None
    config = None
    dataset = None
    models = ["orthrus", "magic", "kairos", "velox", "flash", "nodlink", "rcaid", "threatrace"]
    for m in models:
        if name.startswith(m):
            model = m
            break
    if "_tuned_" in name:
        config = "tuned"
    elif "_default_" in name:
        config = "default"
    # Dataset tokens
    for d in ["cadets_e3", "theia_e3", "clearscope_e3", "cadets_e5", "theia_e5", "optc_h201", "optc_h501", "optc_h051"]:
        if name.endswith(d):
            dataset = d.upper()
            break
    return model, dataset, config


def parse_metrics(text: str) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    for key, rx in METRIC_PATTERNS.items():
        m = rx.search(text)
        if m:
            metrics[key] = m.group(1)
    return metrics


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/python/collect_metrics.py <JOBID> [<JOBID> ...]")
        return 2

    jobids = argv[1:]
    rows = []

    for jid in jobids:
        jobname = get_jobname(jid) or ""
        model, dataset, config = infer_fields_from_jobname(jobname or "")
        log = find_log(jid)
        txt = ""
        if log and log.exists():
            try:
                txt = log.read_text(errors="ignore")
            except Exception:
                txt = ""
        metrics = parse_metrics(txt)
        rows.append(
            {
                "jobid": jid,
                "jobname": jobname,
                "model": model or "",
                "dataset": dataset or "",
                "config": config or "",
                **{k: metrics.get(k, "") for k in METRIC_PATTERNS.keys()},
                "log_file": str(log) if log else "",
            }
        )

    # Write CSV
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "jobid",
                "jobname",
                "model",
                "dataset",
                "config",
                *METRIC_PATTERNS.keys(),
                "log_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
