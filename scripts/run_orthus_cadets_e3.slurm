#!/bin/bash
#SBATCH --job-name=orthus_cadets_e3
#SBATCH --output=/home/dunguyen/slurm-logs/%x_%j.out
#SBATCH --error=/home/dunguyen/slurm-logs/%x_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --partition=cpu
#SBATCH --tmp=50G

set -euo pipefail

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

echo "[$(date)] Starting Orthrus CADETS_E3 job on host: $(hostname)"

# Slurm performance context
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}

# Use node-local PostgreSQL to avoid /fred inode usage
PG_BIN="/home/dunguyen/.conda/envs/pg17/bin"
SRC_PGDATA="/fred/oz411/dunguyen/pg/data"
# Pick a writable node-local base dir
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
"${PG_BIN}/pg_ctl" -D "${NODE_PGDATA}" -l "${NODE_PGLOG}" -o "-p 55432" start || true

# Wait until node-local Postgres is ready to accept connections (max ~180s)
for i in $(seq 1 180); do
  "${PG_BIN}/pg_isready" -h 127.0.0.1 -p 55432 -U postgres && break || true
  [ $i -eq 1 ] || echo "[$(date)] Waiting for node-local PostgreSQL... ($i)"
  sleep 1
done

# Load mamba and activate Python environment (work around lmod PS1 with set -u)
set +u
export PS1="${PS1:-}"  # prevent lmod init from failing on unset PS1
module -q load mamba
source /apps/system/software/mamba/latest/etc/profile.d/conda.sh
conda activate pidsmaker
set -u

cd /home/dunguyen/git/PIDSMaker

# Where to put artifacts for this run (node-local)
ART_DIR="${NODE_WORK}/artifacts"
mkdir -p "${ART_DIR}"

# Save environment and versions for reproducibility
ENV_SNAPSHOT="${NODE_WORK}/env_${SLURM_JOB_ID}.txt"
echo "[$(date)] Environment info:" | tee -a "${ENV_SNAPSHOT}"
python -V | tee -a "${ENV_SNAPSHOT}"
pip freeze | tee -a "${ENV_SNAPSHOT}"

# Run Orthrus on CADETS_E3
echo "[$(date)] Launching training pipeline..."
python -m pidsmaker.main orthrus CADETS_E3 \
  --database.host=127.0.0.1 \
  --database.port=55432 \
  --database.user=postgres \
  --artifact_dir_in_container "${ART_DIR}" \
  --restart_from_scratch \
  --force_restart=build_graphs \
  --wandb --project "${WANDB_PROJECT:-pidsmaker-orthus}" \
  --cpu \
  2>&1 | tee "${NODE_WORK}/pipeline_${SLURM_JOB_ID}.log"

echo "[$(date)] Packaging artifacts to home..."
tar -C "${NODE_WORK}" -czf "/home/dunguyen/slurm-logs/orthus_cadets_e3_${SLURM_JOB_ID}.tar.gz" artifacts postgres.log "pipeline_${SLURM_JOB_ID}.log" wandb || true

echo "[$(date)] Job finished."
