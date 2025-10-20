# Problems encountered (OzSTAR, PIDSMaker/Orthrus)

This document lists issues we hit while setting up and running PIDSMaker (Orthrus) on OzSTAR, plus symptoms, likely causes, and how we addressed them.

## 1) PostgreSQL dump version mismatch
- Symptoms:
  - `pg_restore: unsupported version (1.16) in file header` when using older `pg_restore`.
- Likely cause:
  - The dataset dump was created with a newer PostgreSQL (v16+), but our initial restore attempts used older client/server versions.
- Resolution:
  - Installed PostgreSQL 17 in a dedicated conda env and initialized a cluster under `/fred/.../pg/data`.
  - Restored `cadets_e3` successfully using PG17 tools.

## 2) Disk quota limits on /home and /fred during CUDA installs
- Symptoms:
  - Conda/pip installs for GPU PyTorch failed with “no space left on device” and cache explosions.
- Likely cause:
  - Limited quota and heavy binary wheels (torch+cu117, PyG CUDA extensions) exceeding limits.
- Resolution:
  - Avoided per-node installs; pivoted to Apptainer container with prebuilt SIF on `/fred`.
  - Redirected Apptainer cache/tmp to `/fred/.../.apptainer/{cache,tmp}`.

## 3) Compute nodes lack outbound network
- Symptoms:
  - Pip/conda failing at job runtime: cannot reach `pypi.org`/`docker.io`.
- Likely cause:
  - Standard OzSTAR policy: compute nodes are network-restricted.
- Resolution:
  - Prebuilt the Apptainer SIF on a login node; no pip inside jobs.
  - Ensured all dependencies are baked into the SIF, including Torch+cu117 and PyG 2.5.3 wheels.

## 4) PyTorch/PyG CUDA compatibility headaches
- Symptoms:
  - Version mismatches when trying module-based PyTorch (1.12.1+cu117) with PyG wheels.
- Likely cause:
  - Narrow compatibility matrix between torch/torchvision/torch-geometric/torch-scatter/etc.
- Resolution:
  - Standardized on torch 1.13.1+cu117 and PyG 2.5.3 in the container; validated import versions.

## 5) Early Slurm job failures with ExitCode 0:53 / signal 53
- Symptoms:
  - sacct shows `FAILED 0:53` within seconds; no stdout/err on /fred; tee logs missing.
- Likely cause (hypotheses):
  - Apptainer attempting on-node build/pull or writing to restricted `/tmp` (nodev), or brief /fred unavailability at start.
  - Stdout/err directed to /fred may fail to open at launch.
- Resolution:
  - Stopped on-node builds; ensured a prebuilt SIF exists on `/fred`.
  - Set `APPTAINER_CACHEDIR` and `APPTAINER_TMPDIR` to `/fred/.../.apptainer/{cache,tmp}`.
  - Redirected Slurm stdout/err to `~/slurm-logs` to guarantee logs even if /fred is flaky at start.
  - Kept detailed pipeline log via `tee` on /fred once the job is running.

Note: We also encountered a separate failure with ExitCode 1:0 due to PostgreSQL failing to start because of a user quota error on `/fred`. Postgres logs showed:

> PANIC: could not create file "pg_logical/replorigin_checkpoint.tmp": Disk quota exceeded

Action: Free space under `/fred/<project>/<user>` before starting the job so PG can create small control/checkpoint files.

## 6) Attempt to use module PyTorch with node-local venv
- Symptoms:
  - Job failed at pip install step for PyG due to no network on compute node.
- Likely cause:
  - Network restriction; PyG wheel set not cached locally.
- Resolution:
  - Abandoned node-local venv approach; used container with all deps.

## 7) Apptainer build failed on compute node
- Symptoms:
  - `FATAL: conveyor failed to get: pinging container registry registry-1.docker.io ... connection refused`.
- Likely cause:
  - Building inside job tried to fetch base images; compute node has no outbound network.
- Resolution:
  - Built the SIF on the login node using `apptainer build` and stored it on /fred.

## 8) GPU visibility and CUDA in container
- Symptoms:
  - On login node, `torch.cuda.is_available()` returns False (expected), causing confusion.
- Likely cause:
  - No GPU on login nodes; `--nv` not in use there.
- Resolution:
  - Verified that jobs use `apptainer exec --nv` and added a preflight torch check inside the job to print CUDA availability.

## 9) W&B (Weights & Biases) optional logging
- Consideration:
  - WANDB_API_KEY not set by default; runs won’t upload unless configured.
- Resolution:
  - Added `.env` sourcing in Slurm scripts; set `WANDB_MODE`.
  - Compute nodes block outbound network: ONLINE mode caused `wandb.init` timeout and job failure. Use OFFLINE on compute nodes and `wandb sync` on login node; ONLINE only on login/hosts with egress.

## 10) Paths and bindings
- Symptoms:
  - Potential confusion about where logs/artifacts live and how paths map into the container.
- Resolution:
  - Standardized binds in Slurm scripts:
    - `-B /fred/oz396/dunguyen:/fred/oz396/dunguyen`
    - `-B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker`
  - Artifact dir set to `/fred/.../pids_artifacts`; logs under `/fred/.../pids_logs` with Slurm stdout/err under `~/slurm-logs`.

