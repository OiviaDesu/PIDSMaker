# PIDSMaker Known Issues and Solutions

This document tracks all significant problems encountered while running PIDSMaker/Orthrus on OzSTAR, along with their root causes and solutions.

## Current Status: Tuned Jobs Awaiting Execution (Oct 23, 2025)

### Job Submission: Third Round (6396666-6396671)

**Status:** All 6 jobs PENDING (Priority) - awaiting scheduler assignment

**Jobs:**
- 6396666: orthrus_tuned on CADETS_E3 (1h limit, 32GB RAM)
- 6396667: magic_tuned on CADETS_E3 (1h limit, 32GB RAM)
- 6396668: kairos_tuned on CADETS_E3 (1h limit, 32GB RAM)
- 6396669: orthrus_tuned on THEIA_E3 (1.5h limit, 48GB RAM)
- 6396670: magic_tuned on THEIA_E3 (1.5h limit, 48GB RAM)
- 6396671: kairos_tuned on THEIA_E3 (1.5h limit, 48GB RAM)

**Fixes Applied:**
1. CLI invocation: Changed to positional args `python -m pidsmaker.main {model}_tuned {DATASET} --artifact_dir_in_container`
2. Dataset casing: Changed to uppercase `CADETS_E3` and `THEIA_E3`
3. NLTK offline: Removed network downloads, added regex fallback tokenizer
4. Percentile thresholds: Implemented in codebase (p=78 Kairos, p=92 Magic, p=77 Orthrus)

**Previous Failures:**
- First round (6378640-6378645): CLI argument errors (used --config/--dataset flags instead of positional args)
- Second round (6379295-6379303): Dataset case mismatch (lowercase cadets_e3 vs uppercase CADETS_E3)

**Next Steps:**
- Monitor queue for job start
- Extract metrics once completed
- Update result.md with tuned outcomes

---

## Problem 1: Zero True Positives Detection (Critical, addressed in tuned configs)

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

## Problem 2: CLI Argument Errors (Resolved)

### Status
**RESOLVED** - Jobs 6378640-6378645, 6379295-6379303

### Symptoms
- First batch (6378640-6378645): `argparse.ArgumentTypeError: Unknown args ['--config', '--dataset', '--output_dir', ...]`
- Second batch (6379295-6379303): `ValueError: Unknown dataset cadets_e3. Available datasets are dict_keys(['THEIA_E5', 'THEIA_E3', 'CADETS_E5', 'CADETS_E3', ...])`

### Root Cause
1. pidsmaker.main expects positional arguments (model, dataset), not flags like `--config` and `--dataset`
2. Dataset names are case-sensitive; config expects uppercase `CADETS_E3` and `THEIA_E3`

### Solution
1. Fixed CLI invocation: changed to `python -m pidsmaker.main {model} {DATASET} --artifact_dir_in_container '$WORK_DIR/artifacts'`
2. Fixed dataset casing: `cadets_e3` → `CADETS_E3`, `theia_e3` → `THEIA_E3`

### Impact
**HIGH** - Blocked two rounds of job submissions; resolved in third round (6396666-6396671)

---

## Problem 3: NLTK Offline Compatibility (Resolved)

### Status
**RESOLVED** - Fixed for Apptainer offline environment

### Symptoms
```
[nltk_data] Error loading punkt: <urlopen error [Errno -3] Temporary failure in name resolution>
```

### Root Cause
Apptainer compute nodes have no internet access; `nltk.download("punkt")` attempted network downloads at runtime

### Solution
- Removed unconditional `import nltk` and `nltk.download("punkt")` from pidsmaker/utils/utils.py
- Added guarded optional import with fallback: `from nltk.tokenize import word_tokenize as _nltk_word_tokenize`
- Implemented `safe_word_tokenize()` function with regex fallback: `r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]"`
- Updated all tokenization functions to use safe_word_tokenize

### Impact
**MODERATE** - Ensures offline compatibility; no runtime errors in Apptainer

---

## Problem 4: Slow Training Time (Partially Resolved)

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

---

## Update: October 29, 2025 - Reproduction-Aligned Configuration Changes

### Root Cause Analysis Completed

Based on reproduction guidance from papers, identified three critical mismatches:

1. **ORTHRUS**: `kmeans_top_K=30` too small for 40-120 malicious node datasets; percentile_p=77 excludes too many anomalies
2. **KAIROS**: Using `node_evaluation` instead of paper's `queue_evaluation` (wrong detection granularity)
3. **MAGIC**: Implementation already correct; minor mask_rate tuning applied

### Configuration Updates Applied (Batch 2)

**ORTHRUS**:

---

## Update: October 29, 2025 - Batch 2 Configuration Fixes

### Root Cause Identified
1. **ORTHRUS**: `kmeans_top_K=30` too small; `percentile_p=77` too high
2. **KAIROS**: Using node-level instead of queue-level detection (wrong granularity)
3. **MAGIC**: Implementation correct; minor tuning only

### Fixes Applied
**Config Changes**:
- `config/orthrus.yml`: kmeans_top_K 30→100
- `config/orthrus_tuned.yml`: percentile_p 77→90, kmeans_top_K 150→100 (fixed duplicate)
- `config/kairos.yml` & `kairos_tuned.yml`: node_evaluation → queue_evaluation
- `config/magic.yml` & `magic_tuned.yml`: mask_rate 0.5→0.4
- `scripts/submit_all_e3_jobs.sh`: Added `module load apptainer`

**Batch 2 Submitted**: Jobs 6531376-6531396 (18 jobs: 3 datasets × 3 models × 2 configs)

### Expected Outcomes
- ORTHRUS: 20-80 TPs (from 0), precision 1-10%
- KAIROS: Queue-level detection (if code works)
- MAGIC: <5% change

### Status
Awaiting results (1-2.5h runtime expected)
