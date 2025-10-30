#!/bin/bash
#
# Master submission script for 18 E3 jobs (3 datasets × 3 models × 2 configs)
# Based on reproduction best practices for ORTHRUS, KAIROS, and MAGIC
#
# Usage: bash scripts/submit_all_e3_jobs.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="/home/dunguyen/git/PIDSMaker/scripts"
LOG_DIR="/fred/oz411/dunguyen/slurm-logs"
CONTAINER="/fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif"
PG_BIN="/fred/oz411/dunguyen/.conda/envs/pg17/bin"

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
CPUS_PROFILE["CADETS_E3"]="1"
CPUS_PROFILE["THEIA_E3"]="1"
CPUS_PROFILE["CLEARSCOPE_E3"]="1"

# Function to generate and submit a single job
submit_job() {
    local MODEL=$1
    local CONFIG=$2
    local DATASET=$3
    local PARTITION=$4  # milan-gpu or skylake-gpu
    
    local JOB_NAME="${MODEL}_${CONFIG}_${DATASET,,}"
    local SCRIPT_FILE="${SCRIPT_DIR}/run_${JOB_NAME}_${PARTITION//-/_}_apptainer.slurm"
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
#SBATCH --partition=PARTITION_PLACEHOLDER
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=CPUS_PLACEHOLDER
#SBATCH --mem=MEM_PLACEHOLDER
#SBATCH --gres=gpu:1
#SBATCH --time=TIME_PLACEHOLDER
#SBATCH --output=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_PARTITION_SUFFIX_PLACEHOLDER_%j.out
#SBATCH --error=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_PARTITION_SUFFIX_PLACEHOLDER_%j.err

set -x
set -e

# Ensure log directory exists on shared storage
mkdir -p LOG_DIR_PLACEHOLDER

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
echo "Database: DATASET_LC_PLACEHOLDER"

# Run PIDSMaker inside Apptainer
echo "Running PIDSMaker..."
set -o pipefail
apptainer exec --nv \
    -B /home/dunguyen/git/PIDSMaker:/opt/PIDSMaker \
    -B "${TMPDIR}:${TMPDIR}" \
    CONTAINER_PLACEHOLDER \
    bash -lc "set -o pipefail; cd /opt/PIDSMaker && \
    python -m pidsmaker.main MODEL_CFG_PLACEHOLDER DATASET_PLACEHOLDER \
        --artifact_dir ${ARTIFACT_DIR} \
        --restart_from_scratch \
        --force_restart=build_graphs \
        --database_host tooarrana2 \
        --database_port 5432 \
        --wandb --project PROJECT_PLACEHOLDER \
        2>&1 | tee ${RUN_LOG}"
PY_EXIT=$?
if [ $PY_EXIT -ne 0 ]; then
    echo "PIDSMaker exited with code ${PY_EXIT}" >&2
    exit $PY_EXIT
fi

echo "Job completed successfully."
EOFSCRIPT
    
    # Replace placeholders
    local PARTITION_SUFFIX="${PARTITION//-/_}"
    sed -i "s|JOB_NAME_PLACEHOLDER|${JOB_NAME}|g" "$SCRIPT_FILE"
    sed -i "s|PARTITION_PLACEHOLDER|${PARTITION}|g" "$SCRIPT_FILE"
    sed -i "s|PARTITION_SUFFIX_PLACEHOLDER|${PARTITION_SUFFIX}|g" "$SCRIPT_FILE"
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
    echo "Submitting job: ${JOB_NAME} to ${PARTITION}"
    JOB_ID=$(sbatch --parsable "$SCRIPT_FILE")
    JOB_IDS+=("$JOB_ID")
    echo "  → Job ID: $JOB_ID (${PARTITION})"
    echo ""
    
    # Small delay to avoid overwhelming the scheduler
    sleep 0.5
}

# Main execution
echo "============================================"
echo "PIDSMaker E3 Batch Submission - Milan GPU"
echo "18 jobs: 3 datasets × 3 models × 2 configs"
echo "============================================"
echo ""

# Submit all jobs to milan-gpu partition only
for DATASET in "${DATASETS[@]}"; do
    echo "--- Dataset: $DATASET ---"
    for MODEL in "${MODELS[@]}"; do
        for CONFIG in "default" "tuned"; do
            # Submit to milan-gpu only
            submit_job "$MODEL" "$CONFIG" "$DATASET" "milan-gpu"
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
