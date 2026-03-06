#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data utility functions
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict


def normalize_data(data: np.ndarray, 
                   method: str = 'minmax',
                   vmin: Optional[float] = None,
                   vmax: Optional[float] = None) -> np.ndarray:
    """
    Normalize data array
    
    Parameters:
    -----------
    data : np.ndarray
        Input data
    method : str
        'minmax' or 'zscore'
    vmin, vmax : float, optional
        Custom min/max values
        
    Returns:
    --------
    np.ndarray: Normalized data
    """
    if method == 'minmax':
        data_min = vmin if vmin is not None else np.nanmin(data)
        data_max = vmax if vmax is not None else np.nanmax(data)
        
        if data_max == data_min:
            return np.zeros_like(data)
        
        return (data - data_min) / (data_max - data_min)
    
    elif method == 'zscore':
        mean = np.nanmean(data)
        std = np.nanstd(data)
        
        if std == 0:
            return np.zeros_like(data)
        
        return (data - mean) / std
    
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def calculate_statistics(data: np.ndarray) -> Dict:
    """
    Calculate comprehensive statistics for data
    
    Parameters:
    -----------
    data : np.ndarray
        Input data array
        
    Returns:
    --------
    Dict: Dictionary of statistics
    """
    # Flatten and remove NaN
    flat_data = data.flatten()
    valid_data = flat_data[~np.isnan(flat_data)]
    
    if len(valid_data) == 0:
        return {
            'count': 0,
            'mean': np.nan,
            'std': np.nan,
            'min': np.nan,
            'max': np.nan,
            'median': np.nan,
            'q25': np.nan,
            'q75': np.nan,
            'range': np.nan
        }
    
    stats = {
        'count': len(valid_data),
        'mean': np.mean(valid_data),
        'std': np.std(valid_data),
        'min': np.min(valid_data),
        'max': np.max(valid_data),
        'median': np.median(valid_data),
        'q25': np.percentile(valid_data, 25),
        'q75': np.percentile(valid_data, 75),
        'range': np.max(valid_data) - np.min(valid_data)
    }
    
    return stats


def filter_outliers(data: np.ndarray, 
                    method: str = 'iqr',
                    threshold: float = 1.5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Filter outliers from data
    
    Parameters:
    -----------
    data : np.ndarray
        Input data
    method : str
        'iqr' or 'zscore'
    threshold : float
        Threshold for outlier detection
        
    Returns:
    --------
    Tuple[np.ndarray, np.ndarray]: (filtered_data, outlier_mask)
    """
    if method == 'iqr':
        q1 = np.nanpercentile(data, 25)
        q3 = np.nanpercentile(data, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        outlier_mask = (data < lower_bound) | (data > upper_bound)
        
    elif method == 'zscore':
        mean = np.nanmean(data)
        std = np.nanstd(data)
        
        z_scores = np.abs((data - mean) / std)
        outlier_mask = z_scores > threshold
        
    else:
        raise ValueError(f"Unknown outlier detection method: {method}")
    
    filtered_data = data.copy()
    filtered_data[outlier_mask] = np.nan
    
    return filtered_data, outlier_mask


def create_histogram_bins(data: np.ndarray, n_bins: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create histogram bins for data
    
    Parameters:
    -----------
    data : np.ndarray
        Input data
    n_bins : int
        Number of bins
        
    Returns:
    --------
    Tuple[np.ndarray, np.ndarray]: (hist, bin_edges)
    """
    valid_data = data[~np.isnan(data.flatten())]
    
    if len(valid_data) == 0:
        return np.array([]), np.array([])
    
    hist, bin_edges = np.histogram(valid_data, bins=n_bins)
    return hist, bin_edges


def dataframe_to_2d_array(df: pd.DataFrame, 
                          x_col: str = 'x_index',
                          y_col: str = 'y_index',
                          value_col: str = 'z_value') -> np.ndarray:
    """
    Convert dataframe with x, y, value columns to 2D array
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe
    x_col, y_col : str
        Column names for x and y indices
    value_col : str
        Column name for values
        
    Returns:
    --------
    np.ndarray: 2D array
    """
    if x_col not in df.columns or y_col not in df.columns or value_col not in df.columns:
        raise ValueError(f"Required columns not found in dataframe")
    
    x_max = int(df[x_col].max()) + 1
    y_max = int(df[y_col].max()) + 1
    
    array_2d = np.full((y_max, x_max), np.nan)
    
    for _, row in df.iterrows():
        x_idx = int(row[x_col])
        y_idx = int(row[y_col])
        array_2d[y_idx, x_idx] = row[value_col]
    
    return array_2d
