# PSNEX Map Analysis GUI - Implementation Guide

This document provides implementation templates and guidance for completing the GUI components and widgets.

## Completed Files

### Core Modules (✓ Complete)
- `src/core/__init__.py`
- `src/core/map_processor.py`
- `src/core/data_loader.py`
- `src/core/session_manager.py`
- `src/core/export_manager.py`
- `src/core/integrity_checker.py`

### Configuration (✓ Complete)
- `src/config/__init__.py`
- `src/config/default_params.py`
- `src/config/colormap_config.py`

## Files to Implement

### 1. GUI Components

#### 1.1 Main Window (`src/gui/main_window.py`)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for PSNEX Map Analysis GUI
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QAction, QMenuBar, QStatusBar, QFileDialog,
                             QMessageBox, QProgressDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence

from .map_viewer_widget import MapViewerWidget
from .parameter_panel import ParameterPanel  
from .file_browser_widget import FileBrowserWidget
from .statistics_panel import StatisticsPanel
from .roi_selector_widget import ROISelectorWidget
from .batch_processor_dialog import BatchProcessorDialog

from ..core import MapProcessor, DataLoader, SessionManager, ExportManager
from ..config import DEFAULT_PARAMS

class MapAnalysisMainWindow(QMainWindow):
    # Signals
    map_loaded = pyqtSignal(dict)
    parameters_changed = pyqtSignal(dict)
    roi_selected = pyqtSignal(list)
    
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
        
        self.setupUI()
        self.setupMenuBar()
        self.setupConnections()
        
    def setupUI(self):
        """Setup main user interface"""
        self.setWindowTitle("PSNEX Map Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Main splitter (3 panels)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: File browser and parameters
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.file_browser = FileBrowserWidget()
        self.parameter_panel = ParameterPanel(self.current_parameters)
        left_layout.addWidget(self.file_browser, stretch=2)
        left_layout.addWidget(self.parameter_panel, stretch=3)
        
        # Center panel: Map viewer
        self.map_viewer = MapViewerWidget()
        
        # Right panel: ROI tools and statistics
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.roi_selector = ROISelectorWidget()
        self.statistics_panel = StatisticsPanel()
        right_layout.addWidget(self.roi_selector, stretch=1)
        right_layout.addWidget(self.statistics_panel, stretch=2)
        
        # Add panels to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(self.map_viewer)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(main_splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def setupMenuBar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open Map Folder...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_map_folder)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_session_action = QAction('Save Session...', self)
        save_session_action.setShortcut(QKeySequence.Save)
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)
        
        load_session_action = QAction('Load Session...', self)
        load_session_action.triggered.connect(self.load_session)
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
        analyze_action.triggered.connect(self.analyze_map)
        process_menu.addAction(analyze_action)
        
        batch_action = QAction('Batch Process...', self)
        batch_action.triggered.connect(self.open_batch_processor)
        process_menu.addAction(batch_action)
        
        # Export menu
        export_menu = menubar.addMenu('Export')
        
        export_tiff_action = QAction('Export as TIFF...', self)
        export_tiff_action.triggered.connect(self.export_tiff)
        export_menu.addAction(export_tiff_action)
        
        export_csv_action = QAction('Export as CSV...', self)
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)
        
        export_roi_action = QAction('Export ROI Data...', self)
        export_roi_action.triggered.connect(self.export_roi)
        export_menu.addAction(export_roi_action)
        
    def setupConnections(self):
        """Setup signal-slot connections"""
        # File browser
        self.file_browser.folder_selected.connect(self.on_folder_selected)
        
        # Parameter changes
        self.parameter_panel.parameters_changed.connect(self.on_parameters_changed)
        
        # ROI selection
        self.roi_selector.roi_drawn.connect(self.on_roi_drawn)
        self.map_viewer.roi_selected.connect(self.on_roi_pixels_selected)
        
    # Slot implementations would go here
    def open_map_folder(self):
        """Open map folder dialog"""
        pass
        
    def on_folder_selected(self, folder_path):
        """Handle folder selection"""
        pass
        
    def analyze_map(self):
        """Analyze current map with current parameters"""
        pass
        
    def on_parameters_changed(self, params):
        """Handle parameter changes"""
        pass
        
    # ... more slot implementations
