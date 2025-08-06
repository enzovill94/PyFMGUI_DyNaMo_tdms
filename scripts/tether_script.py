#!/usr/bin/env python3
"""
Tether Analysis Script - Batch Processing
Based on tether_finder_pyfmlab.ipynb

This script processes multiple TDMS files and performs tether analysis
to detect plateau regions in force-displacement curves.

Features:
- Batch processing of TDMS files
- Tilt correction and contact point detection
- Savitzky-Golay smoothing and plateau finding
- CSV export of analysis results
- PNG plot generation for visual inspection
- Error handling with file moving

Requirements:
- plotly and kaleido packages for PNG export
- pip install plotly kaleido
"""

import numpy as np
import pandas as pd
import math
import os
import ast
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import detrend

# Import required modules
from pyfmreader import loadfile
from pyfmreader.ps_nex.parseTDMS import grab_tdms
from pyfmrheo.utils.force_curves import correct_tilt
from scipy.signal import savgol_filter
pi = math.pi
from scipy.stats import linregress

def find_first_positive(arr):
    """
    Returns the index of the first positive value in a NumPy array.
    Returns None if no positive value is found.
    """
    arr = np.asarray(arr)
    positives = np.where(arr > 0)[0]
    return positives[0] if positives.size > 0 else None

def savitzky_golay_smooth(y, window_length=11, polyorder=3):
    """
    Applies Savitzky-Golay smoothing to a 1D array.
    """
    y = np.asarray(y)
    # Ensure window_length is odd and less than or equal to the size of y
    if window_length % 2 == 0:
        window_length += 1
    if window_length > len(y):
        window_length = len(y) if len(y) % 2 == 1 else len(y) - 1
    return savgol_filter(y, window_length=window_length, polyorder=polyorder)

def update_tilt_range(zheight, max_perc, min_perc, offset_type='percentage'):
    """Update tilt correction range based on percentage or absolute values."""
    if offset_type == 'percentage':
        deltaz = zheight.max() - zheight.min()
        maxperc = max_perc / 1e2
        minperc = min_perc / 1e2
        maxoffset = zheight.min() + deltaz * maxperc
        minoffset = zheight.min() + deltaz * minperc
    elif offset_type == 'absolute':
        maxoffset = max_perc / 1e9
        minoffset = min_perc / 1e9
    return maxoffset, minoffset

