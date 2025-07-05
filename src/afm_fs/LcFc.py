#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  1 15:56:10 2021

@author: Ismahene
"""


import matplotlib.pylab as plt
import numpy as np
import parse_tdms_new as tdms
import pandas as pd 
from scipy.signal import find_peaks


# #channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_50.tdms") 

# channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms("18h58m54s_Felix_AC10_SdrG_Fln4FgB__S4_3.000_Basic_19/F_Curve_Basic_S4_3.00_90.tdms") 
# distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = tdms.GetForceDistAndParms("18h58m54s_Felix_AC10_SdrG_Fln4FgB__S4_3.000_Basic_19", channel_data_deflection, channel_data_piezo)


# #distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = tdms.GetForceDistAndParms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1", channel_data_deflection, channel_data_piezo)


# Npoly= 2
# percentage= 90
# corrected_deflection= tdms.CorrectVirtualDeflection(channel_data_deflection, distance, Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage)


# distance, force = tdms.FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)
# distance= np.array(distance)+ max(distance)


# extension= tdms.ComputeExtension(force, distance, K)
# #plt.plot(extension, force)

def FindLc(extension, F):
    """
    This function transform force vs TSS to F vs Lc


    Parameters
    ----------
    extension : np array
        extension (TSS) data in nm
    F : np array
        force data in newton

    Returns
    -------
    bestLc : np array
        The selected contour length values (the criteria is detailed in the report)
    Fc : np array
        force values in newton.

    """
    pl= 0.4 #persistance length
    T= 298  #temperature
    kB = 1.3807e-2  # pNnm/K
    a1= 4   #coeff of the equation
    a3= 0
    a4= -1
    lamb= []    #the lambda value to be calculated
    # Each equation has 3 solutions (L1, L2, L3)
    bestL2= np.zeros(len(F)) 
    bestL1= np.zeros(len(F))
    bestL3= np.zeros(len(F))
    #alpha
    alpha = kB*T/pl

    for i in range(len(F)):
        a2= (4* F[i] / (kB*T/pl ))-3
        lamb.append(np.roots([a1, a2, a3,   a4]))
        #keep only real values
        if (lamb[i][0].imag==0 and lamb[i][0] >0 and lamb[i][0] <1):
            bestL1[i]= lamb[i][0].real
            
        elif (lamb[i][1].imag== 0 and lamb[i][1] >0 and lamb[i][1] <1):
            bestL2[i] = lamb[i][1].real
            
        elif (lamb[i][2].imag== 0 and lamb[i][2] >0 and lamb[i][2] <1):
            bestL3[i]= lamb[i][2].real
    #merge all so solutions in one matrix to easily sort best L 
    L= np.vstack([bestL1, bestL2, bestL3]).T
    
    L[L==0] = 100   #replace 0 by very large value otherwise it will consider O as min later


    bestL= L.min(axis=1)    #returns the minimum for each row
    #matrix of final Lc values
    bestLc= np.zeros(len(extension))
    for i in range(len(extension)):
        bestLc[i] = extension[i]/ (1- bestL[i] )
    #to avoid warning
    np.seterr(divide='ignore', invalid='ignore')
    # Calculate corresponding Force for each Lc value
    Fc= alpha * (((1 - (extension /bestLc))**-2)/4 + (extension/bestLc) - 1/4)
    # filter force < 30 pN
    bestLc[bestLc<0]= None
    Fc[Fc <30] = None
    
    return bestLc, Fc

def GetLcPeak(Fc, Lc):
   # Fc[Fc < threshold]= None

    d= { 'Fc': Fc, 'Lc': Lc}
    plt.plot(Lc, Fc, 'xb')
    df = pd.DataFrame(data=d)
    df=df.dropna()
   # print(df)
   # print(df.nlargest(number_peaks, 'Fc')) 
   # df= pd.cut(df['Lc'], 10)
   # print(df)
    column = df["Fc"]
    max_index = column.idxmax()
    Fc_max= df['Fc'].max()
    Lc_of_max= df.loc[df['Fc'] == Fc_max,'Lc']
    #print(df.iloc[(df['Fc']-Fc_max).abs().argsort()[:1]])
   # df['Fc']= df['Fc'].drop(df['Fc'].loc[Fc_max-10: Fc_max].index)
   # df.drop(df.loc[Lc_of_max-10: Lc_of_max].index)

    #print(df)
    
    #Fc= df['Fc'].to_numpy()
   # Lc= df['Lc'].to_numpy()
  #  Fc= np.delete(Fc, np.argwhere(np.ediff1d(Fc) <= Fc_max) + 1)


    return df, max_index



def return_highest_peaks(properties, peaks, N_peaks):

    list_all_heights=[]
    #print(properties.keys())
    #print(len(properties['peak_heights']))
            #get all the heights of the peaks
   # for i in range(len(properties)):
        #print(i)
    for j in range(len(properties['peak_heights'])):
        list_all_heights.append(properties['peak_heights'][j])
                #sort the heights
    list_all_heights=sorted(list_all_heights) 
                # keep only last highest peaks according tot the user's number N_peaks
    list_all_heights= list_all_heights[-N_peaks:]
    #print(list_all_heights)
                # get the original index of each peak                
    theset = frozenset(list_all_heights)
    theset = sorted(theset, reverse=True)
    thedict = {}
    n_peaks=[]
    if len(list_all_heights) < N_peaks:
        N_peaks=len(list_all_heights)

    for j in range(N_peaks):
        positions = [i for i, x in enumerate(list_all_heights) if x == theset[j]]
        thedict[theset[j]] = positions
        for i in range(len(properties)): 
            n_peaks.append(peaks[list(properties['peak_heights']).index(theset[j])])
    n_peaks = list(set(n_peaks))

    return n_peaks
    
#plt.plot(extension, force)
#plt.xlabel('TSS (nm)')
#plt.ylabel('Force (pN)')
# from scipy.signal import find_peaks, peak_widths
#Lc, Fc= FindLc(extension, force)




#plt.scatter(Lc, Fc)
#plt.scatter(Lc, Fc)
# #plt.savefig('ScatterLcFcPeakDetection.pdf')
# print(type(Fc))

# d= { 'Fc': Fc, 'Lc':Lc}
# df = pd.DataFrame(data=d)
# df = df.dropna()
# Lc=np.array(df['Lc'])
# Fc= np.array(df['Fc'])
# peaks, properties= find_peaks(Fc, width=5, height=0)
# n_peaks= return_highest_peaks(properties, peaks, 3)
# print(n_peaks)

# Lc= Lc[~np.isnan(Lc)]

# #print(properties)
# #print(peaks)
# #peaks= return_highest_peaks(properties, peaks, 1)
#for i in n_peaks:
 #   plt.plot(Lc[i], Fc[i], 'or')
#Lc2, Fc2, df= GetLcPeak(Fc, Lc)
#plt.plot(extension, force)
#plt.scatter(df['Lc'] , df['Fc'], color='red')
#plt.scatter(Lc, Fc)
# def compute_derivative(e2e, ts):

#     """"
#     parameters:
#         -  e2e (matrix) : extension from element to element in nanometer
#         - ts (matrix): time in seconds
    
    
#     returns derivative of extension (from element2element) and x-axis (time in seconds)
#     """
#     np.seterr(divide='ignore')
#     derivative = np.zeros(len(ts))
#     l=len(ts)
#     h=0.001

#     for i in range(2,l-2):

#         derivative[i]=(float(1*e2e[i-2]-8*e2e[i-1]+0*e2e[i+0]+8*e2e[i+1]-1*e2e[i+2])/float(1*12*h))
#     x = (ts[:-1] + ts[1:]) / 2
#     return x, derivative, ts #returns :x-axis of derivative (timeinseconds), the derivative, original time in seconds

# x, derivative, ts= compute_derivative(Fc, Lc)
# plt.scatter(ts, derivative)



