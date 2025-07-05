#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 23 15:59:23 2021

@author: Ismahene
"""
import numpy as np

def get_keff_veff_vBwd_exp(extension, f, deflection, time, peaks,z, distance):
    """
    calculates slopes of force vs extension ==> keff
    and deflection vs time ==> veff
    the user gives parameters according of the parameter he wants to calculate 
    Parameters
    ----------
    extension : list
        contains the extension (TSS) in nanometer.
    f : array
        force in pN.
    peaks : list
        list of peaks ( the indexes of peaks).
    distance : float
        distance before the peak in nanometer set in the entry of the interface by the user.

    Returns
    -------
    d : dict
        dictionnary of information.
    slope : list
        list containing the loading rates the slopes.
    intercept : list
        list containing the intercepts of the slopes.

    """
   # extension=np.array(extension)
   # f= f[index_start_retract: index_end_retract]
    d={'f':[], 'ts':[], 'dis1':[], 'disTMP':[], 'dis2':[], 'index_dis2':[], 'peaks':[]}
    #iterate over all peaks
    time=time *10**-3
    for i in peaks:
        d['f'].append(f[i])
       # d['ts'].append(time[i])
        #compute displacement using corresponding peak index
        d['dis1'].append(extension[i])
    #compute selected value = displacement[peak_index]-distance given by the user in nm
    for i in range(len(peaks)):
        d['disTMP'].append(d['dis1'][i]-distance)
        
       # print(d['disTMP'])

    #search for closest value to selected one (selected one is distance before peak)
    for i in range(len(peaks)):
        d['dis2'].append(extension.flat[np.abs(extension - d['disTMP'][i]).argmin()])
       # print(d['dis2'])
    
    #put found values in dictionnary of info
    for i in range(len(peaks)):
        d['index_dis2'].append(int(list(extension).index(d['dis2'][i])))
        
    for i in peaks:
        d['peaks'].append(int(i))

    keff=[]
    veff= []
    intercept_keff=[]
    intercept_veff=[]
    vBwd_exp= []
    vBwd_exp_intercept= []

    #slopes and intercept computing
    for i in range(len(peaks)):

        keff.append(np.polyfit(np.array(extension[d['index_dis2'][i]:d['peaks'][i]]) , np.array(f[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        intercept_keff.append(np.polyfit(np.array(extension[d['index_dis2'][i]:d['peaks'][i]]),f[d['index_dis2'][i]:d['peaks'][i]], 1)[1])
        
        veff.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]) , np.array(deflection[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        intercept_veff.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]),deflection[d['index_dis2'][i]:d['peaks'][i]], 1)[1])

        vBwd_exp.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]) , np.array(z[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        vBwd_exp_intercept.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]),z[d['index_dis2'][i]:d['peaks'][i]], 1)[1])


    return keff, veff, intercept_keff , intercept_veff, vBwd_exp, vBwd_exp_intercept, d

# Function definition.
def f(force):
    return force

# Integration calculation.
def integration(a, b, n):
    dx = (b - a) / n
    integration = 0
    for i in np.arange(1, n + 1):
        integration += f(a + i * dx)
    integration *= dx
    return "{:.2e}".format(integration)



def get_keff_veff_vBwd_exp_jpk(extension, f,  time, peaks,z, distance):
    """
    calculates slopes of force vs extension ==> keff
    and deflection vs time ==> veff
    the user gives parameters according of the parameter he wants to calculate 
    Parameters
    ----------
    extension : list
        contains the extension (TSS) in nanometer.
    f : array
        force in pN.
    peaks : list
        list of peaks ( the indexes of peaks).
    distance : float
        distance before the peak in nanometer set in the entry of the interface by the user.

    Returns
    -------
    d : dict
        dictionnary of information.
    slope : list
        list containing the loading rates the slopes.
    intercept : list
        list containing the intercepts of the slopes.

    """
   # extension=np.array(extension)
   # f= f[index_start_retract: index_end_retract]
    d={'f':[], 'ts':[], 'dis1':[], 'disTMP':[], 'dis2':[], 'index_dis2':[], 'peaks':[]}
    #iterate over all peaks
    time=time *10**-3
    for i in peaks:
        d['f'].append(f[i])
       # d['ts'].append(time[i])
        #compute displacement using corresponding peak index
        d['dis1'].append(extension[i])
    #compute selected value = displacement[peak_index]-distance given by the user in nm
    for i in range(len(peaks)):
        d['disTMP'].append(d['dis1'][i]-distance)
        
       # print(d['disTMP'])

    #search for closest value to selected one (selected one is distance before peak)
    for i in range(len(peaks)):
        d['dis2'].append(extension.flat[np.abs(extension - d['disTMP'][i]).argmin()])
       # print(d['dis2'])
    
    #put found values in dictionnary of info
    for i in range(len(peaks)):
        d['index_dis2'].append(int(list(extension).index(d['dis2'][i])))
        
    for i in peaks:
        d['peaks'].append(int(i))

    keff=[]
    # veff= []
    intercept_keff=[]
    intercept_veff=[]
    vBwd_exp= []
    vBwd_exp_intercept= []

    #slopes and intercept computing
    for i in range(len(peaks)):

        keff.append(np.polyfit(np.array(extension[d['index_dis2'][i]:d['peaks'][i]]) , np.array(f[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        intercept_keff.append(np.polyfit(np.array(extension[d['index_dis2'][i]:d['peaks'][i]]),f[d['index_dis2'][i]:d['peaks'][i]], 1)[1])
        
        # veff.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]) , np.array(deflection[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        # intercept_veff.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]),deflection[d['index_dis2'][i]:d['peaks'][i]], 1)[1])

        vBwd_exp.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]) , np.array(z[d['index_dis2'][i]:d['peaks'][i]]), 1)[0])
        vBwd_exp_intercept.append(np.polyfit(np.array(time[d['index_dis2'][i]:d['peaks'][i]]),z[d['index_dis2'][i]:d['peaks'][i]], 1)[1])


    return keff,  intercept_keff , intercept_veff, vBwd_exp, vBwd_exp_intercept, d #veff,
