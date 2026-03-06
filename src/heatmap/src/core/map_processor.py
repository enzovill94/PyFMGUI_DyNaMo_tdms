#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map Processor Module
Handles processing of PSNEX map data including heatmap generation and ROI analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
import pyfmreader.ps_nex.loadpsnexMaps as maps


class MapProcessor:
    """Process PSNEX map data and create heatmaps"""
    
    def __init__(self):
        self.current_map_data = None
        self.current_params = None
        self.current_dataframe = None
        self.roi_data = None
        
    def process_map(self, map_path: str, 
                    correct_indices: bool = True,
                    zmin: Optional[float] = None,
                    zmax: Optional[float] = None,
                    value_key: str = 'z_height_um_zero') -> Dict:
        """
        Process a PSNEX map folder and create heatmap data
        
        Parameters:
        -----------
        map_path : str
            Path to PSNEX map folder
        correct_indices : bool
            Whether to correct map indices
        zmin, zmax : float, optional
            Z-axis range for colormap
        value_key : str
            Key for z-values in dataframe
            
        Returns:
        --------
        dict containing:
            - map_tdms: 2D array from TDMS files
            - map_csv: 2D array from CSV files
            - x_axis: X-axis values
            - y_axis: Y-axis values
            - df_map: DataFrame with all map data
            - params: Map parameters dictionary
        """
        try:
            # Use the existing process_map_and_create_heatmap function
            map_tdms, map_csv, x_axis, y_axis, df_map, params = \
                maps.process_map_and_create_heatmap(
                    map_path, 
                    correct_indices=correct_indices,
                    zmin=zmin,
                    zmax=zmax
                )
            
            # Store current data
            self.current_map_data = {
                'map_tdms': map_tdms,
                'map_csv': map_csv,
                'x_axis': x_axis,
                'y_axis': y_axis,
            }
            self.current_dataframe = df_map
            self.current_params = params
            
            return {
                'map_tdms': map_tdms,
                'map_csv': map_csv,
                'x_axis': x_axis,
                'y_axis': y_axis,
                'df_map': df_map,
                'params': params,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'map_tdms': None,
                'map_csv': None,
                'x_axis': None,
                'y_axis': None,
                'df_map': None,
                'params': None
            }
    
    def extract_roi_data(self, roi_pixels: List[Tuple[int, int]], 
                         map_type: str = 'tdms') -> pd.DataFrame:
        """
        Extract data for selected ROI pixels
        
        Parameters:
        -----------
        roi_pixels : List[Tuple[int, int]]
            List of (x, y) pixel coordinates
        map_type : str
            'tdms' or 'csv' to specify which map to use
            
        Returns:
        --------
        DataFrame with ROI pixel data and statistics
        """
        if self.current_dataframe is None:
            raise ValueError("No map data loaded")
        
        if not roi_pixels or len(roi_pixels) == 0:
            raise ValueError("No ROI pixels provided")
        
        # Select the appropriate map
        map_data = self.current_map_data.get(f'map_{map_type}')
        if map_data is None:
            raise ValueError(f"No {map_type} map data available")
        
        # Get axes (may be None)
        x_axis = self.current_map_data.get('x_axis')
        y_axis = self.current_map_data.get('y_axis')
        
        roi_data = []
        for x_idx, y_idx in roi_pixels:
            # Check bounds
            if 0 <= y_idx < map_data.shape[0] and 0 <= x_idx < map_data.shape[1]:
                value = map_data[y_idx, x_idx]
                
                # Get position values safely
                x_pos = None
                y_pos = None
                if x_axis is not None and x_idx < len(x_axis):
                    x_pos = x_axis[x_idx]
                if y_axis is not None and y_idx < len(y_axis):
                    y_pos = y_axis[y_idx]
                
                roi_data.append({
                    'x_pixel': x_idx,
                    'y_pixel': y_idx,
                    'x_position_um': x_pos,
                    'y_position_um': y_pos,
                    'z_value': value
                })
        
        if not roi_data:
            raise ValueError("No valid pixels in ROI (all out of bounds)")
        
        roi_df = pd.DataFrame(roi_data)
        self.roi_data = roi_df
        return roi_df
    
    def get_roi_statistics(self) -> Dict:
        """
        Calculate statistics for current ROI data
        
        Returns:
        --------
        Dictionary with statistical measures
        """
        if self.roi_data is None or len(self.roi_data) == 0:
            return {}
        
        z_values = self.roi_data['z_value'].dropna()
        
        stats = {
            'count': len(z_values),
            'mean': z_values.mean(),
            'std': z_values.std(),
            'min': z_values.min(),
            'max': z_values.max(),
            'median': z_values.median(),
            'q25': z_values.quantile(0.25),
            'q75': z_values.quantile(0.75)
        }
        
        return stats
    
    def create_2d_array_from_dataframe(self, df_map: Dict, 
                                        value_key: str = 'z_height_um_zero',
                                        params: Optional[Dict] = None) -> np.ndarray:
        """
        Create 2D array from dataframe dictionary
        
        Parameters:
        -----------
        df_map : Dict
            Dictionary with map data from load_map_file_square_tdms
        value_key : str
            Key for z-values
        params : Dict, optional
            Map parameters
            
        Returns:
        --------
        2D numpy array
        """
        if not isinstance(df_map, dict):
            raise ValueError("df_map must be a dictionary")
        
        # Get z-values
        if value_key in df_map:
            z_values = df_map[value_key]
        elif 'z_height_um_zero' in df_map:
            z_values = df_map['z_height_um_zero']
        else:
            z_values = df_map['z_height_um']
        
        # Get dimensions
        map_x_pix = params['map_x_pix'] if params and 'map_x_pix' in params else int(np.max(df_map['x_index'])) + 1
        map_y_pix = params['map_y_pix'] if params and 'map_y_pix' in params else int(np.max(df_map['y_index'])) + 1
        
        # Create empty 2D array
        map_2d = np.zeros((map_y_pix, map_x_pix), dtype=np.float64)
        
        # Fill array
        x_indices = df_map['x_index']
        y_indices = df_map['y_index']
        
        for i in range(len(z_values)):
            x_idx = int(x_indices[i])
            y_idx = int(y_indices[i])
            if 0 <= x_idx < map_x_pix and 0 <= y_idx < map_y_pix:
                map_2d[y_idx, x_idx] = z_values[i]
        
        # Roll last column to first (data correction)
        map_2d = np.roll(map_2d, shift=1, axis=1)
        
        return map_2d
