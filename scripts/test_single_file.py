#!/usr/bin/env python3
"""
Test script to debug plateau detection on a single file
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tether_script import process_single_file

def test_single_file():
    # Load the session file to get parameters and file paths
    session_file = "/Users/evillz/Data/article/2025_07_01_THP1_phd/sessions/velocity_normalized_thp1_cell1/tether_session_20250805_225739_new_1.csv"
    
    print(f"Loading session: {session_file}")
    df = pd.read_csv(session_file)
    
    # Filter to good files only
    good_files = df[df['bool_good_curve'] == 1.0].copy()
    print(f"Found {len(good_files)} good files")
    
    if len(good_files) == 0:
        print("No good files found!")
        return
    
    # Take the first good file
    row = good_files.iloc[0]
    file_path = row['local_file_path']
    file_name = Path(file_path).name
    
    print(f"\nTesting file: {file_name}")
    print(f"Path: {file_path}")
    
    # Get parameters
    params = {}
    if 'file_parameters' in row and pd.notna(row['file_parameters']):
        params = json.loads(row['file_parameters'])
        print(f"Parameters loaded: {params}")
    else:
        print("No parameters found, using defaults")
    
    # Test if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist: {file_path}")
        return
    
    print(f"\nProcessing file...")
    try:
        result = process_single_file(file_path, params=params)
        
        if result:
            plateaus = result.get('plateaus', [])
            df_plat = result.get('df_plat', pd.DataFrame())
            
            print(f"\n=== RESULTS ===")
            print(f"Number of plateaus found: {len(plateaus)}")
            print(f"Plateaus: {plateaus}")
            
            if not df_plat.empty:
                print(f"DataFrame shape: {df_plat.shape}")
                print(f"DataFrame columns: {list(df_plat.columns)}")
                print(f"First few rows:")
                print(df_plat.head())
            else:
                print("DataFrame is empty")
                
        else:
            print("ERROR: process_single_file returned None")
            
    except Exception as e:
        print(f"ERROR during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file()
