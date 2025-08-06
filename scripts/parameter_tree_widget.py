from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from pyqtgraph.parametertree import Parameter, ParameterTree
import os
import ast

class ParameterTreeWidget(QWidget):
    parametersChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Analysis Parameters")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Status label for per-file parameters
        self.param_status_label = QLabel("Global parameters")
        self.param_status_label.setFont(QFont("Arial", 9))
        self.param_status_label.setStyleSheet("QLabel { color: #666; background-color: #f0f0f0; padding: 3px; border-radius: 3px; }")
        layout.addWidget(self.param_status_label)
        
        # Parameter tree
        self.param_tree = ParameterTree()
        layout.addWidget(self.param_tree)
        
        # Set column widths to make value column smaller
        header = self.param_tree.header()
        header.resizeSection(0, 180)  # Parameter name column width
        header.resizeSection(1, 50)   # Value column width (smaller)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset Defaults")
        self.reset_button.clicked.connect(self.resetToDefaults)
        self.reset_button.setToolTip("Reset to global default parameters")
        button_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("Apply & Analyze")
        self.apply_button.clicked.connect(self.emitParameters)
        self.apply_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)

        # Define parameters grouped by category (removed z_sensor_delay and bool_correct_overshoot)
        self.param_def = [
            {
                'name': 'Filtering Parameters',
                'type': 'group',
                'children': [
                    {'name': 'Savitzky Window Length', 'type': 'int', 'value': 10, 'limits': (2, 40), 'step': 1, 'key': 'sav_window_length'},
                    {'name': 'Savitzky Poly Order', 'type': 'int', 'value': 1, 'limits': (1, 12), 'step': 1, 'key': 'sav_polyorder'},
                ]
            },
            {
                'name': 'Plateau Detection',
                'type': 'group',
                'children': [
                    {'name': 'Plateau Threshold (nN)', 'type': 'float', 'value': 1.0, 'limits': (1e-3, 1e6), 'step': 0.001, 'key': 'pl_threshold'},
                    {'name': 'Min Plateau Width (μm)', 'type': 'float', 'value': 1.0, 'limits': (1e-4, 60), 'step': 0.001, 'key': 'pl_min_width_um'},
                    {'name': 'Max Plateaus', 'type': 'int', 'value': 7, 'limits': (1, 15), 'step': 1, 'key': 'last_num_plateaus'},
                    {'name': 'Last Plateau Avg (%)', 'type': 'int', 'value': 15, 'limits': (1, 100), 'step': 1, 'key': 'last_plateau_avg_percentage'},
                ]
            },
            {
                'name': 'Baseline Correction',
                'type': 'group',
                'children': [
                    {'name': 'Max Tilt Offset (%)', 'type': 'int', 'value': 100, 'limits': (50, 100), 'step': 5, 'key': 'max_offset'},
                    {'name': 'Min Tilt Offset (%)', 'type': 'int', 'value': 70, 'limits': (30, 90), 'step': 5, 'key': 'min_offset'},
                ]
            },
            {
                'name': 'Denoise Filter',
                'type': 'group',
                'children': [
                    {'name': 'Enable Denoising', 'type': 'bool', 'value': False, 'key': 'enable_denoising'},
                    {'name': 'Butterworth Min λ (µm)', 'type': 'float', 'value': 0.25, 'limits': (0.01, 100), 'step': 0.01, 'key': 'butterworth_min_wavelength'},
                    {'name': 'Butterworth Max λ (µm)', 'type': 'float', 'value': 10.0, 'limits': (0.01, 100), 'step': 0.1, 'key': 'butterworth_max_wavelength'},
                    {'name': 'Butterworth Order', 'type': 'int', 'value': 5, 'limits': (1, 10), 'step': 1, 'key': 'butterworth_order'},
                    {'name': 'Band Suppress Min λ (µm)', 'type': 'float', 'value': 0.167, 'limits': (0.01, 100), 'step': 0.001, 'key': 'band_suppress_min_wavelength'},
                    {'name': 'Band Suppress Max λ (µm)', 'type': 'float', 'value': 1.0, 'limits': (0.01, 100), 'step': 0.01, 'key': 'band_suppress_max_wavelength'},
                    {'name': 'Remove Start (%)', 'type': 'int', 'value': 10, 'limits': (0, 50), 'step': 1, 'key': 'denoise_remove_percent'},
                    {'name': 'Remove End (%)', 'type': 'int', 'value': 10, 'limits': (0, 50), 'step': 1, 'key': 'denoise_remove_end_percent'},
                    {'name': 'Use Interpolation', 'type': 'bool', 'value': True, 'key': 'denoise_interp'},
                ]
            },

        ]
        
        # Create parameter map for easy lookup
        self.param_map = {}
        self._build_param_map(self.param_def)
        
        # Create parameter tree structure
        children = []
        for group in self.param_def:
            group_copy = group.copy()
            if 'children' in group_copy:
                group_copy['children'] = [{k: v for k, v in child.items() if k != 'key'} for child in group_copy['children']]
            children.append(group_copy)
        
        self.param_obj = Parameter.create(name='params', type='group', children=children)
        self.param_tree.setParameters(self.param_obj, showTop=False)
        self.param_obj.sigTreeStateChanged.connect(self.emitParameters)

    def _build_param_map(self, param_list):
        """Build parameter map recursively"""
        for param in param_list:
            if 'key' in param:
                self.param_map[param['key']] = param
            if 'children' in param:
                self._build_param_map(param['children'])

    def emitParameters(self, *args, **kwargs):
        params = self.getCurrentParameters()
        self.parametersChanged.emit(params)

    def getCurrentParameters(self):
        """Get current parameters with automatic wavelength to wavenumber conversion"""
        
        def wavelength_to_wavenumber(wavelength_um):
            """Convert wavelength in micrometers to wavenumber in µm⁻¹"""
            return 1.0 / wavelength_um
        
        values = {}
        for key, param_def in self.param_map.items():
            # Navigate through the parameter tree structure
            param_path = self._find_param_path(param_def['name'])
            if param_path:
                val = self._get_param_value(param_path)
                if key == 'pl_threshold':
                    values[key] = val * 1e-9  # convert nN to N
                elif key == 'pl_min_width_um':
                    values[key] = val * 1e-6  # convert um to m
                else:
                    values[key] = val
        
        # Convert individual wavelength parameters to array format for backward compatibility
        if 'butterworth_min_wavelength' in values and 'butterworth_max_wavelength' in values:
            wl_min = values['butterworth_min_wavelength']
            wl_max = values['butterworth_max_wavelength']
            # Convert wavelength ranges to wavenumber ranges
            wn_low = wavelength_to_wavenumber(wl_max)   # Higher wavelength → lower wavenumber (W0)
            wn_high = wavelength_to_wavenumber(wl_min)  # Lower wavelength → higher wavenumber (W1)
            values['denoise_w0'] = wn_low  # Lower wavenumber
            values['denoise_w1'] = wn_high  # Higher wavenumber
            
            # Also create the array format for compatibility
            wavelength_ranges = [(wl_min, wl_max)]
            values['butterworth_wavelengths'] = str(wavelength_ranges)
        
        if 'band_suppress_min_wavelength' in values and 'band_suppress_max_wavelength' in values:
            wl_min = values['band_suppress_min_wavelength']
            wl_max = values['band_suppress_max_wavelength']
            # Convert wavelength ranges to wavenumber ranges for denoise_ranges
            wn_low = wavelength_to_wavenumber(wl_max)   # Higher wavelength → lower wavenumber
            wn_high = wavelength_to_wavenumber(wl_min)  # Lower wavelength → higher wavenumber
            wavenumber_ranges = [(wn_low, wn_high)]
            values['denoise_ranges'] = str(wavenumber_ranges)
            
            # Also create the array format for compatibility
            wavelength_ranges = [(wl_min, wl_max)]
            values['band_suppression_wavelengths'] = str(wavelength_ranges)
        
        return values

    def _find_param_path(self, param_name):
        """Find the path to a parameter in the tree"""
        for group in self.param_def:
            if 'children' in group:
                for child in group['children']:
                    if child['name'] == param_name:
                        return [group['name'], param_name]
        return None

    def _get_param_value(self, path):
        """Get parameter value using path"""
        param = self.param_obj
        for step in path:
            param = param.child(step)
        return param.value()

    def _set_param_value(self, path, value):
        """Set parameter value using path"""
        param = self.param_obj
        for step in path:
            param = param.child(step)
        param.setValue(value)

    def setParameterValue(self, key, value):
        """Set a single parameter value by key"""
        try:
            if key in self.param_map:
                param_name = self.param_map[key]['name']
                param_path = self._find_param_path(param_name)
                if param_path:
                    val = value
                    if key == 'pl_threshold':
                        val = value / 1e-9  # convert N to nN for display
                    elif key == 'pl_min_width_um':
                        val = value / 1e-6  # convert m to um for display
                    self._set_param_value(param_path, val)
                    # Emit parameter change signal
                    self.parametersChanged.emit(self.getCurrentParameters())
                else:
                    print(f"Warning: Could not find parameter path for {param_name}")
            else:
                print(f"Warning: Parameter key '{key}' not found in param_map")
        except Exception as e:
            print(f"Error setting parameter value for {key}: {e}")

    def setParameters(self, params):
        """Set parameters with automatic wavenumber to wavelength conversion"""
        
        def wavenumber_to_wavelength(wavenumber_um_inv):
            """Convert wavenumber in µm⁻¹ to wavelength in micrometers"""
            return 1.0 / wavenumber_um_inv
        
        # Handle individual wavelength parameters first
        for key, value in params.items():
            if key in self.param_map:
                param_name = self.param_map[key]['name']
                param_path = self._find_param_path(param_name)
                if param_path:
                    val = value
                    if key == 'pl_threshold':
                        val = value / 1e-9  # convert N to nN
                    elif key == 'pl_min_width_um':
                        val = value / 1e-6  # convert m to um
                    self._set_param_value(param_path, val)
        
        # Handle backward compatibility: convert old array format to individual parameters
        if 'butterworth_wavelengths' in params and 'butterworth_min_wavelength' not in params:
            try:
                wavelength_ranges = ast.literal_eval(params['butterworth_wavelengths']) if isinstance(params['butterworth_wavelengths'], str) else params['butterworth_wavelengths']
                if wavelength_ranges and len(wavelength_ranges[0]) == 2:
                    wl_min, wl_max = wavelength_ranges[0]
                    # Set individual parameters
                    min_path = self._find_param_path('Butterworth Min λ (µm)')
                    max_path = self._find_param_path('Butterworth Max λ (µm)')
                    if min_path:
                        self._set_param_value(min_path, wl_min)
                    if max_path:
                        self._set_param_value(max_path, wl_max)
            except (ValueError, SyntaxError):
                pass  # Skip if parsing fails
        
        if 'band_suppression_wavelengths' in params and 'band_suppress_min_wavelength' not in params:
            try:
                wavelength_ranges = ast.literal_eval(params['band_suppression_wavelengths']) if isinstance(params['band_suppression_wavelengths'], str) else params['band_suppression_wavelengths']
                if wavelength_ranges and len(wavelength_ranges[0]) == 2:
                    wl_min, wl_max = wavelength_ranges[0]
                    # Set individual parameters
                    min_path = self._find_param_path('Band Suppress Min λ (µm)')
                    max_path = self._find_param_path('Band Suppress Max λ (µm)')
                    if min_path:
                        self._set_param_value(min_path, wl_min)
                    if max_path:
                        self._set_param_value(max_path, wl_max)
            except (ValueError, SyntaxError):
                pass  # Skip if parsing fails
        
        # Handle conversion from wavenumbers (w0, w1) to individual wavelength parameters
        if 'denoise_w0' in params and 'denoise_w1' in params and 'butterworth_min_wavelength' not in params:
            w0 = params['denoise_w0']  # smaller wavenumber -> larger wavelength
            w1 = params['denoise_w1']  # larger wavenumber -> smaller wavelength
            
            # Convert back to wavelengths
            wl_max = wavenumber_to_wavelength(w0)  # W0 -> max wavelength
            wl_min = wavenumber_to_wavelength(w1)  # W1 -> min wavelength
            
            # Set individual parameters
            min_path = self._find_param_path('Butterworth Min λ (µm)')
            max_path = self._find_param_path('Butterworth Max λ (µm)')
            if min_path:
                self._set_param_value(min_path, wl_min)
            if max_path:
                self._set_param_value(max_path, wl_max)
        
        if 'denoise_ranges' in params and 'band_suppress_min_wavelength' not in params:
            try:
                wavenumber_ranges = ast.literal_eval(params['denoise_ranges']) if isinstance(params['denoise_ranges'], str) else params['denoise_ranges']
                if wavenumber_ranges and len(wavenumber_ranges[0]) == 2:
                    wn_low, wn_high = wavenumber_ranges[0]
                    # Reverse the conversion: smaller wavenumber -> larger wavelength
                    wl_max = wavenumber_to_wavelength(wn_low)  # Lower wavenumber → higher wavelength
                    wl_min = wavenumber_to_wavelength(wn_high)   # Higher wavenumber → lower wavelength
                    
                    # Set individual parameters
                    min_path = self._find_param_path('Band Suppress Min λ (µm)')
                    max_path = self._find_param_path('Band Suppress Max λ (µm)')
                    if min_path:
                        self._set_param_value(min_path, wl_min)
                    if max_path:
                        self._set_param_value(max_path, wl_max)
            except (ValueError, SyntaxError):
                pass  # Skip if parsing fails

    def update_parameter_status(self, filename=None, is_file_specific=False):
        """Update the parameter status label"""
        if is_file_specific and filename:
            self.param_status_label.setText(f"File-specific: {os.path.basename(filename)}")
            self.param_status_label.setStyleSheet("QLabel { color: #2196F3; background-color: #E3F2FD; padding: 3px; border-radius: 3px; font-weight: bold; }")
        else:
            self.param_status_label.setText("Global parameters")
            self.param_status_label.setStyleSheet("QLabel { color: #666; background-color: #f0f0f0; padding: 3px; border-radius: 3px; }")

    def resetToDefaults(self):
        """Reset all parameters to default values"""
        for key, param_def in self.param_map.items():
            param_path = self._find_param_path(param_def['name'])
            if param_path:
                self._set_param_value(param_path, param_def['value'])
        self.emitParameters()
