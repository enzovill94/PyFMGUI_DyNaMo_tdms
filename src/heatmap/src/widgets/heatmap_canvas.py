#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap Canvas Widget - Matplotlib canvas for displaying heatmaps
"""

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
import seaborn as sns


class HeatmapCanvas(QWidget):
    """Interactive matplotlib canvas for heatmap display"""
    
    # Signals
    roi_selected = pyqtSignal(list)  # Emits list of (x, y) pixel coordinates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Size policy
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Current data
        self.current_map_data = None
        self.current_x_axis = None
        self.current_y_axis = None
        self.current_params = None
        self.current_cmap = 'YlOrBr'
        
        # ROI selector
        self.roi_selector = None
        self.roi_enabled = True
        
    def plot_heatmap(self, map_data, x_axis=None, y_axis=None, params=None):
        """
        Plot heatmap data
        
        Parameters:
        -----------
        map_data : np.ndarray
            2D array with map data
        x_axis : np.ndarray, optional
            X-axis values
        y_axis : np.ndarray, optional
            Y-axis values
        params : dict, optional
            Parameters including colormap, z-range, etc.
        """
        # Clear figure completely to remove old colorbars
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        
        # Store data
        self.current_map_data = map_data
        self.current_x_axis = x_axis
        self.current_y_axis = y_axis
        self.current_params = params if params is not None else {}
        
        # Get parameters
        cmap = self.current_params.get('colormap', self.current_cmap)
        zmin = self.current_params.get('zmin')
        zmax = self.current_params.get('zmax')
        show_annot = self.current_params.get('show_annotations', False)
        annot_fmt = self.current_params.get('annotation_format', '.2f')
        
        # Prepare labels
        if x_axis is not None and len(x_axis) > 50:
            xticklabels = list(range(0, len(x_axis), 5))
        else:
            xticklabels = True if x_axis is not None else False
            
        if y_axis is not None and len(y_axis) > 50:
            yticklabels = list(range(0, len(y_axis), 5))
        else:
            yticklabels = True if y_axis is not None else False
        
        # Create heatmap
        sns.heatmap(
            map_data,
            ax=self.ax,
            cmap=cmap,
            vmin=zmin,
            vmax=zmax,
            annot=show_annot if map_data.size < 1000 else False,
            fmt=annot_fmt,
            xticklabels=xticklabels,
            yticklabels=yticklabels,
            cbar_kws={'label': 'Z (µm)'}
        )
        
        # Invert y-axis for proper orientation
        self.ax.invert_yaxis()
        
        # Set aspect ratio
        if params:
            x_sens = params.get('x_sens_um', 1.0)
            y_sens = params.get('y_sens_um', 1.0)
            flip_axis = params.get('flip_axis', True)
            xy_axis = -1 if flip_axis else 1
            self.ax.set_aspect((x_sens / y_sens) ** xy_axis)
        
        # Labels
        self.ax.set_xlabel('X (µm)', fontsize=12)
        self.ax.set_ylabel('Y (µm)', fontsize=12)
        self.ax.set_title('PSNEX Map', fontsize=14)
        
        # Setup ROI selector
        if self.roi_enabled:
            self.setup_roi_selector()
        
        self.canvas.draw()
    
    def set_colormap(self, cmap_name):
        """Update colormap and redraw"""
        self.current_cmap = cmap_name
        if self.current_params is not None:
            self.current_params['colormap'] = cmap_name
        
        if self.current_map_data is not None:
            self.plot_heatmap(
                self.current_map_data,
                self.current_x_axis,
                self.current_y_axis,
                self.current_params
            )
    
    def set_z_range(self, zmin=None, zmax=None):
        """Update z-range and redraw"""
        if self.current_params is not None:
            self.current_params['zmin'] = zmin
            self.current_params['zmax'] = zmax
        
        if self.current_map_data is not None:
            self.plot_heatmap(
                self.current_map_data,
                self.current_x_axis,
                self.current_y_axis,
                self.current_params
            )
    
    def setup_roi_selector(self):
        """Setup interactive ROI selection"""
        def on_select(eclick, erelease):
            """Callback for ROI selection"""
            if eclick.inaxes != self.ax or erelease.inaxes != self.ax:
                return
            
            # Get pixel coordinates
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            
            # Ensure valid range
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            
            # Limit to map boundaries
            if self.current_map_data is not None:
                height, width = self.current_map_data.shape
                x1 = max(0, min(x1, width - 1))
                x2 = max(0, min(x2, width - 1))
                y1 = max(0, min(y1, height - 1))
                y2 = max(0, min(y2, height - 1))
            
            # Generate list of pixels in rectangle
            pixels = []
            for x in range(x1, x2 + 1):
                for y in range(y1, y2 + 1):
                    pixels.append((x, y))
            
            if pixels:
                self.roi_selected.emit(pixels)
        
        # Create rectangle selector
        self.roi_selector = RectangleSelector(
            self.ax,
            on_select,
            useblit=True,
            button=[1],  # Left mouse button
            minspanx=1,
            minspany=1,
            spancoords='pixels',
            interactive=True
        )
    
    def enable_roi_selection(self, enabled=True):
        """Enable or disable ROI selection"""
        self.roi_enabled = enabled
        if self.roi_selector:
            self.roi_selector.set_active(enabled)
    
    def clear_plot(self):
        """Clear the plot and reset state"""
        # Clear ROI selector first
        if self.roi_selector:
            self.roi_selector.set_active(False)
            self.roi_selector = None
        
        # Clear entire figure (removes axes AND colorbars)
        self.figure.clear()
        # Recreate the main axes
        self.ax = self.figure.add_subplot(111)
        
        # Redraw
        self.canvas.draw()
        
        # Clear stored data
        self.current_map_data = None
        self.current_x_axis = None
        self.current_y_axis = None
        self.current_params = None
