from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from pyqtgraph.parametertree import Parameter, ParameterTree
import os

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
            }
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

    def setParameters(self, params):
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
