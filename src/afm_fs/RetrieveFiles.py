#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 16:09:37 2021

@author: Ismahene
"""



import os


import fnmatch,glob

def newest(files):
    path="."
    paths = [os.path.join(path, basename) for basename in files]
    if len(paths) == 0:
        print('no file found')
    else:
        return max(paths, key=os.path.getctime)


def TdmsfileNamesRetrieve( fnMask  ):
    #list of files
    someFiles = []
    tdms_files= []
    maxDepth=5
    top="."
    #looping over directories at each depth 
    for d in range( 1, maxDepth+1 ):
        maxGlob = "/".join( "*" * d )
        topGlob = os.path.join( top, maxGlob )
        allFiles = glob.glob( topGlob )
        someFiles.extend( [ f for f in allFiles if fnmatch.fnmatch( os.path.basename( f ), fnMask ) ] )
    for file in someFiles:
        if file.endswith('.tdms'):
            tdms_files.append(file)
    if len(tdms_files) == 0:
        print('no file found !!')
        recent_file=None
    else:
        recent_file= newest(tdms_files)

    return  recent_file

# #top="."
# # # #maxDepth=5
# fnMask="F_"
# tdms_file= TdmsfileNamesRetrieve(  fnMask  )

# print(tdms_file)  
    
# import parse_tdms_new as tdms

# channel_data_deflection, channel_data_piezo, time= tdms.parse_tdms(tdms_file) 

# print(channel_data_deflection)

#import subprocess
#paths = [line[2:] for line in subprocess.check_output("find . -iname '*.tdms'", shell=True).splitlines()]

#print(paths)



    