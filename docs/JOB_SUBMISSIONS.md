# Job Submission Records

This document tracks all significant job submissions, their status, and outcomes for the PIDSMaker project on OzSTAR.

---

## Phase 1 Overnight Run - Final Submission

**Date**: October 31, 2025 @ 01:07 AEDT  
**Total**: 23 jobs (10 CPU running + 13 GPU pending)

### Complete Breakdown

#### CADETS_E3 (8 jobs: 4 CPU running + 4 GPU pending)

**CPU Jobs:**
- ✅ 6554367 - Kairos (3:10 elapsed, ~50min remaining)
- ✅ 6555846 - Magic Baseline (40min elapsed)
- ✅ 6555847 - Magic Adaptive (40min elapsed)
- ✅ 6555874 - Orthrus (19min elapsed)

**GPU Jobs (Pending):**
- ⏳ 6555870 - Orthrus
- ⏳ 6555871 - Kairos
- ⏳ 6555872 - Magic Baseline
- ⏳ 6555873 - Magic Adaptive

#### THEIA_E3 (9 jobs: 3 CPU running + 6 GPU pending)

**CPU Jobs (Backup):**
- ✅ 6555886 - Orthrus
- ✅ 6555887 - Kairos
- ✅ 6555888 - Magic

**GPU Jobs (Pending):**
- ⏳ 6555877 - Orthrus (duplicate)
- ⏳ 6555879 - Orthrus
- ⏳ 6555880 - Kairos
- ⏳ 6555881 - Magic

#### CLEARSCOPE_E3 (10 jobs: 4 CPU running + 6 GPU pending)

**CPU Jobs (Backup):**
- ✅ 6555889 - Orthrus
- ✅ 6555890 - Kairos
- ✅ 6555891 - Magic
- ✅ 6551632 - Kairos (old job, 17min elapsed)

**GPU Jobs (Pending):**
- ⏳ 6555878 - Orthrus (duplicate)
- ⏳ 6555882 - Orthrus
- ⏳ 6555883 - Kairos
- ⏳ 6555884 - Magic

### Strategy
- ✅ GPU jobs run first (faster: 15-30 min)
- ✅ CPU jobs as backup (slower: 1-2 hours each)
- ✅ Whichever finishes first gives results
- ✅ Can cancel slower jobs once results available

### All Bugs Fixed
- ✅ Bug #1: Magic function signature (commit e68780a)
- ✅ Bug #2: Missing typing import (commit 0dc65c1)
- ✅ Bug #3: CSV column mismatch (commit a43cc44)
- ✅ Bug #4: Orthrus config validation (commit f45d815)

### Expected Results (Morning 08:00 AEDT)

**All 3 datasets × 3-4 models = ~11 experiments complete**

**CADETS_E3:**
- ✅ Orthrus (fixed config!)
- ✅ Kairos
- ✅ Magic Baseline
- ✅ Magic Adaptive

**THEIA_E3:**
- ✅ Orthrus
- ✅ Kairos
- ✅ Magic

**CLEARSCOPE_E3:**
- ✅ Orthrus
- ✅ Kairos
- ✅ Magic

---

## Phase 1 Initial Submission

**Date**: October 31, 2025 @ 01:04 AEDT  
**Total**: 17 Phase 1 jobs (+ 1 old Clearscope)

### Breakdown by Dataset

#### CADETS_E3 (4 CPU + 4 GPU = 8 jobs)

**CPU Jobs (Running):**
- 6554367 - Kairos (3:08 elapsed, ~50min remaining)
- 6555846 - Magic Baseline (37min elapsed)
- 6555847 - Magic Adaptive (37min elapsed)
- 6555874 - Orthrus (17min elapsed)

**GPU Jobs (Pending):**
- 6555870 - Orthrus
- 6555871 - Kairos
- 6555872 - Magic Baseline
- 6555873 - Magic Adaptive