def create_plateau_png(rel_time, defl_savitz, plateaus, df_plat, displacement=None,
                       output_path='plateau_analysis.png', 
                       showDisplacementonX=False, 
                       title='Detected Plateaus with Averages and Δ',
                       width=1200, height=800):
    """
    Create and save a PNG file of the plateau analysis graph.
    
    Parameters:
        rel_time (array): Time array
        defl_savitz (array): Savitzky-Golay smoothed deflection data
        plateaus (list): List of (start, end) tuples for plateau regions
        df_plat (DataFrame): DataFrame with plateau analysis results
        displacement (array): Displacement array (required if showDisplacementonX=True)
        output_path (str): Path where to save the PNG file
        showDisplacementonX (bool): If True, shows displacement on x-axis, else time
        title (str): Title for the plot
        width (int): Width of the image in pixels
        height (int): Height of the image in pixels
    
    Returns:
        str: Path to the saved PNG file or None if failed
    """
    try:
        import plotly.graph_objects as go
        import os
        
        # Prepare the figure
        fig = go.Figure()

        # Use displacement if requested
        if showDisplacementonX:
            x_data = displacement if displacement is not None else rel_time
        else:
            x_data = rel_time

        # 1. Add main signal trace (Savitzky-Golay smoothed)
        fig.add_trace(go.Scatter(
            x=x_data, y=defl_savitz,
            mode='lines',
            name='Savitzky-Golay Smoothed Deflection',
            line=dict(color='blue', width=2)
        ))

        # 2. Add plateau markers with detailed hover info
        for i, idx in enumerate(df_plat['plateau_avg_idx']):
            fig.add_trace(go.Scatter(
                x=[x_data[idx]],
                y=[defl_savitz[idx]],
                mode='markers',
                marker=dict(size=10, color=f'rgba({31+i*40},{119+i*30},{180+i*20},1.0)'),
                name=f'Plateau {i}',
                hovertemplate=(
                    f'Plat {i}<br>'
                    f'Yavg = {df_plat["plateau_avg"].iloc[i]:.2e}<br>'
                    f'ΔYavg = {df_plat["delta_avg"].iloc[i]:.2e}<br>'
                    f'Δt = {df_plat["delta_time"].iloc[i]:.2e} s<br>'
                    f'x̄(dy/dx) = {df_plat["mean dy/dx"].iloc[i]:.2e}<br>'
                    '<extra></extra>'
                )
            ))

        # 3. Overlay plateau rectangles + average and delta lines
        colors = ['rgba(31,119,180,0.3)', 'rgba(255,127,14,0.3)', 'rgba(44,160,44,0.3)', 
                  'rgba(214,39,40,0.3)', 'rgba(148,103,189,0.3)', 'rgba(140,86,75,0.3)', 
                  'rgba(227,119,194,0.3)', 'rgba(127,127,127,0.3)', 'rgba(188,189,34,0.3)', 
                  'rgba(23,190,207,0.3)']

        shapes = []
        for i, (start, end) in enumerate(plateaus):
            # Shaded rectangle
            shapes.append(
                dict(
                    type="rect",
                    xref="x", yref="paper",
                    x0=x_data[start], x1=x_data[end-1],
                    y0=0, y1=1,
                    fillcolor=colors[i % len(colors)],
                    line=dict(width=0),
                    layer="below"
                )
            )

            # Horizontal average line
            plateau_avg = np.mean(defl_savitz[start:end])
            fig.add_trace(go.Scatter(
                x=[x_data[start], x_data[end-1]],
                y=[plateau_avg, plateau_avg],
                mode='lines',
                line=dict(color=colors[i % len(colors)].replace('0.3', '1.0'), width=3, dash='dash'),
                name=f'Avg Pl {i}: {plateau_avg:.2g}',
                showlegend=False  # Don't clutter legend with these
            ))

            # Vertical delta line from previous plateau
            if i > 0:
                prev_start, prev_end = plateaus[i-1]
                prev_avg = np.mean(defl_savitz[prev_start:prev_end])
                delta_x = x_data[start]
                fig.add_trace(go.Scatter(
                    x=[delta_x, delta_x],
                    y=[prev_avg, plateau_avg],
                    mode='lines',
                    line=dict(color='black', width=2, dash='dot'),
                    name=f'Δ {i-1}-{i}: {plateau_avg - prev_avg:.2g}',
                    showlegend=False  # Don't clutter legend with these
                ))

        # Set axis titles
        if showDisplacementonX:
            xaxis_title = 'Displacement (m)'
        else:
            xaxis_title = 'Time (s)'

        # 4. Final layout with enhanced styling for PNG export
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                font=dict(size=20, color='black')
            ),
            xaxis=dict(
                title=dict(text=xaxis_title, font=dict(size=16)),
                tickfont=dict(size=14),
                gridcolor='lightgray',
                showgrid=True
            ),
            yaxis=dict(
                title=dict(text='Deflection (N)', font=dict(size=16)),
                tickfont=dict(size=14),
                gridcolor='lightgray',
                showgrid=True
            ),
            legend=dict(
                font=dict(size=12),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1
            ),
            shapes=shapes,
            showlegend=True,
            plot_bgcolor='white',
            paper_bgcolor='white',
            width=width,
            height=height
        )

        # Save as PNG
        fig.write_image(output_path, format='png', engine='kaleido')
        print(f"  ✅ PNG saved: {os.path.basename(output_path)}")
        return output_path
    except Exception as e:
        print(f"  ❌ Error saving PNG: {e}")
        print("  💡 Make sure you have kaleido installed: pip install kaleido")
        return None
    
def calculate_velocity(displacement_um, rel_time):
    """
    Calculate the average velocity from displacement_um and time arrays using linear regression.

    Parameters:
        displacement_um (np.ndarray): Displacement values (in micrometers).
        rel_time (np.ndarray): Time values (in seconds).

    Returns:
        float: Average velocity (slope) in µm/s.
    """
    displacement_um = -displacement_um * 1e6  # Convert to micrometers (for compatibility with previous code)
    # deriv_displacement = np.gradient(displacement_um, rel_time)
    slope, intercept, _, _, _= linregress(rel_time, displacement_um)
    return slope

