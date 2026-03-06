#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sample Map Analysis Script

Demonstrates basic usage of the PSNEX Map Analysis core modules
without the GUI.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import MapProcessor, DataLoader, ExportManager, SessionManager, IntegrityChecker
from config import DEFAULT_PARAMS

def main():
    # Example PSNEX map folder
    map_folder = '/Users/evillz/Data/psnex_map___2025.03.12_18.23.11.20'
    
    print("=" * 60)
    print("PSNEX Map Analysis Example")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing components...")
    processor = MapProcessor()
    loader = DataLoader()
    exporter = ExportManager()
    checker = IntegrityChecker()
    
    # Validate folder
    print(f"\n2. Validating folder: {map_folder}")
    validation = loader.validate_folder(map_folder)
    print(f"   Valid: {validation['valid']}")
    print(f"   Has CSV: {validation['has_csv']} ({validation['csv_count']} files)")
    print(f"   Has TDMS: {validation['has_tdms']} ({validation['tdms_count']} files)")
    
    if not validation['valid']:
        print("   Errors:", validation['errors'])
        return
    
    # Process map
    print("\n3. Processing map...")
    params = DEFAULT_PARAMS.copy()
    params['zmax'] = 35  # Set custom z-range
    
    result = processor.process_map(map_folder, **params)
    
    if not result['success']:
        print(f"   Error: {result['error']}")
        return
    
    print("   Success!")
    print(f"   TDMS map shape: {result['map_tdms'].shape if result['map_tdms'] is not None else 'N/A'}")
    print(f"   CSV map shape: {result['map_csv'].shape if result['map_csv'] is not None else 'N/A'}")
    
    # Check data integrity
    print("\n4. Checking data integrity...")
    if result['map_tdms'] is not None:
        integrity_result = checker.comprehensive_check(
            result['df_map'],
            result['map_tdms'],
            result['params']['map_x_pix'],
            result['params']['map_y_pix']
        )
        
        print(f"   Overall valid: {integrity_result['overall_valid']}")
        print(f"   NaN values: {integrity_result['checks']['nan_values']['nan_percentage']:.2f}%")
        print(f"   Duplicates: {integrity_result['checks']['duplicates']['has_duplicates']}")
    
    # Extract ROI
    print("\n5. Extracting ROI (center 10x10 pixels)...")
    center_x = result['params']['map_x_pix'] // 2
    center_y = result['params']['map_y_pix'] // 2
    
    roi_pixels = []
    for x in range(center_x - 5, center_x + 5):
        for y in range(center_y - 5, center_y + 5):
            roi_pixels.append((x, y))
    
    roi_df = processor.extract_roi_data(roi_pixels, map_type='tdms')
    print(f"   Extracted {len(roi_df)} ROI pixels")
    
    # Get statistics
    stats = processor.get_roi_statistics()
    print(f"\n6. ROI Statistics:")
    print(f"   Mean: {stats['mean']:.3f} µm")
    print(f"   Std Dev: {stats['std']:.3f} µm")
    print(f"   Min: {stats['min']:.3f} µm")
    print(f"   Max: {stats['max']:.3f} µm")
    print(f"   Median: {stats['median']:.3f} µm")
    
    # Export data
    print("\n7. Exporting data...")
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Export TIFF
    if result['map_tdms'] is not None:
        tiff_path = os.path.join(output_dir, 'example_map_tdms.tiff')
        exporter.export_tiff(
            result['map_tdms'],
            tiff_path,
            px_um_x=result['params']['map_x_step'],
            px_um_y=result['params']['map_y_step']
        )
        print(f"   TIFF exported: {tiff_path}")
    
    # Export ROI CSV
    roi_csv_path = os.path.join(output_dir, 'example_roi_data.csv')
    exporter.export_roi_data(roi_df, roi_csv_path, statistics=stats)
    print(f"   ROI data exported: {roi_csv_path}")
    
    # Save session
    print("\n8. Saving session...")
    session_mgr = SessionManager()
    session_mgr.create_session(map_folder, params)
    session_path = os.path.join(output_dir, 'example_session.json')
    session_mgr.save_session(session_path, roi_df=roi_df, statistics=stats)
    print(f"   Session saved: {session_path}")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
