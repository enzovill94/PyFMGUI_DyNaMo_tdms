#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Loader Module
Handles loading of PSNEX map data from various sources
"""

import os
import glob
from typing import List, Tuple, Dict, Optional
import pandas as pd
import pyfmreader.ps_nex.loadpsnexMaps as maps
import pyfmreader.ps_nex.parseTDMS as tdms


class DataLoader:
    """Load and validate PSNEX map data"""
    
    def __init__(self):
        self.loaded_folders = []
        self.current_folder = None
        
    @staticmethod
    def find_psnex_folders(root_dir: str) -> List[str]:
        """
        Find all PSNEX map folders in directory
        
        Parameters:
        -----------
        root_dir : str
            Root directory to search
            
        Returns:
        --------
        List of PSNEX map folder paths
        """
        pattern = os.path.join(root_dir, 'psnex_map_*')
        folders = [f for f in glob.glob(pattern) if os.path.isdir(f) 
                  and not (f.endswith('.zip') or f.endswith('.csv'))]
        
        # Also use the maps module function if available
        try:
            folders_from_maps = maps.find_psnex_map_folders(root_dir)
            # Combine and remove duplicates
            all_folders = list(set(folders + folders_from_maps))
            return sorted(all_folders)
        except AttributeError:
            return sorted(folders)
    
    @staticmethod
    def find_csv_files(folder_path: str) -> List[str]:
        """
        Find CSV map files in folder
        
        Parameters:
        -----------
        folder_path : str
            Path to PSNEX map folder
            
        Returns:
        --------
        List of CSV file paths
        """
        return maps.find_csv_files(folder_path)
    
    @staticmethod
    def find_tdms_files(folder_path: str) -> Tuple[str, List[str]]:
        """
        Find TDMS files in folder
        
        Parameters:
        -----------
        folder_path : str
            Path to PSNEX map folder
            
        Returns:
        --------
        Tuple of (folder_path, list of tdms files)
        """
        return tdms.grab_tdms(folder_path)
    
    @staticmethod
    def get_map_parameters(folder_path: str) -> Dict:
        """
        Get map parameters from folder
        
        Parameters:
        -----------
        folder_path : str
            Path to PSNEX map folder
            
        Returns:
        --------
        Dictionary of map parameters
        """
        return maps.get_map_parameters(folder_path)
    
    @staticmethod
    def load_csv_map(csv_path: str, params: Dict) -> Tuple[pd.DataFrame, List, List]:
        """
        Load 2D map from CSV file
        
        Parameters:
        -----------
        csv_path : str
            Path to CSV file
        params : Dict
            Map parameters
            
        Returns:
        --------
        Tuple of (map_dataframe, x_axis, y_axis)
        """
        return maps.load_2d_map_file_csv(csv_path, params)
    
    @staticmethod
    def load_tdms_map(folder_path: str) -> Tuple[Dict, int, int, Dict]:
        """
        Load map from TDMS files
        
        Parameters:
        -----------
        folder_path : str
            Path to PSNEX map folder
            
        Returns:
        --------
        Tuple of (df_map dict, map_x_pix, map_y_pix, params)
        """
        return maps.load_map_file_square_tdms(folder_path)
    
    def validate_folder(self, folder_path: str) -> Dict:
        """
        Validate PSNEX map folder
        
        Parameters:
        -----------
        folder_path : str
            Path to PSNEX map folder
            
        Returns:
        --------
        Dictionary with validation results
        """
        validation = {
            'valid': False,
            'has_csv': False,
            'has_tdms': False,
            'has_params': False,
            'csv_count': 0,
            'tdms_count': 0,
            'errors': []
        }
        
        if not os.path.exists(folder_path):
            validation['errors'].append(f"Folder does not exist: {folder_path}")
            return validation
        
        if not os.path.isdir(folder_path):
            validation['errors'].append(f"Path is not a directory: {folder_path}")
            return validation
        
        # Check for CSV files
        try:
            csv_files = self.find_csv_files(folder_path)
            validation['csv_count'] = len(csv_files)
            validation['has_csv'] = len(csv_files) > 0
        except Exception as e:
            validation['errors'].append(f"Error finding CSV files: {str(e)}")
        
        # Check for TDMS files
        try:
            _, tdms_files = self.find_tdms_files(folder_path)
            validation['tdms_count'] = len(tdms_files)
            validation['has_tdms'] = len(tdms_files) > 0
        except Exception as e:
            validation['errors'].append(f"Error finding TDMS files: {str(e)}")
        
        # Check for parameters
        try:
            params = self.get_map_parameters(folder_path)
            validation['has_params'] = params is not None and len(params) > 0
        except Exception as e:
            validation['errors'].append(f"Error loading parameters: {str(e)}")
        
        # Overall validation
        validation['valid'] = (validation['has_csv'] or validation['has_tdms']) and validation['has_params']
        
        return validation
    
    def batch_validate_folders(self, folder_list: List[str]) -> Dict[str, Dict]:
        """
        Validate multiple PSNEX map folders
        
        Parameters:
        -----------
        folder_list : List[str]
            List of folder paths to validate
            
        Returns:
        --------
        Dictionary mapping folder paths to validation results
        """
        results = {}
        for folder in folder_list:
            results[folder] = self.validate_folder(folder)
        return results
