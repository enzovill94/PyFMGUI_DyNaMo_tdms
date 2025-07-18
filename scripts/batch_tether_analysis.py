#!/usr/bin/env python3
"""
Batch Tether Analysis Script

This script loads a session CSV file and performs batch analysis on all files marked as "good".
It runs the tether analysis on each file and exports the results to CSV files.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add the parent directory to the path to import tether_script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tether_script import process_single_file

def load_session_csv(session_file):
    """Load session CSV and return DataFrame"""
    try:
        df = pd.read_csv(session_file)
        print(f"Loaded session file: {session_file}")
        print(f"Found {len(df)} files in session")
        return df
    except Exception as e:
        print(f"Error loading session file: {e}")
        return None

def filter_good_files(df):
    """Filter DataFrame to only include files marked as 'good'"""
    # Check for different possible status column names
    if 'status' in df.columns:
        good_files = df[df['status'] == 'good'].copy()
    elif 'bool_good_curve' in df.columns:
        good_files = df[df['bool_good_curve'] == 1.0].copy()
    else:
        print("No status column found, using all files")
        return df
    
    print(f"Found {len(good_files)} good files out of {len(df)} total files")
    return good_files

def run_batch_analysis(session_file, output_dir=None):
    """
    Run batch analysis on all good files from a session
    
    Args:
        session_file: Path to the session CSV file
        output_dir: Directory to save results (default: same as session file)
    """
    # Load session
    df = load_session_csv(session_file)
    if df is None:
        return
    
    # Filter good files
    good_files = filter_good_files(df)
    if len(good_files) == 0:
        print("No good files found for analysis")
        return
    
    # Set output directory
    if output_dir is None:
        output_dir = Path(session_file).parent / "batch_analysis_results"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    print(f"Results will be saved to: {output_dir}")
    
    # Process each file
    results = []
    
    for idx, row in good_files.iterrows():
        # Get file path - check different possible column names
        if 'file_path' in row:
            file_path = row['file_path']
        elif 'local_file_path' in row:
            file_path = row['local_file_path']
        else:
            print(f"  ✗ No file path column found in row {idx}")
            continue
            
        print(f"\nProcessing {idx+1}/{len(good_files)}: {Path(file_path).name}")
        
        try:
            # Get parameters for this file
            params = {}
            if 'file_parameters' in row and pd.notna(row['file_parameters']):
                import json
                params = json.loads(row['file_parameters'])
                print("  Using file-specific parameters")
            else:
                # Use global parameters from the row
                param_columns = ['window_size', 'jump_threshold', 'min_plateau_length', 
                               'derivative_threshold', 'max_outliers']
                for col in param_columns:
                    if col in row and pd.notna(row[col]):
                        params[col] = row[col]
                print("  Using global parameters")
            
            # Process the file
            result = process_single_file(file_path, params=params)
            
            if result:
                # Extract key metrics from tether_script.py output format
                plateaus = result.get('plateaus', [])
                df_plat = result.get('df_plat', pd.DataFrame())
                
                file_result = {
                    'file_path': file_path,
                    'file_name': Path(file_path).name,
                    'num_plateaus': len(plateaus),
                    'velocity_metadata': result.get('velocity_metadata'),
                    'velocity_calc_um_s': result.get('velocity_calc_um_s'),
                }
                
                # Extract plateau statistics if available
                if not df_plat.empty:
                    plateau_avgs = df_plat['plateau_avg'].values if 'plateau_avg' in df_plat.columns else []
                    plateau_derivatives = df_plat['mean dN/dt'].values if 'mean dN/dt' in df_plat.columns else []
                    plateau_velocities = df_plat['velocity_calc_um_s'].values if 'velocity_calc_um_s' in df_plat.columns else []
                    
                    if len(plateau_avgs) > 0:
                        file_result.update({
                            'mean_force': np.mean(plateau_avgs),
                            'std_force': np.std(plateau_avgs),
                            'min_force': np.min(plateau_avgs),
                            'max_force': np.max(plateau_avgs),
                        })
                    
                    if len(plateau_derivatives) > 0:
                        file_result.update({
                            'mean dN/dt': np.mean(plateau_derivatives),
                            'std_derivative': np.std(plateau_derivatives),
                            'min_derivative': np.min(plateau_derivatives),
                            'max_derivative': np.max(plateau_derivatives)
                        })
                    
                    if len(plateau_velocities) > 0:
                        file_result.update({
                            'mean_plateau_velocity': np.mean(plateau_velocities),
                            'std_plateau_velocity': np.std(plateau_velocities),
                            'min_plateau_velocity': np.min(plateau_velocities),
                            'max_plateau_velocity': np.max(plateau_velocities)
                        })
                else:
                    # Set default values if no plateau data
                    file_result.update({
                        'mean_force': 0, 'std_force': 0, 'min_force': 0, 'max_force': 0,
                        'mean dN/dt': 0, 'std_derivative': 0, 'min_derivative': 0, 'max_derivative': 0,
                        'mean_plateau_velocity': 0, 'std_plateau_velocity': 0, 'min_plateau_velocity': 0, 'max_plateau_velocity': 0
                    })
                
                results.append(file_result)
                print(f"  ✓ Success: {file_result['num_plateaus']} plateaus found")
                
            else:
                print("  ✗ Failed to process file")
                
        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
    
    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_file = output_dir / "batch_analysis_results.csv"
        results_df.to_csv(results_file, index=False)
        print(f"\nSaved {len(results)} results to: {results_file}")
        
        # ALSO: Save detailed plateau data for velocity vs plateau analysis
        detailed_plateau_data = []
        
        print("Extracting detailed plateau data...")
        for idx, row in good_files.iterrows():
            # Get file path
            if 'file_path' in row:
                file_path = row['file_path']
            elif 'local_file_path' in row:
                file_path = row['local_file_path']
            else:
                continue
                
            try:
                # Get parameters for this file
                params = {}
                if 'file_parameters' in row and pd.notna(row['file_parameters']):
                    import json
                    params = json.loads(row['file_parameters'])
                
                # Get plateau selections for this file
                plateau_selections = []
                if 'plateau_selections' in row and pd.notna(row['plateau_selections']):
                    try:
                        plateau_selections = json.loads(row['plateau_selections'])
                        if not isinstance(plateau_selections, list):
                            plateau_selections = []
                    except (json.JSONDecodeError, TypeError):
                        plateau_selections = []
                
                # Process the file again to get plateau details
                result = process_single_file(file_path, params=params)
                
                if result and result.get('df_plat') is not None and not result['df_plat'].empty:
                    df_plat = result['df_plat']
                    
                    # Add file information to each plateau row
                    for plat_idx, plat_row in df_plat.iterrows():
                        # Determine if this plateau was selected
                        plateau_number = int(plat_row.get('plateaus', plat_idx))
                        plateau_selected = False
                        if plateau_number < len(plateau_selections):
                            plateau_selected = bool(plateau_selections[plateau_number])
                        
                        plateau_detail = {
                            'filename': Path(file_path).name,
                            'file_path': file_path,
                            'file_idx': idx,
                            'plateau_idx': plateau_number,
                            'plateau_selected': plateau_selected,
                            'plateau_avg_idx': int(plat_row.get('plateau_avg_idx')),
                            'plateau_avg': float(plat_row.get('plateau_avg')),
                            'delta_avg': float(plat_row.get('delta_avg')),
                            'delta_time': float(plat_row.get('delta_time')),
                            'mean dN/dt': float(plat_row.get('mean dN/dt')),
                            'plateau_velocity_calc': float(plat_row.get('velocity_calc_um_s')),
                            'velocity_metadata': int(round(result.get('velocity_metadata'))),
                            'start_idx': int(plat_row.get('start')),
                            'end_idx': int(plat_row.get('end')),
                            'slope': float(plat_row.get('plateau_slope')),
                            'tether_lifetime_m': float(plat_row.get('tether_lifetime_m')),
                            'tether_lifetime_s': float(plat_row.get('tether_lifetime_s')),
                        }
                        detailed_plateau_data.append(plateau_detail)
                        
            except Exception as e:
                print(f"  Warning: Could not extract plateau details from {Path(file_path).name}: {e}")
        
        # Save detailed plateau data
        if detailed_plateau_data:
            detailed_df = pd.DataFrame(detailed_plateau_data)
            detailed_file = output_dir / "detailed_plateau_data.csv"
            detailed_df.to_csv(detailed_file, index=False)
            print(f"Saved {len(detailed_plateau_data)} plateau measurements to: {detailed_file}")
            print("📊 This file contains plateau_velocity_calc for velocity vs plateau analysis!")
        
        # Create summary statistics
        summary = {
            'total_files_processed': len(results),
            'total_plateaus': results_df['num_plateaus'].sum(),
            'mean_plateaus_per_file': results_df['num_plateaus'].mean(),
            'overall_mean_force': results_df['mean_force'].mean(),
            'overall_std_force': results_df['mean_force'].std(),
            'overall_mean dN/dt': results_df['mean dN/dt'].mean(),
            'overall_std_derivative': results_df['mean dN/dt'].std(),
            'overall_mean_velocity_metadata': results_df['velocity_metadata'].mean(),
            'overall_mean_velocity_calc': results_df['velocity_calc_um_s'].mean(),
            'overall_mean_plateau_velocity': results_df['mean_plateau_velocity'].mean(),
            'overall_plateau_slope': results_df['plateau_slope'].mean() if 'plateau_slope' in results_df.columns else None,
            'tether lifetime_s': results_df['tether_lifetime_s'].mean() if 'tether_lifetime_s' in results_df.columns else None  
        }
        
        summary_df = pd.DataFrame([summary])
        summary_file = output_dir / "batch_analysis_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"Saved summary to: {summary_file}")
        
        # Print summary
        print("\n=== BATCH ANALYSIS SUMMARY ===")
        print(f"Files processed: {summary['total_files_processed']}")
        print(f"Total plateaus found: {summary['total_plateaus']}")
        print(f"Average plateaus per file: {summary['mean_plateaus_per_file']:.1f}")
        print(f"Overall mean force: {summary['overall_mean_force']:.2e} N")
        print(f"Overall std force: {summary['overall_std_force']:.2e} N")
        print(f"Overall mean derivative: {summary['overall_mean dN/dt']:.4e}")
        print(f"Overall std derivative: {summary['overall_std_derivative']:.4e}")
        print(f"Overall mean metadata velocity: {summary['overall_mean_velocity_metadata']:.2f} μm/s")
        print(f"Overall mean calculated velocity: {summary['overall_mean_velocity_calc']:.2f} μm/s")
        print(f"Overall mean plateau velocity: {summary['overall_mean_plateau_velocity']:.2f} μm/s")
        print(f"Overall plateau slope: {summary['overall_plateau_slope']:.4f}" if summary['overall_plateau_slope'] is not None else "Plateau slope data not available")
        
    else:
        print("\nNo files were successfully processed")

def main():
    """Main function for command line usage"""
        # Option 1: Fixed path
    session_file = "/Users/evillz/Data/article/2025_07_01_THP1_phd/sessions/latest/test/tether_session_20250716_192549.csv"

    # # Option 2: Interactive prompt
    # session_file = input("Enter path to session CSV file: ")

    # # Option 3: File dialog (requires PyQt5)
    # from PyQt5.QtWidgets import QFileDialog, QApplication
    # app = QApplication([])
    # session_file, _ = QFileDialog.getOpenFileName(None, "Select Session File", "", "CSV Files (*.csv)")
    
    run_batch_analysis(session_file)

if __name__ == "__main__":
    main()
