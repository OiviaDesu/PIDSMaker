#!/bin/bash
# Monitor a Slurm job until completion
# Usage: ./scripts/monitor_job.sh <JOBID> [interval_seconds]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <JOBID> [interval_seconds]"
    echo "Example: $0 6357922 30"
    exit 1
fi

JOBID="$1"
INTERVAL="${2:-30}"  # Default 30 seconds

echo "Monitoring job $JOBID (checking every ${INTERVAL}s)..."
echo "Press Ctrl+C to stop monitoring."
echo ""

while true; do
    # Get job state
    STATE=$(sacct -j "$JOBID" --format=State -n | head -1 | xargs)
    ELAPSED=$(sacct -j "$JOBID" --format=Elapsed -n | head -1 | xargs)
    
    if [ "$STATE" = "RUNNING" ]; then
        echo "[$(date '+%H:%M:%S')] Job $JOBID: RUNNING (elapsed: $ELAPSED)"
        
        # Show last 3 lines of output
        tail -n 3 "$HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.out" 2>/dev/null | sed 's/^/  | /'
        
        sleep "$INTERVAL"
    elif [ "$STATE" = "PENDING" ]; then
        echo "[$(date '+%H:%M:%S')] Job $JOBID: PENDING"
        sleep "$INTERVAL"
    else
        echo ""
        echo "========================================="
        echo "Job $JOBID has completed!"
        echo "Final state: $STATE"
        echo "Total elapsed: $ELAPSED"
        echo "========================================="
        echo ""
        
        # Show job summary
        sacct -j "$JOBID" --format=JobID,JobName%30,State,ExitCode,Elapsed,MaxRSS,NodeList
        
        echo ""
        echo "Logs:"
        echo "  Stdout: $HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.out"
        echo "  Stderr: $HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.err"
        echo "  Tarball: $HOME/slurm-logs/orthus_cadets_e3_ctn_${JOBID}.tar.gz"
        echo ""
        echo "To sync W&B and extract artifacts:"
        echo "  ./scripts/sync_wandb_run.sh $JOBID"
        
        break
    fi
done
