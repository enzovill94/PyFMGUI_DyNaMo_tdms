#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map Viewer Widget - Combines heatmap canvas with controls
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QDoubleSpinBox, QCheckBox, QGroupBox)
from PyQt5.QtCore import pyqtSignal
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from widgets.heatmap_canvas import HeatmapCanvas
from widgets.colormap_selector import ColormapSelectorWithLabel


class MapViewerWidget(QWidget):
    """Widget for displaying and controlling map visualization"""
    
    # Signals
    roi_selected = pyqtSignal(list)  # List of (x, y) pixel coordinates
    parameters_changed = pyqtSignal(dict)  # Updated visualization parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_map_data = None
        self.setupUI()
        
    def setupUI(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # Heatmap canvas
        self.canvas = HeatmapCanvas()
        layout.addWidget(self.canvas, stretch=1)
        
        # Connect signals
        self.canvas.roi_selected.connect(self.roi_selected.emit)
        
    def create_control_panel(self):
        """Create control panel with colormap and z-range controls"""
        panel = QGroupBox("Visualization Controls")
        layout = QHBoxLayout(panel)
        
        # Colormap selector
        self.colormap_selector = ColormapSelectorWithLabel(
            label_text="Colormap:",
            recommended_only=True
        )
        layout.addWidget(self.colormap_selector)
        
        # Z-range controls
        z_range_widget = QWidget()
        z_layout = QHBoxLayout(z_range_widget)
        z_layout.setContentsMargins(0, 0, 0, 0)
        
        # Z min
        z_layout.addWidget(QLabel("Z Min:"))
        self.z_min_spin = QDoubleSpinBox()
        self.z_min_spin.setRange(-1000, 1000)
        self.z_min_spin.setDecimals(3)
        self.z_min_spin.setSingleStep(0.1)
        self.z_min_spin.setSpecialValueText("Auto")
        self.z_min_spin.setValue(self.z_min_spin.minimum())
        z_layout.addWidget(self.z_min_spin)
        
        # Z max
        z_layout.addWidget(QLabel("Z Max:"))
        self.z_max_spin = QDoubleSpinBox()
        self.z_max_spin.setRange(-1000, 1000)
        self.z_max_spin.setDecimals(3)
        self.z_max_spin.setSingleStep(0.1)
        self.z_max_spin.setSpecialValueText("Auto")
        self.z_max_spin.setValue(self.z_max_spin.minimum())
        z_layout.addWidget(self.z_max_spin)
        
        # Auto z-range checkbox
        self.auto_z_check = QCheckBox("Auto Z-Range")
        self.auto_z_check.setChecked(True)
        z_layout.addWidget(self.auto_z_check)
        
        layout.addWidget(z_range_widget)
        
        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.on_apply_settings)
        layout.addWidget(self.apply_btn)
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_display)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch()
        
        # Connect signals
        self.colormap_selector.colormap_changed.connect(self.on_colormap_changed)
        self.auto_z_check.toggled.connect(self.on_auto_z_toggled)
        
        return panel
    
    def display_map(self, map_data, x_axis=None, y_axis=None, params=None):
        """
        Display map data
        
        Parameters:
        -----------
        map_data : np.ndarray
            2D array with map data
        x_axis : np.ndarray, optional
            X-axis values
        y_axis : np.ndarray, optional
            Y-axis values
        params : dict, optional
            Parameters for visualization
        """
        self.current_map_data = {
            'map_data': map_data,
            'x_axis': x_axis,
            'y_axis': y_axis,
            'params': params if params is not None else {}
        }
        
        # Update z-range if auto
        if self.auto_z_check.isChecked():
            import numpy as np
            z_min = np.nanmin(map_data)
            z_max = np.nanmax(map_data)
            self.z_min_spin.setValue(z_min)
            self.z_max_spin.setValue(z_max)
        
        self.canvas.plot_heatmap(map_data, x_axis, y_axis, params)
    
    def on_colormap_changed(self, cmap_name):
        """Handle colormap change"""
        self.canvas.set_colormap(cmap_name)
        self.emit_parameters_changed()
    
    def on_auto_z_toggled(self, checked):
        """Handle auto z-range toggle"""
        self.z_min_spin.setEnabled(not checked)
        self.z_max_spin.setEnabled(not checked)
        
        if checked and self.current_map_data is not None:
            import numpy as np
            map_data = self.current_map_data['map_data']
            z_min = np.nanmin(map_data)
            z_max = np.nanmax(map_data)
            self.z_min_spin.setValue(z_min)
            self.z_max_spin.setValue(z_max)
            self.on_apply_settings()
    
    def on_apply_settings(self):
        """Apply visualization settings"""
        if self.current_map_data is None:
            return
        
        # Get z-range
        if self.auto_z_check.isChecked():
            zmin = None
            zmax = None
        else:
            zmin = self.z_min_spin.value()
            zmax = self.z_max_spin.value()
            
            # Validate range
            if zmin >= zmax:
                return
        
        # Update canvas
        self.canvas.set_z_range(zmin, zmax)
        self.emit_parameters_changed()
    
    def emit_parameters_changed(self):
        """Emit parameters changed signal"""
        params = {
            'colormap': self.colormap_selector.get_current_colormap(),
            'zmin': None if self.auto_z_check.isChecked() else self.z_min_spin.value(),
            'zmax': None if self.auto_z_check.isChecked() else self.z_max_spin.value(),
            'auto_z_range': self.auto_z_check.isChecked()
        }
        self.parameters_changed.emit(params)
    
    def clear_display(self):
        """Clear the display and reset controls"""
        self.canvas.clear_plot()
        self.current_map_data = None
        
        # Reset controls to default state
        self.auto_z_check.setChecked(True)
        self.z_min_spin.setValue(self.z_min_spin.minimum())
        self.z_max_spin.setValue(self.z_max_spin.minimum())
        self.colormap_selector.reset_to_default()
    
    def enable_roi_selection(self, enabled=True):
        """Enable or disable ROI selection"""
        self.canvas.enable_roi_selection(enabled)
