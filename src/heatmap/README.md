# PSNEX Map Analysis GUI

A PyQt5-based graphical user interface for analyzing PSNEX map data, including heatmap visualization, ROI selection, and batch processing capabilities.

## Features

- **Dynamic Data Loading**: Load both TDMS files and CSV maps
- **Interactive Heatmap Visualization**: Real-time parameter adjustment with customizable colormaps
- **ROI Analysis**: Select regions of interest, get statistical data, and export ROI-specific dataframes
- **Histogram Display**: Visual representation of ROI data distributions
- **Session Management**: Save and load analysis sessions based on CSV dataframes
- **Batch Processing**: Process multiple map folders efficiently
- **Data Integrity Checking**: Automatic validation of map data quality
- **Multiple Export Formats**: Export as TIFF, CSV, and save metadata

## Project Structure

```
heatmap/
├── src/
│   ├── gui/                      # GUI components
│   │   ├── __init__.py
│   │   ├── main_window.py         # Main application window
│   │   ├── map_viewer_widget.py   # Heatmap display widget
│   │   ├── parameter_panel.py     # Parameter tree widget
│   │   ├── file_browser_widget.py # File/folder browser
│   │   ├── statistics_panel.py    # ROI statistics display
│   │   ├── roi_selector_widget.py # ROI selection tools
│   │   └── batch_processor_dialog.py # Batch processing dialog
│   │
│   ├── core/                     # Core processing modules
│   │   ├── __init__.py
│   │   ├── map_processor.py      # Map processing and heatmap generation
│   │   ├── data_loader.py        # Data loading and validation
│   │   ├── session_manager.py    # Session save/load functionality
│   │   ├── export_manager.py     # Export to various formats
│   │   └── integrity_checker.py  # Data integrity validation
│   │
│   ├── widgets/                  # Specialized widgets
│   │   ├── __init__.py
│   │   ├── heatmap_canvas.py     # Matplotlib canvas for heatmaps
│   │   ├── colormap_selector.py  # Colormap selection widget
│   │   ├── drag_drop_table.py    # Drag-drop file table
│   │   └── progress_dialog.py    # Progress dialogs
│   │
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   ├── file_utils.py         # File operations
│   │   ├── plotting_utils.py     # Plotting helpers
│   │   └── data_utils.py         # Data manipulation helpers
│   │
│   ├── config/                   # Configuration
│   │   ├── __init__.py
│   │   ├── default_params.py     # Default parameters
│   │   └── colormap_config.py    # Colormap configurations
│   │
│   ├── main.py                   # Application entry point
│   └── app.py                    # Application class
│
├── examples/                     # Example scripts
│   ├── sample_map_analysis.py
│   └── batch_processing_example.py
│
├── test/                         # Unit tests
│   ├── __init__.py
│   ├── test_map_processor.py
│   ├── test_data_loader.py
│   └── test_integrity_checker.py
│
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
└── README.md                     # This file
```

## Installation

1. Clone the repository or navigate to the heatmap directory:
```bash
cd /Users/evillz/Github/PyFMGUI_DyNaMo_tdms/src/heatmap
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package (optional, for development):
```bash
pip install -e .
```

## Usage

### Running the GUI

```bash
python src/main.py
```

Or from Python:
```python
from src.app import MapAnalysisApp

app = MapAnalysisApp()
app.run()
```

### Basic Workflow

1. **Load Map Data**
   - Click "Browse" or drag-and-drop PSNEX map folders
   - Both TDMS and CSV maps are loaded automatically

2. **Adjust Parameters**
   - Use the Parameter Tree Widget to adjust:
     - Map dimensions and step sizes
     - Sensitivity values
     - Processing options
     - Visualization settings (colormap, z-range)
     - ROI selection mode

3. **Select ROI**
   - Choose ROI mode (rectangle, polygon, ellipse)
   - Click and drag on the heatmap to select regions
   - View statistics in the Statistics Panel
   - See histogram of ROI values

4. **Export Data**
   - Export heatmaps as TIFF files
   - Export full dataframes as CSV
   - Export ROI-specific data with statistics

5. **Save Session**
   - Save current analysis state
   - Load previous sessions to continue work

### Batch Processing

```python
from src.core import DataLoader, ExportManager
from src.gui import BatchProcessorDialog

