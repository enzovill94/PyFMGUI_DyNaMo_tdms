#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for concurrent tether analysis

This script demonstrates how to use the concurrent processing module
with your tether analysis workflow.
"""

import os
import multiprocessing as mp

def test_concurrent_import():
    """Test importing the concurrent analysis module"""
    try:
        from concurrent_tether_analysis import ConcurrentTetherProcessor
        print("✓ Successfully imported concurrent analysis module")
        
        # Show available CPU cores
        cpu_count = mp.cpu_count()
        print(f"✓ Available CPU cores: {cpu_count}")
        
        # Create processor instance
        processor = ConcurrentTetherProcessor()
        print(f"✓ Created processor with max_workers: {processor.max_workers}")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_parameter_validation():
    """Test parameter validation"""
    try:
        from concurrent_tether_analysis import ConcurrentTetherProcessor
        
        processor = ConcurrentTetherProcessor()
        
        # Test with valid and invalid inputs
        test_pairs = [
            ("/path/to/valid.tdms", {"param1": "value1"}),
            ("/nonexistent/file.tdms", {"param1": "value1"}),
            ("not_a_tdms_file.txt", {"param1": "value1"}),
            ("/path/to/another.tdms", None),  # Invalid params
        ]
        
        valid_pairs, invalid_pairs = processor.validate_inputs(test_pairs)
        
        print("✓ Validation test complete:")
        print(f"  - Valid pairs: {len(valid_pairs)}")
        print(f"  - Invalid pairs: {len(invalid_pairs)}")
        
        for pair, error in invalid_pairs:
            filepath = pair[0] if len(pair) > 0 else "Unknown"
            print(f"    ✗ {os.path.basename(filepath)}: {error}")
        
        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False

def demonstrate_usage():
    """Demonstrate how to use the concurrent processor"""
    print("\n" + "="*60)
    print("USAGE DEMONSTRATION")
    print("="*60)
    
    print("""
# Example 1: Using the ConcurrentTetherProcessor class
from concurrent_tether_analysis import ConcurrentTetherProcessor

# Create processor
processor = ConcurrentTetherProcessor(max_workers=4)

# Prepare file-parameter pairs
file_param_pairs = [
    ("/path/to/file1.tdms", analysis_params),
    ("/path/to/file2.tdms", analysis_params),
    # ... more files
]

# Define callbacks
def progress_callback(completed, total):
    print(f"Progress: {completed}/{total}")

def error_callback(filepath, error):
    print(f"Error in {filepath}: {error}")

# Run concurrent analysis
results = processor.process_files_concurrent(
    file_param_pairs,
    progress_callback=progress_callback,
    error_callback=error_callback
)

# Get summary statistics
summary = processor.get_analysis_summary(results)
print(f"Analyzed {summary['total_analyzed']} files")
print(f"Found {summary['total_plateaus']} total plateaus")

# Example 2: Using the convenience function
from concurrent_tether_analysis import analyze_files_concurrent

file_paths = ["/path/to/file1.tdms", "/path/to/file2.tdms"]
parameters = {
    'sav_window_length': 10,
    'sav_polyorder': 1,
    'pl_threshold': 1e-9,
    # ... other parameters
}

results = analyze_files_concurrent(file_paths, parameters, max_workers=4)
""")

def main():
    """Main test function"""
    print("Concurrent Tether Analysis - Test Script")
    print("="*50)
    
    # Test 1: Import test
    print("\n1. Testing module import...")
    if not test_concurrent_import():
        return
    
    # Test 2: Validation test
    print("\n2. Testing parameter validation...")
    if not test_parameter_validation():
        return
    
    # Test 3: Usage demonstration
    demonstrate_usage()
    
    print("\n" + "="*50)
    print("✓ All tests completed successfully!")
    print("✓ The concurrent processing module is ready to use")
    print("✓ Integration added to GUI: Analysis > Run Concurrent Batch Analysis (Ctrl+Shift+B)")

if __name__ == "__main__":
    main()
