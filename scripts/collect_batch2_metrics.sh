#!/usr/bin/env bash
set -euo pipefail
# Collect metrics for Batch 2 jobs and write results/batch2_metrics.csv
# Usage: ./scripts/collect_batch2_metrics.sh

JOBIDS=(
6531376 6531380 6531381 6531382 6531383 6531384 6531385 6531386 6531387 6531388 6531389 6531390 6531391 6531392 6531393 6531394 6531395 6531396
)

python scripts/python/collect_metrics.py "${JOBIDS[@]}"
