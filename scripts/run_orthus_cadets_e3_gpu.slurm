#!/bin/bash
#SBATCH --job-name=orthus_cadets_e3_gpu
#SBATCH --output=/fred/oz411/dunguyen/pids_logs/orthus_cadets_e3_gpu_%j.out
#SBATCH --error=/fred/oz411/dunguyen/pids_logs/orthus_cadets_e3_gpu_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --partition=milan-gpu
#SBATCH --gres=gpu:1

set -euo pipefail

echo "[$(date)] Starting Orthrus CADETS_E3 GPU job on host: $(hostname)"

# Slurm performance context
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}

# Ensure Postgres 17 server is running (use conda pg17 binaries without activating conda)
PG_BIN="/home/dunguyen/.conda/envs/pg17/bin"
PGDATA="/fred/oz411/dunguyen/pg/data"
PGLOG="/fred/oz411/dunguyen/pg/logs/postgres.log"
if ! pgrep -f "postgres .* -D ${PGDATA}" >/dev/null 2>&1; then
  echo "[$(date)] Starting PostgreSQL 17 server..."
  "${PG_BIN}/pg_ctl" -D "${PGDATA}" -l "${PGLOG}" start
else
  echo "[$(date)] PostgreSQL already running."
fi

# Load CUDA + PyTorch module stack (avoid conda/mamba to prevent conflicts)
module purge
module load gcc/11.3.0 openmpi/4.1.4
module load cuda/11.7.0 cudnn/8.4.1.50-cuda-11.7.0
module load pytorch/1.12.1-cuda-11.7.0

which python
python -c "import sys, torch; print(sys.version); print('torch:', torch.__version__, 'cuda:', torch.version.cuda, 'avail:', torch.cuda.is_available())"

cd /home/dunguyen/git/PIDSMaker

# Where to put artifacts for this run
ART_DIR="/fred/oz411/dunguyen/pids_artifacts"
mkdir -p "${ART_DIR}"

# Create a per-job virtualenv on node-local storage and install PyG + deps
VENV_BASE="${SLURM_TMPDIR:-/tmp}/${USER}/pids-${SLURM_JOB_ID}"
VENV_DIR="${VENV_BASE}/venv"
mkdir -p "${VENV_BASE}"

echo "[$(date)] Creating venv at ${VENV_DIR} (with system site-packages to reuse module PyTorch)"
python -m venv --system-site-packages "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade --no-input pip wheel setuptools

# Core Python deps (lightweight; avoid reinstalling torch which comes from the module)
python -m pip install --no-input --no-cache-dir numpy pandas tqdm scikit-learn networkx wandb pyyaml

# Install PyTorch Geometric stack matching torch 1.12.x + cu117
# Use prebuilt wheels from the official PyG index to avoid building from source.
PYG_WHL_INDEX="https://data.pyg.org/whl/torch-1.12.0+cu117.html"
python -m pip install --no-input --no-cache-dir \
  pyg-lib torch-scatter torch-sparse torch-cluster torch-spline-conv torch-geometric \
  -f "${PYG_WHL_INDEX}"

echo "[$(date)] Python packages installed:" | tee -a "${ART_DIR}/env_${SLURM_JOB_ID}.txt"
python -V | tee -a "${ART_DIR}/env_${SLURM_JOB_ID}.txt"
python -c "import torch, torch_geometric, sys; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'avail', torch.cuda.is_available()); print('pyg', torch_geometric.__version__)" | tee -a "${ART_DIR}/env_${SLURM_JOB_ID}.txt"
python -m pip freeze | tee -a "${ART_DIR}/env_${SLURM_JOB_ID}.txt"

# Ensure project is importable without installing into the venv
export PYTHONPATH="/home/dunguyen/git/PIDSMaker:${PYTHONPATH:-}"

echo "[$(date)] Launching training pipeline on GPU..."
python -m pidsmaker.main orthrus CADETS_E3 \
  --database.host=localhost \
  --database.port=5432 \
  --database.user=postgres \
  --artifact_dir_in_container "${ART_DIR}" \
  --restart_from_scratch \
  --force_restart=build_graphs \
  2>&1 | tee "/fred/oz411/dunguyen/pids_logs/orthus_cadets_e3_gpu_run_${SLURM_JOB_ID}.log"

echo "[$(date)] GPU job finished."
