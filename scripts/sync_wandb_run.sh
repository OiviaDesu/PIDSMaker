#!/bin/bash
# Sync W&B offline run and extract artifacts from a completed Slurm job
# Usage: ./scripts/sync_wandb_run.sh <JOBID>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <JOBID>"
    echo "Example: $0 6357922"
    exit 1
fi

JOBID="$1"
TARBALL="$HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.tar.gz"
EXTRACT_DIR="$HOME/slurm-logs/pids_run_${JOBID}"

# Check if tarball exists
if [ ! -f "$TARBALL" ]; then
    echo "ERROR: Tarball not found: $TARBALL"
    echo "Make sure the job has completed and artifacts were packaged."
    exit 1
fi

echo "========================================="
echo "W&B Sync & Artifact Extraction"
echo "Job ID: $JOBID"
echo "========================================="
echo ""

# Extract tarball
echo "[1/4] Extracting artifacts from tarball..."
if [ -d "$EXTRACT_DIR" ]; then
    echo "WARNING: Extract directory already exists: $EXTRACT_DIR"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    rm -rf "$EXTRACT_DIR"
fi

mkdir -p "$HOME/slurm-logs"
cd "$HOME/slurm-logs"
tar -xzf "orthus_cadets_e3_ctn_${JOBID}.tar.gz"
echo "✓ Extracted to: $EXTRACT_DIR"
echo ""

# Find W&B offline run directories
echo "[2/4] Locating W&B offline runs..."
WANDB_DIRS=$(find "$EXTRACT_DIR/wandb" -type d -name "offline-run-*" 2>/dev/null || true)

if [ -z "$WANDB_DIRS" ]; then
    echo "WARNING: No W&B offline runs found in $EXTRACT_DIR/wandb"
    echo "The job may not have logged to W&B, or WANDB_MODE was not set to offline."
else
    echo "Found W&B offline run(s):"
    echo "$WANDB_DIRS"
    echo ""
    
    # Sync each offline run
    echo "[3/4] Syncing to W&B servers..."
    for run_dir in $WANDB_DIRS; do
        echo "Syncing: $run_dir"
        wandb sync "$run_dir" || {
            echo "ERROR: wandb sync failed for $run_dir"
            echo "Check your W&B API key and network connection."
            exit 1
        }
    done
    echo "✓ W&B sync complete!"
    echo ""
fi

# Summary of artifacts
echo "[4/4] Artifact summary..."
echo ""
echo "Artifacts location: $EXTRACT_DIR/artifacts/"
echo ""

# Show key artifact directories
if [ -d "$EXTRACT_DIR/artifacts" ]; then
    echo "Directory structure:"
    tree -L 3 -d "$EXTRACT_DIR/artifacts" 2>/dev/null || find "$EXTRACT_DIR/artifacts" -type d -maxdepth 3 | head -20
    echo ""
    
    # Show evaluation results if available
    RESULTS_FILE=$(find "$EXTRACT_DIR/artifacts/detection/evaluation" -name "results.pth" 2>/dev/null | head -1)
    if [ -n "$RESULTS_FILE" ]; then
        echo "Evaluation results found at:"
        echo "  $RESULTS_FILE"
        echo ""
        echo "To inspect results in Python:"
        echo "  import torch"
        echo "  results = torch.load('$RESULTS_FILE')"
        echo "  print(results)"
    fi
    
    # Show GPU stats if available
    GPU_STATS="$HOME/slurm-logs/gpu_stats_${JOBID}.log"
    if [ -f "$GPU_STATS" ]; then
        echo ""
        echo "GPU statistics logged to: $GPU_STATS"
        echo "Peak GPU memory usage:"
        tail -n 1 "$GPU_STATS" 2>/dev/null || echo "(log may be empty)"
    fi
else
    echo "WARNING: No artifacts directory found in extraction."
fi

echo ""
echo "========================================="
echo "✓ Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. View your W&B run at: https://wandb.ai/<entity>/<project>"
echo "2. Inspect artifacts in: $EXTRACT_DIR/artifacts/"
echo "3. Check logs:"
echo "   - Stdout: $HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.out"
echo "   - Stderr: $HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.err"
echo "   - GPU stats: $HOME/slurm-logs/gpu_stats_${JOBID}.log"
