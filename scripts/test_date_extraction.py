#!/usr/bin/env python3
"""
Test script for date extraction from filenames
"""

import re

def extract_date_from_filename(filename):
    """Extract date taken from filename timestamp if available"""
    try:
        # Look for pattern like "2025.07.01_16.49.19.87" in filename
        
        # Pattern: YYYY.MM.DD_HH.MM.SS.MS
        pattern = r'(\d{4})\.(\d{2})\.(\d{2})_(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})'
        match = re.search(pattern, filename)
        
        if match:
            year, month, day, hour, minute, second, millisecond = match.groups()
            
            # Format as readable datetime string
            date_str = f"{year}-{month}-{day} {hour}:{minute}:{second}.{millisecond}"
            return date_str
        else:
            return None  # No timestamp found
            
    except Exception as e:
        print(f"Warning: Could not extract date from filename {filename}: {e}")
        return None

# Test cases
test_filenames = [
    "fcurve_thp1_cell1_ret_300ums__2025.07.01_16.49.19.87.tdms",
    "fcurve_thp1_cell2_ret_600ums__2024.12.15_09.30.45.12.tdms",
    "regular_file_without_timestamp.tdms",
    "another_file_2023.01.01_12.00.00.00_with_timestamp.tdms",
    "file_with_partial_2025.07.01_incomplete.tdms"
]

print("Testing date extraction from filenames:")
print("=" * 50)

for filename in test_filenames:
    result = extract_date_from_filename(filename)
    print(f"File: {filename}")
    print(f"Date: {result if result else 'No timestamp found'}")
    print("-" * 50)
