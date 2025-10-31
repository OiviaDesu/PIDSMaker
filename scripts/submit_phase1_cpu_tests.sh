#!/bin/bash
# Submit all Phase 1 CPU test jobs
# Usage: ./submit_phase1_cpu_tests.sh

echo "=================================================="
echo "SUBMITTING PHASE 1 CPU TEST JOBS"
echo "=================================================="
echo ""

echo "📋 Submitting 4 CPU test jobs..."
echo ""

# Submit Orthrus
echo "1/4 Submitting Orthrus Phase 1a (CPU)..."
ORTHRUS_JOB=$(sbatch scripts/run_orthrus_phase1_cadets_e3_milan_cpu_apptainer.slurm | awk '{print $4}')
echo "    ✓ Job ID: $ORTHRUS_JOB"

# Submit Kairos
echo "2/4 Submitting Kairos Phase 1 (CPU)..."
KAIROS_JOB=$(sbatch scripts/run_kairos_phase1_cadets_e3_milan_cpu_apptainer.slurm | awk '{print $4}')
echo "    ✓ Job ID: $KAIROS_JOB"

# Submit Magic Baseline
echo "3/4 Submitting Magic Phase 1 Baseline (CPU)..."
MAGIC_JOB=$(sbatch scripts/run_magic_phase1_cadets_e3_milan_cpu_apptainer.slurm | awk '{print $4}')
echo "    ✓ Job ID: $MAGIC_JOB"

# Submit Magic Adaptive
echo "4/4 Submitting Magic Adaptive (CPU)..."
MAGIC_ADAPT_JOB=$(sbatch scripts/run_magic_adaptive_cadets_e3_milan_cpu_apptainer.slurm | awk '{print $4}')
echo "    ✓ Job ID: $MAGIC_ADAPT_JOB"

echo ""
echo "=================================================="
echo "✅ ALL JOBS SUBMITTED"
echo "=================================================="
echo ""
echo "Job IDs:"
echo "  Orthrus:       $ORTHRUS_JOB"
echo "  Kairos:        $KAIROS_JOB"
echo "  Magic:         $MAGIC_JOB"
echo "  Magic Adapt:   $MAGIC_ADAPT_JOB"
echo ""
echo "Monitor with:"
echo "  squeue -u $USER -j $ORTHRUS_JOB,$KAIROS_JOB,$MAGIC_JOB,$MAGIC_ADAPT_JOB"
echo ""
echo "⏱️  Expected runtime: 2-5 hours (CPU slower than GPU)"
echo ""
echo "Note: CPU jobs use partition 'milan' (not 'milan-gpu')"
echo "=================================================="
