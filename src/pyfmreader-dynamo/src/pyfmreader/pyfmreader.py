# File containing the function loadfile,
# used as an entry point to load different
# AFM data format files.

import os
from .constants import *
from .jpk.loadjpkfile import loadJPKfile
from .jpk.loadjpkthermalfile import loadJPKThermalFile
from .nanosc.loadnanoscfile import loadNANOSCfile
# from .ps_nex.loadpsnexfile import loadPSNEXfile
from .ps_nex.loadpsnexfile import loadPSNEXfile
from .load_uff import loadUFFtxt
from .uff import UFF

def loadfile(filepath, **kwargs):
    """
    Load AFM data file in various supported formats.

    Supported formats and their extensions:
        - JPK: .jpk-force, .jpk-force-map, .jpk-qi-data, .zip (JPK archives)
        - JPK Thermal: .tnd
        - NANOSCOPE: .spm, .pfc, .00X (where X is a digit)
        - UFF: .uff, .txt
        - PS-NEX: .tdms
        - HS3: .tdms (when hs3_bool=True)

    Parameters:
        filepath (str): Path to the AFM data file.
        hs3_bool (bool, optional): If True and file is PS-NEX, load as HS3 format. Default is False.
        **kwargs: Additional keyword arguments for specific loaders.

    Returns:
        UFF: For JPK, NANOSCOPE, UFF, and PS-NEX files, returns a UFF object containing loaded data.
        tuple: For JPK Thermal files, returns a tuple:
            (amplitude (np.ndarray), frequencies (np.ndarray), fit_data (np.ndarray), parameters (dict))

    Raises:
        Exception: If the file format is not supported or cannot be loaded.
    """
    # check if hs3_bool is in kwargs
    if 'hs3_bool' in kwargs:
        hs3_bool = kwargs['hs3_bool']
    else:
        hs3_bool = False
    
    split_path = filepath.split(os.extsep)
    # Depending on the configuration of the OS, JPK files have the following
    # extension: .jpk-force.zip
    if split_path[-1] == 'zip': filesuffix = split_path[-2]
    else: filesuffix = split_path[-1]

    uffobj = UFF()

    if filesuffix[1:].isdigit() or filesuffix in nanoscfiles:
        return loadNANOSCfile(filepath, uffobj)

    elif filesuffix in jpkfiles:
        return loadJPKfile(filepath, uffobj, filesuffix)
    
    elif filesuffix in ufffiles:
        return loadUFFtxt(filepath, uffobj)
    
    elif filesuffix in jpkthermalfiles:
        return loadJPKThermalFile(filepath)
    
    elif filesuffix in psnexfiles:
        # print("is the best")
        if hs3_bool:
            from .hs3.loadhs3file import loadHS3file
            return loadHS3file(filepath, uffobj)
            print("HS3 file loaded")
        else:
            return loadPSNEXfile(filepath, uffobj)
    
    else:
        Exception(f"Can not load file: {filepath}")