#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Processing Example

Demonstrates batch processing of multiple PSNEX map folders
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import DataLoader, ExportManager, MapProcessor
from config import DEFAULT_PARAMS

def batch_process_maps(root_directory, output_directory):
    """
    Batch process all PSNEX map folders in a directory
    
    Parameters:
    -----------
    root_directory : str
        Root directory containing PSNEX map folders
    output_directory : str
        Directory for output files
    """
    print("=" * 70)
    print("PSNEX Map Batch Processing")
    print("=" * 70)
    
    # Initialize components
    loader = DataLoader()
    exporter = ExportManager()
    processor = MapProcessor()
    
    # Find all PSNEX folders
    print(f"\n1. Searching for PSNEX folders in: {root_directory}")
    folders = loader.find_psnex_folders(root_directory)
    print(f"   Found {len(folders)} folders")
    
    if len(folders) == 0:
        print("   No PSNEX folders found!")
        return
    
    # Validate folders
    print("\n2. Validating folders...")
    validations = loader.batch_validate_folders(folders)
    
    valid_folders = [f for f, v in validations.items() if v['valid']]
    invalid_folders = [f for f, v in validations.items() if not v['valid']]
    
    print(f"   Valid folders: {len(valid_folders)}")
    print(f"   Invalid folders: {len(invalid_folders)}")
    
    if invalid_folders:
        print("\n   Invalid folders:")
        for folder in invalid_folders[:5]:  # Show first 5
            print(f"      - {os.path.basename(folder)}")
    
    # Process valid folders
    print(f"\n3. Processing {len(valid_folders)} folders...")
    
    results = {
        'success': [],
        'failed': [],
        'exports': []
    }
    
    for i, folder in enumerate(valid_folders, 1):
        folder_name = os.path.basename(folder)
        print(f"\n   [{i}/{len(valid_folders)}] Processing: {folder_name}")
        
        try:
            # Process map
            result = processor.process_map(
                folder,
                correct_indices=True,
                zmin=None,
                zmax=None
            )
            
            if not result['success']:
                print(f"      ✗ Failed: {result['error']}")
                results['failed'].append({
                    'folder': folder,
                    'error': result['error']
                })
                continue
            
            # Create output paths
            output_base = os.path.join(output_directory, folder_name)
            
            # Export TIFF files
            exports_count = 0
            
            if result['map_tdms'] is not None:
                tiff_path_tdms = f"{output_base}_tdms.tiff"
                if exporter.export_tiff(
                    result['map_tdms'],
                    tiff_path_tdms,
                    px_um_x=result['params'].get('map_x_step', 0.14),
                    px_um_y=result['params'].get('map_y_step', 0.14)
                ):
                    results['exports'].append(tiff_path_tdms)
                    exports_count += 1
            
            if result['map_csv'] is not None:
                tiff_path_csv = f"{output_base}_csv.tiff"
                if exporter.export_tiff(
                    result['map_csv'],
                    tiff_path_csv,
                    px_um_x=result['params'].get('map_x_step', 0.14),
                    px_um_y=result['params'].get('map_y_step', 0.14)
                ):
                    results['exports'].append(tiff_path_csv)
                    exports_count += 1
            
            # Export dataframe as CSV
            if result['df_map'] is not None:
                import pandas as pd
                csv_path = f"{output_base}_data.csv"
                
                # Convert dict to DataFrame if needed
                if isinstance(result['df_map'], dict):
                    df_export = pd.DataFrame(result['df_map'])
                else:
                    df_export = result['df_map']
                
                if exporter.export_dataframe_csv(df_export, csv_path):
                    results['exports'].append(csv_path)
                    exports_count += 1
            
            results['success'].append(folder)
            print(f"      ✓ Success! Exported {exports_count} files")
            
        except Exception as e:
            print(f"      ✗ Exception: {str(e)}")
            results['failed'].append({
                'folder': folder,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 70)
    print(f"\nTotal folders found: {len(folders)}")
    print(f"Valid folders: {len(valid_folders)}")
    print(f"Successfully processed: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Total exports: {len(results['exports'])}")
    
    if results['failed']:
        print("\nFailed folders:")
        for item in results['failed']:
            print(f"   - {os.path.basename(item['folder'])}: {item['error']}")
    
    print(f"\nOutput directory: {output_directory}")
    print("=" * 70)
    
    return results

def main():
    # Configuration
    root_dir = '/Users/evillz/Data/'  # Change to your data directory
    output_dir = os.path.join(os.path.dirname(__file__), 'batch_output')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Run batch processing
    results = batch_process_maps(root_dir, output_dir)
    
    return results

if __name__ == '__main__':
    main()
