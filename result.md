# PIDSMaker (Orthrus) Results - CADETS_E3 on OzSTAR

This document summarizes the results from running Orthrus on the CADETS_E3 dataset on OzSTAR's GPU compute nodes.

## Job Information

**Job ID:** 6357922  
**Node:** gina17 (milan-gpu partition, A100 GPU)  
**Started:** October 20, 2025 at 23:21:23 AEDT  
**Completed:** October 21, 2025 at ~00:25:00 AEDT  
**Total Runtime:** ~63-65 minutes  
**Status:** ✅ COMPLETED successfully

## Configuration

**Hardware Allocation:**
- GPU: 1x NVIDIA A100
- CPU: 4 cores
- RAM: 96 GB
- Node-local storage: 50 GB
- Time limit: 2 hours

**Software Stack:**
- Container: Apptainer/Singularity (pidsmaker_cuda117.sif, 6.15GB)
- CUDA: 11.7
- PyTorch: 1.13.1+cu117
- PyTorch Geometric: 2.5.3
- PostgreSQL: 17 (node-local on port 55432)
- W&B: 0.16.6 (offline mode)

**Model Configuration:**
- Model: Orthrus (config/orthrus.yml)
- Word2Vec embedding dim: 128
- Node hidden dim: 128, output dim: 64
- TGN memory dim: 100, time dim: 100
- TGN neighbor size: 10 (reduced from default 20)
- Intra-graph batch size: 256 (reduced from default 1024)
- Training epochs: 12 (max), patience: 3
- Learning rate: 0.00001

## Performance Metrics

### Timing Breakdown (seconds)

| Stage | Time (s) | Time (min) | % of Total |
|-------|----------|------------|------------|
| Build graphs | 163.41 | 2.7 | 4.3% |
| Transformation | 0.54 | 0.0 | 0.0% |
| Feat training (Word2Vec) | 12.46 | 0.2 | 0.3% |
| Feat inference | 203.50 | 3.4 | 5.4% |
| Graph preprocessing | 0.04 | 0.0 | 0.0% |
| **GNN training** | **2712.34** | **45.2** | **71.6%** |
| Evaluation | 582.19 | 9.7 | 15.4% |
| Tracing | 0.08 | 0.0 | 0.0% |
| **Total** | **~3785** | **~63** | **100%** |

### Memory Usage

| Metric | Value |
|--------|-------|
| Peak GPU memory (training) | 1.802 GB |
| Peak GPU memory (inference) | 0.114 GB |
| Peak CPU memory (training) | 0.079 GB |
| Peak CPU memory (inference) | 0.085 GB |
| System RAM allocated | 96 GB |
| System RAM peak usage | <96 GB (successful completion) |

### Training Metrics

| Metric | Value |
|--------|-------|
| Total epochs completed | 11 |
| Final training loss | 0.4668 |
| Final validation loss | 0.4967 |
| Final test loss | 0.4908 |
| Train epoch time (avg) | 153.69 s |
| Time per batch (inference) | 0.007 s |

## Detection Results (Best Epoch)

### Confusion Matrix

| | Predicted Benign | Predicted Malicious |
|---|------------------|---------------------|
| **Actually Benign** | 281,508 (TN) | 9 (FP) |
| **Actually Malicious** | 68 (FN) | 0 (TP) |

### Classification Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **True Positives (TP)** | 0 | Correctly detected attacks |
| **False Positives (FP)** | 9 | Benign nodes flagged as malicious |
| **True Negatives (TN)** | 281,508 | Correctly identified benign nodes |
| **False Negatives (FN)** | 68 | Missed attacks |
| **Precision** | 0.0 | TP / (TP + FP) |
| **Recall** | 0.0 | TP / (TP + FN) |
| **F-Score** | 0.0 | Harmonic mean of precision and recall |
| **False Positive Rate** | 3e-05 | FP / (FP + TN) |
| **Accuracy** | 0.99974 | (TP + TN) / Total |
| **Balanced Accuracy** | 0.49999 | Average of TPR and TNR |
| **MCC** | -9e-05 | Matthews Correlation Coefficient |
| **AUC** | 0.81052 | Area Under ROC Curve |
| **Average Precision** | 0.03314 | Area under precision-recall curve |

### Attack Detection Analysis

| Metric | Value |
|--------|-------|
| Percent detected attacks | 0% |
| Attacks in dataset | 3 (confirmed) |
| TP per attack 0 | 0 |
| TP per attack 1 | 0 |
| TP per attack 2 | 0 |
| Discrimination score | -0.2017 |

### Projected Metrics (If All Attacks Detected)

| Metric | Value |
|--------|-------|
| Projected TPs | 17 |
| Projected FPs | 111 |
| Projected Precision | 0.13281 |
| Projected Recall | 0.22667 |
| ADP Score | 0.124 |

## Comparison to Paper Results

### Paper: ORTHRUS-full on E3-CADETS

