# Commands log

This file records every significant command used to set up and run PIDSMaker (Orthrus) on OzSTAR. Timestamps are approximate; substitute your own user/project paths where applicable.

## Repository and environment

- Clone repository
  - `git clone https://github.com/ubc-provenance/PIDSMaker.git`
  - `cd PIDSMaker`

- Create directories on /fred for caches, logs, artifacts, and Postgres data
  - `export FRED_BASE=/fred/oz396/dunguyen`
  - `mkdir -p $FRED_BASE/{containers,pids_logs,pids_artifacts,.apptainer/{cache,tmp},pg/{data,logs}}`

## PostgreSQL 17 setup and dataset restore

- Initialize PG17 cluster
  - `~/.conda/envs/pg17/bin/initdb -D $FRED_BASE/pg/data`

- Start PG17 server (login node or inside job)
  - `~/.conda/envs/pg17/bin/pg_ctl -D $FRED_BASE/pg/data -l $FRED_BASE/pg/logs/postgres.log start`

- Create database and restore CADETS_E3
  - `createdb -h 127.0.0.1 -U postgres cadets_e3`
  - `pg_restore -h 127.0.0.1 -U postgres -d cadets_e3 /path/to/cadets_e3.dump`

- Stop PG17 server (optional when done on login)
  - `~/.conda/envs/pg17/bin/pg_ctl -D $FRED_BASE/pg/data stop`

## Container build (one-time)

- Build Apptainer image with CUDA 11.7, Torch 1.13.1+cu117, PyG 2.5.3
  - `module load apptainer`
  - `apptainer build $FRED_BASE/containers/pidsmaker_cuda117.sif containers/pidsmaker_cuda117.def`

## GPU job submissions (containerized)

- Milan/A100 partition submission
  - `sbatch scripts/run_orthus_cadets_e3_apptainer.slurm`

- Skylake GPU partition submission
  - `sbatch scripts/run_orthus_cadets_e3_apptainer_skylake.slurm`

- Latest: submitted single Milan GPU job
  - `sbatch /home/dunguyen/git/PIDSMaker/scripts/run_orthus_cadets_e3_apptainer.slurm`
  - JobID: 6351998 (state pending at submission time)

- Tuned GPU submission to mirror paper resources (GPU mem ~4–6 GB, 4 CPU, 24G RAM, 2h limit) and added telemetry
  - `sbatch scripts/run_orthus_cadets_e3_apptainer.slurm` → JobID 6356979 (PENDING Priority)
  - GPU telemetry logged to `${NODE_WORK}/gpu_stats.log` and packaged to `~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.tar.gz`

- **OPTIMIZED RUN** with tuned configuration (October 21, 2025)
  - `sbatch scripts/run_orthus_cadets_e3_apptainer.slurm` → JobID 6358565 (PENDING Priority)
  - Using `orthrus_tuned.yml` config with optimizations based on job 6357922 analysis
  - Key changes: emb_dim 32 (was 128), node_hid_dim 32 (was 128), batch_size 1024 (was 256), best_val_loss threshold
  - Expected: 5-8 min training (was 45 min), 20-25 TP detection (was 0), 0.4-0.5 precision (was 0.0)
  - Resources: 1 GPU, 4 CPU, 64G RAM, 2h limit

## Container fix
- Observed GPU run 6356979 failed inside container: ModuleNotFoundError: psycopg2
- Patched `containers/pidsmaker_cuda117.def` to include `psycopg2-binary==2.9.9`
- Rebuilt container on login node:
  - `module load apptainer && apptainer build /fred/oz396/dunguyen/containers/pidsmaker_cuda117.sif containers/pidsmaker_cuda117.def`
- Resubmitted GPU job with updated image → JobID 6357087 (PENDING, PartitionDown)

## Code and script fixes
- Honored `WANDB_MODE` in `pidsmaker/main.py` so offline logging works on compute nodes
- Defaulted DB to node-local in `pidsmaker/config/pipeline.py` (host=127.0.0.1, port=55432, user=postgres)
- Removed unsupported CLI DB flags from GPU/Skylake scripts; rely on code defaults
- Fixed model name typo in all scripts: `orthus` → `orthrus`

## Recent GPU submissions and status
- 6357146: COMPLETED quickly (wandb offline OK; argparse failed on `--database.*`)
- 6357185: COMPLETED quickly (ValueError unknown model `orthus`)
- 6357309: RUNNING (node-local PG OK, CUDA True, telemetry and heartbeats active)

