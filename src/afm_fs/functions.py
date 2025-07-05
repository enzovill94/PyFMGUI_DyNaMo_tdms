#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 14:57:14 2021

@author: Ismahene
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
import scipy.signal as signal


def get_natural_cubic_spline_model(x, y, minval=None, maxval=None, n_knots=None, knots=None):
    """
    Get a natural cubic spline model for the data.

    For the knots, give (a) `knots` (as an array) or (b) minval, maxval and n_knots.

    If the knots are not directly specified, the resulting knots are equally
    space within the *interior* of (max, min).  That is, the endpoints are
    *not* included as knots.

    Parameters
    ----------
    x: np.array of float
        The input data
    y: np.array of float
        The outpur data
    minval: float 
        Minimum of interval containing the knots.
    maxval: float 
        Maximum of the interval containing the knots.
    n_knots: positive integer 
        The number of knots to create.
    knots: array or list of floats 
        The knots.

    Returns
    --------
    model: a model object
        The returned model will have following method:
        - predict(x):
            x is a numpy array. This will return the predicted y-values.
    """

    if knots:
        spline = NaturalCubicSpline(knots=knots)
    else:
        spline = NaturalCubicSpline(max=maxval, min=minval, n_knots=n_knots)

    p = Pipeline([
        ('nat_cubic', spline),
        ('regression', LinearRegression(fit_intercept=True))
    ])

    p.fit(x, y)

    return p


class AbstractSpline(BaseEstimator, TransformerMixin):
    """Base class for all spline basis expansions."""

    def __init__(self, max=None, min=None, n_knots=None, n_params=None, knots=None):
        if knots is None:
            if not n_knots:
                n_knots = self._compute_n_knots(n_params)
            knots = np.linspace(min, max, num=(n_knots + 2))[1:-1]
            max, min = np.max(knots), np.min(knots)
        self.knots = np.asarray(knots)

    @property
    def n_knots(self):
        return len(self.knots)

    def fit(self, *args, **kwargs):
        return self


class NaturalCubicSpline(AbstractSpline):
    """Apply a natural cubic basis expansion to an array.
    The features created with this basis expansion can be used to fit a
    piecewise cubic function under the constraint that the fitted curve is
    linear *outside* the range of the knots..  The fitted curve is continuously
    differentiable to the second order at all of the knots.
    This transformer can be created in two ways:
      - By specifying the maximum, minimum, and number of knots.
      - By specifying the cutpoints directly.  

    If the knots are not directly specified, the resulting knots are equally
    space within the *interior* of (max, min).  That is, the endpoints are
    *not* included as knots.
    Parameters
    ----------
    min: float 
        Minimum of interval containing the knots.
    max: float 
        Maximum of the interval containing the knots.
    n_knots: positive integer 
        The number of knots to create.
    knots: array or list of floats 
        The knots.
    """

    def _compute_n_knots(self, n_params):
        return n_params

    @property
    def n_params(self):
        return self.n_knots - 1

    def transform(self, X, **transform_params):
        X_spl = self._transform_array(X)
        if isinstance(X, pd.Series):
            col_names = self._make_names(X)
            X_spl = pd.DataFrame(X_spl, columns=col_names, index=X.index)
        return X_spl

    def _make_names(self, X):
        first_name = "{}_spline_linear".format(X.name)
        rest_names = ["{}_spline_{}".format(X.name, idx)
                      for idx in range(self.n_knots - 2)]
        return [first_name] + rest_names

    def _transform_array(self, X, **transform_params):
        X = X.squeeze()
        try:
            X_spl = np.zeros((X.shape[0], self.n_knots - 1))
        except IndexError: # For arrays with only one element
            X_spl = np.zeros((1, self.n_knots - 1))
        X_spl[:, 0] = X.squeeze()

        def d(knot_idx, x):
            def ppart(t): return np.maximum(0, t)

            def cube(t): return t*t*t
            numerator = (cube(ppart(x - self.knots[knot_idx]))
                         - cube(ppart(x - self.knots[self.n_knots - 1])))
            denominator = self.knots[self.n_knots - 1] - self.knots[knot_idx]
            return numerator / denominator

        for i in range(0, self.n_knots - 2):
            X_spl[:, i+1] = (d(i, X) - d(self.n_knots - 2, X)).squeeze()
        return X_spl

def ApplySplineSmoothing(x_data, y_data, knots):
    
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    model = get_natural_cubic_spline_model(x_data, y_data, minval=min(x_data), maxval=max(x_data), n_knots=knots)
    smooth = model.predict(x_data)
    
    return smooth

