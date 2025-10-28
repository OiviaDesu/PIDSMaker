#!/bin/bash
#
# Master submission script for 18 E3 jobs (3 datasets × 3 models × 2 configs)
# Based on reproduction best practices for ORTHRUS, KAIROS, and MAGIC
#
# Usage: bash scripts/submit_all_e3_jobs.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="/home/dunguyen/git/PIDSMaker/scripts"
LOG_DIR="/fred/oz396/dunguyen/slurm-logs"
CONTAINER="/fred/oz396/dunguyen/containers/pidsmaker_cuda117.sif"
PG_BIN="/fred/oz396/dunguyen/.conda/envs/pg17/bin"

# Datasets to run
DATASETS=("CADETS_E3" "THEIA_E3" "CLEARSCOPE_E3")

# Models and their configs
MODELS=("orthrus" "magic" "kairos")

# Track submitted job IDs
declare -a JOB_IDS

# Resource profiles per dataset
declare -A MEM_PROFILE
MEM_PROFILE["CADETS_E3"]="48GB"
MEM_PROFILE["THEIA_E3"]="64GB"
MEM_PROFILE["CLEARSCOPE_E3"]="48GB"

declare -A TIME_PROFILE
TIME_PROFILE["CADETS_E3"]="02:00:00"
TIME_PROFILE["THEIA_E3"]="02:30:00"
TIME_PROFILE["CLEARSCOPE_E3"]="02:00:00"

declare -A CPUS_PROFILE
CPUS_PROFILE["CADETS_E3"]="4"
CPUS_PROFILE["THEIA_E3"]="4"
CPUS_PROFILE["CLEARSCOPE_E3"]="4"

# Function to generate and submit a single job
submit_job() {
    local MODEL=$1
    local CONFIG=$2
    local DATASET=$3
    
    local JOB_NAME="${MODEL}_${CONFIG}_${DATASET,,}"
    local SCRIPT_FILE="${SCRIPT_DIR}/run_${JOB_NAME}_apptainer.slurm"
    local MEM="${MEM_PROFILE[$DATASET]}"
    local TIME="${TIME_PROFILE[$DATASET]}"
    local CPUS="${CPUS_PROFILE[$DATASET]}"
    
    # Determine model config name for Python invocation
    if [ "$CONFIG" = "tuned" ]; then
        MODEL_CFG="${MODEL}_tuned"
    else
        MODEL_CFG="${MODEL}"
    fi
    
    # Determine project name based on dataset
    case $DATASET in
        CADETS_E3)
            PROJECT="pidsmaker-cadets"
            ;;
        THEIA_E3)
            PROJECT="pidsmaker-theia"
            ;;
        CLEARSCOPE_E3)
            PROJECT="pidsmaker-clearscope"
            ;;
    esac
    
    echo "Generating script: $SCRIPT_FILE"
    
    cat > "$SCRIPT_FILE" << 'EOFSCRIPT'
#!/bin/bash
#SBATCH --job-name=JOB_NAME_PLACEHOLDER
#SBATCH --partition=milan-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=CPUS_PLACEHOLDER
#SBATCH --mem=MEM_PLACEHOLDER
#SBATCH --gres=gpu:1
#SBATCH --time=TIME_PLACEHOLDER
#SBATCH --output=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_ctn_%j.out
#SBATCH --error=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_ctn_%j.err

set -x
set -e

# Ensure log directory exists on shared storage
mkdir -p LOG_DIR_PLACEHOLDER

# Environment
export WANDB_MODE=offline
export PYTHONUNBUFFERED=1

# Job-specific paths
JOB_ID=$SLURM_JOB_ID
# Use unique port per job to avoid conflicts when multiple jobs run on same node
PG_PORT=$((55432 + (JOB_ID % 1000)))
# Prefer node-local scratch if available to avoid shared /fred quota
TMPDIR_BASE="${SLURM_TMPDIR}"
if [ -z "${TMPDIR_BASE}" ]; then
    # Fallbacks if SLURM_TMPDIR is not set
    if [ -d "/scratch" ] && [ -w "/scratch" ]; then
        TMPDIR_BASE="/scratch/${USER}/${JOB_ID}"
    else
        TMPDIR_BASE="/fred/oz396/dunguyen/tmp"
    fi
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
        PG_BIN_PLACEHOLDER/pg_ctl -D "${PGDATA}" stop -m fast || true
    fi
    # Persist only lightweight logs to shared storage to avoid quota issues
    if [ -d "${TMPDIR}" ]; then
        ( cd "${TMPDIR}" && tar -czf "LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_ctn_${JOB_ID}_logs.tar.gz" --ignore-failed-read --warning=no-file-changed -- *.log 2>/dev/null ) || true
    fi
    rm -rf "${TMPDIR}"
}
trap cleanup EXIT

# Ensure Apptainer is available on compute node
if ! command -v apptainer >/dev/null 2>&1; then
    module load apptainer || true
fi
command -v apptainer || { echo "ERROR: apptainer not found in PATH" >&2; exit 127; }

