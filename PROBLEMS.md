# PIDSMaker Known Issues and Solutions

This document tracks all significant problems encountered while running PIDSMaker/Orthrus on OzSTAR, along with their root causes and solutions.

## Problem 1: Zero True Positives Detection (Critical, unresolved)

### Status
**UNRESOLVED** - Affects jobs 6357922 and 6358952

### Symptoms
- Model trains successfully with decreasing loss
- AUC scores reasonable (0.70-0.81)
- **0 True Positives** detected on test set
- **0 Precision, 0 Recall, 0 F-Score**
- MCC near zero (~-0.00009)
- Model identifies 1-5 false positives but misses all 68 ground truth malicious nodes

### Root Cause
**Incorrect threshold selection methodology**

The threshold methods provided (`max_val_loss`, `mean_val_loss`) are fundamentally unsuitable for anomaly detection:

1. **Validation loss is not anomaly score:** The validation set loss distribution doesn't correlate with malicious vs normal node behavior
2. **Threshold too conservative:** 
   - Job 6357922: `max_val_loss` = too high
   - Job 6358952: `mean_val_loss` = 0.536 (still too high)
3. **Malicious nodes have low loss:** Most ground truth malicious nodes show reconstruction loss < 0.5, below the threshold
4. **Normal nodes also have low loss:** The distributions overlap heavily

### Evidence
From job 6358952 logs, most malicious nodes detected show very low loss:
```
Malicious node 355502 : loss=0.036 | is TP: no
Malicious node 355507 : loss=0.037 | is TP: no
Malicious node 355470 : loss=0.440 | is TP: no
Malicious node 355535 : loss=0.487 | is TP: no
```

Only extreme outlier malicious nodes have high loss:
```
Malicious node 147459 : loss=4.078 | is TP: no (network connection)
Malicious node 147460 : loss=4.096 | is TP: no (network connection)
Malicious node 147461 : loss=4.216 | is TP: no (network connection)
```

With threshold=0.536, nodes with loss < 0.536 are classified as normal, causing 0 TP.

### Attempted Solutions
1. Attempt: Changed from `max_val_loss` to `mean_val_loss` (job 6358952) - unsuccessful (still 0 TP)
2. Attempt: Optimized model architecture (smaller dimensions) - unsuccessful (threshold issue remains)
3. Attempt: Increased batch sizes - no effect on threshold problem

### Recommended Solutions
1. **Try dataset-specific threshold methods:**
   - `threshold_method: threatrace`
   - `threshold_method: magic`  
   - `threshold_method: flash`
   - `threshold_method: nodlink`

2. **Implement percentile-based threshold:**
   - Use 90th or 95th percentile of validation losses
   - Or use Top-K approach (select top K anomalous nodes)

3. **Use ROC curve optimal threshold:**
   - Find threshold that maximizes F1-score or Youden's J statistic
   - Requires ground truth on validation set

4. **Review paper methodology:**
   - Check original Orthrus paper for exact threshold selection
   - Verify if they use different threshold per attack type

5. **Plot loss distributions:**
   - Histogram of normal vs malicious node losses
   - Understand overlap between distributions
   - Manual threshold selection based on visualization

### Impact
**CRITICAL** - Detection completely non-functional. Model is useless for production despite training successfully.

### Next Steps
1. Immediately try `threshold_method: threatrace` (dataset-specific for CADETS)
2. If that fails, implement percentile-based threshold
3. Review source code for threshold calculation methods
4. Contact original authors or check GitHub issues

---

## Problem 2: PostgreSQL Not in Container (Resolved)

### Status
**RESOLVED** - Used conda environment instead

### Symptoms (Job 6358645)
```
[Tue Oct 21 01:45:33 AEDT 2025] PostgreSQL start failed, checking log...
No log file found
```

### Root Cause
Container image `pidsmaker_cuda117.sif` doesn't include PostgreSQL binaries (`pg_ctl`, `pg_isready`, etc.)

### Attempted Solutions
1. Attempt: Tried to start PostgreSQL from container - failed (binary not found)
2. Attempt: Looked for system PostgreSQL modules - failed (modules unavailable on OzSTAR)

