# PIDSMaker (Orthrus) Results — CADETS_E3 on OzSTAR

This document consolidates every recent Orthrus run on OzSTAR for the CADETS_E3 dataset. It replaces the per-job result files so the history lives in one place.

## Run summary

| Job ID | Date (AEDT) | Configuration | Threshold method | Runtime | TP | FP | AUC | Notes |
|--------|-------------|---------------|------------------|---------|----|----|-----|-------|
| 6357922 | 20 Oct 2025 | `config/orthrus.yml` (baseline) | `max_val_loss` | ~63 min | 0 | 9 | 0.81 | First end-to-end pipeline validation |
| 6358952 | 21 Oct 2025 | `config/orthrus_tuned.yml` (smaller model) | `mean_val_loss` (0.536) | 32m30s | 0 | 5 | 0.69 | Training sped up 2×; detection still zero |
| 6359088 | 21 Oct 2025 | `config/orthrus_tuned.yml` | `nodlink` (90th percentile, 0.82–1.48) | 33m58s | 0 | 10 | 0.84 | Percentile remained too high to surface attacks |
| 6361714 | 21 Oct 2025 | `config/orthrus_aggressive.yml` | `flash` (fixed 0.53) | 27m25s | 0 | 15 | 0.84 | Lower fixed threshold still above malicious losses |

## Job 6357922 – Baseline configuration

### Setup
- Node `gina17` (milan-gpu partition, NVIDIA A100)
- Resources: 1 GPU, 4 CPUs, 96 GB RAM, 50 GB tmp, 2 h limit
- Container: `/fred/oz396/dunguyen/containers/pidsmaker_cuda117.sif`
- Configuration: `orthrus.yml` (128-dim embeddings, reduced batch sizes)

### Performance breakdown

| Stage | Time (s) | Time (min) | Share |
|-------|----------|------------|-------|
| Build graphs | 163.41 | 2.7 | 4.3% |
| Transformation | 0.54 | 0.0 | 0.0% |
| Feature training (Word2Vec) | 12.46 | 0.2 | 0.3% |
| Feature inference | 203.50 | 3.4 | 5.4% |
| Graph preprocessing | 0.04 | 0.0 | 0.0% |
| GNN training | 2712.34 | 45.2 | 71.6% |
| Evaluation | 582.19 | 9.7 | 15.4% |
| Tracing | 0.08 | 0.0 | 0.0% |
| **Total** | **3785** | **63** | **100%** |

Memory usage: GPU 1.80 GB (train) / 0.11 GB (eval), CPU <0.1 GB for both phases, node RAM stayed below the 96 GB allocation.

### Detection metrics (best epoch)

Confusion matrix:

|                | Predicted benign | Predicted malicious |
|----------------|------------------|---------------------|
| Actually benign | 281,508 | 9 |
| Actually malicious | 68 | 0 |

Classification metrics:

| Metric | Value |
|--------|-------|
| Precision | 0.0 |
| Recall | 0.0 |
| F-score | 0.0 |
| False positive rate | 3.0e-05 |
| Accuracy | 0.99974 |
| Balanced accuracy | 0.49999 |
| MCC | -9.0e-05 |
| AUC | 0.81052 |
| Average precision | 0.03314 |

### Observations
- Infrastructure was validated end-to-end: containers, node-local PostgreSQL, and telemetry all worked.
- Training completed 11 epochs with stable loss curves, proving the model is learning something.
- Detection failed because `max_val_loss` produced an overly conservative threshold; every malicious node sat below it.
- Training was ~10× slower than reported in the paper, largely due to 128-dim embeddings and reduced batch sizes.

## Job 6358952 – Optimized hyperparameters

### Configuration changes vs. 6357922

| Component | 6357922 | 6358952 |
|-----------|---------|---------|
| Embedding dimension | 128 | 32 |
| Node hidden / output dim | 128 / 64 | 32 / 16 |
| TGN memory / time dim | 100 / 100 | 50 / 50 |
| Batch size | 256 | 1024 |
| TGN neighbor size | 10 | 20 |
| Threshold method | `max_val_loss` | `mean_val_loss` |

