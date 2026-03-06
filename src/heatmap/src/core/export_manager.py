#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Manager Module
Handles exporting data to various formats (TIFF, CSV, etc.)
"""

import os
import pandas as pd
import numpy as np
from typing import Optional, Dict
import pyfmreader.ps_nex.loadpsnexMaps as maps


class ExportManager:
    """Manage data exports in various formats"""
    
    def __init__(self):
        self.export_history = []
        
    def export_tiff(self, map_data: np.ndarray, 
                    output_path: str,
                    px_um_x: float = 0.14,
                    px_um_y: float = 0.14) -> bool:
        """
        Export map as TIFF file
        
        Parameters:
        -----------
        map_data : np.ndarray
            2D array with map data
        output_path : str
            Path for output TIFF file
        px_um_x : float
            Pixel size in X (micrometers)
        px_um_y : float
            Pixel size in Y (micrometers)
            
        Returns:
        --------
        bool: Success status
        """
        try:
            # Use the maps module save function
            maps.save_map_as_tiff(map_data, px_um_x=px_um_x, px_um_y=px_um_y, out_path=output_path)
            
            self.export_history.append({
                'type': 'tiff',
                'path': output_path,
                'shape': map_data.shape
            })
            
            return True
            
        except Exception as e:
            print(f"Error exporting TIFF: {str(e)}")
            return False
    
    def export_dataframe_csv(self, df: pd.DataFrame, 
                            output_path: str,
                            include_index: bool = False) -> bool:
        """
        Export DataFrame to CSV
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame to export
        output_path : str
            Path for output CSV file
        include_index : bool
            Whether to include index in CSV
            
        Returns:
        --------
        bool: Success status
        """
        try:
            df.to_csv(output_path, index=include_index)
            
            self.export_history.append({
                'type': 'csv',
                'path': output_path,
                'rows': len(df),
                'columns': len(df.columns)
            })
            
            return True
            
        except Exception as e:
            print(f"Error exporting CSV: {str(e)}")
            return False
    
    def export_roi_data(self, roi_df: pd.DataFrame,
                        output_path: str,
                        statistics: Optional[Dict] = None) -> bool:
        """
        Export ROI data with optional statistics
        
        Parameters:
        -----------
        roi_df : pd.DataFrame
            ROI data
        output_path : str
            Output CSV path
        statistics : Dict, optional
            Statistics to append as comment
            
        Returns:
        --------
        bool: Success status
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Export main data
            roi_df.to_csv(output_path, index=False)
            
            # If statistics provided, save separately
            if statistics:
                stats_path = output_path.replace('.csv', '_statistics.csv')
                stats_df = pd.DataFrame([statistics])
                stats_df.to_csv(stats_path, index=False)
            
            self.export_history.append({
                'type': 'roi_csv',
                'path': output_path,
                'roi_count': len(roi_df)
            })
            
            return True
            
        except Exception as e:
            print(f"Error exporting ROI data: {str(e)}")
            return False
    
    def export_map_with_metadata(self, map_data: np.ndarray,
                                 output_base_path: str,
                                 params: Dict,
                                 map_type: str = 'tdms') -> Dict:
        """
        Export map as both TIFF and CSV with metadata
        
        Parameters:
        -----------
        map_data : np.ndarray
            Map data
        output_base_path : str
            Base path for outputs
        params : Dict
            Map parameters
        map_type : str
            'tdms' or 'csv'
            
        Returns:
        --------
        Dictionary with export results
        """
        results = {'success': True, 'exports': []}
        
        try:
            # Create output paths
            tiff_path = f"{output_base_path}_{map_type}.tiff"
            csv_path = f"{output_base_path}_{map_type}_data.csv"
            
            # Export TIFF
            px_x = params.get('map_x_step', 0.14)
            px_y = params.get('map_y_step', 0.14)
            
            if self.export_tiff(map_data, tiff_path, px_um_x=px_x, px_um_y=px_y):
                results['exports'].append({'type': 'tiff', 'path': tiff_path})
            
            # Export as CSV
            map_df = pd.DataFrame(map_data)
            if self.export_dataframe_csv(map_df, csv_path):
                results['exports'].append({'type': 'csv', 'path': csv_path})
            
            # Export parameters as JSON
            import json
            params_path = f"{output_base_path}_{map_type}_params.json"
            with open(params_path, 'w') as f:
                json.dump(params, f, indent=2)
            results['exports'].append({'type': 'params', 'path': params_path})
            
            return results
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            return results
    
    def batch_export_maps(self, map_folders: list,
                          output_dir: str,
                          export_formats: list = ['tiff', 'csv']) -> Dict:
        """
        Batch export multiple map folders
        
        Parameters:
        -----------
        map_folders : list
            List of map folder paths
        output_dir : str
            Output directory
        export_formats : list
            List of export formats ('tiff', 'csv')
            
        Returns:
        --------
        Dictionary with batch export results
        """
        results = {
            'total': len(map_folders),
            'success_count': 0,
            'failed_count': 0,
            'exports': [],
            'errors': []
        }
        
        os.makedirs(output_dir, exist_ok=True)
        
        for map_folder in map_folders:
            try:
                # Process map
                map_data_dict = maps.process_map_and_create_heatmap(map_folder)
                
                if map_data_dict is None:
                    results['errors'].append(f"Failed to process {map_folder}")
                    results['failed_count'] += 1
                    continue
                
                map_tdms, map_csv, x_axis, y_axis, df_map, params = map_data_dict
                
                # Create output base name
                folder_name = os.path.basename(map_folder)
                output_base = os.path.join(output_dir, folder_name)
                
                # Export based on requested formats
                if 'tiff' in export_formats:
                    if map_tdms is not None:
                        tiff_path = f"{output_base}_tdms.tiff"
                        self.export_tiff(map_tdms, tiff_path, 
                                       px_um_x=params.get('map_x_step', 0.14),
                                       px_um_y=params.get('map_y_step', 0.14))
                        results['exports'].append(tiff_path)
                    
                    if map_csv is not None:
                        tiff_path = f"{output_base}_csv.tiff"
                        self.export_tiff(map_csv, tiff_path,
                                       px_um_x=params.get('map_x_step', 0.14),
                                       px_um_y=params.get('map_y_step', 0.14))
                        results['exports'].append(tiff_path)
                
                results['success_count'] += 1
                
            except Exception as e:
                results['errors'].append(f"Error with {map_folder}: {str(e)}")
                results['failed_count'] += 1
        
        return results