### Solution
Installed PostgreSQL 17 in dedicated conda environment:
```bash
rm -rf /fred/oz396/dunguyen/.conda/envs/pg17
mamba create -n pg17 postgresql=17 -c conda-forge -y
```

Updated Slurm script to use:
```bash
PG_BIN="/fred/oz396/dunguyen/.conda/envs/pg17/bin"
"${PG_BIN}/pg_ctl" -D "${NODE_PGDATA}" -l "${NODE_PGLOG}" -o "-p 55432" start
```

### Impact
**MODERATE** - Blocked job execution until resolved

---

## Problem 3: Invalid Threshold Method Configuration (Resolved)

### Status
**RESOLVED**

### Symptoms (Job 6358565)
```
ValueError: Invalid argument threshold_method with value best_val_loss. 
Expected values: ['max_val_loss', 'mean_val_loss', 'threatrace', 'magic', 'flash', 'nodlink']
```

### Root Cause
Incorrectly assumed `best_val_loss` was a valid threshold method. Valid methods are hardcoded in `pidsmaker/config/config.py`:
```python
THRESHOLD_METHODS = ["max_val_loss", "mean_val_loss", "threatrace", "magic", "flash", "nodlink"]
```

### Solution
Changed `config/orthrus_tuned.yml`:
```yaml
threshold_method: mean_val_loss  # Changed from best_val_loss
```

### Impact
**LOW** - Quick configuration fix

---

## Problem 4: PostgreSQL Data Directory Already Exists (Resolved)

### Status
**RESOLVED**

### Symptoms
```
CondaValueError: prefix already exists: /fred/oz396/dunguyen/.conda/envs/pg17
```

### Root Cause
Previously created incomplete pg17 environment (directory exists but PostgreSQL not installed)

### Solution
```bash
rm -rf /fred/oz396/dunguyen/.conda/envs/pg17
mamba create -n pg17 postgresql=17 -c conda-forge -y
```

### Impact
**LOW** - Quick manual cleanup

---

## Problem 5: Slow Training Time (Partially Resolved)

### Status
**PARTIALLY RESOLVED** - Speed improved, but detection broken

### Symptoms (Job 6357922)
- GNN training: 45 minutes (paper reports ~4.5 minutes)
- Total runtime: 65 minutes
- GPU memory: 1.8 GB

### Root Cause
Model dimensions too large:
- Embedding dim: 128 (likely 32 in paper)
- Node hidden dim: 128 (likely 32 in paper)
- Node output dim: 64 (likely 16 in paper)
- TGN memory/time dims: 100 (likely 50 in paper)

Larger embeddings → 16x more GNN parameters → slower training

### Solution (Job 6358952)
Optimized `config/orthrus_tuned.yml`:
```yaml
emb_dim: 32          # Was 128
node_hid_dim: 32     # Was 128
node_out_dim: 16     # Was 64
tgn_memory_dim: 50   # Was 100
tgn_time_dim: 50     # Was 100
batch_size: 1024     # Was 256 (restored to default)
tgn_neighbor_size: 20 # Was 10 (restored to default)
```

### Results
- **GNN training:** 45 min → 14 min (3.2x faster) (successful)
- **Total runtime:** 65 min → 32.5 min (2x faster) (successful)
- **GPU memory:** 1.8 GB → 1.27 GB (29% reduction) (successful)
- **Detection:** Still 0 TP (unsuccessful)

### Impact
**SUCCESS for speed, FAILED for detection** - Model trains faster but doesn't detect anything

---

## Problem 6: Milan-GPU Partition Temporarily Down

### Status
**TRANSIENT** - Partition came back online

### Symptoms (Job 6358595 queued)
```
JOBID   PARTITION    NAME     USER ST  TIME  TIME_LEFT  NODES NODELIST(REASON)
6358595 milan-gpu orthus_... dunguyen PD   0:00    2:00:00  1 (PartitionDown)
```

