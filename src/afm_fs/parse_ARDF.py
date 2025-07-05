#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 2025

@author: Carlota
"""

import numpy as np
import os
from ardf.read_ardf import read_ardf_metadata # functions needed to work with ARDF data
from ardf.get_ardf_data import extract_ardf_data # functions needed to work with ARDF data

def grab_ardf(directory):
    all_ardf = []
    # Maybe for my files its better to sort based on the numbering in the filename?
    # Comment above is pending
    files = sorted(os.scandir(directory), key=lambda d: d.stat().st_mtime)
    for entry in files:
        # take only files wiht .ARDF extension
        if entry.is_file() and entry.name.endswith(".ARDF"):
            all_ardf.append(entry.path)
    # if not all_ardf:
    #    return None, []
    # returns the first file
    return all_ardf[0], all_ardf


def parse_ardf(file, line, point, trace, file_struct):
    """
    This function opens .ARDF file and extracts the deflection, piezo movement
    and time

    Parameters
    ----------
    file : str
        the name of the ARDF file.
    point : int
        1st position in ARDF file forcemap to analyze
    line: int
        2nd position in the ARDF file forcemap to analyze
    trace: int
        Pending proper explanation here
    file_struct: dict
        Dictionary containing metadata about the ARDF file as a whole

    Returns
    -------
    channel_data_deflection : numpy array

    channel_data_piezo : numpy array
    
    time: numpy

    """
    # Extract data from .ARDF file and specific force distance curve
    ardf_data = extract_ardf_data(file, line, point, trace, file_struct)

    # The list needs cleaning because it contains null bytes -> \x00 at the end
    clean_channel_list = [s.rstrip('\x00') for s in file_struct['channelList'][0]]
    
    # channel_piezo = clean_channel_list[clean_list.index('ZSnsr')]
    # channel_deflection = clean_channel_list[clean_list.index('Defl')]

    # Removes the tail of 0s in the array (it is an artifact from parsing ARDF files)
    # We need to multiply by -1 to change the sign of the data 
    last_nonzero_piezo = np.nonzero(ardf_data['y'][:, clean_channel_list.index('ZSnsr')])[0][-1]
    channel_data_piezo = (ardf_data['y'][:, clean_channel_list.index('ZSnsr')][:last_nonzero_piezo + 1])*-1
    last_nonzero_deflection = np.nonzero(ardf_data['y'][:, clean_channel_list.index('Defl')])[0][-1]
    channel_data_deflection = ardf_data['y'][:, clean_channel_list.index('Defl')][:last_nonzero_deflection + 1]*-1

    
    # Generate time channel from .ARDF metadata
    # How much the sampling rate was reduced compared to maximum
    # 1 - you kept all points
    # 2 - only every 2nd point kept
    force_decimation = float(file_struct['Notes']['ForceDecimation'])
    n_pts_per_sec = float(file_struct['Notes']['NumPtsPerSec'])
    real_sampling_rate = n_pts_per_sec / force_decimation  # in Hz
    sampling_interval = 1 / real_sampling_rate
    time = np.arange(len(channel_data_deflection)) * sampling_interval

    # Indexes indicating when approach, retraction and baseline start, repectively
    pnt_list = [ardf_data['pnt0'], ardf_data['pnt1'], ardf_data['pnt2']]

    return channel_data_deflection, channel_data_piezo, time, pnt_list



def get_force_and_params_ardf(file_struct, channel_data_deflection, channel_data_piezo, pnt_list):
    """
    This function converts the deflection and the piezo mouvement 
    to force versus extension curve
    It also extracts important parameters from the file_struct dictionary

    Parameters - ARDF files
    ----------
    file_struct : dict
        The dictionary contains metadata from .ARDF files
    channel_data_deflection : numpy array
        the deflection data in m
    channel_data_piezo : numpy array
        the piezo data in m

    Returns
    -------
    distance : numpy array
        distance in nm
    force : numpy array
       the force data in pN
    K : float
        the spring constant (N/m).
    invOLS : float
        inverse optical level sensitivity 
    sensitivity : float
        optical level sensitivity  (nm/V)
    piezo_gain : float
        
    index_end_approach : int
        index end of the approach
    index_start_approach : int
        index start of the approach
    index_start_retract : int
        index start of retract
    index_end_retract : int
        index end of approach

    """
        
    # Initialize variables
    force= []
    distance= []
        
    # Maybe adding here some error handling
    # What happens if we didnt collect sensitivity
    # In .ARDF files raw invOLS comes in m/V
    # raw K comes in N/m
    sensitivity = float(file_struct['Notes']['ZLVDTSens']) #unit: m/V
    invOLS= float(file_struct['Notes']['InvOLS']) * 1e-9  #unit: nm/V
    K= float(file_struct['Notes']['SpringConstant']) #unit N/m

    # Didnt find a match for piezo_gain
    # I think it's because you get raw data as a distance already in ARDF files
    piezo_gain = 0
    # piezo_gain= float(line.split()[-1])MostNegZvoltage
    # Didnt find a match for "Dec Factor (approach)"
    # Didnt find a match for "Dec Factor (Retract)"

    # Have not figured out yet where the ARDF files store the dwell information
    dwell = 0
    
    # Approach and retraction data
    index_start_approach = pnt_list[0]
    index_end_approach = pnt_list[1]

    # This ones are not used for now
    index_start_retract = pnt_list[1] + 1
    index_end_retract = len(channel_data_deflection)
  
    for i in channel_data_deflection:
        # force.append( i * K *invOLS*1e+12*10**-9) #force in pN
        # No need to use invOLS bc .ARDF data is already in m
        force.append(i * K * 1e12) # force in pN

    for i in channel_data_piezo:
        # Asylum Research distance comes in m
        # -1 is to change the sign of distance, Asylum Researche (.ARDF files) use a different sign convention
        distance.append(i* 1e9) #distance is in nm
    # print(index_start_approach,  index_end_approach, index_start_retract, index_end_retract)


    return distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, dwell


def ComputeExtension(force, distance, K):
    """

    Parameters
    ----------
    force : list
        force in pN.
    distance : list
        in nm.
    K : float
        N/m is converted in the code to pN/nm.

    Returns
    -------
    extension: list
        the extension is nm, mentionned as Tip Separation Surface in the GUI.

    """
    
    # geometric correction for the real tip-sample separation
    inter_dist=[]
    extension=[]
    for i in force:
        inter_dist.append(i/(K*1e12))
        
    extension= np.subtract(distance, inter_dist)
    # check this with Ismahene, I need to subtract
    # extension= extension + max(extension)
    # extension= extension + max(extension) # this is what works for my ARDF

    return extension #in nm



def DeflectionInNanometer(channel_data_deflection):
    """
    This function takes the deflection in m and 
    retunns the deflection in nanometer

    Parameters
    ----------
    channel_data_deflection : np array
        The deflection in m
        

    Returns
    -------
    deflection: np array
        deflection in nm

    """
    deflection= channel_data_deflection *1e9
    return deflection


def FDmodifParms(channel_data_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity):
    """
    When one of the parameters is modified on the GUI, 
    this function  is called to calculate the
    new values of force and distance

    Parameters
    ----------
    channel_data_deflection : TYPE
        DESCRIPTION.
    channel_data_piezo : TYPE
        DESCRIPTION.
    K : TYPE
        DESCRIPTION.
    invOLS : TYPE
        DESCRIPTION.
    piezo_gain : TYPE
        DESCRIPTION.
    sensitivity : TYPE
        DESCRIPTION.

    Returns
    -------
    distance : TYPE
        DESCRIPTION.
    force : TYPE
        DESCRIPTION.

    """
    force= []
    distance= []


    for i in channel_data_deflection:
        force.append( float(i) * float(K) * 1e12) #force in pN

    for i in channel_data_piezo:
        distance.append(float(i)* 1e9) # distance here os in nanometer
       

    return distance, force
    