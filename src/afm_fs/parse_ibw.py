#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 5 2025

@author: Carlota
"""

import sys, os, fnmatch, glob
from afmformats.formats.fmt_igor import load_igor
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def grab_ibw(directory):
        """
        This function gets all the ibw files of the directory and sorts them by time then returns the first file of
        the directory (the oldest one)
        Parameters
        ----------
        directory : str
            The directory selected by the user within the GUI
        Returns
        -------
        first_file: str
            The oldest file of the directory
        """
        files = os.listdir(directory)

        ibw_files = [i for i in files if i.endswith('.ibw')]
        return ibw_files


# grab_ibw("/home/clotis/MyUnixWorkplace/exchange_work/format_UFF/new_afm_fs/afm_fs/test")


def parse_ibw(path):
    """
    Parameters
    ----------
    path : str
        ibw file.
    Returns
    -------
    force: array
        force in pN.
    time: array
        time in ms .
    height_measured : array
        distance in nm
    height_piezo : array
        extension in nm
    parameters : array
        array of params such as spring constant ...etc.
    index_start_approach : int
        index of where the approach starts
    index_end_approach : int
        index of where the approach ends
    index_start_retract : int
        index of where the retract starts
    index_end_retract : int
        index of where the retract ends
    """
    # path=directory+'/'+ file
    dslist = load_igor(path)
    # print(dslist[0]['data'].keys())
    parameters = dslist[0]['metadata']
    # print(parameters)
    data = dslist[0]['data']

    #with open("distance.txt", "w") as f:
    #    for idx, value in enumerate(data['height (measured)']):
    #        print(f"{idx}\t{value}", file=f)
    # I could not find information about where approach and retract start and end when parsin
    # ibw, the information must be somewhere because when you open them in Igor Pro it separates both
    # maybe for future improvements
    # the approach here was validates with the indexes Igor Pro software uses when loading the data
    # trigtime is the point where the distance is min
    index_start_retract = np.argmin(data['height (measured)'])
    index_end_retract = len(data['height (measured)']) -1
    index_start_approach = 0
    index_end_approach = index_start_retract -1

    
    force = data['force'] * 10 ** 12  # newton to pn
    height_measured = data['height (measured)'] * 1e9  # Convert from m to nm #distance
    height_piezo = data['height (piezo)'] * 1e9  # Convert from m to nm #exte
    # force in pN and time in ms
    
    # Generate time channel from .ARDF metadata
    # How much the sampling rate was reduced compared to maximum
    # 1 - you kept all points
    # 2 - only every 2nd point kept
    # the force decimation should be taken from the metadata as I have been doing for ARDF
    # the function from afmformats is not extracting the force_decimation
    # could be a improvement for the future
    force_decimation = 1
    n_pts_per_sec = float(parameters['rate approach'])
    real_sampling_rate = n_pts_per_sec / force_decimation  # in Hz
    sampling_interval = 1 / real_sampling_rate
    time = np.arange(len(force)) * sampling_interval * 1000 # seconds to ms
    #print(index_start_approach,  index_end_approach, index_start_retract, index_end_retract)

    inter_dist=[]
    extension=[]
    for i in force:
        inter_dist.append(i/(parameters['spring constant']*1e12))
        
    extension= np.subtract(height_measured, inter_dist)

    
    return -force, time , height_measured, extension, parameters, index_start_approach, \
        index_end_approach, index_start_retract, index_end_retract


# a = parse_ibw("/home/clotis/MyUnixWorkplace/exchange_work/format_UFF/new_afm_fs/afm_fs/test/Image0010.ibw")

