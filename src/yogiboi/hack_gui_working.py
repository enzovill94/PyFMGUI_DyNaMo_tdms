#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 30 01:28:47 2024

@author: yogehs
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 21:29:17 2024

@author: yogehs
save a folder of cleaning before going to a next folder 
"""
import pygame as pyg
import pandas as pd 

from PyQt5.QtGui import QKeySequence,QColor
import numpy as np 
import sys
import os
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import pyqtgraph as pg
from pyfmreader import loadfile
from collections import defaultdict
from pyqtgraph.Qt import QtWidgets, QtCore
import datetime

class Widget(QWidget):
    def __init__(self,root_dir, *args, **kwargs):
        
        self.i_file_path = 0
        self.jpk_file_path = []
        self.index = 0
        self.df_results = pd.DataFrame()
        QWidget.__init__(self, *args, **kwargs)
        hlay = QHBoxLayout(self)
 
        self.treeview = QTreeView()
        self.listview =QListWidget()
        self.plotview = pg.PlotWidget()
        self.select_edit = QLineEdit()

        hlay.addWidget(self.treeview)
        hlay.addWidget(self.listview)
        hlay.addWidget(self.plotview)
        hlay.addWidget(self.select_edit)
        
    

        self.dirModel = QFileSystemModel()
        self.dirModel.setRootPath(QDir.rootPath())
        self.dirModel.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)

        #self.fileModel_file = QStringListModel()

        #self.fileModel_file.setRootPath(QDir.rootPath())

        self.treeview.setModel(self.dirModel)
        
        #self.listview.setModel(self.fileModel_file)


        
        self.treeview.setRootIndex(self.dirModel.index(root_dir))

        self.treeview.clicked.connect(self.on_clicked_folder)
        self.listview.clicked.connect(self.on_click_file)
        
        selection_model = self.listview.selectionModel()
        #selection_model.selectionChanged.connect(self.update_plot)
        
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Up), self)
        
        self.shortcut_good = QShortcut(QKeySequence(Qt.Key_G), self)
        self.shortcut_bad = QShortcut(QKeySequence(Qt.Key_B), self)

        # Connect shortcuts to actions
        self.shortcut_next.activated.connect(self.file_next)
        self.shortcut_prev.activated.connect(self.file_prev)
        
        self.shortcut_good.activated.connect(self.file_good)
        self.shortcut_bad.activated.connect(self.file_bad)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_joystick)
        self.timer.start(100)
        pyg.init()
        pyg.joystick.init()


        if pyg.joystick.get_count() > 0:
            self.joystick = pyg.joystick.Joystick(0)
            self.joystick.init()
        else:
            self.joystick = None
            print("No joystick found")

    def read_joystick(self):
        if self.joystick is None:
            return

        #pyg.event.pump()
        if self.joystick.get_button(0):  # A
            self.save_sess()
        elif self.joystick.get_button(11):  # up
            self.file_prev()
        elif self.joystick.get_button(12):  # down
            self.file_next()
        elif self.joystick.get_button(9):  # Y
            self.file_bad()
        elif self.joystick.get_button(10):  # X
            self.file_good()
    def find_jpk_files(self,root_dir):
        
        jpk_file_path = [];jpk_file_name = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
           for filename in filenames:
              if filename.endswith(".tdms"):
                  #print(f"{dirpath}/{filename}",'\n')
                  jpk_file_path.append(f"{dirpath}/{filename}")
                  jpk_file_name.append(filename)
                  expt_tags = dirpath.replace(root_dir,'')
                  expt_tags=expt_tags.split('/')
        self.jpk_file = jpk_file_name
        self.jpk_file_path = jpk_file_path
        self.bool_good_curve = np.zeros(len(jpk_file_path))
        
    def on_clicked_folder(self, index):
        self.save_sess()
        self.listview.clear()
        path = self.dirModel.fileInfo(index).absoluteFilePath()
        self.find_jpk_files(path+'/')
        self.listview.addItems(self.jpk_file)
        self.listview.setCurrentRow(self.index)
        self.update_plot()
        
        
        
    def file_good(self):
        self.bool_good_curve[self.index]=1
        self.change_item_color(QColor(0, 255, 0))
        self.file_next()
    def file_bad(self):
        self.bool_good_curve[self.index]=0
        self.change_item_color(QColor(255, 0, 0))

        self.file_next()
    def file_next(self):
        
        if self.index < len(self.jpk_file_path):
            self.index  += 1
        else:
            
            self.index  = 0

        self.listview.setCurrentRow(self.index)
        self.update_plot()
    def file_prev(self):
        
        if self.index < len(self.jpk_file):
            self.index  -= 1
        else:
            self.index  = 0

        self.listview.setCurrentRow(self.index)
        self.update_plot()

            
    def update_plot(self):
        self.i_file_path = self.jpk_file_path[self.index ]
        self.plotview.clear()
        #;self.plotview.addItem(self.rup_pos)
        #self.trace_plt.addItem(self.otr_win)
        
        self.plotview.enableAutoRange(axis='x')
        self.plotview.setAutoVisible(x=True)
        
        uff = loadfile(self.i_file_path)
        metadata = uff.filemetadata
        
        FC = uff.getcurve(0)
        
        # 6. Preprocess curve with the deflection sens in the header
        defl_sens = metadata['defl_sens_nmbyV'] / 1e09 # nm/V --> m/V
        FC.preprocess_force_curve(defl_sens, metadata['height_channel_key'])
        _, ret_seg =FC.get_segments()[-1]
        poc = [0, 0.0] # in nm
        spring_k = metadata['spring_const_Nbym']
        FC.get_force_vs_indentation(poc, spring_k)
        self.plotview.plot(ret_seg.zheight,-ret_seg.force)
    def save_sess(self):
        if len(self.jpk_file_path)>0:
            dict_temp = {"local_file_path":self.jpk_file_path,"file_name":self.jpk_file,"bool_good_curve":self.bool_good_curve}
            df_temp =pd.DataFrame.from_dict(dict_temp)
            self.df_results = pd.concat([self.df_results, df_temp])
    def on_click_file(self,item):
        
        # Get index of clicked item using currentRow()
        self.index = self.listview.currentRow()
        
        self.update_plot()
    def change_item_color(self,color = QColor(0, 0, 255)):
        current_item = self.listview.currentItem()
        if current_item:
            current_item.setBackground(color)


root_dir = '/Users/evillz/Data/article/2025_07_01_THP1_phd'
temp = datetime.datetime.now()

save_path = root_dir+ temp.strftime("%m_%d_%Y__%H:%M_")+'cleaned_SMFS_data_.csv'


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Widget(root_dir)
    w.show()
    sys.exit(app.exec_())
    print(w.df_results)
    w.df_results.to_csv(save_path)