```

Key methods to implement:
- `open_map_folder()`: File dialog to select PSNEX folder
- `on_folder_selected()`: Load and validate selected folder
- `analyze_map()`: Process map with current parameters
- `save_session()`: Save current session
- `load_session()`: Load previous session
- `export_tiff()`, `export_csv()`, `export_roi()`: Export functions
- `on_roi_drawn()`: Handle ROI drawing
- `on_roi_pixels_selected()`: Extract and display ROI data

#### 1.2 Map Viewer Widget (`src/gui/map_viewer_widget.py`)

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PyQt5.QtCore import pyqtSignal
from ..widgets import HeatmapCanvas, ColormapSelector

class MapViewerWidget(QWidget):
    roi_selected = pyqtSignal(list)  # List of (x, y) pixel coordinates
    
    def __init__(self):
        super().__init__()
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # Control bar
        control_layout = QHBoxLayout()
        self.colormap_selector = ColormapSelector()
        control_layout.addWidget(QLabel("Colormap:"))
        control_layout.addWidget(self.colormap_selector)
        control_layout.addStretch()
        
        # Heatmap canvas
        self.canvas = HeatmapCanvas()
        
        layout.addLayout(control_layout)
        layout.addWidget(self.canvas)
        
        # Connections
        self.colormap_selector.colormap_changed.connect(self.update_colormap)
        self.canvas.roi_selected.connect(self.roi_selected.emit)
        
    def display_map(self, map_data, x_axis, y_axis, params):
        """Display heatmap"""
        self.canvas.plot_heatmap(map_data, x_axis, y_axis, params)
        
    def update_colormap(self, cmap_name):
        """Update heatmap colormap"""
        self.canvas.set_colormap(cmap_name)
```

#### 1.3 Parameter Panel (`src/gui/parameter_panel.py`)

This should be similar to the existing ParameterTreeWidget but adapted for map analysis:

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from ..config import PARAMETER_DEFINITIONS

class ParameterPanel(QWidget):
    parameters_changed = pyqtSignal(dict)
    
    def __init__(self, initial_params):
        super().__init__()
        self.params = initial_params.copy()
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Parameter', 'Value'])
        
        # Build tree from PARAMETER_DEFINITIONS
        self.build_tree()
        
        layout.addWidget(self.tree)
        
        # Connect item changed signal
        self.tree.itemChanged.connect(self.on_item_changed)
        
    def build_tree(self):
        """Build parameter tree from definitions"""
        # Implementation similar to ParameterTreeWidget
        pass
        
    def on_item_changed(self, item, column):
        """Handle parameter value change"""
        # Extract changed parameter and emit signal
        pass
```

### 2. Specialized Widgets

#### 2.1 Heatmap Canvas (`src/widgets/heatmap_canvas.py`)

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import seaborn as sns
from PyQt5.QtCore import pyqtSignal

class HeatmapCanvas(QWidget):
    roi_selected = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        
        self.current_cmap = 'YlOrBr'
        self.roi_selector = None
        
        # Enable ROI selection
        self.setup_roi_selector()
        
    def plot_heatmap(self, map_data, x_axis, y_axis, params):
        """Plot heatmap using seaborn"""
        self.ax.clear()
        
        sns.heatmap(map_data, 
                   xticklabels=x_axis.round(2),
                   yticklabels=y_axis.round(2),
                   ax=self.ax,
                   cmap=self.current_cmap,
                   vmin=params.get('zmin'),
                   vmax=params.get('zmax'))
        
        self.ax.invert_yaxis()
        self.canvas.draw()
        
    def setup_roi_selector(self):
        """Setup interactive ROI selection"""
        # Use matplotlib's RectangleSelector or similar
        from matplotlib.widgets import RectangleSelector
        
        def on_select(eclick, erelease):
            # Extract pixel coordinates
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            
            # Generate list of pixels in rectangle
            pixels = []
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    pixels.append((x, y))
            
            self.roi_selected.emit(pixels)
        
        self.roi_selector = RectangleSelector(
            self.ax, on_select,
            useblit=True,
            button=[1],  # Left mouse button
            minspanx=5, minspany=5,
            spancoords='pixels',
            interactive=True
        )
```

