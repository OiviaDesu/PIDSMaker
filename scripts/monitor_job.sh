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

# Helper: find best matching slurm log file for this JOBID
find_log_file() {
    local jid="$1"
    # Common patterns produced by our scripts: *_ctn_<JOBID>.out
    local cand
    cand=$(ls -1 "$HOME"/slurm-logs/*_ctn_"${jid}".out 2>/dev/null | head -n1 || true)
    if [[ -n "$cand" ]]; then
        echo "$cand"
        return 0
    fi

    # Fallback: any file ending with _<JOBID>.out
    cand=$(ls -1 "$HOME"/slurm-logs/*_"${jid}".out 2>/dev/null | head -n1 || true)
    if [[ -n "$cand" ]]; then
        echo "$cand"
        return 0
    fi

    # Last resort: any file containing the JOBID
    cand=$(ls -1 "$HOME"/slurm-logs/*"${jid}"*.out 2>/dev/null | head -n1 || true)
    if [[ -n "$cand" ]]; then
        echo "$cand"
        return 0
    fi

    echo "" # none found
}

while true; do
    # Get job state
    STATE=$(sacct -j "$JOBID" --format=State -n | head -1 | xargs)
    ELAPSED=$(sacct -j "$JOBID" --format=Elapsed -n | head -1 | xargs)
    
    if [ "$STATE" = "RUNNING" ]; then
        echo "[$(date '+%H:%M:%S')] Job $JOBID: RUNNING (elapsed: $ELAPSED)"
        
        # Show last 3 lines of output from detected log
        LOG_FILE=$(find_log_file "$JOBID")
        if [[ -n "$LOG_FILE" ]]; then
            tail -n 3 "$LOG_FILE" 2>/dev/null | sed 's/^/  | /'
        else
            echo "  | (log file not found yet in ~/slurm-logs)"
        fi
        
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
        LOG_FILE=$(find_log_file "$JOBID")
        if [[ -n "$LOG_FILE" ]]; then
            echo "  Stdout: $LOG_FILE"
            # Derive base without extension for related files
            BASE_NOEXT="${LOG_FILE%.out}"
            echo "  Stderr: ${BASE_NOEXT}.err"
            echo "  Tarball: ${BASE_NOEXT}.tar.gz"
        else
            echo "  (log files not found in ~/slurm-logs yet)"
        fi
        echo ""
        echo "To sync W&B and extract artifacts:"
        echo "  ./scripts/sync_wandb_run.sh $JOBID"
        
        break
    fi
done
