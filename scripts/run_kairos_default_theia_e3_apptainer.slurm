#!/bin/bash
#SBATCH --job-name=kairos_default_theia_e3
#SBATCH --partition=milan-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64GB
#SBATCH --gres=gpu:1
#SBATCH --time=02:30:00
#SBATCH --output=/fred/oz396/dunguyen/slurm-logs/kairos_default_theia_e3_ctn_%j.out
#SBATCH --error=/fred/oz396/dunguyen/slurm-logs/kairos_default_theia_e3_ctn_%j.err

set -x
set -e

# Environment
export WANDB_MODE=offline
export PYTHONUNBUFFERED=1

# Job-specific paths
JOB_ID=$SLURM_JOB_ID
TMPDIR="/tmp/pidsmaker_${JOB_ID}"
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
        /fred/oz396/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" stop -m fast || true
    fi
    # Archive artifacts to shared storage
    cd "${TMPDIR}"
    tar -czf "/fred/oz396/dunguyen/slurm-logs/kairos_default_theia_e3_ctn_${JOB_ID}.tar.gz" artifacts/ *.log 2>/dev/null || true
    cd /
    rm -rf "${TMPDIR}"
}
trap cleanup EXIT

# Initialize PostgreSQL with UTF-8
echo "Initializing PostgreSQL..."
/fred/oz396/dunguyen/.conda/envs/pg17/bin/initdb -D "${PGDATA}" \
    --encoding=UTF8 \
    --locale=en_US.UTF-8 \
    --auth=trust \
    --username=dunguyen

# Start PostgreSQL
echo "Starting PostgreSQL on port 55432..."
/fred/oz396/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" -l "${PG_LOG}" -o "-p 55432" start

# Wait for PostgreSQL to be ready
sleep 10
for i in {1..30}; do
    if /fred/oz396/dunguyen/.conda/envs/pg17/bin/pg_ctl -D "${PGDATA}" status > /dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Create database schemas
echo "Creating databases..."
for db in theia_e3; do
    /fred/oz396/dunguyen/.conda/envs/pg17/bin/createdb -h 127.0.0.1 -p 55432 -U dunguyen "${db}" || echo "Database ${db} may already exist"
done

# Run PIDSMaker inside Apptainer
echo "Running PIDSMaker..."
apptainer exec --nv \
    -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
    -B "${TMPDIR}:${TMPDIR}" \
    /fred/oz396/dunguyen/containers/pidsmaker_cuda117.sif \
    bash -lc "cd /opt/PIDSMaker && \
    python -m pidsmaker.main kairos THEIA_E3 \
        --artifact_dir_in_container ${ARTIFACT_DIR} \
        --restart_from_scratch \
        --force_restart=build_graphs \
        --wandb --project pidsmaker-theia \
        2>&1 | tee ${RUN_LOG}"

echo "Job completed successfully."
