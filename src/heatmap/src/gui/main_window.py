#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for PSNEX Map Analysis GUI
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QAction, QMenuBar, QStatusBar, QFileDialog,
                             QMessageBox, QProgressDialog, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
import sys
import os
from copy import deepcopy   

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from gui.map_viewer_widget import MapViewerWidget
from gui.file_browser_widget import FileBrowserWidget
from core import MapProcessor, DataLoader, SessionManager, ExportManager
from config import DEFAULT_PARAMS


class MapAnalysisMainWindow(QMainWindow):
    """Main application window for PSNEX Map Analysis"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.map_processor = MapProcessor()
        self.data_loader = DataLoader()
        self.session_manager = SessionManager()
        self.export_manager = ExportManager()
        
        # Current state
        self.current_map_folder = None
        self.current_parameters = DEFAULT_PARAMS.copy()
        self.current_map_data = None
        self.current_roi_data = None
        
        self.setupUI()
        self.setupMenuBar()
        self.setupConnections()
        self.updateWindowTitle()
        
    def setupUI(self):
        """Setup main user interface"""
        self.setWindowTitle("PSNEX Map Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Main splitter (2 panels for now - browser and viewer)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: File browser
        self.file_browser = FileBrowserWidget()
        
        # Center panel: Map viewer
        self.map_viewer = MapViewerWidget()
        
        # Add panels to splitter
        main_splitter.addWidget(self.file_browser)
        main_splitter.addWidget(self.map_viewer)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(main_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setupMenuBar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open Map Folder...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_map_folder)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_session_action = QAction('Save Session...', self)
        save_session_action.setShortcut(QKeySequence.Save)
        save_session_action.triggered.connect(self.on_save_session)
        file_menu.addAction(save_session_action)
        
        load_session_action = QAction('Load Session...', self)
        load_session_action.triggered.connect(self.on_load_session)
        file_menu.addAction(load_session_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Process menu
        process_menu = menubar.addMenu('Process')
        
        analyze_action = QAction('Analyze Current Map', self)
        analyze_action.setShortcut('Ctrl+R')
        analyze_action.triggered.connect(self.on_analyze_map)
        process_menu.addAction(analyze_action)
        
        # Export menu
        export_menu = menubar.addMenu('Export')
        
        export_tiff_action = QAction('Export as TIFF...', self)
        export_tiff_action.triggered.connect(self.on_export_tiff)
        export_menu.addAction(export_tiff_action)
        
        export_csv_action = QAction('Export as CSV...', self)
        export_csv_action.triggered.connect(self.on_export_csv)
        export_menu.addAction(export_csv_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
        
    def setupConnections(self):
        """Setup signal-slot connections"""
        # File browser
        self.file_browser.folder_selected.connect(self.on_folder_selected)
        
        # Map viewer
        self.map_viewer.roi_selected.connect(self.on_roi_selected)
        self.map_viewer.parameters_changed.connect(self.on_viz_parameters_changed)
        
    def on_open_map_folder(self):
        """Open map folder dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select PSNEX Map Folder",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.file_browser.add_folder(folder)
            self.on_folder_selected(folder)
        
    def on_folder_selected(self, folder_path):
        """Handle folder selection"""
        self.current_map_folder = folder_path
        self.updateWindowTitle()
        self.status_bar.showMessage(f"Selected: {os.path.basename(folder_path)}")
        
        # Auto-analyze if selected
        self.on_analyze_map()
        
    def on_analyze_map(self):
        """Analyze current map with current parameters"""
        if not self.current_map_folder:
            QMessageBox.warning(self, "No Folder", "Please select a map folder first")
            return
        
        self.status_bar.showMessage("Processing map...")
        QApplication.processEvents()
        
        try:
            # Process map
            result = self.map_processor.process_map(
                self.current_map_folder,
                correct_indices=self.current_parameters.get('correct_indices', True),
                zmin=self.current_parameters.get('zmin'),
                zmax=self.current_parameters.get('zmax'),
                value_key=self.current_parameters.get('value_key', 'z_height_um_zero')
            )
            
            if not result['success']:
                QMessageBox.critical(self, "Error", f"Failed to process map:\n{result['error']}")
                self.status_bar.showMessage("Error processing map")
                return
            
            # Store result
            self.current_map_data = result
            
            # Display map (prefer TDMS over CSV)
            map_to_display = result['map_tdms'] if result['map_tdms'] is not None else result['map_csv']
            
            if map_to_display is not None:
                # Update parameters with current visualization settings
                display_params = deepcopy(result['params'])
                # display_params.update(self.current_parameters)
                
                self.map_viewer.display_map(
                    map_to_display,
                    result['x_axis'],
                    result['y_axis'],
                    display_params
                )
                
                self.status_bar.showMessage(f"Map loaded: {map_to_display.shape}")
            else:
                QMessageBox.warning(self, "No Data", "No map data available")
                self.status_bar.showMessage("No map data")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")
            self.status_bar.showMessage("Error")
            import traceback
            traceback.print_exc()
    
    def on_roi_selected(self, roi_pixels):
        """Handle ROI selection"""
        if not self.current_map_data:
            self.status_bar.showMessage("No map loaded")
            return
        
        if not roi_pixels or len(roi_pixels) == 0:
            self.status_bar.showMessage("Empty ROI selected")
            return
        
        try:
            # Determine map type based on what's available
            map_type = 'tdms' if self.current_map_data.get('map_tdms') is not None else 'csv'
            
            # Extract ROI data
            roi_df = self.map_processor.extract_roi_data(roi_pixels, map_type=map_type)
            
            if roi_df is None or len(roi_df) == 0:
                self.status_bar.showMessage("No valid ROI data")
                return
            
            # Get statistics
            stats = self.map_processor.get_roi_statistics()
            
            # Store ROI data
            self.current_roi_data = {'dataframe': roi_df, 'statistics': stats}
            
            # Show statistics in status bar
            if stats and stats.get('count', 0) > 0:
                msg = f"ROI: {stats['count']} pixels, Mean: {stats['mean']:.3f} µm, Std: {stats['std']:.3f} µm"
                self.status_bar.showMessage(msg)
                
                # Show detailed stats in message box
                stats_text = f"""ROI Statistics:
                
Pixels: {stats['count']}
Mean: {stats['mean']:.4f} µm
Std Dev: {stats['std']:.4f} µm
Min: {stats['min']:.4f} µm
Max: {stats['max']:.4f} µm
Median: {stats['median']:.4f} µm
Q25: {stats['q25']:.4f} µm
Q75: {stats['q75']:.4f} µm"""
                
                QMessageBox.information(self, "ROI Statistics", stats_text)
            else:
                self.status_bar.showMessage("ROI selected but no statistics available")
                
        except Exception as e:
            error_msg = f"Error processing ROI:\n{str(e)}"
            QMessageBox.warning(self, "ROI Error", error_msg)
            self.status_bar.showMessage("ROI processing error")
            import traceback
            traceback.print_exc()
    
    def on_viz_parameters_changed(self, params):
        """Handle visualization parameter changes"""
        self.current_parameters.update(params)
    
    def on_save_session(self):
        """Save current session"""
        if not self.current_map_folder:
            QMessageBox.warning(self, "No Data", "No map loaded to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            os.path.join(self.current_map_folder, "session.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                self.session_manager.create_session(self.current_map_folder, self.current_parameters)
                
                roi_df = self.current_roi_data['dataframe'] if self.current_roi_data else None
                stats = self.current_roi_data['statistics'] if self.current_roi_data else None
                
                success = self.session_manager.save_session(file_path, roi_df=roi_df, statistics=stats)
                
                if success:
                    QMessageBox.information(self, "Success", "Session saved successfully")
                    self.status_bar.showMessage(f"Session saved: {file_path}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save session")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving session:\n{str(e)}")
    
    def on_load_session(self):
        """Load session"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            os.path.expanduser("~"),
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                result = self.session_manager.load_session(file_path)
                
                if result['success']:
                    session = result['session']
                    
                    # Load map folder
                    if 'map_folder' in session:
                        self.current_map_folder = session['map_folder']
                        self.file_browser.add_folder(self.current_map_folder)
                        
                    # Load parameters
                    if 'parameters' in session:
                        self.current_parameters.update(session['parameters'])
                    
                    # Load ROI data
                    if result['roi_data'] is not None:
                        self.current_roi_data = {
                            'dataframe': result['roi_data'],
                            'statistics': session.get('statistics')
                        }
                    
                    QMessageBox.information(self, "Success", "Session loaded successfully")
                    self.status_bar.showMessage(f"Session loaded: {file_path}")
                    
                    # Analyze map
                    if self.current_map_folder:
                        self.on_analyze_map()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to load session:\n{result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading session:\n{str(e)}")
    
    def on_export_tiff(self):
        """Export current map as TIFF"""
        if not self.current_map_data:
            QMessageBox.warning(self, "No Data", "No map loaded to export")
            return
        
        map_to_export = self.current_map_data['map_tdms'] if self.current_map_data['map_tdms'] is not None else self.current_map_data['map_csv']
        
        if map_to_export is None:
            QMessageBox.warning(self, "No Data", "No map data available")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export as TIFF",
            os.path.join(self.current_map_folder, "map.tiff"),
            "TIFF Files (*.tiff *.tif);;All Files (*)"
        )
        
        if file_path:
            try:
                params = self.current_map_data['params']
                success = self.export_manager.export_tiff(
                    map_to_export,
                    file_path,
                    px_um_x=params.get('map_x_step', 0.14),
                    px_um_y=params.get('map_y_step', 0.14)
                )
                
                if success:
                    QMessageBox.information(self, "Success", "TIFF exported successfully")
                    self.status_bar.showMessage(f"Exported: {file_path}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to export TIFF")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting TIFF:\n{str(e)}")
    
    def on_export_csv(self):
        """Export current ROI data as CSV"""
        if not self.current_roi_data:
            QMessageBox.warning(self, "No ROI", "No ROI data to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ROI as CSV",
            os.path.join(self.current_map_folder or os.path.expanduser("~"), "roi_data.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                success = self.export_manager.export_roi_data(
                    self.current_roi_data['dataframe'],
                    file_path,
                    statistics=self.current_roi_data.get('statistics')
                )
                
                if success:
                    QMessageBox.information(self, "Success", "ROI data exported successfully")
                    self.status_bar.showMessage(f"Exported: {file_path}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to export CSV")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting CSV:\n{str(e)}")
    
    def on_about(self):
        """Show about dialog"""
        about_text = """PSNEX Map Analysis GUI
        
Version: 0.1.0

A tool for analyzing PSNEX map data with:
- Interactive heatmap visualization
- ROI selection and analysis
- TIFF and CSV export
- Session management

Based on map_ctc_article_final.ipynb

© 2025 DyNaMo-INSERM"""
        
        QMessageBox.about(self, "About PSNEX Map Analysis", about_text)
    
    def updateWindowTitle(self):
        """Update window title"""
        if self.current_map_folder:
            folder_name = os.path.basename(self.current_map_folder)
            self.setWindowTitle(f"PSNEX Map Analysis - {folder_name}")
        else:
            self.setWindowTitle("PSNEX Map Analysis")