#### 2.2 Other Widget Templates

Create similar implementations for:

- **ColormapSelector** (`src/widgets/colormap_selector.py`): QComboBox with colormap preview
- **DragDropTable** (`src/widgets/drag_drop_table.py`): QTableWidget accepting file drops
- **ProgressDialog** (`src/widgets/progress_dialog.py`): QProgressDialog for batch operations

### 3. Utility Modules

#### 3.1 File Utils (`src/utils/file_utils.py`)

```python
import os
from datetime import datetime

def validate_path(path):
    """Validate file/folder path"""
    return os.path.exists(path)

def create_output_filename(base_path, suffix, extension):
    """Create timestamped output filename"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{base_path}_{suffix}_{timestamp}.{extension}"

def ensure_directory(path):
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)
    return path

def get_file_timestamp(filepath):
    """Get file modification timestamp"""
    if os.path.exists(filepath):
        return datetime.fromtimestamp(os.path.getmtime(filepath))
    return None
```

### 4. Application Entry Points

#### 4.1 Main Entry (`src/main.py`)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for PSNEX Map Analysis GUI
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MapAnalysisMainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PSNEX Map Analysis")
    
    window = MapAnalysisMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
```

#### 4.2 App Class (`src/app.py`)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application class for PSNEX Map Analysis
"""

from PyQt5.QtWidgets import QApplication
import sys
from gui.main_window import MapAnalysisMainWindow

class MapAnalysisApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("PSNEX Map Analysis")
        self.window = MapAnalysisMainWindow()
        
    def run(self):
        """Run the application"""
        self.window.show()
        return self.app.exec_()

def main():
    app = MapAnalysisApp()
    sys.exit(app.run())

if __name__ == '__main__':
    main()
```

## Implementation Priority

1. **Phase 1 - Core GUI** (Start here)
   - Implement `main_window.py` basic structure
   - Implement `heatmap_canvas.py` for visualization
   - Implement `parameter_panel.py` for controls
   - Test basic map loading and display

2. **Phase 2 - ROI Functionality**
   - Implement `roi_selector_widget.py`
   - Implement `statistics_panel.py`
   - Add ROI selection to heatmap canvas
   - Test ROI extraction and statistics

3. **Phase 3 - File Management**
   - Implement `file_browser_widget.py`
   - Implement `drag_drop_table.py`
   - Add session save/load
   - Test workflow

4. **Phase 4 - Batch Processing**
   - Implement `batch_processor_dialog.py`
   - Add progress tracking
   - Test batch export

5. **Phase 5 - Polish**
   - Add error handling
   - Improve UI/UX
   - Add tooltips and help
   - Write tests

## Testing Strategy

Create tests in `test/` directory:

```python
# test/test_map_processor.py
import pytest
from src.core.map_processor import MapProcessor

def test_process_map():
    processor = MapProcessor()
    result = processor.process_map('/path/to/test/map')
    assert result['success'] == True
    assert result['map_tdms'] is not None
```

## Next Steps

1. Start with implementing `src/main.py` and `src/app.py`
2. Implement basic `main_window.py` structure
3. Implement `heatmap_canvas.py` for visualization
4. Test basic functionality with a sample map
5. Gradually add ROI, export, and batch features

## Questions?

- For parameter tree widget, refer to `../../PyFMGUI_DyNaMo/scripts/parameter_tree_widget.py`
- For drag-drop table, see `../../PyFMGUI_DyNaMo/scripts/tether_analysis_gui_v3_filter.py` 
- For matplotlib integration, check PyQt5 matplotlib examples
