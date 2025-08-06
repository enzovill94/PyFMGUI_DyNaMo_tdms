#!/usr/bin/env python3

"""
Minimal test to see if the GUI starts up correctly
"""

import sys
import os

# Set up the environment
sys.path.append('.')

try:
    print("Testing PyQt5...")
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
    from PyQt5.QtCore import Qt
    
    print("Testing pyqtgraph...")
    import pyqtgraph as pg
    
    print("Testing pygame...")
    import pygame
    
    print("Testing parameter widget...")
    from parameter_tree_widget import ParameterTreeWidget
    
    print("Testing tether script...")
    from tether_script import process_single_file
    
    print("All imports successful!")
    
    # Try to create a minimal app
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating main window...")
    window = QMainWindow()
    window.setWindowTitle("GUI Test")
    window.resize(400, 300)
    
    label = QLabel("GUI imports working!")
    label.setAlignment(Qt.AlignCenter)
    window.setCentralWidget(label)
    
    print("Showing window...")
    window.show()
    
    print("GUI started successfully! Close the window to continue.")
    
    # Don't actually start the event loop for this test
    # app.exec_()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
