# PIDSMaker Commands and Operations Reference

This document contains all commands, scripts, and operational procedures for running PIDSMaker (Orthrus) on OzSTAR supercomputer.

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [PostgreSQL Management](#postgresql-management)
3. [Container Operations](#container-operations)
4. [Job Submission](#job-submission)
5. [Monitoring and Logs](#monitoring-and-logs)
6. [Post-Run Operations](#post-run-operations)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Repository and Directories

```bash
# Clone repository
git clone https://github.com/ubc-provenance/PIDSMaker.git
cd PIDSMaker

# Create directories on /fred for caches, logs, artifacts, and Postgres data
export FRED_BASE=/fred/oz411/dunguyen
mkdir -p $FRED_BASE/{containers,pids_logs,pids_artifacts,.apptainer/{cache,tmp},pg/{data,logs}}
```

### Environment Variables

```bash
# Set Apptainer cache and tmp to /fred
export APPTAINER_CACHEDIR=$FRED_BASE/.apptainer/cache
export APPTAINER_TMPDIR=$FRED_BASE/.apptainer/tmp

# Verify
echo $APPTAINER_CACHEDIR
echo $APPTAINER_TMPDIR
```

---

## PostgreSQL Management

### Initial Setup

```bash
# Initialize PG17 cluster
~/.conda/envs/pg17/bin/initdb -D $FRED_BASE/pg/data
```

### Start/Stop PostgreSQL

```bash
# Start PG17 server (login node or inside job)
~/.conda/envs/pg17/bin/pg_ctl -D $FRED_BASE/pg/data -l $FRED_BASE/pg/logs/postgres.log start

# Stop PG17 server (optional when done on login)
~/.conda/envs/pg17/bin/pg_ctl -D $FRED_BASE/pg/data stop

# Check status
~/.conda/envs/pg17/bin/pg_ctl -D $FRED_BASE/pg/data status
```

### Database Operations

```bash
# Create database
createdb -h 127.0.0.1 -U postgres cadets_e3

# Restore dataset from dump
pg_restore -h 127.0.0.1 -U postgres -d cadets_e3 /path/to/cadets_e3.dump

# Verify database
psql -h 127.0.0.1 -U postgres -d cadets_e3 -c "SELECT COUNT(*) FROM event_table;"
# Expected: 36,484,667 events for CADETS_E3

# Start with custom port (node-local)
pg_ctl -D /fred/oz411/dunguyen/pg/data -l /tmp/pg_temp.log -o "-p 55432" start
psql -h localhost -p 55432 -U postgres -d cadets_e3
```

### PostgreSQL 17 Reinstallation

```bash
# If pg17 conda environment was incomplete/removed
rm -rf /fred/oz411/dunguyen/.conda/envs/pg17
mamba create -n pg17 postgresql=17 -c conda-forge -y

# Verification
/fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_ctl --version
# Output: pg_ctl (PostgreSQL) 17.6
```

---

## Container Operations

### Build Container

```bash
# Build Apptainer image with CUDA 11.7, Torch 1.13.1+cu117, PyG 2.5.3
module load apptainer
apptainer build $FRED_BASE/containers/pidsmaker_cuda117.sif containers/pidsmaker_cuda117.def
```

### Verify Container

```bash
# Verify container Torch/CUDA (expected True for CUDA)
apptainer exec --nv $FRED_BASE/containers/pidsmaker_cuda117.sif \
  python -c "import torch; import torch_geometric as tg; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), tg.__version__)"
```

---

## Job Submission

### Single Job Submissions

```bash
# GPU job on Milan/A100 partition
sbatch scripts/run_orthus_cadets_e3_apptainer.slurm

# Skylake GPU partition
sbatch scripts/run_orthus_cadets_e3_apptainer_skylake.slurm

# Optimized job with tuned config
sbatch scripts/run_orthrus_tuned_cadets_e3_milan_gpu_apptainer.slurm
```

### Batch Submissions

```bash
# Submit all E3 datasets (18 jobs)
cd /home/dunguyen/git/PIDSMaker
bash scripts/submit_all_e3_jobs.sh

# Submit GPU jobs
./scripts/submit_all_e3_milan_gpu.sh

# Submit CPU jobs
./scripts/submit_all_e3_milan_cpu.sh
```

### Phase 1 Model Submissions

```bash
# Orthrus
sbatch scripts/run_orthrus_tuned_cadets_e3_milan_gpu_apptainer.slurm

# Kairos
sbatch scripts/run_kairos_phase1_cadets_e3_milan_gpu_apptainer.slurm

# Magic Baseline
sbatch scripts/run_magic_phase1_cadets_e3_milan_gpu_apptainer.slurm

# Magic Adaptive
sbatch scripts/run_magic_adaptive_cadets_e3_milan_gpu_apptainer.slurm
```

### Cancel Jobs

```bash
# Cancel specific jobs
scancel <JOBID1> <JOBID2>

# Cancel all pending jobs
scancel -u $USER -t PD

# Cancel all your jobs
scancel -u $USER
```

---

## Monitoring and Logs

### Queue Status

```bash
# Check all your jobs
squeue -u $USER

# Check specific jobs
squeue -j <JOBID1>,<JOBID2>

# Detailed format
squeue -j <JOBID> -o "%i %T %P %R %M %l %D %C %m %b %N"

# Watch queue (refresh every 30 seconds)
watch -n 30 'squeue -u $USER'
```

### Job Accounting

```bash
# Check job status
sacct -j <JOBID>

# Detailed format
sacct -j <JOBID> --format=JobID,State,ExitCode,Start,End,Elapsed,AllocTRES%45,NodeList

# Multiple jobs
sacct -j <JOBID1>,<JOBID2>,<JOBID3> --format=JobID,JobName%30,Partition,State,ExitCode,Start,End,Elapsed

# Last 24 hours
sacct -u $USER -X -S now-24hours --format=JobID,JobName%30,State,ExitCode,Start,End,Elapsed -n

# Count job states
sacct -u $USER -X -S now-24hours --format=State -n | awk '{g[$1]++} END {for(k in g) printf("%s %d\n", k, g[k])}' | sort
```

### Log Files

```bash
# Tail Slurm output
tail -f ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out

# Tail Slurm error
tail -f ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.err

# Check container logs
tail -f $FRED_BASE/pids_logs/orthus_cadets_e3_ctn_run_<JOBID>.log

# Check PostgreSQL logs
tail -n 200 /fred/oz411/dunguyen/pg/logs/postgres.log

# Monitor job continuously (custom script)
./scripts/monitor_job.sh <JOBID> [interval_seconds]
```

### Search Logs

```bash
# Find specific pattern in logs
grep -r "ERROR" ~/slurm-logs/*<JOBID>*.out

# Check for TP/FP results
grep -r "TP:" /fred/oz411/dunguyen/slurm-logs/*_6555*.out | head -20

# Find thresholds
grep "threshold" ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out

# Check for failures
sacct -u $USER -S 2025-10-30 | grep -i fail
```

### Resource Usage

```bash
# Check job details
scontrol show job <JOBID>

# GPU stats (if logged)
tail ~/slurm-logs/gpu_stats_<JOBID>.log

# Disk usage
du -sh /fred/oz411/dunguyen/* | sort -h | tail -n 20
```

---

## Post-Run Operations

### W&B Sync and Artifact Extraction

```bash
# Automated sync and extraction
./scripts/sync_wandb_run.sh <JOBID>

# Manual extraction
cd ~/slurm-logs
tar -xzf orthus_cadets_e3_ctn_<JOBID>.tar.gz

# Manual W&B sync
wandb sync pids_run_<JOBID>/wandb/offline-run-*
```

### Results Review

```bash
# View artifacts
ls ~/slurm-logs/pids_run_<JOBID>/artifacts/

# View logs
less ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out
less ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.err

# View GPU stats
less ~/slurm-logs/gpu_stats_<JOBID>.log

# W&B dashboard
# https://wandb.ai/<entity>/<project>
```

### Extract Metrics

```bash
# Find confusion matrices
grep -A 10 "Confusion Matrix" ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out

# Find AUC scores
grep "AUC" ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out

# Find training time
grep "GNN training:" ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out

# Find evaluation CSVs
find /fred/oz411/dunguyen/tmp/pidsmaker_<JOBID>/artifacts/detection/evaluation -type f -name "*.csv"
```

---

## Troubleshooting

### Diagnostics

```bash
# Verify environment
echo $APPTAINER_CACHEDIR
echo $APPTAINER_TMPDIR

# Check container availability
ls -lh $FRED_BASE/containers/pidsmaker_cuda117.sif

# Test container imports
apptainer exec $FRED_BASE/containers/pidsmaker_cuda117.sif python -c "import pidsmaker; print('OK')"

# Check database
psql -h 127.0.0.1 -U postgres -d cadets_e3 -c "\dt"

# Check disk space
df -h /fred/oz411/dunguyen
quota -s  # Check inode quota
```

### Common Issues

#### PostgreSQL not starting
```bash
# Check if already running
pg_ctl -D $FRED_BASE/pg/data status

# Check logs
tail -100 $FRED_BASE/pg/logs/postgres.log

# Force stop and restart
pg_ctl -D $FRED_BASE/pg/data stop -m immediate
pg_ctl -D $FRED_BASE/pg/data start -l $FRED_BASE/pg/logs/postgres.log
```

#### Job fails immediately
```bash
# Check Slurm error log
cat ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.err

# Check exit code
sacct -j <JOBID> --format=JobID,State,ExitCode

# Verify script syntax
bash -n scripts/run_orthus_cadets_e3_apptainer.slurm
```

#### Out of disk space
```bash
# Check usage
du -sh $FRED_BASE/*

# Clean up old artifacts
rm -rf /fred/oz411/dunguyen/tmp/pidsmaker_<old_jobid>

# Clean up logs
rm ~/slurm-logs/*_<old_jobid>.*
```

#### Container issues
```bash
# Rebuild container
module load apptainer
apptainer build --force $FRED_BASE/containers/pidsmaker_cuda117.sif containers/pidsmaker_cuda117.def

# Check container modules
apptainer exec $FRED_BASE/containers/pidsmaker_cuda117.sif pip list | grep torch
```

---

## Job History Reference

### Notable Job IDs

#### Successful Runs:
- **6357922**: First successful GPU run (October 20, 2025) - 0 TP but validated infrastructure
- **6358952**: Optimized run (October 21, 2025) - 32.5 min runtime, 3.2x faster, but still 0 TP
- **6555874**: Orthrus CADETS_E3 (October 31, 2025) - First run with all bug fixes
- **6555886**: Orthrus THEIA_E3 (October 31, 2025) - Completed
- **6555889**: Orthrus CLEARSCOPE_E3 (October 31, 2025) - Completed
- **6555890**: Kairos CLEARSCOPE_E3 (October 31, 2025) - Completed

#### Failed Runs (with lessons):
- **6356979**: Missing psycopg2 in container
- **6357475**: OUT_OF_MEMORY (24GB) during TGN construction
- **6357821**: OUT_OF_MEMORY (48GB) during TGN construction
- **6358565**: Config validation error (invalid threshold_method)
- **6378640-6378645**: CLI argument errors (used flags instead of positional args)
- **6379295-6379303**: Dataset case mismatch (lowercase vs uppercase)
- **6555540**: Magic CSV column mismatch
- **6555846-6555847**: Magic resubmitted with CSV fix

---

## Quick Reference

### Essential Commands
```bash
# Submit job
sbatch scripts/<script>.slurm

# Check status
squeue -u $USER

# Cancel job
scancel <JOBID>

# Tail log
tail -f ~/slurm-logs/*_<JOBID>.out

# Check completion
sacct -j <JOBID>

# Sync results
./scripts/sync_wandb_run.sh <JOBID>
```

### Resource Requests
```bash
# Typical GPU job
#SBATCH --partition=milan-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=2:00:00

# Typical CPU job
#SBATCH --partition=milan
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=1:00:00
```

### Configuration Shortcuts
```bash
# View config
cat config/orthrus_tuned.yml

# Check threshold method
grep "threshold_method" config/orthrus_tuned.yml

# Verify dataset splits
python scripts/verify_dataset_splits.py
```

---

**Reference Updated**: October 31, 2025
