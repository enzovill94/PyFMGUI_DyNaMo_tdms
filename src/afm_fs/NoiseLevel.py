#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 25 15:55:34 2021

@author: Ismahene
"""

import numpy as np

def get_RMS(force_retract, percentage):
    """
    This function calculates the noise level from the retract curve
    The percentage is set by the user within the GUI

    Parameters
    ----------
    force_retract : array
        the force data of the retract curve.
    percentage : int
        the percentage that will be token to calculate the RMS.

    Returns
    -------
    rms : int
        The noise level in Newton.

    """
    if percentage== 100:
        rms = int(np.sqrt(np.mean(np.array(force_retract)**2)))
    else:
        #get the index of the end according to the % the user set
        index_end= int(len(force_retract)*( percentage /100))
        #print(index_end)
        # get the needed portion from the approach curve
        force = force_retract[index_end:]
        
        # calculate RMS
        rms = int(np.sqrt(np.mean(np.array(force)**2)))
    return  rms

# import parse_tdms_new as tdms


# #file, all_tdms= tdms.grab_tdms("/Users/macbookair/AFM_FS/18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1")
# #print(file)
# file= "/Users/macbookair/AFM_FS/example_Ismahene/F_Curve_Basic_S4_100.00_50.tdms"
# parameter_file= "/Users/macbookair/AFM_FS/example_Ismahene/"

# channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms(file)

# distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract= tdms.GetForceDistAndParms(parameter_file, channel_data_deflection, channel_data_piezo)

# import matplotlib.pylab as plt
# import numpy as np

# #plt.plot(channel_data_piezo, channel_data_deflection)

# percentage=50
# distance_retract= distance[index_start_retract: index_end_retract]
# force_retract= force[index_start_retract: index_end_retract]


# rms= get_RMS(force_retract, 99)
# print(rms)

# # corrected_deflection= tdms.CorrectVirtualDeflection( channel_data_deflection, distance,  99, index_start_approach, index_end_approach, index_start_retract, index_end_retract, 90)
# # distance, force = tdms.FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)


# # slope, intercept= np.polyfit(np.array(distance[200:10000]) , np.array(force[200:10000]), 1)
# # print(slope)

# # plt.plot(distance, force)
# # plt.plot(distance[200:10000],  slope*np.array(distance[200:10000])+intercept)



# # # #distance= distance + max(distance)

# # # from scipy.signal import find_peaks
# # # peaks, _= find_peaks(force_retract)
# # # peaks= peaks[804]

# # # #rms= get_RMS(force_retract[2194:2294], 100)
# # # #print(rms)
# # # plt.plot(distance, force)
# # # plt.plot(distance[peaks], force[peaks], 'or')

# # # def f(force_retract):
# # #     return force_retract


# # # xmin = force_retract[0]
# # # xmax =peaks
# # # #plt.plot(distance[index_start_retract: index_end_retract][2292], force[2292], 'or')
# # # #plt.plot(distance[index_start_retract: index_end_retract][0:2292], force[0:2292])
# # # #plt.plot(distance[index_start_retract: index_end_retract][2292:], force[2292:])

# # # res, err = quad(f, xmin, xmax) 
# # # print(res)


