import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np
import logging
logger = logging.getLogger()

import pyfmgui.const as cts
from pyfmgui.threading import Worker
from pyfmgui.compute import compute
from pyfmgui.widgets.get_params import get_params

from pyfmrheo.utils.force_curves import get_poc_RoV_method, get_poc_regulaFalsi_method, correct_tilt, correct_offset

class HertzFitWidget(QtWidgets.QWidget):
    def __init__(self, session, parent=None):
        super(HertzFitWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.min_val_line = None
        self.max_val_line = None
        self.offset_roi = None
        self.file_dict = {}
        self.session.hertz_fit_widget = self
        self.init_gui()
        if self.session.loaded_files != {}:
            self.updateCombo()

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_hertzfit)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.currentTextChanged.connect(self.file_changed)

        self.params = Parameter.create(name='params', children=cts.hertzfit_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        # added by Lorenzo
        self.correct_app = self.params.child('General Options').child('Correct App')
        self.correct_app.sigValueChanged.connect(self.update)
        

        self.l2 = pg.GraphicsLayoutWidget()

        self.exportHtmlButton = QtWidgets.QPushButton("Export HTML")
        self.exportHtmlButton.clicked.connect(self.export_hertz_html)

        # File range row
        range_layout = QtWidgets.QHBoxLayout()
        range_layout.addWidget(QtWidgets.QLabel("Files:"))
        range_layout.addWidget(QtWidgets.QLabel("From"))
        self.exportRangeFrom = QtWidgets.QSpinBox()
        self.exportRangeFrom.setMinimum(1)
        self.exportRangeFrom.setValue(1)
        range_layout.addWidget(self.exportRangeFrom)
        range_layout.addWidget(QtWidgets.QLabel("To"))
        self.exportRangeTo = QtWidgets.QSpinBox()
        self.exportRangeTo.setMinimum(1)
        self.exportRangeTo.setValue(1)
        range_layout.addWidget(self.exportRangeTo)

        params_layout.addWidget(self.combobox, 1)
        params_layout.addWidget(self.paramTree, 3)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addWidget(self.exportHtmlButton, 1)
        params_layout.addLayout(range_layout)
        params_layout.addWidget(self.l2, 2)

        self.l = pg.GraphicsLayoutWidget()
        
        ## Add 3 plots into the first row (automatic position)
        self.plotItem = pg.PlotItem(lockAspect=True)
        vb = self.plotItem.getViewBox()
        vb.setAspectLocked(lock=True, ratio=1)

        self.ROI = pg.ROI([0,0], [1,1], movable=False, rotatable=False, resizable=False, removable=False, aspectLocked=True)
        self.ROI.setPen("r", linewidht=2)
        self.ROI.setZValue(10)

        self.correlogram = pg.ImageItem(lockAspect=True)
        self.plotItem.addItem(self.correlogram)    # display correlogram
        
        self.p1 = pg.PlotItem()
        self.p2 = pg.PlotItem()
        self.p2legend = self.p2.addLegend()
        self.p3 = pg.PlotItem()
        self.p4 = pg.PlotItem()

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.hertz_fit_widget = None
    
    def clear(self):
        self.combobox.clear()
        self.l.clear()
        self.l2.clear()

    def do_hertzfit(self):
        if not self.current_file:
            return
        if self.params.child('General Options').child('Compute All Files').value():
            filedict = self.session.loaded_files
        else:
            filedict = {self.session.current_file.filemetadata['Entry_filename']:self.session.current_file}
        if self.params.child('General Options').child('Correct App').value():
            print('trueDat')
            logger.info('correct app is true')
        params = get_params(self.params, "HertzFit")
        logger.info('Started ElasticityFit...')
        logger.info(f'Processing {len(filedict)} files')
        logger.info(f'Analysis parameters used: {params}')
        self.session.pbar_widget.reset_pbar()
        self.session.pbar_widget.set_label_text('Computing ElasticityFit...')
        self.session.pbar_widget.show()
        # Create thread to run compute
        self.thread = QtCore.QThread()
        # Create worker to run compute
        self.worker = Worker(compute, self.session, params, filedict, "HertzFit")
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        # When thread starts run worker
        self.thread.started.connect(self.worker.run)
        self.worker.signals.progress.connect(self.reportProgress)
        self.worker.signals.range.connect(self.setPbarRange)
        self.worker.signals.step.connect(self.changestep)
        self.worker.signals.finished.connect(self.oncomplete) # Reset button
        # Start thread
        self.thread.start()
        # Final resets
        self.pushButton.setEnabled(False) # Prevent user from starting another
        # Update the gui
        self.updatePlots()
    
    def changestep(self, step):
        self.session.pbar_widget.set_label_sub_text(step)
    
    def reportProgress(self, n):
        self.session.pbar_widget.set_pbar_value(n)
    
    def setPbarRange(self, n):
        self.session.pbar_widget.set_pbar_range(0, n)
    
    def oncomplete(self):
        self.thread.terminate()
        self.session.pbar_widget.hide()
        self.session.pbar_widget.reset_pbar()
        self.pushButton.setEnabled(True)
        self.updatePlots()
        logger.info('ElasticityFit completed!')

    def update(self):
        self.current_file = self.session.current_file
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
            self.session.current_file = self.session.loaded_files[file_id]
            self.session.current_curve_index = 0
            self.update()
    
    def updateCombo(self):
        self.combobox.clear()
        self.combobox.addItems(self.session.loaded_files.keys())
        index = self.combobox.findText(self.current_file.filemetadata['Entry_filename'], QtCore.Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.combobox.setCurrentIndex(index)
        n_files = len(self.session.loaded_files)
        self.exportRangeFrom.setMaximum(n_files)
        self.exportRangeTo.setMaximum(n_files)
        self.exportRangeTo.setValue(n_files)
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
        self.l.clear()
        self.p1.clear()
        self.p2.clear()
        self.p2legend.clear()
        self.p3.clear()
        self.p4.clear()

        self.hertz_E = None
        self.hertz_d0 = 0
        self.fit_data = None
        self.residual = None

        current_file_id = self.current_file.filemetadata['Entry_filename']
        current_curve_indx = self.session.current_curve_index
        
        analysis_params = self.params.child('Analysis Params')
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9
        spring_k = analysis_params.child('Spring Constant').value()
        curve_seg = analysis_params.child('Curve Segment').value()
        correct_tilt_flag = analysis_params.child('Correct Tilt').value()
        
        hertz_params = self.params.child('Hertz Fit Params')
        poc_method = hertz_params.child('PoC Method').value()
        poc_win = hertz_params.child('PoC Window').value() / 1e9
        poc_sigma = hertz_params.child('Sigma').value()

        print(self.current_file)
        print(type(self.current_file))
        print(self.current_file.filemetadata['file_path'])
        ## added 
        # bool_correct_overshoot = self.params.child('Display Options').child('Correct Overshoot').value()    
        force_curve = self.current_file.getcurve(current_curve_indx, bool_correct_overshoot = self.params.child('General Options').child('Correct App').value())
        force_curve.preprocess_force_curve(deflection_sens, height_channel)

        if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()

        file_hertz_result = self.session.hertz_fit_results.get(current_file_id, None)

        # print(file_hertz_result)
        # print(current_file_id)

        if file_hertz_result is not None:
            for curve_indx, curve_hertz_result in file_hertz_result:
                try:
                    if curve_hertz_result is None:
                        continue
                    if curve_indx == self.session.current_curve_index:
                        self.hertz_E = curve_hertz_result.E0
                        self.hertz_d0 = curve_hertz_result.delta0
                        self.hertz_f0 = curve_hertz_result.f0
                        self.hertz_redchi = curve_hertz_result.redchi
                        self.fit_data = curve_hertz_result
                except Exception:
                    continue

        ext_data = force_curve.extend_segments[0][1]
        ret_data = force_curve.retract_segments[-1][1]

        self.p3.plot(ext_data.zheight, ext_data.vdeflection)
        self.p3.plot(ret_data.zheight, ret_data.vdeflection)

        if curve_seg == 'extend': self.seg_data  = ext_data
        else: self.seg_data  = ret_data
        
        self.update_tilt_range()

        # Perform tilt correction
        if correct_tilt_flag:
            self.seg_data.vdeflection = correct_tilt(
                self.seg_data.zheight, self.seg_data.vdeflection, self.maxoffset, self.minoffset
            )
        else:
            self.seg_data.vdeflection = correct_offset(
                self.seg_data.zheight, self.seg_data.vdeflection, self.maxoffset, self.minoffset
            )

        comp_PoC = [0, 0]
        
        if poc_method == 'RoV':
            comp_PoC = get_poc_RoV_method(self.seg_data.zheight, self.seg_data.vdeflection, poc_win)
        else:
            comp_PoC = get_poc_regulaFalsi_method(self.seg_data.zheight, self.seg_data.vdeflection, poc_sigma)

        if comp_PoC is not None:
            poc = [comp_PoC[0], 0]
        else:
            poc = [0, 0]

        self.poc = poc

        force_curve.get_force_vs_indentation(poc, spring_k)

        if curve_seg == 'extend':
            self.indentation  = ext_data.indentation
            self.force = ext_data.force
            self.force = self.force - self.force[0]
            
        else:
            self.indentation  = ret_data.indentation
            self.force = ret_data.force
            self.force = self.force - self.force[-1]
        
        if hertz_params.child('Downsample Signal').value():
            pts_downsample = hertz_params.child('Downsample Pts.').value()
            downfactor= len(self.indentation) // pts_downsample
            idxDown = list(range(0, len(self.indentation), downfactor))
            self.indentation = self.indentation[idxDown]
            self.force = self.force[idxDown]

        self.p1.plot(self.indentation, self.force)
        vertical_line = pg.InfiniteLine(pos=0, angle=90, pen='y', movable=False, label='Init d0', labelOpts={'color':'y', 'position':0.5})
        self.p1.addItem(vertical_line, ignoreBounds=True)
        if self.hertz_d0 != 0:
            d0_vertical_line = pg.InfiniteLine(pos=self.hertz_d0, angle=90, pen='g', movable=False, label='Hertz d0', labelOpts={'color':'g', 'position':0.7})
            self.p1.addItem(d0_vertical_line, ignoreBounds=True)

        self.p2.plot(self.indentation - self.hertz_d0, self.force)

        self.update_fit_range()
 
        if self.fit_data is not None:
            x = self.indentation
            y = self.fit_data.eval(x)
            self.p2.plot(x - self.hertz_d0, y, pen ='g', name='Fit')
            style = pg.PlotDataItem(pen=None)
            self.p2legend.addItem(style, f'Hertz E: {self.hertz_E:.2f} Pa')
            self.p2legend.addItem(style, f'Hertz d0: {self.hertz_d0 + poc[0]:.3E} m')
            self.p2legend.addItem(style, f'Red. Chi: {self.hertz_redchi:.3E}')
            res = self.p4.plot(x - self.hertz_d0, self.fit_data.get_residuals(x, self.force), pen=None, symbol='o')
            res.setSymbolSize(5)
        
        self.p1.setLabel('left', 'Force', 'N')
        self.p1.setLabel('bottom', 'Indentation', 'm')
        self.p1.setTitle("Force-Indentation")
        self.p1.addLegend()
        self.p2.setLabel('left', 'Force', 'N')
        self.p2.setLabel('bottom', 'Indentation', 'm')
        self.p2.setTitle("Force-Indentation Hertz Fit")
        self.p3.setLabel('left', 'Deflection', 'm')
        self.p3.setLabel('bottom', 'zHeight', 'm')
        self.p3.setTitle('Deflection-zHeight')
        self.p4.setLabel('left', 'Residuals')
        self.p4.setLabel('bottom', 'Indentation', 'm')
        self.p4.setTitle("Hertz Fit Residuals")

        self.l.addItem(self.p1)
        self.l.addItem(self.p2)
        self.l.nextRow()
        self.l.addItem(self.p3)
        self.l.addItem(self.p4)
    
    def update_tilt_range(self):
        dataItems = self.p3.listDataItems()
        analysis_params = self.params.child('Analysis Params')
        offset_type = analysis_params.child('Offset Type').value()
        if offset_type == 'percentage':
            deltaz = self.seg_data.zheight.max() - self.seg_data.zheight.min()
            maxperc = analysis_params.child('Perc. Max Offset').value() / 1e2
            minperc = analysis_params.child('Perc. Min Offset').value() / 1e2
            self.maxoffset = self.seg_data.zheight.min() + deltaz * maxperc
            self.minoffset = self.seg_data.zheight.min() + deltaz * minperc
        else:
            self.maxoffset = analysis_params.child('Abs. Max Offset').value() / 1e9
            self.minoffset = analysis_params.child('Abs. Min Offset').value() / 1e9
        if self.offset_roi is not None:
            self.p3.removeItem(self.offset_roi)
        self.offset_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='w', movable=False)
        self.offset_roi.setZValue(10)
        self.offset_roi.setClipItem(dataItems[0])
        self.p3.removeItem(self.offset_roi)
        self.p3.addItem(self.offset_roi, ignoreBounds=True)
        self.offset_roi.setRegion([self.minoffset, self.maxoffset])

    def update_fit_range(self):
        hertz_params = self.params.child('Hertz Fit Params')
        fit_range_type = hertz_params.child('Fit Range Type').value()
        if fit_range_type == 'full':
            angle=90
            min_val = 0.0
            max_val = np.max(self.indentation - self.hertz_d0)
            hertz_params.child('Min Indentation').setValue(min_val * 1e9)
            hertz_params.child('Max Indentation').setValue(max_val * 1e9)
        elif fit_range_type == 'indentation':
            angle=90
            min_val = hertz_params.child('Min Indentation').value() / 1e9
            max_val = hertz_params.child('Max Indentation').value() / 1e9
            if max_val  == 0.0:
                max_val = np.max(self.indentation - self.hertz_d0)
                hertz_params.child('Max Indentation').setValue(max_val * 1e9)
        elif fit_range_type == 'force':
            angle=0
            min_val = hertz_params.child('Min Force').value() / 1e9
            max_val = hertz_params.child('Max Force').value() / 1e9
            if max_val  == 0.0:
                max_val = np.max(self.force)
                hertz_params.child('Max Force').setValue(max_val * 1e9)
        if self.min_val_line and self.max_val_line:
            self.p2.removeItem(self.min_val_line)
            self.p2.removeItem(self.max_val_line)
        self.min_val_line = pg.InfiniteLine(pos=min_val, angle=angle, pen='y', movable=False, label='Min', labelOpts={'color':'y', 'position':0.7})
        self.max_val_line = pg.InfiniteLine(pos=max_val, angle=angle, pen='y', movable=False, label='Max', labelOpts={'color':'y', 'position':0.7})
        self.p2.addItem(self.min_val_line, ignoreBounds=True)
        self.p2.addItem(self.max_val_line, ignoreBounds=True)

    def _process_curve_for_export(self, file_obj, curve_indx):
        """Process a single curve and return (indentation, force, poc) using current params."""
        analysis_params = self.params.child('Analysis Params')
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9
        spring_k = analysis_params.child('Spring Constant').value()
        curve_seg = analysis_params.child('Curve Segment').value()
        correct_tilt_flag = analysis_params.child('Correct Tilt').value()

        hertz_params = self.params.child('Hertz Fit Params')
        poc_method = hertz_params.child('PoC Method').value()
        poc_win = hertz_params.child('PoC Window').value() / 1e9
        poc_sigma = hertz_params.child('Sigma').value()

        force_curve = file_obj.getcurve(
            curve_indx,
            bool_correct_overshoot=self.params.child('General Options').child('Correct App').value()
        )
        force_curve.preprocess_force_curve(deflection_sens, height_channel)

        if file_obj.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()

        ext_data = force_curve.extend_segments[0][1]
        ret_data = force_curve.retract_segments[-1][1]
        seg_data = ext_data if curve_seg == 'extend' else ret_data

        # Offset range
        offset_type = analysis_params.child('Offset Type').value()
        if offset_type == 'percentage':
            deltaz = seg_data.zheight.max() - seg_data.zheight.min()
            maxperc = analysis_params.child('Perc. Max Offset').value() / 1e2
            minperc = analysis_params.child('Perc. Min Offset').value() / 1e2
            maxoffset = seg_data.zheight.min() + deltaz * maxperc
            minoffset = seg_data.zheight.min() + deltaz * minperc
        else:
            maxoffset = analysis_params.child('Abs. Max Offset').value() / 1e9
            minoffset = analysis_params.child('Abs. Min Offset').value() / 1e9

        if correct_tilt_flag:
            seg_data.vdeflection = correct_tilt(
                seg_data.zheight, seg_data.vdeflection, maxoffset, minoffset
            )
        else:
            seg_data.vdeflection = correct_offset(
                seg_data.zheight, seg_data.vdeflection, maxoffset, minoffset
            )

        comp_PoC = [0, 0]
        if poc_method == 'RoV':
            comp_PoC = get_poc_RoV_method(seg_data.zheight, seg_data.vdeflection, poc_win)
        else:
            comp_PoC = get_poc_regulaFalsi_method(seg_data.zheight, seg_data.vdeflection, poc_sigma)

        poc = [comp_PoC[0], 0] if comp_PoC is not None else [0, 0]
        force_curve.get_force_vs_indentation(poc, spring_k)

        if curve_seg == 'extend':
            indentation = ext_data.indentation
            force = ext_data.force - ext_data.force[0]
        else:
            indentation = ret_data.indentation
            force = ret_data.force - ret_data.force[-1]

        return indentation, force, poc

    def export_hertz_html(self):
        """Export Force-Indentation Hertz Fits for a range of files to an interactive HTML file."""
        if not self.current_file:
            return

        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import plotly.io as pio
            import datetime

            file_ids = list(self.session.loaded_files.keys())
            n_total = len(file_ids)
            if n_total == 0:
                return

            idx_from = self.exportRangeFrom.value() - 1   # 0-based
            idx_to = min(self.exportRangeTo.value(), n_total) - 1  # 0-based inclusive

            if idx_from > idx_to:
                idx_from, idx_to = idx_to, idx_from

            selected_ids = file_ids[idx_from: idx_to + 1]
            n_files = len(selected_ids)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"hertz_fit_export_{timestamp}.html"

            html_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export Hertz Fit as HTML",
                default_filename,
                "HTML files (*.html);;All files (*.*)"
            )

            if not html_path:
                return

            # Progress dialog
            progress = QtWidgets.QProgressDialog(
                "Exporting Hertz fits...", "Cancel", 0, n_files, self
            )
            progress.setWindowTitle("Exporting HTML")
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            n_cols = 2
            n_rows = (n_files + n_cols - 1) // n_cols

            subplot_titles = [fid[:40] for fid in selected_ids]
            if n_rows > 1:
                vertical_spacing = min(0.05, 0.8 / (n_rows - 1))
            else:
                vertical_spacing = 0.05

            fig = make_subplots(
                rows=n_rows,
                cols=n_cols,
                subplot_titles=subplot_titles,
                vertical_spacing=vertical_spacing,
                horizontal_spacing=0.08
            )

            for plot_idx, file_id in enumerate(selected_ids):
                if progress.wasCanceled():
                    progress.close()
                    return
                progress.setLabelText(f"Processing {plot_idx + 1}/{n_files}: {file_id[:50]}")
                progress.setValue(plot_idx)
                QtWidgets.QApplication.processEvents()
                row = (plot_idx // n_cols) + 1
                col = (plot_idx % n_cols) + 1
                file_obj = self.session.loaded_files[file_id]

                # Pick first curve index that has a fit result for this file
                file_hertz_result = self.session.hertz_fit_results.get(file_id, None)
                curve_indx = 0
                hertz_E = None
                hertz_d0 = 0.0
                hertz_redchi = None
                fit_data = None

                if file_hertz_result is not None:
                    for cidx, cresult in file_hertz_result:
                        if cresult is not None:
                            curve_indx = cidx
                            hertz_E = cresult.E0
                            hertz_d0 = cresult.delta0
                            hertz_redchi = cresult.redchi
                            fit_data = cresult
                            break

                try:
                    indentation, force, poc = self._process_curve_for_export(file_obj, curve_indx)
                except Exception:
                    continue

                x_plot = indentation - hertz_d0
                show_legend = plot_idx == 0

                fig.add_trace(go.Scatter(
                    x=x_plot, y=force,
                    mode='lines',
                    name='Force-Indentation',
                    line=dict(color='blue', width=1),
                    legendgroup='data',
                    showlegend=show_legend
                ), row=row, col=col)

                if fit_data is not None:
                    y_fit = fit_data.eval(indentation)
                    fig.add_trace(go.Scatter(
                        x=x_plot, y=y_fit,
                        mode='lines',
                        name='Hertz Fit',
                        line=dict(color='green', width=2),
                        legendgroup='fit',
                        showlegend=show_legend
                    ), row=row, col=col)

                    poc_offset = poc[0] if poc else 0.0
                    annotation_text = (
                        f"E={hertz_E:.2f} Pa<br>"
                        f"d0={hertz_d0 + poc_offset:.3E} m<br>"
                        f"RedChi={hertz_redchi:.3E}"
                    )
                    # Plotly axis refs: first subplot is 'x'/'y', subsequent are 'x2','x3',...
                    ax_suffix = '' if plot_idx == 0 else str(plot_idx + 1)
                    fig.add_annotation(
                        text=annotation_text,
                        xref=f"x{ax_suffix} domain",
                        yref=f"y{ax_suffix} domain",
                        x=0.02, y=0.98,
                        xanchor='left', yanchor='top',
                        showarrow=False,
                        font=dict(size=8, color='black'),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='gray',
                        borderwidth=1,
                        borderpad=2,
                        row=row, col=col
                    )

                fig.update_xaxes(title_text="Indentation (m)", row=row, col=col)
                fig.update_yaxes(title_text="Force (N)", row=row, col=col)

            progress.setLabelText("Generating HTML...")
            progress.setValue(n_files)
            QtWidgets.QApplication.processEvents()

            fig.update_layout(
                showlegend=True,
                height=max(400, 400 * n_rows),
                width=1200,
                font=dict(size=10),
                margin=dict(t=40)
            )

            # --- Collect parameters ---
            analysis_params = self.params.child('Analysis Params')
            hertz_params = self.params.child('Hertz Fit Params')
            gen_opts = self.params.child('General Options')

            p_height_ch   = analysis_params.child('Height Channel').value()
            p_defl_sens   = analysis_params.child('Deflection Sensitivity').value()
            p_spring_k    = analysis_params.child('Spring Constant').value()
            p_curve_seg   = analysis_params.child('Curve Segment').value()
            p_correct_t   = analysis_params.child('Correct Tilt').value()
            p_offset_type = analysis_params.child('Offset Type').value()
            if p_offset_type == 'percentage':
                p_offset_min = f"{analysis_params.child('Perc. Min Offset').value():.1f} %"
                p_offset_max = f"{analysis_params.child('Perc. Max Offset').value():.1f} %"
            else:
                p_offset_min = f"{analysis_params.child('Abs. Min Offset').value():.1f} nm"
                p_offset_max = f"{analysis_params.child('Abs. Max Offset').value():.1f} nm"

            p_poc_method  = hertz_params.child('PoC Method').value()
            p_poc_win     = hertz_params.child('PoC Window').value()
            p_poc_sigma   = hertz_params.child('Sigma').value()
            p_fit_range   = hertz_params.child('Fit Range Type').value()
            p_min_ind     = hertz_params.child('Min Indentation').value()
            p_max_ind     = hertz_params.child('Max Indentation').value()
            p_min_f       = hertz_params.child('Min Force').value()
            p_max_f       = hertz_params.child('Max Force').value()
            p_downsample  = hertz_params.child('Downsample Signal').value()
            p_correct_app = gen_opts.child('Correct App').value()

            # Representative metadata from first selected file
            first_file_obj = self.session.loaded_files[selected_ids[0]]
            fmeta = first_file_obj.filemetadata
            m_file_type  = fmeta.get('file_type', 'N/A')
            m_spring_k   = fmeta.get('spring_const_Nbym', 'N/A')
            m_defl_sens  = fmeta.get('defl_sens_nmbyV', 'N/A')
            m_height_key = fmeta.get('height_channel_key', 'N/A')

            # --- Collect per-file results for summary table ---
            results_rows = []
            for fid in selected_ids:
                fhr = self.session.hertz_fit_results.get(fid, None)
                if fhr is not None:
                    for cidx, cresult in fhr:
                        if cresult is not None:
                            results_rows.append((
                                fid,
                                f"{cresult.E0:.2f}",
                                f"{cresult.delta0:.3E}",
                                f"{cresult.redchi:.3E}"
                            ))
                            break
                    else:
                        results_rows.append((fid, '—', '—', '—'))
                else:
                    results_rows.append((fid, '—', '—', '—'))

            # --- Build HTML summary block ---
            gen_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            css = """
<style>
  body { font-family: Arial, sans-serif; margin: 16px; color: #222; }
  h1   { font-size: 1.4em; margin-bottom: 4px; }
  h2   { font-size: 1.1em; margin: 12px 0 4px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
  .meta-grid { display: grid; grid-template-columns: repeat(4, auto); gap: 4px 24px;
               background: #f5f5f5; padding: 10px 14px; border-radius: 6px;
               border: 1px solid #ddd; width: fit-content; }
  .meta-grid .key   { font-weight: bold; white-space: nowrap; }
  .meta-grid .val   { white-space: nowrap; }
  table  { border-collapse: collapse; font-size: 0.88em; margin-top: 6px; }
  th, td { border: 1px solid #ccc; padding: 4px 10px; text-align: left; }
  th     { background: #e8e8e8; }
  tr:nth-child(even) { background: #fafafa; }
  .section { margin-bottom: 18px; }
</style>"""

            def kv(k, v):
                return f'<div class="key">{k}</div><div class="val">{v}</div>'

            params_block = f"""
<div class="section">
  <h2>Analysis Parameters</h2>
  <div class="meta-grid">
    {kv('Height Channel', p_height_ch)}
    {kv('Deflection Sensitivity', f'{p_defl_sens:.2f} nm/V')}
    {kv('Spring Constant', f'{p_spring_k:.4f} N/m')}
    {kv('Curve Segment', p_curve_seg)}
    {kv('Correct Tilt', str(p_correct_t))}
    {kv('Correct App (overshoot)', str(p_correct_app))}
    {kv('Offset Type', p_offset_type)}
    {kv('Offset Min', p_offset_min)}
    {kv('Offset Max', p_offset_max)}
    {kv('PoC Method', p_poc_method)}
    {kv('PoC Window', f'{p_poc_win:.1f} nm')}
    {kv('PoC Sigma', str(p_poc_sigma))}
    {kv('Fit Range Type', p_fit_range)}
    {kv('Min Indentation', f'{p_min_ind:.2f} nm')}
    {kv('Max Indentation', f'{p_max_ind:.2f} nm')}
    {kv('Min Force', f'{p_min_f:.4f} nN')}
    {kv('Max Force', f'{p_max_f:.4f} nN')}
    {kv('Downsample Signal', str(p_downsample))}
  </div>
</div>"""

            metadata_block = f"""
<div class="section">
  <h2>File Metadata (representative — first file)</h2>
  <div class="meta-grid">
    {kv('File Type', m_file_type)}
    {kv('Spring Constant (file)', f'{m_spring_k} N/m')}
    {kv('Deflection Sensitivity (file)', f'{m_defl_sens} nm/V')}
    {kv('Height Channel Key', m_height_key)}
  </div>
</div>"""

            results_table_rows = ''.join(
                f'<tr><td>{fid}</td><td>{e}</td><td>{d0}</td><td>{rc}</td></tr>'
                for fid, e, d0, rc in results_rows
            )
            results_block = f"""
<div class="section">
  <h2>Fit Results Summary ({len(results_rows)} files)</h2>
  <table>
    <tr><th>File</th><th>E (Pa)</th><th>d0 (m)</th><th>Reduced χ²</th></tr>
    {results_table_rows}
  </table>
</div>"""

            header_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Hertz Fit Export</title>
  {css}
</head>
<body>
  <h1>Hertz Fit Export — Files {idx_from + 1} to {idx_to + 1}</h1>
  <p style="color:#666; margin-top:0;">Generated: {gen_time} &nbsp;|&nbsp; {n_files} file(s)</p>
  {params_block}
  {metadata_block}
  {results_block}
  <h2>Interactive Plots</h2>
"""

            plot_div = fig.to_html(
                full_html=False,
                config={'responsive': True, 'displayModeBar': True, 'displaylogo': False},
                include_plotlyjs='cdn'
            )

            footer_html = "\n</body>\n</html>"

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(header_html + plot_div + footer_html)

            progress.close()

        except Exception as e:
            import traceback
            traceback.print_exc()

    def updateParams(self):
        # Updates params related to the current file
        analysis_params = self.params.child('Analysis Params')
        analysis_params.child('Height Channel').setValue(self.current_file.filemetadata['height_channel_key'])
        if self.session.global_k is None:
            analysis_params.child('Spring Constant').setValue(self.current_file.filemetadata['spring_const_Nbym'])
        else:
            analysis_params.child('Spring Constant').setValue(self.session.global_k)
        if self.session.global_involts is None:
            analysis_params.child('Deflection Sensitivity').setValue(self.current_file.filemetadata['defl_sens_nmbyV'])
        else:
            analysis_params.child('Deflection Sensitivity').setValue(self.session.global_involts)
        
        analysis_params.child('Correct Tilt').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Offset Type').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Perc. Min Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Perc. Max Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Abs. Min Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Abs. Max Offset').sigValueChanged.connect(self.updatePlots)
        
        hertz_params = self.params.child('Hertz Fit Params')
        hertz_params.child('Fit Range Type').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Max Indentation').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Min Indentation').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Max Force').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Min Force').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Downsample Signal').sigValueChanged.connect(self.updatePlots)
        hertz_params.child('PoC Method').sigValueChanged.connect(self.updatePlots)
        hertz_params.child('PoC Window').sigValueChanged.connect(self.updatePlots)
        hertz_params.child('Sigma').sigValueChanged.connect(self.updatePlots)