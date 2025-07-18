

from pyfmreader.ps_nex.parseTDMS import grab_tdms
from pyfmreader import loadfile
import matplotlib.pyplot as plt 
from nptdms import TdmsFile #from nptdms import tdms  # pip install nptdms

import pandas as pd
import os 
import shutil
import seaborn as sns

import glob
import time
import traceback

from scipy.signal import savgol_filter
from scipy.stats import linregress

import numpy as np
import random

import math
pi = math.pi
import plotly.graph_objects as go


#%% File management functions %%#
def move_to_error_folder(fp, rootdir, error_msg=None, error_type=None, processing_stage="unknown", include_traceback=False):
    """
    Move error files to error folder and return detailed error information.
    
    Args:
        fp: File path
        rootdir: Root directory 
        error_msg: Error message
        error_type: Type of error (e.g., 'FileLoadError', 'ProcessingError')
        processing_stage: Stage where error occurred (e.g., 'file_loading', 'metadata_extraction', 'curve_processing')
        include_traceback: Whether to include full stack trace
    """
    error_folder = os.path.join(rootdir, 'error_file')
    if not os.path.exists(error_folder):
        os.makedirs(error_folder)
    
    # Move files
    try:
        shutil.move(fp, os.path.join(error_folder, os.path.basename(fp)))
        if os.path.exists(fp + '_index'):
            shutil.move(fp + '_index', os.path.join(error_folder, os.path.basename(fp) + '_index'))
    except Exception as move_error:
        print(f"Warning: Could not move file {fp}: {move_error}")
    
    # Capture stack trace if requested
    stack_trace = None
    if include_traceback:
        stack_trace = traceback.format_exc()
    
    if error_msg:
        print(f"ERROR in {processing_stage}: {error_msg}")
    print(f"Moved to error folder: {fp}")

    temp_dict = {
        'file_path': fp,
        'total_len': None,
        'total_len_cal_tick': None,
        'diff_cal': None,
        'diff_store': None,
        'total_len_stored_point': None,
        "store_nbpts_app": None,
        "store_nbpts_con": None,
        "store_nbpts_ret": None,
        "cal_nbpts_app": None,
        "cal_nbpts_con": None,
        "cal_nbpts_ret": None,
        "set_pt_z_pos_V": None,
        "error_message": error_msg,
        "error_type": error_type,
        "processing_stage": processing_stage,
        "stack_trace": stack_trace,
        "has_error": True
    }
    return temp_dict

