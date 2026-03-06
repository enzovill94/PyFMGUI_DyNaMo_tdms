#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application class for PSNEX Map Analysis
"""

import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import QApplication
from gui.main_window import MapAnalysisMainWindow


class MapAnalysisApp:
    """PSNEX Map Analysis Application"""
    
    def __init__(self, argv=None):
        """
        Initialize application
        
        Parameters:
        -----------
        argv : list, optional
            Command line arguments
        """
        if argv is None:
            argv = sys.argv
            
        self.app = QApplication(argv)
        self.app.setApplicationName("PSNEX Map Analysis")
        self.app.setOrganizationName("DyNaMo-INSERM")
        
        self.window = MapAnalysisMainWindow()
        
    def run(self):
        """Run the application"""
        self.window.show()
        return self.app.exec_()


def main():
    """Main function"""
    app = MapAnalysisApp()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
