#!/usr/bin/env bash
set -euo pipefail
# Watch Batch 2 jobs until completion, then collect metrics and generate summaries.
# Usage: ./scripts/watch_and_collect_batch2.sh [interval_seconds]

INTERVAL="${1:-60}"

JOBIDS=(
6531376 6531380 6531381 6531382 6531383 6531384 6531385 6531386 6531387 6531388 6531389 6531390 6531391 6531392 6531393 6531394 6531395 6531396
)

join_by_comma() { local IFS=","; echo "$*"; }
JOBLIST=$(join_by_comma "${JOBIDS[@]}")

echo "Watching jobs: ${JOBLIST} (interval ${INTERVAL}s)"

# Function to count active jobs in squeue
active_count() {
  squeue -h -j "$JOBLIST" | wc -l | tr -d ' '
}

# Function to print a compact status line
print_status() {
  squeue -j "$JOBLIST" -o "%.10i %.28j %.8T %.10M %.6D" | sed -e '1!b' -e '1,1{s/.*/JOBID       NAME                        STATE     ELAPSED   NODES/}'
}

# Poll until no jobs remain active in the queue
while true; do
  AC=$(active_count)
  if [[ "$AC" == "0" ]]; then
    echo "All jobs have left the queue. Proceeding to metrics collection..."
    break
  fi
  printf '[%s] Queue still active: %s jobs\n' "$(date +%H:%M:%S)" "$AC"
  print_status || true
  sleep "$INTERVAL"
done

# Collect metrics
./scripts/collect_batch2_metrics.sh || true

# Generate markdown summaries and append to result.md
python scripts/python/generate_markdown_summary.py || true

# Optional auto-commit
if [[ "${PUSH:-0}" == "1" ]]; then
  git add results/batch2_metrics.csv results/batch2_summary.md result.md
  git commit -m "Add Batch 2 results (auto-generated)"
  git push origin supercomputer
fi

echo "Done. See results/batch2_metrics.csv, results/batch2_summary.md, and result.md."
