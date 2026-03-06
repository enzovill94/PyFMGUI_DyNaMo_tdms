#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrity Checker Module
Validates map data integrity and detects issues
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
import pyfmreader.ps_nex.loadpsnexMaps as maps


class IntegrityChecker:
    """Check integrity of PSNEX map data"""
    
    def __init__(self):
        self.last_check_results = None
        
    def check_map_indices(self, df_map: Dict, 
                          map_x_pix: int, 
                          map_y_pix: int) -> Tuple[bool, Dict]:
        """
        Check map indices for integrity
        
        Parameters:
        -----------
        df_map : Dict
            Dictionary with map data
        map_x_pix : int
            Expected X dimension
        map_y_pix : int
            Expected Y dimension
            
        Returns:
        --------
        Tuple of (has_errors, error_details)
        """
        try:
            # Use the existing integrity check function
            has_errors, error_details = maps.check_map_indice_integrity(df_map, map_x_pix, map_y_pix)
            
            self.last_check_results = {
                'has_errors': has_errors,
                'details': error_details,
                'dimensions': {'x': map_x_pix, 'y': map_y_pix}
            }
            
            return has_errors, error_details
            
        except Exception as e:
            return True, {'error': str(e)}
    
    def check_nan_values(self, data: np.ndarray) -> Dict:
        """
        Check for NaN values in map data
        
        Parameters:
        -----------
        data : np.ndarray
            Map data array
            
        Returns:
        --------
        Dictionary with NaN analysis
        """
        nan_mask = np.isnan(data)
        nan_count = np.sum(nan_mask)
        total_pixels = data.size
        
        nan_info = {
            'has_nans': nan_count > 0,
            'nan_count': int(nan_count),
            'total_pixels': int(total_pixels),
            'nan_percentage': (nan_count / total_pixels * 100) if total_pixels > 0 else 0,
            'nan_positions': []
        }
        
        if nan_count > 0 and nan_count < 100:  # Only get positions if reasonable number
            nan_positions = np.argwhere(nan_mask)
            nan_info['nan_positions'] = [(int(pos[0]), int(pos[1])) for pos in nan_positions]
        
        return nan_info
    
    def check_dataframe_columns(self, df_map: Dict, 
                                 required_keys: List[str] = None) -> Dict:
        """
        Check if dataframe has required columns
        
        Parameters:
        -----------
        df_map : Dict
            Map data dictionary
        required_keys : List[str], optional
            List of required keys
            
        Returns:
        --------
        Dictionary with column check results
        """
        if required_keys is None:
            required_keys = ['x_index', 'y_index', 'z_height_um']
        
        results = {
            'valid': True,
            'missing_keys': [],
            'present_keys': [],
            'has_nan_values': {}
        }
        
        if not isinstance(df_map, dict):
            results['valid'] = False
            results['error'] = "Input is not a dictionary"
            return results
        
        # Check for required keys
        for key in required_keys:
            if key in df_map:
                results['present_keys'].append(key)
                
                # Check for NaN values in this column
                if isinstance(df_map[key], (list, np.ndarray)):
                    has_nan = np.isnan(df_map[key]).any()
                    results['has_nan_values'][key] = bool(has_nan)
            else:
                results['missing_keys'].append(key)
                results['valid'] = False
        
        return results
    
    def check_duplicate_indices(self, df_map: Dict) -> Dict:
        """
        Check for duplicate pixel indices
        
        Parameters:
        -----------
        df_map : Dict
            Map data dictionary
            
        Returns:
        --------
        Dictionary with duplicate analysis
        """
        results = {
            'has_duplicates': False,
            'duplicate_count': 0,
            'duplicate_positions': []
        }
        
        if 'x_index' not in df_map or 'y_index' not in df_map:
            results['error'] = "Missing x_index or y_index"
            return results
        
        # Create coordinate pairs
        coords = list(zip(df_map['x_index'], df_map['y_index']))
        
        # Find duplicates
        seen = set()
        duplicates = []
        for i, coord in enumerate(coords):
            if coord in seen:
                duplicates.append((i, coord))
            seen.add(coord)
        
        results['has_duplicates'] = len(duplicates) > 0
        results['duplicate_count'] = len(duplicates)
        
        if len(duplicates) < 50:  # Only store if reasonable number
            results['duplicate_positions'] = duplicates
        
        return results
    
    def comprehensive_check(self, df_map: Dict, 
                           map_data: np.ndarray,
                           map_x_pix: int,
                           map_y_pix: int) -> Dict:
        """
        Perform comprehensive integrity check
        
        Parameters:
        -----------
        df_map : Dict
            Map data dictionary
        map_data : np.ndarray
            2D map array
        map_x_pix : int
            Expected X dimension
        map_y_pix : int
            Expected Y dimension
            
        Returns:
        --------
        Comprehensive check results dictionary
        """
        results = {
            'overall_valid': True,
            'checks': {}
        }
        
        # Check indices
        has_index_errors, index_details = self.check_map_indices(df_map, map_x_pix, map_y_pix)
        results['checks']['indices'] = {
            'has_errors': has_index_errors,
            'details': index_details
        }
        if has_index_errors:
            results['overall_valid'] = False
        
        # Check NaN values
        nan_info = self.check_nan_values(map_data)
        results['checks']['nan_values'] = nan_info
        if nan_info['has_nans'] and nan_info['nan_percentage'] > 10:
            results['overall_valid'] = False
        
        # Check dataframe columns
        column_check = self.check_dataframe_columns(df_map)
        results['checks']['columns'] = column_check
        if not column_check['valid']:
            results['overall_valid'] = False
        
        # Check duplicates
        duplicate_check = self.check_duplicate_indices(df_map)
        results['checks']['duplicates'] = duplicate_check
        if duplicate_check['has_duplicates']:
            results['overall_valid'] = False
        
        # Dimension check
        expected_size = map_x_pix * map_y_pix
        actual_size = len(df_map.get('x_index', []))
        results['checks']['dimensions'] = {
            'expected_pixels': expected_size,
            'actual_pixels': actual_size,
            'match': expected_size == actual_size
        }
        
        self.last_check_results = results
        return results
    
    def get_validation_summary(self) -> str:
        """
        Get human-readable validation summary
        
        Returns:
        --------
        String summary of last validation
        """
        if self.last_check_results is None:
            return "No validation performed yet"
        
        if 'overall_valid' in self.last_check_results:
            results = self.last_check_results
            summary = []
            
            if results['overall_valid']:
                summary.append("✓ Map data passed all integrity checks")
            else:
                summary.append("✗ Map data has integrity issues:")
            
            for check_name, check_data in results.get('checks', {}).items():
                if check_name == 'indices' and check_data.get('has_errors'):
                    summary.append(f"  - Index errors detected")
                elif check_name == 'nan_values' and check_data.get('has_nans'):
                    pct = check_data.get('nan_percentage', 0)
                    summary.append(f"  - NaN values: {pct:.1f}%")
                elif check_name == 'duplicates' and check_data.get('has_duplicates'):
                    count = check_data.get('duplicate_count', 0)
                    summary.append(f"  - Duplicate indices: {count}")
                elif check_name == 'columns' and not check_data.get('valid'):
                    missing = check_data.get('missing_keys', [])
                    summary.append(f"  - Missing columns: {', '.join(missing)}")
            
            return "\n".join(summary)
        
        return "Unknown validation state"
