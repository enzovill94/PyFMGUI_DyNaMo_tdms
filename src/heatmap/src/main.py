#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for PSNEX Map Analysis GUI
"""

import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import QApplication
from gui.main_window import MapAnalysisMainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("PSNEX Map Analysis")
    app.setOrganizationName("DyNaMo-INSERM")
    
    # Create and show main window
    window = MapAnalysisMainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
