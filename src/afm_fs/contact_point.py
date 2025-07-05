#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 11 13:56:01 2021

@author: Ismahene
"""

import numpy as np
import tkinter.messagebox

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
    prev_idx = None
    indices = []
    # This way we can get the index of the point just before the zero crossing
    for i, (t1, c1, c2) in enumerate(zip(x, deflection, zero_axis)):
    #for t1, c1, c2 in zip(x, deflection, zero_axis):
        new_dif = c2 - c1
        if np.abs(new_dif) < 1e-12: # found an exact zero, this is very unprobable
            intersections.append((t1, c1))
            indices.append(i)
        elif new_dif * prev_dif < 0:  # the function changed signs between this point and the previous
        # do a linear interpolation to find the t between t0 and t1 where the curves would be equal
        # this is the intersection between the line [(t0, prev_c1), (t1, c1)] and the line [(t0, prev_c2), (t1, c2)]
        # because of the sign change, we know that there is an intersection between t0 and t1
            denom = prev_dif - new_dif
            intersections.append(((-new_dif*t0  + prev_dif*t1) / denom, (c1*prev_c2 - c2*prev_c1) / denom))
            indices.append(prev_idx)
        t0, prev_c1, prev_c2, prev_dif = t1, c1, c2, new_dif
        prev_idx = i

    if len(intersections)== 0:
        tkinter.messagebox.showinfo('warning' ,'No intersection point found')
    elif len(intersections) != 0:
        return intersections[0], indices[0]





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
    corrected_data = data - intersection
    return corrected_data 

# import matplotlib.pyplot
#from parse_tdms_new import *
#channel_data_deflection, channel_data_piezo, time= parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_55.tdms")
#channel_data_deflection, channel_data_piezo, time= parse_tdms("/Users/macbookair/AFM_FS/examp_fidan/F_Curve_Basic_S4_100.00_2.tdms")

#distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = GetForceDistAndParms("/Users/macbookair/AFM_FS/examp_fidan/", channel_data_deflection, channel_data_piezo)
#distance= distance+ max(distance)

# plt.close()


# distance= distance+ max(distance)
#plt.plot(distance[index_start_retract: index_end_retract],force[index_start_retract: index_end_retract])

#extension= ComputeExtension(force, distance, K)

#plt.plot(extension, force)
# print(len(distance[index_start_approach: index_end_approach]))
# index_end= int(len(distance[index_start_approach: index_end_approach])*(80/100))
# print(index_end)

# plt.plot(distance[index_start_approach: index_end_approach][0:50],force[index_start_approach: index_end_approach][0:50])


# #plt.plot(distance[index_start_approach: index_end_approach])
# plt.plot(distance[index_start_approach: index_end_approach],force[index_start_approach: index_end_approach])


# intersection= FindContactPoint(distance[index_start_approach: index_end_approach][::-1]
#                                             , force[index_start_approach: index_end_approach][::-1])

# #plt.plot(distance,force)
# #plt.plot(distance[index_start_approach: index_end_approach],force[index_start_approach: index_end_approach])

# plt.plot(*intersection, 'ro', alpha=0.7, ms=10)
# print(intersection)
# plt.plot(distance[index_start_approach: index_end_approach]- intersection[0],force[index_start_approach: index_end_approach])


        