# Find all PSNEX folders
loader = DataLoader()
folders = loader.find_psnex_folders('/path/to/data')

# Batch process
exporter = ExportManager()
results = exporter.batch_export_maps(
    folders, 
    output_dir='/path/to/output',
    export_formats=['tiff', 'csv']
)
```

## Configuration

### Default Parameters

Edit `src/config/default_params.py` to change default settings:

```python
DEFAULT_PARAMS = {
    'map_x_pix': 40,
    'map_y_pix': 40,
    'map_x_step': 0.14,
    'map_y_step': 0.14,
    'z_sens_um': 6.0,
    'x_sens_um': 5.685,
    'y_sens_um': 3.960,
    'colormap': 'YlOrBr',
    # ... more parameters
}
```

### Colormaps

Available colormap categories:
- **Sequential**: viridis, plasma, YlOrBr, etc.
- **Diverging**: coolwarm, RdYlBu, seismic, etc.
- **Topographic**: terrain, gist_earth, hot, etc.

Recommended for height maps: `YlOrBr`, `terrain`, `viridis`

## Key Classes

### Core Module

- **MapProcessor**: Processes map data and generates heatmaps
  - `process_map()`: Load and process PSNEX map folder
  - `extract_roi_data()`: Extract data from selected ROI pixels
  - `get_roi_statistics()`: Calculate statistics for ROI

- **DataLoader**: Loads and validates PSNEX data
  - `find_psnex_folders()`: Find all PSNEX map folders
  - `validate_folder()`: Check folder integrity
  - `load_tdms_map()`, `load_csv_map()`: Load data

- **SessionManager**: Manages analysis sessions
  - `save_session()`: Save current state
  - `load_session()`: Restore previous session

- **ExportManager**: Handles data exports
  - `export_tiff()`: Export as TIFF with metadata
  - `export_dataframe_csv()`: Export dataframes
  - `batch_export_maps()`: Batch processing

- **IntegrityChecker**: Validates data quality
  - `check_map_indices()`: Check for index errors
  - `check_nan_values()`: Find NaN values
  - `comprehensive_check()`: Full validation

### GUI Components

- **MapAnalysisMainWindow**: Main application window
- **MapViewerWidget**: Interactive heatmap display
- **ParameterPanel**: Real-time parameter adjustment
- **FileBrowserWidget**: File/folder browser with drag-drop
- **StatisticsPanel**: ROI statistics and histogram display
- **ROISelectorWidget**: ROI selection tools

## Dependencies

- Python >= 3.7
- PyQt5 >= 5.15
- numpy >= 1.20
- pandas >= 1.3
- matplotlib >= 3.4
- seaborn >= 0.11
- pyfmreader (custom module)

## Development

### Running Tests

```bash
pytest test/
```

### Adding New Parameters

1. Add to `DEFAULT_PARAMS` in `src/config/default_params.py`
2. Add to `PARAMETER_DEFINITIONS` for GUI display
3. Update processing functions to use the parameter

### Adding New Export Formats

1. Add export method to `ExportManager` class
2. Update GUI export options
3. Add to export history tracking

## Troubleshooting

**Issue**: Map data not loading
- Check that folder contains TDMS or CSV files
- Verify folder naming: `psnex_map_*`
- Check integrity with `IntegrityChecker`

**Issue**: Heatmap not displaying
- Verify colormap name is valid
- Check z-range settings (zmin, zmax)
- Ensure map data is not all NaN

**Issue**: ROI selection not working
- Check ROI mode setting
- Verify heatmap is displayed first
- Try different ROI modes

## Contributing

This is an internal research tool. For questions or improvements, contact the development team.

## License

Internal use only - DyNaMo-INSERM

## Authors

- Based on `map_ctc_article_final.ipynb` analysis workflow
- GUI structure inspired by `tether_analysis_gui_v3_filter.py`

## Version

0.1.0 - Initial structure (October 2025)