# Initialize PostgreSQL with UTF-8
echo "Initializing PostgreSQL..."
PG_BIN_PLACEHOLDER/initdb -D "${PGDATA}" \
    --encoding=UTF8 \
    --locale=en_US.UTF-8 \
    --auth=trust \
    --username=postgres

# Start PostgreSQL
echo "Starting PostgreSQL on port ${PG_PORT}..."
PG_BIN_PLACEHOLDER/pg_ctl -D "${PGDATA}" -l "${PG_LOG}" -o "-p ${PG_PORT}" start

# Wait for PostgreSQL to be ready
sleep 10
for i in {1..30}; do
    if PG_BIN_PLACEHOLDER/pg_ctl -D "${PGDATA}" status > /dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Create database and restore from dump
echo "Creating database and restoring from dump..."
PG_BIN_PLACEHOLDER/createdb -h 127.0.0.1 -p ${PG_PORT} -U postgres DATASET_LC_PLACEHOLDER || echo "Database DATASET_LC_PLACEHOLDER may already exist"

echo "Restoring database from /fred/oz396/dunguyen/data/DATASET_LC_PLACEHOLDER.dump..."
PG_BIN_PLACEHOLDER/pg_restore -h 127.0.0.1 -p ${PG_PORT} -U postgres -d DATASET_LC_PLACEHOLDER \
    /fred/oz396/dunguyen/data/DATASET_LC_PLACEHOLDER.dump || echo "Restore may have completed with warnings"

# Run PIDSMaker inside Apptainer
echo "Running PIDSMaker..."
apptainer exec --nv \
    -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
    -B "${TMPDIR}:${TMPDIR}" \
    CONTAINER_PLACEHOLDER \
    bash -lc "cd /opt/PIDSMaker && \
    python -m pidsmaker.main MODEL_CFG_PLACEHOLDER DATASET_PLACEHOLDER \
        --artifact_dir_in_container ${ARTIFACT_DIR} \
        --restart_from_scratch \
        --force_restart=build_graphs \
        --db_port ${PG_PORT} \
        --wandb --project PROJECT_PLACEHOLDER \
        2>&1 | tee ${RUN_LOG}"

echo "Job completed successfully."
EOFSCRIPT
    
    # Replace placeholders
    sed -i "s|JOB_NAME_PLACEHOLDER|${JOB_NAME}|g" "$SCRIPT_FILE"
    sed -i "s|CPUS_PLACEHOLDER|${CPUS}|g" "$SCRIPT_FILE"
    sed -i "s|MEM_PLACEHOLDER|${MEM}|g" "$SCRIPT_FILE"
    sed -i "s|TIME_PLACEHOLDER|${TIME}|g" "$SCRIPT_FILE"
    sed -i "s|LOG_DIR_PLACEHOLDER|${LOG_DIR}|g" "$SCRIPT_FILE"
    sed -i "s|PG_BIN_PLACEHOLDER|${PG_BIN}|g" "$SCRIPT_FILE"
    sed -i "s|CONTAINER_PLACEHOLDER|${CONTAINER}|g" "$SCRIPT_FILE"
    sed -i "s|MODEL_CFG_PLACEHOLDER|${MODEL_CFG}|g" "$SCRIPT_FILE"
    sed -i "s|DATASET_PLACEHOLDER|${DATASET}|g" "$SCRIPT_FILE"
    sed -i "s|DATASET_LC_PLACEHOLDER|${DATASET,,}|g" "$SCRIPT_FILE"
    sed -i "s|PROJECT_PLACEHOLDER|${PROJECT}|g" "$SCRIPT_FILE"
    
    chmod +x "$SCRIPT_FILE"
    
    # Submit the job
    echo "Submitting job: ${JOB_NAME}"
    JOB_ID=$(sbatch --parsable "$SCRIPT_FILE")
    JOB_IDS+=("$JOB_ID")
    echo "  → Job ID: $JOB_ID"
    echo ""
    
    # Small delay to avoid overwhelming the scheduler
    sleep 1
}

# Main execution
echo "============================================"
echo "PIDSMaker E3 Batch Submission"
echo "18 jobs: 3 datasets × 3 models × 2 configs"
echo "============================================"
echo ""

# Submit all jobs
for DATASET in "${DATASETS[@]}"; do
    echo "--- Dataset: $DATASET ---"
    for MODEL in "${MODELS[@]}"; do
        for CONFIG in "default" "tuned"; do
            submit_job "$MODEL" "$CONFIG" "$DATASET"
        done
    done
    echo ""
done

# Summary
echo "============================================"
echo "Submission complete!"
echo "Total jobs submitted: ${#JOB_IDS[@]}"
echo "Job IDs: ${JOB_IDS[*]}"
echo "============================================"
echo ""
echo "Monitor with:"
echo "  squeue -j $(IFS=,; echo "${JOB_IDS[*]}")"
echo ""
echo "Check status:"
echo "  sacct -j $(IFS=,; echo "${JOB_IDS[*]}") --format=JobID,JobName,State,Elapsed,MaxRSS"
