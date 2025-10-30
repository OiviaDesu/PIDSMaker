#!/bin/bash
#SBATCH --job-name=orthus_cadets_e3_ctn_sk
#SBATCH --output=/home/dunguyen/slurm-logs/%x_%j.out
#SBATCH --error=/home/dunguyen/slurm-logs/%x_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --partition=skylake-gpu
#SBATCH --gres=gpu:1
#SBATCH --tmp=50G

set -euo pipefail
set -x

echo "[$(date)] Starting Orthrus CADETS_E3 in container on host: $(hostname)"

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

# Use node-local PostgreSQL to avoid /fred inode usage
PG_BIN="/home/dunguyen/.conda/envs/pg17/bin"
SRC_PGDATA="/fred/oz411/dunguyen/pg/data"
# Pick a writable node-local base dir
NODE_BASE="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
NODE_WORK="${NODE_BASE}/pids_run_${SLURM_JOB_ID}"
NODE_PGDATA="${NODE_WORK}/pgdata"
NODE_PGLOG="${NODE_WORK}/postgres.log"
mkdir -p "${NODE_PGDATA}" "${NODE_WORK}"

echo "[$(date)] Syncing PostgreSQL data to node-local storage: ${NODE_PGDATA}"
rsync -a --delete "${SRC_PGDATA}/" "${NODE_PGDATA}/"

echo "[$(date)] Starting node-local PostgreSQL on port 55432..."
"${PG_BIN}/pg_ctl" -D "${NODE_PGDATA}" -l "${NODE_PGLOG}" -o "-p 55432" start || true

# Wait until node-local Postgres is ready to accept connections (max ~180s)
for i in $(seq 1 180); do
  "${PG_BIN}/pg_isready" -h 127.0.0.1 -p 55432 -U postgres && break || true
  [ $i -eq 1 ] || echo "[$(date)] Waiting for node-local PostgreSQL... ($i)"
  sleep 1
done

module -q load apptainer

# Use prebuilt container image on /fred to avoid network during job
IMG="/fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif"
echo "[$(date)] Using image ${IMG}"
export APPTAINER_CACHEDIR="/fred/oz411/dunguyen/.apptainer/cache"
export APPTAINER_TMPDIR="/fred/oz411/dunguyen/.apptainer/tmp"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"
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

# Lightweight heartbeat while job runs (every 60s)
(
  while true; do echo "[$(date)] Heartbeat: job ${SLURM_JOB_ID} running on $(hostname)"; sleep 60; done
) &
apptainer exec --nv \
  -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
  -B "${NODE_WORK}":"${NODE_WORK}" \
  "${IMG}" \
  bash -lc "set -o pipefail; python -m pidsmaker.main orthrus CADETS_E3 \
    --artifact_dir_in_container "${ART_DIR}" \
    --restart_from_scratch \
    --force_restart=build_graphs \
    2>&1 | tee "${NODE_WORK}/orthus_cadets_e3_ctn_sk_run_${SLURM_JOB_ID}.log""

echo "[$(date)] Packaging artifacts to home..."
tar -C "${NODE_WORK}" -czf "/home/dunguyen/slurm-logs/orthus_cadets_e3_ctn_sk_${SLURM_JOB_ID}.tar.gz" artifacts postgres.log "orthus_cadets_e3_ctn_sk_run_${SLURM_JOB_ID}.log" || true

echo "[$(date)] Container job finished."