def check_files_in_directory(directory, isMap=False):
    """ 
    Check all tdms files in directory to see for any errors in the files. If yes, move them to a new folder called 'error_file'.
    
    """

    if isMap:
        # Define the pattern to match files that start with "psnex_map__" and do not end with ".zip"
        pattern = os.path.join(directory, 'psnex_map__*')
        files = [f for f in glob.glob(pattern) if not f.endswith('.zip')]

    else:
        # Get all the folders in the directory including the directory itself
        folders = [f.path for f in os.scandir(directory) if f.is_dir()]
        folders.append(directory)

    print(f'# of folders found : {len(folders)}')

    # start time
    start_time = time.time()

    for rootdir in folders:
        
        # _,all_files,filenames = find_directories_with_file_type(rootdir,'.tdms')
        # Check if there are files inside the folder, if not, move folder into a new folder called 'empty_folders
        print (f"Checking folder: {rootdir}")
        
        try:
            first_file, all_files = grab_tdms(rootdir)
        except FileNotFoundError as e:
            print(f"TDMS FileNotFoundError: {e}")
            continue

        df_point_log = pd.DataFrame()

        tp_file = []
        for fp in all_files[:]:
            print(f'now analyzing {fp}')
            
            # Initialize default values for ALL variables
            temp_dict = {
                'file_path': fp,
                'total_len': None,
                'total_len_cal_tick': None,
                'diff_cal': None,
                'diff_store': None,
                'total_len_stored_point': None,
                "store_nbpts_app": None,
                "store_nbpts_con": None,
                "store_nbpts_ret": None,
                "cal_nbpts_app": None,
                "cal_nbpts_con": None,
                "cal_nbpts_ret": None,
                "set_pt_z_pos_V": None,
            }

            # Try to load the file
            try:
                file = loadfile(fp)
            except (KeyError, TypeError, ValueError, UnboundLocalError) as e:
                move_to_error_folder(fp, rootdir, f"{type(e).__name__}: {e}")
                # Log the error file with None values
                df_temp = pd.DataFrame([temp_dict])  # Note: [temp_dict] not temp_dict
                df_point_log = pd.concat([df_point_log, df_temp], ignore_index=True)
                continue  # Skip to next file
            except Exception as e:
                move_to_error_folder(fp, rootdir, f"Unexpected error loading file: {e}")
                # Log the error file with None values
                df_temp = pd.DataFrame([temp_dict])
                df_point_log = pd.concat([df_point_log, df_temp], ignore_index=True)
                continue  # Skip to next file
            
            # if error in loading file, do not execute this part
            if file is not None:
                try:
                    filemetadata = file.filemetadata
                    #closed_loop = filemetadata['z_closed_loop']
                    file_deflection_sensitivity = filemetadata['defl_sens_nmbyV']  # nm/V
                    file_spring_constant = filemetadata['spring_const_Nbym']  # N/m
                    height_channel = filemetadata['height_channel_key']
                    #force_set_point = filemetadata["force_setpoint"]
                    deflection_sensitivity = filemetadata['defl_sens_nmbyV'] / 1e9  # m/V
                    spring_constant = file_spring_constant
                
                    curve_properties = filemetadata['curve_properties']
                    tick_time_s = filemetadata['instrument_tick_time_(s)']# 2* 10**-6

                    force_curve = file.getcurve(0)
                    # Preprocess curve
                    force_curve.preprocess_force_curve(deflection_sensitivity, height_channel)
                    tdms_file_ps_nex_file = TdmsFile.open(fp)
                    tdms_groups = tdms_file_ps_nex_file.groups() 
                    tdms_psnex_fc = tdms_groups[0]
                    
                    height = tdms_psnex_fc[height_channel][:]
                    total_len = len(height)
                    stored_arr =[]
                    cal_arr = []

                    for i, segment in force_curve.get_segments():
                        temp_seg_dict = curve_properties[str(0)][i]
                        seg_i_pt_cal = temp_seg_dict[f"segment_{i}_nb_points_cal"]
                        seg_i_pt_stored = temp_seg_dict[f"segment_{i}_nb_points_(points)"]
                        stored_arr.append(seg_i_pt_stored)
                        cal_arr.append(seg_i_pt_cal)

                        segment_duration = temp_seg_dict[f"segment_{i}_duration_(ticks)"]*tick_time_s
                        if i ==0:
                            set_pt_z_pos_V = temp_seg_dict[f"segment_{i}_Z_position_setpoint_trigger_(V)"]
                        print(f"segment duration {segment_duration}, \n numb of point cal (ticks, dec, sampling rate {seg_i_pt_cal}, num pts stored per segment {seg_i_pt_stored}")
            
                    # Update temp_dict with successful values
                    temp_dict.update({
                        'total_len': total_len,
                        'total_len_cal_tick': sum(cal_arr),
                        'diff_cal': total_len - sum(cal_arr),
                        'diff_store': total_len - sum(stored_arr),
                        'total_len_stored_point': sum(stored_arr),
                        "store_nbpts_app": stored_arr[0] if stored_arr else None,
                        "store_nbpts_con": stored_arr[1] if len(stored_arr) > 0 else None,
                        "store_nbpts_ret": stored_arr[2] if len(stored_arr) > 1 else None,
                        "cal_nbpts_app": cal_arr[0] if cal_arr else None,
                        "cal_nbpts_con": cal_arr[1] if len(cal_arr) > 0 else None,
                        "cal_nbpts_ret": cal_arr[2] if len(cal_arr) > 1 else None,
                        "set_pt_z_pos_V": set_pt_z_pos_V if 'set_pt_z_pos_V' in locals() else None
                    })
                    
                except Exception as e:
                    move_to_error_folder(fp, rootdir, f"Error processing file: {e}")
                    # temp_dict already has None values, so we're good
                    
            # ALWAYS log the file (moved inside the loop!)
            df_temp = pd.DataFrame([temp_dict])
            df_point_log = pd.concat([df_point_log, df_temp], ignore_index=True)

        # Save results for this folder (this stays outside the file loop)
        if not df_point_log.empty:
            results_folder = os.path.join(rootdir, 'results')
            if not os.path.exists(results_folder):
                os.makedirs(results_folder)
            df_point_log.to_csv(os.path.join(results_folder, 'df_point_log.csv'), index=False)

    # Print the total time taken
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time} seconds")