def find_plateaus(x, y, params=None, dt=1e-3):
    """
    Identify plateaus in 1D data where the first derivative is close to 0.
    
    Parameters:
        x (array): x-axis data (displacement)
        y (array): 1D signal (e.g., deflection)
        params (dict): Analysis parameters
        dt (float): time step for calculations
    
    Returns:
        plateaus (list): List of (start_idx, end_idx) tuples
        df_plat (DataFrame): DataFrame with plateau analysis results
        df_data (DataFrame): DataFrame with data for plotting
        velocity (float): Average velocity during the whole retract
    """
    # Define default parameters
    default_params = {
        'sav_window_length': 10,
        'sav_polyorder': 1,
        
        'pl_threshold': 0.01,
        'pl_min_width': 2,
        'pl_min_width_um': 2,

        'last_num_plateaus': 7,
        'last_plateau_avg_percentage': 15,  # New parameter: percentage of last plateau to average
    }
    
    # Merge with input params
    if params is None:
        params = {}
    final_params = {**default_params, **params}
    
    # Calculate spacing for time array
    dt_arr = np.arange(len(y)) * dt

    # calculate dx of displacement
    dx =np.abs(x[0] - x[1])
    if dx == 0: 
        #shift to the left 
        dx = np.abs(x[-2] - x[-3])

    print(f'Pl_threshold: {final_params["pl_threshold"]:.2e} N')
    print(f'total distance: {dx * len(y):.2e} m, dx: {dx:.2e} m')
    
    # Calculate velocity from displacement vs time
    velocity_um_s = -(calculate_velocity(x, dt_arr))
    print (f'velocity: {velocity_um_s:.4e} m/s, dt: {dt:.4e} sec')
    
    # Find index of maximum deflection in the whole first half of the force curve
    idx_max = np.argmax(y[:len(y) // 2])
    print(f"Index of maximum deflection: {idx_max}, value: {y[idx_max]:.4e}")

    # Calculate derivative of deflection with respect to time
    dy = np.gradient(y, dt_arr * velocity_um_s)
    dy_smooth = np.abs(dy)
    dy_abs_sav = savitzky_golay_smooth(
        dy_smooth,
        window_length=final_params['sav_window_length'], 
        polyorder=final_params['sav_polyorder']
    )

    # Convert pl_min_width_um to number of points
    # sampling_rate = 1 / dt  # Hz
    velocity_m_s = velocity_um_s * 1e-06  # Convert µm/s to m/s
    distance_per_point = velocity_m_s * dt  # meters per data point
    pl_min_width_points = int(final_params['pl_min_width_um'] * 1e-6 / distance_per_point)
    # Print the actual physical distance covered by the minimum plateau width (in µm)
    actual_distance_um = pl_min_width_points * distance_per_point * 1e6 
    print(f'pl_min_width_points: {pl_min_width_points} points, distance = {actual_distance_um:.2f} µm')
    # final_params['pl_min_width'] = pl_min_width_points


    # Find flat plateaus
    is_flat = dy_abs_sav < final_params['pl_threshold']
    plateaus = []
    start = None
    
    for i, flat in enumerate(is_flat):
        if flat and start is None:
            start = i
        elif not flat and start is not None:
            if i - start >= pl_min_width_points:
                plateaus.append((start, i))
            start = None
    
    if start is not None and len(y) - start >= pl_min_width_points:
        plateaus.append((start, len(y)))
    
    print(f'Raw plateaus found: {len(plateaus)}')
    
    # Keep only the last N plateaus
    if final_params['last_num_plateaus'] == -1:
        # plot all plateaus
        plateaus = plateaus[:]
    else:
        # plot only the last N plateaus
        plateaus = plateaus[-final_params['last_num_plateaus']:]
    
    print(f'Plateaus after filtering (last {final_params["last_num_plateaus"]}): {len(plateaus)}')
    
    # Calculate plateau statistics
    plateau_avg_idx_arr = []
    plateau_delta_avg_arr = []
    
    for i, (start, end) in enumerate(plateaus):
        # Special handling for the last plateau average calculation
        if i == len(plateaus) - 1:
            # For the last plateau, use only a percentage of the plateau for averaging
            percentage = final_params['last_plateau_avg_percentage'] / 100.0
            plateau_length = end - start
            avg_length = max(1, int(plateau_length * percentage))  # Ensure at least 1 point
            
            # Take the first X% of the last plateau
            avg_end = start + avg_length
            plateau_avg = np.mean(y[start:avg_end])
            plateau_avg_idx = start + np.argmin(np.abs(y[start:avg_end] - plateau_avg))
            
            # Use start - 1 for the index array (maintaining existing behavior)
            plateau_avg_idx_arr.append(start - 1)
        else:
            # For all other plateaus, use the full plateau for averaging
            plateau_avg = np.mean(y[start:end])
            plateau_avg_idx = start + np.argmin(np.abs(y[start:end] - plateau_avg))
            plateau_avg_idx_arr.append(plateau_avg_idx)
        
        # Calculate delta differences from the perspective of going backwards
        if i < len(plateaus) - 1:
            current_avg = np.mean(y[start:end])
            next_avg = np.mean(y[plateaus[i+1][0]:plateaus[i+1][1]])
            delta = next_avg - current_avg  # Difference to next plateau
            plateau_delta_avg_arr.append(delta)
        else:
            # For the last plateau, there's no next plateau to compare
            plateau_delta_avg_arr.append(0.0)  # or np.nan if you prefer
            
    # Calculate plateau derivatives
    plateau_derivatives = []
    for start, end in plateaus:
        plateau_derivative = np.mean(np.abs(dy[start:end]))
        plateau_derivatives.append(plateau_derivative)

    # calculate slope of plateau
    plateau_slopes = []
    for start, end in plateaus:
        x_slice = x[start:end]
        y_slice = y[start:end]
        if end - start > 1 and len(np.unique(x_slice)) > 1:
            # check if there are only two points, that they are not the same, if so, 
            slope, _, _, _, _ = linregress(x_slice, y_slice)
            plateau_slopes.append(slope)
        else:
            plateau_slopes.append(np.nan)

    #

    # Create results DataFrame for plateaus
    df_plat = pd.DataFrame({
        'plateaus': [i for i, _ in enumerate(plateaus)],
        'plateau_avg': [
            # Special calculation for last plateau average
            np.mean(y[start:start + max(1, int((end - start) * final_params['last_plateau_avg_percentage'] / 100.0))]) 
            if i == len(plateaus) - 1 
            else np.mean(y[start:end]) 
            for i, (start, end) in enumerate(plateaus)
        ],
        'delta_avg': plateau_delta_avg_arr,
        'start': [start for start, _ in plateaus],
        'end': [end for _, end in plateaus],
        'plateau_avg_idx': plateau_avg_idx_arr,
        'delta_time': [plateau_avg_idx * dt for plateau_avg_idx in plateau_avg_idx_arr],
        'mean dN/dt': plateau_derivatives,
        'velocity_calc_um_s': [calculate_velocity(x[start:end], dt_arr[start:end]) for start, end in plateaus],
        'plateau_slope': plateau_slopes,
        'tether_lifetime_m':[plateau_avg_idx * dx for plateau_avg_idx in plateau_avg_idx_arr],
        'tether_lifetime_s': [(end - start) * dt for start, end in plateaus],
        'average_velocity': velocity_um_s,
    })

    # Create dataframe of data for plotting
    df_data = {
        'x': x,
        'y': y,
        # 'dy_smooth': dy_smooth,
        'dy_abs_sav': dy_abs_sav,
        # 'is_flat': is_flat,
        'dt': dt_arr,
        'idx_max': idx_max,
    }
    
    return plateaus, df_plat, df_data, velocity_um_s

def process_single_file(filename, params=None, save_plots=False, output_dir=None):
    """
    Process a single TDMS file for tether analysis.
    
    Parameters:
        filename (str): Path to TDMS file
        curve_idx (int): Index of curve to analyze
        params (dict): Analysis parameters
        save_plots (bool): Whether to save plots
        output_dir (str): Directory to save outputs
    
    Returns:
        dict: Analysis results
    """
    
    print(f"\nProcessing file: {os.path.basename(filename)}")
    
    # Load file
    file = loadfile(filename)
    filemetadata = file.filemetadata
    
    # Get file parameters
    file_deflection_sensitivity = filemetadata['defl_sens_nmbyV']  # nm/V
    K = filemetadata['spring_const_Nbym']  # N/m
    height_channel_key = filemetadata['height_channel_key']
    defl_sens = file_deflection_sensitivity / 1e9  # m/V
    
    # Get force curve with parameters from GUI
    # z_sensor_delay = params.get('z_sensor_delay', 0.001)
    # bool_correct_overshoot = params.get('bool_correct_overshoot', True)
    force_curve = file.getcurve(0)
    force_curve.preprocess_force_curve(defl_sens, height_channel_key)
    
    # Get segments
    # segs = force_curve.get_segments()
    # final_nb_points = filemetadata['final_nb_points']
    relative_SR = filemetadata['relative_sr']
    
    # Extract retract segment data
    for segid, segment in force_curve.get_segments():
        if segment.segment_type in ('Approach', 'App'):
            pass  # We only need retract data for this analysis
        elif segment.segment_type in ('Retract', 'Ret'):
            ret_piezo = -segment.zheight
            ret_deflection = -segment.vdeflection * K
            relative_SR_ret = relative_SR[segid]
            vel_ret_um_s = segment.velocity * 1e-03  # Convert from nm to um/s
            time_ret = np.arange(len(ret_piezo)) * relative_SR_ret 
    
    # Tilt correction
    max_offset = params.get('max_offset', 100)  # %
    min_offset = params.get('min_offset', 70)   # %
    max_offset, min_offset = update_tilt_range(ret_piezo, max_offset, min_offset, offset_type='percentage')
    tilt_ret_deflection_N = correct_tilt(ret_piezo, ret_deflection, max_offset, min_offset)

    # ADD Denoise processing here
    filtered_signal = tilt_ret_deflection_N.copy()
    fourier_data = {}  # Initialize Fourier data storage
    
    # Apply denoising if enabled
    if params.get('enable_denoising', False):
        try:
            # Get denoising parameters
            w0 = params.get('denoise_w0', 0.1)
            w1 = params.get('denoise_w1', 1.0)
            butterworth_order = params.get('butterworth_order', 5)
            remove_percent = params.get('denoise_remove_percent', 10)
            remove_end_percent = params.get('denoise_remove_end_percent', 10)
            use_interpolation = params.get('denoise_interp', True)
            w_min = params.get('denoise_w_min', 1.0)
            w_max = params.get('denoise_w_max', 6.0)
            
            # Calculate remove indices for both start and end
            remove_start_index = remove_percent * len(ret_piezo) // 100
            remove_end_index = remove_end_percent * len(ret_piezo) // 100
            end_index = len(ret_piezo) - remove_end_index
            
            # Prepare signal for filtering (remove both start and end portions)
            from scipy.signal import detrend
            signal_trimmed = detrend(tilt_ret_deflection_N[remove_start_index:end_index])
            
            # Calculate parameters for FFT
            sampling_rate = 1 / relative_SR_ret
            velocity_calc = -calculate_velocity(ret_piezo, time_ret)  # µm/s
            
            # Apply Butterworth band-stop filter
            N = len(signal_trimmed)
            # Convert velocity to m/s for proper unit handling
            velocity_calc_m_s = velocity_calc * 1e-6  # Convert µm/s to m/s
            T = velocity_calc_m_s / sampling_rate  # m/sample

            # FFT
            yf = fft(signal_trimmed)
            xf = fftfreq(N, T)  # Now in units of m⁻¹
            
            # Store original FFT data
            fourier_data['xf'] = xf
            fourier_data['yf_original'] = yf.copy()
            
            # Apply Butterworth filter (convert µm⁻¹ to m⁻¹)
            w0_m_inv = w0 * 1e6  # Convert µm⁻¹ to m⁻¹
            w1_m_inv = w1 * 1e6  # Convert µm⁻¹ to m⁻¹
            butter_mask = butterworth_bandstop(xf, w0_m_inv, w1_m_inv, order=butterworth_order)
            yf_filtered = yf * butter_mask
            filtered_deflection = np.real(ifft(yf_filtered))
            
            # Store Butterworth filtered FFT data
            fourier_data['yf_filtered'] = yf_filtered.copy()
            
            # Update filtered signal (place filtered data back in the correct position)
            filtered_signal[remove_start_index:end_index] = filtered_deflection
            
            # Apply single Fourier band suppression
            filtered_signal = suppress_fourier_band(
                filtered_signal,
                sampling_rate=sampling_rate,
                velocity=velocity_calc,
                w_range=(w_min, w_max),
                remove=remove_start_index,
                remove_end=remove_end_index,
                interp=use_interpolation,
            )
            
            # Store final band-suppressed FFT data
            final_signal_trimmed = filtered_signal[remove_start_index:end_index]
            yf_band_suppressed = fft(final_signal_trimmed)
            fourier_data['yf_band_suppressed'] = yf_band_suppressed
            
            print(f"  Applied denoising: W0={w0}, W1={w1}, Order={butterworth_order}, Range=[{w_min}, {w_max}]")
            
        except Exception as e:
            print(f"  Warning: Denoising failed, using original signal: {e}")
            filtered_signal = tilt_ret_deflection_N.copy()
    
    # Use filtered signal for further processing
    tilt_ret_deflection_N = filtered_signal
    
    # Apply baseline correction a second time after denoising (using same offset values)
    if params.get('enable_denoising', False):
        print("  Applying second baseline correction after denoising...")
        tilt_ret_deflection_N = correct_tilt(ret_piezo, tilt_ret_deflection_N, max_offset, min_offset)
        print(f"  Second baseline correction applied using same offsets: max={max_offset}, min={min_offset}")
    
    # Find contact point
    index_first_positive = find_first_positive(tilt_ret_deflection_N)
    first_positive_displacement = ret_piezo[index_first_positive]
    ret_corrected_displacement = ret_piezo - first_positive_displacement
    
    # Apply Savitzky-Golay smoothing in force curve
    savitz_defl = savitzky_golay_smooth(tilt_ret_deflection_N, window_length=5, polyorder=1)
    
    # Extract data after contact point
    defl_savitz = savitz_defl[index_first_positive:]
    displacement = ret_corrected_displacement[index_first_positive:]
    rel_time = np.arange(len(displacement)) * relative_SR_ret
    
    # Find plateaus
    plateaus, df_plat, df_data, velocity_calc_um_s = find_plateaus(displacement, defl_savitz, params, dt=relative_SR_ret)
    
    # Save PNG plot if requested and plateaus were found
    png_path = None
    if save_plots and len(plateaus) > 0 and output_dir:
        # Create PNG filename based on original file
        base_name = os.path.splitext(os.path.basename(filename))[0]
        png_filename = f"{base_name}_plateau_analysis.png"
        png_path = os.path.join(output_dir, png_filename)
        
        # Generate PNG plot
        try:
            png_result = create_plateau_png(
                rel_time=time_ret,
                defl_savitz=defl_savitz,
                plateaus=plateaus,
                df_plat=df_plat,
                displacement=displacement,
                output_path=png_path,
                showDisplacementonX=False,  # Use time axis by default
                title=f'Plateau Analysis - {base_name}',
                width=1400,
                height=900
            )
            if png_result:
                png_path = png_result
        except Exception as e:
            print(f"  ⚠️  PNG generation failed: {e}")
            png_path = None
    
    # Create results dictionary
    results = {
        'filename': filename,
        'filemetadata': filemetadata,
        'plateaus': plateaus,
        'df_plat': df_plat,
        'rel_time': rel_time,
        'defl_savitz': defl_savitz,
        'displacement': displacement,
        'relative_SR_ret': relative_SR_ret,
        'index_first_positive': index_first_positive,
        'png_path': png_path,
        'velocity_metadata': -vel_ret_um_s,
        'velocity_calc_um_s': velocity_calc_um_s,
        'df_data': df_data,
        'fourier_data': fourier_data,
    }
    
    print(f"  Found {len(plateaus)} plateaus")
    
    return results

def batch_process_files(directory, file_indices=None, params=None, save_results=True, save_plots=True, output_dir=None):
    """
    Batch process multiple TDMS files for tether analysis.
    
    Parameters:
        directory (str): Directory containing TDMS files
        file_indices (list): List of file indices to process (if None, process all)
        params (dict): Analysis parameters
        save_results (bool): Whether to save results to CSV
        save_plots (bool): Whether to save PNG plots for each analyzed file
        output_dir (str): Output directory for results
    
    Returns:
        list: List of analysis results
    """
    print(f"Starting batch processing in directory: {directory}")
    
    # Get TDMS files
    first_file, all_files = grab_tdms(directory)
    print(f"Found {len(all_files)} TDMS files")
    
    # Select files to process
    if file_indices is None:
        files_to_process = all_files
        print("Processing all files")
    else:
        files_to_process = [all_files[i] for i in file_indices if i < len(all_files)]
        print(f"Processing {len(files_to_process)} selected files")
    
    # Default parameters
    if params is None:
        params = {
            'sav_window_length': 10,
            'sav_polyorder': 1,
            'pl_threshold': 150e-9,
            'pl_min_width': 2,
            'last_num_plateaus': 7,
            'max_offset': 100,  # % for tilt correction
            'min_offset': 70,   # % for tilt correction
            'z_sensor_delay': 0.001,
            'bool_correct_overshoot': True,
        }
    
    # Set up output directory
    if output_dir is None:
        output_dir = os.path.join(directory, 'tether_analysis_results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Process files
    all_results = []
    results = []
    
    for i, filename in enumerate(files_to_process):
        print(f"\nProcessing file {i+1}/{len(files_to_process)}")
        try:
            result = process_single_file(filename, params, save_plots=save_plots, output_dir=output_dir)
            all_results.append(result)
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            # Move file to error folder in the same directory
            error_folder = os.path.join(os.path.dirname(filename), 'error_files')
            os.makedirs(error_folder, exist_ok=True)
            try:
                os.rename(filename, os.path.join(error_folder, os.path.basename(filename)))
                print(f"Moved {filename} to {error_folder}")
            except Exception as move_err:
                print(f"Failed to move {filename} to error folder: {move_err}")
                all_results.append(None)
                
    
    # Mark files as successfully processed if they have plateaus
    for result in all_results:
        success = result is not None and 'plateaus' in result and len(result['plateaus']) > 0
        result['success'] = success
        if success:
            results.append(result)

    print("\nBatch processing complete!")
    print(f"Successfully processed: {len(results)}/{len(files_to_process)} files")
    
    # # Save summary results
    # if save_results and results:
    #     summary_data = []
    #     for result in results:
    #         index = 0
    #         if result['success'] and len(result['plateaus']) > 0:
    #             df_plat = result['df_plat']
    #             for i, (idx, row) in enumerate(df_plat.iterrows()):
    #                 summary_data.append({
    #                     'filename': os.path.basename(result['filename']),
    #                     'file_idx': i,  # Use the file index from the outer loop
    #                     'plateau_idx': int(row['plateaus']),
    #                     'plateau_avg': float(f"{row['plateau_avg']:.6g}"),
    #                     'delta_avg': float(f"{row['delta_avg']:.6g}"),
    #                     'delta_time': float(f"{row['delta_time']:.6g}"),
    #                     'mean_derivative': float(f"{row['mean dy/dx']:.6g}"),
    #                     'start_idx': int(row['start']),
    #                     'end_idx': int(row['end'])
    #                 })
    #         index += 1  # Increment index for each row in the summary dat
    # Save summary results
    if save_results and results:
        summary_data = []
        for file_idx, result in enumerate(results):
            if result['success'] and len(result['plateaus']) > 0:
                df_plat = result['df_plat']
                for idx, row in df_plat.iterrows():
                    summary_data.append({
                        'filename': os.path.basename(result['filename']),
                        'file_idx': file_idx,  # This now correctly increments for each file
                        'plateau_idx': int(row['plateaus']),
                        'plateau_avg': float(f"{row['plateau_avg']:.6g}"),
                        'delta_avg': float(f"{row['delta_avg']:.6g}"),
                        'delta_time': float(f"{row['delta_time']:.6g}"),
                        'mean_derivative': float(f"{row['mean dy/dx']:.6g}"),
                        'plateau_velocity_calc': float(f"{row['velocity_calc_um_s']:.6g}"),  # Add plateau velocity
                        'plateau_slope': float(f"{row['plateau_slope']:.6g}"),  # Add plateau slope
                        'velocity_metadata': float(f"{result['velocity_metadata']:.6g}"),  # Add metadata velocity
                        'start_idx': int(row['start']),
                        'end_idx': int(row['end'])
                    })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = os.path.join(output_dir, 'tether_analysis_summary.csv')
            summary_df.to_csv(summary_file, index=False)
            print(f"Summary results saved to: {summary_file}")
    
    return all_results

def suppress_fourier_band(signal, sampling_rate, velocity, w_range, remove=0, remove_end=0, interp=True):
    # Calculate end index
    end_index = len(signal) - remove_end
    signal_trimmed = signal[remove:end_index]
    N = len(signal_trimmed)
    # Convert velocity from µm/s to m/s for proper unit handling
    velocity_m_s = velocity * 1e-6
    T = velocity_m_s / sampling_rate  # m/sample

    yf = fft(signal_trimmed)
    xf = fftfreq(N, T)  # Now in units of m⁻¹

    xf_half = xf[:N//2]
    yf_half = yf[:N//2]

    # Convert w_range from µm⁻¹ to m⁻¹ for proper comparison
    w_range_m_inv = [w_range[0] * 1e6, w_range[1] * 1e6]
    
    # Get mask only for positive frequencies
    mask = (xf_half >= w_range_m_inv[0]) & (xf_half <= w_range_m_inv[1])
    xf_masked = xf_half[mask]
    yf_masked = yf_half[mask]

    if len(xf_masked) == 0:
        return signal.copy()  # Skip if no points in range
    
    yf_interp = yf.copy()
    if interp:
        # Interpolate suppressed region
        interp_vals = np.interp(xf_masked, [xf_masked[0], xf_masked[-1]],
                                [yf_masked[0], yf_masked[-1]])

        # Rebuild full FFT with interpolated suppression
        yf_interp = yf.copy()
        yf_interp[:N//2][mask] = interp_vals
        yf_interp[-(N//2):][::-1][mask] = np.conj(interp_vals)  # maintain Hermitian symmetry
    else:
        # Zero out the frequencies in the specified range
        yf_interp[:N//2][mask] = 0
        yf_interp[-(N//2):][::-1][mask] = 0

    signal_filtered = np.real(ifft(yf_interp))
    full_output = signal.copy()
    full_output[remove:end_index] = signal_filtered
    return full_output

# --- Butterworth Band-Stop Filter ---
def butterworth_bandstop(xf, f_low, f_high, order=5):
    f_center = (f_low + f_high) / 2
    bandwidth = f_high - f_low
    eps = 1e-12
    return 1 / (1 + ((xf * bandwidth) / ((xf**2 - f_center**2) + eps))**(2 * order))

# to run batch analysis standalone
if __name__ == "__main__":
    # Configuration
    directory = '/Users/evillz/Data/article/2025_07_01_THP1_phd/test_analysis/300'
    
    # Select specific file indices to process (None for all files)
    # file_indices = [29, 31]  # Example: process files at these indices
    # file_indices = None  # Process all files

    file_indices = None  # Process all files
    
    # Analysis parameters
    params = {
        'sav_window_length': 10,
        'sav_polyorder': 1,
        'pl_threshold': 150e-9,
        'pl_min_width': 2,
        'last_num_plateaus': 7,
        'max_offset': 100,  # % for tilt correction
        'min_offset': 70,   # % for tilt correction
        'z_sensor_delay': 0.001,
        'bool_correct_overshoot': True,
    }
    
    # Run batch processing
    results = batch_process_files(
        directory=directory,
        file_indices=file_indices,
        params=params,
        save_results=True,
        save_plots=False,  # Enable PNG generation for each analyzed file
        output_dir=None  # Will create 'tether_analysis_results' in the data directory
    ) 
    
    # Print summary statistics
    if results:
        total_plateaus = sum(len(r['plateaus']) for r in results)
        png_count = sum(1 for r in results if r.get('png_path') is not None)
        print("\nSummary Statistics:")
        print(f"Total plateaus detected: {total_plateaus}")
        print(f"Average plateaus per file: {total_plateaus/len(results):.1f}")
        print(f"PNG plots generated: {png_count}/{len(results)} files")
        
        # Show example of first successful result
        first_result = results[0]
        print(f"\nExample result from {os.path.basename(first_result['filename'])}:")
        print(first_result['df_plat'])
