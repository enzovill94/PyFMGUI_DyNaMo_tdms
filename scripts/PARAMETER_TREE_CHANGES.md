# Parameter Tree Widget Migration

## Changes Made

### 1. Created New Parameter Tree Widget (`parameter_tree_widget.py`)
- Replaced the old `ParameterWidget` class with a new `ParameterTreeWidget` class
- Uses PyQt Graph's `ParameterTree` for a more dynamic and organized interface
- Parameters are now organized into logical groups:
  - **Filtering Parameters**: Savitzky-Golay window length and polynomial order
  - **Plateau Detection**: Threshold, minimum width, maximum plateaus, and averaging percentage
  - **Baseline Correction**: Tilt offset parameters
  - **Denoise Filter**: Butterworth filter and Fourier band suppression parameters

### 2. Removed Parameters
The following parameters were removed from the analysis:
- `z_sensor_delay` - Z sensor delay timing parameter
- `bool_correct_overshoot` - Overshoot correction boolean flag

### 3. Added Denoising Parameters
New denoising functionality with the following parameters:
- `enable_denoising` - Boolean to enable/disable denoising (default: False)
- `denoise_w0` - Lower frequency bound for Butterworth filter in µm⁻¹ (default: 0.1)
- `denoise_w1` - Upper frequency bound for Butterworth filter in µm⁻¹ (default: 1.0)
- `butterworth_order` - Order of the Butterworth filter (default: 5)
- `denoise_ranges` - String representation of list of tuples for band suppression (default: '[(1, 6)]')
- `denoise_remove_percent` - Percentage of signal start to remove before filtering (default: 10%)
- `denoise_interp` - Use interpolation in band suppression (default: True)

### 4. Updated Main GUI (`tether_analysis_gui_v3_filter.py`)
- Replaced `ParameterWidget` instantiation with `ParameterTreeWidget`
- Simplified parameter loading/saving logic to use the new tree widget methods
- Updated default parameters dictionary to include denoising parameters
- Cleaned up unused imports (`QDoubleSpinBox`, `QSpinBox`)

### 5. Enhanced Tether Script (`tether_script.py`)
- Added denoising implementation in the `process_single_file` function
- Integrated Butterworth band-stop filtering and Fourier band suppression
- Added proper error handling for denoising failures
- Supports parsing of band ranges from string format to list of tuples

### 6. Benefits of Parameter Tree
- **Better Organization**: Parameters are grouped logically for easier navigation
- **Dynamic Interface**: Easy to add new parameter groups and types
- **PyFM Lab Consistency**: Uses the same parameter tree style as PyFM Lab
- **Cleaner Code**: Simplified parameter management with fewer manual UI controls
- **Advanced Filtering**: Sophisticated noise reduction capabilities

### 7. Parameter Groups Structure
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

Denoise Filter
├── Enable Denoising (bool, default: False)
├── W0 (µm⁻¹) (0.001-10.0, default: 0.1)
├── W1 (µm⁻¹) (0.001-10.0, default: 1.0)
├── Butterworth Order (1-10, default: 5)
├── Band Ranges (µm⁻¹) (string, default: '[(1, 6)]')
├── Remove Start (%) (0-50, default: 10)
└── Use Interpolation (bool, default: True)
```

### 8. Usage
The parameter tree widget maintains the same external interface:
- `getCurrentParameters()` - Get current parameter values
- `setParameters(params)` - Set parameter values from dictionary
- `update_parameter_status()` - Update status display
- `resetToDefaults()` - Reset to default values
- `parametersChanged` signal - Emitted when parameters change

### 9. Unit Conversions
The widget automatically handles unit conversions:
- Plateau threshold: displayed in nN, stored in N
- Minimum plateau width: displayed in μm, stored in m

### 10. Denoising Implementation
The denoising process includes:
1. **Signal preparation**: Detrending and trimming based on remove percentage
2. **Butterworth filtering**: Band-stop filter applied in frequency domain
3. **Band suppression**: Multiple frequency bands can be suppressed using Fourier transforms
4. **Interpolation**: Optional interpolation of suppressed frequency regions
5. **Error handling**: Graceful fallback to original signal if denoising fails

The denoising is based on Evan's implementation from the notebook and supports:
- Configurable frequency ranges for noise suppression
- Butterworth band-stop filtering
- Multiple band suppression ranges
- Interpolation or zeroing of suppressed frequencies
