#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  1 10:52:07 2021

@author: Ismahene
"""

from scipy.optimize import curve_fit
from scipy import interpolate
import numpy as np


def FJC(extension, Lc):
    kB = 1.3807e-2  # pNnm/K
    T= 298
    kBT= kB*T
    fm= 5.3
    pl=0.4
    F=np.linspace(0.001, 5000, 10000)
    Ex= (np.tanh(F*2*pl/kBT)- (kBT/F/2/pl))*(Lc+F/fm)
    
    #print(Ex)
    
    func= interpolate.interp1d(Ex, F)
    force= func(extension)
  #  tck= interpolate.splrep(Ex, F)
   # force = interpolate.splev(extension, tck)
    
    return force


# import parse_tdms_new as tdms 
# import contact_point as CP
# import matplotlib.pylab as plt
# from scipy.signal import find_peaks

# deflection, channel_data_piezo, time= tdms.parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_50.tdms") 
# plt.grid()

# distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, dwell_time = tdms.GetForceDistAndParms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1", deflection, channel_data_piezo)

# corrected_deflection= tdms.CorrectVirtualDeflection( deflection, distance,  99, index_start_approach, index_end_approach, index_start_retract, index_end_retract, 90)

# #corrected_deflection= tdms.CorrectVirtualDeflection( corrected_deflection, distance,  99, index_start_approach, index_end_approach, index_start_retract, index_end_retract, 90)

# extension= tdms.ComputeExtension(force, distance, K)
# extension= extension+ max(extension)

# #plt.plot(extension, corrected_deflection)



# distance, force= tdms.FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)



# intersection= CP.FindContactPoint(extension,  corrected_deflection)
# extension= CP.CorrectContactPoint(extension, intersection[1])


# peaks, properties= find_peaks(force[index_start_retract: index_end_retract], height=0)

# peak= [2283]


# lc=[55]
# start= 2100
# force_= FJC(extension, 45)

# plt.plot(extension, force)
# plt.ylim([min(force), max(force)+100])
# plt.plot(extension[0: len(force_)], force_)

# plt.plot(extension[peak[0]], force[peak[0]], 'or')

# for i in range(len(lc)):
#     popt, pcov = curve_fit(FJC, extension[index_start_retract: index_end_retract] , 
#                              force[index_start_retract : index_end_retract],
#                        p0=[lc[i]],
#                         method='trf')
#                        #bounds=((lc[i]), (start*10))
#                    # ) #Algorithm to perform minimization.‘trf’ : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds. Generally robust method.


# #plt.plot( extension[0: peaks[0]], FJC(extension[0: peak[0]], *popt))
                