### Root Cause
Cluster administrators disabled milan-gpu partition temporarily

### Solution
Waited for partition to come back online (~15 minutes)

### Impact
**LOW** - Temporary delay

---

## Problem 7: PostgreSQL Dump Version Mismatch (Resolved)

### Status
**RESOLVED** - PostgreSQL 17 toolchain installed

### Symptoms
- `pg_restore: unsupported version (1.16) in file header`
- Restores failed when using older PostgreSQL clients

### Root Cause
Dataset dump created with newer PostgreSQL (v16+) while local environment used older binaries

### Solution
- Installed PostgreSQL 17 in dedicated conda environment
- Initialized cluster under `/fred/oz396/dunguyen/pg/data`
- Restored `cadets_e3` using PG17 tools without errors

### Impact
**HIGH** - Blocked database restore until client/server versions matched

---

## Problem 8: Disk Quota Limits During CUDA Installs (Resolved)

### Status
**RESOLVED** - Containerized dependencies

### Symptoms
- `no space left on device` when installing CUDA-enabled PyTorch / PyG wheels via conda or pip
- Large caches accumulated under `/home` and `/fred`

### Root Cause
Project quotas on `/home` and `/fred` insufficient for repeated GPU wheel installs and caches

### Solution
- Avoided per-node installs; built Apptainer SIF with prepackaged dependencies stored on `/fred`
- Redirected Apptainer cache and tmp directories to `/fred/oz396/dunguyen/.apptainer/{cache,tmp}`

### Impact
**MODERATE** - Prevented environment setup during jobs

---

## Problem 9: Compute Nodes Lack Outbound Network (Known Limitation)

### Status
**KNOWN LIMITATION** - Must plan around network restrictions

### Symptoms
- pip and conda failed during job runtime with connection errors
- Apptainer builds attempted to pull base images and stalled

### Root Cause
OzSTAR compute nodes are intentionally isolated from the public internet

### Solution
- Build Apptainer images on login nodes with outbound access
- Bundle all Python dependencies (Torch, PyG, NLTK data) inside the container
- Documented workflow so no network calls happen during jobs

### Impact
**HIGH** - Any workflow assuming live package installs will fail

---

## Problem 10: PyTorch and PyG CUDA Compatibility (Resolved)

### Status
**RESOLVED** - Standardized versions inside container

### Symptoms
- Import errors and binary incompatibilities between Torch, Torchvision, and PyG wheels

### Root Cause
Version mismatches when mixing module-provided Torch with downloaded PyG wheels

### Solution
- Standardized on `torch==1.13.1+cu117` and `pyg==2.5.3`
- Baked the compatible stack into the Apptainer image

### Impact
**MODERATE** - Blocked model start-up until resolved

---

## Problem 11: Slurm ExitCode 0:53 Failures (Resolved)

### Status
**RESOLVED** - Prebuilt container and resilient logging

### Symptoms
- Jobs exited within seconds with `FAILED 0:53`
- No stdout/err captured on `/fred`

### Root Cause
Apptainer attempted to build or pull images on compute nodes and wrote to unwritable `/tmp` locations; `/fred` not always available at job launch

### Solution
- Prebuilt SIF stored on `/fred`
- Set Apptainer cache/tmp to project-owned paths
- Routed Slurm stdout/err to `~/slurm-logs` to avoid early write failures

### Impact
**HIGH** - Jobs failed immediately before training

---

## Problem 12: Module PyTorch with Node-Local Virtualenv (Resolved)

### Status
**RESOLVED**

### Symptoms
- pip installs for PyG wheels failed during job startup because packages were not cached

### Root Cause
Compute nodes cannot reach package mirrors, so wheel downloads timed out

### Solution
- Abandoned node-local virtualenv approach in favor of self-contained Apptainer image

### Impact
**LOW** - Early experimentation path retired

---

## Problem 13: Apptainer Build on Compute Nodes (Resolved)

### Status
**RESOLVED**

### Symptoms
- `FATAL: conveyor failed to get: pinging container registry ... connection refused`

### Root Cause
Attempted to build Apptainer image inside Slurm job without network access