#%% Main Analysis functions to analyze tether data %%#
def find_first_positive(arr):
    """
    Returns an array of first positives in a NumPy array.
    Returns None if no positive value is found.
    """
    arr = np.asarray(arr)
    positives = np.where(arr > 0)[0]
    return positives if positives.size > 0 else None

def savitzky_golay_smooth(y, window_length=11, polyorder=3):
    """
    Applies Savitzky-Golay smoothing to a 1D array.

    Parameters:
    - y: array-like, the signal to smooth
    - window_length: int, length of the filter window (must be odd and >= polyorder+2)
    - polyorder: int, order of the polynomial used to fit the samples

    Returns:
    - smoothed_y: numpy array, the smoothed signal
    # """
    y = np.asarray(y)
    # Ensure window_length is odd and less than or equal to the size of y
    if window_length % 2 == 0:
        window_length += 1
    if window_length > len(y):
        window_length = len(y) if len(y) % 2 == 1 else len(y) - 1
    return savgol_filter(y, window_length=window_length, polyorder=polyorder)

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

def update_tilt_range(zheight, max, min, offset_type='percentage'):
    """
    Use this function with the correct_tilt function from pyfmrheo.utils.force_curves.py
    """
    if offset_type == 'percentage':
        deltaz = zheight.max() - zheight.min()
        maxperc = max / 1e2
        minperc = min / 1e2
        maxoffset = zheight.min() + deltaz * maxperc
        minoffset = zheight.min() + deltaz * minperc
    elif offset_type == 'absolute':
        maxoffset = max / 1e9
        minoffset = min / 1e9
    return maxoffset, minoffset

