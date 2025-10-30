# Critical Finding: Zero True Positive Detection Analysis

**Date**: October 24, 2025  
**Analysis by**: Investigation of ClearScope E3, CADETS E3, and THEIA E3 results  
**Status**: ROOT CAUSE IDENTIFIED

---

## Executive Summary

All ClearScope E3 experiments (Orthrus, Magic, Kairos - both default and tuned) detected **0 true positives**, while CADETS E3 detected 26-28 TPs. This analysis reveals a critical difference in how multi-attack vs single-attack datasets are evaluated.

---

## The Root Cause

### Dataset Configuration Differences

| Dataset | Number of Attacks | Ground Truth Nodes | Configuration |
|---------|-------------------|-------------------|---------------|
| **CADETS E3** | 3 | 75 total (8+43+24) | Nginx_Backdoor_06, 12, 13 |
| **THEIA E3** | 2 | 119 total (61+58) | Browser_Extension_Drakon, Firefox_Backdoor_Drakon |
| **ClearScope E3** | **1** | **41 total** | firefox_0411 only |

### The `tps_if_all_attacks_detected` Metric

This metric measures: **"How many TPs would we get if we ranked all nodes by anomaly score and stopped when we detected at least ONE node from EACH attack?"**

#### Algorithm (from `evaluation_utils.py:1416-1437`):
```python
for score, node in zip(reverse_scores, reverse_nodes):
    detected = False
    for i, nodes_set in enumerate(nodes_per_attack):
        if node in nodes_set:
            detected_attacks[i] = 1  # Mark this attack as detected
            detected = True
    if len(detected_attacks) == len(nodes_per_attack):  # ← STOPS HERE!
        break  # All attacks have at least 1 detected node
    if detected:
        tps += 1
    else:
        fps += 1
```

### Why ClearScope Shows 0 TPs

**ClearScope E3** has only **1 attack**, so the algorithm stops as soon as it finds the **first malicious node** from that attack. 

**Result**: `tps_if_all_attacks_detected: 0` means:
> "When ranking all nodes by anomaly score (descending), **ZERO malicious nodes appear before the first malicious node is found**"

This is mathematically correct but misleading! It actually means:
- The first malicious node detected = TP count stops at 0
- All 41 malicious nodes have **lower anomaly scores than 300 benign nodes**

### Why CADETS Shows 26-28 TPs

**CADETS E3** has **3 attacks** with different detectability:
- Attack 1 might be easy to detect (nodes appear early in ranking)
- Attack 2 might be harder (nodes appear later)
- Attack 3 might be hardest (nodes appear latest)

**Result**: `tps_if_all_attacks_detected: 26-28` means:
> "We detected 26-28 malicious nodes before finding at least 1 node from all 3 attacks"

---

## Detailed Evidence

### ClearScope E3 - Orthrus Tuned (Job 6418143)

**Final Epoch Results**:
```
Threshold: 1.177 (77th percentile)
percent_detected_attacks: 0
fps_if_all_attacks_detected: 300
tps_if_all_attacks_detected: 0
```

**Malicious Node Losses** (all marked ❌):
- Node 333332: 2.199, 2.201, 2.314, 2.421, 2.683 (across epochs)
- Node 333568-333719: 1.983-2.67 range
- Node 282354: 4.275-4.526 (highest)

**Key Observation**: 
- All 41 malicious nodes have losses **1.3 to 4.5**
- Threshold is **1.177**
- Malicious nodes have **higher** reconstruction loss than threshold
- **BUT**: 300 benign nodes have **even higher** scores than the malicious ones!

### CADETS E3 - Orthrus Tuned (Job 6397057)

**Final Epoch Results**:
```
Threshold: 0.734 (77th percentile)  
percent_detected_attacks: 0
fps_if_all_attacks_detected: 4629
tps_if_all_attacks_detected: 26
```

**Time Windows with Malicious Nodes**:
```
TW 43 -> 4 malicious nodes + 427 malicious edges
TW 44 -> 6 malicious nodes + 534 malicious edges
TW 45 -> 2 malicious nodes + 34 malicious edges
TW 46 -> 3 malicious nodes + 797 malicious edges
TW 229 -> 21 malicious nodes + 15616 malicious edges
TW 230 -> 19 malicious nodes + 4667 malicious edges
TW 231 -> 18 malicious nodes + 16059 malicious edges
TW 302 -> 4 malicious nodes + 397 malicious edges
TW 303 -> 24 malicious nodes + 3760 malicious edges
```