### Solution
- Build SIF on login node and reuse artifact for jobs

### Impact
**LOW** - Clarified build process

---

## Problem 14: GPU Visibility Confusion on Login Nodes (Clarified)

### Status
**CLARIFIED**

### Symptoms
- `torch.cuda.is_available()` returned `False` on login nodes, causing concern about CUDA availability

### Root Cause
Login nodes lack GPUs and `--nv` flag not used during ad-hoc tests

### Solution
- Documented expectation that CUDA is only available inside jobs with `apptainer exec --nv`
- Added preflight CUDA check inside job scripts to print availability

### Impact
**LOW** - Avoided false troubleshooting efforts

---

## Problem 15: Weights & Biases Initialization Mode (Resolved)

### Status
**RESOLVED** - Honor offline mode and `.env` configuration

### Symptoms
- `wandb.init` timeout when `--wandb` flag used on compute nodes
- Timeout persisted even after setting `WANDB_MODE=offline`

### Root Cause
Application forced `mode="online"` when CLI flag present, conflicting with network-restricted environment

### Solution
- Patched `pidsmaker/main.py` to respect `WANDB_MODE`
- Documented workflow: run jobs in offline mode, then execute `wandb sync` from login node if needed

### Impact
**MODERATE** - Jobs failed until patched

---

## Problem 16: Path Bindings and Artifact Locations (Resolved)

### Status
**RESOLVED**

### Symptoms
- Confusion over where logs and artifacts were written inside the container

### Root Cause
Inconsistent bind mounts between `/home` workspace and `/fred` storage

### Solution
- Standardized Apptainer binds:
   - `-B /fred/oz396/dunguyen:/fred/oz396/dunguyen`
   - `-B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker`
- Defined artifact directory `/fred/oz396/dunguyen/pids_artifacts` and logs under `/fred/oz396/dunguyen/pids_logs`

### Impact
**LOW** - Improved reproducibility and debugging

---

## Problem 17: PostgreSQL Service Management Within Jobs (Resolved)

### Status
**RESOLVED**

### Symptoms
- Jobs occasionally started without PostgreSQL running, causing connection failures

### Root Cause
Node-local PostgreSQL required explicit startup when job began

### Solution
- Slurm scripts now detect existing PG instance and start `pg_ctl` if required using data directory on `/fred`

### Impact
**MODERATE** - Prevented intermittent job failures

---

## Problem 18: /fred Inode Quota Exhaustion (Critical, unresolved)

### Status
**UNRESOLVED** - Requires project-wide cleanup

### Symptoms
- Immediate job failure: `Disk quota exceeded`
- PostgreSQL errors: `could not create file ... Disk quota exceeded`, `could not create lock file "postmaster.pid"`
- Group quota report: >99.9% of one million inodes consumed

### Root Cause
Project members collectively exhausted inode quota, primarily due to large conda caches and environments

### Solution
- Identify heavy users (`thoang`, `aho`) and request they run `conda clean --all --yes` and prune unused environments
- Engage system administrators to request quota increase if cleanup insufficient

### Impact
**CRITICAL** - Blocks creation of new files, preventing PostgreSQL from starting and jobs from running

### Next Steps
1. Coordinate cleanup with project members holding large inode counts
2. Escalate to support if quota increase is required

---

## Problem 19: Node-Local Path Capacity for PGDATA (Resolved)

### Status
**RESOLVED**

### Symptoms
- `Permission denied` when creating node-local working directory under `/jobfs`
- `rsync: write failed ... No space left on device` while copying PGDATA to `/tmp`

### Root Cause
- Some node-local paths were not writable or had insufficient space under default tmp directories

### Solution
- Switched to `${SLURM_TMPDIR:-${TMPDIR:-/tmp}}` and requested `--tmp=50G`
- Ensured node-local PostgreSQL runs from adequately sized temporary storage

### Impact
**MODERATE** - Prevented database initialization until resolved

---

## Problem 20: lmod PS1 Unbound Variable Under `set -u` (Resolved)