# def detect_peaks(data,    **kwargs  ):
#     """
#     peak detection

#     Parameters
#     ----------
#     data : TYPE
#         DESCRIPTION.
#     **kwargs : TYPE
#         DESCRIPTION.

#     Returns
#     -------
#     smooth : TYPE
#         DESCRIPTION.
#     TYPE
#         DESCRIPTION.
#     prominences : TYPE
#         DESCRIPTION.

#     """
#     prominence = kwargs.get('prominence', None)
#     peaks=signal.find_peaks(data ,prominence=prominence)[0] #using find peaks from signal
#     prominences = signal.peak_prominences(data, peaks)[0]
#     return peaks, prominences


#import parse_tdms_new as tdms
import matplotlib.pylab as plt

#channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_20.tdms") 

#distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = tdms.GetForceDistAndParms("18h58m54s_Felix_AC10_SdrG_Fln4FgB__S4_3.000_Basic_19", channel_data_deflection, channel_data_piezo)

def find_peaks(data, **kwargs):
    """
    Parameters
    ----------
    ts : table of info extracted from log (type= pandas.df)
    knots : int
        The knots
    **kwargs : int
        The threshold of prominence.

    Returns
    -------
    df : data frame
        data frame of data.
    smooth : array of smooth data
        
    peaks:list
        list of all detected peaks
    prominences : array
        array of all prominences 

    """

  #  width = kwargs.get('width', None)
    prominence= kwargs.get('prominence', None)

    properties= []

    peaks=signal.find_peaks(data, prominence=prominence,  height=0)[0] #using find peaks from signal
    properties.append(signal.find_peaks(data,  prominence=prominence, height=0)[1])
    return list(peaks), properties

#import parse_tdms_new as tdms
#channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_20.tdms") 

#distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = tdms.GetForceDistAndParms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1", channel_data_deflection, channel_data_piezo)

#peaks, properties = find_peaks(force, width=10)
#plt.plot(distance, force)
#for i in peaks:
 #   plt.plot(distance[i], force[i], 'or')
#print(peaks)

def get_slopes(extension, f, peaks, distance, time):
    """
    Compute loading rates (slopes) and intercepts before each peak in force-extension data.

    Parameters
    ----------
    extension : list or array-like
        Extension values (TSS) in nanometers.
    f : array-like
        Force values in piconewtons.
    peaks : list of int
        Indices of the detected peaks.
    distance : float
        Distance before the peak (in nanometers) to calculate slope from.
    time : array-like
        Time values in seconds.

    Returns
    -------
    d : dict
        Dictionary containing computed values including:
        - 'f': force at peak
        - 'dis1': extension at peak
        - 'disTMP': target extension (extension at peak - distance)
        - 'dis2': closest matching extension in the dataset
        - 'index_dis2': index of 'dis2'
        - 'peaks': list of peak indices
    slopes : list of float
        List of computed slopes (loading rates).
    intercepts : list of float
        List of y-intercepts from linear fits.
    """
    # Convert inputs to numpy arrays for easier processing
    extension = np.asarray(extension)
    f = np.asarray(f)
    time = np.asarray(time)

    d = {
        'f': [],
        'dis1': [],
        'disTMP': [],
        'dis2': [],
        'index_dis2': [],
        'peaks': []
    }

    slopes = []
    intercepts = []

    for peak_index in peaks:
        # Get extension and force at peak
        peak_extension = extension[peak_index]
        d['f'].append(f[peak_index])
        d['dis1'].append(peak_extension)

        # Target extension before the peak
        target_extension = peak_extension - distance
        d['disTMP'].append(target_extension)

        # Find index of the closest extension value to the target
        idx_nearest = np.abs(extension - target_extension).argmin()
        d['dis2'].append(extension[idx_nearest])
        d['index_dis2'].append(idx_nearest)
        d['peaks'].append(peak_index)

        # Slice data between the found index and the peak
        start, end = idx_nearest, peak_index
        if end <= start:
            # Prevent invalid slice
            slopes.append(np.nan)
            intercepts.append(np.nan)
            continue

        time_slice = time[start:end]
        force_slice = f[start:end]

        # Fit a line: f = slope * t + intercept
        coeffs = np.polyfit(time_slice, force_slice, 1)
        slopes.append(coeffs[0])
        intercepts.append(coeffs[1])

    return d, slopes, intercepts
