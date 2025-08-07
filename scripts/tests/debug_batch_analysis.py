#!/usr/bin/env python3
"""
Debug script to test batch analysis on a single file
"""

import os
import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Add the parent directory to the path to import tether_script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tether_script import process_single_file

def debug_single_file():
    # Load the session file
    session_file = "/Users/evillz/Data/article/2025_07_01_THP1_phd/sessions/velocity_normalized_thp1_cell1/tether_session_20250805_225739_new_1.csv"
    
    try:
        df = pd.read_csv(session_file)
        print(f"Loaded session file with {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Find first good file
        good_files = df[df['bool_good_curve'] == 1.0]
        print(f"Found {len(good_files)} good files")
        
        if len(good_files) == 0:
            print("No good files found!")
            return
            
        # Get first good file
        first_good = good_files.iloc[0]
        file_path = first_good['local_file_path']
        print(f"\nTesting file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Parse parameters
        if pd.notna(first_good['file_parameters']):
            params = json.loads(first_good['file_parameters'])
            print(f"Parameters: {params}")
        else:
            params = {}
            print("No parameters found, using defaults")
            
        # Test the analysis
        print("\n--- Running tether analysis ---")
        result = process_single_file(file_path, params=params)
        
        if result:
            plateaus = result.get('plateaus', [])
            df_plat = result.get('df_plat', pd.DataFrame())
            
            print(f"\n--- RESULTS ---")
            print(f"Plateaus found: {len(plateaus)}")
            print(f"Plateau data shape: {df_plat.shape if not df_plat.empty else 'Empty'}")
            
            if not df_plat.empty:
                print(f"Plateau DataFrame columns: {list(df_plat.columns)}")
                print(f"First few plateau values:")
                print(df_plat.head())
            
            print(f"Other result keys: {list(result.keys())}")
            
        else:
            print("❌ process_single_file returned None or False")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_single_file()
