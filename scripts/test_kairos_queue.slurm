#!/bin/bash
#SBATCH --job-name=test_kairos_queue
#SBATCH --partition=milan-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32GB
#SBATCH --time=0:30:00
#SBATCH --output=/fred/oz396/dunguyen/slurm-logs/test_kairos_queue_%j.out
#SBATCH --error=/fred/oz396/dunguyen/slurm-logs/test_kairos_queue_%j.err

# Test KAIROS queue_evaluation on CADETS_E3 to verify code works
echo "Testing KAIROS queue_evaluation on CADETS_E3..."
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start time: $(date)"

# PostgreSQL setup
export PG_BIN=/fred/oz396/dunguyen/.conda/envs/pg17/bin
export PGDATA=$TMPDIR/postgres_data_$SLURM_JOB_ID
export PGPORT=55432
export PGHOST=localhost

# Initialize PostgreSQL with UTF-8 encoding
echo "Initializing PostgreSQL..."
$PG_BIN/initdb --encoding=UTF8 --locale=en_US.UTF-8 -D $PGDATA
$PG_BIN/pg_ctl -D $PGDATA -l $TMPDIR/postgres_$SLURM_JOB_ID.log -o "-p $PGPORT" start
sleep 5

# Create database
$PG_BIN/createdb -h $PGHOST -p $PGPORT pidsmaker

# Container and artifact setup
CONTAINER=/fred/oz396/dunguyen/containers/pidsmaker_cuda117.sif
ARTIFACT_DIR=/fred/oz396/dunguyen/artifacts/test_kairos_queue_${SLURM_JOB_ID}
mkdir -p $ARTIFACT_DIR

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    $PG_BIN/pg_ctl -D $PGDATA stop
    echo "PostgreSQL stopped"
}
trap cleanup EXIT

# Run KAIROS with queue_evaluation
echo "Running KAIROS with queue_evaluation..."
export WANDB_MODE=offline

apptainer exec --nv \
    --bind /fred/oz396/dunguyen:/fred/oz396/dunguyen \
    --bind $TMPDIR:$TMPDIR \
    --pwd /fred/oz396/dunguyen/git/PIDSMaker \
    $CONTAINER \
    python -m pidsmaker.main config/kairos.yml CADETS_E3 \
    --artifact_dir_in_container ${ARTIFACT_DIR} \
    --restart_from_scratch \
    --force_restart=build_graphs \
    --wandb \
    --project test_kairos_queue_eval

echo "Test complete at $(date)"