def find_plateaus(y, params=None, dt = 1e-3, plot_results=False):
    """
    Identify plateaus in 1D data where the first derivative is close to 0.

    Parameters:
        y (array): 1D signal (e.g., deflection).
        params (dict, optional): Dictionary of parameters to override defaults:
            - 'sav_window_length' (int): Window length for Savitzky-Golay smoothing.
            - 'sav_polyorder' (int): Polynomial order for Savitzky-Golay filter.
            - 'pl_threshold' (float): Max allowed slope (abs(dy/dx)) for plateau detection.
            - 'pl_min_width' (int): Minimum length (in points) of a plateau.
            - 'last_num_plateaus' (int): Number of plateaus to keep from the end.
        dt (float, optional): Spacing between x-values. Default is 1e-3.

    Returns:
        plateaus (list of tuples): List of (start_idx, end_idx) for each detected plateau.
        df_plat (pd.DataFrame): DataFrame with plateau statistics (average, delta, indices, etc.).

    Steps:
        1. Set default and user parameters for smoothing and plateau detection.
        2. Compute the derivative of y with respect to x.
        3. Smooth the derivative using Savitzky-Golay filtering.
        4. Identify regions where the smoothed derivative is below a threshold (potential plateaus).
        5. Filter plateaus by minimum width and keep only the last N plateaus if specified.
        6. For each plateau, calculate statistics such as average value, index of average, and mean derivative.
        7. Compute the difference (delta) between consecutive plateau averages.
        8. Store all plateau statistics in a pandas DataFrame.
        9. Optionally, plot the results for debugging and visualization.
    """

    # Define default parameters
    default_params = {

        'sav_window_length': 10,
        'sav_polyorder': 1,

        'pl_threshold': 0.01,
        'pl_min_width': 20,

        'last_num_plateaus': 5,  # Number of plateaus to ignore at the end
    }
    
    # Merge with input params (input params override defaults)
    if params is None:
        params = {}
    
    final_params = {**default_params, **params}

    # Calculate derivative of the signal, smooth it, and apply Savitzky-Golay filter
    dy = np.gradient(y, dt)
    dy_smooth = np.abs(dy)
    dy_smooth_sav = savitzky_golay_smooth(
            dy_smooth,
            window_length=final_params['sav_window_length'], 
            polyorder=final_params['sav_polyorder']
            )

    x = np.arange(len(y)) * dt  # Create x-axis based on dt

    if plot_results:
        plt.figure(figsize=(12, 6))
        # Debug Plot processed signals
        plt.plot(x, dy, label='dy')
        plt.plot(x, dy_smooth, label='dy_smooth')
        plt.plot(x, dy_smooth_sav, label='dy_smooth_sav')
        print(final_params['pl_threshold'])
        plt.axhline(final_params['pl_threshold'], color='r', linestyle='--', label='pl_threshold')
        plt.title('Segment: dy/dx vs x')
        plt.xlabel('x')
        plt.legend()
        plt.show()

    #n Find flat plateaus in Savitzky-Golay smoothed signal
    is_flat = dy_smooth_sav < final_params['pl_threshold']
    plateaus = []
    start = None
    for i, flat in enumerate(is_flat):
        if flat and start is None:
            start = i
        elif not flat and start is not None:
            if i - start >= final_params['pl_min_width']:
                plateaus.append((start, i))
            start = None
    if start is not None and len(y) - start >= final_params['pl_min_width']:
        plateaus.append((start, len(y)))

    # Define how many plateaus to show starting from the end
    plateaus = plateaus[-final_params['last_num_plateaus']:]

    plateau_avg_idx_arr = []
    # Get the average of each plateau and index of this mean average
    for i, (start, end) in enumerate(plateaus):
        plateau_avg = np.mean(y[start:end])
        # Find the index of the value in y[start:end] closest to plateau_avg
        plateau_avg_idx = start + np.argmin(np.abs(y[start:end] - plateau_avg))
        if i == len(plateaus) - 1:
            plateau_avg_idx_arr.append(start - 1)  # Use start-1 for the last plateau
            print(f'Plateau {i} (last): start={start}, end={end}, average={plateau_avg:.2e}, avg_idx={plateau_avg_idx}')
        else:
            plateau_avg_idx_arr.append(plateau_avg_idx)
            print(f'Plateau {i}: start={start}, end={end}, average={plateau_avg:.2e}, avg_idx={plateau_avg_idx}')    
    
    plateau_delta_avg_arr = []
    # Get the delta of each average of plateau 
    for i, (start, end) in enumerate(plateaus):
        if i > 0:
            prev_avg = np.mean(y[plateaus[i-1][0]:plateaus[i-1][1]])
            # delta_avg = plateau_avg - prev_avg
            print(f'Plateau {i}: delta from previous Y_avg={prev_avg:.2e}')
            plateau_delta_avg_arr.append(prev_avg)
        else:
            # For the first plateau (i == 0), subtract the last plateau average from the first
            last_avg = np.mean(y[plateaus[-1][0]:plateaus[-1][1]])
            first_avg = np.mean(y[start:end])
            delta_first_last = first_avg - last_avg
            # print(f'Plateau {i}: delta from last plateau Y_avg={last_avg:.2e}')
            print(f'Plateau {i}: delta from starting 0 = {delta_first_last:.2e}')
            plateau_delta_avg_arr.append(first_avg)

    # Get the dt of the segment from 0 to the end of the plateau
    for i, (start, end), plateau_avg_idx in zip(range(len(plateaus)), plateaus, plateau_avg_idx_arr):
        delta_time = plateau_avg_idx * dt
        print(f'Plateau {i}: delta time from 0 to avg plat={delta_time:.2e} sec, Y_avg={y[plateau_avg_idx]:.2e}')     


    # create dataframe of plateaus, plateaus_avg, and delta_avg, include plateau index and plateaus
    # shortened functions are done in dataframe, longer are above for debugging


    # Calculate the mean of the derivative of each plateau from dy
    plateau_derivatives = []
    for start, end in plateaus:
        plateau_derivative = np.mean(np.abs(dy_smooth_sav[start:end]))
        plateau_derivatives.append(plateau_derivative)
        print(f'Plateau {len(plateaus)}: dy/dx avg={plateau_derivative:.2e}')


    df_plat = pd.DataFrame({
        'plateaus': [i for i, _ in enumerate(plateaus)],
        'plateau_avg': [np.mean(y[start:end]) for start, end in plateaus],
        'delta_avg': plateau_delta_avg_arr,
        'start': [start for start, _ in plateaus],
        'end': [end for _, end in plateaus],
        'plateau_avg_idx': plateau_avg_idx_arr,
        'delta_time': [plateau_avg_idx * dt for plateau_avg_idx in plateau_avg_idx_arr],
        'mean dy/dx': plateau_derivatives,
        'plateau_std.dev': [np.std(y[start:end]) for start, end in plateaus],
        'plateau_MSE': [np.mean((y[start:end] - np.mean(y[start:end]))**2) for start, end in plateaus]
    })

    ### Debug plot plateaus along x axis using plotly
    if plot_results:
        plateau_shapes = []
        colors = ['rgba(31,119,180,0.3)', 'rgba(255,127,14,0.3)', 'rgba(44,160,44,0.3)', 
                'rgba(214,39,40,0.3)', 'rgba(148,103,189,0.3)', 'rgba(140,86,75,0.3)', 
                'rgba(227,119,194,0.3)', 'rgba(127,127,127,0.3)', 'rgba(188,189,34,0.3)', 
                'rgba(23,190,207,0.3)']

        avg_traces = []
        for i, (start, end) in enumerate(plateaus):
            plateau_shapes.append(
                dict(
                    type="rect",
                    xref="x", yref="paper",
                    x0=x[start], x1=x[end-1],
                    y0=0, y1=1,
                    fillcolor=colors[i % len(colors)],
                    line=dict(width=0),
                    layer="below"
                )
            )
            # Plot the average as a horizontal line
            plateau_avg = np.mean(y[start:end])
            avg_traces.append(go.Scatter(
                x=[x[start], x[end-1]],
                y=[plateau_avg, plateau_avg],
                mode='lines',
                line=dict(color=colors[i % len(colors)].replace('0.3', '1.0'), width=2, dash='dash'),
                name=f'Avg Pl {i}: {plateau_avg:.2g}'
            ))

            # Plot the delta between this and previous average as a vertical line
            if i > 0:
                prev_start, prev_end = plateaus[i-1]
                prev_avg = np.mean(y[prev_start:prev_end])
                delta_x = x[start]
                avg_traces.append(go.Scatter(
                x=[delta_x, delta_x],
                y=[prev_avg, plateau_avg],
                mode='lines',
                line=dict(color='black', width=1, dash='dot'),
                name=f'Delta {i-1}-{i}: {plateau_avg - prev_avg:.2g}'
                ))

        trace = go.Scatter(x=x, y=y, mode='lines', name='Signal')
        layout = go.Layout(
            title='Detected Plateaus in y along x',
            xaxis=dict(title='x'),
            yaxis=dict(title='y'),
            shapes=plateau_shapes,
            showlegend=True
        )
        fig = go.Figure(data=[trace] + avg_traces, layout=layout)
        fig.show()

    # Return values for plotting and list of plateaus
    
    return plateaus, df_plat