### Performance comparison

| Metric | 6357922 | 6358952 | Change |
|--------|---------|---------|--------|
| Total runtime | 65 min | 32.5 min | 2× faster |
| GNN training | 45 min | 14 min | 3.2× faster |
| Evaluation | ~9.7 min | ~6.0 min | Slightly slower (more epochs considered) |
| Peak GPU memory | 1.80 GB | 1.27 GB | 29% lower |

Training loss dropped from 1.48 to 0.54 over 12 epochs, matching expectations for the smaller model.

### Detection metrics (best epoch, threshold 0.536)

| Metric | Value |
|--------|-------|
| TP / FP / TN / FN | 0 / 5 / 281,512 / 68 |
| Precision | 0.0 |
| Recall | 0.0 |
| AUC | 0.689 |
| MCC | -0.00007 |

### Observations
- Architectural tuning achieved the desired speed and memory reductions.
- `mean_val_loss` remained too conservative; most malicious nodes continue to have losses below 0.5.
- The run confirms the model can learn useful representations (AUC ~0.69) but the post-processing threshold is still the bottleneck.

## Job 6359088 – Nodlink percentile threshold

### Goal
Replace the average-loss threshold with the NodLink 90th percentile method to lower the cutoff.

### Outcome
- Runtime: 33 minutes 58 seconds on node `gina2`.
- Observed thresholds per epoch: 1.48 → 0.82 (still higher than most malicious losses).
- Detection metrics at the chosen epoch: TP 0, FP 10, TN 281,507, FN 68, AUC 0.835.
- Conclusion: the percentile remains too high for CADETS_E3; detection stays at zero despite healthy AUC.

### Notes
- Artifacts archived at `~/slurm-logs/orthus_cadets_e3_ctn_6359088.tar.gz`.
- Next iteration needs a genuinely low threshold or a manual sweep.

## Job 6361714 – Flash threshold (aggressive config)

### Goal
Use the `flash` method (fixed threshold 0.53) and enlarge `kmeans_top_K` to 50 to force more detections.

### Outcome
- Runtime: 27 minutes 25 seconds on node `gina16` (fastest run so far).
- Detection metrics at epoch 11: TP 0, FP 15, TN 281,502, FN 68, AUC 0.836.
- Despite the lower threshold, nearly every malicious node still falls below 0.53, so recall is unchanged.

### Notes
- Artifacts archived at `~/slurm-logs/orthus_cadets_e3_ctn_6361714.tar.gz`.
- W&B offline run: `/tmp/pids_run_6361714/wandb/offline-run-20251021_010140-c1xixj7q` (sync via `wandb sync` from login node).

## Key takeaways
- Infrastructure is stable: every run since 6357922 has completed within 34 minutes, with consistent GPU/CPU usage and packaged artifacts.
- All three threshold strategies tried (`max_val_loss`, `mean_val_loss`, `nodlink`, `flash`) deliver zero true positives, proving the cutoffs are still far above the malicious node loss distribution.
- AUC values between 0.69 and 0.84 indicate the model encodes useful signal; the issue is solely threshold calibration.
- Next experiments should focus on data-driven thresholds (percentile sweep, ROC-derived cut points, or top-K) and potentially post-processing (e.g., per-time-window normalization) rather than further architectural tweaks.

## Artifact locations

| Job ID | Tarball |
|--------|---------|
| 6357922 | `~/slurm-logs/orthus_cadets_e3_ctn_6357922.tar.gz` |
| 6358952 | `~/slurm-logs/orthus_cadets_e3_ctn_6358952.tar.gz` |
| 6359088 | `~/slurm-logs/orthus_cadets_e3_ctn_6359088.tar.gz` |
| 6361714 | `~/slurm-logs/orthus_cadets_e3_ctn_6361714.tar.gz` |

Each archive contains the `artifacts/`, `wandb/`, `gpu_stats.log`, and standard output log captured during the run.
