#!/bin/bash
#SBATCH --job-name=kairos_tuned_cadets_e3
#SBATCH --partition=milan-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48GB
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=/fred/oz411/dunguyen/slurm-logs/kairos_tuned_cadets_e3_ctn_%j.out
#SBATCH --error=/fred/oz411/dunguyen/slurm-logs/kairos_tuned_cadets_e3_ctn_%j.err

set -x
set -e

# Ensure log directory exists on shared storage
mkdir -p /fred/oz411/dunguyen/slurm-logs

# Environment
export WANDB_MODE=offline
export PYTHONUNBUFFERED=1

# Job-specific paths
JOB_ID=$SLURM_JOB_ID
# Prefer node-local scratch if available to avoid shared /fred quota
# Priority: $SLURM_TMPDIR (if set), then /scratch/$USER/$JOB_ID, then a non-/tmp $TMPDIR, else fallback to /fred
TMPDIR_BASE=""
if [ -n "${SLURM_TMPDIR:-}" ] && [ -d "${SLURM_TMPDIR}" ] && [ -w "${SLURM_TMPDIR}" ]; then
    TMPDIR_BASE="${SLURM_TMPDIR}"
elif [ -d "/scratch" ] && [ -w "/scratch" ]; then
    TMPDIR_BASE="/scratch/${USER}/${JOB_ID}"
elif [ -n "${TMPDIR:-}" ] && [ "${TMPDIR}" != "/tmp" ]; then
    TMPDIR_BASE="${TMPDIR}"
else
    TMPDIR_BASE="/fred/oz411/dunguyen/tmp"
fi
TMPDIR="${TMPDIR_BASE}/pidsmaker_${JOB_ID}"
ARTIFACT_DIR="${TMPDIR}/artifacts"
RUN_LOG="${TMPDIR}/run.log"

# Create directories
mkdir -p "${TMPDIR}" "${ARTIFACT_DIR}"

# Ensure Apptainer is available on compute node
if ! command -v apptainer >/dev/null 2>&1; then
    module load apptainer || true
fi
command -v apptainer || { echo "ERROR: apptainer not found in PATH" >&2; exit 127; }

# Database connection info (shared PostgreSQL on oz411)
echo "Connecting to shared PostgreSQL at 127.0.0.1:5432..."
echo "Database: cadets_e3"

# Run PIDSMaker inside Apptainer
echo "Running PIDSMaker..."
set -o pipefail
apptainer exec --nv \
    -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
    -B "${TMPDIR}:${TMPDIR}" \
    /fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif \
    bash -lc "set -o pipefail; cd /opt/PIDSMaker && \
    python -m pidsmaker.main kairos_tuned CADETS_E3 \
        --artifact_dir ${ARTIFACT_DIR} \
        --restart_from_scratch \
        --force_restart=build_graphs \
        --database_host 127.0.0.1 \
        --database_port 5432 \
        --wandb --project pidsmaker-cadets \
        2>&1 | tee ${RUN_LOG}"
PY_EXIT=$?
if [ $PY_EXIT -ne 0 ]; then
    echo "PIDSMaker exited with code ${PY_EXIT}" >&2
    exit $PY_EXIT
fi

echo "Job completed successfully."