#%% Plotting functions %%#
def generate_random_colors(n, alpha=0.3):
    """
    Generate n random rgba color strings for plotly.
    """
    colors = []
    for _ in range(n):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        colors.append(f'rgba({r},{g},{b},{alpha})')
    return colors

def plot_plateaus_with_plotly(x, y, plateaus, colors=None):
    """
    Debug plot plateaus along x axis using plotly.

    Args:
        x (np.ndarray): x-axis data
        y (np.ndarray): y-axis data
        plateaus (list of tuples): List of (start_idx, end_idx) for plateaus
        colors (list): List of color strings for plotly

    Returns:
        None (shows plotly figure)
    """
    import plotly.graph_objs as go

    if colors is None:
        colors = generate_random_colors(len(plateaus))

    plateau_shapes = []
    for i, (start, end) in enumerate(plateaus):
        plateau_shapes.append(
            dict(
                type="rect",
                xref="x", yref="paper",
                x0=x[start], x1=x[end-1],
                y0=0, y1=1,
                fillcolor=colors[i % len(colors)],
                line=dict(width=0),
                layer="below"
            )
        )
    avg_traces = []
    for i, (start, end) in enumerate(plateaus):
        plateau_avg = np.mean(y[start:end])
        avg_traces.append(go.Scatter(
            x=[x[start], x[end-1]],
            y=[plateau_avg, plateau_avg],
            mode='lines',
            line=dict(color=colors[i % len(colors)].replace('0.3', '1.0'), width=2, dash='dash'),
            name=f'Avg Pl {i}: {plateau_avg:.2f}'
        ))

    trace = go.Scatter(x=x, y=y, mode='lines', name='Signal')
    layout = go.Layout(
        title='Detected Plateaus in y along x',
        xaxis=dict(title='x'),
        yaxis=dict(title='y'),
        shapes=plateau_shapes,
        showlegend=True
    )
    fig = go.Figure(data=[trace] + avg_traces, layout=layout)

    # Add invisible traces for legend
    for i, (start, end) in enumerate(plateaus):
        plateau_avg = np.mean(y[start:end])
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(color=colors[i % len(colors)]),
            name=f'Pl {i}: {x[end-1]-x[start]:0.1f} x, avg={plateau_avg:.2f}'
        ))

    fig.show()