#### THEIA_E3 (3 GPU jobs)
- 6555877 - Orthrus (duplicate submitted)
- 6555879 - Orthrus
- 6555880 - Kairos
- 6555881 - Magic

#### CLEARSCOPE_E3 (3 GPU jobs + 1 old)
- 6555882 - Orthrus (duplicate submitted)
- 6555883 - Kairos
- 6555884 - Magic
- 6551632 - Kairos (old job, 14min elapsed)

### Bugs Fixed
- ✅ Bug #1: Magic function signature mismatch (commit e68780a)
- ✅ Bug #2: Missing typing import (commit 0dc65c1)
- ✅ Bug #3: CSV column mismatch (commit a43cc44)
- ✅ Bug #4: Orthrus config validation - max_val_loss (commit f45d815)

### Known Issues
- Some duplicate Orthrus jobs submitted (6555877, 6555882) - can cancel if needed
- CPU jobs take longer than GPU - GPU results should be ready first

---

## Batch 2: Reproduction-Aligned Configuration

**Date**: October 29, 2025  
**Jobs**: 6531376-6531396 (18 jobs total)

### Configuration Changes Applied

**ORTHRUS:**
- `kmeans_top_K`: 30 → 100 (capture more anomaly candidates)
- `percentile_p`: 77 → 90 (more sensitive threshold in tuned config)

**KAIROS:**
- `used_method`: node_evaluation → queue_evaluation (queue-level detection)

