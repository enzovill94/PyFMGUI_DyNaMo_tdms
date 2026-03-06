import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from pyfmreader import loadfile

from pyfmreader.ps_nex.parseTDMS import get_channel_names, parse_tdms
from typing import Tuple, Dict

from typing import Optional



def smooth_derivative(y, t, window_size=5):
    """
    Computes the derivative of y with respect to t, and applies a moving average for smoothing.

    Parameters:
    - y: array-like, the signal values
    - t: array-like, the time values (must be the same length as y)
    - window_size: int, the size of the moving average window (in number of points)

    Returns:
    - smoothed_derivative: numpy array of the smoothed derivative
    """

    y = np.asarray(y)
    t = np.asarray(t)
    
    # Ensure input validity
    if y.shape != t.shape:
        raise ValueError("y and t must be the same shape.")
    
    # Numerical derivative using central differences
    dy_dt = np.gradient(y, t)
    
    # Moving average smoothing (pandas handles edges nicely)
    smoothed = pd.Series(dy_dt).rolling(window=window_size, center=True, min_periods=1).mean().to_numpy()
    
    return smoothed

def plot_fft_signals_plotly(sampling_rate, **signals):
    """
    Plot the FFT of multiple signals in the frequency domain using Plotly.

    Parameters:
    sampling_rate (float): Sampling rate of the signals.
    **signals: Keyword arguments where the key is the signal name and the value is the signal data (np.ndarray).
    """
    fig = go.Figure()

    for signal_name, signal in signals.items():
        # Compute the FFT of the signal
        fft_signal = np.fft.fft(signal)
        
        # Compute the corresponding frequencies
        freqs = np.fft.fftfreq(len(signal), 1 / sampling_rate)
        
        # Add the FFT data to the plot
        fig.add_trace(go.Scatter(x=freqs[:len(freqs)//2], y=np.abs(fft_signal)[:len(freqs)//2], mode='lines', name=f'FFT of {signal_name}'))

    # Update the layout
    fig.update_layout(
        title='FFT of the Signals',
        xaxis_title='Frequency (Hz)',
        yaxis_title='Amplitude',
        xaxis_type='log',
        yaxis_type='log',
        template='plotly_white'
    )

    # Show the plot
    fig.show()

def plot_signals_logscale_plotly(freqs, plt_title = 'FFT of the Signals',\
                                 x_title = 'Frequency (Hz)',
                                 y_title = 'Amplitude',
                                 
                                 
                                  **signals):
    """
    Plot the FFT of multiple signals in the frequency domain using Plotly.

    Parameters:
    freqs (np.ndarray): Frequency array.
    **signals: Keyword arguments where the key is the signal name and the value is the signal data (np.ndarray).
    """
    pio.templates.default = 'plotly_dark'  # or try 'ggplot2', 'seaborn', etc.
    fig = go.Figure()

    for signal_name, signal in signals.items():
        # Compute the FFT of the signal
        fft_signal = np.fft.fft(signal)
        
        # Add the FFT data to the plot
        fig.add_trace(go.Scatter(x=freqs[:len(freqs)//2], y=np.abs(fft_signal)[:len(freqs)//2], mode='lines', name=f'FFT of {signal_name}'))

    # Update the layout
    fig.update_layout(
        title=plt_title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis_type='log',
        yaxis_type='log',
        # template='plotly_white',
        legend=dict(x=0.01, y=0.99),
        width=1000,
        height=600,
        paper_bgcolor='black',  # Black background
        plot_bgcolor='black'    # Black plot area
    )

    # Show the plot
    fig.show()
# metadata, piezo_um, deflection_zero_N, time_s

def load_fcurve_metadata (file:str) -> Tuple[Dict[str, float], np.ndarray, np.ndarray, np.ndarray]:
    """
    Loads the metadata using pyfmreader's Loadfile.filemetadata function

    Parameters:
    - file: filepath to .tdms file 

    Returns:
    - metadata : numpy array of the smoothed derivative
    - piezo_um : numpy array of piezo channnel in µm
    - deflection_N_zero : numpy array of deflection channel in N
    - time : numpy array of time channel in seconds
    """

    # constants
    z_stage_loop_constant = 80 # to scale the v_tick_ to match the 500Khz 


    # Read Channel data from tdms 
    channels = get_channel_names(file)
    name_deflectionChannel = channels[0][0]
    name_zDisplacement = channels[0][1]
    # for channel in channels:
    #     print(channel)
    channel_data_deflection, channel_data_piezo, channel_time = parse_tdms(file, deflectionChannel=name_deflectionChannel, zDisplacement=name_zDisplacement)

    # Open file metadata
    file_meta = loadfile(file)
    metadata= file_meta.filemetadata


    # Load all necessary metadata
    dec_app = int(metadata['curve_properties']['0'][0]['segment_0_dec_factor'])
    dec_con = int(metadata['curve_properties']['0'][1]['segment_1_dec_factor'])
    dec_ret = int(metadata['curve_properties']['0'][2]['segment_2_dec_factor'])

    fs = float(metadata['curve_properties']['0'][0]['segment_0_sampling_rate_(S/s)'])
    dt = 1/fs
    if dec_app and dec_con and dec_ret:
        print(f'All segments have decimation factors: {dec_app}, {dec_con}, {dec_ret}')

    app_vel_v_tick = float(metadata['curve_properties']['0'][0]['segment_0_velocity(V/tick)'])
    ret_vel_v_tick = float(metadata['curve_properties']['0'][2]['segment_2_velocity(V/tick)'])
    tick_time = float(metadata['instrument_tick_time_(s)'])


    decimation_factor = metadata['curve_properties']['0'][0]['segment_0_dec_factor']

    # get sensitivities for Z calibration
    z_sens_um_v = float(metadata['curve_properties']['0'][0]['z_stage_sensitivity'])*1e-3
    k = float(metadata['cantilever_spring_constant_calib_N/m']) # N/m
    invols_m_v = float(metadata['invOLS_(nm/V)']) * 1e-9 # nm/V

    #% calculate velocities
    app_um_s = app_vel_v_tick * (tick_time * z_stage_loop_constant) 
    ret_um_s = ret_vel_v_tick * (tick_time * z_stage_loop_constant) 

    # convert channles to proper units
    piezo_um = channel_data_piezo * z_sens_um_v
    deflection_N = channel_data_deflection * invols_m_v * k  # convert to um
    deflection_zero_N = deflection_N - deflection_N.mean() #subtract the mean to get center the curve on zero
    time_s = channel_time * dt * decimation_factor # convert to seconds


    metadata = {
        'ch_name_vdeflection': name_deflectionChannel,
        'ch_name_zpiezo': name_zDisplacement,
        'vel_app_um_s': app_um_s,
        'vel_ret_um_s': ret_um_s,
        'fs': fs,
        'z_sens_um_v': z_sens_um_v,
        'K_N_m': k,
        'invols_m_v': invols_m_v,
    }
    return metadata, piezo_um, deflection_zero_N, time_s




def plot_force_curve(
    time_s: np.ndarray,
    piezo_um: np.ndarray,
    deriv_piezo_smooth: np.ndarray,
    deflection_zero_uN: np.ndarray,
    color1: str = 'red',
    color2: str = 'black',
    def_color: str = 'green'
) -> None:
    """
    Plot force curve with piezo displacement, velocity, and deflection using Plotly.

    Parameters:
        time_s (np.ndarray): Time array in seconds.
        piezo_um (np.ndarray): Z piezo displacement in micrometers.
        deriv_piezo_smooth (np.ndarray): Smoothed derivative of piezo position (velocity).
        deflection_zero_uN (np.ndarray): Deflection force in microNewtons.
        color1 (str): Color for piezo trace.
        color2 (str): Color for velocity trace.
        def_color (str): Color for force trace.
    """

    pio.templates.default = 'plotly_dark'  # Set Plotly template

    fig = go.Figure()

    # Z piezo(µm)
    fig.add_trace(go.Scatter(
        x=time_s,
        y=piezo_um,
        mode='lines',
        name='Z piezo(µm)',
        yaxis='y1',
        line=dict(color=color1, width=2)
    ))

    # Z vel(mm/s)
    fig.add_trace(go.Scatter(
        x=time_s,
        y=deriv_piezo_smooth * 10,
        mode='lines',
        name='Z vel(mm/s)',
        yaxis='y2',
        line=dict(color=color2, width=2)
    ))

    # Force (µN)
    fig.add_trace(go.Scatter(
        x=time_s,
        y=deflection_zero_uN,
        mode='lines',
        name='Force (µN)',
        yaxis='y3',
        line=dict(color=def_color, width=2)
    ))

    fig.update_layout(
        title='Z piezo fast approach force curve',
        title_font=dict(size=24, color='black'),
        showlegend=False,
        xaxis=dict(
            title=dict(
                text='Time (ms)',
                font=dict(size=24, family='Arial')
            ),
            showgrid=True,
            color='black',
            tickfont=dict(size=24)
        ),
        yaxis=dict(
            title='piezo(µm)',
            tickformat='1.f',
            side='right',
            showgrid=False,
            color=color1,
            tickfont=dict(size=24)
        ),
        yaxis2=dict(
            title='Vel(mm/s)',
            overlaying='y',
            side='left',
            showgrid=True,
            color=color2,
            position=0.0,
            tickfont=dict(size=24)
        ),
        yaxis3=dict(
            title='Force(N)',
            overlaying='y',
            side='left',
            showgrid=False,
            color=def_color,
            position=0.2,
            tickfont=dict(size=24)
        ),
        legend=dict(
            x=0.99, y=0.99,
            font=dict(color='black', size=24),
        ),
        width=1000,
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    fig.show()