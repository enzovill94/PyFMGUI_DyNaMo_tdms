#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  1 15:53:31 2021

@author: Ismahene
"""

# import numpy as np
# # =============================================================================
# # WLC
# # =============================================================================

def WLC(extension, Lc):

    L_p=0.4
    kB = 1.38064852e-2  # Boltzmann constant in pN·nm/K
    T = 298  # Room temperature in Kelvin
    kBT = kB * T
    epsilon = 1e-12  # Small offset to avoid division by zero

    x_ratio = extension / (L_c + epsilon)
    x_ratio = np.clip(x_ratio, 0, 0.99)  # Prevent singularity at x = L_c

    F = (kBT / L_p) * (1 / (4 * (1 - x_ratio)**2) - 1/4 + x_ratio)
    return F


def residuals( y, extension, Lc):
    return y - WLC(extension, Lc)

import numpy as np

# =============================================================================
# WLC Model - Marko-Siggia Approximation
# =============================================================================
# def WLC(extension, Lc):
#     """
#     Computes the force-extension relationship using the Marko-Siggia WLC model.

#     Parameters:
#         extension (array-like): Extension values in nm.
#         Lc (float): Contour length in nm.
#         pl (float): Persistence length in nm (default = 0.4 nm for ssDNA).
#         T (float): Temperature in Kelvin (default = 298 K, room temperature).
    
#     Returns:
#         numpy.ndarray: Force values in pN.
#     """
#     pl=0.4
#     T=298
#     kB = 1.3807e-2  # pN·nm/K (Boltzmann constant)
#     kBT = kB * T

#     # Avoid division by zero when extension = Lc
#     extension = np.clip(extension, 0, 0.99 * Lc)

#     # Vectorized calculation for performance
#     force = (kBT / pl) * (1 / (4 * (1 - extension / Lc) ** 2) - 1 / 4 + extension / Lc)

#     return force

# =============================================================================
# Residuals Function for Fitting
# =============================================================================
def residuals(y_exp, extension, Lc, pl=0.4):
    """
    Computes residuals between experimental and WLC model predictions.

    Parameters:
        y_exp (array-like): Experimental force data in pN.
        extension (array-like): Extension values in nm.
        Lc (float): Contour length in nm.
        pl (float): Persistence length in nm (default = 0.4 nm).

    Returns:
        numpy.ndarray: Residuals (difference between experimental and model).
    """
    return y_exp - WLC(extension, Lc )



# import matplotlib.pyplot as plt

# import parse_jpk as JPK
# import parse_tdms_new as TDMS
# directory="/media/mesbah/ADATA HD650/PEG10k/20250321_MLCTBIODCd_I27/30ums/"


# files= JPK.grab_jpk(directory)    
# path= directory + files[30]


# force, time , height_measured, height_piezo, parameters,index_start_approach, \
#                 index_end_approach, index_start_retract, index_end_retract= JPK.parse_jpk(path)
                
# force= TDMS.CorrectVirtualDeflection(force, height_measured, 2, index_start_approach, index_end_approach, 90)                
                
# intersection= JPK.FindContactPoint(height_measured,  force)                
# extension=    JPK.CorrectContactPoint(height_measured, intersection)    

# # plt.plot(extension , force)


# # Define polymer parameters
# Lc_real = -380 # Contour length in nm
# pl_real = 0.4    # Persistence length in nm



# # Compute force using WLC model
# force_values = WLC(extension[index_start_retract: index_end_retract], Lc_real)

# res= residuals(force, extension, Lc_real, pl=0.4)


# plt.scatter(res, force)

# # Plot the force-extension curve
# plt.figure(figsize=(7, 5))
# plt.plot(extension[index_start_retract: index_end_retract], force_values, label="WLC Model", color="red")
# plt.plot(extension, force, color="blue")

# plt.ylim(-200,  max(force)+ 500)

# plt.xlabel("Extension (nm)")
# plt.ylabel("Force (pN)")
# plt.title("WLC Force-Extension Curve")
# plt.legend()
# plt.grid()
# plt.show()