## 11) Postgres service management in jobs
- Symptoms:
  - Jobs may start without PG running; restores vs runtime access need host DB available.
- Resolution:
  - Slurm scripts check for PG17 and start `pg_ctl` if not running, using data dir under /fred.

## 12) Inode quota exhaustion on /fred (CRITICAL BLOCKER)
- Symptoms:
  - Jobs fail immediately with "Disk quota exceeded" when trying to create lock files.
  - PostgreSQL cannot start or create `postmaster.pid`: `FATAL: could not create lock file "postmaster.pid": Disk quota exceeded`
  - Group quota shows 999,487+ / 1,000,000 inodes used (>99.9%).
- Likely cause:
  - The oz396 project group has exhausted its 1 million inode (file count) limit on /fred.
  - This is a shared quota affecting all users in the project.
- Root causes identified (inode usage breakdown):
  - **thoang**: 454,381 files (45.3%) - primarily `.conda` directory with 400k+ files
    - `.conda/pkgs` cache: 124,801 files (can be safely deleted)
    - `.conda/envs`: 275,803 files (old environments)
  - **aho**: 401,781 files (40%)
  - **lbao**: 61,014 files (6%)
  - **dunguyen** (you): 59,027 files (5.9%) - reasonable usage
  - **xmeng**: 27,789 files (2.8%)
- Resolution:
  - **Critical action needed**: Contact **thoang** and **aho** to clean their conda caches:
    - `conda clean --all --yes` (removes package caches safely)
    - Remove old/unused conda environments
    - Could free 300-400k inodes immediately
  - **Alternative**: Contact system admin to request inode quota increase for oz396 project
  - **Workaround attempted**: Scripts updated to avoid creating new lock files; rely on existing postmaster.pid checks
  - **Status**: PostgreSQL running but cannot create new files; all jobs blocked until quota freed
  - **Permission issue**: Cannot clean other users' files directly; they must do it themselves

## 13) Node-local path and capacity issues for PGDATA clone
- Symptoms:
  - `/jobfs/local/slurm/.../pids_run`: Permission denied when creating node-local run dir.
  - `/tmp/pids_run_<JOBID>/pgdata`: rsync failed with `No space left on device` while copying PGDATA.
- Likely cause:
  - `/jobfs` path not writable by the job, and default `/tmp` capacity too small or limited by cgroups.
- Resolution:
  - Switched to robust node-local selection: `${SLURM_TMPDIR:-${TMPDIR:-/tmp}}`.
  - Requested sufficient node-local tmp space via `#SBATCH --tmp=50G`.
  - All scripts now use node-local PG on port 55432 and package artifacts to home at job end.

## 14) lmod PS1 unbound variable under set -u
- Symptoms:
  - Job fails after PG starts with `/apps/system/lmod/lmod/init/bash: line 106: PS1: unbound variable`.
- Likely cause:
  - `set -u` treats unset `PS1` as an error when initializing the `module` shell functions (lmod).
- Resolution:
  - Wrap module/conda init with `set +u` and set a default `PS1` before `module load mamba`, then restore `set -u`.

## 15) W&B init timeout despite WANDB_MODE=offline in env
- Symptoms:
  - `wandb.init` timed out even after setting WANDB_MODE=offline in `.env`.
- Likely cause:
  - Code forced `mode="online"` when `--wandb` was used; compute nodes have no egress.
- Resolution:
  - Patched `pidsmaker/main.py` to honor `WANDB_MODE` (offline/online/disabled).

## 16) CLI database flags rejected by argparse
- Symptoms:
  - Argparse raised `Unknown args ['--database.host=...', '--database.port=...', '--database.user=...']`.
- Likely cause:
  - These overrides weren’t defined as CLI args; DB is configured via cfg.
- Resolution:
  - Removed CLI DB flags from Slurm scripts.
  - Defaulted DB config in code to node-local Postgres (127.0.0.1:55432).

## 17) Model name typo (`orthus` vs `orthrus`)
- Symptoms:
  - `ValueError: Unknown model orthus` when launching.
- Likely cause:
  - Slurm scripts passed `orthus`, but config file is `orthrus.yml`.
- Resolution:
  - Fixed scripts to pass `orthrus`.

## 18) Missing psycopg2 in container
- Symptoms:
  - `ModuleNotFoundError: No module named 'psycopg2'` in container run.
- Likely cause:
  - Base SIF lacked the driver.
- Resolution:
  - Added `psycopg2-binary==2.9.9` to `containers/pidsmaker_cuda117.def` and rebuilt SIF.

## 19) NLTK `punkt` download errors on compute nodes
- Symptoms:
  - `[nltk_data] Error loading punkt: Temporary failure in name resolution`.
- Likely cause:
  - No outbound network; NLTK can’t fetch data at runtime.
- Resolution / Notes:
  - Non-blocking for current pipeline; if required, vendor the tokenizer or set `NLTK_DATA` to a prepopulated path in the image.

---

If new problems arise, add a new section with: Symptoms → Likely cause → Resolution. PRs welcome to refine these notes.