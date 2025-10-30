## OzSTAR migration: oz396 -> oz411

Date: 2025-10-30

Summary
- Updated all active Slurm/Apptainer scripts to use `/fred/oz411/dunguyen`.
- Created runtime dirs on oz411 and copied required assets (containers, pg data, dumps).
- Brought up a shared PostgreSQL 17 on oz411 and ensured E3 databases exist.
- Submitted and validated jobs; fixed failures by installing `pg17` under oz411.
- Synced historical offline Weights & Biases runs using containerized CLI.

Details
- Directories created on oz411:
  - `/fred/oz411/dunguyen/{containers,pids_logs,pids_artifacts,.apptainer/{cache,tmp},pg/{data,logs},data,slurm-logs,tmp}`
- Copied from oz396 → oz411:
  - `containers/pidsmaker_cuda117.sif`
  - `pg/data`, `pg/logs`
  - `data/{cadets_e3.dump,theia_e3.dump,clearscope_e3.dump,...}`
- PostgreSQL 17 (conda) installed for oz411:
  - Copied `/fred/oz396/dunguyen/.conda/envs/pg17` to `/fred/oz411/dunguyen/.conda/envs/pg17`
  - Started server: `/fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_ctl -D /fred/oz411/dunguyen/pg/data -l /fred/oz411/dunguyen/pg/logs/postgres.log start`
  - Verified DBs: `cadets_e3`, `theia_e3`, `clearscope_e3`

Script changes
- Replaced `/fred/oz396` with `/fred/oz411` in `scripts/*.slurm` and submission helper.
- `scripts/submit_all_e3_jobs.sh` now binds to oz411 paths for LOG_DIR, CONTAINER, PG_BIN.
- Leftovers referencing oz396 only remain in `archived/` and W&B logs.

W&B sync
- Used `.env` for `WANDB_API_KEY`, entity, project.
- Staged run dirs to `/fred/oz411/dunguyen/tmp/wandb_sync` and used container `wandb` to sync 74/74 runs.
- Cleaned staged copies to free space.

Notes
- Jobs prefer node-local scratch when available; fallback is `/fred/oz411/dunguyen/tmp`.
- Keep `WANDB_MODE=offline` during compute; sync later from login node.


