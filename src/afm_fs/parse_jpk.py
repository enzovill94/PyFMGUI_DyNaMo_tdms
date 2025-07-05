#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 29 15:05:14 2024

@author: Ismahene Mesbah
"""

import sys, os, fnmatch, glob
from afmformats.formats.fmt_jpk import load_jpk
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def grab_jpk( directory):
        """
        This function gets all the tdms files of the directory and sorts them by time then returns the first file of
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

        jpk_files = [i for i in files if i.endswith('.jpk-force') or i.endswith('jpk')]
        return jpk_files

# directory="/media/mesbah/ADATA HD330/AFM_EXPERIMENTS_JPK/20250320_MLCTD_VCAM1D2/2ums/"
# files= grab_jpk(directory)

def parse_jpk(path):
    """
    Parameters
    ----------
    path : str
        jpk-force file.
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
    dslist = load_jpk(path)
    parameters = dslist[0]['metadata']
    # print(parameters)
    # print(parameters)
    data = dslist[0]['data']
    indexes_retract = []
    indexes_approach = []
    for idx, x in np.ndenumerate(data['segment']):
        if x == 2:
            indexes_retract.append(list(idx))
        if x == 0:
            indexes_approach.append(list(idx))
    index_start_retract = indexes_retract[0][0]
    index_end_retract = indexes_retract[-1][0]
    index_start_approach = indexes_approach[0][0]
    index_end_approach = indexes_approach[-1][0]
    force = data['force'] * 10 ** 12  # newton to pn
    time = data['time'] * 1000  # seconds to ms
    height_measured = data['height (measured)'] * 1e9  # Convert from m to nm #distance
    height_piezo = data['height (piezo)'] * 1e9  # Convert from m to nm #exte
    # print(index_start_approach,  index_end_approach, index_start_retract, index_end_retract)
    # force in pN and time in ms
    return -force, time , height_measured, height_piezo, parameters, index_start_approach, \
        index_end_approach, index_start_retract, index_end_retract



def FindContactPoint(x,  deflection):
    """
    this function finds the contact point ( the intersection of each curve with 0 axis)

    Parameters
    ----------
    x : array
        array x-axis (could be distance, extension or piezo ).
    deflection : array
        deflection data



    """
    zero_axis= np.zeros(len(deflection))
    intersections = []
    prev_dif = 0
    t0, prev_c1, prev_c2 = None, None, None
    for t1, c1, c2 in zip(x, deflection, zero_axis):
        new_dif = c2 - c1
        if np.abs(new_dif) < 1e-12: # found an exact zero, this is very unprobable
            intersections.append((t1, c1))
        elif new_dif * prev_dif < 0:  # the function changed signs between this point and the previous
        # do a linear interpolation to find the t between t0 and t1 where the curves would be equal
        # this is the intersection between the line [(t0, prev_c1), (t1, c1)] and the line [(t0, prev_c2), (t1, c2)]
        # because of the sign change, we know that there is an intersection between t0 and t1
            denom = prev_dif - new_dif
            intersections.append(((-new_dif*t0  + prev_dif*t1) / denom, (c1*prev_c2 - c2*prev_c1) / denom))
        t0, prev_c1, prev_c2, prev_dif = t1, c1, c2, new_dif

    if len(intersections)== 0:
        print('No intersection point found')
    elif len(intersections) != 0:
        return intersections[0]

def CorrectContactPoint(data, intersection):
    """
    Offset each trace in the x-direction such that the first intercept 
    with the distance axis occurs at a distance of 0 nm.

    Parameters
    ----------
    data : array
        data of the x-axis, could be extension, distance or piezo.
    intersection : float
        the x intersection coordinate.

    Returns
    -------
    corrected_data : array
        data after correction.

    """
    if intersection is None:
        intersection= 0
        corrected_data = data - intersection
    elif len(intersection)== 1:
        corrected_data = data - intersection

    
    elif len(intersection)>1:
        
        corrected_data = data - intersection[0]
        
    return corrected_data 