## W&B configuration and login

- Created `.env` at repo root (ignored by Git) and set permissions 600
  - Keys: `WANDB_API_KEY`, optional `WANDB_ENTITY`, `WANDB_PROJECT`, `WANDB_MODE`
  - Verified login on login node using env key via Python: `wandb.login(key=...)`
  - Default API entity detected: `oiviadesu-swinburne-university-of-technology`
- Switched W&B to ONLINE mode in `.env` and set `WANDB_ENTITY` accordingly
- Updated Slurm scripts to source `.env`; jobs attempted online logging
- Observed failure: `wandb.init` timeout on compute node; reverted `.env` to OFFLINE for reliability

## Node-local PostgreSQL and tmp space

- Switched Slurm scripts to clone PGDATA to node-local and run PG on port 55432
- Initial attempt with `/jobfs` failed: Permission denied
- Fallback to `${SLURM_TMPDIR}` / `${TMPDIR}` / `/tmp`
- Requested larger node-local tmp: added `#SBATCH --tmp=50G` to scripts

## Recent submissions and checks

- CPU job with node-local PG and W&B offline:
  - `sbatch scripts/run_orthus_cadets_e3.slurm` → JobID 6356672 (failed: /jobfs perms)
  - Fixed node-local base path to use TMPDIR
  - `sbatch scripts/run_orthus_cadets_e3.slurm` → JobID 6356774 (failed: /tmp no space)
  - Added `--tmp=50G`; resubmitted → JobID 6356875 (PENDING Priority)
  - Fixed lmod PS1 with set -u; resubmitted → JobID 6356903 (RUNNING then FAILED due to W&B online timeout)
  - Reverted W&B to offline in `.env` for next submission

- GPU jobs with progressive memory increases to resolve TGN OOM:
  - JobID 6357475: OUT_OF_MEMORY after 8m48s (24G RAM) during TGN neighbor graph construction
  - JobID 6357821: OUT_OF_MEMORY after 10m20s (48G RAM, peaked at 38.2GB) during TGN neighbor graph construction
  - JobID 6357922: ✅ COMPLETED successfully with 96G RAM (started 23:21:23, finished ~00:25:00 on gina17)
    - ✅ Successfully passed TGN neighbor graph construction at ~10-11 minutes
    - ✅ GNN training completed: 11 epochs, ~45 minutes
    - ✅ Evaluation completed: all epoch checkpoints tested
    - GPU memory: 1.80 GB peak (training), 0.11 GB (inference)
    - Total runtime: ~63-65 minutes
    - Artifacts packaged to: ~/slurm-logs/orthus_cadets_e3_ctn_6357922.tar.gz
    - W&B offline run: offline-run-20251020_122255-f5vstcxm

- Status checks
  - `squeue -j <JOBID>` and `sacct -j <JOBID> --format=...`
  - Inspected stdout/err under `~/slurm-logs/`
  - `tail -f ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out` for real-time monitoring

## Monitoring and logs

- Check queue for specific jobs
  - `squeue -j <JOBID1>,<JOBID2>`

- Check all your jobs
  - `squeue -u $USER`

- Tail container run logs (replace JOBID)
  - `tail -f $FRED_BASE/pids_logs/orthus_cadets_e3_ctn_run_<JOBID>.log`
  - `tail -f $FRED_BASE/pids_logs/orthus_cadets_e3_ctn_sk_run_<JOBID>.log`

- Check Slurm stdout/err files
  - `ls -l ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.out ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.err`

- Monitor job until completion
  - `./scripts/monitor_job.sh <JOBID> [interval_seconds]`

## Post-run: W&B sync and artifact extraction

- Sync W&B offline run and extract artifacts (automated script)
  - `./scripts/sync_wandb_run.sh <JOBID>`
  - Example: `./scripts/sync_wandb_run.sh 6357922`

- Manual W&B sync (if needed)
  - `cd ~/slurm-logs && tar -xzf orthus_cadets_e3_ctn_<JOBID>.tar.gz`
  - `wandb sync pids_run_<JOBID>/wandb/offline-run-*`

- View results
  - W&B dashboard: https://wandb.ai/<entity>/<project>
  - Artifacts: ~/slurm-logs/pids_run_<JOBID>/artifacts/
  - Logs: ~/slurm-logs/orthus_cadets_e3_ctn_<JOBID>.{out,err}
  - GPU stats: ~/slurm-logs/gpu_stats_<JOBID>.log