| Metric | Paper | This Run | Delta |
|--------|-------|----------|-------|
| TP | 25 | 0 | -25 |
| FP | 23 | 9 | -14 |
| TN | 268,062 | 281,508 | +13,446 |
| FN | 43 | 68 | +25 |
| Precision | 0.52 | 0.0 | -0.52 |
| MCC | 0.44 | -0.00009 | -0.44009 |
| Training Time | 4min40s | 45min12s | +40min32s |
| Testing Time | 52min31s | 9min42s | -42min49s |
| GPU Memory | 3.82GB | 1.80GB | -2.02GB |

### Analysis of Differences

**Why detection performance differs:**
1. **Threshold selection:** Using MAX threshold strategy (very conservative) resulted in 0 TPs
2. **Modified hyperparameters:** 
   - Our config uses larger embedding dimensions (128 vs likely 32 in paper)
   - Reduced TGN parameters to manage RAM usage
   - Different training dynamics due to model size
3. **Threshold tuning needed:** The evaluation shows AUC of 0.81, suggesting the model learned some signal but the detection threshold is poorly calibrated

**Why training time differs:**
- Paper: 4min40s (likely with smaller embedding dimensions: 32)
- Our run: 45min12s (with larger dimensions: 128, 4x more parameters)
- Word2Vec embedding training scales with dimension size
- GNN training also scales with hidden dimensions

**Why GPU memory is lower:**
- Our batch sizes were reduced to manage system RAM (256 vs 1024)
- Smaller batches = less GPU memory but longer training time

**Why testing time is faster:**
- Likely due to different evaluation configurations
- Our run evaluated multiple epoch checkpoints in parallel or used faster evaluation methods

## Lessons Learned

### What Worked

1. ✅ **96GB RAM allocation:** Successfully handled TGN neighbor graph construction for 2.68M nodes
2. ✅ **Node-local PostgreSQL:** Avoided /fred inode pressure and provided fast database access
3. ✅ **Containerized stack:** Eliminated dependency issues and network restrictions on compute nodes
4. ✅ **W&B offline mode:** Collected all metrics and artifacts without network access
5. ✅ **Telemetry (heartbeats, GPU stats):** Provided visibility into long-running job

### What Needs Improvement

1. ❌ **Detection performance:** 0 TP indicates threshold calibration or model tuning issues
2. ⚠️ **Hyperparameter mismatch:** Our config doesn't match paper's baseline settings
3. ⚠️ **Training time:** 10x slower than paper (45min vs 4.5min) due to larger model
4. ⚠️ **Evaluation strategy:** Need to explore different threshold selection methods beyond MAX

### Recommendations for Next Runs

1. **Match paper's hyperparameters exactly:**
   - Reduce `emb_dim` to 32 (from 128)
   - Reduce `node_hid_dim` to 32 (from 128)
   - Reduce `node_out_dim` to 16 (from 64)
   - Reduce `tgn_memory_dim` and `tgn_time_dim` to 32-50 (from 100)
   - Restore original batch sizes if RAM permits

2. **Improve threshold selection:**
   - Try `threshold_method: best_val_loss` or adaptive thresholds
   - Experiment with percentile-based thresholds (90th, 95th, 99th)
   - Use validation set for threshold tuning

3. **Validate model learning:**
   - Check loss curves for convergence
   - Inspect attention weights and embeddings
   - Verify ground truth labels are loaded correctly

4. **Performance optimization:**
   - If RAM usage stays well below 96GB, try increasing batch sizes back to defaults
   - Consider reducing epochs with stricter early stopping (patience=2)

## Artifacts and Outputs

**Location:** `~/slurm-logs/orthus_cadets_e3_ctn_6357922.tar.gz`

**Contents:**
- `/artifacts/` - All pipeline outputs
  - `featurization/` - Word2Vec models and embeddings
  - `detection/gnn_training/` - Trained GNN model checkpoints
  - `detection/evaluation/` - Confusion matrices, PR curves, ROC curves, results.pth
- `/wandb/` - W&B offline run data
  - `offline-run-20251020_122255-f5vstcxm/`

**Logs:**
- Stdout: `~/slurm-logs/orthus_cadets_e3_ctn_6357922.out`
- Stderr: `~/slurm-logs/orthus_cadets_e3_ctn_6357922.err`
- GPU stats: `~/slurm-logs/gpu_stats_6357922.log`

**To extract and sync:**
```bash
./scripts/sync_wandb_run.sh 6357922
```

## Conclusion

Job 6357922 represents the **first successful end-to-end run** of PIDSMaker (Orthrus) on OzSTAR's GPU infrastructure for the CADETS_E3 dataset. While detection performance (0 TP) indicates the model configuration needs tuning to match the paper's results, the run validates that:

1. The infrastructure can handle the full pipeline
2. GPU acceleration works correctly (1.8GB VRAM usage)
3. TGN neighbor graph construction completes with 96GB RAM
4. All metrics and artifacts are successfully captured

Next steps should focus on matching the paper's exact hyperparameters to achieve comparable detection performance (25 TP, 0.52 precision, 0.44 MCC) while maintaining the infrastructure stability demonstrated in this run.
