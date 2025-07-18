#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 11 13:56:01 2021

@author: Ismahene
"""

from nptdms import TdmsFile 
import numpy as np
import matplotlib.pyplot as plt
import os
import scipy.signal
from scipy.optimize import curve_fit  # For curve fitting
import pandas as pd
import statistics
from math import *
from pyfmreader import loadfile


def grab_tdms(directory):
    """
    This function gets all the tdms files of the directory
    and sorts them by time then returns the first file of
    the directory (the oldest file)

    Parameters
    ----------
    directory : str
        The directory selected by the user within the GUI

    Returns
    -------
    first_file: str
        The oldest file of the directory

    """
    all_tdms=[]
    #get all the files of the directory and sort them by time
    files=sorted(os.scandir(directory), key=lambda d: d.stat().st_mtime)
    # loop over the files
    for entry in files: 
        #take only files that have tdms extension
        if  (entry.is_file() and entry.name.endswith('.tdms')):
            #append these files on a list
            all_tdms.append(entry.path)
    # select the first file 
    first_file= all_tdms[0]
    # return the first file and all the list to facilitate the navigation
    return first_file, all_tdms


def parse_tdms(myfile, Group = 'Force Curve', deflectionChannel = 'Deflection', zpiezo = 'Piezo'):
    """
    This function opens tdms file and extracts info

    Parameters
    ----------
    myfile : str
        the tdms file.

    Returns
    -------
    channel_data_deflection : numpy array

    channel_data_piezo : numpy array

    """
    with TdmsFile.open(myfile) as tdms_file:
        
        channel_piezo= tdms_file[Group][zpiezo]
        channel_data_piezo= channel_piezo[:]
        channel_deflection= tdms_file[Group][deflectionChannel]
        channel_data_deflection= channel_deflection[:]

        time = channel_deflection.time_track()*1000 #miliseconds

    #using 'with open' closes the file automatically at the end of the operation
    return channel_data_deflection, channel_data_piezo, time


def DeflectionInNanometer( channel_data_deflection, invOLS):
    """
    This function takes the deflection in Volts and 
    retunns the deflection in nanometer

    Parameters
    ----------
    channel_data_deflection : np array
        The deflection in volts.
    invOLS : int
        

    Returns
    -------
    deflection: np array
        deflection in nanometer

    """
    deflection= channel_data_deflection *invOLS
    return deflection 

def GetForceDistAndParms_psnex(tdms_filepath):
    """
    Extracts force-distance data and relevant parameters from a TDMS file containing PSNEX HS AFM force spectroscopy curves.

    This function loads a TDMS file, processes the force curve data, and extracts the distance, force, and key calibration parameters.
    It also segments the force curve into approach, contact, and retract regions, returning indices and timing information for each segment.

    tdms_filepath : str
        Path to the TDMS file containing the AFM force curve data.

    distance_nm : np.ndarray
        The piezo position (distance) in nanometers for the entire force curve.
    force_pN : np.ndarray
        The cantilever deflection (force) in picoNewtons for the entire force curve.
        Spring constant of the cantilever in N/m.
        Inverse optical lever sensitivity in nm/V.
    deflection_sensitivity : float
        Deflection sensitivity in m/V.
    piezo_gain : float
        Piezo gain (currently set to 1, not implemented).
    index_end_approach : int
        Index of the last point in the approach segment.
    index_start_approach : int
        Index of the first point in the approach segment.
    index_start_retract : int
        Index of the first point in the retract segment.
    index_end_retract : int
        Index of the last point in the retract segment.
    contact_pts : int
        Number of points in the contact segment.
    time : np.ndarray
        Time array corresponding to the force curve data points.

    Notes
    -----
    - The function assumes the TDMS file contains metadata fields such as 'defl_sens_nmbyV', 'spring_const_Nbym', 'height_channel_key', 
      'invOLS_(nm/V)', 'start_indices', 'end_indices', 'numPnts', and 'relative_sr'.
    - Only the first force curve (index 0) is processed.
    - The function prints segment information for debugging purposes.

    """
    # directory = '/Users/evillz/Data/article/2025_07_01_THP1_phd/cell2/600'
    # first_file, all_files = tdms.grab_tdms(directory)


    # Load File
    file = loadfile(tdms_filepath)
    filemetadata = file.filemetadata
    print(filemetadata['file_type'])

    # metadata
    file_deflection_sensitivity = filemetadata['defl_sens_nmbyV'] #nm/V
    K = filemetadata['spring_const_Nbym'] #N/m
    height_channel = filemetadata['height_channel_key']

    deflection_sensitivity = file_deflection_sensitivity / 1e9 #m/V
    invOLS = filemetadata['invOLS_(nm/V)']

    # print(f"Closed loop: {closed_loop}")
    print(f"Height channel: {height_channel}")
    print(f"Deflection Sens.: {deflection_sensitivity} m/V")
    print(f"Spring Constant: {K} N/m")

    # Select curve by index
    curve_idx = 0
    force_curve = file.getcurve(curve_idx, bool_correct_overshoot=False, z_sensor_delay=1e-3)

    start_indices = filemetadata['start_indices']
    end_indices = filemetadata['end_indices']
    nm_pnts = filemetadata['numPnts']

    # Preprocess curve
    force_curve.preprocess_force_curve(deflection_sensitivity, height_channel)

    # To get each segment
    fc_segments = force_curve.get_segments()
    n_segments = len(fc_segments)
    segment_types = [segment.segment_type for _, segment in fc_segments]
    print("Segment types:", segment_types)


    for segid, segment in fc_segments:
        seg_type = segment.segment_type.lower()
        if seg_type == 'app':
            # You can add specific processing for approach here
            index_end_approach = end_indices[segid]
            index_start_approach = start_indices[segid]
            print(f"Segment {segid}: Approach, {index_start_approach}:{index_end_approach}")
        elif seg_type == 'con':
            # You can add specific processing for contact here
            contact_pts  = nm_pnts[segid]
            print(f"Segment {segid}: Contact, #pnts: {contact_pts}")
        elif seg_type == 'ret':
            # You can add specific processing for retract here
            index_end_retract = end_indices[segid]
            index_start_retract = start_indices[segid]
            print(f"Segment {segid}: Retract, {index_start_retract}:{index_end_retract}")
        else:
            print(f"Segment {segid}: Unknown type '{segment.segment_type}'")

    zheight_list = []
    vdeflection_list = []
    time_list = []

    relative_dt = filemetadata['relative_sr']

    for dt, nm_pnt in zip(relative_dt, nm_pnts):
        print(dt, nm_pnt)
        # Create a time array for each segment based on dt and number of points
        time_segment = np.arange(nm_pnt) * dt
        time_list.append(time_segment)


    for segid, segment in fc_segments:
        zheight_list.append(segment.zheight)
        vdeflection_list.append(segment.vdeflection)

    distance_nm = np.concatenate(zheight_list)
    force_pN = np.concatenate(vdeflection_list)
    piezo_gain = 1 # not implemented, Forced to 1
    time = np.concatenate(time_list)

    # plt.plot(distance_nm, force_pN)
    return -distance_nm, -force_pN, K, invOLS, deflection_sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, int(contact_pts),time

def GetForceDistAndParms(directory, channel_data_deflection, channel_data_piezo, time):

    """
    This function converts deflection & piezo mouvement
    and extract the information from the parameter file

    Parameters
    ----------
    directory : str
        the current directory containing the parameter file
    channel_data_deflection : np array
        a matrix containing the deflection data in volts.
    channel_data_piezo : np array
        a matrix containing the pizeo mouvement in volts.

    Returns
    -------
    distance : list
        the distance in nanometer (indentation/separation ).
    force : list
        the force in pN.
    K : float
        K represents the spring constant.
    invOLS : float
        (nm/V)
    Sensitivity: float
        in (nm/V).

    """

    for root, dirs, files in os.walk(os.path.abspath(directory)):
        #print("root", root)
        #print("directory", dirs)
        #print("files", files)
        for file in files:
            if file.endswith(".dat"):
                parms_file= os.path.join(os.path.abspath(root), file)
        break

    file = open(parms_file, "r")

    force= []
    distance= []
    approach=[]
    retract=[]
    S1S2=[]
    S4S5=[]

    #print(file.readline())

    lines= file.readlines()
    #print(lines)
    for line in lines:
      #  print(line)
        if "Sensitivity" in line:
            sensitivity= float(line.split()[-1])
        if "invOLS" in line:
            invOLS= float(line.split()[-1]) #unit: nm/V
        if "K" in line:
            K= float(line.split()[-1]) #unit N/m
          #  print(K)
        if "Piezo Gain" in line:
            piezo_gain= float(line.split()[-1])
        if "Dec Factor (approach)" in line:
            real_sample_rate_approach= float(line.split()[-1])
        
        if "Dec Factor (Retract)" in line:
            real_sample_rate_retract= float(line.split()[-1])
                     
            
        if line.startswith("S1"):
            S1S2.append(float(line.split()[-1]))
        if line.startswith("S2"):
            S1S2.append(float(line.split()[-1]))
            
        if line.startswith("S4"):
            S4S5.append(float(line.split()[-1]))
        if line.startswith("S5"):
            S4S5.append(float(line.split()[-1]))      
        
        if "Approach_S1S2" in line:
            approach_S1S2= float(line.split()[-1])
        if "Retract_S4S5" in line:
            retract_S4S5= float(line.split()[-1])
            
        if line.startswith("Contact_S3"):
            dwell= float(line.split()[-1])

    file.close()

    for i in S1S2:
        approach.append(i*real_sample_rate_retract)
    coef= approach_S1S2/ sum(approach)   #ramener le resultat retract à Approach_S1S2 en multipliant par coeff
    approach[:] = [x * coef for x in approach]

  #  print("retract", retract)
    time_retract =[]

    for i in S4S5:
        retract.append(i*real_sample_rate_approach)



    coef= retract_S4S5/ sum(retract)
    retract[:] = [x * coef for x in retract]
    approach= sorted(approach)
    index_start_approach= int(approach[0])
   # index_end_approach= int(approach[1])
    index_end_approach=  int(approach_S1S2)
   # index_end_approach= int(retract[0])
   # print("approach S1S2", approach_S1S2)
    
    
    retract= sorted(retract)
   # index_start_retract= int(approach[1])
    index_start_retract= int(approach_S1S2)
   # index_start_retract= int(retract[0])
   # index_end_retract= int(retract[1])
    index_end_retract= len(channel_data_deflection)
    
    # print('S1S2', S1S2)
    # print('S4S5', S4S5)
    # print('retract S4S5', retract_S4S5)
    # print('approach S1S2', approach_S1S2)
    # print('start approach', index_start_approach)
    # print('end approach', index_end_approach)
    # print('start retract', index_start_retract)
    # print('end retract', index_end_retract)
    
    for i in channel_data_deflection:
        force.append( i * K *invOLS*1e+12*10**-9) #force in pN

    for i in channel_data_piezo:
        distance.append(i* sensitivity*piezo_gain ) #distance is in nm

    
    time[index_start_approach : index_end_approach]= np.flip(time[index_start_approach : index_end_approach]*real_sample_rate_approach )
    time[index_start_approach : index_end_approach]= time[index_start_approach : index_end_approach]- max(time[index_start_approach : index_end_approach])
   # print(abs(time[index_start_retract : index_end_retract][-1]))
        
    time[index_start_retract : index_end_retract]= time[index_start_retract : index_end_retract]*real_sample_rate_retract 




    return distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, dwell,time

# Calculate the value :
def calc_sine(x,a,b,c,d):
    #perms of sinus: amplitude, period, phase shif, vertical shift (a,b,c,d)
    #return a * np.sin(b* ( x + np.radians(c))) + d
    return a+b*np.sin(2*pi*x/c+d)

def CorrectVirtualDeflection( deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage,  **kwargs):
    """
    Corrects virtual deflection from the approach curve only
    the percentage is taken from the end of the approach curve

    Parameters
    ----------
    deflection_approach : numpy array
        contains the deflection data of the approach curve.
    distance : list
        contains all distance values .
    percentage : 
        DESCRIPTION.

    Returns
    -------
    corrected_deflection_approach : TYPE
        DESCRIPTION.

    """
    
    #https://towardsdatascience.com/polynomial-regression-bbe8b9d97491

    dist_approach= distance[index_start_approach:index_end_approach]

    index_end= int(len(dist_approach)*(percentage/100))

    hysteresis = kwargs.get('hysteresis', 0)

    deflection_approach= deflection[index_start_approach: index_end_approach]


    
    if Npoly ==99:
        stdyp=statistics.stdev(deflection)
        distance[index_start_retract: index_end_retract]= np.array(distance[index_start_retract: index_end_retract]) - hysteresis

        popt, pcov = curve_fit(calc_sine, np.asarray(distance[index_start_approach: index_end_approach][: index_end]),
                      deflection_approach[: index_end],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        corrected_deflection=  deflection - calc_sine(np.asarray(distance),*popt)
        #print(popt)
        
        #Coefficient
    else:
       # p= P.fit(dist_approach[:index_end], deflection_approach[:index_end], Npoly)
        z = np.polyfit(dist_approach[:index_end], deflection_approach[:index_end], Npoly)
        p = np.poly1d(z)    #equation
    #print('equation ', p)
        distance[index_start_retract: index_end_retract]= np.array(distance[index_start_retract: index_end_retract]) - hysteresis
        corrected_deflection= deflection - p(distance)

    
    return  corrected_deflection #corrected_deflection_approach, corrected_deflection_retract



def CorrectDeflectionFromRetract(deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage_retract, percentage_approach):
    """
    

    Parameters
    ----------
    deflection : array
        the deflection of the laser.
    distance : array
        the distance in nm.
    Npoly : int
        the order of the polynomial fitting.
    index_start_approach : int
        index of where the approach curve starts
    index_end_approach : int
        index of where the retract curve ends
    index_start_retract : int
        index of where the retract curve starts.
    index_end_retract : int
        index of where the retract curve ends
    percentage_retract : int
        percentage of retract curve to fit (from the end)
    percentage_approach : int
        percentage of approach curve to fit (from the end)

    Returns
    -------
    corrected deflection: array
        the corrected deflection after fitting

    """
    
    dist_approach= distance[index_start_approach:index_end_approach]
    deflection_approach= deflection[index_start_approach : index_end_approach]
    deflection_retract= deflection[index_start_retract : index_end_retract]
   
    index_end_a= int(len(dist_approach)*(percentage_approach/100))

    dist_retract= distance[index_start_retract:index_end_retract]

    index_end_r= len(deflection_retract) -  int(len(dist_retract)*(percentage_retract/100))


    if Npoly== 99:
    #optimal parameters
        meanyp= statistics.mean(deflection)
        stdyp=statistics.stdev(deflection)
        popt_approach, pcov_approach = curve_fit(calc_sine, distance[index_start_approach: index_end_approach][: index_end_a], 
                      deflection[index_start_approach: index_end_approach][: index_end_a],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        

        popt_retract, pcov_retract= curve_fit(calc_sine, distance[index_start_retract: index_end_retract][: index_end_r], 
                      deflection[index_start_retract: index_end_retract][: index_end_r],
                      bounds= ([min(deflection), 0, 200, -pi*2],
                               [max(deflection), 10*stdyp, 350, pi*2]))
        
        
        corrected_deflection= np.zeros(len(deflection))
        for i in range(len(deflection[index_start_retract: index_end_retract])):
            corrected_deflection[index_start_retract: index_end_retract][i]=  deflection_retract[i] - calc_sine(np.asarray(distance[index_start_retract: index_end_retract][i]),*popt_retract)
        
        for i in range(len(deflection[index_start_approach: index_end_approach])):
            corrected_deflection[index_start_approach: index_end_approach][i]=  deflection_approach[i] - calc_sine(np.asarray(distance[index_start_approach: index_end_approach][i]),*popt_approach)

        
    else:

        #Coefficient
        za = np.polyfit(dist_approach[:index_end_a], deflection_approach[:index_end_a], Npoly)
   #     print('coeff of polynomial', za) 
        pa = np.poly1d(za)    #equation
   #     print('equation ', pa)

        # Check if size of deflection and distance are the same and account for it
        pnt_rem = abs(len(distance)-len(dist_retract))

        pnt_remove = len(distance)-len(deflection)
        if pnt_remove < 0 :
            deflection = deflection[:pnt_remove]  
        else :
            distance = distance[pnt_rem:]

        print(f'len_distance: {len(distance)}, len_deflection: {len(deflection)}')
       
        if pnt_rem != 0:
            if len(deflection_retract) > len(dist_retract):
                deflection_retract_polyfit = deflection_retract[index_end_r:-pnt_rem]
                distance_retract_polyfit = dist_retract[index_end_r:]
            else:
                deflection_retract_polyfit = deflection_retract[index_end_r:]
                distance_retract_polyfit = dist_retract[index_end_r:]

        print(f'length_Deflection_retract: {len(deflection_retract_polyfit)} length_distance_retract: {len(distance_retract_polyfit)}')
            

       # corrected_deflection_approach= deflection_approach - pa(dist_approach)
        z = np.polyfit(distance_retract_polyfit, deflection_retract_polyfit, Npoly)
        p = np.poly1d(z)    #equation
        
        corrected_deflection= np.zeros(len(deflection))
        for i in range(len(deflection[index_start_retract: index_end_retract - pnt_rem])):
            # print(f'break{i}')
            corrected_deflection[index_start_retract: index_end_retract][i]= deflection_retract[i]- p(distance[index_start_retract: index_end_retract][i] - pnt_rem)
        
        for i in range(len(deflection[index_start_approach: index_end_approach])):
            corrected_deflection[index_start_approach: index_end_approach][i]= deflection_approach[i] - pa(dist_approach[i])

        #corrected_deflection_retract= deflection_retract- p(distance[index_start_retract: index_end_retract])

   # return corrected_deflection_approach, corrected_deflection_retract
    return corrected_deflection

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
    
    inter_dist=[]
    extension=[]
    for i in force:
        inter_dist.append(i/(K*10**3))
        
    extension= np.subtract(distance, inter_dist)
    #extension= extension + max(extension)
    
    return extension #in nm


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
        force.append( float(i) * float(K) *float(invOLS)*1e+12*10**-9) #force in pN

    for i in channel_data_piezo:
        distance.append(float(i)* float(sensitivity)* float(piezo_gain)) # distance here os in nanometer
       

    return distance, force

def props(cls):
    """
    Get all the properties of a given class

    Parameters
    ----------
    cls : TYPE
        DESCRIPTION.

    Returns
    -------
    list
        DESCRIPTION.

    """
    
    return [i for i in cls.__dict__.keys() if i[:1] != '_']


def ApplySavgol(data, window):
    """
    

    Parameters
    ----------
    data : np array
        the matrix containing data.
    window : int
        the window length, this number has to be greater than 3 (the order) and impair  .

    Returns
    -------
    smoothed : np array
        a matrix containing the smoothed data.

    """
    smoothed= scipy.signal.savgol_filter(data, window, 1) # window size 51, polynomial order 3
    return smoothed




def downsampling(data, pts):
    
    """
    Parameters
    ----------
    data : array
        array of data.

    Returns
    -------
    Panda data frame of downsampled data
        

    """
    data=np.array(data)
    l=len(data) #length of data
    new_sample=[]
    for i in range(0, l , pts):
        new_sample.append(data[i:i+pts])
    new_sample=pd.DataFrame(new_sample)
    return new_sample[0]

# file="example_Ismahene/F_Curve_Basic_S4_100.00_50.tdms"
# channel_data_deflection, channel_data_piezo, time= parse_tdms(file)
# distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract, dzell, timeA, timeR=GetForceDistAndParms("example_Ismahene/", channel_data_deflection, channel_data_piezo,time)
# extension= ComputeExtension(force, distance, K)
# extension= extension+max(extension)
# Npoly= 99
# percentage=90
# ##APART
# #corrected_deflection= CorrectVirtualDeflection( np.flipud(channel_data_deflection), np.flipud(distance),  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage, hysteresis=35)
#
# #corrected_deflection= np.flipud(corrected_deflection)
# ##########
# corrected_deflection= CorrectVirtualDeflection( channel_data_deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage, hysteresis=35)
#
# distance, force=FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)
# plt.plot(extension[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract], label='hysteresis applied')
# plt.plot(extension[index_start_approach: index_end_approach], force[index_start_approach: index_end_approach], label='hysteresis applied')

# plt.legend()
#Npoly= 99
#percentage=90
#corrected_deflection= CorrectVirtualDeflection( channel_data_deflection, distance,  Npoly, index_start_approach, index_end_approach, index_start_retract, index_end_retract, percentage)
#distance, force=FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)

#plt.plot(extension[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract])
#plt.plot(extension[index_start_approach: index_end_approach], force[index_start_approach: index_end_approach])

# axs[1].grid()
# distance, force=FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)
# axs[1].plot(extension[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract])
# axs[1].plot(extension[index_start_approach: index_end_approach], force[index_start_approach: index_end_approach])
# #axs[1].set_title('without hysteresis')

#plt.savefig('corrected_deflection_hysteresis.pdf')
#plt.plot(extension, channel_data_deflection)
# #plt.plot(time, channel_data_deflection)