### Status
**RESOLVED**

### Symptoms
- `/apps/system/lmod/lmod/init/bash: line 106: PS1: unbound variable`

### Root Cause
Shell ran with `set -u`, causing lmod initialization to fail when `PS1` unset in non-interactive shell

### Solution
- Wrapped module and conda initialization with `set +u`
- Set default `PS1` before loading modules, then restored `set -u`

### Impact
**LOW** - Prevented environment setup until patched

---

## Problem 21: CLI Database Flag Rejections (Resolved)

### Status
**RESOLVED**

### Symptoms
- `argparse` errors: `Unknown args ['--database.host=...']`

### Root Cause
Database connection overrides not exposed as CLI options

### Solution
- Removed unsupported CLI flags from Slurm scripts
- Relied on configuration file defaults for database settings

### Impact
**LOW** - Minor script cleanup

---

## Problem 22: Model Name Typo (`orthus` vs `orthrus`) (Resolved)

### Status
**RESOLVED**

### Symptoms
- `ValueError: Unknown model orthus`

### Root Cause
Typographical error in Slurm scripts referencing model name

### Solution
- Updated scripts to use `orthrus`

### Impact
**LOW** - Quick fix once identified

---

## Problem 23: Missing psycopg2 Driver in Container (Resolved)

### Status
**RESOLVED**

### Symptoms
- `ModuleNotFoundError: No module named 'psycopg2'`

### Root Cause
Base Apptainer image lacked PostgreSQL client driver

### Solution
- Added `psycopg2-binary==2.9.9` to container definition and rebuilt SIF

### Impact
**LOW** - Required rebuild but straightforward

---

## Problem 24: NLTK Punkt Downloads (Resolved)

### Status
**RESOLVED**

### Symptoms
- `Error loading punkt: Temporary failure in name resolution`

### Root Cause
NLTK attempted to download resources at runtime without network access

### Solution
- Pre-downloaded `punkt` during container build and set `NLTK_DATA=/usr/local/share/nltk_data`

### Impact
**LOW** - Ensured text preprocessing works offline

---

## Problem 25: TGN Neighbor Graph Construction OOM (Resolved)

### Status
**RESOLVED** - Increased memory allocation

### Symptoms
- Jobs failed with `OUT_OF_MEMORY` during "Computing TGN last neighbor graphs"
- Failures occurred even with reduced neighborhood parameters

### Root Cause
CADeTS_E3 dataset (2.68M nodes) requires substantial RAM during TGN neighbor graph batching

### Solution
- Increased Slurm memory request to 96 GB
- Job 6357922 completed successfully with higher memory allocation

### Impact
**HIGH** - Blocked training until memory increased

### Notes
- Peak GPU memory was modest (~1.8 GB); system RAM was the limiting factor
- Consider disabling TGN batching or using higher-memory nodes for larger datasets

---

## Summary of Current Status

### Resolved
- PostgreSQL installation and setup
- Configuration validation errors
- Training speed optimization
- GPU memory optimization

### Unresolved
- **CRITICAL:** Zero true positive detection due to wrong threshold methodology
- **CRITICAL:** /fred inode quota exhaustion blocking PostgreSQL startup and file creation

### Optimization Results

| Metric | Before (6357922) | After (6358952) | Status |
|--------|------------------|-----------------|---------|
| Runtime | 65 min | 32.5 min | Improved (2x faster) |
| GNN Training | 45 min | 14 min | Improved (3.2x faster) |
| GPU Memory | 1.8 GB | 1.27 GB | Improved (29% less) |
| True Positives | 0 | 0 | Unchanged (still zero) |
| Precision | 0.0 | 0.0 | Unchanged (still zero) |
| AUC | 0.81 | 0.70 | Slightly worse |

### Critical Next Action
**Fix threshold selection** - This is blocking all downstream work. Model architecture is fine; threshold methodology is broken.

## References
- Job 6357922 results: `result.md`
- Job 6358952 results: `result_6358952.md`
- All commands: `command.md`
- Configuration: `config/orthrus_tuned.yml`
