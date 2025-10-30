#!/bin/bash
#
# Submit jobs to Milan CPU partition (no GPU)
# Same 18 jobs as GPU version but on CPU nodes
#
# Usage: bash scripts/submit_all_e3_milan_cpu.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="/home/dunguyen/git/PIDSMaker/scripts"
LOG_DIR="/fred/oz411/dunguyen/slurm-logs"
CONTAINER="/fred/oz411/dunguyen/containers/pidsmaker_cuda117.sif"

# Datasets to run
DATASETS=("CADETS_E3" "THEIA_E3" "CLEARSCOPE_E3")

# Models and their configs
MODELS=("orthrus" "magic" "kairos")

# Track submitted job IDs
declare -a JOB_IDS

# Resource profiles per dataset (adjusted for CPU)
declare -A MEM_PROFILE
MEM_PROFILE["CADETS_E3"]="48GB"
MEM_PROFILE["THEIA_E3"]="64GB"
MEM_PROFILE["CLEARSCOPE_E3"]="48GB"

declare -A TIME_PROFILE
TIME_PROFILE["CADETS_E3"]="02:00:00"  # Double time for CPU
TIME_PROFILE["THEIA_E3"]="03:00:00"
TIME_PROFILE["CLEARSCOPE_E3"]="02:00:00"

declare -A CPUS_PROFILE
CPUS_PROFILE["CADETS_E3"]="1"  # 1 CPU for CPU-only
CPUS_PROFILE["THEIA_E3"]="1"
CPUS_PROFILE["CLEARSCOPE_E3"]="1"

# Function to generate and submit a single job
submit_job() {
    local MODEL=$1
    local CONFIG=$2
    local DATASET=$3
    
    local JOB_NAME="${MODEL}_${CONFIG}_${DATASET,,}"
    local SCRIPT_FILE="${SCRIPT_DIR}/run_${JOB_NAME}_milan_cpu_apptainer.slurm"
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
#SBATCH --partition=milan
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=CPUS_PLACEHOLDER
#SBATCH --mem=MEM_PLACEHOLDER
#SBATCH --time=TIME_PLACEHOLDER
#SBATCH --output=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_milan_cpu_%j.out
#SBATCH --error=LOG_DIR_PLACEHOLDER/JOB_NAME_PLACEHOLDER_milan_cpu_%j.err

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

# Database connection info (shared PostgreSQL on login node tooarrana2)
echo "Connecting to shared PostgreSQL at tooarrana2:5432..."
echo "Database: DATASET_LC_PLACEHOLDER"

# Run PIDSMaker inside Apptainer (CPU mode - no GPU required)
echo "Running PIDSMaker on CPU..."
set -o pipefail
apptainer exec \
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
    sed -i "s|JOB_NAME_PLACEHOLDER|${JOB_NAME}|g" "$SCRIPT_FILE"
    sed -i "s|CPUS_PLACEHOLDER|${CPUS}|g" "$SCRIPT_FILE"
    sed -i "s|MEM_PLACEHOLDER|${MEM}|g" "$SCRIPT_FILE"
    sed -i "s|TIME_PLACEHOLDER|${TIME}|g" "$SCRIPT_FILE"
    sed -i "s|LOG_DIR_PLACEHOLDER|${LOG_DIR}|g" "$SCRIPT_FILE"
    sed -i "s|CONTAINER_PLACEHOLDER|${CONTAINER}|g" "$SCRIPT_FILE"
    sed -i "s|MODEL_CFG_PLACEHOLDER|${MODEL_CFG}|g" "$SCRIPT_FILE"
    sed -i "s|DATASET_PLACEHOLDER|${DATASET}|g" "$SCRIPT_FILE"
    sed -i "s|DATASET_LC_PLACEHOLDER|${DATASET,,}|g" "$SCRIPT_FILE"
    sed -i "s|PROJECT_PLACEHOLDER|${PROJECT}|g" "$SCRIPT_FILE"
    
    chmod +x "$SCRIPT_FILE"
    
    # Submit the job
    echo "Submitting job: ${JOB_NAME} to milan (CPU)"
    JOB_ID=$(sbatch --parsable "$SCRIPT_FILE")
    JOB_IDS+=("$JOB_ID")
    echo "  → Job ID: $JOB_ID (milan CPU)"
    echo ""
    
    # Small delay to avoid overwhelming the scheduler
    sleep 0.5
}

# Main execution
echo "============================================"
echo "PIDSMaker E3 Batch Submission - Milan CPU"
echo "18 jobs: 3 datasets × 3 models × 2 configs"
echo "============================================"
echo ""

# Submit all jobs to Milan CPU partition
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
