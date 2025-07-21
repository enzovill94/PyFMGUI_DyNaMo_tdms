#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tether Analysis GUI
Based on hack_gui_working.py with integrated tether analysis functionality

Features:
- Browse and select TDMS files`
- Real-time parameter adjustment
- Live plateau analysis visualization
- Keyboard and joystick controls
- Save analysis results
- Mark files as good/bad for batch processing

Controls:
- Up/Down arrows or joystick: Navigate files
- G: Mark file as good
- B: Mark file as bad
- Enter: Run analysis with current parameters
- S: Save current session results
- L: Load previous session

Requirements:
- pip install PyQt5 pyqtgraph plotly kaleido pygame
"""

import pygame as pyg
import pandas as pd
import numpy as np
import xarray as xr
import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QGroupBox, 
                             QDoubleSpinBox, QSpinBox, QCheckBox, QTextEdit, QTreeView,
                             QShortcut, QFileSystemModel, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QDialog, QRadioButton, QButtonGroup)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QDir
from PyQt5.QtGui import QKeySequence, QColor, QFont
import pyqtgraph as pg
from pyfmreader import loadfile
import datetime

# Import tether analysis functions
from tether_script import process_single_file

class ParameterWidget(QWidget):
    """Widget for adjusting analysis parameters"""
    
    parametersChanged = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
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
        
        # Create parameter controls
        self.param_controls = {}
        
        # Define parameters with their default values and ranges
        params_config = [
            ('sav_window_length', 10, 3, 50, 2, "Savitzky Window Length"),
            ('sav_polyorder', 1, 1, 5, 1, "Savitzky Poly Order"),
            ('pl_threshold', 150e-9, 1e-9, 1e-6, 1e-9, "Plateau Threshold"),
            ('pl_min_width', 2, 1, 20, 1, "Min Plateau Width"),
            ('last_num_plateaus', 7, 1, 15, 1, "Max Plateaus"),
            ('last_plateau_avg_percentage', 15, 1, 100, 1, "Last Plateau Avg (%)"),
            ('max_offset', 100, 50, 100, 5, "Max Tilt Offset (%)"),
            ('min_offset', 70, 30, 90, 5, "Min Tilt Offset (%)"),
            ('z_sensor_delay', 0.001, 0.0001, 0.01, 0.0001, "Z Sensor Delay (s)"),
        ]
        
        # Add checkbox parameters
        checkbox_params = [
            ('bool_correct_overshoot', True, "Correct Overshoot")
        ]
        
        for param_name, default, min_val, max_val, step, label in params_config:
            group = QGroupBox(label)
            group_layout = QHBoxLayout(group)
            
            if param_name == 'pl_threshold':
                # Special handling for scientific notation
                spinbox = QDoubleSpinBox()
                spinbox.setDecimals(2)
                spinbox.setRange(min_val * 1e9, max_val * 1e9)  # Convert to nano scale
                spinbox.setValue(default * 1e9)
                spinbox.setSuffix(" nN")
                spinbox.valueChanged.connect(lambda v, name=param_name: self.updateParameter(name, v * 1e-9))
            elif param_name == 'z_sensor_delay':
                # Special handling for z_sensor_delay with more precision
                spinbox = QDoubleSpinBox()
                spinbox.setDecimals(4)
                spinbox.setRange(min_val, max_val)
                spinbox.setValue(default)
                spinbox.setSingleStep(step)
                spinbox.setSuffix(" s")
                spinbox.valueChanged.connect(lambda v, name=param_name: self.updateParameter(name, v))
            elif param_name == 'last_plateau_avg_percentage':
                # Special handling for percentage parameter
                spinbox = QSpinBox()
                spinbox.setRange(int(min_val), int(max_val))
                spinbox.setValue(default)
                spinbox.setSingleStep(int(step))
                spinbox.setSuffix(" %")
                spinbox.setToolTip("Percentage of last plateau to use for averaging (1-100%)")
                spinbox.valueChanged.connect(lambda v, name=param_name: self.updateParameter(name, v))
            else:
                if isinstance(default, int):
                    spinbox = QSpinBox()
                    spinbox.setRange(int(min_val), int(max_val))
                    spinbox.setValue(default)
                    spinbox.setSingleStep(int(step))
                else:
                    spinbox = QDoubleSpinBox()
                    spinbox.setRange(min_val, max_val)
                    spinbox.setValue(default)
                    spinbox.setSingleStep(step)
                    spinbox.setDecimals(1)
                
                spinbox.valueChanged.connect(lambda v, name=param_name: self.updateParameter(name, v))
            
            self.param_controls[param_name] = spinbox
            group_layout.addWidget(spinbox)
            layout.addWidget(group)
        
        # Add checkbox parameters
        for param_name, default, label in checkbox_params:
            group = QGroupBox(label)
            group_layout = QHBoxLayout(group)
            
            checkbox = QCheckBox()
            checkbox.setChecked(default)
            checkbox.stateChanged.connect(lambda state, name=param_name: self.updateParameter(name, state == 2))
            
            self.param_controls[param_name] = checkbox
            group_layout.addWidget(checkbox)
            layout.addWidget(group)
        
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
        layout.addStretch()
        
    def updateParameter(self, name, value):
        """Update parameter and emit signal"""
        self.emitParameters()
    
    def emitParameters(self):
        """Emit current parameters"""
        params = self.getCurrentParameters()
        self.parametersChanged.emit(params)
    
    def getCurrentParameters(self):
        """Get current parameter values"""
        params = {}
        for name, control in self.param_controls.items():
            if hasattr(control, 'isChecked'):  # Checkbox
                value = control.isChecked()
            else:  # SpinBox
                value = control.value()
                if name == 'pl_threshold':
                    value *= 1e-9  # Convert back from nano scale
            params[name] = value
        return params
    
    def resetToDefaults(self):
        """Reset all parameters to default values"""
        defaults = {
            'sav_window_length': 10,
            'sav_polyorder': 1,
            'pl_threshold': 150,  # In nano scale for display
            'pl_min_width': 2,
            'last_num_plateaus': 7,
            'last_plateau_avg_percentage': 15,
            'max_offset': 100,
            'min_offset': 70,
            'z_sensor_delay': 0.001,
            'bool_correct_overshoot': True
        }
        
        for name, value in defaults.items():
            if name in self.param_controls:
                control = self.param_controls[name]
                if hasattr(control, 'setChecked'):  # Checkbox
                    control.setChecked(value)
                else:  # SpinBox
                    control.setValue(value)
    
    def update_parameter_status(self, filename=None, is_file_specific=False):
        """Update the parameter status label"""
        if is_file_specific and filename:
            self.param_status_label.setText(f"File-specific: {os.path.basename(filename)}")
            self.param_status_label.setStyleSheet("QLabel { color: #2196F3; background-color: #E3F2FD; padding: 3px; border-radius: 3px; font-weight: bold; }")
        else:
            self.param_status_label.setText("Global parameters")
            self.param_status_label.setStyleSheet("QLabel { color: #666; background-color: #f0f0f0; padding: 3px; border-radius: 3px; }")

class TetherAnalysisGUI(QWidget):
    def __init__(self, root_dir, *args, **kwargs):
        self.i_file_path = 0
        self.file_path = []
        self.index = 0
        self.current_analysis_result = None
        # Initialize per-file parameter storage (empty at start)
        self.file_parameters = {}
        # Initialize plateau selection storage
        self.plateau_selections = {}
        
        QWidget.__init__(self, *args, **kwargs)
        self.setupUI()
        self.setupJoystick()
        self.setupShortcuts()
        
        # Initialize parameter status
        self.param_widget.update_parameter_status()
        
        # Set initial directory
        self.root_dir = root_dir
        self.dirModel.setRootPath(root_dir)
        self.treeview.setRootIndex(self.dirModel.index(root_dir))
        
    def setupUI(self):
        """Setup the user interface"""
        self.setWindowTitle("Tether Analysis GUI")
        self.setGeometry(100, 100, 1600, 900)
        
        main_layout = QHBoxLayout(self)
        
        # Left panel - File browser
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("File Browser"))
        
        self.treeview = QTreeView()
        self.listview = QListWidget()
        
        left_panel.addWidget(self.treeview, 1)
        left_panel.addWidget(self.listview, 1)
        
        # Status info
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        left_panel.addWidget(self.status_label)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(350)
        
        # Center panel - Plots
        center_panel = QVBoxLayout()
        
        # Plot controls
        plot_controls = QHBoxLayout()
        self.raw_check = QCheckBox("Raw Data")
        self.raw_check.setChecked(False)
        self.processed_check = QCheckBox("Processed Data") 
        self.processed_check.setChecked(True)
        self.plateaus_check = QCheckBox("Plateaus")
        self.plateaus_check.setChecked(True)
        
        plot_controls.addWidget(self.raw_check)
        plot_controls.addWidget(self.processed_check)
        plot_controls.addWidget(self.plateaus_check)
        plot_controls.addStretch()
        
        center_panel.addLayout(plot_controls)
        
        # Main plot
        self.plotview = pg.PlotWidget()
        self.plotview.setLabel('left', 'Deflection', units='N')
        self.plotview.setLabel('bottom', 'Time', units='s')
        self.plotview.showGrid(x=True, y=True)
        # Add legend with top-right positioning
        legend = self.plotview.addLegend(offset=(30, 30))
        legend.anchor = (1, 0)  # Top-right anchor
        center_panel.addWidget(self.plotview, 1)
        
        # Results display
        results_layout = QHBoxLayout()
        
        # Left side - Text display
        results_text_layout = QVBoxLayout()
        text_label = QLabel("File Info & Status")
        text_label.setStyleSheet("QLabel { font-weight: bold; }")
        results_text_layout.addWidget(text_label)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(120)
        self.results_text.setReadOnly(True)
        
        # Set default instructions text
        default_instructions = """Welcome to Tether Analysis GUI!

Keyboard Shortcuts:
• ↑/↓ - Navigate files (Previous/Next)
• G - Mark file as Good
• B - Mark file as Bad  
• Enter - Run analysis
• S - Save session
• L - Load session

Click a folder to start analyzing TDMS files."""
        self.results_text.setText(default_instructions)
        
        results_text_layout.addWidget(self.results_text)
        
        # Right side - Plateau table
        table_layout = QVBoxLayout()
        table_label = QLabel("Plateau Analysis Results")
        table_label.setStyleSheet("QLabel { font-weight: bold; }")
        table_layout.addWidget(table_label)
        
        # Plateau selection controls
        plateau_controls_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        self.export_selected_button = QPushButton("Export Selected")
        
        self.select_all_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 10px; }")
        self.select_none_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-size: 10px; }")
        self.export_selected_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-size: 10px; }")
        
        self.select_all_button.clicked.connect(self.select_all_plateaus)
        self.select_none_button.clicked.connect(self.select_no_plateaus)
        self.export_selected_button.clicked.connect(self.export_selected_plateaus)
        
        plateau_controls_layout.addWidget(self.select_all_button)
        plateau_controls_layout.addWidget(self.select_none_button)
        plateau_controls_layout.addWidget(self.export_selected_button)
        plateau_controls_layout.addStretch()
        table_layout.addLayout(plateau_controls_layout)
        
        self.plateau_table = QTableWidget()
        self.plateau_table.setMinimumHeight(200)
        self.plateau_table.setMaximumHeight(300)
        self.setup_plateau_table()
        table_layout.addWidget(self.plateau_table)
        
        # Add velocity indicators below the plateau table
        velocity_layout = QHBoxLayout()
        
        # Calculated velocity indicator
        self.calc_ret_vel_label = QLabel("Calc Ret Vel: -- μm/s")
        self.calc_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F5E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")
        self.calc_ret_vel_label.setToolTip("Calculated retract velocity from linear regression")
        velocity_layout.addWidget(self.calc_ret_vel_label)
        
        # Metadata velocity indicator  
        self.meta_ret_vel_label = QLabel("Meta Ret Vel: -- μm/s")
        self.meta_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F0FF; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")
        self.meta_ret_vel_label.setToolTip("Retract velocity from file metadata")
        velocity_layout.addWidget(self.meta_ret_vel_label)
        
        velocity_layout.addStretch()  # Push indicators to the left
        table_layout.addLayout(velocity_layout)
        
        results_layout.addLayout(results_text_layout, 1)
        results_layout.addLayout(table_layout, 2)  # Give table more space
        
        center_panel.addLayout(results_layout)
        
        center_widget = QWidget()
        center_widget.setLayout(center_panel)
        
        # File navigation buttons - separate panel for edge positioning
        nav_layout = QVBoxLayout()
        self.prev_button = QPushButton("Previous (↑)")
        self.next_button = QPushButton("Next (↓)")
        self.good_button = QPushButton("Good (G)")
        self.bad_button = QPushButton("Bad (B)")
        self.analyze_button = QPushButton("Analyze (Enter)")
        self.load_session_button = QPushButton("Load Session (L)")
        
        self.good_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        self.bad_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        self.analyze_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        self.load_session_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.good_button)
        nav_layout.addWidget(self.bad_button)
        nav_layout.addWidget(self.analyze_button)
        nav_layout.addWidget(self.load_session_button)
        nav_layout.addStretch()
        
        nav_widget = QWidget()
        nav_widget.setLayout(nav_layout)
        nav_widget.setFixedWidth(140)  # Increased width for Load Session button
        
        # Right panel - Parameters
        self.param_widget = ParameterWidget()
        self.param_widget.setFixedWidth(300)
        
        # Add panels to main layout - navigation buttons at far right edge
        main_layout.addWidget(left_widget)
        main_layout.addWidget(center_widget, 1)
        main_layout.addWidget(self.param_widget)
        main_layout.addWidget(nav_widget)  # Navigation buttons at far right edge
        
        # Setup file system model
        self.dirModel = QFileSystemModel()
        self.dirModel.setRootPath(QDir.rootPath())
        self.dirModel.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        self.treeview.setModel(self.dirModel)
        
        # Connect signals
        self.treeview.clicked.connect(self.on_clicked_folder)
        self.listview.clicked.connect(self.on_click_file)
        self.param_widget.parametersChanged.connect(self.on_parameters_changed)
        
        # Connect navigation buttons
        self.prev_button.clicked.connect(self.file_prev)
        self.next_button.clicked.connect(self.file_next)
        self.good_button.clicked.connect(self.file_good)
        self.bad_button.clicked.connect(self.file_bad)
        self.analyze_button.clicked.connect(self.run_analysis)
        self.load_session_button.clicked.connect(self.load_session)
        
        # Connect plot checkboxes
        self.raw_check.stateChanged.connect(self.update_plot_display)
        self.processed_check.stateChanged.connect(self.update_plot_display)
        self.plateaus_check.stateChanged.connect(self.update_plot_display)
        
    def setupShortcuts(self):
        """Setup keyboard shortcuts"""
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_good = QShortcut(QKeySequence(Qt.Key_G), self)
        self.shortcut_bad = QShortcut(QKeySequence(Qt.Key_B), self)
        self.shortcut_analyze = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut_save = QShortcut(QKeySequence(Qt.Key_S), self)
        self.shortcut_load = QShortcut(QKeySequence(Qt.Key_L), self)
        
        # Connect shortcuts
        self.shortcut_next.activated.connect(self.file_next)
        self.shortcut_prev.activated.connect(self.file_prev)
        self.shortcut_good.activated.connect(self.file_good)
        self.shortcut_bad.activated.connect(self.file_bad)
        self.shortcut_analyze.activated.connect(self.run_analysis)
        self.shortcut_save.activated.connect(self.save_session)
        self.shortcut_load.activated.connect(self.load_session)
        
    def setupJoystick(self):
        """Setup joystick support"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_joystick)
        self.timer.start(100)
        
        pyg.init()
        pyg.joystick.init()
        
        if pyg.joystick.get_count() > 0:
            self.joystick = pyg.joystick.Joystick(0)
            self.joystick.init()
            self.status_label.setText(f"Joystick connected: {self.joystick.get_name()}")
        else:
            self.joystick = None
            
    def read_joystick(self):
        """Read joystick input"""
        if self.joystick is None:
            return
            
        pyg.event.pump()
        if self.joystick.get_button(0):  # A
            self.save_session()
        elif self.joystick.get_button(11):  # up
            self.file_prev()
        elif self.joystick.get_button(12):  # down
            self.file_next()
        elif self.joystick.get_button(9):  # Y
            self.file_bad()
        elif self.joystick.get_button(10):  # X
            self.file_good()
        elif self.joystick.get_button(1):  # B - analyze
            self.run_analysis()

    def find_tdms_files(self, root_dir):
        """Find all TDMS files in directory, excluding files in specified error folders"""
        file_path = []
        file_name = []
        
        # Define folders to exclude
        exclude_folders = ['error_file', 'error_files', 'errors', 'bad_files']
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip if current directory matches any exclude pattern
            if any(exclude_name in os.path.basename(dirpath) for exclude_name in exclude_folders):
                continue
                
            # Remove excluded directories from subdirectories to skip
            dirnames[:] = [d for d in dirnames if not any(exclude_name in d for exclude_name in exclude_folders)]
                
            for filename in filenames:
                if filename.endswith(".tdms"):
                    full_path = os.path.join(dirpath, filename)
                    file_path.append(full_path)
                    file_name.append(filename)
                    
        self.file = file_name
        self.file_path = file_path
        self.bool_good_curve = np.zeros(len(file_path))
        self.file_parameters = {}
        self.plateau_selections = {}  # Reset plateau selections for new directory
            
    def on_clicked_folder(self, index):
        """Handle folder selection"""
        self.save_session()
        self.listview.clear()
        
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        self.find_tdms_files(path)
        
        if self.file:
            self.listview.addItems(self.file)
            self.index = 0
            self.listview.setCurrentRow(self.index)
            # Load parameters for the first file
            self.load_parameters_for_current_file()
            # Automatically run analysis on first file
            QTimer.singleShot(200, self.run_analysis)
            self.status_label.setText(f"Loaded {len(self.file)} TDMS files")
        else:
            self.status_label.setText("No TDMS files found in directory")
            
    def on_click_file(self, item):
        """Handle file selection"""
        # Save parameters for previous file
        self.save_parameters_for_current_file()
        
        self.index = self.listview.currentRow()
        # Clear previous analysis result
        self.current_analysis_result = None
        
        # Load parameters for the new file
        self.load_parameters_for_current_file()
        
        # Automatically run analysis after file selection
        QTimer.singleShot(100, self.run_analysis)
        
    def file_good(self):
        """Mark current file as good"""
        if self.file_path:
            self.bool_good_curve[self.index] = 1
            self.change_item_color(QColor(0, 255, 0))
            self.status_label.setText("File marked as GOOD")
            self.file_next()
            
    def file_bad(self):
        """Mark current file as bad"""
        if self.file_path:
            self.bool_good_curve[self.index] = 0
            self.change_item_color(QColor(255, 0, 0))
            self.status_label.setText("File marked as BAD")
            self.file_next()
            
    def file_next(self):
        """Navigate to next file"""
        if self.file_path:
            # Save parameters for current file
            self.save_parameters_for_current_file()
            
            self.index = (self.index + 1) % len(self.file_path)
            self.listview.setCurrentRow(self.index)
            # Clear previous analysis result
            self.current_analysis_result = None
            
            # Load parameters for the new file
            self.load_parameters_for_current_file()
            
            # Automatically run analysis after navigation
            QTimer.singleShot(100, self.run_analysis)
            
    def file_prev(self):
        """Navigate to previous file"""
        if self.file_path:
            # Save parameters for current file
            self.save_parameters_for_current_file()
            
            self.index = (self.index - 1) % len(self.file_path)
            self.listview.setCurrentRow(self.index)
            # Clear previous analysis result
            self.current_analysis_result = None
            
            # Load parameters for the new file
            self.load_parameters_for_current_file()
            
            # Automatically run analysis after navigation
            QTimer.singleShot(100, self.run_analysis)
            
    def change_item_color(self, color=QColor(0, 0, 255)):
        """Change color of current list item"""
        current_item = self.listview.currentItem()
        if current_item:
            current_item.setBackground(color)
            
    def on_parameters_changed(self, params):
        """Handle parameter changes"""
        if self.file_path and hasattr(self, 'current_file_loaded'):
            self.run_analysis()
            
    def run_analysis(self):
        """Run tether analysis on current file"""
        if not self.file_path:
            return
            
        try:
            filename = self.file_path[self.index]
            params = self.param_widget.getCurrentParameters()
            
            self.status_label.setText("Running analysis...")
            QApplication.processEvents()
            
            # Run analysis
            result = process_single_file(filename, params, save_plots=False)
            self.current_analysis_result = result
            
            # Update plot and results
            self.update_plot_with_analysis(result)
            self.update_results_display(result)
            self.update_plateau_table(result)
            
            plateau_count = len(result['plateaus']) if result['plateaus'] else 0
            self.status_label.setText(f"Analysis complete - {plateau_count} plateaus found")
            
        except Exception as e:
            self.status_label.setText(f"Analysis failed: {str(e)}")
            self.results_text.setText(f"Error: {str(e)}")
            self.update_plateau_table(None)  # Clear table on error
            
    def get_file_parameters(self, file_path):
        """Get parameters for a specific file, or default if not set"""
        # Ensure file_parameters exists
        if not hasattr(self, 'file_parameters'):
            self.file_parameters = {}
            
        if file_path in self.file_parameters:
            return self.file_parameters[file_path].copy()
        else:
            # Return default parameters from parameter widget
            try:
                return self.param_widget.getCurrentParameters()
            except Exception:
                # Fallback to hardcoded defaults if parameter widget not ready
                return self.get_default_parameters()
    
    def get_default_parameters(self):
        """Get hardcoded default parameters as fallback"""
        return {
            'sav_window_length': 10,
            'sav_polyorder': 1,
            'pl_threshold': 150e-9,  # In actual units (not nano scale)
            'pl_min_width': 2,
            'last_num_plateaus': 7,
            'last_plateau_avg_percentage': 15,
            'max_offset': 100,
            'min_offset': 70,
            'z_sensor_delay': 0.001,
            'bool_correct_overshoot': True
        }
    
    def set_file_parameters(self, file_path, params):
        """Set parameters for a specific file"""
        # Ensure file_parameters exists
        if not hasattr(self, 'file_parameters'):
            self.file_parameters = {}
        self.file_parameters[file_path] = params.copy()
    
    def load_parameters_for_current_file(self):
        """Load parameters for the current file into the parameter widget"""
        if not self.file_path or self.index >= len(self.file_path):
            return
            
        try:
            current_file = self.file_path[self.index]
            file_params = self.get_file_parameters(current_file)
            
            # Update parameter widget with file-specific parameters
            for name, value in file_params.items():
                if hasattr(self.param_widget, 'param_controls') and name in self.param_widget.param_controls:
                    control = self.param_widget.param_controls[name]
                    try:
                        if hasattr(control, 'setChecked'):  # Checkbox
                            control.setChecked(value)
                        else:  # SpinBox
                            if name == 'pl_threshold':
                                value *= 1e9  # Convert to nano scale for display
                            control.setValue(value)
                    except Exception as e:
                        # Skip this parameter if there's an issue setting it
                        print(f"Warning: Could not set parameter {name} to {value}: {e}")
            # Update status label
            is_file_specific = True  # Indicate that these are file-specific parameters
            self.param_widget.update_parameter_status(current_file, is_file_specific)
        except Exception as e:
            print(f"Warning: Could not load parameters for current file: {e}")
    
    def save_parameters_for_current_file(self):
        """Save current parameter widget values for the current file"""
        if not self.file_path or self.index >= len(self.file_path):
            return
            
        try:
            current_file = self.file_path[self.index]
            current_params = self.param_widget.getCurrentParameters()
            self.set_file_parameters(current_file, current_params)
        except Exception as e:
            print(f"Warning: Could not save parameters for current file: {e}")
            
    def update_plot(self):
        """Update plot with raw data"""
        if not self.file_path:
            return
            
        try:
            self.i_file_path = self.file_path[self.index]
            self.plotview.clear()
            legend = self.plotview.addLegend(offset=(30, 30))
            legend.anchor = (1, 0)  # Top-right anchor
            
            # Load and plot raw data
            uff = loadfile(self.i_file_path)
            metadata = uff.filemetadata
            FC = uff.getcurve(0)
            
            defl_sens = metadata['defl_sens_nmbyV'] / 1e09
            FC.preprocess_force_curve(defl_sens, metadata['height_channel_key'])
            
            # Get retract segment
            for segid, segment in FC.get_segments():
                if segment.segment_type in ('Retract', 'Ret'):
                    ret_deflection = -segment.vdeflection * metadata['spring_const_Nbym']
                    
                    # Create time array
                    relative_SR = metadata['relative_sr'][segid]
                    time_array = np.arange(len(ret_deflection)) * relative_SR
                    
                    if self.raw_check.isChecked():
                        self.plotview.plot(time_array, ret_deflection, 
                                         pen=pg.mkPen(color='blue', width=1),
                                         name='Raw Data')
                    break
                    
            self.current_file_loaded = True
            filename = os.path.basename(self.i_file_path)
            self.results_text.setText(f"Loaded: {filename}\nPress Enter to analyze")
            
        except Exception as e:
            self.status_label.setText(f"Error loading file: {str(e)}")
            
    def update_plot_with_analysis(self, result):
        """Update plot with analysis results"""
        # Clear everything including legend
        self.plotview.clear()
        legend = self.plotview.addLegend(offset=(30, 30))
        legend.anchor = (1, 0)  # Top-right anchor
        
        if not result:
            return
            
        try:
            # Plot raw data if requested
            if self.raw_check.isChecked():
                # Get raw data
                uff = loadfile(result['filename'])
                metadata = uff.filemetadata
                FC = uff.getcurve(0)
                
                defl_sens = metadata['defl_sens_nmbyV'] / 1e09
                FC.preprocess_force_curve(defl_sens, metadata['height_channel_key'])
                
                for segid, segment in FC.get_segments():
                    if segment.segment_type in ('Retract', 'Ret'):
                        ret_deflection = -segment.vdeflection * metadata['spring_const_Nbym']
                        relative_SR = metadata['relative_sr'][segid]
                        time_array = np.arange(len(ret_deflection)) * relative_SR
                        
                        self.plotview.plot(time_array, ret_deflection,
                                         pen=pg.mkPen(color='lightblue', width=1),
                                         name='Raw Data')
                        break
            
            # Plot processed data
            if self.processed_check.isChecked():
                rel_time = result['rel_time']
                defl_savitz = result['defl_savitz']
                
                self.plotview.plot(rel_time, defl_savitz,
                                 pen=pg.mkPen(color='blue', width=2),
                                 name='Processed Data')
            
            # Plot plateaus
            if self.plateaus_check.isChecked() and result['plateaus']:
                rel_time = result['rel_time']
                defl_savitz = result['defl_savitz']
                plateaus = result['plateaus']
                df_plat = result['df_plat']
                
                # Get selected plateau indices
                selected_plateaus = self.get_selected_plateaus()
                
                # Plot plateau regions (only selected ones)
                colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
                displayed_count = 0
                
                for i, (start, end) in enumerate(plateaus):
                    # Only plot if this plateau is selected
                    if i in selected_plateaus:
                        color = colors[displayed_count % len(colors)]
                        
                        # Plateau region
                        self.plotview.plot(rel_time[start:end], defl_savitz[start:end],
                                         pen=pg.mkPen(color=color, width=3),
                                         name=f'Plateau {i+1}')
                        
                        # Average line
                        plateau_avg = np.mean(defl_savitz[start:end])
                        self.plotview.plot([rel_time[start], rel_time[end-1]],
                                         [plateau_avg, plateau_avg],
                                         pen=pg.mkPen(color=color, width=2, style=Qt.DashLine),
                                         name=f'Avg {i+1}')
                        
                        # Plot plateau markers
                        if i < len(df_plat['plateau_avg_idx']):
                            idx = df_plat['plateau_avg_idx'].iloc[i]
                            self.plotview.plot([rel_time[idx]], [defl_savitz[idx]],
                                             pen=None, symbol='o', symbolSize=8,
                                             symbolBrush=color,
                                             name=f'Center {i+1}')
                        
                        displayed_count += 1
                                     
        except Exception as e:
            self.status_label.setText(f"Error plotting analysis: {str(e)}")
            
    def update_plot_display(self):
        """Update plot display based on checkboxes"""
        if hasattr(self, 'current_analysis_result') and self.current_analysis_result:
            # Re-plot with current analysis results
            self.update_plot_with_analysis(self.current_analysis_result)
        elif hasattr(self, 'i_file_path') and self.file_path:
            # Show raw data only if no analysis results
            self.plotview.clear()
            legend = self.plotview.addLegend(offset=(30, 30))
            legend.anchor = (1, 0)  # Top-right anchor
            self.update_plot()
            
    def update_results_display(self, result):
        """Update results text display and plateau table"""
        if not result or not result['plateaus']:
            self.results_text.setText("No plateaus detected")
            self.update_plateau_table(None)
            return
            
        # Update text display
        filename = os.path.basename(result['filename'])
        
        results_text = f"File: {filename}\n"
        results_text += f"Plateaus found: {len(result['plateaus'])}\n"
        results_text += "Analysis completed successfully"
        
        self.results_text.setText(results_text)
        
        # Update plateau table
        self.update_plateau_table(result)
        
    def setup_plateau_table(self):
        """Setup the plateau table with appropriate columns"""
        # Define columns - added 'Include' column for selection
        headers = ['Include', 'Plateau #', 'Avg Force (N)', 'ΔAvg (N)', 'ΔTime (s)', 'x̄(dy/dx)', 'Slope', 'Vel (μm/s)']
        self.plateau_table.setColumnCount(len(headers))
        self.plateau_table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.plateau_table.setAlternatingRowColors(True)
        self.plateau_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plateau_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Initialize plateau selection state storage
        self.plateau_selections = {}
        
        # Adjust column widths
        header = self.plateau_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Include column
        for i in range(1, len(headers) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
    def update_plateau_table(self, result):
        """Update the plateau table with analysis results"""
        if not result or not result['plateaus']:
            self.plateau_table.setRowCount(0)
            self.reset_velocity_indicators()
            return
            
        df_plat = result['df_plat']
        self.plateau_table.setRowCount(len(df_plat))
        
        # Get current file identifier for plateau selection storage
        current_file = self.file_path[self.index] if self.file_path else "default"
        
        # Initialize plateau selections for this file if not exists
        if current_file not in self.plateau_selections:
            self.plateau_selections[current_file] = [True] * len(df_plat)  # Default: all selected
        
        # Ensure the selection list matches current plateau count
        selections = self.plateau_selections[current_file]
        if len(selections) != len(df_plat):
            # Adjust selection list size - new plateaus default to selected
            if len(selections) < len(df_plat):
                selections.extend([True] * (len(df_plat) - len(selections)))
            else:
                selections = selections[:len(df_plat)]
            self.plateau_selections[current_file] = selections
        
        for row, (i, data) in enumerate(df_plat.iterrows()):
            # Include checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(selections[row])
            checkbox.stateChanged.connect(lambda state, r=row, f=current_file: self.on_plateau_selection_changed(r, f, state == 2))
            self.plateau_table.setCellWidget(row, 0, checkbox)
            
            # Plateau number
            self.plateau_table.setItem(row, 1, QTableWidgetItem(str(int(data['plateaus']))))
            
            # Average force (in scientific notation)
            avg_force = QTableWidgetItem(f"{data['plateau_avg']:.2e}")
            self.plateau_table.setItem(row, 2, avg_force)
            
            # Delta average
            delta_avg = QTableWidgetItem(f"{data['delta_avg']:.2e}")
            self.plateau_table.setItem(row, 3, delta_avg)
            
            # Delta time
            delta_time = QTableWidgetItem(f"{data['delta_time']:.3f}")
            self.plateau_table.setItem(row, 4, delta_time)
            
            # Mean dy/dx (derivative) in scientific notation
            if 'mean dN/dt' in data:
                mean_dNdt = QTableWidgetItem(f"{data['mean dN/dt']:.2e}")
                self.plateau_table.setItem(row, 5, mean_dNdt)
            else:
                self.plateau_table.setItem(row, 5, QTableWidgetItem("N/A"))
            
            # Plateau slope in scientific notation
            if 'plateau_slope' in data:
                plateau_slope = QTableWidgetItem(f"{data['plateau_slope']:.2e}")
                self.plateau_table.setItem(row, 6, plateau_slope)
            else:
                self.plateau_table.setItem(row, 6, QTableWidgetItem("N/A"))
            
            # Calculated velocity for this plateau
            if 'velocity_calc_um_s' in data:
                velocity_calc = QTableWidgetItem(f"{data['velocity_calc_um_s']:.1f}")
                self.plateau_table.setItem(row, 7, velocity_calc)
            else:
                self.plateau_table.setItem(row, 7, QTableWidgetItem("N/A"))
                
        # Resize columns to content
        self.plateau_table.resizeColumnsToContents()
        
        # Update velocity indicators
        self.update_velocity_indicators(result)
        
        # Update plot to reflect current selections
        self.update_plot_plateau_visibility()
    
    def update_velocity_indicators(self, result):
        """Update velocity indicators based on analysis results"""
        try:
            if result and 'velocity_metadata' in result and 'velocity_calc_um_s' in result:
                # Update metadata velocity (from file metadata)
                vel_meta = result['velocity_metadata']
                if isinstance(vel_meta, (int, float)) and not np.isnan(vel_meta):
                    self.meta_ret_vel_label.setText(f"Meta Ret Vel: {vel_meta:.1f} μm/s")
                    self.meta_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F0FF; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: black; }")
                else:
                    self.meta_ret_vel_label.setText("Meta Ret Vel: N/A")
                    self.meta_ret_vel_label.setStyleSheet("QLabel { background-color: #FFE8E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: #666; }")
                
                # Update calculated velocity (from linear regression)
                vel_calc = result['velocity_calc_um_s']
                if isinstance(vel_calc, (int, float)) and not np.isnan(vel_calc):
                    self.calc_ret_vel_label.setText(f"Calc Ret Vel: {vel_calc:.1f} μm/s")
                    self.calc_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F5E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: black; }")
                else:
                    self.calc_ret_vel_label.setText("Calc Ret Vel: N/A")
                    self.calc_ret_vel_label.setStyleSheet("QLabel { background-color: #FFE8E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: #666; }")
            else:
                self.reset_velocity_indicators()
        except Exception as e:
            print(f"Warning: Could not update velocity indicators: {e}")
            self.reset_velocity_indicators()
    
    def reset_velocity_indicators(self):
        """Reset velocity indicators when no data is available"""
        self.calc_ret_vel_label.setText("Calc Ret Vel: -- μm/s")
        self.calc_ret_vel_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: #666; }")
        
        self.meta_ret_vel_label.setText("Meta Ret Vel: -- μm/s")
        self.meta_ret_vel_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: #666; }")

    def update_plot_plateau_visibility(self):
        """Update plot to show/hide plateaus based on current selections"""
        if hasattr(self, 'current_analysis_result') and self.current_analysis_result:
            # Re-plot with current analysis results to update plateau visibility
            self.update_plot_with_analysis(self.current_analysis_result)
        
    def on_plateau_selection_changed(self, row, file_path, checked):
        """Handle plateau selection checkbox changes"""
        if file_path in self.plateau_selections:
            if row < len(self.plateau_selections[file_path]):
                self.plateau_selections[file_path][row] = checked
                # Update plot to show/hide plateaus based on selection
                self.update_plot_plateau_visibility()
    
    def get_selected_plateaus(self):
        """Get indices of currently selected plateaus for the current file"""
        current_file = self.file_path[self.index] if self.file_path else "default"
        if current_file in self.plateau_selections:
            # Return list of indices where selection is True
            return [i for i, selected in enumerate(self.plateau_selections[current_file]) if selected]
        return []  # Return empty list if no selections or no current file
    
    def select_all_plateaus(self):
        """Select all plateaus in the current file"""
        current_file = self.file_path[self.index] if self.file_path else "default"
        if current_file in self.plateau_selections:
            # Set all to True
            self.plateau_selections[current_file] = [True] * len(self.plateau_selections[current_file])
            # Update checkboxes in table
            for row in range(self.plateau_table.rowCount()):
                checkbox = self.plateau_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def select_no_plateaus(self):
        """Deselect all plateaus in the current file"""
        current_file = self.file_path[self.index] if self.file_path else "default"
        if current_file in self.plateau_selections:
            # Set all to False
            self.plateau_selections[current_file] = [False] * len(self.plateau_selections[current_file])
            # Update checkboxes in table
            for row in range(self.plateau_table.rowCount()):
                checkbox = self.plateau_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
    
    def export_selected_plateaus(self):
        """Export only the selected plateaus to CSV"""
        if not hasattr(self, 'current_analysis_result') or not self.current_analysis_result:
            self.status_label.setText("No analysis results to export")
            return
        
        # Get selected plateau indices
        selected_indices = self.get_selected_plateaus()
        if not selected_indices:
            self.status_label.setText("No plateaus selected for export")
            return
        
        try:
            # Filter the analysis results to only include selected plateaus
            result = self.current_analysis_result
            df_plat = result['df_plat']
            
            # Filter dataframe to only selected plateaus
            selected_df = df_plat.iloc[selected_indices].copy()
            
            # Generate filename with timestamp
            filename = os.path.basename(result['filename'])
            base_name = os.path.splitext(filename)[0]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"{base_name}_selected_plateaus_{timestamp}.csv"
            
            # Save to same directory as the original file
            export_path = os.path.join(os.path.dirname(result['filename']), export_filename)
            
            # Add metadata to the export
            export_data = {
                'filename': filename,
                'total_plateaus_found': len(df_plat),
                'selected_plateaus': len(selected_indices),
                'selected_indices': selected_indices,
                'export_timestamp': timestamp
            }
            
            # Save the filtered dataframe
            selected_df.to_csv(export_path, index=False)
            
            # Save metadata as well
            metadata_path = export_path.replace('.csv', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            # Also create xarray export of the analysis results
            xarray_path = self.export_analysis_results_xarray(export_path, timestamp)
            
            status_msg = f"Exported {len(selected_indices)} plateaus to {os.path.basename(export_path)}"
            if xarray_path:
                status_msg += f" + XArray"
            self.status_label.setText(status_msg)
            
        except Exception as e:
            self.status_label.setText(f"Export failed: {str(e)}")
    
    def save_session(self):
        """Save current session with all file parameters and plateau selections"""
        try:
            if not self.file_path:
                self.status_label.setText("No files loaded to save session")
                return
            
            # Open file dialog to save session CSV file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"tether_session_{timestamp}.csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Tether Analysis Session", 
                os.path.join(self.root_dir, default_filename),
                "CSV files (*.csv);;All files (*.*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Prepare session data for CSV
            session_data = []
            
            for i, (filepath, filename) in enumerate(zip(self.file_path, self.file)):
                # Get current parameters for this file
                file_params = self.file_parameters.get(filepath, self.get_default_parameters())
                
                # Get current plateau selections for this file
                plateau_selections = self.plateau_selections.get(filepath, [])
                
                # Create row data
                row_data = {
                    'local_file_path': filepath,
                    'file_name': filename,
                    'bool_good_curve': int(self.bool_good_curve[i]) if i < len(self.bool_good_curve) else 0,
                    'file_parameters': json.dumps(file_params),
                    'plateau_selections': json.dumps(plateau_selections)
                }
                
                session_data.append(row_data)
            
            # Create DataFrame and save CSV
            df_session = pd.DataFrame(session_data)
            df_session.to_csv(file_path, index=False)
            
            # Create xarray Dataset for more structured data storage
            xarray_path = file_path.replace('.csv', '_xarray.nc')
            self.save_session_xarray(xarray_path, timestamp)
            
            # Update status
            good_count = int(np.sum(self.bool_good_curve)) if len(self.bool_good_curve) > 0 else 0
            total_count = len(self.file_path)
            
            session_info = f"Session saved: {os.path.basename(file_path)}\n"
            session_info += f"Total files: {total_count}\n"
            session_info += f"Good files: {good_count}\n"
            session_info += f"Bad files: {total_count - good_count}\n"
            session_info += "Per-file parameters: Saved\n"
            session_info += "Plateau selections: Saved\n"
            session_info += f"XArray dataset: {os.path.basename(xarray_path)}"
            
            self.results_text.setText(session_info)
            self.status_label.setText(f"Session saved: {os.path.basename(file_path)} + XArray")
            
        except Exception as e:
            self.status_label.setText(f"Error saving session: {str(e)}")
            self.results_text.setText(f"Error saving session: {str(e)}")
    
    def save_session_xarray(self, xarray_path, timestamp):
        """Save session data as xarray Dataset with rich metadata and structure"""
        try:
            # Prepare data arrays
            n_files = len(self.file_path)
            
            # File information - use proper data types
            file_paths = np.array(self.file_path, dtype='U')  # String array for paths
            file_names = np.array(self.file, dtype='U')  # String array for names 
            good_curve_flags = self.bool_good_curve.astype(bool)  # Boolean array
            
            # Prepare parameter data and plateau selections as JSON strings
            # (since parameters have mixed types, JSON strings are most compatible)
            file_parameters_json = []
            plateau_selections_json = []
            
            for filepath in self.file_path:
                # Get parameters for this file and convert to JSON string
                file_params = self.file_parameters.get(filepath, self.get_default_parameters())
                file_parameters_json.append(json.dumps(file_params))
                
                # Get plateau selections and convert to JSON string
                plateau_sel = self.plateau_selections.get(filepath, [])
                plateau_selections_json.append(json.dumps(plateau_sel))
            
            # Convert to numpy arrays with proper dtypes
            file_parameters_array = np.array(file_parameters_json, dtype='U')
            plateau_selections_array = np.array(plateau_selections_json, dtype='U')
            
            # Create coordinate array
            file_coords = np.arange(n_files)
            
            # Create data variables with appropriate data types
            data_vars = {
                'file_path': (['file'], file_paths),  # String data
                'file_name': (['file'], file_names),  # String data  
                'bool_good_curve': (['file'], good_curve_flags),  # Boolean data
                'file_parameters': (['file'], file_parameters_array),  # JSON strings
                'plateau_selections': (['file'], plateau_selections_array),  # JSON strings
            }
            
            # Create coordinates  
            coords = {
                'file': file_coords,  # Numeric coordinate
            }
            
            # Create Dataset with comprehensive attributes
            ds = xr.Dataset(
                data_vars=data_vars,
                coords=coords,
                attrs={
                    'title': 'Tether Analysis Session Data',
                    'description': 'Session data from Tether Analysis GUI with per-file parameters and selections',
                    'creation_timestamp': timestamp,
                    'creation_date': datetime.datetime.now().isoformat(),
                    'software': 'Tether Analysis GUI v2',
                    'total_files': n_files,
                    'good_files': int(np.sum(good_curve_flags)),
                    'bad_files': int(n_files - np.sum(good_curve_flags)),
                    'data_format_version': '2.0',
                    'root_directory': self.root_dir,
                    'coordinate_description': 'file: numeric index for each TDMS file',
                    'data_types': 'file_path: string, file_name: string, bool_good_curve: boolean, file_parameters: JSON string, plateau_selections: JSON string'
                }
            )
            
            # Add detailed attributes to data variables with proper descriptions
            ds['file_path'].attrs = {
                'long_name': 'File paths',
                'description': 'Full local file system paths to TDMS files',
                'data_type': 'string'
            }
            
            ds['file_name'].attrs = {
                'long_name': 'File names',
                'description': 'Base names of TDMS files without directory path',
                'data_type': 'string'
            }
            
            ds['bool_good_curve'].attrs = {
                'long_name': 'Good curve flags',
                'description': 'Boolean flags indicating whether curve was marked as good (True) or bad (False)',
                'data_type': 'boolean'
            }
            
            ds['file_parameters'].attrs = {
                'long_name': 'Analysis parameters',
                'description': 'JSON-encoded analysis parameters for each file (mixed numeric/string/boolean types)',
                'data_type': 'JSON string',
                'parameter_keys': str(list(self.get_default_parameters().keys())),
                'example_parameters': str(self.get_default_parameters())
            }
            
            ds['plateau_selections'].attrs = {
                'long_name': 'Plateau selections',
                'description': 'JSON-encoded boolean arrays indicating which plateaus were selected for each file',
                'data_type': 'JSON string',
                'note': 'Each entry is a JSON list of boolean values'
            }
            
            # Save the dataset with proper encoding
            ds.to_netcdf(xarray_path, format='NETCDF4')
            
            print(f"XArray dataset saved to: {xarray_path}")
            
        except Exception as e:
            print(f"Warning: Could not save xarray dataset: {e}")
            # Don't fail the main save operation if xarray save fails
    
    def export_analysis_results_xarray(self, base_path, timestamp):
        """Export current analysis results as xarray Dataset"""
        try:
            if not hasattr(self, 'current_analysis_result') or not self.current_analysis_result:
                return None
                
            result = self.current_analysis_result
            
            # Extract data from analysis result
            rel_time = result['rel_time']
            defl_savitz = result['defl_savitz']
            displacement = result['displacement']
            df_plat = result['df_plat']
            plateaus = result['plateaus']
            
            n_points = len(rel_time)
            n_plateaus = len(df_plat) if len(df_plat) > 0 else 1
            
            # Create coordinate arrays
            time_coords = rel_time
            plateau_coords = np.arange(n_plateaus)
            
            # Prepare plateau data arrays
            plateau_data = {}
            if len(df_plat) > 0:
                plateau_data = {
                    'plateau_numbers': (['plateau'], df_plat['plateaus'].values),
                    'plateau_avg_force': (['plateau'], df_plat['plateau_avg'].values),
                    'plateau_delta_avg': (['plateau'], df_plat['delta_avg'].values),
                    'plateau_start_idx': (['plateau'], df_plat['start'].values),
                    'plateau_end_idx': (['plateau'], df_plat['end'].values),
                    'plateau_avg_idx': (['plateau'], df_plat['plateau_avg_idx'].values),
                    'plateau_delta_time': (['plateau'], df_plat['delta_time'].values),
                    'plateau_mean_derivative': (['plateau'], df_plat['mean dN/dt'].values),
                    'plateau_velocity_calc': (['plateau'], df_plat['velocity_calc_um_s'].values),
                }
            else:
                # Create empty arrays if no plateaus
                empty_array = np.array([np.nan])
                plateau_data = {
                    'plateau_numbers': (['plateau'], empty_array),
                    'plateau_avg_force': (['plateau'], empty_array),
                    'plateau_delta_avg': (['plateau'], empty_array),
                    'plateau_start_idx': (['plateau'], empty_array),
                    'plateau_end_idx': (['plateau'], empty_array),
                    'plateau_avg_idx': (['plateau'], empty_array),
                    'plateau_delta_time': (['plateau'], empty_array),
                    'plateau_mean_derivative': (['plateau'], empty_array),
                    'plateau_velocity_calc': (['plateau'], empty_array),
                }
            
            # Create data variables dictionary
            data_vars = {
                'time': (['time'], rel_time),
                'deflection_savgol': (['time'], defl_savitz),
                'displacement': (['time'], displacement),
                **plateau_data
            }
            
            # Create coordinates
            coords = {
                'time': time_coords,
                'plateau': plateau_coords,
            }
            
            # Get file metadata
            filemetadata = result.get('filemetadata', {})
            filename = os.path.basename(result['filename'])
            
            # Create Dataset
            ds = xr.Dataset(
                data_vars=data_vars,
                coords=coords,
                attrs={
                    'title': f'Tether Analysis Results - {filename}',
                    'description': 'Analysis results from single TDMS file tether analysis',
                    'source_file': result['filename'],
                    'source_filename': filename,
                    'creation_timestamp': timestamp,
                    'creation_date': datetime.datetime.now().isoformat(),
                    'software': 'Tether Analysis GUI v2',
                    'total_plateaus': len(plateaus),
                    'total_data_points': n_points,
                    'sampling_rate_retract': result.get('relative_SR_ret'),
                    'contact_point_index': result.get('index_first_positive'),
                    'velocity_metadata_um_s': result.get('velocity_metadata'),
                    'velocity_calc_um_s': result.get('velocity_calc_um_s'),
                    'data_format_version': '1.0',
                }
            )
            
            # Add comprehensive attributes to data variables
            ds['time'].attrs = {
                'long_name': 'Relative time from contact point',
                'units': 'seconds',
                'description': 'Time array starting from detected contact point'
            }
            
            ds['deflection_savgol'].attrs = {
                'long_name': 'Savitzky-Golay filtered deflection',
                'units': 'N',
                'description': 'Deflection signal after tilt correction and Savitzky-Golay smoothing',
                'processing': 'Tilt corrected, contact point normalized, Savitzky-Golay filtered'
            }
            
            ds['displacement'].attrs = {
                'long_name': 'Displacement from contact point',
                'units': 'm',
                'description': 'Z-piezo displacement normalized to contact point (0 = contact)'
            }
            
            if len(df_plat) > 0:
                ds['plateau_avg_force'].attrs = {
                    'long_name': 'Average force per plateau',
                    'units': 'N',
                    'description': 'Mean deflection force calculated for each detected plateau'
                }
                
                ds['plateau_delta_avg'].attrs = {
                    'long_name': 'Force difference between plateaus',
                    'units': 'N',
                    'description': 'Force difference between current and next plateau'
                }
                
                ds['plateau_velocity_calc'].attrs = {
                    'long_name': 'Calculated velocity per plateau',
                    'units': 'μm/s',
                    'description': 'Velocity calculated from linear regression of displacement vs time for each plateau'
                }
            
            # Add file metadata as global attributes if available
            if filemetadata:
                ds.attrs.update({
                    'spring_constant_N_per_m': filemetadata.get('spring_const_Nbym'),
                    'deflection_sensitivity_nm_per_V': filemetadata.get('defl_sens_nmbyV'),
                    'height_channel': filemetadata.get('height_channel_key'),
                })
            
            # Save the dataset
            xarray_path = base_path.replace('.csv', '_analysis_results.nc')
            ds.to_netcdf(xarray_path, format='NETCDF4')
            
            return xarray_path
            
        except Exception as e:
            print(f"Warning: Could not export analysis results to xarray: {e}")
            return None
    
    def load_session(self):
        """Load a previously saved session file with per-file parameters"""
        try:
            # Open file dialog to select session CSV file
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Load Tether Analysis Session", 
                self.root_dir, 
                "CSV files (*.csv);;All files (*.*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Show dialog to choose load options
            dialog = LoadSessionDialog(self)
            dialog.setModal(True)  # Make sure dialog is modal
            dialog.raise_()  # Bring to front
            dialog.activateWindow()  # Activate the window
            if dialog.exec_() != QDialog.Accepted:
                return  # User cancelled the options dialog
            
            load_option = dialog.get_selected_option()
            
            # Load the CSV file
            df_session = pd.read_csv(file_path)
            
            # Validate the CSV format
            required_columns = ['local_file_path', 'file_name', 'bool_good_curve']
            if not all(col in df_session.columns for col in required_columns):
                self.status_label.setText("Error: Invalid session file format")
                return
            
            # Check if session has per-file parameters and plateau selections
            has_file_parameters = 'file_parameters' in df_session.columns
            has_plateau_selections = 'plateau_selections' in df_session.columns
            
            # Convert bool_good_curve to numeric to ensure proper filtering
            df_session['bool_good_curve'] = pd.to_numeric(df_session['bool_good_curve'], errors='coerce').fillna(0).astype(int)
            
            # Filter files based on user selection
            if load_option == "good":
                df_session = df_session[df_session['bool_good_curve'] == 1]
            elif load_option == "bad":
                df_session = df_session[df_session['bool_good_curve'] == 0]
            # For "all", no filtering needed
            
            if len(df_session) == 0:
                self.status_label.setText(f"Error: No {load_option} files found in session")
                return
            
            # Check if files still exist and load parameters
            existing_files = []
            existing_names = []
            existing_good_curve = []
            missing_files = []
            loaded_file_parameters = {}
            loaded_plateau_selections = {}
            
            for _, row in df_session.iterrows():
                file_path_row = row['local_file_path']
                if os.path.exists(file_path_row):
                    existing_files.append(file_path_row)
                    existing_names.append(row['file_name'])
                    existing_good_curve.append(int(row['bool_good_curve']))
                    
                    # Load per-file parameters if available
                    if has_file_parameters and pd.notna(row['file_parameters']):
                        try:
                            file_params = json.loads(row['file_parameters'])
                            loaded_file_parameters[file_path_row] = file_params
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"Warning: Could not load parameters for {row['file_name']}: {e}")
                            # Use default parameters
                            loaded_file_parameters[file_path_row] = self.get_default_parameters()
                    else:
                        # Use default parameters if no saved parameters
                        loaded_file_parameters[file_path_row] = self.get_default_parameters()
                    
                    # Load plateau selections if available
                    if has_plateau_selections and pd.notna(row['plateau_selections']):
                        try:
                            plateau_selections = json.loads(row['plateau_selections'])
                            loaded_plateau_selections[file_path_row] = plateau_selections
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"Warning: Could not load plateau selections for {row['file_name']}: {e}")
                            # Use empty selection list
                            loaded_plateau_selections[file_path_row] = []
                    else:
                        # Use empty selection list if no saved selections
                        loaded_plateau_selections[file_path_row] = []
                else:
                    missing_files.append(row['file_name'])
            
            if not existing_files:
                self.status_label.setText(f"Error: No {load_option} files from session found")
                return
            
            # Clear current file list
            self.listview.clear()
            
            # Load the session files
            self.file_path = existing_files
            self.file = existing_names
            self.bool_good_curve = np.array(existing_good_curve)
            self.file_parameters = loaded_file_parameters
            self.plateau_selections = loaded_plateau_selections
            
            # Populate the file list and apply colors
            self.listview.addItems(self.file)
            for i, is_good in enumerate(self.bool_good_curve):
                item = self.listview.item(i)
                if is_good == 1:
                    item.setBackground(QColor(0, 255, 0))  # Green for good
                elif is_good == 0:
                    item.setBackground(QColor(255, 0, 0))  # Red for bad
            
            # Set to first file
            self.index = 0
            self.listview.setCurrentRow(self.index)
            
            # Load parameters for the first file
            self.load_parameters_for_current_file()
            
            # Update status and results text
            good_count = int(np.sum(self.bool_good_curve))
            total_count = len(self.bool_good_curve)
            
            # Format option name for display
            option_display = {
                "all": "All files",
                "good": "Good files only", 
                "bad": "Bad files only"
            }[load_option]
            
            session_info = f"Session loaded: {os.path.basename(file_path)}\n"
            session_info += f"Load option: {option_display}\n"
            session_info += f"Files loaded: {total_count}\n"
            session_info += f"Good files: {good_count}\n"
            session_info += f"Bad files: {total_count - good_count}\n"
            
            if has_file_parameters:
                session_info += "Per-file parameters: Restored\n"
            else:
                session_info += "Per-file parameters: Using defaults (old session format)\n"
            
            if has_plateau_selections:
                session_info += "Plateau selections: Restored"
            else:
                session_info += "Plateau selections: Using defaults (all selected)"
            
            if missing_files:
                session_info += f"\n\nMissing files ({len(missing_files)}):\n"
                session_info += "\n".join(missing_files[:5])  # Show first 5 missing files
                if len(missing_files) > 5:
                    session_info += f"\n... and {len(missing_files) - 5} more"
            
            self.results_text.setText(session_info)
            
            # Automatically run analysis on first file
            QTimer.singleShot(200, self.run_analysis)
            
            self.status_label.setText(f"Loaded {option_display}: {good_count}/{total_count} good files")
            
        except Exception as e:
            self.status_label.setText(f"Error loading session: {str(e)}")
            self.results_text.setText(f"Error loading session: {str(e)}")


class LoadSessionDialog(QDialog):
    """Dialog for selecting which files to load from session"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_option = None
        self.setupUI()
        
    def setupUI(self):
        self.setWindowTitle("Load Session Options")
        self.setFixedSize(300, 250)
        self.setWindowModality(Qt.ApplicationModal)  # Make it modal
        
        # Center the dialog relative to parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        
        layout = QVBoxLayout(self)
        
        # Title label
        title = QLabel("Choose which files to load:")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Create radio buttons for options
        self.option_group = QGroupBox()
        option_layout = QVBoxLayout(self.option_group)
        
        self.button_group = QButtonGroup()
        
        self.all_files_radio = QRadioButton("All Files")
        self.all_files_radio.setChecked(True)  # Default selection
        self.button_group.addButton(self.all_files_radio, 0)
        option_layout.addWidget(self.all_files_radio)
        
        self.good_files_radio = QRadioButton("Good Files Only")
        self.button_group.addButton(self.good_files_radio, 1)
        option_layout.addWidget(self.good_files_radio)
        
        self.bad_files_radio = QRadioButton("Bad Files Only")
        self.button_group.addButton(self.bad_files_radio, 2)
        option_layout.addWidget(self.bad_files_radio)
        
        layout.addWidget(self.option_group)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
    def get_selected_option(self):
        """Get the selected option"""
        checked_id = self.button_group.checkedId()
        if checked_id == 0:
            return "all"
        elif checked_id == 1:
            return "good"
        elif checked_id == 2:
            return "bad"
        return "all"  # Default fallback


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set default directory - change this to your data directory
    root_dir = '/Users/evillz/Data/article/2025_07_01_THP1_phd'
    
    # Create and show GUI
    gui = TetherAnalysisGUI(root_dir)
    gui.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()