**MAGIC:**
- `mask_rate`: 0.5 → 0.4 (minor tuning within paper's recommended range)

### Job Mapping
```
CADETS_E3:     6531376-6531384 (orthrus default/tuned, magic default/tuned, kairos default/tuned)
THEIA_E3:      6531385-6531390 (orthrus default/tuned, magic default/tuned, kairos default/tuned)
CLEARSCOPE_E3: 6531391-6531396 (orthrus default/tuned, magic default/tuned, kairos default/tuned)
```

### Status
- All PENDING awaiting scheduler
- Runtime: 1-2.5 hours per job expected

---

## Third Round: Corrected Dataset Casing

**Date**: October 23, 2025  
**Status**: All PENDING (Priority)

### Jobs Submitted
```bash
sbatch scripts/run_orthrus_tuned_cadets_e3_apptainer.slurm  # JobID 6396666
sbatch scripts/run_magic_tuned_cadets_e3_apptainer.slurm    # JobID 6396667
sbatch scripts/run_kairos_tuned_cadets_e3_apptainer.slurm   # JobID 6396668
sbatch scripts/run_orthrus_tuned_theia_e3_apptainer.slurm   # JobID 6396669
sbatch scripts/run_magic_tuned_theia_e3_apptainer.slurm     # JobID 6396670
sbatch scripts/run_kairos_tuned_theia_e3_apptainer.slurm    # JobID 6396671
```

### Fixes Applied
- Uppercase dataset names (CADETS_E3, THEIA_E3)
- Positional CLI args
- NLTK offline mode

### Resources
- **CADETS_E3**: 2 CPUs, 32GB RAM, 1h limit
- **THEIA_E3**: 2 CPUs, 48GB RAM, 1.5h limit
- **All**: milan-gpu partition, 1 GPU, node-local PostgreSQL

---

## Second Round: Dataset Case Mismatch (FAILED)

**Date**: October 22, 2025 16:32-16:38  
**Status**: All FAILED with ValueError: Unknown dataset cadets_e3  
**Issue**: Scripts passed lowercase `cadets_e3`/`theia_e3` but config expects uppercase

### Failed Jobs
- 6379295, 6379296, 6379297, 6379298, 6379301, 6379303

All showed: FAILED 1:0 after ~27s on gina7

---

## First Round: CLI Argument Errors (FAILED)

**Date**: October 22, 2025  
**Status**: All FAILED with argparse errors  
**Issue**: Used `--config`, `--dataset`, `--output_dir` flags instead of positional args

### Failed Jobs
- 6378640-6378645

Error: `argparse.ArgumentTypeError: Unknown args ['--config', '--dataset', '--output_dir', ...]`

---

## Optimization Jobs

### Job 6358952: Optimized Run (Completed)

**Date**: October 21, 2025  
**Config**: config/orthrus_tuned.yml (optimized hyperparameters)  
**Status**: Completed in 32 minutes 30 seconds  
**Node**: gina2

**Optimizations Applied:**
- Embedding dim: 128 → 32 (4x reduction)
- Node dims: 128/64 → 32/16 (4x reduction)
- TGN dims: 100 → 50 (2x reduction)
- Batch size: 256 → 1024 (4x increase)
- Neighbor size: 10 → 20 (2x increase)
- Threshold: max_val_loss → mean_val_loss
- PostgreSQL: Node-local on /tmp for faster I/O

**Results:**
- Training speed: 32.5 min vs 65 min (2x faster)
- GPU memory: 1.27 GB vs 1.8 GB (29% reduction)
- GNN training: 14 min vs 45 min (3.2x faster)
- Detection: 0 TP (still broken)
- AUC: 0.70 (vs 0.81 in job 6357922)
- Threshold: mean_val_loss = 0.536 (still too high)

**Conclusion**: Speed optimization SUCCESS, detection FAILED

### Job 6357922: First Successful GPU Run (Completed)

**Date**: October 20, 2025  
**Config**: config/orthrus.yml (default configuration)  
**Status**: COMPLETED in 65 minutes

**Results:**
- Training successful but 0 TP detection
- Performance: 45 min GNN training, 1.8GB GPU memory, AUC=0.81
- Issue: max_val_loss threshold too conservative

---

## Failed Jobs - Lessons Learned

### Job 6357821: OUT_OF_MEMORY (48GB)
- **Date**: October 21, 2025
- **Failed**: After 10m20s during TGN neighbor graph construction
- **RAM**: Peaked at 38.2GB
- **Solution**: Increased to 96GB for next run

### Job 6357475: OUT_OF_MEMORY (24GB)
- **Date**: October 21, 2025
- **Failed**: After 8m48s during TGN neighbor graph construction
- **Solution**: Increased to 48GB for next run

### Job 6358595: PostgreSQL Startup Failed
- **Date**: October 21, 2025
- **Failed**: After 1 minute
- **Error**: PostgreSQL container startup failed (PostgreSQL not in container)
- **Issue**: Attempted to use container's PostgreSQL, but not installed

### Job 6356979: Missing psycopg2
- **Date**: October 21, 2025
- **Failed**: ModuleNotFoundError: psycopg2
- **Solution**: Added psycopg2-binary==2.9.9 to container and rebuilt

---

## Morning Quick Checks

```bash
# 1. Job status
squeue -u dunguyen

# 2. Check failures
sacct -u dunguyen -S 2025-10-30 | grep -i fail

# 3. Quick results check
grep -r "TP:" /fred/oz411/dunguyen/slurm-logs/*_6555*.out | head -20

# 4. View CADETS_E3 Orthrus
tail -100 /fred/oz411/dunguyen/slurm-logs/orthrus_tuned_cadets_e3_milan_*_6555870.out
# or CPU if GPU didn't start:
tail -100 /fred/oz411/dunguyen/slurm-logs/orthrus_tuned_cadets_e3_milan_cpu_6555874.out

# 5. Cancel redundant jobs if needed
# If GPU finished, cancel slower CPU:
scancel 6555886 6555887 6555888 6555889 6555890 6555891
```

---

## Results Locations

- **Logs**: `/fred/oz411/dunguyen/slurm-logs/*_6555*.out`
- **Artifacts**: `/fred/oz411/dunguyen/tmp/pidsmaker_*/artifacts/`
- **Documentation**: `/home/dunguyen/git/PIDSMaker/result.md`

---

**Last Updated**: October 31, 2025
