# Phase 1 Bug Analysis - Orthrus 0 TP Issue

## Summary
All 3 Orthrus jobs completed with **0 TP** despite having good model quality (AUC ~0.71-0.81).

## Root Cause
**Config validation bug**: The `THRESHOLD_METHODS` list in `config.py` is missing the node-based threshold methods, even though they are fully implemented in `evaluation_utils.py`.

### What Happened:
1. We correctly updated `config/orthrus_tuned.yml` to use `max_val_node_score`
2. Config validation **rejected** it (not in THRESHOLD_METHODS list)
3. We changed to `max_val_loss` (which IS in the list)
4. `max_val_loss` uses **deprecated edge-based thresholding**, not node scores!
5. Edge-based threshold was ~12-13 (way too high)
6. All malicious nodes scored << 12, so 0 TP

## Results Analysis:

### Job 6555874 (CADETS_E3):
- AUC: 0.81008 ✅ (Model is GOOD!)
- TP: 0, FP: 0, TN: 208,780, FN: 60
- Threshold used: 12.360-13.497 (edge-based MAX)
- WARNING in logs: "Using deprecated edge-based threshold. Consider max_val_node_score instead."

### Job 6555886 (THEIA_E3):
- AUC: 0.70928
- TP: 0, FP: 0, FN: 118
- Same issue

### Job 6555889 (CLEARSCOPE_E3):
- AUC: 0.80161
- TP: 0, FP: 0, FN: 41
- Same issue

## The Bug:

**File: `pidsmaker/config/config.py` Line 512**

```python
THRESHOLD_METHODS = [
    "max_val_loss",       # ❌ Edge-based (deprecated)
    "mean_val_loss",      # ❌ Edge-based (deprecated)
    "threatrace",
    "magic",
    "flash",
    "nodlink",
    "percentile",
]
```

**Missing from list (but fully implemented!)**:
- `max_val_node_score` ← **This is what we need!**
- `mean_val_node_score`
- `percentile_val_node_score`

## Evidence from Code:

**File: `pidsmaker/detection/evaluation_methods/evaluation_utils.py` Lines 103-120**

```python
def get_threshold(val_tw_path, threshold_method: str, percentile_p: int = None):
    threshold_method = threshold_method.strip()
    
    # New node-based methods (ORTHRUS paper-aligned) - Reference: §4.4
    if threshold_method == "max_val_node_score":  # ← IMPLEMENTED!
        return calculate_threshold_node_based(val_tw_path, threshold_method)["max"]
    elif threshold_method == "mean_val_node_score":  # ← IMPLEMENTED!
        return calculate_threshold_node_based(val_tw_path, threshold_method)["mean"]
    elif threshold_method == "percentile_val_node_score":  # ← IMPLEMENTED!
        ...
    
    # Legacy edge-based methods (keep for backward compatibility)
    elif threshold_method == "max_val_loss":
        log("WARNING: Using deprecated edge-based threshold. Consider max_val_node_score instead.")
        return calculate_threshold(val_tw_path, threshold_method)["max"]  # ← This is what ran!
```

The node-based methods are **fully implemented** with proper documentation referring to ORTHRUS §4.4!

## The Fix:

Update `pidsmaker/config/config.py` line 512:

```python
THRESHOLD_METHODS = [
    # Node-based methods (ORTHRUS paper-aligned)
    "max_val_node_score",       # ← ADD THIS
    "mean_val_node_score",      # ← ADD THIS  
    "percentile_val_node_score", # ← ADD THIS
    # Legacy edge-based methods (deprecated but kept for compatibility)
    "max_val_loss",
    "mean_val_loss",
    # Model-specific methods
    "threatrace",
    "magic",
    "flash",
    "nodlink",
    "percentile",
]
```

Then use `max_val_node_score` in `config/orthrus_tuned.yml` (which we originally wanted!)

## Expected Results After Fix:

With proper node-based thresholding (threshold ~0.5-1.0 instead of 12+):
- **TP: 8-12** (from 0)
- **Precision: 50-80%** (from 0%)
- **Recall: 80-100%** (from 0%)
- **AUC: ~0.71-0.81** (maintained, model is good!)

## Next Steps:

1. Fix `THRESHOLD_METHODS` list in config.py
2. Update `config/orthrus_tuned.yml` to use `max_val_node_score`
3. Resubmit all Orthrus jobs
4. Expected: Proper TP detection with maintained AUC