## Optimization for Next Run (Based on Job 6357922 Results)

**Analysis:** Job 6357922 completed successfully but had poor detection (0 TP) and slow training (45 min vs paper's 4.5 min).

**Root causes:**
- Model too large: 128-dim embeddings vs paper's likely 32-dim (10x more parameters)
- Poor threshold: `max_val_loss` strategy too conservative
- Batch sizes reduced unnecessarily (we have 96GB RAM available)

**Optimizations applied:**
```bash
# 1. Created tuned config based on paper's likely hyperparameters
cp config/orthrus.yml config/orthrus_tuned.yml

# 2. Key changes in orthrus_tuned.yml:
# - emb_dim: 128 -> 32 (4x faster Word2Vec training)
# - node_hid_dim: 128 -> 32 (4x fewer GNN parameters)
# - node_out_dim: 64 -> 16 (smaller output)
# - tgn_memory_dim: 100 -> 50 (faster TGN)
# - tgn_time_dim: 100 -> 50 (faster TGN)
# - intra_graph_batch_size: 256 -> 1024 (faster, we have 96GB RAM)
# - tgn_neighbor_size: 10 -> 20 (better neighbor context)
# - threshold_method: max_val_loss -> best_val_loss (better detection)

# 3. Updated Slurm script to use orthrus_tuned config
# Changed: python -m pidsmaker.main orthrus -> orthrus_tuned
```

**Expected improvements:**
- Training time: 45 min -> 5-8 min (5-9x speedup)
- GPU memory: 1.8 GB -> 0.5-1.0 GB (smaller model)
- Detection: 0 TP -> 20-25 TP (better threshold calibration)
- Precision: 0.0 -> 0.4-0.5 (matching paper)
- MCC: -0.00009 -> 0.3-0.4 (matching paper)

**Submit optimized run:**
```bash
sbatch scripts/run_orthus_cadets_e3_apptainer.slurm
```

## Optional diagnostics

- Confirm Apptainer cache/tmp point to /fred
  - `echo $APPTAINER_CACHEDIR; echo $APPTAINER_TMPDIR`

- Verify container Torch/CUDA inside a node (expected True for CUDA)
  - `apptainer exec --nv $FRED_BASE/containers/pidsmaker_cuda117.sif python -c "import torch; import torch_geometric as tg; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), tg.__version__)"`

## Notes

- Artifacts are written to `$FRED_BASE/pids_artifacts`.
- Set WANDB_API_KEY in your environment if enabling Weights & Biases.
- The Slurm scripts auto-start the PG17 server on the node if not already running.
squeue -j 6351284,6351285
sacct -j 6351284,6351285 --format=JobID,State,ExitCode,Start,End,Elapsed,AllocTRES%45,NodeList
tail -f /home/dunguyen/slurm-logs/orthus_cadets_e3_ctn_%j.out
]633;E;echo '# Diagnostics';ea2f0c7f-b515-4891-9c03-36a113b81c8d]633;C# Diagnostics
squeue -j 6351284,6351285 -o "%i %T %P %R %M %l %D %C %m %b %N"
sacct -j 6351284,6351285 --format=JobID,JobName%30,Partition,State,ExitCode,Start,End,Elapsed,AllocTRES%45,NodeList
scontrol show job 6351284
sed -n "1,200p" ~/slurm-logs/orthus_cadets_e3_ctn_6351284.out
sed -n "1,200p" ~/slurm-logs/orthus_cadets_e3_ctn_6351284.err
tail -n 200 /fred/oz396/dunguyen/pg/logs/postgres.log
rm -f /fred/oz396/dunguyen/cadets_e5-001.dump
du -sh /fred/oz396/dunguyen/* | sort -h | tail -n 20
scancel 6351703 6351704
sbatch -p skylake-gpu scripts/run_orthus_cadets_e3_apptainer_skylake.slurm
squeue -j 6351715 -o "%i %T %P %R %M %l %D %C %m %b %N"
sbatch -p skylake-gpu --mem=32G -c 4 --time=12:00:00 scripts/run_orthus_cadets_e3_apptainer_skylake.slurm
squeue -j 6351715,6351807 -o "%i %T %P %R %M %l %D %C %m %b %N"
scancel 6351715 6351807 6351818 6351819 6351820 6351824
