#!/usr/bin/env python3
"""
Test script for interactive threshold line functionality
"""

import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
import pyqtgraph as pg

def test_interactive_threshold():
    """Test the interactive threshold line"""
    app = QApplication(sys.argv)
    
    # Create test widget
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # Create plot widget
    plot_widget = pg.PlotWidget()
    plot_widget.setLabel('left', 'dy/dx', units='N/m')
    plot_widget.setLabel('bottom', 'Displacement', units='m')
    plot_widget.showGrid(x=True, y=True)
    
    layout.addWidget(plot_widget)
    
    # Generate test data
    x = np.linspace(0, 10, 1000)
    y = np.abs(np.sin(x) * np.exp(-x/5)) * 1e-9  # Simulate derivative data
    
    # Plot test data
    plot_widget.plot(x, y, pen=pg.mkPen(color='blue', width=2), name='Test Data')
    
    # Create interactive threshold line
    threshold_value = 5e-10
    threshold_line = pg.InfiniteLine(
        pos=threshold_value,
        angle=0,  # Horizontal line
        pen=pg.mkPen('r', width=2, style=Qt.DashLine),
        movable=True,
        label='Threshold',
        labelOpts={'position': 0.95, 'color': 'red', 'fill': pg.mkBrush(255, 255, 255, 100)}
    )
    
    def on_threshold_moved():
        """Handle threshold line movement"""
        new_threshold = threshold_line.pos().y()
        print(f"Threshold moved to: {new_threshold:.2e} N/m")
    
    # Connect signal
    threshold_line.sigPositionChanged.connect(on_threshold_moved)
    plot_widget.addItem(threshold_line)
    
    # Add reset button
    reset_button = QPushButton("Reset Threshold")
    def reset_threshold():
        threshold_line.setPos(threshold_value)
        print(f"Reset threshold to: {threshold_value:.2e} N/m")
    
    reset_button.clicked.connect(reset_threshold)
    layout.addWidget(reset_button)
    
    widget.setWindowTitle("Interactive Threshold Test")
    widget.setGeometry(100, 100, 800, 600)
    widget.show()
    
    print("Test Instructions:")
    print("1. Try dragging the red dashed line up/down")
    print("2. Check console for position updates")
    print("3. Use Reset button to return to original position")
    print("4. Close window to exit")
    
    return app.exec_()

if __name__ == '__main__':
    test_interactive_threshold()
