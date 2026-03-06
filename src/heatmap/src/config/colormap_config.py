#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Colormap Configuration for Heatmap Visualization
"""

import matplotlib.pyplot as plt

# Available colormaps organized by category
COLORMAP_OPTIONS = {
    'Sequential': [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
        'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
        'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn'
    ],
    'Diverging': [
        'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
        'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic'
    ],
    'Qualitative': [
        'Pastel1', 'Pastel2', 'Paired', 'Accent',
        'Dark2', 'Set1', 'Set2', 'Set3', 'tab10', 'tab20'
    ],
    'Miscellaneous': [
        'flag', 'prism', 'ocean', 'gist_earth', 'terrain',
        'gist_stern', 'gnuplot', 'gnuplot2', 'CMRmap',
        'cubehelix', 'brg', 'gist_rainbow', 'rainbow', 'jet',
        'turbo', 'nipy_spectral', 'gist_ncar'
    ],
    'Topographic': [
        'hot', 'afmhot', 'gist_heat', 'copper'
    ]
}

# Flatten all colormaps into a single list
ALL_COLORMAPS = []
for category, cmaps in COLORMAP_OPTIONS.items():
    ALL_COLORMAPS.extend(cmaps)

# Default colormap
DEFAULT_COLORMAP = 'YlOrBr'

# Recommended colormaps for height maps
HEIGHT_MAP_COLORMAPS = [
    'YlOrBr',      # Yellow-Orange-Brown (good for topography)
    'terrain',     # Terrain colors
    'gist_earth',  # Earth tones
    'viridis',     # Perceptually uniform
    'plasma',      # Perceptually uniform
    'inferno',     # Perceptually uniform
    'coolwarm',    # Diverging (good for showing deviations)
    'RdYlBu_r',    # Red-Yellow-Blue reversed
]

# Custom colormap presets for specific analysis types
PRESET_COLORMAPS = {
    'height_analysis': 'YlOrBr',
    'force_analysis': 'viridis',
    'stiffness_analysis': 'plasma',
    'adhesion_analysis': 'coolwarm',
    'topography': 'terrain',
}


def get_colormap_list(category=None):
    """
    Get list of colormaps by category
    
    Parameters:
    -----------
    category : str, optional
        Category name. If None, returns all colormaps
        
    Returns:
    --------
    List of colormap names
    """
    if category is None:
        return ALL_COLORMAPS
    
    return COLORMAP_OPTIONS.get(category, [])


def get_colormap_categories():
    """Get list of colormap categories"""
    return list(COLORMAP_OPTIONS.keys())


def is_colormap_valid(cmap_name):
    """Check if colormap name is valid"""
    try:
        plt.get_cmap(cmap_name)
        return True
    except ValueError:
        return False


def get_recommended_colormap(analysis_type='height_analysis'):
    """
    Get recommended colormap for analysis type
    
    Parameters:
    -----------
    analysis_type : str
        Type of analysis
        
    Returns:
    --------
    Colormap name
    """
    return PRESET_COLORMAPS.get(analysis_type, DEFAULT_COLORMAP)


# Colormap metadata for UI display
COLORMAP_METADATA = {
    'YlOrBr': {
        'name': 'Yellow-Orange-Brown',
        'description': 'Good for topography and height maps',
        'category': 'Sequential'
    },
    'viridis': {
        'name': 'Viridis',
        'description': 'Perceptually uniform, colorblind-friendly',
        'category': 'Sequential'
    },
    'plasma': {
        'name': 'Plasma',
        'description': 'Perceptually uniform, high contrast',
        'category': 'Sequential'
    },
    'coolwarm': {
        'name': 'Cool-Warm',
        'description': 'Diverging, good for deviations from mean',
        'category': 'Diverging'
    },
    'terrain': {
        'name': 'Terrain',
        'description': 'Natural terrain colors',
        'category': 'Topographic'
    },
}


def get_colormap_info(cmap_name):
    """Get metadata for colormap"""
    return COLORMAP_METADATA.get(cmap_name, {
        'name': cmap_name,
        'description': 'No description available',
        'category': 'Unknown'
    })
