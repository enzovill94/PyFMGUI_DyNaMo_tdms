#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File utility functions
"""

import os
from datetime import datetime
from typing import Optional


def validate_path(path: str) -> bool:
    """
    Validate if file or folder path exists
    
    Parameters:
    -----------
    path : str
        Path to validate
        
    Returns:
    --------
    bool: True if path exists
    """
    return os.path.exists(path)


def create_output_filename(base_path: str, suffix: str = '', extension: str = 'tiff') -> str:
    """
    Create timestamped output filename
    
    Parameters:
    -----------
    base_path : str
        Base path or folder
    suffix : str
        Suffix to add to filename
    extension : str
        File extension (without dot)
        
    Returns:
    --------
    str: Full output path with timestamp
    """
    if os.path.isdir(base_path):
        folder_name = os.path.basename(base_path)
        output_dir = base_path
    else:
        folder_name = os.path.basename(os.path.dirname(base_path))
        output_dir = os.path.dirname(base_path)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{folder_name}_{suffix}_{timestamp}.{extension}" if suffix else f"{folder_name}_{timestamp}.{extension}"
    
    return os.path.join(output_dir, filename)


def ensure_directory(path: str) -> str:
    """
    Ensure directory exists, create if needed
    
    Parameters:
    -----------
    path : str
        Directory path
        
    Returns:
    --------
    str: The directory path
    """
    os.makedirs(path, exist_ok=True)
    return path


def get_file_timestamp(filepath: str) -> Optional[datetime]:
    """
    Get file modification timestamp
    
    Parameters:
    -----------
    filepath : str
        Path to file
        
    Returns:
    --------
    datetime or None: File modification time
    """
    if os.path.exists(filepath):
        return datetime.fromtimestamp(os.path.getmtime(filepath))
    return None


def get_folder_size(folder_path: str) -> int:
    """
    Get total size of folder in bytes
    
    Parameters:
    -----------
    folder_path : str
        Path to folder
        
    Returns:
    --------
    int: Total size in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Parameters:
    -----------
    size_bytes : int
        Size in bytes
        
    Returns:
    --------
    str: Formatted size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
