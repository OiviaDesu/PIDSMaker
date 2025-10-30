# Phase 1 Implementation Summary
**Date**: October 30, 2025  
**Time**: 19:30-21:30 AEDT  
**Status**: ✅ COMPLETE - Ready for Testing

---

## 🎯 Objective
Fix the critical gap between our results (0 TP) and ORTHRUS paper results (10-25 TP) by implementing paper-accurate threshold selection and clustering methodology.

---

## 🔴 Root Causes Identified

### Bug #1: Wrong Validation Set Split ⭐ CRITICAL
- **Current**: `val_files: ["graph_10"]`
- **Paper**: `val_files: ["graph_2", "graph_6"]` (Table 8)
- **Impact**: Threshold computed from wrong day distribution

### Bug #2: Edge-Level vs Node-Level Thresholding ⭐⭐ PRIMARY
- **Current**: Threshold on raw edge reconstruction losses
- **Paper**: Threshold on per-node anomaly scores fA(u) = mean(incident edge losses)
- **Impact**: Wrong granularity → scores in wrong numerical range

### Bug #3: Wrong K-means Order ⭐ SECONDARY
- **Current**: Select top-K → cluster → filter
- **Paper**: Threshold → cluster ALL flagged → keep higher-mean cluster
- **Impact**: Biased pre-selection doesn't filter benign anomalies correctly

---

## ✅ Implementation Complete

### Changes Made

**1. Config File: `pidsmaker/config/config.py`**
```python
# Lines 100-111: CADETS_E3 splits aligned to paper Table 8
"train_files": ["graph_3", "graph_4", "graph_5", "graph_7", "graph_8", "graph_9", "graph_10"],
"val_files": ["graph_2", "graph_6"],  # Was: ["graph_10"]
"test_files": ["graph_11", "graph_12", "graph_13"],  # Was: included graph_6
```

**2. Detection Utils: `pidsmaker/detection/evaluation_methods/evaluation_utils.py`**

Added two new functions (95 lines total):
- `calculate_node_scores_from_edges()` - Aggregates edge losses to node scores
- `calculate_threshold_node_based()` - Computes threshold from validation node scores

Updated `get_threshold()`:
- Added: `max_val_node_score`, `mean_val_node_score`, `percentile_val_node_score`
- Kept legacy methods with deprecation warnings

Rewrote `compute_kmeans_labels()` (70 lines):
- Paper mode (kmeans_top_K=0): Cluster ALL flagged nodes
- Legacy mode (kmeans_top_K>0): Old behavior preserved
- Edge cases: 0 nodes→empty, 1 node→keep it, 2+→cluster

**3. Default Config: `config/orthrus.yml`**
```yaml
threshold_method: max_val_node_score  # Was: max_val_loss
kmeans_top_K: 0  # Was: 30 (paper mode: cluster all flagged)
```

---

## 📊 Expected Results

### Target: ORTHRUS-ano Performance
| Metric | Before (Baseline) | After (Phase 1) | Improvement |
|--------|-------------------|-----------------|-------------|
| **TP** | 0 | 8-12 | ∞ (0→positive) |
| **Precision** | 0% | 50-80% | +50-80% |
| **MCC** | -0.0001 | 0.1-0.4 | +0.1-0.4 |
| **FPR** | 0.00003 | <1% | Acceptable |

### Dataset-Specific Targets
- **CADETS_E3**: 10 TP, 0-2 FP (paper: 10 TP, 0 FP)
- **THEIA_E3**: 4-8 TP, 0-2 FP (paper: 4 TP, 0 FP)
- **CLEARSCOPE_E3**: 1-2 TP, 0-5 FP (paper: 1 TP, 1 FP)

---

## 🧪 Testing Instructions

### Quick Test (1 job, 1 hour)
```bash
cd /home/dunguyen/git/PIDSMaker
sbatch scripts/run_orthrus_default_cadets_e3_milan_cpu_apptainer.slurm

# Monitor
JOBID=$(squeue -u dunguyen -h -o "%i" | head -1)
watch -n 30 "squeue -u dunguyen -j $JOBID"
tail -f /fred/oz411/dunguyen/slurm-logs/orthrus_default_cadets_e3_milan_cpu_${JOBID}.out
```

**Look for in logs**:
```
[Node-based] Thresholds: MEAN=X.XX, STD=Y.YY, MAX=Z.ZZ
K-means clustering: N suspicious nodes -> 2 clusters
  Cluster 0: X nodes, mean score A.AAA ✓ SELECTED
  Cluster 1: Y nodes, mean score B.BBB   ignored
```

### Full Re-run (36 jobs, 4-12 hours)
```bash
# Cancel pending jobs with old config
scancel -u dunguyen -t PD

# Resubmit all
cd /home/dunguyen/git/PIDSMaker/scripts
./submit_all_e3_milan_gpu.sh   # 18 GPU jobs
./submit_all_e3_milan_cpu.sh   # 18 CPU jobs
```

---

## ✅ Success Criteria

**Phase 1 succeeds if:**
1. ✅ Non-zero true positives detected
2. ✅ Precision > 50% (vs 0%)
3. ✅ MCC > 0.1 (vs -0.0001)
4. ✅ Logs show node-based thresholds and k-means clustering

**If successful, proceed to:**
- **Phase 2**: Implement reconstruction pipeline (15-min windows, causality tracing, DAG, criticality scoring)
- **Target**: ORTHRUS-full performance (25 TP, 23 FP, 52% precision)

---

## 📚 References

All implementations follow:
- **ORTHRUS §4.4**: Threshold selection methodology
- **ORTHRUS Eq. 10**: Node anomaly score definition
- **ORTHRUS Appendix A, Table 8**: Dataset splits
- **ORTHRUS §4.3**: Stateless encoder (no TGN memory)

---

## 🎉 Implementation Status

- [x] Bug identification and root cause analysis
- [x] Dataset split correction
- [x] Per-node score aggregation
- [x] Node-based threshold methods
- [x] K-means clustering rewrite
- [x] Config updates
- [x] Documentation
- [ ] Testing (next step)
- [ ] Phase 2 (conditional on Phase 1 success)

**Total time**: 2 hours  
**Files modified**: 3  
**Lines added**: ~180  
**Lines modified**: ~40

---

**Ready to test!** 🚀