#%% saving functions %%#
def create_plateau_png(rel_time, defl_savitz, plateaus, df_plat, 
                       output_path='plateau_analysis.png', 
                       showDisplacementonX=False, 
                       title='Detected Plateaus with Averages and Δ',
                       width=1200, height=800):
    """
    Create and save a PNG file of the plateau analysis graph.
    
    Parameters:
        rel_time (array): Time or displacement array
        defl_savitz (array): Savitzky-Golay smoothed deflection data
        plateaus (list): List of (start, end) tuples for plateau regions
        df_plat (DataFrame): DataFrame with plateau analysis results
        output_path (str): Path where to save the PNG file
        showDisplacementonX (bool): If True, shows displacement on x-axis, else time
        title (str): Title for the plot
        width (int): Width of the image in pixels
        height (int): Height of the image in pixels
    
    Returns:
        str: Path to the saved PNG file
    """
    import plotly.graph_objects as go
    import os
    
    # Prepare the figure
    fig = go.Figure()

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
    try:
        fig.write_image(output_path, format='png', engine='kaleido')
        print(f"✅ PNG saved successfully: {output_path}")
        print(f"📊 File size: {os.path.getsize(output_path)} bytes")
        return output_path
    except Exception as e:
        print(f"❌ Error saving PNG: {e}")
        print("💡 Make sure you have kaleido installed: pip install kaleido")
        return None

# Example usage function
def save_current_analysis_as_png(filename='plateau_analysis.png', rel_time=None, defl_savitz=None, plateaus=None, df_plat=None):
    """
    Save the current plateau analysis as a PNG file using the data from the notebook.
    This function uses the global variables from the notebook analysis.
    """
    if 'plateaus' in globals() and 'df_plat' in globals():
        output_path = create_plateau_png(
            rel_time=rel_time,
            defl_savitz=defl_savitz, 
            plateaus=plateaus,
            df_plat=df_plat,
            output_path=filename,
            showDisplacementonX=False,
            title=f'Plateau Analysis - {os.path.basename(filename)}',
            width=1400,
            height=900
        )
        return output_path
    else:
        print("❌ No plateau analysis data found. Run the analysis first!")
        return None