def find_intersection(f ,g):
    """
    this function finds the contact point ( the intersection of each curve with 0 axis)

    Parameters
    ----------
    x : array
        array x-axis (could be distance, extension or piezo ).
    deflection : array
        deflection data



    """
    max_force= np.full(len(f), max(f)+2*10**3)
   # print(max(f))
    intersections = []
    prev_dif = 0
    t0, prev_c1, prev_c2 = None, None, None
    for t1, c1, c2 in zip(f, g, max_force):
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

  #  if len(intersections)== 0:
   #     tkinter.messagebox.showinfo('warning' ,'No intersection point found')
    if len(intersections) != 0:
       # print(intersections)
        return intersections[0]


def return_highest_peaks(properties, peaks, N_peaks):
    list_all_heights=[]
            #get all the heights of the peaks
    for i in range(len(properties)):
        for j in range(len(properties[i]['peak_heights'])):
            list_all_heights.append(properties[i]['peak_heights'][j])
                #sort the heights
            list_all_heights=sorted(list_all_heights) 
          #  print(list_all_heights)
                # keep only last highest peaks according tot the user's number N_peaks
            list_all_heights= list_all_heights[-N_peaks:]
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
                #append the heighest peaks in a list
                n_peaks.append(peaks[list(properties[i]['peak_heights']).index(theset[j])])
    return n_peaks

# import parse_tdms_new as tdms 
# import contact_point as CP

# channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1/F_Curve_Basic_S4_100.00_50.tdms") 
# plt.grid()

# distance, force, K, invOLS, sensitivity, piezo_gain, index_end_approach, index_start_approach, index_start_retract, index_end_retract = tdms.GetForceDistAndParms("18h17m45s_Felix_AC10_SdrG_Fln4FgB__S4_100.000_Basic_1", channel_data_deflection, channel_data_piezo)

# corrected_deflection= tdms.CorrectVirtualDeflection( channel_data_deflection, distance,  2, index_start_approach, index_end_approach, index_start_retract, index_end_retract, 90)
# extension= tdms.ComputeExtension(force, distance, K)
# extension= extension+ max(extension)

# distance, force= tdms.FDmodifParms(corrected_deflection, channel_data_piezo, K, invOLS, piezo_gain, sensitivity)



# intersection= CP.FindContactPoint(extension,  corrected_deflection)
# extension= CP.CorrectContactPoint(extension, intersection[1])

# peaks, properties= find_peaks(force[index_start_retract: index_end_retract])

# peak= return_highest_peaks(properties, peaks, 2)
# peak= list(peak)
# print(peak)
# plt.xlabel("Time (s)")
# plt.ylabel("Force (pN)")
# #plt.ylim([-600, 200])
# #peak= list([peaks[360]])

# #print('extension' ,extension[index_start_retract: index_end_retract][peaks[3]])
# #print(peak)

# #print('extension fun ', extension[index_start_retract: index_end_retract][0: 10])
# #print('dist func ', distance[0:10])
# d, slope, intercept= get_slopes(extension[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract], peak, 3, time[index_start_retract: index_end_retract])

# plt.plot(time[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract])

# for i in range(len(d['peaks'])): 
#     plt.plot(time[index_start_retract: index_end_retract][d['index_dis2'][i]:d['peaks'][i]], slope[i]*np.array(time[index_start_retract: index_end_retract][d['index_dis2'][i]:d['peaks'][i]])+intercept[i],'r')
# #plt.plot(extension, force)
# #plt.close()

# #plt.plot(extension, force)
# #plt.savefig('force vs extension func.pdf')
# #np.savetxt("extension_1.csv", extension, delimiter="  ")

# # # #plt.savefig('slope.pdf')
#for i in peak: 
 #   plt.plot(time[index_start_retract: index_end_retract][i], force[index_start_retract: index_end_retract][i], 'or')
#plt.plot(extension, force)
 
#plt.savefig('slope_.pdf')

# #smooth= ApplySplineSmoothing(distance, force, 200)
# smooth= tdms.ApplySavgol(force[index_start_retract: index_end_retract], 77)
# peaks, prominences= find_peaks(smooth, prominence=100)
# plt.plot(extension[index_start_retract: index_end_retract], force[index_start_retract: index_end_retract])


# for i in peaks:
#     plt.plot(distance[index_start_retract: index_end_retract][i], force[index_start_retract: index_end_retract][i], 'or')


# #print(peaks)

# Lc= 28
# pl=0.4
# force= tdms.FitWLC( extension[index_start_retract: index_end_retract], Lc, pl)

# #print(force)
# plt.plot( force,'ob', label='WLC')
# plt.legend()
