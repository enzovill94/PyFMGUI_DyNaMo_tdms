#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Default Parameters for Map Analysis
"""

# Default map processing parameters
DEFAULT_PARAMS = {
    # Map dimensions
    'map_x_pix': 40,
    'map_y_pix': 40,
    'map_x_step': 0.14,
    'map_y_step': 0.14,
    
    # Sensitivity values
    'z_sens_um': 6.0,
    'x_sens_um': 5.685,
    'y_sens_um': 3.960,
    
    # Processing options
    'correct_indices': True,
    'flip_axis': True,
    'value_key': 'z_height_um_zero',
    
    # Visualization
    'colormap': 'YlOrBr',
    'zmin': None,
    'zmax': None,
    'show_annotations': False,
    'annotation_format': '.2f',
    
    # ROI selection
    'roi_mode': 'rectangle',  # rectangle, polygon, freehand
    'roi_color': '#FF0000',
    'roi_alpha': 0.3,
    
    # Export settings
    'export_tiff': True,
    'export_csv': True,
    'export_roi_data': True,
}

# Parameter definitions for ParameterTreeWidget
PARAMETER_DEFINITIONS = [
    {
        'name': 'Map Properties',
        'type': 'group',
        'children': [
            {'name': 'X Pixels', 'type': 'int', 'value': 40, 'key': 'map_x_pix'},
            {'name': 'Y Pixels', 'type': 'int', 'value': 40, 'key': 'map_y_pix'},
            {'name': 'X Step (V)', 'type': 'float', 'value': 0.14, 'key': 'map_x_step', 'step': 0.01},
            {'name': 'Y Step (V)', 'type': 'float', 'value': 0.14, 'key': 'map_y_step', 'step': 0.01},
        ]
    },
    {
        'name': 'Sensitivity',
        'type': 'group',
        'children': [
            {'name': 'Z (µm/V)', 'type': 'float', 'value': 6.0, 'key': 'z_sens_um', 'step': 0.1},
            {'name': 'X (µm/V)', 'type': 'float', 'value': 5.685, 'key': 'x_sens_um', 'step': 0.001},
            {'name': 'Y (µm/V)', 'type': 'float', 'value': 3.960, 'key': 'y_sens_um', 'step': 0.001},
        ]
    },
    {
        'name': 'Processing',
        'type': 'group',
        'children': [
            {'name': 'Correct Indices', 'type': 'bool', 'value': True, 'key': 'correct_indices'},
            {'name': 'Flip Axis', 'type': 'bool', 'value': True, 'key': 'flip_axis'},
            {'name': 'Value Key', 'type': 'list', 'value': 'z_height_um_zero', 
             'values': ['z_height_um_zero', 'z_height_um', 'z_height'], 'key': 'value_key'},
        ]
    },
    {
        'name': 'Visualization',
        'type': 'group',
        'children': [
            {'name': 'Colormap', 'type': 'list', 'value': 'YlOrBr',
             'values': ['YlOrBr', 'viridis', 'plasma', 'inferno', 'magma', 'cividis', 
                       'hot', 'coolwarm', 'RdYlBu_r', 'seismic'], 'key': 'colormap'},
            {'name': 'Z Min (µm)', 'type': 'float', 'value': None, 'key': 'zmin', 'step': 0.1, 'optional': True},
            {'name': 'Z Max (µm)', 'type': 'float', 'value': None, 'key': 'zmax', 'step': 0.1, 'optional': True},
            {'name': 'Show Annotations', 'type': 'bool', 'value': False, 'key': 'show_annotations'},
            {'name': 'Annotation Format', 'type': 'str', 'value': '.2f', 'key': 'annotation_format'},
        ]
    },
    {
        'name': 'ROI Selection',
        'type': 'group',
        'children': [
            {'name': 'ROI Mode', 'type': 'list', 'value': 'rectangle',
             'values': ['rectangle', 'polygon', 'freehand', 'ellipse'], 'key': 'roi_mode'},
            {'name': 'ROI Color', 'type': 'color', 'value': '#FF0000', 'key': 'roi_color'},
            {'name': 'ROI Alpha', 'type': 'float', 'value': 0.3, 'key': 'roi_alpha', 
             'limits': (0.0, 1.0), 'step': 0.1},
        ]
    },
    {
        'name': 'Export Options',
        'type': 'group',
        'children': [
            {'name': 'Export TIFF', 'type': 'bool', 'value': True, 'key': 'export_tiff'},
            {'name': 'Export CSV', 'type': 'bool', 'value': True, 'key': 'export_csv'},
            {'name': 'Export ROI Data', 'type': 'bool', 'value': True, 'key': 'export_roi_data'},
        ]
    },
]

# Helper function to get parameter value by key
def get_param_by_key(key, definitions=None):
    """Get parameter definition by key"""
    if definitions is None:
        definitions = PARAMETER_DEFINITIONS
    
    for group in definitions:
        if 'children' in group:
            for param in group['children']:
                if param.get('key') == key:
                    return param
    return None

# Helper function to update parameter value
def update_param_value(key, value, definitions=None):
    """Update parameter value by key"""
    if definitions is None:
        definitions = PARAMETER_DEFINITIONS
    
    for group in definitions:
        if 'children' in group:
            for param in group['children']:
                if param.get('key') == key:
                    param['value'] = value
                    return True
    return False
