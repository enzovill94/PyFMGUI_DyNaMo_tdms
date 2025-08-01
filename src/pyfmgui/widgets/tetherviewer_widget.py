from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np
import pandas as pd
import logging
import os
import datetime
import json
import sys
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QLabel, QPushButton, QShortcut
from PyQt5.QtGui import QKeySequence
import pyfmgui.const as cts

logger = logging.getLogger()

# Import tether analysis function
try:
    import sys
    sys.path.append('/Users/evillz/Github/PyFMGUI_DyNaMo_tdms/PyFMGUI_DyNaMo/scripts')
    from tether_script import process_single_file
    HAS_TETHER_ANALYSIS = True
except ImportError:
    logger.warning("Could not import tether_script.process_single_file - tether analysis will be disabled")
    HAS_TETHER_ANALYSIS = False

class TetherViewerWidget(QtWidgets.QWidget):
    def __init__(self, session, parent=None):
        super(TetherViewerWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.min_val_line = None
        self.max_val_line = None
        self.offset_roi = None
        self.file_dict = {}
        self.session.tether_viewer_widget = self
        
        # Tether analysis specific attributes
        self.current_analysis_result = None
        self.plateau_selections = {}
        self.plateau_table = None
        self.calc_ret_vel_label = None
        self.meta_ret_vel_label = None
        
        # Session management
        self.file_parameters = {}  # Store parameters per file
        self.file_status = {}  # Store good/bad status per file
        self.session_results = {}  # Store analysis results per file
        self.current_session_file = None
        
        self.init_gui()
        if self.session.loaded_files != {}:
            self.updateCombo()

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        self.pushButton = QtWidgets.QPushButton("Analyze Tether")
        self.pushButton.setText("Analyze Tether")
        self.pushButton.setToolTip("Run tether analysis (Shortcut: Enter)")
        self.pushButton.clicked.connect(self.do_tether_analysis)

        # Session management buttons
        session_layout = QHBoxLayout()
        self.save_session_button = QPushButton("Save Session")
        self.load_session_button = QPushButton("Load Session")
        self.export_batch_button = QPushButton("Export Batch")
        self.save_session_button.setToolTip("Save session (Shortcut: S)")
        self.load_session_button.setToolTip("Load session (Shortcut: L)")
        self.export_batch_button.setToolTip("Export batch results (Shortcut: E)")
        self.save_session_button.clicked.connect(self.save_session)
        self.load_session_button.clicked.connect(self.load_session)
        self.export_batch_button.clicked.connect(self.export_batch_results)
        self.save_session_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-size: 10px; }")
        self.load_session_button.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; font-size: 10px; }")
        self.export_batch_button.setStyleSheet("QPushButton { background-color: #607D8B; color: white; font-size: 10px; }")
        session_layout.addWidget(self.save_session_button)
        session_layout.addWidget(self.load_session_button)
        session_layout.addWidget(self.export_batch_button)

        # File status controls
        status_layout = QHBoxLayout()
        self.mark_good_button = QPushButton("Mark Good")
        self.mark_bad_button = QPushButton("Mark Bad")
        self.file_status_label = QLabel("Status: --")
        self.mark_good_button.setToolTip("Mark file as good (Shortcut: G)")
        self.mark_bad_button.setToolTip("Mark file as bad (Shortcut: B)")
        self.mark_good_button.clicked.connect(self.mark_file_good)
        self.mark_bad_button.clicked.connect(self.mark_file_bad)
        self.mark_good_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 10px; }")
        self.mark_bad_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-size: 10px; }")
        self.file_status_label.setStyleSheet("QLabel { background-color: #F5F5F5; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")
        status_layout.addWidget(self.mark_good_button)
        status_layout.addWidget(self.mark_bad_button)
        status_layout.addWidget(self.file_status_label)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.currentTextChanged.connect(self.file_changed)

        self.params = Parameter.create(name='params', children=cts.tether_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)
        
        # Connect parameter changes to auto-save
        self.params.sigTreeStateChanged.connect(self.on_parameter_changed)

        # Plateau controls
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

        # Plateau table
        self.plateau_table = QTableWidget()
        self.setup_plateau_table()

        # Velocity indicators
        self.calc_ret_vel_label = QLabel("Calc Ret Vel: -- μm/s")
        self.meta_ret_vel_label = QLabel("Meta Ret Vel: -- μm/s")
        self.calc_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F5E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")
        self.meta_ret_vel_label.setStyleSheet("QLabel { background-color: #E8F0FF; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")
        
        velocity_layout = QHBoxLayout()
        velocity_layout.addWidget(self.calc_ret_vel_label)
        velocity_layout.addWidget(self.meta_ret_vel_label)

        self.l2 = pg.GraphicsLayoutWidget()

        params_layout.addWidget(self.combobox, 1)
        params_layout.addWidget(self.paramTree, 3)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addLayout(session_layout)
        params_layout.addLayout(status_layout)
        params_layout.addLayout(plateau_controls_layout)
        params_layout.addWidget(self.plateau_table)
        params_layout.addLayout(velocity_layout)
        params_layout.addWidget(self.l2, 2)

        # Single main plot for tether analysis
        self.main_plot = pg.PlotWidget()
        self.main_plot.setLabel('left', 'Deflection', 'N')
        self.main_plot.setLabel('bottom', 'Time', 's')
        self.main_plot.showGrid(x=True, y=True)
        
        # Keep the original multi-plot structure for backwards compatibility 
        self.l = pg.GraphicsLayoutWidget()
        
        ## Add 3 plots into the first row (automatic position)
        self.plotItem = pg.PlotItem(lockAspect=True)
        vb = self.plotItem.getViewBox()
        vb.setAspectLocked(lock=True, ratio=1)

        self.ROI = pg.ROI([0,0], [1,1], movable=False, rotatable=False, resizable=False, removable=False, aspectLocked=True)
        self.ROI.setPen("r", linewidth=2)
        self.ROI.setZValue(10)

        self.correlogram = pg.ImageItem(lockAspect=True)
        self.plotItem.addItem(self.correlogram)    # display correlogram
        
        self.p1 = pg.PlotItem()
        self.p2 = pg.PlotItem()
        self.p2legend = self.p2.addLegend()
        self.p3 = pg.PlotItem()
        self.p4 = pg.PlotItem()
        
        # Set default segment to 'retract'
        analysis_params = self.params.child('Analysis Params')
        analysis_params.child('Curve Segment').setValue('retract')

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.main_plot, 3)  # Use single main plot instead of l
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Ensure the widget can receive keyboard focus
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for quick file navigation and marking"""        
        # G key - mark file as good
        self.shortcut_good = QShortcut(QKeySequence('G'), self)
        self.shortcut_good.activated.connect(self.mark_file_good)
        
        # B key - mark file as bad
        self.shortcut_bad = QShortcut(QKeySequence('B'), self)
        self.shortcut_bad.activated.connect(self.mark_file_bad)
        
        # Enter key - run analysis (try both Return and Enter keys)
        self.shortcut_analyze = QShortcut(QKeySequence(QtCore.Qt.Key_Return), self)
        self.shortcut_analyze.activated.connect(self.do_tether_analysis)
        
        self.shortcut_analyze_enter = QShortcut(QKeySequence(QtCore.Qt.Key_Enter), self)
        self.shortcut_analyze_enter.activated.connect(self.do_tether_analysis)
        
        # Also try Ctrl+Return as backup
        self.shortcut_analyze_ctrl = QShortcut(QKeySequence('Ctrl+Return'), self)
        self.shortcut_analyze_ctrl.activated.connect(self.do_tether_analysis)
        
        # S key - save session
        self.shortcut_save = QShortcut(QKeySequence('S'), self)
        self.shortcut_save.activated.connect(self.save_session)
        
        # L key - load session
        self.shortcut_load = QShortcut(QKeySequence('L'), self)
        self.shortcut_load.activated.connect(self.load_session)
        
        # E key - export batch results
        self.shortcut_export = QShortcut(QKeySequence('E'), self)
        self.shortcut_export.activated.connect(self.export_batch_results)
        
        # Up/Down arrows for file navigation
        self.shortcut_prev = QShortcut(QKeySequence(QtCore.Qt.Key_Up), self)
        self.shortcut_prev.activated.connect(self.navigate_prev_file)
        
        self.shortcut_next = QShortcut(QKeySequence(QtCore.Qt.Key_Down), self)
        self.shortcut_next.activated.connect(self.navigate_next_file)
    
    def navigate_prev_file(self):
        """Navigate to previous file in combobox"""
        current_index = self.combobox.currentIndex()
        if current_index > 0:
            self.combobox.setCurrentIndex(current_index - 1)
    
    def navigate_next_file(self):
        """Navigate to next file in combobox"""
        current_index = self.combobox.currentIndex()
        if current_index < self.combobox.count() - 1:
            self.combobox.setCurrentIndex(current_index + 1)
    
    def closeEvent(self, evnt):
        self.session.tether_viewer_widget = None

    def keyPressEvent(self, event):
        """Handle key press events directly"""
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.do_tether_analysis()
            event.accept()
        elif event.key() == QtCore.Qt.Key_G:
            self.mark_file_good()
            event.accept()
        elif event.key() == QtCore.Qt.Key_B:
            self.mark_file_bad()
            event.accept()
        elif event.key() == QtCore.Qt.Key_S:
            self.save_session()
            event.accept()
        elif event.key() == QtCore.Qt.Key_L:
            self.load_session()
            event.accept()
        elif event.key() == QtCore.Qt.Key_E:
            self.export_batch_results()
            event.accept()
        elif event.key() == QtCore.Qt.Key_Up:
            self.navigate_prev_file()
            event.accept()
        elif event.key() == QtCore.Qt.Key_Down:
            self.navigate_next_file()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def clear(self):
        self.combobox.clear()
        self.l.clear()
        self.l2.clear()

    def do_tether_analysis(self):
        """Run tether analysis on current file"""
        if not HAS_TETHER_ANALYSIS:
            logger.error("Tether analysis requires tether_script module")
            return

        logger.info('Entered Tether analysis...')
        
        if not self.current_file:
            logger.warning("No file selected for analysis")
            return
        
        # Visual feedback - disable button and show running state
        self.pushButton.setEnabled(False)
        self.pushButton.setText("Running Analysis...")
        
        # Save current parameters for this file before analysis
        self.save_parameters_for_current_file()
            
        # Get analysis parameters
        params = self.get_tether_analysis_params()
        
        try:
            # Run tether analysis using process_single_file
            file_path = self.current_file.filemetadata['file_path']
            result = process_single_file(file_path, params, save_plots=False)
            
            self.current_analysis_result = result
            
            # Store result in session results
            self.session_results[file_path] = result
            
            # Update plateau table and velocity indicators
            self.update_plateau_table(result)
            self.update_velocity_indicators(result)
            
            # Update plots
            self.update_plot_with_analysis(result)
            
            logger.info(f'Tether analysis completed: found {len(result["plateaus"])} plateaus')
            
        except Exception as e:
            logger.error(f"Tether analysis failed: {e}")
            self.reset_velocity_indicators()
        finally:
            # Re-enable button
            self.pushButton.setEnabled(True)
            self.pushButton.setText("Analyze Tether")

    def get_tether_analysis_params(self):
        """Extract tether analysis parameters from the parameter tree"""
        tether_params = self.params.child('Tether Params')
        params = {
            'sav_window_length': tether_params.child('Savitzky Window Length').value(),
            'sav_polyorder': tether_params.child('Savitzky Poly Order').value(),
            'pl_threshold': tether_params.child('Plateau Threshold').value(),
            'pl_min_width': tether_params.child('Min Plateau Width').value(),
            'last_num_plateaus': tether_params.child('Max Plateaus').value(),
            'last_plateau_avg_percentage': tether_params.child('Last Plateau Avg (%)').value(),
            'max_offset': self.params.child('Analysis Params').child('Perc. Max Offset').value(),
            'min_offset': self.params.child('Analysis Params').child('Perc. Min Offset').value(),
            'z_sensor_delay': tether_params.child('Z Sensor Delay').value(),
            'bool_correct_overshoot': tether_params.child('Correct Overshoot').value(),
        }
        return params

    def get_file_parameters(self, file_path):
        """Get stored parameters for a specific file"""
        return self.file_parameters.get(file_path, self.get_default_parameters())
    
    def get_default_parameters(self):
        """Get default analysis parameters"""
        return {
            'sav_window_length': 151,
            'sav_polyorder': 3,
            'pl_threshold': 0.02,
            'pl_min_width': 100,
            'last_num_plateaus': 10,
            'last_plateau_avg_percentage': 80,
            'max_offset': 90,
            'min_offset': 10,
            'z_sensor_delay': 1e-3,
            'bool_correct_overshoot': True,
        }
    
    def set_file_parameters(self, file_path, params):
        """Store parameters for a specific file"""
        self.file_parameters[file_path] = params.copy()
    
    def load_parameters_for_current_file(self):
        """Load parameters for the currently selected file"""
        if not self.current_file:
            return
            
        file_path = self.current_file.filemetadata['file_path']
        params = self.get_file_parameters(file_path)
        
        # Update parameter tree with file-specific parameters
        try:
            tether_params = self.params.child('Tether Params')
            tether_params.child('Savitzky Window Length').setValue(params['sav_window_length'])
            tether_params.child('Savitzky Poly Order').setValue(params['sav_polyorder'])
            tether_params.child('Plateau Threshold').setValue(params['pl_threshold'])
            tether_params.child('Min Plateau Width').setValue(params['pl_min_width'])
            tether_params.child('Max Plateaus').setValue(params['last_num_plateaus'])
            tether_params.child('Last Plateau Avg (%)').setValue(params['last_plateau_avg_percentage'])
            tether_params.child('Z Sensor Delay').setValue(params['z_sensor_delay'])
            tether_params.child('Correct Overshoot').setValue(params['bool_correct_overshoot'])
            
            analysis_params = self.params.child('Analysis Params')
            analysis_params.child('Perc. Max Offset').setValue(params['max_offset'])
            analysis_params.child('Perc. Min Offset').setValue(params['min_offset'])
        except Exception as e:
            logger.warning(f"Could not load parameters for file: {e}")
    
    def save_parameters_for_current_file(self):
        """Save current parameters for the current file"""
        if not self.current_file:
            return
            
        file_path = self.current_file.filemetadata['file_path']
        params = self.get_tether_analysis_params()
        self.set_file_parameters(file_path, params)

    def setup_plateau_table(self):
        """Setup the plateau results table"""
        headers = ['Include', 'Plateau #', 'Avg Force (N)', 'ΔAvg (N)', 'ΔTime (s)', 'x̄(dy/dx)', 'Slope', 'Vel (μm/s)']
        self.plateau_table.setColumnCount(len(headers))
        self.plateau_table.setHorizontalHeaderLabels(headers)
        self.plateau_table.setAlternatingRowColors(True)
        self.plateau_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plateau_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.plateau_table.setMinimumHeight(200)
        self.plateau_table.setMaximumHeight(300)

    def update_plateau_table(self, result):
        """Update the plateau table with analysis results"""
        if not result or not result['plateaus']:
            self.plateau_table.setRowCount(0)
            self.reset_velocity_indicators()
            return
            
        df_plat = result['df_plat']
        self.plateau_table.setRowCount(len(df_plat))
        
        # Get current file identifier for plateau selection storage
        current_file = self.current_file.filemetadata['file_path']
        
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
        """Update velocity indicator labels"""
        if result:
            calc_vel = result.get('velocity_calc_um_s', 0)
            meta_vel = result.get('velocity_metadata', 0)
            self.calc_ret_vel_label.setText(f"Calc Ret Vel: {calc_vel:.1f} μm/s")
            self.meta_ret_vel_label.setText(f"Meta Ret Vel: {meta_vel:.1f} μm/s")
        else:
            self.reset_velocity_indicators()

    def reset_velocity_indicators(self):
        """Reset velocity indicators to default"""
        self.calc_ret_vel_label.setText("Calc Ret Vel: -- μm/s")
        self.meta_ret_vel_label.setText("Meta Ret Vel: -- μm/s")

    def on_plateau_selection_changed(self, row, file_path, checked):
        """Handle plateau selection changes"""
        if file_path in self.plateau_selections:
            if row < len(self.plateau_selections[file_path]):
                self.plateau_selections[file_path][row] = checked
                self.update_plot_plateau_visibility()

    def select_all_plateaus(self):
        """Select all plateaus"""
        if not self.current_file:
            return
        current_file = self.current_file.filemetadata['file_path']
        if current_file in self.plateau_selections:
            self.plateau_selections[current_file] = [True] * len(self.plateau_selections[current_file])
            for row in range(self.plateau_table.rowCount()):
                checkbox = self.plateau_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)

    def select_no_plateaus(self):
        """Deselect all plateaus"""
        if not self.current_file:
            return
        current_file = self.current_file.filemetadata['file_path']
        if current_file in self.plateau_selections:
            self.plateau_selections[current_file] = [False] * len(self.plateau_selections[current_file])
            for row in range(self.plateau_table.rowCount()):
                checkbox = self.plateau_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)

    def export_selected_plateaus(self):
        """Export selected plateau data to CSV"""
        if not self.current_analysis_result or not self.current_file:
            return
            
        result = self.current_analysis_result
        if not result['df_plat'].shape[0]:
            return
            
        current_file = self.current_file.filemetadata['file_path']
        if current_file not in self.plateau_selections:
            return
            
        selected_indices = [i for i, selected in enumerate(self.plateau_selections[current_file]) if selected]
        if not selected_indices:
            logger.info("No plateaus selected for export")
            return
            
        df_plat = result['df_plat']
        selected_df = df_plat.iloc[selected_indices].copy()
        
        # Generate export filename
        filename = os.path.basename(result['filename'])
        base_name = os.path.splitext(filename)[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"{base_name}_selected_plateaus_{timestamp}.csv"
        export_path = os.path.join(os.path.dirname(result['filename']), export_filename)
        
        # Save CSV
        selected_df.to_csv(export_path, index=False)
        
        # Save metadata
        metadata_path = export_path.replace('.csv', '_metadata.json')
        export_data = {
            'filename': filename,
            'total_plateaus_found': len(df_plat),
            'selected_plateaus': len(selected_indices),
            'selected_indices': selected_indices,
            'export_timestamp': timestamp
        }
        with open(metadata_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported {len(selected_indices)} plateaus to {export_path}")

    def mark_file_good(self):
        """Mark current file as good"""
        if not self.current_file:
            return
        file_path = self.current_file.filemetadata['file_path']
        self.file_status[file_path] = 'good'
        self.update_file_status_display()
        logger.info(f"Marked file as good: {os.path.basename(file_path)}")
    
    def mark_file_bad(self):
        """Mark current file as bad"""
        if not self.current_file:
            return
        file_path = self.current_file.filemetadata['file_path']
        self.file_status[file_path] = 'bad'
        self.update_file_status_display()
        logger.info(f"Marked file as bad: {os.path.basename(file_path)}")
    
    def update_file_status_display(self):
        """Update the file status label"""
        if not self.current_file:
            self.file_status_label.setText("Status: --")
            return
            
        file_path = self.current_file.filemetadata['file_path']
        status = self.file_status.get(file_path, 'unset')
        
        if status == 'good':
            self.file_status_label.setText("Status: ✓ Good")
            self.file_status_label.setStyleSheet("QLabel { background-color: #E8F5E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: green; }")
        elif status == 'bad':
            self.file_status_label.setText("Status: ✗ Bad")
            self.file_status_label.setStyleSheet("QLabel { background-color: #FFE8E8; padding: 3px 6px; border-radius: 3px; font-size: 10px; color: red; }")
        else:
            self.file_status_label.setText("Status: -- Unset")
            self.file_status_label.setStyleSheet("QLabel { background-color: #F5F5F5; padding: 3px 6px; border-radius: 3px; font-size: 10px; }")

    def save_session(self):
        """Save current session including parameters, results, and file status"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Tether Analysis Session", 
            "", "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            if selected_filter == "CSV Files (*.csv)" or file_path.endswith('.csv'):
                self.save_csv_session(file_path)
            else:
                self.save_json_session(file_path)
                
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def save_json_session(self, file_path):
        """Save session as JSON file"""
        session_data = {
            'file_parameters': self.file_parameters,
            'file_status': self.file_status,
            'session_results': self.session_results,
            'plateau_selections': self.plateau_selections,
            'timestamp': datetime.datetime.now().isoformat(),
            'session_type': 'tether_analysis'
        }
        
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        self.current_session_file = file_path
        logger.info(f"JSON session saved to {file_path}")
    
    def save_csv_session(self, file_path):
        """Save session as CSV file (compatible with original tether_analysis_gui_v2)"""
        # Create a list to store session data
        session_rows = []
        
        # Get all unique file paths from parameters and status
        all_files = set(self.file_parameters.keys()) | set(self.file_status.keys())
        
        for file_path_key in all_files:
            row_data = {'filename': file_path_key}
            
            # Add file status
            row_data['status'] = self.file_status.get(file_path_key, 'unset')
            
            # Add parameters if available
            if file_path_key in self.file_parameters:
                params = self.file_parameters[file_path_key]
                row_data.update(params)
            else:
                # Add default parameters
                row_data.update(self.get_default_parameters())
            
            # Add analysis summary if available
            if file_path_key in self.session_results:
                result = self.session_results[file_path_key]
                row_data['num_plateaus'] = len(result.get('plateaus', []))
                row_data['velocity_calc'] = result.get('velocity_calc_um_s', 0)
                row_data['velocity_metadata'] = result.get('velocity_metadata', 0)
            
            session_rows.append(row_data)
        
        # Create DataFrame and save
        if session_rows:
            df = pd.DataFrame(session_rows)
            df.to_csv(file_path, index=False)
            self.current_session_file = file_path
            logger.info(f"CSV session saved to {file_path}")
            logger.info(f"Saved {len(session_rows)} file entries")
        else:
            logger.warning("No session data to save")

    def export_batch_results(self):
        """Export all session results to a batch CSV file"""
        from PyQt5.QtWidgets import QFileDialog
        
        if not self.session_results:
            logger.warning("No analysis results to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Batch Analysis Results", 
            "", "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            batch_rows = []
            
            for file_path_key, result in self.session_results.items():
                if 'df_plat' not in result or result['df_plat'].empty:
                    continue
                
                df_plat = result['df_plat']
                file_status = self.file_status.get(file_path_key, 'unset')
                file_params = self.file_parameters.get(file_path_key, {})
                
                # Get selected plateaus for this file
                selected_indices = []
                if file_path_key in self.plateau_selections:
                    selected_indices = [i for i, selected in enumerate(self.plateau_selections[file_path_key]) if selected]
                else:
                    selected_indices = list(range(len(df_plat)))  # All selected by default
                
                # Add each selected plateau as a row
                for idx in selected_indices:
                    if idx < len(df_plat):
                        plat_data = df_plat.iloc[idx]
                        row = {
                            'filename': os.path.basename(file_path_key),
                            'full_path': file_path_key,
                            'file_status': file_status,
                            'plateau_number': int(plat_data['plateaus']),
                            'plateau_avg_force': plat_data['plateau_avg'],
                            'delta_avg': plat_data['delta_avg'],
                            'delta_time': plat_data['delta_time'],
                            'velocity_calc_um_s': result.get('velocity_calc_um_s', 0),
                            'velocity_metadata': result.get('velocity_metadata', 0),
                            'total_plateaus_found': len(df_plat),
                            'selected_plateaus': len(selected_indices)
                        }
                        
                        # Add plateau-specific data if available
                        if 'mean dN/dt' in plat_data:
                            row['mean_dNdt'] = plat_data['mean dN/dt']
                        if 'plateau_slope' in plat_data:
                            row['plateau_slope'] = plat_data['plateau_slope']
                        if 'velocity_calc_um_s' in plat_data:
                            row['plateau_velocity'] = plat_data['velocity_calc_um_s']
                        
                        # Add some key parameters
                        for param_key in ['sav_window_length', 'sav_polyorder', 'pl_threshold', 'pl_min_width']:
                            if param_key in file_params:
                                row[param_key] = file_params[param_key]
                        
                        batch_rows.append(row)
            
            if batch_rows:
                df_batch = pd.DataFrame(batch_rows)
                df_batch.to_csv(file_path, index=False)
                
                # Also save summary statistics
                summary_path = file_path.replace('.csv', '_summary.csv')
                summary_rows = []
                
                for file_path_key, result in self.session_results.items():
                    if 'df_plat' not in result or result['df_plat'].empty:
                        continue
                    
                    selected_count = len([i for i, selected in enumerate(self.plateau_selections.get(file_path_key, [])) if selected])
                    if selected_count == 0:
                        selected_count = len(result['df_plat'])  # All selected by default
                    
                    summary_rows.append({
                        'filename': os.path.basename(file_path_key),
                        'full_path': file_path_key,
                        'file_status': self.file_status.get(file_path_key, 'unset'),
                        'total_plateaus': len(result['df_plat']),
                        'selected_plateaus': selected_count,
                        'velocity_calc_um_s': result.get('velocity_calc_um_s', 0),
                        'velocity_metadata': result.get('velocity_metadata', 0)
                    })
                
                if summary_rows:
                    df_summary = pd.DataFrame(summary_rows)
                    df_summary.to_csv(summary_path, index=False)
                    logger.info(f"Batch results exported to {file_path}")
                    logger.info(f"Summary exported to {summary_path}")
                    logger.info(f"Exported {len(batch_rows)} plateau entries from {len(summary_rows)} files")
                
            else:
                logger.warning("No plateau data to export")
                
        except Exception as e:
            logger.error(f"Failed to export batch results: {e}")
    
    def load_session(self):
        """Load a previously saved session"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Tether Analysis Session", 
            "", "Session Files (*.json *.csv);;JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.csv'):
                self.load_csv_session(file_path)
            else:
                self.load_json_session(file_path)
                
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
    
    def load_json_session(self, file_path):
        """Load JSON session file"""
        with open(file_path, 'r') as f:
            session_data = json.load(f)
        
        # Validate session type
        if session_data.get('session_type') != 'tether_analysis':
            logger.warning("Invalid session file format")
            return
        
        # Load session data
        self.file_parameters = session_data.get('file_parameters', {})
        self.file_status = session_data.get('file_status', {})
        self.session_results = session_data.get('session_results', {})
        self.plateau_selections = session_data.get('plateau_selections', {})
        self.current_session_file = file_path
        
        # Update current file parameters and status
        self.load_parameters_for_current_file()
        self.update_file_status_display()
        
        # Load analysis results if available for current file
        if self.current_file:
            current_file_path = self.current_file.filemetadata['file_path']
            if current_file_path in self.session_results:
                self.current_analysis_result = self.session_results[current_file_path]
                self.update_plateau_table(self.current_analysis_result)
                self.update_velocity_indicators(self.current_analysis_result)
                self.update_plot_with_analysis(self.current_analysis_result)
        
        logger.info(f"JSON session loaded from {file_path}")
        logger.info(f"Loaded {len(self.file_parameters)} file parameter sets")
    
    def load_csv_session(self, file_path):
        """Load CSV session file (original tether_analysis_gui_v2 format)"""        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Extract file information from CSV
            # The CSV format should have columns for file paths, parameters, and status
            if 'filename' not in df.columns:
                logger.error("Invalid CSV session format - missing 'filename' column")
                return
            
            # Load file status if available
            if 'status' in df.columns:
                for _, row in df.iterrows():
                    filename = row['filename']
                    status = row.get('status', 'unset')
                    self.file_status[filename] = status
            
            # Load parameters if available (look for parameter columns)
            param_columns = [
                'sav_window_length', 'sav_polyorder', 'pl_threshold', 'pl_min_width',
                'last_num_plateaus', 'last_plateau_avg_percentage', 'max_offset', 
                'min_offset', 'z_sensor_delay', 'bool_correct_overshoot'
            ]
            
            for _, row in df.iterrows():
                filename = row['filename']
                file_params = {}
                
                # Extract available parameters
                for param in param_columns:
                    if param in df.columns and pd.notna(row[param]):
                        file_params[param] = row[param]
                
                # If we found parameters, store them
                if file_params:
                    # Fill in missing parameters with defaults
                    default_params = self.get_default_parameters()
                    for key, default_value in default_params.items():
                        if key not in file_params:
                            file_params[key] = default_value
                    
                    self.file_parameters[filename] = file_params
            
            self.current_session_file = file_path
            
            # Update current file if loaded
            if self.current_file:
                self.load_parameters_for_current_file()
                self.update_file_status_display()
            
            logger.info(f"CSV session loaded from {file_path}")
            logger.info(f"Loaded {len(self.file_parameters)} file parameter sets")
            logger.info(f"Loaded {len(self.file_status)} file status entries")
            
        except Exception as e:
            logger.error(f"Failed to load CSV session: {e}")
            # Try alternative CSV format - maybe it's just a simple file list
            try:
                # Simple fallback - just read filenames and set default status
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                for line in lines[1:]:  # Skip header
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Assume first column is filename
                        parts = line.split(',')
                        if parts:
                            filename = parts[0].strip('"')
                            self.file_status[filename] = 'unset'
                            # Set default parameters
                            self.file_parameters[filename] = self.get_default_parameters()
                
                logger.info(f"Loaded CSV as simple file list: {len(self.file_status)} files")
                
            except Exception as e2:
                logger.error(f"Failed to load CSV as simple file list: {e2}")
                raise e

    def on_parameter_changed(self, param, changes):
        """Handle parameter changes - automatically save for current file"""
        if self.current_file:
            self.save_parameters_for_current_file()

    def update_plot_plateau_visibility(self):
        """Update plot to show only selected plateaus"""
        if self.current_analysis_result:
            self.update_plot_with_analysis(self.current_analysis_result)

    def update_plot_with_analysis(self, result):
        """
        Visualize tether analysis results in the same way as tether_analysis_gui_v2.
        """
        if not result:
            return

        # Clear the main plot
        self.main_plot.clear()
        
        # Add legend with top-right positioning
        legend = self.main_plot.addLegend(offset=(30, 30))
        legend.anchor = (1, 0)  # Top-right anchor
        
        # Plot raw data if available
        if 'raw_data' in result:
            rel_time = result['rel_time']
            raw_defl = result['raw_data']
            self.main_plot.plot(rel_time, raw_defl,
                               pen=pg.mkPen(color='lightgray', width=1),
                               name='Raw Data')

        # Plot processed data
        rel_time = result['rel_time']
        defl_savitz = result['defl_savitz']
        self.main_plot.plot(rel_time, defl_savitz,
                           pen=pg.mkPen(color='blue', width=2),
                           name='Processed Data')

        # Plot plateaus (only selected)
        plateaus = result['plateaus']
        df_plat = result['df_plat']
        current_file = self.current_file.filemetadata['file_path']
        
        # Define colors for plateaus
        colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta', 'yellow']
        
        if current_file in self.plateau_selections:
            selected_plateaus = [i for i, selected in enumerate(self.plateau_selections[current_file]) if selected]
            displayed_count = 0

            for i, (start, end) in enumerate(plateaus):
                if i in selected_plateaus:
                    color = colors[displayed_count % len(colors)]
                    
                    # Plateau region
                    self.main_plot.plot(rel_time[start:end], defl_savitz[start:end],
                                       pen=pg.mkPen(color=color, width=3),
                                       name=f'Plateau {i+1}')
                    
                    # Average line
                    plateau_avg = np.mean(defl_savitz[start:end])
                    self.main_plot.plot([rel_time[start], rel_time[end-1]],
                                       [plateau_avg, plateau_avg],
                                       pen=pg.mkPen(color=color, width=2, style=pg.QtCore.Qt.DashLine))
                    
                    # Plateau center marker
                    if i < len(df_plat) and 'plateau_avg_idx' in df_plat.columns:
                        idx = df_plat['plateau_avg_idx'].iloc[i]
                        if idx < len(rel_time):
                            self.main_plot.plot([rel_time[idx]], [defl_savitz[idx]],
                                               pen=None, symbol='o', symbolSize=8,
                                               symbolBrush=color)
                    displayed_count += 1
        else:
            # If no specific selections, show all plateaus
            for i, (start, end) in enumerate(plateaus):
                color = colors[i % len(colors)]
                
                # Plateau region
                self.main_plot.plot(rel_time[start:end], defl_savitz[start:end],
                                   pen=pg.mkPen(color=color, width=3),
                                   name=f'Plateau {i+1}')
                
                # Average line
                plateau_avg = np.mean(defl_savitz[start:end])
                self.main_plot.plot([rel_time[start], rel_time[end-1]],
                                   [plateau_avg, plateau_avg],
                                   pen=pg.mkPen(color=color, width=2, style=pg.QtCore.Qt.DashLine))

        # Set labels and title
        self.main_plot.setLabel('left', 'Deflection', 'N')
        self.main_plot.setLabel('bottom', 'Time', 's')
        self.main_plot.setTitle("Tether Analysis - Plateau Detection")
    
    def update(self):
        self.current_file = self.session.current_file
        
        # Load parameters and status for current file
        if self.current_file:
            self.load_parameters_for_current_file()
            self.update_file_status_display()
        
        self.updateParams()
        self.l2.clear()
        if self.current_file.isFV:
            self.l2.addItem(self.plotItem)
            self.plotItem.addItem(self.ROI)
            self.plotItem.scene().sigMouseClicked.connect(self.mouseMoved)
            # create transform to center the corner element on the origin, for any assigned image:
            if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
                img = self.session.current_file.imagedata.get('Height(measured)', None)
                if img is None:
                    img = self.session.current_file.imagedata.get('Height', None)
                img = np.rot90(np.fliplr(img))
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
                if self.current_file.filemetadata['file_type'] == "jpk-force-map":
                    curve_coords = np.asarray([row[::(-1)**i] for i, row in enumerate(curve_coords)])
                curve_coords = np.rot90(np.fliplr(curve_coords))
            elif self.session.current_file.filemetadata['file_type'] in cts.nanoscope_file_extensions:
                img = self.session.current_file.piezoimg
                img = np.rot90(np.fliplr(img))

                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
                curve_coords = np.rot90(np.fliplr(curve_coords))

            self.correlogram.setImage(img)

            self.session.map_coords = curve_coords
        self.session.current_curve_index = 0
        self.ROI.setPos(0, 0)
        self.updatePlots()
    
    def file_changed(self, file_id):
        if file_id != '':
            # Save parameters for the previous file
            if self.current_file:
                self.save_parameters_for_current_file()
            
            # Switch to new file
            self.session.current_file = self.session.loaded_files[file_id]
            self.session.current_curve_index = 0
            
            # Load parameters and status for the new file
            self.load_parameters_for_current_file()
            self.update_file_status_display()
            
            # Load analysis results if available
            file_path = self.session.current_file.filemetadata['file_path']
            if file_path in self.session_results:
                self.current_analysis_result = self.session_results[file_path]
                self.update_plateau_table(self.current_analysis_result)
                self.update_velocity_indicators(self.current_analysis_result)
            else:
                self.current_analysis_result = None
                self.plateau_table.setRowCount(0)
                self.reset_velocity_indicators()
            
            self.update()
    
    def updateCombo(self):
        self.combobox.clear()
        self.combobox.addItems(self.session.loaded_files.keys())
        index = self.combobox.findText(self.current_file.filemetadata['Entry_filename'], QtCore.Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.combobox.setCurrentIndex(index)
        self.update()
    
    def mouseMoved(self,event):
        vb = self.plotItem.vb
        scene_coords = event.scenePos()
        if self.correlogram.sceneBoundingRect().contains(scene_coords):
            items = vb.mapSceneToView(event.scenePos())
            pixels = vb.mapFromViewToItem(self.correlogram, items)
            x, y = int(pixels.x()), int(pixels.y())
            self.ROI.setPos(x, y)
            self.session.current_curve_index = self.session.map_coords[x,y]
            self.updatePlots()
            if self.session.data_viewer_widget is not None:
                self.session.data_viewer_widget.ROI.setPos(x, y)
                self.session.data_viewer_widget.updateCurve()
    
    def manual_override(self):
        pass

    def updatePlots(self):
        if not self.current_file:
            return
        
        # Check if we have tether analysis results for this file
        if self.current_analysis_result and self.current_analysis_result.get('filename') == self.current_file.filemetadata['file_path']:
            # Use tether analysis visualization with single main plot
            self.update_plot_with_analysis(self.current_analysis_result)
            return
        
        # For non-tether analysis, clear the main plot and show a default message
        self.main_plot.clear()
        self.main_plot.setLabel('left', 'Force', 'N')
        self.main_plot.setLabel('bottom', 'Time or Indentation', 'm')
        self.main_plot.setTitle("Click 'Analyze Tether' to run tether analysis")
        
                # Add instruction text
        text_item = pg.TextItem("Run tether analysis to see plateau detection results", 
                               anchor=(0.5, 0.5), color='gray')
        text_item.setPos(0.5, 0.5)
        self.main_plot.addItem(text_item)
    
    def changestep(self, step):
        self.session.pbar_widget.set_label_sub_text(step)
    
    def reportProgress(self, n):
        self.session.pbar_widget.set_pbar_value(n)
    
    def setPbarRange(self, n):
        self.session.pbar_widget.set_pbar_range(0, n)
    
    def oncomplete(self):
        if hasattr(self, 'thread'):
            self.thread.terminate()
        self.session.pbar_widget.hide()
        self.session.pbar_widget.reset_pbar()
        self.pushButton.setEnabled(True)
        self.updatePlots()
        logger.info('Analysis completed!')

    def updateParams(self):
        # Updates params related to the current file
        if not self.current_file:
            return
            
        analysis_params = self.params.child('Analysis Params')
        
        # Only update if the parameters exist (they may not for tether analysis)
        try:
            analysis_params.child('Height Channel').setValue(self.current_file.filemetadata['height_channel_key'])
            if self.session.global_k is None:
                analysis_params.child('Spring Constant').setValue(self.current_file.filemetadata['spring_const_Nbym'])
            else:
                analysis_params.child('Spring Constant').setValue(self.session.global_k)
            if self.session.global_involts is None:
                analysis_params.child('Deflection Sensitivity').setValue(self.current_file.filemetadata['defl_sens_nmbyV'])
            else:
                analysis_params.child('Deflection Sensitivity').setValue(self.session.global_involts)
        except Exception:
            # Parameters may not exist for tether analysis mode
            pass