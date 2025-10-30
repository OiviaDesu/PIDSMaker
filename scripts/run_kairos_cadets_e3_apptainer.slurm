#!/bin/bash
#SBATCH --job-name=kairos_cadets_e3_ctn
#SBATCH --output=/home/dunguyen/slurm-logs/%x_%j.out
#SBATCH --error=/home/dunguyen/slurm-logs/%x_%j.err
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --partition=milan-gpu
#SBATCH --gres=gpu:1
#SBATCH --tmp=50G

# Kairos run on CADETS_E3 with default configuration

set -euo pipefail
set -x

echo "[$(date)] Starting Kairos CADETS_E3 in container on host: $(hostname)"

# Ensure home slurm logs directory exists (stdout/err target)
mkdir -p /home/dunguyen/slurm-logs

# Load secrets/config if present
ENV_FILE="/home/dunguyen/git/PIDSMaker/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

# Setup paths - using node-local PostgreSQL from conda environment
PG_BIN="/fred/oz411/dunguyen/.conda/envs/pg17/bin"
SRC_PGDATA="/fred/oz411/dunguyen/pg/data"
NODE_BASE="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
NODE_WORK="${NODE_BASE}/pids_run_${SLURM_JOB_ID}"
NODE_PGDATA="${NODE_WORK}/pgdata"
NODE_PGLOG="${NODE_WORK}/postgres.log"
mkdir -p "${NODE_PGDATA}" "${NODE_WORK}"

# Optional: Weights & Biases offline logging to node-local dir
export WANDB_MODE="${WANDB_MODE:-offline}"
export WANDB_DIR="${NODE_WORK}/wandb"
mkdir -p "${WANDB_DIR}"

echo "[$(date)] Syncing PostgreSQL data to node-local storage: ${NODE_PGDATA}"
rsync -a --delete "${SRC_PGDATA}/" "${NODE_PGDATA}/"

echo "[$(date)] Starting node-local PostgreSQL on port 55432..."
"${PG_BIN}/pg_ctl" -D "${NODE_PGDATA}" -l "${NODE_PGLOG}" -o "-p 55432" start

# Wait until Postgres is ready to accept connections (max ~180s)
echo "[$(date)] Waiting for PostgreSQL to become ready..."
for i in $(seq 1 180); do
  if "${PG_BIN}/pg_isready" -h 127.0.0.1 -p 55432 -U postgres >/dev/null 2>&1; then
    echo "[$(date)] PostgreSQL is ready!"
    break
  fi
  [ $i -eq 1 ] || echo "[$(date)] Waiting for PostgreSQL... ($i)"
  sleep 1
  if [ $i -eq 180 ]; then
    echo "[$(date)] ERROR: PostgreSQL failed to start after 180 seconds"
    tail -100 "${NODE_PGLOG}"
    exit 1
  fi
done

module -q load apptainer

# Use prebuilt container image on /fred to avoid network during job
IMG="/fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif"
echo "[$(date)] Using image ${IMG}"
export APPTAINER_CACHEDIR="/fred/oz411/dunguyen/.apptainer/cache"
export APPTAINER_TMPDIR="/fred/oz411/dunguyen/.apptainer/tmp"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"
echo "[$(date)] Using image ${IMG}"
which apptainer || true
apptainer --version || true
ls -l "${IMG}" || true
echo "GPU devices: $CUDA_VISIBLE_DEVICES"

# Quick container sanity check before running the pipeline
echo "[$(date)] Container torch check..."
apptainer exec --nv "${IMG}" python - <<'PY'
import torch, sys
print('torch', torch.__version__, 'cuda', torch.version.cuda, 'avail', torch.cuda.is_available())
PY

ART_DIR="${NODE_WORK}/artifacts"
LOG_DIR="${NODE_WORK}"
mkdir -p "${ART_DIR}" "${LOG_DIR}"

echo "[$(date)] Launching training pipeline inside container..."
# Ensure line-buffered output for immediate log visibility
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}

# GPU telemetry (memory/utilization every 15s)
(
  echo "[$(date)] Starting nvidia-smi sampling..."; 
  while true; do 
    nvidia-smi --query-gpu=timestamp,index,name,memory.total,memory.used,utilization.gpu,utilization.memory --format=csv,noheader; 
    sleep 15; 
  done >> "${NODE_WORK}/gpu_stats.log" 2>&1; 
) &

# Lightweight heartbeat while job runs (every 60s)
(
  while true; do echo "[$(date)] Heartbeat: job ${SLURM_JOB_ID} running on $(hostname)"; sleep 60; done
) &

apptainer exec --nv \
  -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
  -B "${NODE_WORK}":"${NODE_WORK}" \
  "${IMG}" \
  bash -lc "set -o pipefail; python -m pidsmaker.main kairos CADETS_E3 \
    --artifact_dir_in_container \"${ART_DIR}\" \
    --restart_from_scratch \
    --force_restart=build_graphs \
    --wandb --project \"${WANDB_PROJECT:-pidsmaker-kairos}\" \
    2>&1 | tee \"${NODE_WORK}/kairos_cadets_e3_ctn_run_${SLURM_JOB_ID}.log\""

echo "[$(date)] Stopping PostgreSQL..."
"${PG_BIN}/pg_ctl" -D "${NODE_PGDATA}" stop -m fast || true

echo "[$(date)] Packaging artifacts to home..."
tar -C "${NODE_WORK}" -czf "/home/dunguyen/slurm-logs/kairos_cadets_e3_ctn_${SLURM_JOB_ID}.tar.gz" artifacts postgres.log wandb "kairos_cadets_e3_ctn_run_${SLURM_JOB_ID}.log" gpu_stats.log || true

echo "[$(date)] Container job finished."
