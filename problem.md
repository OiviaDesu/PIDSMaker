# PIDSMaker Supercomputer Run – Problems (Oct 29, 2025)

This document captures the root causes behind the latest batch (Batch 10, jobs 6532643–6532660) failures and the concrete fixes applied in-repo. No jobs have been resubmitted yet.

## Summary of issues

4) ImportError in container: missing set_task_to_done
- Evidence: All Batch 11 jobs failed in ~1–9 minutes with
  - `ImportError: cannot import name 'set_task_to_done' from 'pidsmaker.config'`
- Impact: The pipeline aborted at startup inside the container, before running any tasks.
- Root cause: The function `set_task_to_done` and the marker `TASK_FINISHED_FILE` were referenced by `pidsmaker.main` / `pipeline` but not defined in the config package.
- Fix in repo: Implemented in `pidsmaker/config/pipeline.py`:
  - `TASK_FINISHED_FILE = "TASK_FINISHED"`
  - `set_task_to_done(task_path)` creates the marker file inside a task folder
  - Exported implicitly via `from .pipeline import *` so `from pidsmaker.config import set_task_to_done` works inside the container

1) Node-local storage not used → Postgres restore ran on /tmp and ran out of space
- Evidence: `No space left on device` during `pg_restore` across CADETS_E3 and THEIA_E3.
  - Example (6532649, orthrus_default_theia_e3):
    - pg_restore: ERROR: could not extend file ... No space left on device
    - tee: /tmp/pidsmaker_6532649/run.log: No space left on device
- Impact: Database initialization failed early; run logs couldn’t be written; jobs exited quickly (< 1m).
- Root cause: The older submission script defaulted to `/tmp` when `$TMPDIR`/`$SLURM_TMPDIR` were unset.
- Fix in repo: `scripts/submit_all_e3_jobs.sh` now prioritizes node-local scratch and never falls back to `/tmp`:
  - Prefer `$SLURM_TMPDIR`, then `/scratch/$USER/$JOB_ID`, then a non-`/tmp` `$TMPDIR`, else shared `/fred`.

2) PIDSMaker CLI rejected `--db_port`
- Evidence: All jobs that launched Python failed with:
  - `argparse.ArgumentTypeError: Unknown args ['--db_port', '<PORT>']`
- Impact: Even when Postgres was up, the pipeline aborted immediately because the CLI didn’t accept `--db_port`.
- Root cause: `pidsmaker.main` uses `get_runtime_required_args()` from `pidsmaker/config/pipeline.py`, which didn’t define `--db_port` (nor `--db_host`).
- Fix in repo:
  - Added optional `--db_port` and `--db_host` to the runtime arg parser.
  - Added override logic in `get_default_cfg(...)` to set `cfg.database.host/port` from env (`PIDSM_DB_HOST`, `PIDSM_DB_PORT`) or CLI flags.

3) Slurm job falsely reported success when Python failed
- Evidence: Some jobs showed `COMPLETED` in Slurm despite the argparse error, and printed “Job completed successfully.”
  - Cause: The script piped Python output through `tee`, causing the pipeline to return the exit code of `tee` (0) instead of Python.
- Fix in repo: Hardened the job wrapper to not mask failures
  - Added `set -o pipefail` within the `bash -lc` context and propagate the Python exit code.
  - If Python exits non-zero, the job now exits with the same code (no “false green”).

## Files changed (already committed locally)

- `scripts/submit_all_e3_jobs.sh`
  - TMPDIR selection now avoids `/tmp`; prefers `$SLURM_TMPDIR` or `/scratch`.
  - Added `set -o pipefail` and exit-code propagation after the Apptainer exec.
- `pidsmaker/config/pipeline.py`
  - Added CLI args: `--db_host`, `--db_port`.
  - Added env/CLI override for `cfg.database.host/port`.

## Next steps (no resubmission yet)

- Optionally validate one job with `--db_port` override to confirm the CLI/plumbing works end-to-end (when you’re ready to resubmit).
- Consider checking available free space in chosen TMPDIR prior to `pg_restore` and fail early with a clear message if low.
- Keep persisting only lightweight logs to `/fred` to avoid quota/inode pressure.

## Log pointers

- Slurm logs: `/fred/oz411/dunguyen/slurm-logs/*_ctn_<JOB_ID>.*`
  - Example fails: 6532643 (cadets), 6532649 (theia).
  - Example “COMPLETED” but still argparse error due to masking: 6532655–6532660 (clearscope).
