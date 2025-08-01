# Parameter Tree Widget Migration

## Changes Made

### 1. Created New Parameter Tree Widget (`parameter_tree_widget.py`)
- Replaced the old `ParameterWidget` class with a new `ParameterTreeWidget` class
- Uses PyQt Graph's `ParameterTree` for a more dynamic and organized interface
- Parameters are now organized into logical groups:
  - **Filtering Parameters**: Savitzky-Golay window length and polynomial order
  - **Plateau Detection**: Threshold, minimum width, maximum plateaus, and averaging percentage
  - **Baseline Correction**: Tilt offset parameters

### 2. Removed Parameters
The following parameters were removed from the analysis:
- `z_sensor_delay` - Z sensor delay timing parameter
- `bool_correct_overshoot` - Overshoot correction boolean flag

### 3. Updated Main GUI (`tether_analysis_gui_v3_filter.py`)
- Replaced `ParameterWidget` instantiation with `ParameterTreeWidget`
- Simplified parameter loading/saving logic to use the new tree widget methods
- Updated default parameters dictionary to exclude removed parameters
- Cleaned up unused imports (`QDoubleSpinBox`, `QSpinBox`)

### 4. Benefits of Parameter Tree
- **Better Organization**: Parameters are grouped logically for easier navigation
- **Dynamic Interface**: Easy to add new parameter groups and types
- **PyFM Lab Consistency**: Uses the same parameter tree style as PyFM Lab
- **Cleaner Code**: Simplified parameter management with fewer manual UI controls

### 5. Parameter Groups Structure
```
Filtering Parameters
├── Savitzky Window Length (2-40, default: 10)
└── Savitzky Poly Order (1-12, default: 1)

Plateau Detection  
├── Plateau Threshold (nN) (0.001-1e6, default: 1.0)
├── Min Plateau Width (μm) (0.0001-60, default: 1.0) 
├── Max Plateaus (1-15, default: 7)
└── Last Plateau Avg (%) (1-100, default: 15)

Baseline Correction
├── Max Tilt Offset (%) (50-100, default: 100)
└── Min Tilt Offset (%) (30-90, default: 70)
```

### 6. Usage
The parameter tree widget maintains the same external interface:
- `getCurrentParameters()` - Get current parameter values
- `setParameters(params)` - Set parameter values from dictionary
- `update_parameter_status()` - Update status display
- `resetToDefaults()` - Reset to default values
- `parametersChanged` signal - Emitted when parameters change

### 7. Unit Conversions
The widget automatically handles unit conversions:
- Plateau threshold: displayed in nN, stored in N
- Minimum plateau width: displayed in μm, stored in m
