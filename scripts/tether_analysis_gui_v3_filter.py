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
# import xarray as xr
import sys
import os
import json
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QCheckBox, QTextEdit, QTreeView,
                             QShortcut, QFileSystemModel, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QDialog, QRadioButton, QButtonGroup,
                             QMainWindow, QAction)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QDir, QObject
from PyQt5.QtGui import QKeySequence, QFont
import pyqtgraph as pg
from pyfmreader import loadfile
import datetime

# Import tether analysis functions
from tether_script import process_single_file
from parameter_tree_widget import ParameterTreeWidget

class TetherAnalysisGUI(QMainWindow):
    def __init__(self, root_dir, *args, **kwargs):
        QMainWindow.__init__(self, *args, **kwargs)
        self.i_file_path = 0
        self.file_path = []
        self.index = 0
        self.current_analysis_result = None

        # Initialize joystick with error handling
        try:
            self.joystick_handler = JoystickHandler(self)
            self.joystick_handler.buttonPressed.connect(self.handle_joystick_button)
            print("Joystick handler initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize joystick: {e}")
            self.joystick_handler = None

        # Initialize per-file parameter storage (empty at start)
        self.file_parameters = {}
        # Initialize plateau selection storage
        self.plateau_selections = {}
        
        # Initialize timer for threshold updates (debouncing)
        self.threshold_update_timer = QTimer()
        self.threshold_update_timer.setSingleShot(True)
        self.threshold_update_timer.timeout.connect(self.delayed_threshold_analysis)
        self.pending_threshold_value = None
        
        self.setupUI()
        # self.setupJoystick()
        self.setupShortcuts()
        
        # Initialize parameter status
        self.param_widget.update_parameter_status()
        
        # Set initial directory
        self.root_dir = root_dir
        self.dirModel.setRootPath(root_dir)
        self.treeview.setRootIndex(self.dirModel.index(root_dir))
        
    def setupUI(self):
        """Setup the user interface"""
        self.setWindowTitle("Tether Analysis GUI V3")
        self.setGeometry(100, 100, 1600, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - File browser
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("File Browser"))
        
        self.treeview = QTreeView()
        # Replace QListWidget with QTableWidget for sortable file list
        self.file_table = QTableWidget()
        self.setup_file_table()
        
        left_panel.addWidget(self.treeview, 1)
        left_panel.addWidget(self.file_table, 1)
        
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
        self.displacement_check = QCheckBox("Displacement")
        self.displacement_check.setChecked(False)
        self.displacement_check.setToolTip("Show displacement (m) instead of time (s) on X-axis")
        self.snap_check = QCheckBox("Snap")
        self.snap_check.setChecked(False) 
        self.snap_check.setToolTip("Auto-zoom: Y-axis to max+15%, X-axis from -0.55s to 30% of last plateau")
        
        plot_controls.addWidget(self.raw_check)
        plot_controls.addWidget(self.processed_check)
        plot_controls.addWidget(self.plateaus_check)
        plot_controls.addWidget(self.displacement_check)
        plot_controls.addWidget(self.snap_check)
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
        
        # Add analysis plot selection controls
        analysis_plot_controls = QHBoxLayout()
        analysis_plot_label = QLabel("Analysis Plot:")
        analysis_plot_label.setStyleSheet("QLabel { font-weight: bold; }")
        analysis_plot_controls.addWidget(analysis_plot_label)
        
        # Radio buttons for plot selection
        self.plot_type_group = QButtonGroup()
        self.derivative_radio = QRadioButton("Derivative Analysis")
        self.fourier_radio = QRadioButton("Fourier Spectrum")
        self.derivative_radio.setChecked(True)  # Default selection
        
        self.plot_type_group.addButton(self.derivative_radio, 0)
        self.plot_type_group.addButton(self.fourier_radio, 1)
        
        # Connect radio button signals
        self.derivative_radio.toggled.connect(self.update_analysis_plot)
        self.fourier_radio.toggled.connect(self.update_analysis_plot)
        
        analysis_plot_controls.addWidget(self.derivative_radio)
        analysis_plot_controls.addWidget(self.fourier_radio)
        analysis_plot_controls.addStretch()
        
        results_text_layout.addLayout(analysis_plot_controls)
        
        # Add analysis plot widget
        self.analysis_plotview = pg.PlotWidget()
        self.analysis_plotview.setLabel('left', 'dy/dx', units='N/m')
        self.analysis_plotview.setLabel('bottom', 'Displacement', units='m')
        self.analysis_plotview.showGrid(x=True, y=True)
        self.analysis_plotview.setMaximumHeight(200)
        self.analysis_plotview.setMinimumHeight(150)
        # Add legend for analysis plot
        self.analysis_legend = self.analysis_plotview.addLegend(offset=(10, 10))
        self.analysis_legend.anchor = (1, 0)  # Top-right anchor
        results_text_layout.addWidget(self.analysis_plotview)
    # Removed interactive threshold drag handler
        
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
        
        # Right panel - Parameters
        self.param_widget = ParameterTreeWidget()
        self.param_widget.setFixedWidth(300)
        
        # Add panels to main layout - removed navigation buttons
        main_layout.addWidget(left_widget)
        main_layout.addWidget(center_widget, 1)
        main_layout.addWidget(self.param_widget)
        
        # Setup file system model
        self.dirModel = QFileSystemModel()
        self.dirModel.setRootPath(QDir.rootPath())
        self.dirModel.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        self.treeview.setModel(self.dirModel)
        
        # Connect signals
        self.treeview.clicked.connect(self.on_clicked_folder)
        self.file_table.cellClicked.connect(self.on_file_table_click)
        self.param_widget.parametersChanged.connect(self.on_parameters_changed)
        
        # Navigation buttons removed - functionality available via keyboard shortcuts and menu
        # Previous/Next: Arrow keys ↑/↓ or menu items
        # Good/Bad: G/B keys or menu items
        # Analysis: Enter key or menu items
        # Load Session: L key or menu items
        
        # Connect plot checkboxes
        self.raw_check.stateChanged.connect(self.update_plot_display)
        self.processed_check.stateChanged.connect(self.update_plot_display)
        self.plateaus_check.stateChanged.connect(self.update_plot_display)
        self.displacement_check.stateChanged.connect(self.update_plot_display)
        self.snap_check.stateChanged.connect(self.update_plot_display)
        
        # Setup menu bar (after all widgets are created)
        self.setupMenuBar()
        
    def setupMenuBar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Change Directory action
        change_dir_action = QAction('Change Directory...', self)
        change_dir_action.setShortcut('Ctrl+D')
        change_dir_action.setStatusTip('Change the root directory for TDMS files')
        change_dir_action.triggered.connect(self.change_directory)
        file_menu.addAction(change_dir_action)
        
        file_menu.addSeparator()
        
        # Load Session action
        load_session_action = QAction('Load Session...', self)
        load_session_action.setShortcut('Ctrl+L')
        load_session_action.setStatusTip('Load a previously saved analysis session (Ctrl+L or L key)')
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)
        
        # Save Session action
        save_session_action = QAction('Save Session...', self)
        save_session_action.setShortcut('Ctrl+S')
        save_session_action.setStatusTip('Save current analysis session (Ctrl+S or S key)')
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit the application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Analysis menu
        analysis_menu = menubar.addMenu('Analysis')
        
        # Run Analysis action
        run_analysis_action = QAction('Run Analysis', self)
        # Remove shortcut to avoid conflict with QShortcut (Enter key)
        run_analysis_action.setStatusTip('Run analysis on current file (Enter key)')
        run_analysis_action.triggered.connect(self.run_analysis)
        analysis_menu.addAction(run_analysis_action)
        
        # Batch Analysis action
        batch_analysis_action = QAction('Run Batch Analysis...', self)
        batch_analysis_action.setShortcut('Ctrl+B')
        batch_analysis_action.setStatusTip('Run analysis on all files in session')
        batch_analysis_action.triggered.connect(self.run_batch_analysis_on_session_files)
        analysis_menu.addAction(batch_analysis_action)
        
        # Rerun with Updated Filters action
        rerun_filters_action = QAction('Rerun with Updated Filters', self)
        rerun_filters_action.setShortcut('Ctrl+R')
        rerun_filters_action.setStatusTip('Rerun analysis with current filter parameters')
        rerun_filters_action.triggered.connect(self.trigger_reanalysis)
        analysis_menu.addAction(rerun_filters_action)
        
        analysis_menu.addSeparator()
        
        # Mark as Good action
        mark_good_action = QAction('Mark as Good', self)
        # Remove shortcut to avoid conflict with QShortcut (G key)
        mark_good_action.setStatusTip('Mark current file as good (G key)')
        mark_good_action.triggered.connect(self.file_good)
        analysis_menu.addAction(mark_good_action)
        
        # Mark as Bad action
        mark_bad_action = QAction('Mark as Bad', self)
        # Remove shortcut to avoid conflict with QShortcut (B key)
        mark_bad_action.setStatusTip('Mark current file as bad (B key)')
        mark_bad_action.triggered.connect(self.file_bad)
        analysis_menu.addAction(mark_bad_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Toggle plot options
        toggle_raw_action = QAction('Toggle Raw Data', self)
        toggle_raw_action.setCheckable(True)
        toggle_raw_action.setChecked(self.raw_check.isChecked())
        toggle_raw_action.triggered.connect(lambda checked: self.raw_check.setChecked(checked))
        view_menu.addAction(toggle_raw_action)
        
        toggle_processed_action = QAction('Toggle Processed Data', self)
        toggle_processed_action.setCheckable(True) 
        toggle_processed_action.setChecked(self.processed_check.isChecked())
        toggle_processed_action.triggered.connect(lambda checked: self.processed_check.setChecked(checked))
        view_menu.addAction(toggle_processed_action)
        
        toggle_plateaus_action = QAction('Toggle Plateaus', self)
        toggle_plateaus_action.setCheckable(True)
        toggle_plateaus_action.setChecked(self.plateaus_check.isChecked())
        toggle_plateaus_action.triggered.connect(lambda checked: self.plateaus_check.setChecked(checked))
        view_menu.addAction(toggle_plateaus_action)
        
        view_menu.addSeparator()
        
        # Auto-reanalysis option for interactive filter controls
        self.auto_reanalysis_action = QAction('Auto-reanalysis on Filter Changes', self)
        self.auto_reanalysis_action.setCheckable(True)
        self.auto_reanalysis_action.setChecked(False)  # Default to False for performance
        self.auto_reanalysis_action.setStatusTip('Automatically rerun analysis when filter parameters change in Fourier plot')
        view_menu.addAction(self.auto_reanalysis_action)
        
        # Status bar
        self.statusBar().showMessage('Ready')
        
    def change_directory(self):
        """Change the root directory for TDMS files"""
        try:
            # Open directory selection dialog
            new_directory = QFileDialog.getExistingDirectory(
                self,
                "Select Root Directory for TDMS Files",
                self.root_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if new_directory:
                # Update root directory
                old_directory = self.root_dir
                self.root_dir = new_directory
                
                # Update directory model
                self.dirModel.setRootPath(new_directory)
                self.treeview.setRootIndex(self.dirModel.index(new_directory))
                
                # Clear current file list
                self.file_table.clearContents()
                self.file_table.setRowCount(0)
                self.file_path = []
                self.file = []
                self.bool_good_curve = np.array([])
                self.file_parameters = {}
                self.plateau_selections = {}
                
                # Clear current analysis
                self.current_analysis_result = None
                self.plotview.clear()
                self.analysis_plotview.clear()
                
                # Update status
                self.status_label.setText("Directory changed - select a folder to load TDMS files")
                self.results_text.setText(f"Directory changed from:\n{old_directory}\n\nTo:\n{new_directory}\n\nClick a folder to start analyzing TDMS files.")
                self.statusBar().showMessage(f"Changed directory to: {new_directory}")
                
        except Exception as e:
            self.status_label.setText(f"Error changing directory: {str(e)}")
            self.statusBar().showMessage(f"Error: {str(e)}")
        
    def setupShortcuts(self):
        """Setup keyboard shortcuts"""
        # Create shortcuts with proper context to work regardless of widget focus
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_good = QShortcut(QKeySequence(Qt.Key_G), self)
        self.shortcut_bad = QShortcut(QKeySequence(Qt.Key_B), self)
        self.shortcut_analyze = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut_save = QShortcut(QKeySequence(Qt.Key_S), self)
        self.shortcut_load = QShortcut(QKeySequence(Qt.Key_L), self)
        
        # Set context to work across the entire window
        self.shortcut_next.setContext(Qt.ApplicationShortcut)
        self.shortcut_prev.setContext(Qt.ApplicationShortcut)
        self.shortcut_good.setContext(Qt.ApplicationShortcut)
        self.shortcut_bad.setContext(Qt.ApplicationShortcut)
        self.shortcut_analyze.setContext(Qt.ApplicationShortcut)
        self.shortcut_save.setContext(Qt.ApplicationShortcut)
        self.shortcut_load.setContext(Qt.ApplicationShortcut)
        
        # Connect shortcuts
        self.shortcut_next.activated.connect(self.file_next)
        self.shortcut_prev.activated.connect(self.file_prev)
        self.shortcut_good.activated.connect(self.file_good)
        self.shortcut_bad.activated.connect(self.file_bad)
        self.shortcut_analyze.activated.connect(self.run_analysis)
        self.shortcut_save.activated.connect(self.save_session)
        self.shortcut_load.activated.connect(self.load_session)
        
        print("✓ Keyboard shortcuts configured:")
        print("  ↑/↓: Navigate files")
        print("  G: Mark as Good")
        print("  B: Mark as Bad") 
        print("  Enter: Run Analysis")
        print("  S: Save Session")
        print("  L: Load Session")
        
    def setup_file_table(self):
        """Setup the file table with sortable columns"""
        # Define columns for file information
        headers = ['Filename', 'Status', 'Date Taken', 'Date Modified', 'Size (KB)', 'Analysis Status']
        self.file_table.setColumnCount(len(headers))
        self.file_table.setHorizontalHeaderLabels(headers)
        
        # Enable sorting
        self.file_table.setSortingEnabled(True)
        
        # Set table properties
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Adjust column widths
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Filename stretches
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
    def extract_date_from_filename(self, filename):
        """Extract date taken from filename timestamp if available"""
        try:
            # Look for pattern like "2025.07.01_16.49.19.87" in filename
            
            # Pattern: YYYY.MM.DD_HH.MM.SS.MS
            pattern = r'(\d{4})\.(\d{2})\.(\d{2})_(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})'
            match = re.search(pattern, filename)
            
            if match:
                year, month, day, hour, minute, second, millisecond = match.groups()
                
                # Format as readable datetime string
                date_str = f"{year}-{month}-{day} {hour}:{minute}:{second}.{millisecond}"
                return date_str
            else:
                return None  # No timestamp found
                
        except Exception as e:
            print(f"Warning: Could not extract date from filename {filename}: {e}")
            return None
    
    def on_file_table_click(self, row, column):
        """Handle file table selection"""
        # Save parameters for previous file
        self.save_parameters_for_current_file()
        
        self.index = row
        # Clear previous analysis result
        self.current_analysis_result = None
        
        # Load parameters for the new file
        self.load_parameters_for_current_file()
        
        # Automatically run analysis after file selection
        QTimer.singleShot(100, self.run_analysis)
        
    def handle_joystick_button(self, button_idx):
        """Map button indices to actions"""
        print(f"Joystick button {button_idx} pressed")
        if button_idx == 0:  # A button
            self.save_session()
            print("Save session triggered")
        elif button_idx == 1:  # B button  
            self.run_analysis()
            print("Run analysis triggered")
        elif button_idx == 2:  # X button
            self.file_good()
            print("File marked as good")
        elif button_idx == 3:  # Y button
            self.file_bad()
            print("File marked as bad")
        elif button_idx == 11:  # D-pad up
            self.file_prev()
            print("Previous file")
        elif button_idx == 12:  # D-pad down
            self.file_next()
            print("Next file")
        elif button_idx == 9:  # Left shoulder (L1)
            self.load_session()
            print("Load session triggered")
        elif button_idx == 10:  # Right shoulder (R1)
            # Toggle processed data display
            self.processed_check.setChecked(not self.processed_check.isChecked())
            print("Toggled processed data display")
        elif button_idx == 4:  # Left trigger (L2)
            # Toggle plateau display
            self.plateaus_check.setChecked(not self.plateaus_check.isChecked())
            print("Toggled plateau display")
        elif button_idx == 5:  # Right trigger (R2)
            # Toggle snap zoom
            self.snap_check.setChecked(not self.snap_check.isChecked())
            print("Toggled snap zoom")
    
    def find_tdms_files(self, root_dir):
        """Find all TDMS files and populate the sortable table"""
        from datetime import datetime
        
        file_data = []
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
                    
                    # Get file statistics
                    try:
                        stat_info = os.stat(full_path)
                        file_size_kb = stat_info.st_size / 1024
                        mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                        date_str = mod_time.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        file_size_kb = 0
                        date_str = "Unknown"
                    
                    # Extract date taken from filename
                    date_taken = self.extract_date_from_filename(filename)
                    
                    file_data.append({
                        'filename': filename,
                        'full_path': full_path,
                        'status': 'New',  # Will be updated when files are marked
                        'date_taken': date_taken,
                        'date_modified': date_str,
                        'size_kb': file_size_kb,
                        'analysis_status': 'Not Analyzed'
                    })
        
        # Store data for later use
        self.file = file_name
        self.file_path = file_path
        self.file_data = file_data
        self.bool_good_curve = np.zeros(len(file_path))
        self.file_parameters = {}
        self.plateau_selections = {}  # Reset plateau selections for new directory
        
        # Populate the table
        self.populate_file_table()
            
    def populate_file_table(self):
        """Populate the file table with current file data"""
        if not hasattr(self, 'file_data'):
            return
            
        self.file_table.setRowCount(len(self.file_data))
        
        for row, file_info in enumerate(self.file_data):
            # Filename
            self.file_table.setItem(row, 0, QTableWidgetItem(file_info['filename']))
            
            # Status (Good/Bad/New)
            status_item = QTableWidgetItem(file_info['status'])
            if file_info['status'] == 'Good':
                status_item.setBackground(Qt.green)
            elif file_info['status'] == 'Bad':
                status_item.setBackground(Qt.red)
            self.file_table.setItem(row, 1, status_item)
            
            # Date Taken (from filename)
            date_taken = file_info.get('date_taken', None)
            if date_taken:
                self.file_table.setItem(row, 2, QTableWidgetItem(date_taken))
            else:
                # Empty cell if no date found in filename
                self.file_table.setItem(row, 2, QTableWidgetItem(""))
            
            # Date Modified
            self.file_table.setItem(row, 3, QTableWidgetItem(file_info['date_modified']))
            
            # Size
            size_item = QTableWidgetItem(f"{file_info['size_kb']:.1f}")
            size_item.setData(Qt.UserRole, file_info['size_kb'])  # For proper numeric sorting
            self.file_table.setItem(row, 4, size_item)
            
            # Analysis Status
            self.file_table.setItem(row, 5, QTableWidgetItem(file_info['analysis_status']))
        
        # Resize columns to content
        self.file_table.resizeColumnsToContents()
            
    def on_clicked_folder(self, index):
        """Handle folder selection"""
        self.save_session()
        self.file_table.clearContents()
        self.file_table.setRowCount(0)
        
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        
        # Get directory information for display
        directory_name = os.path.basename(path)
        directory_path = path
        
        self.find_tdms_files(path)
        
        if self.file:
            self.index = 0
            self.file_table.selectRow(self.index)
            # Load parameters for the first file
            self.load_parameters_for_current_file()
            
            # Calculate directory statistics
            total_files = len(self.file)
            total_size_mb = sum(info['size_kb'] for info in self.file_data) / 1024
            
            # Get date range from files
            dates = [info.get('date_taken', '') for info in self.file_data if info.get('date_taken')]
            date_range = ""
            if dates:
                dates_sorted = sorted([d for d in dates if d])
                if dates_sorted:
                    earliest = dates_sorted[0][:10]  # Just the date part
                    latest = dates_sorted[-1][:10]
                    if earliest == latest:
                        date_range = f"Date: {earliest}"
                    else:
                        date_range = f"Date range: {earliest} to {latest}"
            
            # Display directory information
            directory_info = f"""Directory Loaded: {directory_name}

📁 Path: {directory_path}

📊 TDMS Files Statistics:
• Total files: {total_files}
• Total size: {total_size_mb:.1f} MB
• Status: Ready for analysis
{date_range}

🎯 Controls:
• Click files to analyze
• ↑/↓: Navigate files
• G/B: Mark Good/Bad
• Enter: Run analysis

Current file: {os.path.basename(self.file_path[self.index])}"""
            
            self.results_text.setText(directory_info)
            
            # Automatically run analysis on first file
            QTimer.singleShot(200, self.run_analysis)
            self.status_label.setText(f"Loaded {len(self.file)} TDMS files from {directory_name}")
        else:
            # No TDMS files found - show directory info anyway
            no_files_info = f"""Directory: {directory_name}

📁 Path: {directory_path}

⚠️  No TDMS files found in this directory.

The directory exists but contains no .tdms files.
Try selecting a different folder that contains
TDMS data files for analysis.

💡 Tip: Look for folders with experimental data
that contain files ending in .tdms extension."""
            
            self.results_text.setText(no_files_info)
            self.status_label.setText(f"No TDMS files found in {directory_name}")
            
    def file_good(self):
        """Mark current file as good"""
        print("DEBUG: file_good() called - G key pressed")
        if self.file_path and len(self.file_path) > 0 and self.index < len(self.file_path):
            self.bool_good_curve[self.index] = 1
            self.update_file_status(self.index, 'Good', Qt.green)
            self.status_label.setText("File marked as GOOD")
            self.file_next()
        else:
            print("DEBUG: Cannot mark file as good - no files loaded or invalid index")
            self.status_label.setText("No files loaded to mark as good")
            
    def file_bad(self):
        """Mark current file as bad"""
        print("DEBUG: file_bad() called - B key pressed")
        if self.file_path and len(self.file_path) > 0 and self.index < len(self.file_path):
            self.bool_good_curve[self.index] = 0
            self.update_file_status(self.index, 'Bad', Qt.red)
            self.status_label.setText("File marked as BAD")
            self.file_next()
        else:
            print("DEBUG: Cannot mark file as bad - no files loaded or invalid index")
            self.status_label.setText("No files loaded to mark as bad")
    
    def update_file_status(self, file_index, status, color):
        """Update file status in the table"""
        if hasattr(self, 'file_data') and file_index < len(self.file_data):
            self.file_data[file_index]['status'] = status
            # Update the status column in the table
            status_item = QTableWidgetItem(status)
            status_item.setBackground(color)
            self.file_table.setItem(file_index, 1, status_item)
            
    def file_next(self):
        """Navigate to next file"""
        print("DEBUG: file_next() called - Down arrow pressed")
        if self.file_path and len(self.file_path) > 0:
            # Save parameters for current file
            self.save_parameters_for_current_file()
            
            self.index = (self.index + 1) % len(self.file_path)
            self.file_table.selectRow(self.index)
            # Clear previous analysis result
            self.current_analysis_result = None
            
            # Load parameters for the new file
            self.load_parameters_for_current_file()
            
            # Automatically run analysis after navigation
            QTimer.singleShot(100, self.run_analysis)
        else:
            print("DEBUG: Cannot navigate - no files loaded")
            self.status_label.setText("No files loaded to navigate")
            
    def file_prev(self):
        """Navigate to previous file"""
        print("DEBUG: file_prev() called - Up arrow pressed")
        if self.file_path and len(self.file_path) > 0:
            # Save parameters for current file
            self.save_parameters_for_current_file()
            
            self.index = (self.index - 1) % len(self.file_path)
            self.file_table.selectRow(self.index)
            # Clear previous analysis result
            self.current_analysis_result = None
            
            # Load parameters for the new file
            self.load_parameters_for_current_file()
            
            # Automatically run analysis after navigation
            QTimer.singleShot(100, self.run_analysis)
        else:
            print("DEBUG: Cannot navigate - no files loaded")
            self.status_label.setText("No files loaded to navigate")
            
            
    def update_analysis_status(self, file_index, status):
        """Update analysis status in the table"""
        if hasattr(self, 'file_data') and file_index < len(self.file_data):
            self.file_data[file_index]['analysis_status'] = status
            # Update the analysis status column in the table (column 5 now)
            self.file_table.setItem(file_index, 5, QTableWidgetItem(status))
            
    def on_parameters_changed(self, params):
        """Handle parameter changes - automatically run analysis"""
        if self.file_path and len(self.file_path) > 0:
            # Only run analysis if we have a current file loaded
            if hasattr(self, 'current_analysis_result') or hasattr(self, 'current_file_loaded'):
                print("Parameters changed - running automatic analysis...")
                self.run_analysis()
            
    def run_analysis(self):
        """Run tether analysis on current file"""
        if not self.file_path:
            return
            
        try:
            filename = self.file_path[self.index]
            params = self.param_widget.getCurrentParameters()
            
            self.status_label.setText("Running analysis...")
            self.update_analysis_status(self.index, "Analyzing...")
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
            self.update_analysis_status(self.index, f"Analyzed ({plateau_count} plateaus)")
            self.update_velocity_indicators(result)
            
        except Exception as e:
            self.status_label.setText(f"Analysis failed: {str(e)}")
            self.results_text.setText(f"Error: {str(e)}")
            self.update_analysis_status(self.index, "Analysis Failed")
            self.update_plateau_table(None)  # Clear table on error
            # Clear derivative plot on error
            if hasattr(self, 'derivative_plotview'):
                self.derivative_plotview.clear()
            
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
            'pl_threshold': 1e-9,  # In actual units (not nano scale)
            'pl_min_width_um': 1e-6,
            'last_num_plateaus': 7,
            'last_plateau_avg_percentage': 15,
            'max_offset': 100,
            'min_offset': 70,
            # Denoising parameters
            'enable_denoising': False,
            'denoise_w0': 0.1,
            'denoise_w1': 1.0,
            'butterworth_order': 5,
            'denoise_ranges': '[(1, 6)]',
            'denoise_remove_percent': 10,
            'denoise_remove_end_percent': 10,
            'denoise_interp': True
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
            
            # Temporarily block parameter change signals to prevent double analysis
            self.param_widget.blockSignals(True)
            
            # Update parameter widget with file-specific parameters
            self.param_widget.setParameters(file_params)
            
            # Re-enable signals
            self.param_widget.blockSignals(False)
            
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
    
    def get_displacement_from_time(self, result, time_array):
        """Convert time array to displacement array using velocity"""
        try:
            if 'velocity_calc_um_s' in result and result['velocity_calc_um_s']:
                velocity_um_s = result['velocity_calc_um_s']
                # Convert velocity from μm/s to m/s
                velocity_m_s = velocity_um_s * 1e-6
                # Calculate displacement: d = v * t
                displacement = velocity_m_s * time_array
                return displacement
            elif 'velocity_metadata' in result and result['velocity_metadata']:
                velocity_um_s = result['velocity_metadata']
                velocity_m_s = velocity_um_s * 1e-6
                displacement = velocity_m_s * time_array
                return displacement
            else:
                # Fallback: assume default velocity of 1 μm/s
                velocity_m_s = 1e-6
                displacement = velocity_m_s * time_array
                return displacement
        except Exception as e:
            print(f"Warning: Could not calculate displacement: {e}")
            # Return time array as fallback
            return time_array
    
    def get_x_axis_data(self, result, time_array):
        """Get appropriate x-axis data based on displacement checkbox"""
        if self.displacement_check.isChecked():
            return self.get_displacement_from_time(result, time_array)
        else:
            return time_array
    
    def set_plot_labels(self):
        """Set appropriate plot labels based on displacement mode"""
        self.plotview.setLabel('left', 'Deflection', units='N')
        if self.displacement_check.isChecked():
            self.plotview.setLabel('bottom', 'Displacement', units='m')
        else:
            self.plotview.setLabel('bottom', 'Time', units='s')
    
    def apply_snap_zoom(self, result):
        """Apply snap zoom based on analysis results"""
        if not self.snap_check.isChecked() or not result:
            return
        
        try:
            # Get data for zoom calculation
            defl_savitz = result.get('defl_savitz', [])
            
            plateaus = result.get('plateaus', [])
            if self.displacement_check.isChecked():
                x_axis = result.get('displacement', [])
            else :
                # Use time axis for snap zoom
                x_axis = result.get('rel_time', [])
            
            # zoom settings
            if plateaus != 0:
                start_idx, end_idx = plateaus[-1]  # last plateau
                average_idx = (start_idx + end_idx) // 2  # Integer division for index
                ten_percent_idx = (start_idx + end_idx) # 30% into the last plateau
                rel_time_snap_max = x_axis[average_idx] * 0.4  # Get time at 30% of last plateau
                if ten_percent_idx-1 < len(x_axis):
                    rel_time_snap_min = x_axis [ten_percent_idx-1] * 0.1
                else:
                    rel_time_snap_min = x_axis[-1] * 0.1

            if len(defl_savitz) == 0 or len(x_axis) == 0:
                return
            
            # Y-axis: max value + 15% more
            max_force = np.max(defl_savitz)
            y_max = max_force * 1.15
            y_min = np.min(defl_savitz) * 1.20  # Add some padding on bottom too
            
            # X-axis: from -0.55s to 30% of last plateau
            # x_start_time = rel_time_snap
            
            # # Find 30% position of last plateau
            # if plateaus and len(plateaus) > 0:
            #     last_plateau_start, last_plateau_end = plateaus[-1]
            #     # Get time at 30% into the last plateau
            #     plateau_30_percent_idx = int(last_plateau_start + 0.3 * (last_plateau_end - last_plateau_start))
            #     if plateau_30_percent_idx < len(rel_time):
            #         x_end_time = rel_time[plateau_30_percent_idx]
            #     else:
            #         x_end_time = rel_time[-1] * 0.8  # Fallback to 80% of total time
            # else:
            #     x_end_time = rel_time[-1] * 0.8  # Fallback to 80% of total time
            
            # # Convert to displacement if needed
            # if self.displacement_check.isChecked():
            #     x_start = self.get_displacement_from_time(result, np.array([x_start_time]))[0]
            #     x_end = self.get_displacement_from_time(result, np.array([x_end_time]))[0]
            # else:
            #     x_start = x_start_time
            #     x_end = x_end_time
            
            # Apply zoom
            self.plotview.setRange(xRange=[-(rel_time_snap_min), rel_time_snap_max], yRange=[y_min, y_max])
            print(f"Applied snap zoom - X: [{-rel_time_snap_min:.3f}, {rel_time_snap_max:.3f}], Y: [{y_min:.2e}, {y_max:.2e}]")
            
        except Exception as e:
            print(f"Warning: Could not apply snap zoom: {e}")
            
    def update_plot(self):
        """Update plot with raw data"""
        if not self.file_path:
            return
            
        try:
            self.i_file_path = self.file_path[self.index]
            self.plotview.clear()
            legend = self.plotview.addLegend(offset=(30, 30))
            legend.anchor = (1, 0)  # Top-right anchor
            
            # Set appropriate axis labels
            self.plotview.setLabel('left', 'Deflection', units='N')
            if self.displacement_check.isChecked():
                self.plotview.setLabel('bottom', 'Displacement', units='m')
            else:
                self.plotview.setLabel('bottom', 'Time', units='s')
            
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
                        # For raw data, we can't get displacement without analysis results
                        # So use time for now, displacement will work with processed data
                        x_data = time_array
                        self.plotview.plot(x_data, ret_deflection, 
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
        
        # Set appropriate axis labels
        self.set_plot_labels()
        
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
                        
                        # Get appropriate x-axis data (time or displacement)
                        x_data = self.get_x_axis_data(result, time_array)
                        
                        self.plotview.plot(x_data, ret_deflection,
                                         pen=pg.mkPen(color='lightblue', width=1),
                                         name='Raw Data')
                        break
            
            # Plot processed data
            if self.processed_check.isChecked():
                rel_time = result['rel_time']
                defl_savitz = result['defl_savitz']
                
                # Get appropriate x-axis data (time or displacement)
                x_data = self.get_x_axis_data(result, rel_time)
                
                self.plotview.plot(x_data, defl_savitz,
                                 pen=pg.mkPen(color='blue', width=2),
                                 name='Processed Data')
                
                # Plot idx_max marker if available in df_data
                if 'df_data' in result and 'idx_max' in result['df_data']:
                    idx_max = result['df_data']['idx_max']
                    if idx_max < len(defl_savitz) and idx_max < len(x_data):
                        x_max = x_data[idx_max]
                        y_max = defl_savitz[idx_max]
                        
                        self.plotview.plot([x_max], [y_max],
                                         pen=None, symbol='o', symbolSize=10,
                                         symbolBrush='red', symbolPen='darkred',
                                         name='Max Force')
            
            # Plot plateaus
            if self.plateaus_check.isChecked() and result['plateaus']:
                rel_time = result['rel_time']
                defl_savitz = result['defl_savitz']
                plateaus = result['plateaus']
                df_plat = result['df_plat']
                
                # Get appropriate x-axis data (time or displacement)
                x_data = self.get_x_axis_data(result, rel_time)
                
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
                        self.plotview.plot(x_data[start:end], defl_savitz[start:end],
                                         pen=pg.mkPen(color=color, width=3),
                                         name=f'Plateau {i+1}')
                        
                        # Average line
                        plateau_avg = np.mean(defl_savitz[start:end])
                        self.plotview.plot([x_data[start], x_data[end-1]],
                                         [plateau_avg, plateau_avg],
                                         pen=pg.mkPen(color=color, width=2, style=Qt.DashLine),
                                         name=f'Avg {i+1}')
                        
                        # Plot plateau markers
                        if i < len(df_plat['plateau_avg_idx']):
                            idx = df_plat['plateau_avg_idx'].iloc[i]
                            self.plotview.plot([x_data[idx]], [defl_savitz[idx]],
                                             pen=None, symbol='o', symbolSize=8,
                                             symbolBrush=color,
                                             name=f'Center {i+1}')
                        
                        displayed_count += 1
            
            # Apply snap zoom if enabled
            self.apply_snap_zoom(result)
            
            # Check for Fourier data availability and enable/disable radio button
            fourier_available = result and 'fourier_data' in result and bool(result['fourier_data'])
            self.fourier_radio.setEnabled(fourier_available)
            
            # If Fourier data is not available and Fourier is selected, switch to derivative
            if not fourier_available and self.fourier_radio.isChecked():
                self.derivative_radio.setChecked(True)
            
            # Update analysis plot
            self.update_analysis_plot()
       
                                     
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
            # Clear analysis plot when no analysis results
            if hasattr(self, 'analysis_plotview'):
                self.analysis_plotview.clear()
            # Disable Fourier radio button when no analysis results
            self.fourier_radio.setEnabled(False)
            if self.fourier_radio.isChecked():
                self.derivative_radio.setChecked(True)
    
    def update_analysis_plot(self):
        """Update the analysis plot based on selected radio button"""
        if self.current_analysis_result:
            if self.derivative_radio.isChecked():
                self.update_derivative_plot(self.current_analysis_result)
            elif self.fourier_radio.isChecked():
                self.update_fourier_plot(self.current_analysis_result)
    
    def update_derivative_plot(self, result):
        """Update the derivative analysis plot"""
        # Clear the analysis plot and set labels for derivative
        self.analysis_plotview.clear()
        # Re-add legend after clearing
        self.analysis_legend = self.analysis_plotview.addLegend(offset=(10, 10))
        self.analysis_legend.anchor = (1, 0)  # Top-right anchor
        self.analysis_plotview.setLabel('left', 'dy/dx', units='N/m')
        self.analysis_plotview.setLabel('bottom', 'Displacement', units='m')

        if not result or 'df_data' not in result:
            return

        try:
            df_data = result['df_data']
            # Get current parameters to show threshold
            params = self.param_widget.getCurrentParameters()
            pl_threshold = params.get('pl_threshold', 150e-9)

            # Plot dy_abs_sav vs displacement
            if 'dy_abs_sav' in df_data and 'x' in df_data:
                x_data = df_data['x']
                dy_data = df_data['dy_abs_sav']
                # Plot the derivative curve
                self.analysis_plotview.plot(x_data, dy_data,
                                           pen=pg.mkPen(color='blue', width=2),
                                           name='|dy/dx|')
                
                # Create or update interactive threshold line
                try:
                    if not hasattr(self, 'threshold_line') or self.threshold_line is None:
                        # Create new threshold line
                        self.threshold_line = pg.InfiniteLine(
                            pos=pl_threshold,
                            angle=0,  # Horizontal line
                            pen=pg.mkPen('r', width=2, style=Qt.DashLine),
                            movable=True
                        )
                        # Connect the line movement to parameter update
                        self.threshold_line.sigPositionChanged.connect(self.on_threshold_changed)
                        self.analysis_plotview.addItem(self.threshold_line)
                        print(f"Created interactive threshold line at {pl_threshold:.2e} N/m")
                    else:
                        # Update existing line position without triggering signals
                        self.threshold_line.blockSignals(True)
                        self.threshold_line.setPos(pl_threshold)
                        self.threshold_line.blockSignals(False)
                        if self.threshold_line not in self.analysis_plotview.items():
                            self.analysis_plotview.addItem(self.threshold_line)
                        print(f"Updated threshold line position to {pl_threshold:.2e} N/m")
                        
                except Exception as line_error:
                    print(f"Error creating/updating threshold line: {line_error}")
                    # Fallback to static line
                    self.analysis_plotview.addLine(y=pl_threshold, 
                                                  pen=pg.mkPen('r', width=2, style=Qt.DashLine))
                        
        except Exception as e:
            print(f"Error updating derivative plot: {e}")
            import traceback
            traceback.print_exc()
    
    def on_threshold_changed(self):
        """Handle interactive threshold line movement with debouncing"""
        try:
            if hasattr(self, 'threshold_line') and self.threshold_line is not None:
                # Get new threshold value from the line position
                new_threshold = self.threshold_line.pos().y()
                
                # Store the pending threshold value
                self.pending_threshold_value = new_threshold
                
                # Update the parameter widget immediately for visual feedback
                self.param_widget.blockSignals(True)
                self.param_widget.setParameterValue('pl_threshold', new_threshold)
                self.param_widget.blockSignals(False)
                
                # Stop any existing timer and start a new one (debouncing)
                self.threshold_update_timer.stop()
                self.threshold_update_timer.start(300)  # 300ms delay
                
                print(f"Threshold moved to: {new_threshold:.2e} N/m (analysis delayed)")
                
        except Exception as e:
            print(f"Error handling threshold change: {e}")
            import traceback
            traceback.print_exc()
    
    def delayed_threshold_analysis(self):
        """Run analysis after threshold change delay"""
        try:
            if self.pending_threshold_value is not None:
                print(f"Running delayed analysis with threshold: {self.pending_threshold_value:.2e} N/m")
                self.run_analysis()
                self.pending_threshold_value = None
        except Exception as e:
            print(f"Error in delayed threshold analysis: {e}")
            import traceback
            traceback.print_exc()
    

    
    def update_fourier_plot(self, result):
        """Update the Fourier spectrum plot"""
        # Clear the analysis plot and set labels for Fourier spectrum
        self.analysis_plotview.clear()
        
        # Re-add legend after clearing
        self.analysis_legend = self.analysis_plotview.addLegend(offset=(10, 10))
        self.analysis_legend.anchor = (1, 0)  # Top-right anchor
        self.analysis_plotview.setLabel('left', 'Magnitude', units='')
        self.analysis_plotview.setLabel('bottom', 'Wavenumber', units='µm⁻¹')

        if not result or 'fourier_data' not in result or not result['fourier_data']:
            # Show a message that no Fourier data is available
            self.analysis_plotview.addItem(pg.TextItem("No Fourier data available\nEnable denoising to generate Fourier spectrum", 
                                                      anchor=(0.5, 0.5), 
                                                      fill=pg.mkBrush(255, 255, 255, 100),
                                                      border=pg.mkPen(color='black', width=1)))
            return

        try:
            fourier_data = result['fourier_data']
            
            # Check if fourier_data has the required keys
            if 'xf' not in fourier_data or 'yf_original' not in fourier_data:
                print("Fourier data incomplete")
                return
            
            xf = fourier_data['xf']
            yf_original = fourier_data['yf_original']
            
            # Plot only positive frequencies (half spectrum)
            N_half = len(xf) // 2
            xf_pos = xf[:N_half]
            
            # Convert from m⁻¹ to µm⁻¹ for display
            xf_pos_um_inv = xf_pos * 1e-6
            
            # Filter out zero and negative frequencies for log scale
            pos_mask = xf_pos_um_inv > 0
            xf_filtered = xf_pos_um_inv[pos_mask]
            
            if len(xf_filtered) == 0:
                print("No positive frequencies found")
                return
            
            # Set log scale for x-axis
            self.analysis_plotview.setLogMode(x=True, y=False)
            
            # Plot original FFT
            yf_orig_filtered = np.abs(yf_original[:N_half])[pos_mask]
            self.analysis_plotview.plot(xf_filtered, yf_orig_filtered,
                                       pen=pg.mkPen(color='blue', width=2),
                                       name='Original FFT')
            
            # Plot Butterworth filtered FFT
            if 'yf_filtered' in fourier_data:
                yf_filtered = fourier_data['yf_filtered']
                yf_butter_filtered = np.abs(yf_filtered[:N_half])[pos_mask]
                self.analysis_plotview.plot(xf_filtered, yf_butter_filtered,
                                           pen=pg.mkPen(color='orange', width=2),
                                           name='Butterworth Filtered')
            
            # Plot band suppressed FFT
            if 'yf_band_suppressed' in fourier_data:
                yf_band = fourier_data['yf_band_suppressed']
                yf_band_filtered = np.abs(yf_band[:N_half])[pos_mask]
                self.analysis_plotview.plot(xf_filtered, yf_band_filtered,
                                           pen=pg.mkPen(color='green', width=2),
                                           name='Band Suppressed')
                
        except Exception as e:
            print(f"Error updating Fourier plot: {e}")
    

            
    def trigger_reanalysis(self):
        """Trigger reanalysis with updated filter parameters"""
        try:
            if self.file_path and len(self.file_path) > 0:
                print("Triggering reanalysis with updated filter parameters...")
                self.run_analysis()
        except Exception as e:
            print(f"Error triggering reanalysis: {e}")
            
    def update_results_display(self, result):
        """Update results text display and plateau table"""
        try:
            filename = result.get('filename', '')
            results_text = f"File: {filename}\n"
            results_text += f"Plateaus found: {len(result['plateaus'])}\n"
            results_text += "Analysis completed successfully"
            self.results_text.setText(results_text)
            # Update plateau table
            self.update_plateau_table(result)
        except Exception as e:
            self.results_text.setText(f"Error displaying results: {e}")
        
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
            # xarray_path = self.export_analysis_results_xarray(export_path, timestamp)
            
            status_msg = f"Exported {len(selected_indices)} plateaus to {os.path.basename(export_path)}"
            # if xarray_path:
            #     status_msg += " + XArray"
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
                    'plateau_selections': json.dumps(plateau_selections),
                    'current_file_index': self.index if i == self.index else -1  # Mark current file
                }
                
                session_data.append(row_data)
            
            # Also save session metadata
            session_metadata = {
                'last_file_index': self.index,
                'root_directory': self.root_dir,
                'total_files': len(self.file_path),
                'save_timestamp': timestamp
            }
            
            # Add metadata as the first row (will be handled specially during load)
            metadata_row = {
                'local_file_path': 'SESSION_METADATA',
                'file_name': 'SESSION_METADATA', 
                'bool_good_curve': -1,
                'file_parameters': json.dumps(session_metadata),
                'plateau_selections': '[]',
                'current_file_index': self.index
            }
            session_data.insert(0, metadata_row)
            
            # Create DataFrame and save CSV
            df_session = pd.DataFrame(session_data)
            df_session.to_csv(file_path, index=False)
            
            # Create xarray Dataset for more structured data storage
            # xarray_path = file_path.replace('.csv', '_xarray.nc')
            # self.save_session_xarray(xarray_path, timestamp)
            
            # Update status
            good_count = int(np.sum(self.bool_good_curve)) if len(self.bool_good_curve) > 0 else 0
            total_count = len(self.file_path)
            
            session_info = f"Session saved: {os.path.basename(file_path)}\n"
            session_info += f"Total files: {total_count}\n"
            session_info += f"Good files: {good_count}\n"
            session_info += f"Bad files: {total_count - good_count}\n"
            session_info += "Per-file parameters: Saved\n"
            session_info += "Plateau selections: Saved\n"
            # session_info += f"XArray dataset: {os.path.basename(xarray_path)}"
            
            self.results_text.setText(session_info)
            self.status_label.setText(f"Session saved: {os.path.basename(file_path)}")
            # self.status_label.setText(f"Session saved: {os.path.basename(file_path)} + XArray")
            
        except Exception as e:
            self.status_label.setText(f"Error saving session: {str(e)}")
            self.results_text.setText(f"Error saving session: {str(e)}")
    
    # def save_session_xarray(self, xarray_path, timestamp):
    #     """Save session data as xarray Dataset with rich metadata and structure"""
    #     try:
    #         # Prepare data arrays
    #         n_files = len(self.file_path)
    #         
    #         # File information - use proper data types
    #         file_paths = np.array(self.file_path, dtype='U')  # String array for paths
    #         file_names = np.array(self.file, dtype='U')  # String array for names 
    #         good_curve_flags = self.bool_good_curve.astype(bool)  # Boolean array
    #         
    #         # Prepare parameter data and plateau selections as JSON strings
    #         # (since parameters have mixed types, JSON strings are most compatible)
    #         file_parameters_json = []
    #         plateau_selections_json = []
    #         
    #         for filepath in self.file_path:
    #             # Get parameters for this file and convert to JSON string
    #             file_params = self.file_parameters.get(filepath, self.get_default_parameters())
    #             file_parameters_json.append(json.dumps(file_params))
    #             
    #             # Get plateau selections and convert to JSON string
    #             plateau_sel = self.plateau_selections.get(filepath, [])
    #             plateau_selections_json.append(json.dumps(plateau_sel))
    #         
    #         # Convert to numpy arrays with proper dtypes
    #         file_parameters_array = np.array(file_parameters_json, dtype='U')
    #         plateau_selections_array = np.array(plateau_selections_json, dtype='U')
    #         
    #         # Create coordinate array
    #         file_coords = np.arange(n_files)
    #         
    #         # Create data variables with appropriate data types
    #         data_vars = {
    #             'file_path': (['file'], file_paths),  # String data
    #             'file_name': (['file'], file_names),  # String data  
    #             'bool_good_curve': (['file'], good_curve_flags),  # Boolean data
    #             'file_parameters': (['file'], file_parameters_array),  # JSON strings
    #             'plateau_selections': (['file'], plateau_selections_array),  # JSON strings
    #         }
    #         
    #         # Create coordinates  
    #         coords = {
    #             'file': file_coords,  # Numeric coordinate
    #         }
    #         
    #         # Create Dataset with comprehensive attributes
    #         ds = xr.Dataset(
    #             data_vars=data_vars,
    #             coords=coords,
    #             attrs={
    #                 'title': 'Tether Analysis Session Data',
    #                 'description': 'Session data from Tether Analysis GUI with per-file parameters and selections',
    #                 'creation_timestamp': timestamp,
    #                 'creation_date': datetime.datetime.now().isoformat(),
    #                 'software': 'Tether Analysis GUI v2',
    #                 'total_files': n_files,
    #                 'good_files': int(np.sum(good_curve_flags)),
    #                 'bad_files': int(n_files - np.sum(good_curve_flags)),
    #                 'data_format_version': '2.0',
    #                 'root_directory': self.root_dir,
    #                 'coordinate_description': 'file: numeric index for each TDMS file',
    #                 'data_types': 'file_path: string, file_name: string, bool_good_curve: boolean, file_parameters: JSON string, plateau_selections: JSON string'
    #             }
    #         )
    #         
    #         # Add detailed attributes to data variables with proper descriptions
    #         ds['file_path'].attrs = {
    #             'long_name': 'File paths',
    #             'description': 'Full local file system paths to TDMS files',
    #             'data_type': 'string'
    #         }
    #         
    #         ds['file_name'].attrs = {
    #             'long_name': 'File names',
    #             'description': 'Base names of TDMS files without directory path',
    #             'data_type': 'string'
    #         }
    #         
    #         ds['bool_good_curve'].attrs = {
    #             'long_name': 'Good curve flags',
    #             'description': 'Boolean flags indicating whether curve was marked as good (True) or bad (False)',
    #             'data_type': 'boolean'
    #         }
    #         
    #         ds['file_parameters'].attrs = {
    #             'long_name': 'Analysis parameters',
    #             'description': 'JSON-encoded analysis parameters for each file (mixed numeric/string/boolean types)',
    #             'data_type': 'JSON string',
    #             'parameter_keys': str(list(self.get_default_parameters().keys())),
    #             'example_parameters': str(self.get_default_parameters())
    #         }
    #         
    #         ds['plateau_selections'].attrs = {
    #             'long_name': 'Plateau selections',
    #             'description': 'JSON-encoded boolean arrays indicating which plateaus were selected for each file',
    #             'data_type': 'JSON string',
    #             'note': 'Each entry is a JSON list of boolean values'
    #         }
    #         
    #         # Save the dataset with proper encoding
    #         ds.to_netcdf(xarray_path, format='NETCDF4')
    #         
    #         print(f"XArray dataset saved to: {xarray_path}")
    #         
    #     except Exception as e:
    #         print(f"Warning: Could not save xarray dataset: {e}")
    #         # Don't fail the main save operation if xarray save fails
    
    # def export_analysis_results_xarray(self, base_path, timestamp):
    #     """Export current analysis results as xarray Dataset"""
    #     try:
    #         if not hasattr(self, 'current_analysis_result') or not self.current_analysis_result:
    #             return None
    #             
    #         result = self.current_analysis_result
    #         
    #         # Extract data from analysis result
    #         rel_time = result['rel_time']
    #         defl_savitz = result['defl_savitz']
    #         displacement = result['displacement']
    #         df_plat = result['df_plat']
    #         plateaus = result['plateaus']
    #         
    #         n_points = len(rel_time)
    #         n_plateaus = len(df_plat) if len(df_plat) > 0 else 1
    #         
    #         # Create coordinate arrays
    #         time_coords = rel_time
    #         plateau_coords = np.arange(n_plateaus)
    #         
    #         # Prepare plateau data arrays
    #         plateau_data = {}
    #         if len(df_plat) > 0:
    #             plateau_data = {
    #                 'plateau_numbers': (['plateau'], df_plat['plateaus'].values),
    #                 'plateau_avg_force': (['plateau'], df_plat['plateau_avg'].values),
    #                 'plateau_delta_avg': (['plateau'], df_plat['delta_avg'].values),
    #                 'plateau_start_idx': (['plateau'], df_plat['start'].values),
    #                 'plateau_end_idx': (['plateau'], df_plat['end'].values),
    #                 'plateau_avg_idx': (['plateau'], df_plat['plateau_avg_idx'].values),
    #                 'plateau_delta_time': (['plateau'], df_plat['delta_time'].values),
    #                 'plateau_mean_derivative': (['plateau'], df_plat['mean dN/dt'].values),
    #                 'plateau_velocity_calc': (['plateau'], df_plat['velocity_calc_um_s'].values),
    #             }
    #         else:
    #             # Create empty arrays if no plateaus
    #             empty_array = np.array([np.nan])
    #             plateau_data = {
    #                 'plateau_numbers': (['plateau'], empty_array),
    #                 'plateau_avg_force': (['plateau'], empty_array),
    #                 'plateau_delta_avg': (['plateau'], empty_array),
    #                 'plateau_start_idx': (['plateau'], empty_array),
    #                 'plateau_end_idx': (['plateau'], empty_array),
    #                 'plateau_avg_idx': (['plateau'], empty_array),
    #                 'plateau_delta_time': (['plateau'], empty_array),
    #                 'plateau_mean_derivative': (['plateau'], empty_array),
    #                 'plateau_velocity_calc': (['plateau'], empty_array),
    #             }
    #         
    #         # Create data variables dictionary
    #         data_vars = {
    #             'time': (['time'], rel_time),
    #             'deflection_savgol': (['time'], defl_savitz),
    #             'displacement': (['time'], displacement),
    #             **plateau_data
    #         }
    #         
    #         # Create coordinates
    #         coords = {
    #             'time': time_coords,
    #             'plateau': plateau_coords,
    #         }
    #         
    #         # Get file metadata
    #         filemetadata = result.get('filemetadata', {})
    #         filename = os.path.basename(result['filename'])
    #         
    #         # Create Dataset
    #         ds = xr.Dataset(
    #             data_vars=data_vars,
    #             coords=coords,
    #             attrs={
    #                 'title': f'Tether Analysis Results - {filename}',
    #                 'description': 'Analysis results from single TDMS file tether analysis',
    #                 'source_file': result['filename'],
    #                 'source_filename': filename,
    #                 'creation_timestamp': timestamp,
    #                 'creation_date': datetime.datetime.now().isoformat(),
    #                 'software': 'Tether Analysis GUI v2',
    #                 'total_plateaus': len(plateaus),
    #                 'total_data_points': n_points,
    #                 'sampling_rate_retract': result.get('relative_SR_ret'),
    #                 'contact_point_index': result.get('index_first_positive'),
    #                 'velocity_metadata_um_s': result.get('velocity_metadata'),
    #                 'velocity_calc_um_s': result.get('velocity_calc_um_s'),
    #                 'data_format_version': '1.0',
    #             }
    #         )
    #         
    #         # Add comprehensive attributes to data variables
    #         ds['time'].attrs = {
    #             'long_name': 'Relative time from contact point',
    #             'units': 'seconds',
    #             'description': 'Time array starting from detected contact point'
    #         }
    #         
    #         ds['deflection_savgol'].attrs = {
    #             'long_name': 'Savitzky-Golay filtered deflection',
    #             'units': 'N',
    #             'description': 'Deflection signal after tilt correction and Savitzky-Golay smoothing',
    #             'processing': 'Tilt corrected, contact point normalized, Savitzky-Golay filtered'
    #         }
    #         
    #         ds['displacement'].attrs = {
    #             'long_name': 'Displacement from contact point',
    #             'units': 'm',
    #             'description': 'Z-piezo displacement normalized to contact point (0 = contact)'
    #         }
    #         
    #         if len(df_plat) > 0:
    #             ds['plateau_avg_force'].attrs = {
    #                 'long_name': 'Average force per plateau',
    #                 'units': 'N',
    #                 'description': 'Mean deflection force calculated for each detected plateau'
    #             }
    #             
    #             ds['plateau_delta_avg'].attrs = {
    #                 'long_name': 'Force difference between plateaus',
    #                 'units': 'N',
    #                 'description': 'Force difference between current and next plateau'
    #             }
    #             
    #             ds['plateau_velocity_calc'].attrs = {
    #                 'long_name': 'Calculated velocity per plateau',
    #                 'units': 'μm/s',
    #                 'description': 'Velocity calculated from linear regression of displacement vs time for each plateau'
    #             }
    #         
    #         # Add file metadata as global attributes if available
    #         if filemetadata:
    #             ds.attrs.update({
    #                 'spring_constant_N_per_m': filemetadata.get('spring_const_Nbym'),
    #                 'deflection_sensitivity_nm_per_V': filemetadata.get('defl_sens_nmbyV'),
    #                 'height_channel': filemetadata.get('height_channel_key'),
    #             })
    #         
    #         # Save the dataset
    #         xarray_path = base_path.replace('.csv', '_analysis_results.nc')
    #         ds.to_netcdf(xarray_path, format='NETCDF4')
    #         
    #         return xarray_path
    #         
    #     except Exception as e:
    #         print(f"Warning: Could not export analysis results to xarray: {e}")
    #         return None
    
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
            run_batch_analysis = dialog.get_batch_analysis_enabled()
            
            # Load the CSV file
            df_session = pd.read_csv(file_path)
            
            # Check for session metadata (first row with special marker)
            session_metadata = None
            last_file_index = 0
            
            if (len(df_session) > 0 and 
                df_session.iloc[0]['local_file_path'] == 'SESSION_METADATA'):
                try:
                    metadata_row = df_session.iloc[0]
                    session_metadata = json.loads(metadata_row['file_parameters'])
                    last_file_index = metadata_row.get('current_file_index', 0)
                    # Remove metadata row from dataframe
                    df_session = df_session.iloc[1:].reset_index(drop=True)
                except Exception as e:
                    print(f"Warning: Could not load session metadata: {e}")
            
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
            
            # Clear current file table
            self.file_table.clearContents()
            self.file_table.setRowCount(0)
            
            # Load the session files
            self.file_path = existing_files
            self.file = existing_names
            self.bool_good_curve = np.array(existing_good_curve)
            self.file_parameters = loaded_file_parameters
            self.plateau_selections = loaded_plateau_selections
            
            # Create file data for the table with session data
            from datetime import datetime
            self.file_data = []
            for i, (file_path, file_name) in enumerate(zip(existing_files, existing_names)):
                # Get file statistics
                try:
                    stat_info = os.stat(file_path)
                    file_size_kb = stat_info.st_size / 1024
                    mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                    date_str = mod_time.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    file_size_kb = 0
                    date_str = "Unknown"
                
                # Determine status from bool_good_curve
                status = 'Good' if self.bool_good_curve[i] == 1 else ('Bad' if self.bool_good_curve[i] == 0 else 'New')
                
                # Extract date taken from filename
                date_taken = self.extract_date_from_filename(file_name)
                
                self.file_data.append({
                    'filename': file_name,
                    'full_path': file_path,
                    'status': status,
                    'date_taken': date_taken,
                    'date_modified': date_str,
                    'size_kb': file_size_kb,
                    'analysis_status': 'Not Analyzed'
                })
            
            # Populate the table
            self.populate_file_table()
            
            # Restore last file index if valid, otherwise start from 0
            if 0 <= last_file_index < len(self.file_path):
                self.index = last_file_index
            else:
                self.index = 0
            
            self.file_table.selectRow(self.index)
            
            # Load parameters for the current file
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
            session_info += f"Restored to file: {self.index + 1}/{total_count}\n"
            
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
            
            # Conditionally run batch analysis based on user selection
            if run_batch_analysis:
                QTimer.singleShot(200, self.run_batch_analysis_on_session_files)
            else:
                # Just analyze the current file to show something
                QTimer.singleShot(200, self.run_analysis)
            
            self.status_label.setText(f"Loaded {option_display}: {good_count}/{total_count} good files")
            
        except Exception as e:
            self.status_label.setText(f"Error loading session: {str(e)}")
            self.results_text.setText(f"Error loading session: {str(e)}")

    def run_batch_analysis_on_session_files(self):
        """Run analysis on all files loaded from the session"""
        if not self.file_path:
            return
            
        total_files = len(self.file_path)
        processed_files = 0
        failed_files = 0
        
        # Store original index to restore later
        original_index = self.index
        
        self.status_label.setText(f"Running batch analysis on {total_files} session files...")
        
        # Process each file
        for file_index in range(total_files):
            try:
                # Set current index and load parameters for this file
                self.index = file_index
                self.load_parameters_for_current_file()
                
                # Update table selection to show progress
                self.file_table.selectRow(self.index)
                
                # Update status
                filename = os.path.basename(self.file_path[file_index])
                self.status_label.setText(f"Analyzing {file_index + 1}/{total_files}: {filename}")
                self.update_analysis_status(file_index, "Analyzing...")
                
                # Force GUI update
                QApplication.processEvents()
                
                # Get parameters for this specific file
                params = self.get_file_parameters(self.file_path[file_index])
                
                # Run analysis
                result = process_single_file(self.file_path[file_index], params, save_plots=False)
                
                if result:
                    # Store the result for the current file
                    if file_index == original_index:
                        self.current_analysis_result = result
                    
                    # Update analysis status
                    plateau_count = len(result['plateaus']) if result['plateaus'] else 0
                    self.update_analysis_status(file_index, f"Analyzed ({plateau_count} plateaus)")
                    processed_files += 1
                    
                    print(f"✓ Analyzed {filename}: {plateau_count} plateaus found")
                else:
                    self.update_analysis_status(file_index, "Analysis Failed")
                    failed_files += 1
                    print(f"✗ Failed to analyze {filename}")
                    
            except Exception as e:
                self.update_analysis_status(file_index, "Analysis Failed")
                failed_files += 1
                print(f"✗ Error analyzing {os.path.basename(self.file_path[file_index])}: {e}")
        
        # Restore original index and load its results
        self.index = original_index
        self.file_table.selectRow(self.index)
        self.load_parameters_for_current_file()
        
        # Update display for the current file if we have results
        if hasattr(self, 'current_analysis_result') and self.current_analysis_result:
            self.update_plot_with_analysis(self.current_analysis_result)
            self.update_results_display(self.current_analysis_result)
            self.update_plateau_table(self.current_analysis_result)
            self.update_velocity_indicators(self.current_analysis_result)
        else:
            # Run analysis on current file to show something
            QTimer.singleShot(100, self.run_analysis)
        
        # Update final status
        success_rate = (processed_files / total_files) * 100 if total_files > 0 else 0
        final_status = f"Batch analysis complete: {processed_files}/{total_files} files analyzed successfully ({success_rate:.0f}%)"
        
        if failed_files > 0:
            final_status += f", {failed_files} failed"
            
        self.status_label.setText(final_status)
        
        # Update results text with batch analysis summary
        batch_summary = f"""Batch Analysis Complete!

Files processed: {processed_files}/{total_files}
Success rate: {success_rate:.1f}%
Failed analyses: {failed_files}

Current file: {self.index + 1}/{total_files}
File: {os.path.basename(self.file_path[self.index]) if self.file_path else 'None'}

Navigation: Use ↑/↓ to browse analyzed files
All file-specific parameters have been preserved."""

        self.results_text.setText(batch_summary)


class LoadSessionDialog(QDialog):
    """Dialog for selecting which files to load from session"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_option = None
        self.setupUI()
        
    def setupUI(self):
        self.setWindowTitle("Load Session Options")
        self.setFixedSize(300, 320)  # Increased height for new checkbox
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
        self.option_group = QGroupBox("File Selection")
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
        layout.addSpacing(15)
        
        # Add batch analysis option
        self.analysis_group = QGroupBox("Analysis Options")
        analysis_layout = QVBoxLayout(self.analysis_group)
        
        self.run_batch_analysis_checkbox = QCheckBox("Run batch analysis on all loaded files")
        self.run_batch_analysis_checkbox.setChecked(False)  # Default: disabled
        self.run_batch_analysis_checkbox.setToolTip("Automatically analyze all files after loading session.\nUncheck to load files without analysis.")
        analysis_layout.addWidget(self.run_batch_analysis_checkbox)
        
        # Add explanation text
        explanation = QLabel("When enabled, all files will be analyzed immediately after loading.\nWhen disabled, files are loaded but require manual analysis.")
        explanation.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
        explanation.setWordWrap(True)
        analysis_layout.addWidget(explanation)
        
        layout.addWidget(self.analysis_group)
        
        # Add spacing
        layout.addSpacing(15)
        
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
    
    def get_batch_analysis_enabled(self):
        """Get whether batch analysis is enabled"""
        return self.run_batch_analysis_checkbox.isChecked()


class JoystickHandler(QObject):
    buttonPressed = pyqtSignal(int)  # Signal: emits button index when pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.joystick = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_joystick)
        self.timer.start(100)  # Poll every 100ms
        self.button_states = {}  # Track button states to prevent repeated signals
        self.init_joystick()

    def init_joystick(self):
        """Initialize pygame joystick"""
        try:
            pyg.init()
            pyg.joystick.init()
            if pyg.joystick.get_count() > 0:
                self.joystick = pyg.joystick.Joystick(0)
                self.joystick.init()
                print(f"Joystick connected: {self.joystick.get_name()}")
            else:
                self.joystick = None
                print("No joystick detected.")
        except Exception as e:
            print(f"Error initializing joystick: {e}")
            self.joystick = None

    def poll_joystick(self):
        """Poll joystick for button presses"""
        if self.joystick is None:
            return
        try:
            pyg.event.pump()
            for i in range(self.joystick.get_numbuttons()):
                current_state = self.joystick.get_button(i)
                previous_state = self.button_states.get(i, False)
                
                # Only emit signal on button press (not while held)
                if current_state and not previous_state:
                    print(f"Button {i} pressed")
                    self.buttonPressed.emit(i)
                
                self.button_states[i] = current_state
                
        except Exception as e:
            print(f"Error polling joystick: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    root_dir = str(os.environ.get("workingDirectory"))
    print ('Root directory set to:', root_dir)
    
    # Set default directory - change this to your data directory
    # root_dir = '/Users/evillz/Data/article/2025_07_01_THP1_phd'
    
    # Create and show GUI
    gui = TetherAnalysisGUI(root_dir)

    # --- Add this block to choose which screen to show the window on ---
    # screen_number = 1  # Change to 0 for primary, 1 for secondary, etc.
    screen_number = int(os.environ.get("SCREEN_IDX", 0))
    screens = app.screens()
    if len(screens) > screen_number:
        screen = screens[screen_number]
        geometry = screen.geometry()
        gui.move(geometry.left(), geometry.top())
    # ---------------------------------------------------------------

    gui.show()
    
    sys.exit(app.exec_())


# Create an alias for backward compatibility
TetherAnalysisApp = TetherAnalysisGUI


if __name__ == '__main__':
    main()