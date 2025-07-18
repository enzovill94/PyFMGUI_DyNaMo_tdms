#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 22 15:11:41 2021

@author: Ismahene
"""

#start = time.perf_counter()
#end3 = time.perf_counter()
#print(f"Execution time: {end3 - end2:.6f} seconds - Setting up GUI")
from pathlib import Path
import tkinter.messagebox  # to show pop-up windows to the user
from tkinter import * #library needed for the GUI
#from tkinter.filedialog import askopenfilename  #permits to the user to open a file
from tkinter import filedialog
from tkinter import ttk   #needed for treeview
from matplotlib.backends.backend_tkagg import ( FigureCanvasTkAgg,NavigationToolbar2Tk) #matplitlib backend compatible with tkinter 
from matplotlib.figure import Figure # to create figures

# import pyfmreader.ps_nex.parseTDMS as tdms
from scipy.signal import find_peaks
import os #needed for path
import time #needed to calculate time

import numpy as np #numpy for matrix & arrays
from scipy.optimize import curve_fit  # For curve fitting (e.g. polynomial, sinusoidal...etc,.)

from ardf.read_ardf import read_ardf_metadata # functions needed to work with ARDF data
from ardf.get_ardf_data import extract_ardf_data # functions needed to work with ARDF data


## Personal custom libraries
import parse_tdms_new as tdms #personal library that parses tdms files and extracts info
import parse_jpk as JPK   #personal library that parses JPK files and extracts info
import parse_ARDF as ARDF  #personal library that parses ARDF files and extracts info
import parse_ibw as IBW #personal library that parses ibw files and extracts info
import functions as func #personal library that contains smoothing functions
import contact_point as cp  #personal library that finds contact point of retract and approach
import WLC as wlc #personal library that fits the Warm-like Chain model
import LcFc as Lc
import NoiseLevel as NL
import RetrieveFiles as RF
import pandas as pd
import export_parms as xp
import FJC as fjc


from pyfmreader import loadfile

class App:
    def __init__(self):
        
       # self.widget_main= None
       # self.toolbar_main= None 
        #self.widget_second_tab= None
        #self.toolbar_second_tab=None        global saved_directory
        self.widget_main= None
        self.toolbar_main= None
        self.dict_info= { }
        self.dict_raw= { }
        self.window = Tk() 
        self.style = ttk.Style(self.window)
        self.style.configure("lefttab.TNotebook", tabposition="nw")
        self.notebook = ttk.Notebook(self.window, style="lefttab.TNotebook")
        self.export_file_path = None # Export function, if filled then exports automatically to the first give file
        self.psnex_file = None
        self.filetype = None


        # Get screen size
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        #self.window.geometry("%dx%d" % (screen_width/2, screen_height/2))
        #self.window.resizable(height = screen_width,  width = screen_height)
    #   self.window.resizable(width=True, height=False)

        

        # Get percentage of screen size from Base size
        percentage_width = screen_width / (600/ 100)
        percentage_height = screen_height / (200/ 100)
        
        # Make a scaling factor, this is bases on average percentage from
        # width and height.
        scale_factor = ((percentage_width + percentage_height) / 2) / 100


        # Set the fontsize based on scale_factor,
        # if the fontsize is less than minimum_size
        # it is set to the minimum size
        fontsize = int(14 * scale_factor)
        minimum_size = 8
        if fontsize < minimum_size:
            fontsize = minimum_size
        #creation of frames
        self.main_tab = Frame(self.notebook,  width=screen_width*scale_factor, height=screen_height*scale_factor)


        #add notebook
        self.notebook.add(self.main_tab, text="Main")

        # initialization 
        self.frame=Frame(self.main_tab)
        
        #pack notebook 
        self.notebook.pack(side='top')
        
        #window title
        self.window.title("AFM_FS software")
        #window size
        self.window.minsize(800, 400)
        self.window.config()

# =============================================================================
# Add subframes of main tab (subframes are needed to embedd plots and buttons 
# in the same window)
# =============================================================================
        self.subframe_main_tab= Frame(self.frame)
        self.subframe_plots= Frame(self.frame)
        
        #creation of treeview to  visualize detected peak detection 

        self.subframe_tab_peaks= Frame(self.frame)
        self.subframe_list_peaks= Frame(self.frame)

        # creation of left frame
        self.subframe_second_tab = Frame(self.frame)
        self.subframe_other = Frame(self.frame)

        
        self.columns=('peak index', 'Indentation/Separation (nm)', 'Force [pN]' , 'Loading Rate (pN/s)')
        self.scrollbar=Scrollbar(self.subframe_tab_peaks)
        self.tab_peak_detection = ttk.Treeview(self.subframe_tab_peaks,columns=self.columns,selectmode="extended",yscrollcommand=self.scrollbar.set)

        #defenition of headers and size of columns of peak detection tab
        self.tab_peak_detection.heading("peak index", text="peak index")
        self.tab_peak_detection.column("peak index")
        self.tab_peak_detection.heading("Indentation/Separation (nm)", text="Indentation/Separation (nm)")
        self.tab_peak_detection.column("Indentation/Separation (nm)")
        self.tab_peak_detection.heading("Force [pN]", text="force [pN]")
        self.tab_peak_detection.column("Force [pN]")
        self.tab_peak_detection.heading("Loading Rate (pN/s)", text="Loading Rate (pN/s)")
        self.tab_peak_detection.column("Loading Rate (pN/s)")
        self.scrollbar.config(command=self.tab_peak_detection.yview)


        # Expand frame
        self.frame.pack(expand=YES)
        
        self.subframe_second_tab.grid(row=0, column=0)
        self.subframe_other.grid(row=1, column=0)
        self.subframe_main_tab.grid(row=0, column =2)
        self.subframe_plots.grid(row=0, column=1)
        self.subframe_tab_peaks.grid(row=1, column=1)
        self.subframe_list_peaks.grid(row=1, column=2)




        # creation of composants
        self.create_widgets()

        
        
    def create_widgets(self):
        """
        Loads all the widgets of the app
        
        Returns
        -------
        None.
        
        """
        self.create_buttons_main_tab()
        
    def create_buttons_main_tab(self):
        """
        This function creates all the buttons and entries of the main tab

        Returns
        -------
        None.

        """
        upload_button = Button(self.subframe_main_tab, text=" Upload file", font=("Courrier", 10)
                          ,width=30, command=self.fileDialog)
        upload_button.grid(row=0,column=1)
        
        self.combo_file = ttk.Combobox(self.subframe_main_tab, 
                            values=[
                                    ".tdms", 
                                    ".jpk",
                                    ".ibw",
                                    ".ARDF"
                                    ], font=("Courrier", 10),width=5)
        self.combo_file.grid(row=0, column= 2)
        self.combo_file.current(0)
        
        label_file_name= Label(self.subframe_main_tab,  text=" or set file name", font=("Courrier", 10),width=15)
        label_file_name.grid(row=2, column= 1, sticky=W)
        
        self.file_name= StringVar()
        entry_file_name= Entry(self.subframe_main_tab, textvariable= self.file_name,  font=("Courrier", 10),width=20)
        entry_file_name.grid(row=2, column= 1, sticky=E)
       # entry_file_name.insert('end', '*')

    
    def get_file_from_retrieve(self):
        """
        Gets the files from the name given by the user 

        Returns
        -------
        None.

        """
        if self.file_name.get() and  self.combo_file.get() == ".tdms":
            fnMask= self.file_name.get() + str('*')
            self.path= RF.TdmsfileNamesRetrieve(fnMask)
            if (os.path.sep) == "\\" :
                self.directory = self.path.split('\\')[-2]

            else:
                self.directory= self.path.split('/')[-2]

            self.path, self.all_tdms= tdms.grab_tdms(self.directory)
            self.tdms_file=self.path.split('/')
                        #add a label with the name of the file
            self.label_tdms= Label(self.subframe_main_tab, text=str(self.tdms_file[-1]),font=("Courrier", 10),width=30)
            self.label_tdms.grid(row=1, column=1)


    def fileDialog(self):
        """
        
        This function opens a window to select the tdms or JPK files 
        -------
        Returns
        -------
        None.
        """

        self.path=None
        self.get_file_from_retrieve()
        
        
        
        if self.combo_file.get() == ".tdms" and self.path == None:
           
            #self.path=askopenfilename(title = "Select A File",
             #                                 filetypes =(("tdms File", "*.tdms"),("tdms", "*.tdms"),("tdms","*.tdms*")) ) 
            self.directory = filedialog.askdirectory( initialdir=".")
            #self.path=self.directory
            #if (os.path.sep) == "\\" :
            #  self.directory = self.path.split('\\')


            # else:
            # self.directory= self.path.split('/')


            self.path, self.all_tdms= tdms.grab_tdms(self.directory)

            try: 
                self.psnex_file = loadfile(self.path)
                print ('psnex file loaded')
            except: 
                return


            if self.path ==None:
                tkinter.messagebox.showinfo("Warning ", "No tdms file found !!")
            self.tdms_file=self.path.split('/')
            #add a label with the name of the file
            self.label_tdms= Label(self.subframe_main_tab, text=str(self.tdms_file[-1]),font=("Courrier", 10),width=30)
            self.label_tdms.grid(row=1, column=1)
            #save the name of the directory in a variable, this one is needed to load the text file of parameters
            #try:
            # self.directory= '/'.join(map(str, self.tdms_file[:-1]))
            # except:
            #  tkinter.messagebox.showinfo("Warning ", "Please upload a file")
                
        
        elif self.combo_file.get() == ".jpk":
            
           # self.path=askopenfilename( title = "Select A File",
            #                                  filetypes =(("jpk File", "*.jpk"),("jpk-force", "*.jpk-force"),("jpk","*.jpk*")) ) 
            self.directory = filedialog.askdirectory( initialdir="")
            # print(self.directory)
            self.path= self.directory +'/' + JPK.grab_jpk(self.directory)[0]
            if self.path==None:
                tkinter.messagebox.showinfo("Warning ", "No JPK file found !!")
            
            #start = time.perf_counter()
            self.all_jpk_files= JPK.grab_jpk(self.directory+'/')
            
            self.jpk_file=self.path.split('/')[-1]
            

            self.label_jpk= Label(self.subframe_main_tab, text=str(self.jpk_file),font=("Courrier", 10),width=40)
            self.label_jpk.grid(row=1, column=1)
        
        elif self.combo_file.get() == ".ARDF": 
            self.directory = filedialog.askdirectory( initialdir=".")
            #start = time.perf_counter()
            self.path, self.all_ardf = ARDF.grab_ardf(self.directory)


            if self.path==None:
                tkinter.messagebox.showinfo("Warning ", "No ARDF file found !!")
            
            self.ardf_file=self.path.split('/')
    
            self.label_ardf= Label(self.subframe_main_tab, text=str(self.ardf_file[-1]),font=("Courrier", 10),width=30)
            self.label_ardf.grid(row=1, column=1)

            
            # These variables will be needed to iterate through the force distance curves in ARDF files
            self.current_curve_index = 0  # tracks which curve inside the ARDF
            self.current_file_index = 0   # tracks which ARDF file in folder
            self.point = 0
            self.line = 0
            self.trace = 1

            # File metadata, we get it here so it is not collected for every single force curve of the same ARDF file
            self.file_struct = read_ardf_metadata(self.path)
            self.nlines = self.file_struct['y'].shape[0]
            self.npoints = self.file_struct['y'].shape[1]
            self.all_positions_ardf = []

            for line in range(self.nlines):
                for point in range(self.npoints):
                    self.all_positions_ardf.append([line, point])
            # print(self.all_positions_ardf)
            # Needed to navigate to next file
            #self.total_curves_in_current_file = self.nlines * self.npoints

            
            try:
                self.ardf_file[-2]
                self.directory= '/'.join(map(str, self.ardf_file[:-1]))
            except:
                tkinter.messagebox.showinfo("Warning ", "Please upload a file")
        
        
        elif self.combo_file.get() == ".ibw":
             
            self.directory = filedialog.askdirectory( initialdir="")
            # print(self.directory)
            self.path= self.directory +'/' + IBW.grab_ibw(self.directory)[0]
            if self.path==None:
                tkinter.messagebox.showinfo("Warning ", "No ibw file found !!")
            self.all_ibw_files= IBW.grab_ibw(self.directory+'/')
            
            self.ibw_file=self.path.split('/')[-1]
            

            self.label_ibw= Label(self.subframe_main_tab, text=str(self.ibw_file),font=("Courrier", 10),width=40)
            self.label_ibw.grid(row=1, column=1)

        #end2 = time.perf_counter()
        #print(f"Execution time: {end2 - start:.6f} seconds - Selecting file")
        # plot the graph on the GUI
        self.get_deflection_vs_piezo()

        #create and pack 'next' button to be able to navigate through the files
        next_button= Button (self.subframe_main_tab, text= "Next",  font=("Courrier", 10) , width=5, command= self.nextFile)
        next_button.grid(row=3,column=1, sticky= E)
        
        
        #previous button
        previous_button= Button (self.subframe_main_tab, text= "Previous",  font=("Courrier", 10), width=5, command= self.PreviousFile)
        previous_button.grid(row=3,column=1, sticky= W)
        
        # prepare checkbuttons and variables ( the user can choose to see approach and retract seperated or not )
        self.approachOn=IntVar()
        approach_checkbutton= Checkbutton(self.subframe_main_tab, text= "approach", variable=self.approachOn, font=("Courrier", 10), onvalue = 1, offvalue = 0)
        #approahc is selected by default
        approach_checkbutton.select()
        approach_checkbutton.grid(row=7, column=2)
        
        self.retractOn= IntVar()
        retract_checkbutton= Checkbutton(self.subframe_main_tab, text= "retract", variable=self.retractOn, font=("Courrier", 10),onvalue = 1, offvalue = 0)
        #retract is selected by default
        retract_checkbutton.select()
        retract_checkbutton.grid(row=8, column=2)

        
        

        
        if self.combo_file.get() == ".tdms":
            


            #loading the parameters from the txt file of the parameters in the same folder as the force curves 
            if self.psnex_file == None:
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms(self.directory, self.channel_data_deflection, self.channel_data_piezo, self.time)
            else: 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms_psnex(self.path)
            
            #compute the extension 
            self.extension= tdms.ComputeExtension(self.force, self.distance, self.K)
            self.channel_data_deflection_nm= tdms.DeflectionInNanometer(self.channel_data_deflection , self.invOLS)
            self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
            self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm


            
            # offset and save the extension in a dictionary that contains all important info
            self.dict_info["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            #print(self.dict_info["Indentation/Separation (nm)"][0:10])
            self.dict_raw["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            # offset and save the distance in nm in the dictionnary of info
            self.dict_info["Distance (nm)"]= self.distance+ max(self.distance)
            self.dict_raw["Distance (nm)"]= self.distance+ max(self.distance)
            # save the force in pN in the dictionnary of info
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            # save the index of the start of the approach
            self.dict_info["index start approach"]= self.index_start_approach
            # save the inddex of the end of the approach
            self.dict_info["index end approach"]= self.index_end_approach
            # save the index of the start of the retract
            self.dict_info["index start retract"]= self.index_start_retract
            # save the index of the end of the retract 
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_info["Spring constant (N/m)"]= self.K


        # if it is a JPK file, the information is loaded differently from tdms
        elif self.combo_file.get() == ".jpk":
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= JPK.parse_jpk(self.path)
            #save all necessary info in dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity'] * 10**9
            self.invOLS= 1/self.sensitivity
            self.velocity= self.parameters['speed retract'] * 10**6
            
        
            


        # if it is an ARDF file, the information is loaded differently from the others
        elif self.combo_file.get() == ".ARDF":
            
            # loading the parameters from the txt file of the parameters in the same folder as the force curves 
            # extracting 
            self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
            # compute the extension 
            self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
            # ARDF deflection already comes in m (no Volts)
            self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)
            self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
            self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm


            
            # offset and save the extension in a dictionary that contains all important info
            # self.dict_info["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            self.dict_info["Indentation/Separation (nm)"]= self.extension 
            #self.dict_raw["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            # offset and save the distance in nm in the dictionnary of info
            # self.dict_info["Distance (nm)"]= self.distance - min(self.distance)
            # self.dict_raw["Distance (nm)"]= self.distance - min(self.distance)
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            # save the force in pN in the dictionnary of info
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force

            self.dict_raw["index start approach"]= self.index_start_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            self.dict_raw["index start retract"]= self.index_start_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            # save the index of the start of the approach
            self.dict_info["index start approach"]= self.index_start_approach
            # save the inddex of the end of the approach
            self.dict_info["index end approach"]= self.index_end_approach
            # save the index of the start of the retract
            self.dict_info["index start retract"]= self.index_start_retract
            # save the index of the end of the retract 
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_info["Spring constant (N/m)"]= self.K
            self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6
            # print("Reached here and no problems, point 1")
            
    
            # if the user wants to change to the next ARDF file but not the next item in the current ARDF file
            next_button_ardf= Button (self.subframe_main_tab, text= "Next ARDF",  font=("Courrier", 10) , width=8, command=lambda: self.nextFile(ARDF_flag=True))
            next_button_ardf.grid(row=20,column=1)

            #start = time.perf_counter()
            #end = time.perf_counter()
            #print(f"Execution time: {end - start:.6f} seconds - Loading file")

            
            




        # if it is a JPK file, the information is loaded differently from tdms
        elif self.combo_file.get() == ".ibw":
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= IBW.parse_ibw(self.path)
            #save all necessary info in dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity'] * 10**9
            self.invOLS= 1/self.sensitivity
            self.velocity= self.parameters['speed retract'] * 10**6

        

        #end4 = time.perf_counter()
        #print(f"Execution time: {end4 - end3:.6f} seconds - Loading file")
        # create entry to indicate the RMS
        self.percentage_noise= IntVar()
        entry_percentage_noise=Entry(self.subframe_main_tab, textvariable= self.percentage_noise,  font=("Courrier", 10),width=10)
        entry_percentage_noise.delete(0, 'end')
        entry_percentage_noise.insert(0, 30)
        entry_percentage_noise.grid(row=4, column=1, sticky= E)

       # self.entry_noise= Entry(self.subframe_main_tab,   font=("Courrier", 10),width=5)
            #calculate RMS
        self.RMS= NL.get_RMS(self.dict_info["Force (pN)"][ self.dict_info["index start retract"]: self.dict_info["index end retract"]], 1)  
      #  self.entry_noise.delete(0, 'end')
      #  self.entry_noise.insert(0, str(self.RMS))
       # self.entry_noise.grid(row=4, column=1,sticky=E)

        self.label_noise= Label(self.subframe_main_tab, text= "RMS:     "+str(self.RMS)+ "  pN"+ "      Set %  here: ",  font=("Courrier", 10) )
        
        self.label_noise.grid(row= 4, column=1, sticky=W)
        
        button_noise= Button(self.subframe_main_tab,  text= "Get RMS",  font=("Courrier", 10), width=5, command= self.noise_level)
        button_noise.grid(row=4, column=2 )
        
        # spring constant
        self.entry_k= Entry(self.subframe_main_tab,   font=("Courrier", 10),width=15)
        self.entry_k.insert(0, str(self.K))
        self.entry_k.grid(row=5, column=1, sticky=E)
        label_k= Label(self.subframe_main_tab, text= "Spring constant"+'\n'+ "(pN/nm)",  font=("Courrier", 9) )
        label_k.grid(row= 5, column=1, sticky=W)
        
        # if the user wants to change the spring constant
        self.change_K= IntVar()
        change_k_checkbutton= Checkbutton(self.subframe_main_tab, variable= self.change_K,   text= "Change it",  font=("Courrier", 10), width=10, onvalue=1, offvalue=0)
                                 
        change_k_checkbutton.grid(row=5, column=2 )
        
        #invOLS entry
        self.entry_invols= Entry(self.subframe_main_tab,   font=("Courrier", 10),width=15)
        self.entry_invols.insert(0, str(self.invOLS))
        self.entry_invols.grid(row=6, column=1, sticky=E)
        label_invols= Label(self.subframe_main_tab, text= "invOLS (nm/V)",  font=("Courrier", 10) )
        label_invols.grid(row= 6, column=1, sticky=W)
        
        # if the user wants to change the invols
        self.change_invOLS= IntVar()
        change_invols_checkbutton= Checkbutton(self.subframe_main_tab, variable=self.change_invOLS ,text= "Change it",  font=("Courrier", 10), width=10 ,onvalue=1, offvalue=0)
                                   
        change_invols_checkbutton.grid(row=6, column=2 )

        
        ## if the user wants to change the invols
        #change_invols_button= Button(self.subframe_main_tab,  text= "OK",  font=("Courrier", 10), width=5,
         #                            command= self.change_parameters)
        #change_invols_button.grid(row=6, column=2, sticky= E )

        #combobox containing plotting options on the x-axis
        self.combo_xaxis = ttk.Combobox(self.subframe_main_tab, 
                            values=[
                                    "Piezo (V)", 
                                    "Indentation/Separation (nm)",
                                    "time (ms)",
                                    "Distance (nm)"
                                    ], font=("Courrier", 10),width=30)
        self.combo_xaxis.grid(row=7, column= 1)
        self.combo_xaxis.current(1)
        

        # combobox containing plotting options on the y-axis
        self.combo_yaxis = ttk.Combobox(self.subframe_main_tab, 
                            values=[
                                    "Deflection (V)", 
                                    "Deflection (nm)", 
                                    "Force (pN)"
                                    ],font=("Courrier", 10),width=30)
        self.combo_yaxis.grid(row=8, column= 1)
        self.combo_yaxis.current(2)
        

        # once parameters selected from combobox x-axis and y-axis the user can press see curve
        plot_button= Button(self.subframe_main_tab, text= "See curve",  font=("Courrier", 10)
                             , width=5, command= self.get_combo_values)
        plot_button.grid(row=9,column=1)

        
# =============================================================================
#    •	Savitzky-Golay filter buttons and entries 
# =============================================================================
        self.smoothing_window= IntVar()
        entry_smoothing=Entry(self.subframe_main_tab, textvariable=self.smoothing_window, width=15, font=("Courrier", 10))  
        entry_smoothing.grid(row=10, column=1, sticky= E)
        
        label_smoothing=Label(self.subframe_main_tab, text='Savizky-Golay filter'  , font=("Courrier", 10))  
        label_smoothing.grid(row=10, column=1, sticky= W )
        
        self.SmoothingOn= IntVar()
        smooth_checkbutton= Checkbutton(self.subframe_main_tab, text= "Apply filter",variable=self.SmoothingOn,  font=("Courrier", 12), onvalue = 1, offvalue = 0
                             , width=10)
        smooth_checkbutton.grid(row=11,column=1)
        
        
# =============================================================================
# buttons and entries to Correct the virtual deflection
# =============================================================================
        label_correction= Label(self.subframe_main_tab, text= "Correct virtual deflection")
        label_correction.grid(row=12, column= 1)

        # if the user wants to correct the deflection only from the approach curve
        self.FromApp=IntVar()
        correction_from_approach_button= Checkbutton(self.subframe_main_tab, text= "from approach", variable=self.FromApp, font=("Courrier", 10), onvalue = 1, offvalue = 0)
        #correction_from_approach_button.select()
        correction_from_approach_button.grid(row=13, column=1)
        
        # entry of the order of the polynomial fitting that the user needs to indicate
        self.Npoly= IntVar()
        entry_Npoly= Entry(self.subframe_main_tab, textvariable=self.Npoly, font=("Courrier", 10), width=15) 
        #delete default value ( zero is default value given by tkinter)
        entry_Npoly.delete(0, 'end')
        #insert polynomial order 1
        entry_Npoly.insert(0, 1)
        entry_Npoly.grid(row=14, column= 1 ,sticky= E)
         
        #label of polynomial order 
        label_Npoly= Label(self.subframe_main_tab, text=" N poly", font=("Courrier", 10)) 
        label_Npoly.grid(row=14, column= 1 ,sticky= W)
        
        # the user can correct the deflection from both retract and approach by setting the % of each curve
        self.pourcentage_retract= IntVar()
        entry_retract_pourcentage= Entry(self.subframe_main_tab, textvariable=self.pourcentage_retract, font=("Courrier", 10)) 
        entry_retract_pourcentage.insert(0, 3)
        entry_retract_pourcentage.grid(row=15, column= 1 ,sticky= E)
        
        #label % retract
        label_retract_pourcentage= Label(self.subframe_main_tab, text=" % retract", font=("Courrier", 10)) 
        label_retract_pourcentage.grid(row=15, column= 1 ,sticky= W)
        # entry of the % of the approach curve
        self.pourcentage_approach= IntVar()
        entry_approach_pourcentage= Entry(self.subframe_main_tab, textvariable=self.pourcentage_approach, font=("Courrier", 10)) 
        entry_approach_pourcentage.insert(0, 7)
        entry_approach_pourcentage.grid(row=16, column= 1 ,sticky= E)
        # label of the percentage from the approach
        label_approach_pourcentage= Label(self.subframe_main_tab, text=" % approach", font=("Courrier", 10)) 
        label_approach_pourcentage.grid(row=16, column= 1 ,sticky= W)
        # button to press after all parms are selected to get the deflection corrected
        self.CorrectVirtualDeflection = IntVar()
        correct_deflection_checkbutton= Checkbutton(self.subframe_main_tab, text= "Correct deflection",  variable= self.CorrectVirtualDeflection, font=("Courrier", 10), onvalue=1, offvalue=0) 
        correct_deflection_checkbutton.select()
        correct_deflection_checkbutton.grid(row=17,column=1, sticky= W)
        
        
        apply_deflection_correction_button= Button(self.subframe_main_tab, text= "Apply ",  font=("Courrier", 10), width=5,
                              command=self.apply_virtual_deflection_correction)
        apply_deflection_correction_button.grid(row=19,column=1, sticky=E)#avant row=17
        
        
        #automatic correction of virtual deflection
        #button of contact point of retract 
        self.CpRetractOn=IntVar()
        contact_point_retract_checkbutton= Checkbutton(self.subframe_main_tab, text= "Contact Point"+'\n'+"retract", variable=self.CpRetractOn, font=("Courrier", 10), onvalue = 1, offvalue = 0)
        #approach is selected by default
        contact_point_retract_checkbutton.select()
        #show CP of retract
        
        #contact_point_retract_button= Button(self.subframe_main_tab,  text= "Contact Point"+'\n'+"retract",  font=("Courrier", 10), 
         #                          command=self.show_point_contact_retract )
        contact_point_retract_checkbutton.grid(row=18, column=1 , sticky=E)
        #button of contact point of approach
        self.CpApproachOn=IntVar()
        contact_point_approach_checkbutton= Checkbutton(self.subframe_main_tab, text= "Contact Point"+'\n'+"approach", variable=self.CpApproachOn, font=("Courrier", 10), onvalue = 1, offvalue = 0)
        contact_point_approach_checkbutton.select()

        contact_point_approach_checkbutton.grid(row=18, column=1, sticky= W)
        #show CP of approach
        # offset the contact point to 0 on the x-axis
        self.CorrectCP=IntVar()
        #correct_contact_point_button= Button(self.subframe_main_tab,  text= "Correct Contact Point ",   font=("Courrier", 10), 
         #                                    command= self.correct_point_contact)
        #correct_contact_point_button.grid(row=19, column=1)
        correct_contact_point_checkbutton= Checkbutton(self.subframe_main_tab,  text= "Correct Contact Point ",  variable= self.CorrectCP, font=("Courrier", 10),  onvalue = 1, offvalue = 0)
        correct_contact_point_checkbutton.select()
        correct_contact_point_checkbutton.grid(row=19, column=1, sticky= W)
        
        # apply_corrections_button= Button(self.subframe_main_tab,  text= "Apply ",   font=("Courrier", 10), width=5,
        #                                      command= self.apply_corrections)
        # apply_corrections_button.grid(row=19, column=1, sticky= E)


        
        #correct contact point of approach and retract
        #plots the options selected on the combobox once the file is loaded
        self.get_combo_values()
        # int variable that contains the number of peaks given by the user
        self.N_peaks =IntVar()
        # int variable that contains the width value given by the user before the peak detection
        self.width= IntVar()

        # Needed to remember deleted peaks in the params file
        self.export_selected_items = None
        
        self.prominence= IntVar()
        # labels for both number of peaks and width
        label_number_peaks= Label(self.subframe_main_tab, text= 'Number '+ '\n'+'of'+'\n'+'peaks', font=("Courrier", 10)) 
        label_number_peaks.grid(row=11, column= 2, sticky=W)
        
        label_width= Label(self.subframe_main_tab, text= 'Width', font=("Courrier", 10)) 
        label_width.grid(row=10, column= 2, sticky=W)
        
        width_entry= Entry(self.subframe_main_tab, textvariable= self.width,  font=("Courrier", 10), width=5)
        width_entry.grid(row= 10, column=2, sticky=E)
        width_entry.delete(0, END)
        width_entry.insert(0, 3)
        
        label_prominence= Label(self.subframe_main_tab, text= 'Promi-'+ '\n'+'nence', font=("Courrier", 10)) 
        label_prominence.grid(row=9, column= 2, sticky=W)
        
        prominence_entry= Entry(self.subframe_main_tab, textvariable= self.prominence,  font=("Courrier", 10), width=5)
        prominence_entry.grid(row= 9, column=2, sticky=E)
        
        #button for peak detection
        self.DetectPeaksOn= IntVar()
        peak_detection_checkbutton= Checkbutton(self.subframe_main_tab, text= "Detect peaks", variable=self.DetectPeaksOn,  font=("Courrier", 10), onvalue=1, offvalue=0
                             , width=12)
        peak_detection_checkbutton.grid(row=12,column=2)
        # entry to set the number of peaks 
        npeaks_entry= Entry(self.subframe_main_tab, textvariable= self.N_peaks,  font=("Courrier", 10), width=5)
        npeaks_entry.grid(row= 11, column=2, sticky=E)
        npeaks_entry.delete(0, END)
        npeaks_entry.insert(0, 1)
        
        # float variable to save the persistence length
        self.range_before_peak= IntVar()
        # string variable to save the contour length
        self.contour_length= StringVar()
        #label for the persistence length
        pl_label= Label(self.subframe_main_tab, text= 'Range '+ '\n'+ '(nm)', font=("Courrier", 10)) 
        pl_label.grid(row=13, column= 2, sticky=E)
        # label to introduce the contour length
        lc_label= Label(self.subframe_main_tab, text= 'Contour '+ '\n'+'length', font=("Courrier", 10)) 
        lc_label.grid(row=13, column= 2, sticky=W)
        
        # button to fit WLC model
        #self.WLCOn= IntVar()
        #fit_WLC_checkbutton= Checkbutton(self.subframe_main_tab, text= "Fit WLC",  variable= self.WLCOn, font=("Courrier", 10), onvalue=1, offvalue=0,
         #                     width=8)
        #fit_WLC_checkbutton.grid(row=14,column=2)
        
        self.combo_fit_model = ttk.Combobox(self.subframe_main_tab, 
                            values=[
                                    "fit WLC", 
                                    "fit FJC",
                                    ], font=("Courrier", 10),width=5)
        self.combo_fit_model.grid(row=15,column=2)
        #self.combo_fit_model.current(0)
        
        
        
        # persistance length entry (here the user sets the value)
        range_before_peak_entry= Entry(self.subframe_main_tab, textvariable= self.range_before_peak,  font=("Courrier", 10), width=5)
        range_before_peak_entry.grid(row= 14, column=2, sticky=E)
        range_before_peak_entry.delete(0, END)
        range_before_peak_entry.insert(0, 3)
        # contour length entry (here the user sets the value)
        self.lc_entry= Entry(self.subframe_main_tab, textvariable= self.contour_length,  font=("Courrier", 10), width=5)
        self.lc_entry.grid(row= 14, column=2, sticky=W)
        
        FcLc_button= Button(self.subframe_main_tab, text= "Plot Fc vs Lc"+'\n'+"& detect peaks",  font=("Courrier", 10)
                             , width=8, command= self.plot_FcLc)
        FcLc_button.grid(row=16,column=2)

        
        self.force_threashold= IntVar()
        force_threshold_entry= Entry(self.subframe_main_tab, textvariable= self.force_threashold,  font=("Courrier", 10), width=5)
        force_threshold_entry.grid(row= 18, column=2)
        
        Lc_peak_button= Button(self.subframe_main_tab, text= "Superpose peaks"+ '\n'+"on F-dis",  font=("Courrier", 10)
                             , width=8, command= self.plot_peak_FcLc)
        Lc_peak_button.grid(row=18,column=2)
        
        
        self.threshold= DoubleVar()
        entry_threshold=Entry(self.subframe_main_tab, textvariable=self.threshold, width=4, font=("Courrier", 10))  
        entry_threshold.grid(row= 17, column =2, sticky= E)
        
        threshold_label= Label(self.subframe_main_tab, text= 'Force '+ '\n'+'threshold '+ '\n'+ '(pN)', font=("Courrier", 9), width=6) 
        threshold_label.grid(row=17, column= 2, sticky=W)
        
        
        loading_rate_button= Button(self.subframe_main_tab, text= "Show"+ '\n'+ "loading rates",  font=("Courrier", 10)
                             , width=8, command= self.plot_loading_rate)
        loading_rate_button.grid(row=19,column=2)
        
        export_data_button= Button(self.subframe_main_tab, text= "export data",  font=("Courrier", 10)
                             , width=8, command= self.export_data)
        export_data_button.grid(row=20,column=2)

        
        #button for peak detection
        self.DetectPeaksOn= IntVar()
        peak_detection_checkbutton= Checkbutton(self.subframe_main_tab, text= "Detect peaks", variable=self.DetectPeaksOn,  font=("Courrier", 10), onvalue=1, offvalue=0
                             , width=12)
        peak_detection_checkbutton.grid(row=12,column=2)
        
        self.hysteresis= IntVar()
        entry_hysteresis=Entry(self.subframe_main_tab, textvariable=self.hysteresis, width=5, font=("Courrier", 10))  
        entry_hysteresis.delete(0, END)
        entry_hysteresis.insert(0, 35)
        entry_hysteresis.grid(row=3, column=2, sticky=S)
        
       # label_hysteresis=Label(self.subframe_main_tab, text='Hysteresis', font=("Courrier", 10), width=10)  
        #label_hysteresis.grid(row=2, column=2, sticky= N)
                
        hysteresis_label= Label(self.subframe_main_tab, text= "Hysteresis",  font=("Courrier", 10)
                             , width=10)
        hysteresis_label.grid(row=2,column=2)
        
        #activate jump to next curve option
        self.JumpOn= IntVar()
        jump_curve_checkbutton= Checkbutton(self.subframe_main_tab, text= "Jump to next", variable=self.JumpOn,  font=("Courrier", 10), onvalue=1, offvalue=0
                             , width=12)
        jump_curve_checkbutton.grid(row=1,column=2)
        
        self.delete_button= Button(self.subframe_tab_peaks, text= "Delete selected peaks ",  font=("Courrier", 12)
                             , width=15, command= self.delete_peaks)
        
# =============================================================================
#    •	left panel buttons and entries 
# =============================================================================

        
        # choose x and y axis range     

        label_x_axis_range= Label(self.subframe_second_tab, text= 'X-axis range', font=("Courrier", 10)) 
        label_x_axis_range.grid(row=8, column= 2, sticky=NW)
        
        label_x_axis_range_from= Label(self.subframe_second_tab, text= 'From', font=("Courrier", 10)) 
        label_x_axis_range_from.grid(row=9, column= 2, sticky=NW)
        
        label_x_axis_range_to= Label(self.subframe_second_tab, text= 'To', font=("Courrier", 10)) 
        label_x_axis_range_to.grid(row=9, column= 3, sticky=NW)
        

        # This if we want range
        self.x_axis_range_from_entry= Entry(self.subframe_second_tab,  font=("Courrier", 10), width=5)
        self.x_axis_range_from_entry.grid(row=10, column=2, sticky=NW)
        self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
  
        self.x_axis_range_to_entry= Entry(self.subframe_second_tab,  font=("Courrier", 10), width=5)
        self.x_axis_range_to_entry.grid(row=10, column=3, sticky=NW)
        self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))

        # This if we want nm
        #self.x_axis_range_nm = Entry(self.subframe_second_tab, font=("Courrier", 10), width=5)
        #self.x_axis_range_nm.grid(row=10, column=3, sticky=NW)
        # 0.1 is a random number just so the code goes through, after the correction it's changed to the 
        # nm of the end of retract position
        #self.x_axis_range_nm.insert(0, str(0))

        self.change_x_axis = IntVar()
        change_x_axis_checkbutton= Checkbutton(self.subframe_second_tab, variable=self.change_x_axis ,text= "Change it",  font=("Courrier", 10), width=10 ,onvalue=1, offvalue=0)                      
        change_x_axis_checkbutton.grid(row=11, column=2 )

        automatic_analysis_button= Button(self.subframe_second_tab, text= "Automatic_analysis",  font=("Courrier", 12)
                             , width=15, command= self.automatic_analysis)
        automatic_analysis_button.grid(row=20,column=2)

        print('Break')
        self.apply_virtual_deflection_correction()
        # end = time.perf_counter()
        # print(f"Execution time: {end - start:.6f} seconds - Loading file")
        self.show_point_contact_approach()
        self.show_point_contact_retract()
        self.correct_point_contact()
        print('Break')
        
        
        #self.x_axis_range_nm.insert(0, str(self.dict_info["Indentation/Separation (nm)"][self.index_end_retract-1]))




    def nextFile(self, ARDF_flag=False):
        """
        When the button 'Next' is pressed, this function is called
        it navigates through the files of directory
        and plot deflection vs piezo

        Returns
        -------
        None.

        """
        """
        When the button 'Next' is pressed, this function is called
        it navigates through the files of directory
        and plot deflection vs piezo

        Returns
        -------
        None.

        """
        start2 = time.perf_counter()
        # if the user wants to see the next file, the dico containing info of the previous file is cleaned
        self.dict_info.clear()
        if self.combo_file.get() == ".tdms":

            # get the index of the next file on the list
            next_index= self.all_tdms.index(self.directory+'/'+self.tdms_file[-1])+1
            # if the user gets to the end of the list: go back to first element (index 0)
            if  next_index == len(self.all_tdms):
                next_index=0
            next_file= self.all_tdms[next_index]
            #get whole path to the selected file
            self.path=  os.path.abspath(self.all_tdms[next_index])
            
            try: 
                self.psnex_file = loadfile(self.path)
                print ('psnex file loaded')
            except: 
                return


            # get the name of the file
            self.tdms_file= next_file.split('/')
            # show the name of the file on the label of the GUI
            self.label_tdms.config(text=self.tdms_file[-1] )
            # extract deflection and piezo from file and plot them
            self.get_deflection_vs_piezo()
            # extract all parms, force, distance...etc.

            #loading the parameters from the txt file of the parameters in the same folder as the force curves 
            if self.psnex_file == None:
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms(self.directory, self.channel_data_deflection, self.channel_data_piezo, self.time)
            else: 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms_psnex(self.path)
            
            
            # compute the extension
            self.extension= tdms.ComputeExtension(self.force, self.distance, self.K)
            # save all info the dico 
            self.dict_info["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            self.dict_raw["Indentation/Separation (nm)"]= self.extension + max(self.extension)

            self.dict_info["Distance (nm)"]= self.distance+ max(self.distance)
            self.dict_raw["Distance (nm)"]= self.distance+ max(self.distance)

            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force

            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_info["index end retract"]= self.index_end_retract
            self.apply_virtual_deflection_correction()
            self.show_point_contact_approach()
            self.show_point_contact_retract()
            self.correct_point_contact()
            self.noise_level()
        # if the user selects JPK
        elif self.combo_file.get() == ".jpk":

            current_index = self.all_jpk_files.index(self.jpk_file)
            next_file_index = (current_index + 1) % len(self.all_jpk_files)
            next_file= self.all_jpk_files[next_file_index]

            self.path=  self.directory + '/' + next_file
            #save the name of JPK file after splitting
            self.jpk_file= next_file
            # insert the name in the label
            self.label_jpk.config(text=self.jpk_file)
            # get the deflection and the piezo
            self.get_deflection_vs_piezo()
            # extract parms, time, force...etc,.
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= JPK.parse_jpk(self.path)
            # save all the info in the dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity']
            self.invOLS= 1/self.sensitivity
            # print(self.all_jpk_files)
            # print(type(self.all_jpk_files))
            # self.all_jpk_files.remove(str(next_file))
            # print(self.all_jpk_files)

        elif self.combo_file.get() == ".ibw":

            current_index = self.all_ibw_files.index(self.ibw_file)
            next_file_index = (current_index + 1) % len(self.all_ibw_files)
            next_file= self.all_ibw_files[next_file_index]

            self.path=  self.directory + '/' + next_file
            #save the name of JPK file after splitting
            self.ibw_file= next_file
            # insert the name in the label
            self.label_ibw.config(text=self.ibw_file)
            # get the deflection and the piezo
            self.get_deflection_vs_piezo()
            # extract parms, time, force...etc,.
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= IBW.parse_ibw(self.path)
            # save all the info in the dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity']
            self.invOLS= 1/self.sensitivity
            # print(self.all_jpk_files)
            # print(type(self.all_jpk_files))
            # self.all_jpk_files.remove(str(next_file))
            # print(self.all_jpk_files)

        elif self.combo_file.get() == ".ARDF":
            # call here the function if the function runs then skip next file, if it doesnt run then go for next file.

            #total_curves_in_current_file = self.nlines * self.npoints
            self.current_curve_index += 1
            # add while loop to iterate over all the force curves in the same file
            #if self.current_curve_index < total_curves_in_current_file - 1 and not ARDF_flag:
            if self.current_curve_index < len(self.all_positions_ardf) - 1 and not ARDF_flag:
                self.line, self.point = self.all_positions_ardf[self.current_curve_index]
                            
            
                # extract deflection and piezo from file and plot them
                self.get_deflection_vs_piezo()


                # extracting 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
                #compute the extension 
                self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
                # ARDF deflection already comes in m (no Volts)
                self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)

                # save all info the dico 
                self.dict_info["Indentation/Separation (nm)"]= self.extension
                self.dict_raw["Indentation/Separation (nm)"]= self.extension

                self.dict_info["Distance (nm)"]= self.distance
                self.dict_raw["Distance (nm)"]= self.distance

                self.dict_info["Force (pN)"]= self.force
                self.dict_raw["Force (pN)"]= self.force

                self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
                self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

                self.dict_raw["index start approach"]= self.index_start_approach
                self.dict_raw["index end approach"]= self.index_end_approach
                self.dict_raw["index start retract"]= self.index_start_retract
                self.dict_raw["index end retract"]= self.index_end_retract

                self.dict_info["index start approach"]= self.index_start_approach
                self.dict_info["index end approach"]= self.index_end_approach
                self.dict_info["index start retract"]= self.index_start_retract
                self.dict_info["index end retract"]= self.index_end_retract
                self.dict_info["Spring constant (N/m)"]=self.K
                self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6

                # self.x_axis_range_from_entry.delete(0, 'end')
                # self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
                # self.x_axis_range_to_entry.delete(0, 'end')
                # self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))

                self.apply_virtual_deflection_correction()
                self.show_point_contact_approach()
                self.show_point_contact_retract()
                self.correct_point_contact()
                self.noise_level()
            
            # it goes here if all the force curves in the previous ARDF have been checked
            else:
                if (os.path.sep) == "\\" :
                    next_index = self.all_ardf.index(self.directory+ '\\' +self.ardf_file[-1].split( "\\")[-1] ) + 1
                else:
                    next_index = self.all_ardf.index(self.directory + '/' + self.ardf_file[-1]) + 1

                # get the index of the next file on the list
                # next_index= self.all_tdms.index(self.directory+'/'+self.tdms_file[-1])+1
                # if the user gets to the end of the list: go back to first element (index 0)
                if  next_index == len(self.all_ardf):
                    next_index=0
                next_file= self.all_ardf[next_index]
                #get whole path to the selected file
                self.path=  os.path.abspath(self.all_ardf[next_index])
                # get the name of the file
                self.ardf_file= next_file.split('/')
                # show the name of the file on the label of the GUI
                self.label_ardf.config(text=self.ardf_file[-1])


                # Re-initialize variables
                self.current_curve_index = 0  # tracks which curve inside the ARDF
                self.current_file_index += 1   # tracks which ARDF file in folder
                self.point = 0
                self.line = 0
                self.trace = 1

                # File metadata, we get it here so it is not collected for every single force curve of the same ARDF file
                self.file_struct = read_ardf_metadata(self.path)
                self.nlines = self.file_struct['y'].shape[0]
                self.npoints = self.file_struct['y'].shape[1]
                self.all_positions_ardf = []

                for line in range(self.nlines):
                    for point in range(self.npoints):
                        self.all_positions_ardf.append([line, point])

                
                # extract deflection and piezo from file and plot them
                self.get_deflection_vs_piezo()

                # extracting all params, force, distance, etc.
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
                #compute the extension 
                self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
                # ARDF deflection already comes in m (no Volts)
                self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)

                
                # save all info the dico 
                self.dict_info["Indentation/Separation (nm)"]= self.extension
                self.dict_raw["Indentation/Separation (nm)"]= self.extension

                self.dict_info["Distance (nm)"]= self.distance
                self.dict_raw["Distance (nm)"]= self.distance

                self.dict_info["Force (pN)"]= self.force
                self.dict_raw["Force (pN)"]= self.force

                self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
                self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

                self.dict_raw["index start approach"]= self.index_start_approach
                self.dict_raw["index end approach"]= self.index_end_approach
                self.dict_raw["index start retract"]= self.index_start_retract
                self.dict_raw["index end retract"]= self.index_end_retract

                self.dict_info["index start approach"]= self.index_start_approach
                self.dict_info["index end approach"]= self.index_end_approach
                self.dict_info["index start retract"]= self.index_start_retract
                self.dict_info["index end retract"]= self.index_end_retract
                self.dict_info["Spring constant (N/m)"]=self.K
                self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6

                # self.x_axis_range_from_entry.delete(0, 'end')
                # self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
                # self.x_axis_range_to_entry.delete(0, 'end')
                # self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))

                self.apply_virtual_deflection_correction()
                self.show_point_contact_approach()
                self.show_point_contact_retract()
                self.correct_point_contact()
                self.noise_level()
        # plot according to what the user have selected from x-axis and y-axis in the combobox
        self.get_combo_values()
        end = time.perf_counter()
        print(f"Section 2 time: {end - start2:.6f} seconds - NEXT FILE")
            
        
            
        
    def PreviousFile(self):
        """
        When the button 'previous' is pressed, this function is called
        it navigates through the files of directory
        and plot deflection vs piezo

        Returns
        -------
        None.

        """
        # if 'previous' button is pressed: the dico of info is cleaned 
        self.dict_info.clear()
        self.dict_raw.clear()
        if self.combo_file.get() == ".tdms":
            if (os.path.sep) == "\\" :
                prev_index = self.all_tdms.index(self.directory+ '\\' +self.tdms_file[-1].split( "\\")[-1] ) - 1
            else:
                prev_index = self.all_tdms.index(self.directory + '/' + self.tdms_file[-1]) - 1

            # get the index of the previous file
            # prev_index= self.all_tdms.index(self.directory+'/'+self.tdms_file[-1])-1
            # if the index is 0: go back to the end of the list to be able to navigate 
            if  prev_index == -1:
                prev_index=len(self.all_tdms) -1
            prev_file= self.all_tdms[prev_index]
            self.path=  os.path.abspath(prev_file)

            try: 
                self.psnex_file = loadfile(self.path)
                print ('psnex file loaded')
            except: 
                return

            self.tdms_file= self.path.split('/')
            #insert the name in the label on the GUI
            self.label_tdms.config(text=self.tdms_file[-1] )
            
            # get the deflection and the piezo
            self.get_deflection_vs_piezo()
            #loading the parameters from the txt file of the parameters in the same folder as the force curves 
            if self.psnex_file == None:
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms(self.directory, self.channel_data_deflection, self.channel_data_piezo, self.time)
            else: 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell, self.time= tdms.GetForceDistAndParms_psnex(self.path)
            
            # compute the extension
            self.extension= tdms.ComputeExtension(self.force, self.distance, self.K)
            self.channel_data_deflection_nm= tdms.DeflectionInNanometer(self.channel_data_deflection , self.invOLS)
            self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
            self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

            
            # save all info in the dictionary
            self.dict_info["Indentation/Separation (nm)"]= self.extension + max(self.extension)
            self.dict_raw["Indentation/Separation (nm)"]= self.extension + max(self.extension)

            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance

            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force

            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_info["Spring constant (N/m)"]=self.K

            self.apply_virtual_deflection_correction()
            self.show_point_contact_approach()
            self.show_point_contact_retract()
            self.correct_point_contact()    
            self.noise_level()
            
        # if the user wants to load a JPK file
        elif self.combo_file.get() == ".jpk":
            
            current_index = self.all_jpk_files.index(self.jpk_file)
            prev_file_index = (current_index - 1) % len(self.all_jpk_files)
            prev_file= self.all_jpk_files[prev_file_index]
            self.path=  self.directory + '/' + prev_file
            
            #save the name of JPK file after splitting
            self.jpk_file= prev_file

            #insert the name of the file on the GUI
            self.label_jpk.config(text=self.jpk_file)
            # get the deflection vs piezo
            self.get_deflection_vs_piezo()
            #extract parms, force, time...etc
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= JPK.parse_jpk(self.path)
            # save all info in dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity']
            self.invOLS= 1/self.sensitivity
            # self.all_jpk_files.remove(str(prev_file))
        

        elif self.combo_file.get() == ".ibw":
            
            current_index = self.all_ibw_files.index(self.ibw_file)
            prev_file_index = (current_index - 1) % len(self.all_ibw_files)
            prev_file= self.all_ibw_files[prev_file_index]
            self.path=  self.directory + '/' + prev_file
            
            #save the name of JPK file after splitting
            self.ibw_file= prev_file

            #insert the name of the file on the GUI
            self.label_ibw.config(text=self.ibw_file)
            # get the deflection vs piezo
            self.get_deflection_vs_piezo()
            #extract parms, force, time...etc
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= IBW.parse_ibw(self.path)
            # save all info in dico of info
            self.dict_info["Indentation/Separation (nm)"]= self.extension
            self.dict_raw["Indentation/Separation (nm)"]= self.extension
            
            self.dict_info["Distance (nm)"]= self.distance
            self.dict_raw["Distance (nm)"]= self.distance
            
            self.dict_info["Force (pN)"]= self.force
            self.dict_raw["Force (pN)"]= self.force
            
            self.dict_info["index start approach"]= self.index_start_approach
            self.dict_raw["index start approach"]= self.index_start_approach
            
            self.dict_info["index end approach"]= self.index_end_approach
            self.dict_raw["index end approach"]= self.index_end_approach
            
            self.dict_info["index start retract"]= self.index_start_retract
            self.dict_raw["index start retract"]= self.index_start_retract
            
            self.dict_info["index end retract"]= self.index_end_retract
            self.dict_raw["index end retract"]= self.index_end_retract
            
            self.dict_info['time (ms)'] =self.time
            self.dict_raw['time (ms)'] =self.time
            
            self.K= self.parameters['spring constant']
            self.sensitivity= self.parameters['sensitivity']
            self.invOLS= 1/self.sensitivity
            # self.all_jpk_files.remove(str(prev_file))

        elif self.combo_file.get() == ".ARDF":
            # call here the function if the function runs then skip next file, if it doesnt run then go for next file.


            #total_curves_in_current_file = self.nlines * self.npoints
            self.current_curve_index -= 1
            # add while loop to iterate over all the force curves in the same file
            if self.current_curve_index >= 0 :
                self.line, self.point = self.all_positions_ardf[self.current_curve_index]
                            
            
                # extract deflection and piezo from file and plot them
                self.get_deflection_vs_piezo()


                # extracting 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
                #compute the extension 
                self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
                # ARDF deflection already comes in m (no Volts)
                self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)

                # save all info the dico 
                self.dict_info["Indentation/Separation (nm)"]= self.extension
                self.dict_raw["Indentation/Separation (nm)"]= self.extension

                self.dict_info["Distance (nm)"]= self.distance
                self.dict_raw["Distance (nm)"]= self.distance

                self.dict_info["Force (pN)"]= self.force
                self.dict_raw["Force (pN)"]= self.force

                self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
                self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

                self.dict_raw["index start approach"]= self.index_start_approach
                self.dict_raw["index end approach"]= self.index_end_approach
                self.dict_raw["index start retract"]= self.index_start_retract
                self.dict_raw["index end retract"]= self.index_end_retract

                self.dict_info["index start approach"]= self.index_start_approach
                self.dict_info["index end approach"]= self.index_end_approach
                self.dict_info["index start retract"]= self.index_start_retract
                self.dict_info["index end retract"]= self.index_end_retract
                self.dict_info["Spring constant (N/m)"]=self.K
                self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6

                self.x_axis_range_from_entry.delete(0, 'end')
                self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
                self.x_axis_range_to_entry.delete(0, 'end')
                self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))

                self.apply_virtual_deflection_correction()
                self.show_point_contact_approach()
                self.show_point_contact_retract()
                self.correct_point_contact()    
                self.noise_level()
            
            # if self.current_curve_index is -1 then you have to go to the previous file
            else:
                if (os.path.sep) == "\\" :
                    prev_index = self.all_ardf.index(self.directory+ '\\' +self.ardf_file[-1].split( "\\")[-1] ) - 1
                else:
                    prev_index = self.all_ardf.index(self.directory + '/' + self.ardf_file[-1]) - 1

                # get the index of the previous file
                # prev_index= self.all_tdms.index(self.directory+'/'+self.tdms_file[-1])-1
                # if the index is 0: go back to the end of the list to be able to navigate 
                if  prev_index == -1:
                    prev_index=len(self.all_ardf) -1
                prev_file= self.all_ardf[prev_index]
                self.path=  os.path.abspath(prev_file)

                self.ardf_file= self.path.split('/')
                #insert the name in the label on the GUI
                self.label_ardf.config(text=self.ardf_file[-1])


                # File metadata, we get it here so it is not collected for every single force curve of the same ARDF file
                self.file_struct = read_ardf_metadata(self.path)
                self.nlines = self.file_struct['y'].shape[0]
                self.npoints = self.file_struct['y'].shape[1]
                self.all_positions_ardf = []

                for line in range(self.nlines):
                    for point in range(self.npoints):
                        self.all_positions_ardf.append([line, point])
                
                self.line, self.point = self.all_positions_ardf[-1]
                self.trace = 1

                # Re-initialize variables
                self.current_curve_index = len(self.all_positions_ardf)-1  # tracks which curve inside the ARDF
                self.current_file_index -= 1   # tracks which ARDF file in folder

                

                # extract deflection and piezo from file and plot them
                self.get_deflection_vs_piezo()

                # extracting all params, force, distance, etc.
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
                #compute the extension 
                self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
                # ARDF deflection already comes in m (no Volts)
                self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)

                
                # save all info the dico 
                self.dict_info["Indentation/Separation (nm)"]= self.extension
                self.dict_raw["Indentation/Separation (nm)"]= self.extension

                self.dict_info["Distance (nm)"]= self.distance
                self.dict_raw["Distance (nm)"]= self.distance

                self.dict_info["Force (pN)"]= self.force
                self.dict_raw["Force (pN)"]= self.force

                self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
                self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

                self.dict_raw["index start approach"]= self.index_start_approach
                self.dict_raw["index end approach"]= self.index_end_approach
                self.dict_raw["index start retract"]= self.index_start_retract
                self.dict_raw["index end retract"]= self.index_end_retract

                self.dict_info["index start approach"]= self.index_start_approach
                self.dict_info["index end approach"]= self.index_end_approach
                self.dict_info["index start retract"]= self.index_start_retract
                self.dict_info["index end retract"]= self.index_end_retract
                self.dict_info["Spring constant (N/m)"]=self.K

                
                self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6

                self.x_axis_range_from_entry.delete(0, 'end')
                self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
                self.x_axis_range_to_entry.delete(0, 'end')
                self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))

                self.apply_virtual_deflection_correction()
                self.show_point_contact_approach()
                self.show_point_contact_retract()
                self.correct_point_contact()    
                self.noise_level()
        # plot according to what the user selected on x-axis and y-axis
        self.get_combo_values()
        
        
        
    def noise_level(self):
        """
        Noise level via RMS estimation

        Returns
        -------
        None.

        """
        percentage= self.percentage_noise.get()
        self.RMS= NL.get_RMS(self.dict_info["Force (pN)"][ self.dict_info["index start retract"]: self.dict_info["index end retract"]], percentage)  
        self.label_noise.config(text= "RMS:     "+str(self.RMS)+ "  pN"+ "      Set %  here: ")
        
        
    def get_deflection_vs_piezo(self):
        """
        This function extracts the deflection vs piezo , time from both JPK and tdms
        by calling parse_tdms (if it is tdms file) function or parse_jpk (if is JPK file)

        Returns
        -------
        None.

        """

        print ('entered get_deflection_vs_piezo')



        if self.combo_file.get() == ".tdms" and self.psnex_file == None:
            self.channel_data_deflection, self.channel_data_piezo, self.time= tdms.parse_tdms(self.path)

            self.dict_info['time (ms)'] =self.time
            self.dict_info['Piezo (V)'] =self.channel_data_piezo
            self.dict_info['Deflection (V)'] =self.channel_data_deflection
            self.dict_raw['Piezo (V)'] =self.channel_data_piezo
            self.dict_raw['Deflection (V)'] =self.channel_data_deflection

        elif self.combo_file.get() == ".tdms" and self.psnex_file != None:
            self.filetype = app.psnex_file.filemetadata['file_type']
            self.deflectionChannel = app.psnex_file.filemetadata['deflection_chanel_key']
            self.zpiezoChannel = app.psnex_file.filemetadata['height_channel_key']
            self.channel_data_deflection, self.channel_data_piezo, self.time= tdms.parse_tdms(self.path, deflectionChannel=self.deflectionChannel, zpiezo=self.zpiezoChannel)

            self.dict_info['time (ms)'] =self.time
            self.dict_info['Piezo (V)'] =self.channel_data_piezo
            self.dict_info['Deflection (V)'] =self.channel_data_deflection
            self.dict_raw['Piezo (V)'] =self.channel_data_piezo
            self.dict_raw['Deflection (V)'] =self.channel_data_deflection

            

        elif self.combo_file.get() == ".jpk":
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= JPK.parse_jpk(self.path)

        elif self.combo_file.get() == ".ARDF":
            #print(self.point)
            #print(self.line)
            
            self.channel_data_deflection, self.channel_data_piezo, self.time, self.pnt_list = ARDF.parse_ardf(self.path, self.line, self.point, self.trace, self.file_struct)
            
            self.dict_info['time (ms)'] =self.time
            self.dict_info['Piezo (V)'] =self.channel_data_piezo
            self.dict_info['Deflection (V)'] =self.channel_data_deflection
            self.dict_raw['Piezo (V)'] =self.channel_data_piezo
            self.dict_raw['Deflection (V)'] =self.channel_data_deflection

            # Original data
            self.dict_info['Original Deflection (V)'] = self.channel_data_deflection
            self.dict_info['Original Deflection (V)'] = self.channel_data_deflection

            self.dict_info['Original Piezo (V)'] = self.channel_data_piezo
            self.dict_info['Original Piezo (V)'] = self.channel_data_piezo


        
        elif self.combo_file.get() == ".ibw":
            self.force, self.time, self.distance, self.extension, self.parameters, self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract= IBW.parse_ibw(self.path)



    def get_combo_values(self):
        """
        Gets the combobox values selected by the user and plots them

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        widget= canvas.get_tk_widget()

        widget.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)

        toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame)
        ax.grid()
        
        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())
        #if xaxis == "time (ms)":
         #   ax.set_xlim([min(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']]- 50), 
          #              max(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])])
        # if the user wants to plot approach and retract seperatly
        if self.approachOn.get()==1 and self.retractOn.get()==1:
            #print(self.dict_info['index end retract'])
            
            ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                    self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])

            ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                    self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])
            ax.set_xlabel(xaxis)
            ax.set_ylabel(yaxis)
        # if the user wants to plot approach and retract together
        else:
            ax.plot(self.dict_info[xaxis], self.dict_info[yaxis])
            
            ax.set_xlabel(xaxis)
            ax.set_ylabel(yaxis)


    def apply_filter(self):
        """
        Applies and plots the filter

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        start= time.time()
        # get the value from combobox
        # permet de piocher plus facilement dans le dico d'informations
        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())
        # if the user gives a value for the smoothing window
        smoothing_window= self.smoothing_window.get()

        # applying savitzgy-golay filter
        self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']]= tdms.ApplySavgol(self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], smoothing_window )
        #plotting
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                 toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']])
        ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])

        ax.set_xlabel(xaxis)
        ax.set_ylabel(yaxis)


        end= time.time()
        print('smoothing ', round(end-start, 2))

    def get_index_x_axis(self):
        """This function transforms the number in nm entered by the user into an index that can be used
        to plot the desired range. It finds the index of the closest smaller value to the value entered"""
        if self.x_axis_range_nm.get():
            idx = np.searchsorted(self.dict_info['Indentation/Separation (nm)'][self.dict_raw["index start retract"]:self.dict_raw["index end retract"]], float(self.x_axis_range_nm.get()), side='left')
            # move one step back to get the actual smaller value
            idx -= 1
            #if idx < len(self.dict_info['Indentation/Separation (nm)']):
            if idx >= 0:
                
                return idx + self.dict_raw["index start retract"]
                
            else:
                tkinter.messagebox.showinfo('warning' ,'The value provided is out of range')
                #print("The value provided is out of range")

    
        
    def change_parameters(self):
        """
        This function is called when the user changes
        one of the parameters (K (cste spring), sensitivity, invOLS)
        it plots the new curve after the parameters are changed by the user 

        Returns
        -------
        None.

        """
        #plot
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1) 
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                     toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()

        # if the user gives a new invols value
        if self.entry_invols.get():
            self.invOLS= self.entry_invols.get()
            # calculate new disrance and force
            self.dict_info["Distance (nm)"],  self.dict_info["Force (pN)"]= tdms.FDmodifParms(self.channel_data_deflection, self.channel_data_piezo,  self.K, self.invOLS, self.piezo_gain, self.sensitivity)
            self.dict_info["Indentation/Separation (nm)"]= tdms.ComputeExtension(self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"], float(self.K))
            self.dict_info["Indentation/Separation (nm)"]=self.dict_info["Indentation/Separation (nm)"]+max(self.dict_info["Indentation/Separation (nm)"])
        
        # if the user gives a new spring constant 
        if self.entry_k.get():
            self.k= self.entry_k.get()
            #calculate the new values
            self.dict_info["Distance (nm)"],  self.dict_info["Force (pN)"]= tdms.FDmodifParms(self.channel_data_deflection, self.channel_data_piezo,  self.k, self.invOLS, self.piezo_gain, self.sensitivity)
            self.dict_info["Indentation/Separation (nm)"]= tdms.ComputeExtension(self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"], float(self.k))
            self.dict_info["Indentation/Separation (nm)"]= self.dict_info["Indentation/Separation (nm)"]+max(self.dict_info["Indentation/Separation (nm)"])
        
            
        # self.correct_point_contact()
            #self.apply_corrections()


    def correct_virtual_deflection(self):
        """
        Correct the virtual deflection once the user press the button
        the corrected deflection is plotted on the GUI

        Returns
        -------
        None.

        """
        #figure widgets
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1) 
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                     toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())
        # if a polynomial order is set 
        Npoly= self.Npoly.get()
        hysteresis= self.hysteresis.get()
        #if it is tdms file
        if self.combo_file.get() == ".tdms":
            # if the user wants to correct only from approach
            if self.FromApp.get() == 1:
                # if the user gives the % of approach
                if self.pourcentage_approach.get():
                    # get the % of the approach
                    percentage= self.pourcentage_approach.get()
                                        #plot
                    if self.change_invOLS.get()==1 or self.change_K.get()==1:
                        self.change_parameters()
                        self.dict_info["Force (pN)"]= tdms.CorrectVirtualDeflection( self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"],  Npoly,
                                                                                self.dict_info['index start approach'], self.dict_info['index end approach'], 
                                                                                self.dict_info['index start retract'], self.dict_info['index end retract'],
                                                                                percentage,  hysteresis=hysteresis)

                    else:                                         
                        # correct the virtual deflection
                        corrected_deflection= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage, hysteresis=hysteresis )
                        # get the new force after the deflection is corrected
                        distance, force = tdms.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                        self.dict_info['Deflection (nm)']= tdms.DeflectionInNanometer(np.asarray(corrected_deflection, dtype='float64'))
                        # store info in dico
                        self.dict_info['Force (pN)']= force
                        self.dict_info['Deflection (V)']= corrected_deflection
                        # on recupere les vrais valeur pour appliquer les prochaines corrections dessus, pour eviter d'appliquer une correction sur la correction 
                        self.dict_info['Deflection (V)']= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage, hysteresis=-hysteresis )
                        

            # if the user wants to correct the deflection from both retract and approach               
            elif self.FromApp.get() == 0 and  self.pourcentage_retract.get():
                # get the % of retract
                percentage_retract= self.pourcentage_retract.get()
                # get the % of approach
                percentage_approach= self.pourcentage_approach.get()
                
                if self.change_invOLS.get()==1 or self.change_K.get()==1:
                    
                    self.change_parameters()
                    self.dict_info["Force (pN)"]= tdms.CorrectDeflectionFromRetract( self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"],  Npoly,self.dict_info['index start approach'], 
                                                                                    self.dict_info['index end approach'], self.dict_info['index start retract'], self.dict_info['index end retract'], percentage_retract, percentage_approach)
                else:

                    # get corrected deflection
                    corrected_deflection= tdms.CorrectDeflectionFromRetract(self.channel_data_deflection, self.distance,  Npoly, self.index_start_approach, 
                                                                            self.index_end_approach, self.index_start_retract, self.index_end_retract, percentage_retract, percentage_approach)
                    # get the new values of force after the deflection has been corrected 
                    distance, force = tdms.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                    #store the information in dico
                    self.dict_info['Force (pN)']= force
                    self.dict_info['Deflection (V)']= corrected_deflection



        #same for jpk
        elif self.combo_file.get() == ".jpk":
            if self.FromApp.get() == 1:
                if self.pourcentage_approach.get():
                    percentage= self.pourcentage_approach.get()
                    self.corrected_force= tdms.CorrectVirtualDeflection( self.force,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage )
                    self.dict_info['Force (pN)']= self.corrected_force

                    
            elif self.FromApp.get() == 0 and  self.pourcentage_retract.get():
                percentage_retract= self.pourcentage_retract.get()
                percentage_approach= self.pourcentage_approach.get()
                self.corrected_force= tdms.CorrectDeflectionFromRetract(self.force, self.distance,  Npoly, self.index_start_approach, 
                            self.index_end_approach, self.index_start_retract, self.index_end_retract, percentage_retract, percentage_approach)
                
                self.dict_info['Force (pN)']= self.corrected_force
        
        # if the file is ibw
        elif self.combo_file.get() == ".ibw":
            if self.FromApp.get() == 1:
                if self.pourcentage_approach.get():
                    percentage= self.pourcentage_approach.get()
                    self.corrected_force= tdms.CorrectVirtualDeflection( self.force,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage )
                    self.dict_info['Force (pN)']= self.corrected_force

                    
            elif self.FromApp.get() == 0 and  self.pourcentage_retract.get():
                percentage_retract= self.pourcentage_retract.get()
                percentage_approach= self.pourcentage_approach.get()
                self.corrected_force= tdms.CorrectDeflectionFromRetract(self.force, self.distance,  Npoly, self.index_start_approach, 
                            self.index_end_approach, self.index_start_retract, self.index_end_retract, percentage_retract, percentage_approach)
                
                self.dict_info['Force (pN)']= self.corrected_force
                                                     
        
        #start = time.perf_counter()
        # if the file is ARDF
        elif self.combo_file.get() == ".ARDF":
            change_invOLS = self.change_invOLS.get() == 1
            change_K = self.change_K.get() == 1
            change_x_axis = self.change_x_axis.get() == 1
            from_app = self.FromApp.get() == 1

            # if the user wants to correct only from approach
            if from_app:
            #if self.FromApp.get() == 1:
                # if the user gives the % of approach
                if self.pourcentage_approach.get():
                    # get the % of the approach
                    percentage= self.pourcentage_approach.get()
                                        #plot
                    if change_invOLS or change_K:
                    #if self.change_invOLS.get()==1 or self.change_K.get()==1:
                        self.change_parameters()
                        self.dict_info["Force (pN)"]= tdms.CorrectVirtualDeflection( self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"],  Npoly,
                                                                                self.dict_info['index start approach'], self.dict_info['index end approach'], 
                                                                                self.dict_info['index start retract'], self.dict_info['index end retract'],
                                                                                percentage,  hysteresis=hysteresis)
                    
                    elif change_x_axis:
                    #elif self.change_x_axis.get()==1:
                        # next two lines for getting index
                        self.index_start_approach = int(self.x_axis_range_from_entry.get())
                        self.dict_info['index start approach'] = self.index_start_approach
                        self.index_end_retract = int(self.x_axis_range_to_entry.get())
                        self.dict_info['index end retract'] = self.index_end_retract
                        # get_index_x_axis transforms the nm entered by the user into the closest index
                        # self.index_end_retract = self.get_index_x_axis()
                        # self.dict_info['index end retract'] = self.get_index_x_axis()
                        # correct the virtual deflection
                        corrected_deflection= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                     self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                     self.index_end_retract, percentage, hysteresis=hysteresis )
                        # get the new force after the deflection is corrected
                        distance, force = ARDF.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                        self.dict_info['Deflection (nm)']= ARDF.DeflectionInNanometer(np.asarray(corrected_deflection, dtype='float64'))
                        # store info in dico
                        self.dict_info['Force (pN)']= force
                        self.dict_info['Deflection (V)']= corrected_deflection
                        # on recupere les vrais valeur pour appliquer les prochaines corrections dessus, pour eviter d'appliquer une correction sur la correction 
                        self.dict_info['Deflection (V)']= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage, hysteresis=-hysteresis )


                    else:
                        # Recover values
                        # self.index_start_approach = self.dict_raw['index start approach']
                        # self.dict_info['index start approach'] = self.dict_raw['index start approach']
                        # self.index_end_retract = self.dict_raw['index end retract']
                        # self.dict_info['index end retract'] = self.dict_raw['index end retract']                
                        # # correct the virtual deflection
                        print("hello")
                        corrected_deflection= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage, hysteresis=hysteresis )
                        # get the new force after the deflection is corrected
                        distance, force = ARDF.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                        self.dict_info['Deflection (nm)']= ARDF.DeflectionInNanometer(np.asarray(corrected_deflection, dtype='float64'))
                        # store info in dico
                        self.dict_info['Force (pN)']= force
                        self.dict_info['Deflection (V)']= corrected_deflection
                        # on recupere les vrais valeur pour appliquer les prochaines corrections dessus, pour eviter d'appliquer une correction sur la correction 
                        self.dict_info['Deflection (V)']= tdms.CorrectVirtualDeflection( self.channel_data_deflection,
                                    self.distance, Npoly, self.index_start_approach, self.index_end_approach, self.index_start_retract,
                                    self.index_end_retract, percentage, hysteresis=-hysteresis )
                        
                        

            # if the user wants to correct the deflection from both retract and approach               
            elif not from_app and self.pourcentage_retract.get():
            #elif self.FromApp.get() == 0 and  self.pourcentage_retract.get():
                # get the % of retract
                percentage_retract = self.pourcentage_retract.get()
                # get the % of approach
                percentage_approach= self.pourcentage_approach.get()
                
                if change_invOLS or change_K:
                #if self.change_invOLS.get()==1 or self.change_K.get()==1:
                    
                    self.change_parameters()
                    self.dict_info["Force (pN)"]= tdms.CorrectDeflectionFromRetract( self.dict_info["Force (pN)"], self.dict_info["Distance (nm)"],  Npoly,self.dict_info['index start approach'], 
                                                                                    self.dict_info['index end approach'], self.dict_info['index start retract'], self.dict_info['index end retract'], percentage_retract, percentage_approach)
                
                elif change_x_axis:
                #elif self.change_x_axis.get()==1:
                    # next two lines for getting index
                    self.index_start_approach = int(self.x_axis_range_from_entry.get())
                    self.dict_info['index start approach'] = int(self.x_axis_range_from_entry.get())
                    self.index_end_retract = int(self.x_axis_range_to_entry.get())
                    self.dict_info['index end retract'] = int(self.x_axis_range_to_entry.get())
                    # get_index_x_axis transforms the nm entered by the user into the closest index
                    #self.index_end_retract = self.get_index_x_axis()
                    #self.dict_info['index end retract'] = self.get_index_x_axis()
                    corrected_deflection = tdms.CorrectDeflectionFromRetract(self.channel_data_deflection, self.distance,  Npoly, self.index_start_approach , 
                                                                            self.index_end_approach, self.index_start_retract, self.index_end_retract, percentage_retract, percentage_approach)
                    # get the new values of force after the deflection has been corrected 
                    distance, force = ARDF.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                    #store the information in dico
                    self.dict_info['Force (pN)']= force
                    self.dict_info['Deflection (V)']= corrected_deflection
                          

                else:
                    # Recover values
                    # self.index_start_approach = self.dict_raw['index start approach']
                    # self.dict_info['index start approach'] = self.dict_raw['index start approach']
                    # self.index_end_retract = self.dict_raw['index end retract']
                    # self.dict_info['index end retract'] = self.dict_raw['index end retract']                
                        
                    # get corrected deflection
                    corrected_deflection= tdms.CorrectDeflectionFromRetract(self.channel_data_deflection, self.distance,  Npoly, self.dict_raw['index start approach'], 
                                                                            self.index_end_approach, self.index_start_retract, self.dict_raw['index end retract'], percentage_retract, percentage_approach)
                    # get the new values of force after the deflection has been corrected 
                    distance, force = ARDF.FDmodifParms(corrected_deflection, self.channel_data_piezo, self.K, self.invOLS, self.piezo_gain, self.sensitivity)
                    #store the information in dico
                    self.dict_info['Force (pN)']= force
                    self.dict_info['Deflection (V)']= corrected_deflection

        self.get_combo_values()
        self.apply_corrections()

        if self.SmoothingOn.get()==1:
            self.apply_filter()
        
        if self.DetectPeaksOn.get() ==1:
            self.plot_detected_peaks()
        if self.combo_fit_model.get() == "fit WLC":
        #if self.WLCOn.get() == 1:
            self.plot_WLC_model()
            
        if self.combo_fit_model.get()  == "fit FJC":
            self.plot_FJC_model()

        
                
    def apply_virtual_deflection_correction(self):
        """
        Applies the corrections if the needed buttons are checked

        Returns
        -------
        None.

        """
        #start = time.perf_counter()
        if self.widget_main:
            self.widget_main.destroy()
        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1) 
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                     toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        
        #end1 = time.perf_counter()
        #print(f"Execution time: {end1 - start:.6f} seconds - Before correcting deflection")
        if self.CorrectVirtualDeflection.get()==1:
            self.correct_virtual_deflection()
            #end2 = time.perf_counter()
            #print(f"Execution time: {end2 - end1:.6f} seconds - After correcting deflection")
        elif self.CorrectVirtualDeflection.get()==0:

            #print(self.index_start_approach, self.index_end_approach, self.index_start_retract, self.index_end_retract)

            xaxis=  str(self.combo_xaxis.get())
            yaxis= str(self.combo_yaxis.get())
        # if the user wants to plot approach and retract seperatly
            if self.approachOn.get()==1 and self.retractOn.get()==1:
            
                ax.plot(self.dict_raw[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                        self.dict_raw[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])

                ax.plot(self.dict_raw[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                        self.dict_raw[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])
                ax.set_xlabel(xaxis)
                ax.set_ylabel(yaxis)
                # if the user wants to plot approach and retract together
            else:
                ax.plot(self.dict_raw[xaxis], self.dict_raw[yaxis])
                ax.set_xlabel(xaxis)
                ax.set_ylabel(yaxis)
            
        
    def show_point_contact_retract(self):
        """
        Shows the point of contact of the retract curve once the button is pressed 

        Returns
        -------
        None.

        """
        #prepare figure widgets
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
       
        self.widget_main= canvas.get_tk_widget()
        canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1) 
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                     toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())
    
        if self.CpRetractOn.get()==1:
        # get the intersection point with 0
            self.intersection_retract, self.intersection_retract_idx = cp.FindContactPoint(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']]
                                            , self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])
            #print(self.intersection_retract)
            #print(self.intersection_retract_idx)
            
        # plot curves and intersection point
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
            #             self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
                
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
            #                 self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])
        
            # ax.plot(*self.intersection_retract, 'ro', alpha=0.7, ms=10)
        elif self.CpRetractOn.get()==0:
            self.get_combo_values()
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
            #             self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
                
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
            #                 self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])
        
        if self.intersection_retract ==None:
            #tkinter.messagebox.showinfo('warning' ,'No intersection point found')

            self.nextFile()
        ax.set_xlabel(str(xaxis))
        ax.set_ylabel(str(yaxis))

    def show_point_contact_approach(self):
        """
        Shows the point of contact of the approach curve once the button is pressed 

        Returns
        -------
        None.

        """
        #prepare widgets of the figure
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1) 
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                                     toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())
        
        # zero_axis= np.zeros(len(self.dict_info["Deflection (V)"]))
        if self.CpApproachOn.get()==1:
        #get contact point approach
            self.intersection_approach, self.intersection_approach_idx = cp.FindContactPoint(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']][::-1]
                                                            , self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']][::-1])
                                                          
        
        #plot
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
            #                 self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
            #                     self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])

            #ax.plot(*self.intersection_approach, 'ro', alpha=0.7, ms=10)
        elif self.CpApproachOn.get()==0:
            self.get_combo_values()
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
            #                 self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
            # ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
            #                     self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])

        if self.intersection_approach==None:
            self.nextFile()
        
            
        ax.set_xlabel(str(xaxis))
        ax.set_ylabel(str(yaxis))
    
    def correct_point_contact(self):
        """This function corrects the CP
            ==> offset to 0 on the x-axis
        """

        xaxis=  str(self.combo_xaxis.get())
        yaxis= str(self.combo_yaxis.get())

        if self.intersection_approach ==None or self.intersection_retract==None:
            tkinter.messagebox.showinfo('warning' ,'please, start by detecting the contact points of approach and retract')

        else:
            if self.CorrectCP.get()==1:
                self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']]= cp.CorrectContactPoint(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], self.intersection_retract[0])
                if xaxis != "time (ms)":
                    self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']]= cp.CorrectContactPoint(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], self.intersection_approach[0])
                self.get_combo_values()

            elif self.CorrectCP.get()==0:
                self.get_combo_values()

        
    def apply_corrections(self):
        self.show_point_contact_approach()
        self.show_point_contact_retract()
        self.correct_point_contact()

        
        
    def plot_detected_peaks(self):
        """
        plots the peaks

        Returns
        -------
        None.

        """
        #figure widgets
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        ax.set_xlabel("Indentation/Separation (nm)")
        ax.set_ylabel("Force (pN)")
        # get the value of the width set by the user
        w =self.width.get()
        p= self.prominence.get()
        distance= self.range_before_peak.get()

        #renisialize
        try:
            self.dict_info['peaks']
            del self.dict_info['peaks']
        except:
            None


        # try:
        #     self.dict_info['smoothed']
        # except:
        #     self.dict_info['smoothed']=self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']]
            
        # find the peaks
        self.peaks, self.properties= func.find_peaks(self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']],prominence=p)
        # plot
        ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                    self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
        ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                    self.dict_info['Force (pN)'][self.dict_info['index start approach']: self.dict_info['index end approach']])
    
        # if a number of peaks is NOT set
        if not self.N_peaks.get():
            self.dict_info['peaks']= self.peaks

            for i in self.dict_info['peaks']:
                ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i],
                        self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][i],'or')
        
        # if a number of peaks is set: the program takes the higher peaks according to the number set by the user 

        elif self.N_peaks.get():
            N_peaks= self.N_peaks.get()
            list_all_heights=[]
            #get all the heights of the peaks
            for i in range(len(self.properties)):
                for j in range(len(self.properties[i]['peak_heights'])):
                    list_all_heights.append(self.properties[i]['peak_heights'][j])
            #sort the heights
            list_all_heights=sorted(list_all_heights) 
            # keep only last highest peaks according tot the user's number N_peaks
            list_all_heights= list_all_heights[-N_peaks:]
            # get the original index of each peak                
            theset = frozenset(list_all_heights)
            theset = sorted(theset, reverse=True)
            thedict = {}
            n_peaks=[]
            if len(list_all_heights) < N_peaks:
                N_peaks=len(list_all_heights)
                tkinter.messagebox.showinfo('information' ,' Only '+ str(N_peaks) + ' peaks were detected')

            for j in range(N_peaks):
                positions = [i for i, x in enumerate(list_all_heights) if x == theset[j]]
                thedict[theset[j]] = positions
                for i in range(len(self.properties)):
                    #append the heighest peaks in a list
                    n_peaks.append(self.peaks[list(self.properties[i]['peak_heights']).index(theset[j])])
            self.dict_info['peaks']= sorted(n_peaks)
            #plot all peaks
            self.lc_entry.delete('0', 'end')
            for i in self.dict_info['peaks']:
                self.lc_entry.insert(0, str(int(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i]+0.1))+ ', ')
                
                
                ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 
                        self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 'or')
                
                # Plot area under the curve for first peak only
                # if i == self.dict_info['peaks'][0]:
                #     # Get the x value of that peak in the retraction curve
                #     x_peak = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i]

                #     # Find the index in the approach curve whose x-value is closest to x_peak
                #     x_approach = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']]

                #     # Use np.abs + argmin to find the closest match
                #     idx_in_approach = np.argmin(np.abs(x_approach - x_peak))

                #     #start_idx = idx_in_approach
                #     #end_idx = self.dict_info['index start retract'] + i

                #     start_idx = self.dict_info['index end approach'] - self.intersection_approach_idx
                #     end_idx = self.dict_info['index start retract'] + self.intersection_retract_idx
                    

                #     x = self.dict_info["Indentation/Separation (nm)"][start_idx:end_idx]
                #     y = self.dict_info["Force (pN)"][start_idx:end_idx]

                #     ax.fill_between(x, y, color='lightblue', alpha=0.5, label='Adhesion work (1st peak)')

        self.tab_peak_detection.delete(*self.tab_peak_detection.get_children())

        d, self.slope,intercept= func.get_slopes(self.dict_raw["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                            self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']], self.dict_info['peaks'], distance,
                                            self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
        
        for i in range(len(self.dict_info['peaks'])):
            # Previously IDs were assigned randomly
            #self.tab_peak_detection.insert('' ,i ,values=(i+1, "{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]), 
            #                                              "{:.2e}".format(self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]] ), "{:.2e}".format(self.slope[i]*10**3) ))
            # This assigns IDs that correspond with the peak index
            peak_index = self.dict_info['peaks'][i]
            iid = f"peak_{peak_index}"  # ID based on actual data index
            ### insert into tab peak de
            self.tab_peak_detection.insert('', 'end', iid=iid,values=(i + 1,
                "{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][peak_index]),
                "{:.2e}".format(self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][peak_index]),
                "{:.2e}".format(self.slope[i]*10**3)))
            self.tab_peak_detection.grid(row=2, column=0, sticky=W+E+S+N)   
            self.scrollbar.grid(row=2, column=1, sticky="ns")
            
        self.delete_button.grid(row=0, column= 0)

        print('Total time (ms) ', self.dict_info['time (ms)'][-1])
        print('Total extension (nm)', self.dict_raw["Indentation/Separation (nm)"][-1])
        print('Velocity (um/s) ', self.velocity)
        self.dict_info['Velocity (um/s)']= self.velocity
        
        print("Plotted peaks")
        print(self.dict_info['peaks'])

        
        if len(self.dict_info['peaks']) ==  0 and self.JumpOn.get()==1: 
            self.nextFile()
            
  
    
    def plot_WLC_model(self):
        """
        This function fits the WLC model

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()

        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        ax.set_xlabel("Indentation/Separation (nm)")
        ax.set_ylabel("Force (pN)")

        if self.range_before_peak.get()== 0 or len(self.contour_length.get())== 0:
            tkinter.messagebox.showinfo('warning' ,'please, set range before peak and/or contour length')
            
        else:
            
            Lc= self.contour_length.get()
            Lc= Lc[:-2]
            range_before_peak= self.range_before_peak.get()
  

            ax.set_ylim([int(min(self.dict_info["Force (pN)"])), int(max(self.dict_info["Force (pN)"])+100)])
            ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
            ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                self.dict_info["Force (pN)"][self.dict_info['index start approach']: self.dict_info['index end approach']])

            self.ListLc= []
            d={ 'dis1':[], 'disTMP':[], 'dis2':[], 'index_dis2':[]}
            lc= Lc.split(',')
            lc = [ int(x) for x in lc ]
            self.dict_info['peaks']= sorted(self.dict_info['peaks'])

            for i in range(len( self.dict_info['peaks'])):
                # print('extension at peak ', extension[index_start_retract: index_end_retract][i])
                d['dis1'].append(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]])
                #compute selected value = displacement[peak_index]-distance given by the user in nm
            for i in range(len( self.dict_info['peaks'])):
                d['disTMP'].append(d['dis1'][i]- range_before_peak)

                #search for closest value to selected one (selected one is distance before peak)
                d['dis2'].append(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']].flat[np.abs(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] - d['disTMP'][i]).argmin()])
                #put found values in dictionnary of info
                d['index_dis2']= int(list(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(d['dis2'][i]))
                start= d['index_dis2']
                
               # print('fitting start at ', self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start])
                end= self.dict_info['peaks'][i]

                popt, pcov = curve_fit(wlc.WLC, self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start: end] ,
                                    self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][start: end],
                        p0=[self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]+5],

                        bounds=(( self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][0]),
                                (self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][-1])),
                        method='trf') #Algorithm to perform minimization.‘trf’ : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds. Generally robust method.

                self.ListLc.extend(popt)
                
                print('starting  Lc', lc[i],  ' (nm) optimal Lc : ', popt, ' nm')

                y= wlc.WLC(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][0:int(len(self.force)/2)], *popt)
                # intersection of the WLC fitting with the x-axis constant max Force value
                intersection= func.find_intersection(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] 
                                                     ,y)
                if intersection==None:
                    tkinter.messagebox.showinfo('warning' ,'Set a correct contour length value')

                # get the closest value to the intersection point from the extension data to be able to get index later
                close_value_intersection= self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']].flat[np.abs(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] - intersection[0]).argmin()]
                # Get the index of the intersection
                index_intersection= list(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(close_value_intersection)

                
                ax.plot( self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][0: index_intersection],
                        wlc.WLC(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][0: index_intersection], *popt))
                
                for i in self.dict_info['peaks']: 
                    ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 
                        self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 'or')  
                    
                    
    def plot_FJC_model(self):
        """
        This function fits the WLC model

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()

        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        ax.set_xlabel("Indentation/Separation (nm)")
        ax.set_ylabel("Force (pN)")

        if self.range_before_peak.get()== 0 or len(self.contour_length.get())== 0:
            tkinter.messagebox.showinfo('warning' ,'please, set range before peak and/or contour length')
            
        else:
            
            Lc= self.contour_length.get()
            Lc= Lc[:-2]
            range_before_peak= self.range_before_peak.get()
  

            ax.set_ylim([int(min(self.dict_info["Force (pN)"])), int(max(self.dict_info["Force (pN)"])+100)])
            ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
            ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                self.dict_info["Force (pN)"][self.dict_info['index start approach']: self.dict_info['index end approach']])

            self.ListLcFJC= []
            d={ 'dis1':[], 'disTMP':[], 'dis2':[], 'index_dis2':[]}
            lc= Lc.split(',')
            lc = [ int(x) for x in lc ]
            self.dict_info['peaks']= sorted(self.dict_info['peaks'])

            for i in range(len( self.dict_info['peaks'])):
                # print('extension at peak ', extension[index_start_retract: index_end_retract][i])
                d['dis1'].append(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]])
                #compute selected value = displacement[peak_index]-distance given by the user in nm
            for i in range(len( self.dict_info['peaks'])):
                d['disTMP'].append(d['dis1'][i]- range_before_peak)

                #search for closest value to selected one (selected one is distance before peak)
                d['dis2'].append(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']].flat[np.abs(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] - d['disTMP'][i]).argmin()])
                #put found values in dictionnary of info
                d['index_dis2']= int(list(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(d['dis2'][i]))
                start= d['index_dis2']
                
               # print('fitting start at ', self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start])
                end= self.dict_info['peaks'][i]
                popt, pcov = curve_fit(wlc.WLC, self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start: end] , 
                                   self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][start: end],
                       p0=[lc[i]], 
                       bounds=((lc[i]), (start*10)),
                       method='trf') #Algorithm to perform minimization.‘trf’ : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds. Generally robust method.
                self.ListLcFJC.extend(popt)

                
                print('starting  Lc', lc[i],  ' (nm) optimal Lc : ', popt, ' nm')

                y= fjc.FJC(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][0:int(len(self.force)/2)], *popt)
                # intersection of the WLC fitting with the x-axis constant max Force value
                #intersection= func.find_intersection(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] 
                 #                                    ,y)
                #if intersection==None:
                 #   tkinter.messagebox.showinfo('warning' ,'Set a correct contour length value')

                # get the closest value to the intersection point from the extension data to be able to get index later
                #close_value_intersection= self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']].flat[np.abs(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] - intersection[0]).argmin()]
                # Get the index of the intersection
                #index_intersection= list(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(close_value_intersection)

                
                ax.plot( self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start: end ],
                        fjc.FJC(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][start : end], *popt))
                
                for i in self.dict_info['peaks']: 
                    ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 
                        self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][i], 'or')
 
    def plot_FcLc(self):
        """
        This functions shows the Force vs Contour length
        Fc: force in pN
        Lc: contour length i nm 

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        ax.set_xlabel("Contour Length (nm)")
        ax.set_ylabel("Force (pN)")
        self.dict_info['Contour Length (nm)'], self.dict_info['Fc (pN)']= Lc.FindLc(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']] , self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])

        w= self.width.get()
        p= self.prominence.get()
        number_wanted_peaks= self.N_peaks.get()
        d= { 'Fc': self.dict_info['Fc (pN)'], 'Lc':self.dict_info['Contour Length (nm)']}
        df = pd.DataFrame(data=d)
        df = df.dropna()
        if self.threshold.get() :
            df['Fc']= df[df['Fc'] > self.threshold.get()]

        self.dict_info['Contour Length (nm)']=np.array(df['Lc'])
        self.dict_info['Fc (pN)']= np.array(df['Fc'])
        peaks, properties= find_peaks(self.dict_info['Fc (pN)'],  prominence=p, width=w )
        n_peaks= Lc.return_highest_peaks(properties, peaks, number_wanted_peaks )
        for i in n_peaks:
            ax.plot(self.dict_info['Contour Length (nm)'][i],self.dict_info['Fc (pN)'][i], 'or' )
        self.dict_info["Force (pN)"]= np.array(self.dict_info["Force (pN)"])
        closest=[]
        self.idx_peaks_2nd_detection=[]
        for i in n_peaks:
            #find closest value to the max force in Lc vs force profile in force dataset
            closest.append(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']].flat[np.abs(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']] - self.dict_info['Fc (pN)'][i]).argmin()])

        for i in range(len(closest)):
            self.idx_peaks_2nd_detection.append(int(list(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(closest[i])))
        ax.scatter(self.dict_info['Contour Length (nm)'], self.dict_info['Fc (pN)'])
    
    def plot_loading_rate(self):
        """
        This function plots the loading rates

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)
        ax=figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()
        ax.grid()
        distance= self.range_before_peak.get()
        
        # self.intersection_time= cp.FindContactPoint(self.dict_info['time (ms)'], self.dict_info['Deflection (V)'])
        # self.dict_info['time (ms)']= cp.CorrectContactPoint(self.dict_info['time (ms)'], self.intersection_time[0])
        
        dico_peaks, self.slope,intercept= func.get_slopes(self.dict_raw["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                            self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']], self.dict_info['peaks'], distance,
                                            self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        
        ax.plot(self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        # ax.plot(self.dict_info["time (ms)"][self.dict_info['index start approach']: self.dict_info['index end approach']], self.dict_info["Force (pN)"][self.dict_info['index start approach']: self.dict_info['index end approach']])


        for i in range(len(dico_peaks['peaks'])):
            # print(dico_peaks)
            ax.plot(self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']][dico_peaks['index_dis2'][i]:dico_peaks['peaks'][i]], 
                    self.slope[i]*np.array(self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']][dico_peaks['index_dis2'][i]:dico_peaks['peaks'][i]])+intercept[i],'r')
            # print('Peak '+str(i+1)+ '  '+'Loading Rate '+ str(self.slope[i]*10**3), ' (pN/s)')

        # self.apply_corrections()
        ax.set_xlabel("time (ms)")
        ax.set_ylabel("Force (pN)")

    def plot_peak_FcLc(self):
        """
        plots the force vs contour length profile

        Returns
        -------
        None.

        """
        if self.widget_main:
            self.widget_main.destroy()

        if self.toolbar_main:
            self.toolbar_main.destroy()
        figure = Figure(figsize=(7,5), dpi=100)

        ax=figure.add_subplot(111)

        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()

        self.widget_main= canvas.get_tk_widget()
        self.widget_main.grid(row=8, column=1)

        
        # navigation toolbar
        toolbarFrame = Frame(master= self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        self.toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame) 
        self.toolbar_main.update()


        ax.grid()

        try:
            self.dict_info['Contour Length (nm)']
            self.dict_info['Fc (pN)']
        except:
            tkinter.messagebox.showinfo('warning' ,'please, Click plot Fc vs Lc first') 
            
        
        ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                 self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])
        ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                 self.dict_info["Force (pN)"][self.dict_info['index start approach']: self.dict_info['index end approach']])

        #plot it
        for i in self.idx_peaks_2nd_detection:
            ax.plot(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i],
                self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i],
                'or')

        for i in range(len(self.idx_peaks_2nd_detection)): 
           
            if self.idx_peaks_2nd_detection[i] not in self.dict_info['peaks']:
                
                self.tab_peak_detection.insert('' ,i ,values=(i+1, "{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.idx_peaks_2nd_detection[i]]), "{:.2e}".format(self.dict_info['Force (pN)'][self.dict_info['index start retract']: self.dict_info['index end retract']][self.idx_peaks_2nd_detection[i]] ) ))
                
                self.dict_info['peaks'].append(self.idx_peaks_2nd_detection[i])
            
            self.tab_peak_detection.grid(row=2, column=0, sticky=W+E+S+N)   
            self.scrollbar.grid(row=2, column=1, sticky="ns")

        

        ax.set_xlabel("Indentation/Separation (nm)")
        ax.set_ylabel("Force (pN)")
        
    def delete_peaks(self):
        """
        This function deletes the peak selected by the user
        from the total list of peaks

        Returns
        -------
        None.

        """
        # curItem= self.tab_peak_detection.selection()
        # curItems = [(self.tab_peak_detection.item(i)['values']) for i in curItem]
 
        # indentation= []
        # selected_items = self.tab_peak_detection.selection()
        # This will be used later for the params export file
        # self.export_selected_items = selected_items
        # #print(self.export_selected_items)
        # for i in self.dict_info["peaks"]: 
        #     indentation.append("{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][i]))
        
        # for selected_item in selected_items:  
        #     self.tab_peak_detection.delete(selected_item)
           
        # print("indentation", indentation)
        # for i in curItems:
        #     print(i)
        #     if i[1] in indentation:
        #         print("habemus problem")
        #         index_peak= indentation.index(i[1])
        #         indentation.remove(i[1])
                
        #         self.dict_info["peaks"].pop(index_peak)
        # #print("After deleting peaks")
        # #print(self.dict_info['peaks'])

        selected_items = self.tab_peak_detection.selection()
        # This will be used later for the params export file
        self.export_selected_items = selected_items  # for later export, if needed

        #print("Selected Treeview items:", selected_items)

        # Extract peak indices from Treeview item IDs like "peak_707"
        selected_peak_indices = []
        for item_id in selected_items:
            try:
                peak_index = int(item_id.replace("peak_", ""))
                selected_peak_indices.append(peak_index)
            except ValueError:
                print(f"Warning: Cannot parse peak index from item ID {item_id}")

        # Delete the selected items from the Treeview
        for item_id in selected_items:
            self.tab_peak_detection.delete(item_id)

        print("Selected peak indices to remove:", selected_peak_indices)
        print("Original peaks list:", self.dict_info["peaks"])

        # Remove the corresponding peak indices from self.dict_info['peaks']
        self.dict_info["peaks"] = [i for i in self.dict_info["peaks"] if i not in selected_peak_indices]

        print("Updated peaks list:", self.dict_info["peaks"])
        

    def export_data(self):
        """
        This function exports the data

        Returns
        -------
        None.

        """
        try:
            self.ListLc
            self.ListLc=sorted(self.ListLc)
        except:
            self.ListLc=None

        self.dict_info['peaks']= sorted(self.dict_info['peaks'])
        
        distance=self.range_before_peak.get()
        d= {'file name': '', 'rupt number':[], 'rupt force (pN)':[], 'rupt time (s)':[], 'rupt sep (nm)':[], 'keff (pN/nm)':[], 'veff (nm/s)':[], 'loading rate (pN/s)':[],
            'vBwd_exp (nm/s)':[], 'peak work (pN* nm)':[], 'cumulative peak work (pN* nm)':[], 'incremental peak work (pN* nm)':[]
            }
        
        params_d = {'file name': '', 'from approach':'', 'from both':'', 'ap_percentage':'', 'ret_percentage':'', 'N_poly':'', 'apply_filter':'', 'filter':'', 'change_K':'', 'k spring':'', 'change_invOLS':'', 'invOLS':'',
                    'x_axis_change':'', 'from':'', 'to':'', 'detect peaks':'', 'deleted peak index':'', 'number of peaks':'', 'prominence':'',}
        #d= dict(self.dict_info)


        # Collect params info
        
        if self.FromApp.get() == 1:
            params_d['from approach'] = 1
            params_d['from both'] = 0
            params_d['ap_percentage'] = self.pourcentage_approach.get()
            params_d['ret_percentage'] = 0
        else:
            params_d['from approach'] = 0
            params_d['from both'] = 1
            params_d['ap_percentage'] = self.pourcentage_approach.get()
            params_d['ret_percentage'] = self.pourcentage_retract.get()

        params_d['N_poly'] = self.Npoly.get()

        params_d['apply_filter'] = self.SmoothingOn.get()
        params_d['filter'] = self.smoothing_window.get()

        params_d['change_K'] = self.change_K.get()
        params_d['change_invOLS'] = self.change_invOLS.get()
        params_d['k spring'] = self.K
        params_d['invOLS'] = self.invOLS

        params_d['x_axis_change'] = self.change_x_axis.get()
        params_d['from']=  int(self.x_axis_range_from_entry.get())
        params_d['to'] = int(self.x_axis_range_to_entry.get())

        params_d['detect peaks'] = self.DetectPeaksOn.get()
        if self.export_selected_items:
            params_d['deleted peak index'] = ",".join(str(item) for item in self.export_selected_items)
            self.export_selected_items = ''
        else:
            params_d['deleted peak index'] = 0
        params_d['number of peaks'] = self.N_peaks.get()
        params_d['prominence'] = self.prominence.get()


        all_decimals_peak_work = []
        for i in range(len(self.dict_info['peaks'])):
            d['rupt number'].append(i+1)
            
            
            d['peak work (pN* nm)'].append(xp.integration(0,
                           self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]],
                           len(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])))
            

            # Total adhesion work calculation
            # We need to get the perpendicular point in the approach curve
            # Get the x value of that peak in the retraction curve
            x_peak = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]
            # Find the index in the approach curve whose x-value is closest to x_peak
            x_approach = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']]
            idx_in_approach = np.argmin(np.abs(x_approach - x_peak))

            approach_peak_work = np.trapezoid(self.dict_info["Force (pN)"][idx_in_approach: self.dict_info['index end approach']-self.intersection_approach_idx],
                                                        self.dict_info["Indentation/Separation (nm)"][idx_in_approach: self.dict_info['index end approach']-self.intersection_approach_idx])


            retract_peak_work = np.trapezoid(self.dict_info["Force (pN)"][self.dict_info['index start retract'] + self.intersection_retract_idx: self.dict_info['index start retract']+self.dict_info['peaks'][i]],
                                                          self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract'] + self.intersection_retract_idx: self.dict_info['index start retract']+self.dict_info['peaks'][i]])

            total_peak_work = retract_peak_work - abs(approach_peak_work)

            all_decimals_peak_work.append(total_peak_work)


            if i == 0:
                d['cumulative peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
                d['incremental peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
            else:
                d['cumulative peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
                d['incremental peak work (pN* nm)'].append("{:.2e}".format(total_peak_work-all_decimals_peak_work[i-1]))

            
                                                                        

            figure = Figure(figsize=(7,5), dpi=100)
            ax=figure.add_subplot(111)
            canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
            canvas.draw()
            widget= canvas.get_tk_widget()

            widget.grid(row=8, column=1)
            # navigation toolbar
            toolbarFrame = Frame(master= self.subframe_plots)
            toolbarFrame.grid(row=11,column=1)

            toolbar_main = NavigationToolbar2Tk(canvas, 
                                           toolbarFrame)
            ax.grid()
        
            xaxis=  str(self.combo_xaxis.get())
            yaxis= str(self.combo_yaxis.get())
            # if the user wants to plot approach and retract seperatly
            if self.approachOn.get()==1 and self.retractOn.get()==1:
                #print(self.dict_info['index end retract'])
            
                ax.plot(self.dict_info[xaxis][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                        self.dict_info[yaxis][self.dict_info['index start retract']: self.dict_info['index end retract']])

                ax.plot(self.dict_info[xaxis][self.dict_info['index start approach']: self.dict_info['index end approach']], 
                        self.dict_info[yaxis][self.dict_info['index start approach']: self.dict_info['index end approach']])
                ax.set_xlabel(xaxis)
                ax.set_ylabel(yaxis)
            # if the user wants to plot approach and retract together
            else:
                ax.plot(self.dict_info[xaxis], self.dict_info[yaxis])
            
                ax.set_xlabel(xaxis)
                ax.set_ylabel(yaxis)

        #try:
        #   self.tdms_file
        #   file= tdms_file
        #except:
        #   self.jpk_file
        #   file= self.jpk_file

        try:
            file = self.tdms_file
        except:
            try:
                file = self.jpk_file
            except:
                try:
                    file = self.ardf_file[-1]
                except AttributeError:
                    raise ValueError("No valid file found to export.")

        
        # d['file name']= str( file )
        num_peaks = len(d['rupt number'])
        d['file name'] = [str(file)] * num_peaks
        params_d['file name'] = [str(file)]
        

        # Keeping track of the line and point in ARDF files
        if self.combo_file.get() == ".ARDF":
            d['file name'] = [str(file)+"_L"+str(self.line)+"_P"+str(self.point)] * num_peaks
            params_d['file name'] = [str(file)+"_L"+str(self.line)+"_P"+str(self.point)]

        d['invOLS (nm/V)'] = ["{:.2e}".format(self.invOLS)]

        d['Zsens (nm/V)']="{:.2e}".format(self.sensitivity)
        


        # d['Lc (nm)']=["{:.2e}".format(float(i)) for i in self.ListLc]
        
        
        d['keff (pN/nm)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info['peaks'], 
                                              self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              distance)[0])
        
        
        d['veff (nm/s)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info['peaks'], 
                                              self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              distance)[1])
        
        
        d['vBwd_exp (nm/s)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info['peaks'], 
                                              self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              distance)[4])     
        
        d['keff (pN/nm)']= ["{:.2e}".format(i) for i in d['keff (pN/nm)']]
        d['veff (nm/s)']= ["{:.2e}".format(i) for i in d['veff (nm/s)']]
        d['vBwd_exp (nm/s)']= ["{:.2e}".format(i) for i in d['vBwd_exp (nm/s)']]
        
        
        # trigger thres is mininmum of force after point of contact
        d['trigger thres (pN)']= min(self.dict_info["Force (pN)"])
        
        for i in range(len(self.dict_info['peaks'])):
            d['loading rate (pN/s)'].append("{:.2e}".format(self.slope[i]*10**3))
            d['rupt force (pN)'].append("{:.2e}".format(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]))
            d['rupt sep (nm)'].append("{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]))
            d['rupt time (s)'].append("{:.2e}".format(self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]*10**-3))

        print('Break')
        d['indentation (nm)']=[ min(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']])]
        # index_min_force= list(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']]).index(d['trigger thres (pN)'])
        
        # d['indentation (nm)'] =["{:.2e}".format( abs(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][index_min_force]))]
                        
        
        
        # d['kcanti (pN/nm)']= "{:.2e}".format(self.K*10**12*10**-9)
        d['vBwd (nm/s)']= ["{:.2e}".format(self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][-1]/ (self.dict_info["time (ms)"][-1]*10**-3))]
        
        # d['trigger thres (pN)']="{:.2e}".format( min(self.dict_info["Force (pN)"]))
        # d['dwell time (s)']= "{:.2e}".format(self.dwell*10**-3)
        
        d['Zsens (nm/V)'] = ["{:.2e}".format(self.sensitivity)]
        d['kcanti (pN/nm)'] = ["{:.2e}".format(self.K * 10**12 * 10**-9)]
        d['trigger thres (pN)'] = ["{:.2e}".format(min(self.dict_info["Force (pN)"]))]
        
        #for TDMS
        # d['dwell time (s)'] = ["{:.2e}".format(self.dwell * 10**-3)]


        for key, value in d.items():
            print(f"{key}: {len(value)}")
            
        

        df = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in d.items() ]))
        # df = pd.DataFrame.from_dict(d)
        params_df = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in params_d.items() ]))


        if self.export_file_path is None:
            self.export_file_path = filedialog.asksaveasfilename(defaultextension='.csv')
            self.export_params_file_path = self.export_file_path[:-4] + "_params.csv"
            if not self.export_file_path:
                print("Export canceled.")
                return

        # Check if file already exists to decide whether to write headers
        file_exists = os.path.isfile(self.export_file_path)

        df.to_csv(self.export_file_path, sep='\t', header=not file_exists, index=False, mode='a')
        print(f"Data exported to {self.export_file_path}")

        # Writing the params file
        params_file_exists = os.path.isfile(self.export_params_file_path)
        params_df.to_csv(self.export_params_file_path, sep='\t', header=not params_file_exists, index=False, mode='a')
        print(f"Data exported to {self.export_params_file_path}")


    def automatic_analysis(self):
        """This function analyses data automatically if a params file is provided"""
          
        # Read params file
        params_file_path = filedialog.askopenfilename(title="Select parameter file",
                                                      filetypes=[("CSV files", "*.csv"), ("TSV files", "*.tsv"), ("All files", "*.*")])

        # If a file was selected, read it
        if params_file_path:
            params_df = pd.read_csv(params_file_path, sep="\t")
            print("Parameters loaded:")
            print(params_df.head())
        else:
            print("No file selected. Analysis aborted.")
            return
        
        if self.export_file_path is None:
            self.export_file_path = filedialog.asksaveasfilename(defaultextension='.csv',
                                                                             title="Choose a name for the output file")
                        
            if not self.export_file_path:
                print("No file name given. Analysis aborted.")
                return


        # Now you can access parameters by column names (from the header)
        for index, row in params_df.iterrows():
            self.dict_info.clear()
            self.dict_raw = {}
            self.dict_info['peaks'] = {}
            self.slope = []

            # Reset variables
            #self.FromApp.set(0)
            #self.SmoothingOn.set(0)
            #self.change_K.set(0)
            #self.change_invOLS.set(0)
            #self.change_x_axis.set(0)
            #self.DetectPeaksOn.set(0)
         
            if self.combo_file.get() == ".ARDF":
                file_name = row["file name"].split(".")[0]
                self.line = int(row["file name"].split("_")[1][1:])
                self.point = int(row["file name"].split("_")[2][1:])
                self.trace = 1

                # File metadata, we get it here so it is not collected for every single force curve of the same ARDF file
                # Maybe should only do this once for each file, CORRECT LATER
                self.path = Path(self.path).parent / (file_name + ".ARDF")
                self.file_struct = read_ardf_metadata(self.path)

                self.get_deflection_vs_piezo()

                # loading the parameters from the txt file of the parameters in the same folder as the force curves 
                # extracting 
                self.distance, self.force, self.K, self.invOLS, self.sensitivity, self.piezo_gain , self.index_end_approach, self.index_start_approach, self.index_start_retract, self.index_end_retract, self.dwell = ARDF.get_force_and_params_ardf(self.file_struct, self.channel_data_deflection, self.channel_data_piezo, self.pnt_list)
                # compute the extension 
                self.extension= ARDF.ComputeExtension(self.force, self.distance, self.K)
                # ARDF deflection already comes in m (no Volts)
                self.channel_data_deflection_nm= ARDF.DeflectionInNanometer(self.channel_data_deflection)
                self.dict_info["Deflection (nm)"]= self.channel_data_deflection_nm
                self.dict_raw["Deflection (nm)"]= self.channel_data_deflection_nm

                # offset and save the extension in a dictionary that contains all important info
                # self.dict_info["Indentation/Separation (nm)"]= self.extension + max(self.extension)
                self.dict_info["Indentation/Separation (nm)"]= self.extension
                #print(self.dict_info["Indentation/Separation (nm)"][0:10])
                #self.dict_raw["Indentation/Separation (nm)"]= self.extension + max(self.extension)
                self.dict_raw["Indentation/Separation (nm)"]= self.extension
                # offset and save the distance in nm in the dictionnary of info
                # self.dict_info["Distance (nm)"]= self.distance + max(self.distance)
                # self.dict_raw["Distance (nm)"]= self.distance + max(self.distance)
                self.dict_info["Distance (nm)"]= self.distance
                self.dict_raw["Distance (nm)"]= self.distance
                # save the force in pN in the dictionnary of info
                self.dict_info["Force (pN)"]= self.force
                self.dict_raw["Force (pN)"]= self.force
                
                self.dict_raw["index start approach"]= self.index_start_approach
                self.dict_raw["index end approach"]= self.index_end_approach
                self.dict_raw["index start retract"]= self.index_start_retract
                self.dict_raw["index end retract"]= self.index_end_retract
                # save the index of the start of the approach
                self.dict_info["index start approach"]= self.index_start_approach
                # save the inddex of the end of the approach
                self.dict_info["index end approach"]= self.index_end_approach
                # save the index of the start of the retract
                self.dict_info["index start retract"]= self.index_start_retract
                # save the index of the end of the retract 
                self.dict_info["index end retract"]= self.index_end_retract
                self.dict_info["Spring constant (N/m)"]= self.K
                self.velocity= float(self.file_struct['Notes']['RetractVelocity']) * 10**6

                # self.x_axis_range_from_entry.delete(0, 'end')
                # self.x_axis_range_from_entry.insert(0, str(self.index_start_approach))
                # self.x_axis_range_to_entry.delete(0, 'end')
                # self.x_axis_range_to_entry.insert(0, str(self.index_end_retract))
                try:
                    self.apply_virtual_deflection_correction()
                    self.show_point_contact_approach()
                    self.show_point_contact_retract()
                    self.correct_point_contact()
                except Exception as e:
                    print("An error occurred:", e)

                # self.apply_virtual_deflection_correction()
                # self.show_point_contact_approach()
                # self.show_point_contact_retract()
                # self.correct_point_contact()
            
                # Load parameters from file
                # Fill tkinter variables first
                self.FromApp.set(row['from approach'])

                #self.pourcentage_approach = IntVar()
                self.pourcentage_approach.set(row['ap_percentage'])
                
                #self.pourcentage_retract = IntVar()
                self.pourcentage_retract.set(row['ret_percentage'])

                self.Npoly.set(row['N_poly'])

                #self.SmoothingOn = IntVar()
                self.SmoothingOn.set(row['apply_filter'])

                #self.smoothing_window = IntVar()
                self.smoothing_window.set(row['filter'])

                #self.change_K = IntVar()
                self.change_K.set(row['change_K'])

                #self.change_invOLS = IntVar()
                self.change_invOLS.set(row['change_invOLS'])

                if self.change_invOLS == 1:
                    self.entry_invols.set(row['invOLS'])
                else:
                    self.invOLS = row['invOLS']

                if self.change_K == 1:
                    self.entry_k.set(row['k spring'])
                else:
                    self.K = row['k spring']


                #self.change_x_axis = IntVar()
                self.change_x_axis.set(row['x_axis_change'])
                
                self.x_axis_range_from_entry = IntVar()
                #self.x_axis_range_from_entry.insert(0, str(row['from']))
                self.x_axis_range_from_entry.set(row['from'])

                self.x_axis_range_to_entry = IntVar()
                #self.x_axis_range_to_entry.insert(0, str(row['to']))
                self.x_axis_range_to_entry.set(row['to'])
               
                
                #self.DetectPeakOn = IntVar()
                self.DetectPeaksOn.set(row['detect peaks'])

                self.export_selected_items = tuple(item.strip() for item in str(row['deleted peak index']).split(",") if item.strip())
                #self.N_peaks = IntVar()
                self.N_peaks.set(row['number of peaks'])
                #self.prominence = IntVar()
                self.prominence.set(row['prominence'])
                
                # Perform last operations
                self.apply_virtual_deflection_correction()
                # self.show_point_contact_approach()
                # self.show_point_contact_retract()
                # self.correct_point_contact()



                if self.export_selected_items[0] != "0":
                    #print("Currently available Treeview items:", self.tab_peak_detection.get_children())
                    #print("Items to select:", self.export_selected_items)

                    #print(self.export_selected_items)
                    print(row["file name"])
                    self.tab_peak_detection.selection_set(self.export_selected_items)
                    #print(self.tab_peak_detection.selection())
                    self.delete_peaks()
                    #print(self.dict_info["peaks"])


                # Export results
                self.dict_info['peaks']= sorted(self.dict_info['peaks'])
        
                distance=self.range_before_peak.get()
                d= {'file name': '', 'rupt number':[], 'rupt force (pN)':[], 'rupt time (s)':[], 'rupt sep (nm)':[], 'keff (pN/nm)':[], 'veff (nm/s)':[], 'loading rate (pN/s)':[],
                    'vBwd_exp (nm/s)':[], 'peak work (pN* nm)':[], 'cumulative peak work (pN* nm)':[], 'incremental peak work (pN* nm)':[]
                    }
                
                all_decimals_peak_work = []
                for i in range(len(self.dict_info['peaks'])):
                    d['rupt number'].append(i+1)
                    
                    
                    d['peak work (pN* nm)'].append(xp.integration(0,
                                self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]],
                                len(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']])))
                    

                    # Total adhesion work calculation
                    # We need to get the perpendicular point in the approach curve
                    # Get the x value of that peak in the retraction curve
                    x_peak = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]
                    # Find the index in the approach curve whose x-value is closest to x_peak
                    x_approach = self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start approach']: self.dict_info['index end approach']]
                    idx_in_approach = np.argmin(np.abs(x_approach - x_peak))

                    approach_peak_work = np.trapezoid(self.dict_info["Force (pN)"][idx_in_approach: self.dict_info['index end approach']-self.intersection_approach_idx],
                                                                self.dict_info["Indentation/Separation (nm)"][idx_in_approach: self.dict_info['index end approach']-self.intersection_approach_idx])


                    retract_peak_work = np.trapezoid(self.dict_info["Force (pN)"][self.dict_info['index start retract'] + self.intersection_retract_idx: self.dict_info['index start retract']+self.dict_info['peaks'][i]],
                                                                self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract'] + self.intersection_retract_idx: self.dict_info['index start retract']+self.dict_info['peaks'][i]])

                    total_peak_work = retract_peak_work - abs(approach_peak_work)

                    all_decimals_peak_work.append(total_peak_work)

                    if i == 0:
                        d['cumulative peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
                        d['incremental peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
                    else:
                        d['cumulative peak work (pN* nm)'].append("{:.2e}".format(total_peak_work))
                        d['incremental peak work (pN* nm)'].append("{:.2e}".format(total_peak_work-all_decimals_peak_work[i-1]))


                    # d['file name']= str( file )
                num_peaks = len(d['rupt number'])
                d['file name'] = [str(file_name) + ".ARDF"] * num_peaks
                    

                # Keeping track of the line and point in ARDF files
                if self.combo_file.get() == ".ARDF":
                    d['file name'] = [str(file_name)+ ".ARDF"+"_L"+str(self.line)+"_P"+str(self.point)] * num_peaks
                       
                d['invOLS (nm/V)'] = ["{:.2e}".format(self.invOLS)]

                d['Zsens (nm/V)']="{:.2e}".format(self.sensitivity)

                d['keff (pN/nm)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info['peaks'], 
                                              self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              distance)[0])
        
        
                d['veff (nm/s)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                                    self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                                    # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                                    self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                                    self.dict_info['peaks'], 
                                                    self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                                    distance)[1])
                d['vBwd_exp (nm/s)'].extend(xp.get_keff_veff_vBwd_exp_jpk(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              # self.dict_info["Deflection (V)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']], 
                                              self.dict_info['peaks'], 
                                              self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']],
                                              distance)[4])
                    
                d['keff (pN/nm)']= ["{:.2e}".format(i) for i in d['keff (pN/nm)']]
                d['veff (nm/s)']= ["{:.2e}".format(i) for i in d['veff (nm/s)']]
                d['vBwd_exp (nm/s)']= ["{:.2e}".format(i) for i in d['vBwd_exp (nm/s)']]


                # trigger thres is mininmum of force after point of contact
                d['trigger thres (pN)']= min(self.dict_info["Force (pN)"])
                    
                for i in range(len(self.dict_info['peaks'])):
                    d['loading rate (pN/s)'].append("{:.2e}".format(self.slope[i]*10**3))
                    d['rupt force (pN)'].append("{:.2e}".format(self.dict_info["Force (pN)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]))
                    d['rupt sep (nm)'].append("{:.2e}".format(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]))
                    d['rupt time (s)'].append("{:.2e}".format(self.dict_info["time (ms)"][self.dict_info['index start retract']: self.dict_info['index end retract']][self.dict_info['peaks'][i]]*10**-3))
                

                
                d['indentation (nm)']=[ min(self.dict_info["Indentation/Separation (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']])]
                
                d['vBwd (nm/s)']= ["{:.2e}".format(self.dict_info["Distance (nm)"][self.dict_info['index start retract']: self.dict_info['index end retract']][-1]/ (self.dict_info["time (ms)"][-1]*10**-3))]
                    
                d['Zsens (nm/V)'] = ["{:.2e}".format(self.sensitivity)]
                d['kcanti (pN/nm)'] = ["{:.2e}".format(self.K * 10**12 * 10**-9)]
                d['trigger thres (pN)'] = ["{:.2e}".format(min(self.dict_info["Force (pN)"]))]
                df = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in d.items() ]))
                    
                
                    

                # Check if file already exists to decide whether to write headers
                file_exists = os.path.isfile(self.export_file_path)

                df.to_csv(self.export_file_path, sep='\t', header=not file_exists, index=False, mode='a')
                print(f"Data exported to {self.export_file_path}")

              
                                            




    




app = App()

app.window.mainloop()
