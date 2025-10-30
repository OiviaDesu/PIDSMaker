#!/bin/bash
#SBATCH --job-name=orthrus_default_clearscope_e3
#SBATCH --partition=milan-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48GB
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=/fred/oz411/dunguyen/slurm-logs/orthrus_default_clearscope_e3_ctn_%j.out
#SBATCH --error=/fred/oz411/dunguyen/slurm-logs/orthrus_default_clearscope_e3_ctn_%j.err

set -x
set -e

# Ensure log directory exists on shared storage
mkdir -p /fred/oz411/dunguyen/slurm-logs

# Environment
export WANDB_MODE=offline
export PYTHONUNBUFFERED=1

# Job-specific paths
JOB_ID=$SLURM_JOB_ID
# Use unique port per job to avoid conflicts when multiple jobs run on same node
PG_PORT=$((55432 + (JOB_ID % 1000)))
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
PGDATA="${TMPDIR}/pgdata"
ARTIFACT_DIR="${TMPDIR}/artifacts"
PG_LOG="${TMPDIR}/postgres.log"
RUN_LOG="${TMPDIR}/run.log"

# Create directories
mkdir -p "${TMPDIR}" "${PGDATA}" "${ARTIFACT_DIR}"

# Function to stop PostgreSQL on exit
    cleanup() {
    echo "Cleaning up..."
    if [ -f "${PGDATA}/postmaster.pid" ]; then
        /fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" stop -m fast || true
    fi
    # Per user request: Do NOT persist large tarballs to shared storage and do NOT remove TMPDIR here.
    # This avoids filling /fred or any shared filesystem when node-local scratch is limited.
    echo "NOTE: Skipping tarball creation and TMPDIR deletion (logs remain in ${TMPDIR})."
}
trap cleanup EXIT

# Ensure Apptainer is available on compute node
if ! command -v apptainer >/dev/null 2>&1; then
    module load apptainer || true
fi
command -v apptainer || { echo "ERROR: apptainer not found in PATH" >&2; exit 127; }

# Initialize PostgreSQL with UTF-8
echo "Initializing PostgreSQL..."
/fred/oz411/dunguyen/.conda/envs/pg17/bin/initdb -D "${PGDATA}" \
    --encoding=UTF8 \
    --locale=en_US.UTF-8 \
    --auth=trust \
    --username=postgres

# Start PostgreSQL
echo "Starting PostgreSQL on port ${PG_PORT}..."
/fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" -l "${PG_LOG}" -o "-p ${PG_PORT}" start

# Wait for PostgreSQL to be ready
sleep 10
for i in {1..30}; do
    if /fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" status > /dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Create database and restore from dump
echo "Creating database and restoring from dump..."
/fred/oz411/dunguyen/.conda/envs/pg17/bin/createdb -h 127.0.0.1 -p ${PG_PORT} -U postgres clearscope_e3 || echo "Database clearscope_e3 may already exist"

echo "Restoring database from /fred/oz411/dunguyen/data/clearscope_e3.dump..."
# Check available free space in TMPDIR before restoring large DB dump.
# If free space is below MIN_TMP_BYTES, fail early with a clear message.
MIN_TMP_BYTES=$((10 * 1024 * 1024 * 1024))  # 10 GiB
avail_bytes=$(df -PB1 "${TMPDIR}" | awk 'END{print $4+0}') || avail_bytes=0
echo "TMPDIR=${TMPDIR} available bytes=${avail_bytes} threshold=${MIN_TMP_BYTES}"
if [ "${avail_bytes}" -lt "${MIN_TMP_BYTES}" ]; then
    echo "ERROR: Not enough free space in ${TMPDIR} to restore the database (need >= ${MIN_TMP_BYTES} bytes)." >&2
    echo "Suggest: set SLURM_TMPDIR to a node-local location or increase scratch allocation." >&2
    exit 1
fi

/fred/oz411/dunguyen/.conda/envs/pg17/bin/pg_restore -h 127.0.0.1 -p ${PG_PORT} -U postgres -d clearscope_e3 \
    /fred/oz411/dunguyen/data/clearscope_e3.dump || echo "Restore may have completed with warnings"

# Run PIDSMaker inside Apptainer
echo "Running PIDSMaker..."
set -o pipefail
apptainer exec --nv \
    -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
    -B "${TMPDIR}:${TMPDIR}" \
    /fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif \
    bash -lc "set -o pipefail; cd /opt/PIDSMaker && \
    python -m pidsmaker.main orthrus CLEARSCOPE_E3 \
        --artifact_dir_in_container ${ARTIFACT_DIR} \
        --restart_from_scratch \
        --force_restart=build_graphs \
        --db_port ${PG_PORT} \
        --wandb --project pidsmaker-clearscope \
        2>&1 | tee ${RUN_LOG}"
PY_EXIT=$?
if [ $PY_EXIT -ne 0 ]; then
    echo "PIDSMaker exited with code ${PY_EXIT}" >&2
    exit $PY_EXIT
fi

echo "Job completed successfully."