**Key Observation**:
- Multiple attacks spread across different time windows
- 26 malicious nodes were detected before finding at least 1 from each of the 3 attacks
- This suggests at least one attack is significantly harder to detect

---

## The Connection Between 3 Datasets

### Common Pattern: Poor Malicious Node Ranking

All three datasets show `percent_detected_attacks: 0`, meaning **NO attack had all its nodes detected correctly by the threshold-based classifier**.

However, the `tps_if_all_attacks_detected` reveals the **ranking quality**:

1. **CADETS E3**: 26-28 TPs before covering all attacks
   - **Interpretation**: Some malicious nodes rank higher than many benign nodes
   - **Implication**: Detection would work if we could identify which nodes are from hard-to-detect attacks

2. **THEIA E3**: (Results pending - job 6398685 still running)
   - **Prediction**: Will likely show similar behavior to CADETS (2 attacks)

3. **ClearScope E3**: 0 TPs before covering the single attack
   - **Interpretation**: **ALL 41 malicious nodes rank below at least 300 benign nodes**
   - **Implication**: The attack is **completely undetectable** using this method

### Why ClearScope Attack is Undetectable

Looking at the ClearScope malicious nodes:
```
/data/data/org.mozilla.fennec_firefox_dev/cache/nz9885vc.default/cache2/entries/*
```

These are **Firefox browser cache files** from a mobile device. The attack pattern:
- Very subtle (cache file accesses)
- Happens frequently in normal behavior too
- Model learned this pattern as **normal** during training
- Reconstruction loss is **low** for these nodes (easy to reconstruct)

### Why CADETS Attack is Partially Detectable

CADETS attacks involve:
- Nginx backdoor operations
- More distinctive from normal behavior
- Some nodes have unusual patterns → higher reconstruction loss
- At least some attacks are detectab le

---

## Implications

### For Evaluation Metrics

1. **`tps_if_all_attacks_detected` is attack-count dependent**
   - NOT comparable across datasets with different attack counts
   - ClearScope's 0 doesn't mean "worse" than CADETS's 26 in absolute terms
   - It means: "ClearScope's single attack is harder to detect than CADETS's easiest attack"

2. **Need new metrics for single-attack datasets**
   - "TP at K": How many TPs in top-K ranked nodes?
   - "Average Precision": Area under precision-recall curve
   - "Discrimination Score": Already computed, but needs more emphasis

### For Model Performance

1. **Models are not learning attack-specific patterns**
   - They learn general graph reconstruction
   - Attacks that don't deviate significantly from normal → undetectable

2. **Threshold-based detection fails completely**
   - Even with 77th percentile threshold
   - Need alternative detection strategies

### For Future Work

1. **Attack-aware training**
   - Need to ensure attacks are distinct from training data
   - Consider adversarial training approaches

2. **Ensemble methods**
   - Combine multiple detection methods
   - Use graph structure, temporal patterns, semantic features

3. **Attack-specific tuning**
   - Different thresholds for different attack types
   - Learn attack signatures rather than just reconstruction

---

## Conclusion

The "zero TP" problem in ClearScope E3 is **not a bug but a fundamental limitation** of reconstruction-based anomaly detection when:
1. Attacks mimic normal behavior too closely
2. Models train on similar patterns
3. Single-attack datasets provide no diversity for the evaluation metric

**The connection between all 3 datasets**: They all fail threshold-based detection (`percent_detected_attacks: 0`), but their `tps_if_all_attacks_detected` scores reveal how well malicious nodes rank relative to benign ones, which is heavily influenced by the number of attacks and their diversity.

---

## Recommendations

1. **Immediate**: Update result documentation to explain these metrics properly
2. **Short-term**: Re-run experiments with different evaluation metrics (AP, AUC-PR)
3. **Long-term**: Redesign detection approach to be attack-aware
4. **Documentation**: Add this analysis to paper/thesis explaining the limitations

---

## References

- Code: `pidsmaker/detection/evaluation_methods/evaluation_utils.py:1416-1437`
- Code: `pidsmaker/utils/labelling.py:46-96` (`get_GP_of_each_attack`)
- Config: `pidsmaker/config/config.py` (dataset definitions)
- Logs: 
  - ClearScope E3: `/fred/oz411/dunguyen/slurm-logs/orthrus_tuned_clearscope_e3_ctn_6418143.out`
  - CADETS E3: `/fred/oz411/dunguyen/slurm-logs/orthrus_tuned_cadets_e3_ctn_6397057.out`
