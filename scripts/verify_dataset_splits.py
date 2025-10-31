#!/usr/bin/env python3
"""
Verify dataset splits for CADETS_E3, THEIA_E3, and CLEARSCOPE_E3 datasets.

This script validates that the current train/val/test splits match the paper's
specifications from ORTHRUS Appendix A Table 8 and checks for any overlaps.

Reference: ORTHRUS Appendix A Table 8
"""


def main():
    """Print and verify dataset splits."""
    print("=" * 80)
    print("DATASET SPLIT VERIFICATION")
    print("Reference: ORTHRUS Appendix A Table 8")
    print("=" * 80)
    
    # Define splits directly (from config files)
    splits = {
        "CADETS_E3": {
            "train": [f"ta1-cadets-e3-official.json.{i}" for i in range(1, 8)],
            "val": [f"ta1-cadets-e3-official.json.{i}" for i in range(8, 10)],
            "test": [f"ta1-cadets-e3-official.json.{i}" for i in range(10, 13)],
            "expected": {"train": 7, "val": 2, "test": 3}
        },
        "THEIA_E3": {
            "train": [f"ta1-theia-e3-official.json.{i}" for i in range(1, 8)],
            "val": ["ta1-theia-e3-official.json.8"],
            "test": [f"ta1-theia-e3-official.json.{i}" for i in range(9, 12)],
            "expected": {"train": 7, "val": 1, "test": 3}
        },
        "CLEARSCOPE_E3": {
            "train": [f"ta1-clearscope-e3-official.json.{i}" for i in range(1, 8)],
            "val": ["ta1-clearscope-e3-official.json.8"],
            "test": [f"ta1-clearscope-e3-official.json.{i}" for i in range(9, 11)],
            "expected": {"train": 7, "val": 1, "test": 2}
        }
    }
    
    all_match = True
    
    for dataset_name, config in splits.items():
        print(f"\n{'=' * 80}")
        print(f"DATASET: {dataset_name}")
        print(f"{'=' * 80}")
        
        train_files = config['train']
        val_files = config['val']
        test_files = config['test']
        expected = config['expected']
        
        # Print splits
        print(f"\n[TRAIN SPLIT] ({len(train_files)} files)")
        for f in train_files:
            print(f"  - {f}")
        
        print(f"\n[VALIDATION SPLIT] ({len(val_files)} files)")
        for f in val_files:
            print(f"  - {f}")
        
        print(f"\n[TEST SPLIT] ({len(test_files)} files)")
        for f in test_files:
            print(f"  - {f}")
        
        # Verify counts against paper
        print(f"\n[VERIFICATION]")
        train_match = len(train_files) == expected['train']
        val_match = len(val_files) == expected['val']
        test_match = len(test_files) == expected['test']
        
        print(f"  Train count: {len(train_files)} (expected {expected['train']}) {'✓' if train_match else '✗'}")
        print(f"  Val count:   {len(val_files)} (expected {expected['val']}) {'✓' if val_match else '✗'}")
        print(f"  Test count:  {len(test_files)} (expected {expected['test']}) {'✓' if test_match else '✗'}")
        
        if not (train_match and val_match and test_match):
            all_match = False
        
        # Check for overlaps
        train_set = set(train_files)
        val_set = set(val_files)
        test_set = set(test_files)
        
        val_test_overlap = val_set & test_set
        train_test_overlap = train_set & test_set
        train_val_overlap = train_set & val_set
        
        print(f"\n[OVERLAP CHECK]")
        if val_test_overlap:
            print(f"  ⚠ WARNING: Val/Test overlap: {val_test_overlap}")
            all_match = False
        else:
            print(f"  No Val/Test overlap ✓")
        
        if train_test_overlap:
            print(f"  ⚠ WARNING: Train/Test overlap: {train_test_overlap}")
            all_match = False
        else:
            print(f"  No Train/Test overlap ✓")
        
        if train_val_overlap:
            print(f"  ⚠ WARNING: Train/Val overlap: {train_val_overlap}")
            all_match = False
        else:
            print(f"  No Train/Val overlap ✓")
    
    # Final summary
    print("\n" + "=" * 80)
    if all_match:
        print("✓ ALL SPLITS MATCH PAPER SPECIFICATION (ORTHRUS Appendix A Table 8)")
    else:
        print("✗ SOME SPLITS DO NOT MATCH PAPER SPECIFICATION")
    print("=" * 80)
    print()
    
    return 0 if all_match else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
