#!/usr/bin/env python3

"""
Test GUI startup without tether_script import to isolate the issue
"""

import sys
import os

# Set up the environment
sys.path.append('.')

# Mock the tether script import
class MockTetherScript:
    @staticmethod
    def process_single_file(*args, **kwargs):
        return {"plateaus": [], "fourier_data": None, "filename": "test"}

# Replace the import in the main module temporarily
sys.modules['tether_script'] = type(sys)('tether_script')
sys.modules['tether_script'].process_single_file = MockTetherScript.process_single_file

try:
    print("Starting GUI with mock tether script...")
    from PyQt5.QtWidgets import QApplication
    
    # Import the main GUI
    from tether_analysis_gui_v3_filter import TetherAnalysisApp
    
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating main window...")
    window = TetherAnalysisApp()
    
    print("Showing window...")
    window.show()
    
    print("GUI started successfully! Check if interactive regions appear in Fourier plot.")
    print("Close the window to exit.")
    
    # Start the event loop for this test
    app.exec_()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
