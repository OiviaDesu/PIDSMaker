# PIDSMaker Known Issues and Solutions

This document tracks all significant problems encountered while running PIDSMaker/Orthrus on OzSTAR, along with their root causes and solutions.

## Problem 1: Zero True Positives Detection (CRITICAL) ❌

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
Malicious node 355502 : loss=0.036 | is TP: ❌
Malicious node 355507 : loss=0.037 | is TP: ❌  
Malicious node 355470 : loss=0.440 | is TP: ❌
Malicious node 355535 : loss=0.487 | is TP: ❌
```

Only extreme outlier malicious nodes have high loss:
```
Malicious node 147459 : loss=4.078 | is TP: ❌ (network connection)
Malicious node 147460 : loss=4.096 | is TP: ❌ (network connection)
Malicious node 147461 : loss=4.216 | is TP: ❌ (network connection)
```

With threshold=0.536, nodes with loss < 0.536 are classified as normal, causing 0 TP.

### Attempted Solutions
1. ❌ Changed from `max_val_loss` to `mean_val_loss` (job 6358952) - Still 0 TP
2. ❌ Optimized model architecture (smaller dims) - Didn't fix threshold issue
3. ❌ Increased batch sizes - Unrelated to threshold problem

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

## Problem 2: PostgreSQL Not in Container ❌

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
1. ❌ Tried to start PostgreSQL from container - Binary not found
2. ❌ Looked for system PostgreSQL modules - None available on OzSTAR

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

## Problem 3: Invalid Threshold Method Configuration ❌

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

## Problem 4: PostgreSQL Data Directory Already Exists ❌

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

## Problem 5: Slow Training Time (Partially Resolved) ⚠️

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
- **GNN training:** 45 min → 14 min (3.2x faster) ✅
- **Total runtime:** 65 min → 32.5 min (2x faster) ✅
- **GPU memory:** 1.8 GB → 1.27 GB (29% reduction) ✅
- **Detection:** Still 0 TP ❌

### Impact
**SUCCESS for speed, FAILED for detection** - Model trains faster but doesn't detect anything

---

## Problem 6: Milan-GPU Partition Temporarily Down ⚠️

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

## Summary of Current Status

### Resolved ✅
- PostgreSQL installation and setup
- Configuration validation errors
- Training speed optimization
- GPU memory optimization

### Unresolved ❌
- **CRITICAL:** Zero true positive detection due to wrong threshold methodology
- Need to try alternative threshold methods or implement custom solution

### Optimization Results

| Metric | Before (6357922) | After (6358952) | Status |
|--------|------------------|-----------------|---------|
| Runtime | 65 min | 32.5 min | ✅ 2x faster |
| GNN Training | 45 min | 14 min | ✅ 3.2x faster |
| GPU Memory | 1.8 GB | 1.27 GB | ✅ 29% less |
| True Positives | 0 | 0 | ❌ Still broken |
| Precision | 0.0 | 0.0 | ❌ Still broken |
| AUC | 0.81 | 0.70 | ⚠️ Slightly worse |

### Critical Next Action
**Fix threshold selection** - This is blocking all downstream work. Model architecture is fine; threshold methodology is broken.

## References
- Job 6357922 results: `result.md`
- Job 6358952 results: `result_6358952.md`
- All commands: `command.md`
- Configuration: `config/orthrus_tuned.yml`
