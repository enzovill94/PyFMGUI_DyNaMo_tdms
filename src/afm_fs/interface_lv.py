import tkinter.messagebox
from tkinter import *
from tkinter import filedialog, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import os
import numpy as np
import pandas as pd

# --- Import your custom modules ---
import parse_tdms_new as tdms
import parse_jpk as JPK
import parse_ARDF as ARDF
import parse_ibw as IBW
from pyfmreader import loadfile
import contact_point as cp
import functions as func
import WLC as wlc
import LcFc as Lc
import NoiseLevel as NL
import export_parms as xp

class App:
    def __init__(self):
        self.window = Tk()
        self.setup_gui()
        self.init_vars()
        self.create_widgets()
        self.psnex_file = None

    def setup_gui(self):
        self.style = ttk.Style(self.window)
        self.style.configure("lefttab.TNotebook", tabposition="nw")
        self.notebook = ttk.Notebook(self.window, style="lefttab.TNotebook")
        self.main_tab = Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")
        self.frame = Frame(self.main_tab)
        self.notebook.pack(side='top')
        self.window.title("AFM_FS software")
        self.window.minsize(800, 400)
        self.frame.pack(expand=YES)
        # Subframes
        self.subframe_main_tab = Frame(self.frame)
        self.subframe_plots = Frame(self.frame)
        self.subframe_tab_peaks = Frame(self.frame)
        self.subframe_list_peaks = Frame(self.frame)
        self.subframe_second_tab = Frame(self.frame)
        self.subframe_other = Frame(self.frame)
        self.subframe_second_tab.grid(row=0, column=0)
        self.subframe_other.grid(row=1, column=0)
        self.subframe_main_tab.grid(row=0, column=2)
        self.subframe_plots.grid(row=0, column=1)
        self.subframe_tab_peaks.grid(row=1, column=1)
        self.subframe_list_peaks.grid(row=1, column=2)

    def init_vars(self):
        # All IntVar, StringVar, etc.
        self.widget_main = None
        self.toolbar_main = None
        self.dict_info = {}
        self.dict_raw = {}
        self.export_file_path = None
        self.approachOn = IntVar(value=1)
        self.retractOn = IntVar(value=1)
        self.Npoly = IntVar(value=1)
        self.percentage_noise = IntVar(value=30)
        self.change_K = IntVar()
        self.change_invOLS = IntVar()
        self.change_x_axis = IntVar()
        self.SmoothingOn = IntVar()
        self.DetectPeaksOn = IntVar()
        self.CorrectVirtualDeflection = IntVar()
        self.CpRetractOn = IntVar()
        self.CpApproachOn = IntVar()
        self.CorrectCP = IntVar()
        self.N_peaks = IntVar()
        self.width = IntVar()
        self.prominence = IntVar()
        self.range_before_peak = IntVar()
        self.contour_length = StringVar()
        self.force_threashold = IntVar()
        self.threshold = DoubleVar()
        self.hysteresis = IntVar()
        self.JumpOn = IntVar()
        # ... add other variables as needed

    def create_widgets(self):
        # All widget creation and layout
        self.create_buttons_main_tab()
        # ... add other widget creation as needed

    # --- Helper Functions ---

    def clear_main_plot(self):
        if self.widget_main:
            self.widget_main.destroy()
        if self.toolbar_main:
            self.toolbar_main.destroy()

    def create_figure_canvas(self):
        self.clear_main_plot()
        figure = Figure(figsize=(7,5), dpi=100)
        ax = figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=self.subframe_plots)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.grid(row=8, column=1)
        toolbarFrame = Frame(master=self.subframe_plots)
        toolbarFrame.grid(row=11,column=1)
        toolbar_main = NavigationToolbar2Tk(canvas, toolbarFrame)
        toolbar_main.update()
        self.widget_main = widget
        self.toolbar_main = toolbar_main
        return ax

    def update_dicts(self, info_dict, raw_dict):
        self.dict_info.update(info_dict)
        self.dict_raw.update(raw_dict)

    def load_file(self, filetype, path):
        # Centralized file loading logic for each filetype
        # Returns info_dict, raw_dict, and any other needed values
        pass

    # --- File Dialog and File Navigation ---

    def fileDialog(self):
        # Use self.load_file() and self.update_dicts()
        # Centralize file dialog logic here
        pass

    def nextFile(self, ARDF_flag=False):
        # Use self.load_file() and self.update_dicts()
        pass

    def PreviousFile(self):
        # Use self.load_file() and self.update_dicts()
        pass

    # --- Plotting and Analysis Functions ---

    def get_deflection_vs_piezo(self):
        ax = self.create_figure_canvas()
        # Plotting logic here
        pass

    def get_combo_values(self):
        ax = self.create_figure_canvas()
        # Plotting logic here
        pass

    def correct_virtual_deflection(self):
        ax = self.create_figure_canvas()
        # Correction logic here
        pass

    def apply_virtual_deflection_correction(self):
        # Use self.correct_virtual_deflection() and plotting helpers
        pass

    def show_point_contact_retract(self):
        ax = self.create_figure_canvas()
        # Logic for showing contact point
        pass

    def show_point_contact_approach(self):
        ax = self.create_figure_canvas()
        # Logic for showing contact point
        pass

    def correct_point_contact(self):
        # Logic for correcting contact point
        pass

    def plot_detected_peaks(self):
        ax = self.create_figure_canvas()
        # Logic for plotting detected peaks
        pass

    def plot_WLC_model(self):
        ax = self.create_figure_canvas()
        # Logic for WLC model fitting and plotting
        pass

    def plot_FJC_model(self):
        ax = self.create_figure_canvas()
        # Logic for FJC model fitting and plotting
        pass

    def plot_FcLc(self):
        ax = self.create_figure_canvas()
        # Logic for plotting Fc vs Lc
        pass

    def plot_loading_rate(self):
        ax = self.create_figure_canvas()
        # Logic for plotting loading rate
        pass

    def plot_peak_FcLc(self):
        ax = self.create_figure_canvas()
        # Logic for plotting force vs contour length with peaks
        pass

    def delete_peaks(self):
        # Logic for deleting selected peaks
        pass

    def export_data(self):
        # Logic for exporting data
        pass

    def automatic_analysis(self):
        # Logic for automatic analysis from parameter file
        pass

# --- Run the application ---
if __name__ == "__main__":
    app = App()
    app.window.mainloop()