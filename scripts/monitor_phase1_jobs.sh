#!/bin/bash
# Monitor Phase 1 test jobs
# Usage: ./monitor_phase1_jobs.sh

JOBS="6552895 6552896 6552897 6552898"
LOG_DIR="/fred/oz411/dunguyen/slurm-logs"

echo "=================================================="
echo "PHASE 1 MULTI-MODEL TEST JOBS MONITOR"
echo "=================================================="
echo ""
echo "Jobs being monitored:"
echo "  6552895 - orthrus_tuned_cadets_e3 (Phase 1a validation)"
echo "  6552896 - kairos_phase1_cadets_e3 (Queue detection)"
echo "  6552897 - magic_phase1_cadets_e3 (KNN baseline)"
echo "  6552898 - magic_adaptive_cadets_e3 (KNN + adaptation)"
echo ""
echo "=================================================="
echo ""

while true; do
    clear
    echo "=== JOB STATUS (refreshed every 30s) ==="
    echo ""
    
    squeue -u dunguyen -j $JOBS --format="%.10i %.30j %.10T %.10M %.9l %R" 2>/dev/null || echo "All jobs completed or not found"
    
    echo ""
    echo "=== COMPLETED JOBS CHECK ==="
    
    for job_id in $JOBS; do
        # Check for output files
        OUT_FILE=$(ls -t $LOG_DIR/*_${job_id}.out 2>/dev/null | head -1)
        
        if [ -f "$OUT_FILE" ]; then
            # Get job name from file
            JOB_NAME=$(basename "$OUT_FILE" | sed 's/_[0-9]*\.out$//')
            
            # Check if job finished
            if tail -1 "$OUT_FILE" 2>/dev/null | grep -q "Job completed successfully"; then
                echo "✅ Job $job_id ($JOB_NAME) - COMPLETED"
                
                # Extract key metrics
                if grep -q "TP:" "$OUT_FILE"; then
                    TP=$(grep "TP:" "$OUT_FILE" | tail -1 | awk '{print $2}')
                    FP=$(grep "FP:" "$OUT_FILE" | tail -1 | awk '{print $4}')
                    echo "   → Results: TP=$TP, FP=$FP"
                fi
            elif grep -q "ERROR\|Error\|error\|Traceback\|FAILED" "$OUT_FILE"; then
                echo "❌ Job $job_id ($JOB_NAME) - ERROR DETECTED"
                echo "   → Check: tail -100 $OUT_FILE"
            else
                # Check last update time
                LAST_MOD=$(stat -c %Y "$OUT_FILE" 2>/dev/null)
                NOW=$(date +%s)
                AGE=$((NOW - LAST_MOD))
                
                if [ $AGE -lt 60 ]; then
                    echo "🔄 Job $job_id ($JOB_NAME) - RUNNING (active)"
                elif [ $AGE -lt 300 ]; then
                    echo "⏳ Job $job_id ($JOB_NAME) - RUNNING (last update ${AGE}s ago)"
                else
                    echo "⚠️  Job $job_id ($JOB_NAME) - STALLED? (last update $((AGE/60))m ago)"
                fi
            fi
        else
            echo "⏳ Job $job_id - PENDING (no output file yet)"
        fi
    done
    
    echo ""
    echo "=== QUEUE POSITION ==="
    echo "Total pending jobs ahead:"
    AHEAD=$(squeue -u dunguyen -t PENDING -j $JOBS --format="%i" 2>/dev/null | tail -n +2 | wc -l)
    echo "  Your jobs pending: $AHEAD / 4"
    
    ALL_AHEAD=$(squeue -u dunguyen -t PENDING --format="%i" 2>/dev/null | tail -n +2 | wc -l)
    echo "  Total jobs in queue: $ALL_AHEAD"
    
    echo ""
    echo "Press Ctrl+C to exit. Refreshing in 30s..."
    sleep 30
done
