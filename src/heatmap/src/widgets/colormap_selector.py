#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Colormap Selector Widget
"""

from PyQt5.QtWidgets import QComboBox, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from config.colormap_config import HEIGHT_MAP_COLORMAPS, ALL_COLORMAPS, COLORMAP_OPTIONS


class ColormapSelector(QWidget):
    """Widget for selecting colormap"""
    
    # Signal emitted when colormap changes
    colormap_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, recommended_only=False):
        super().__init__(parent)
        
        self.recommended_only = recommended_only
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Colormap dropdown
        self.combo = QComboBox()
        
        # Populate with colormaps
        if recommended_only:
            self.combo.addItems(HEIGHT_MAP_COLORMAPS)
        else:
            # Add recommended first, then separator, then all others
            self.combo.addItems(HEIGHT_MAP_COLORMAPS)
            self.combo.insertSeparator(len(HEIGHT_MAP_COLORMAPS))
            
            # Add other colormaps by category
            for category, cmaps in COLORMAP_OPTIONS.items():
                # Skip if already in recommended
                other_cmaps = [c for c in cmaps if c not in HEIGHT_MAP_COLORMAPS]
                if other_cmaps:
                    self.combo.addItem(f"--- {category} ---")
                    for cmap in other_cmaps:
                        self.combo.addItem(f"  {cmap}")
        
        # Set default
        default_index = self.combo.findText('YlOrBr')
        if default_index >= 0:
            self.combo.setCurrentIndex(default_index)
        
        layout.addWidget(self.combo)
        
        # Connect signal
        self.combo.currentTextChanged.connect(self.on_colormap_changed)
    
    def on_colormap_changed(self, text):
        """Handle colormap selection"""
        # Clean up text (remove category markers and spacing)
        colormap = text.strip()
        
        # Skip category headers
        if colormap.startswith('---'):
            return
        
        # Emit signal
        self.colormap_changed.emit(colormap)
    
    def get_current_colormap(self):
        """Get currently selected colormap"""
        return self.combo.currentText().strip()
    
    def set_colormap(self, colormap_name):
        """Set colormap by name"""
        index = self.combo.findText(colormap_name)
        if index >= 0:
            self.combo.setCurrentIndex(index)
    
    def reset_to_default(self):
        """Reset to default colormap"""
        default_index = self.combo.findText('YlOrBr')
        if default_index >= 0:
            self.combo.setCurrentIndex(default_index)
        else:
            self.combo.setCurrentIndex(0)


class ColormapSelectorWithLabel(QWidget):
    """Colormap selector with label"""
    
    colormap_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, label_text="Colormap:", recommended_only=False):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(label_text)
        layout.addWidget(self.label)
        
        # Selector
        self.selector = ColormapSelector(recommended_only=recommended_only)
        layout.addWidget(self.selector, stretch=1)
        
        # Forward signal
        self.selector.colormap_changed.connect(self.colormap_changed.emit)
    
    def get_current_colormap(self):
        """Get currently selected colormap"""
        return self.selector.get_current_colormap()
    
    def set_colormap(self, colormap_name):
        """Set colormap by name"""
        self.selector.set_colormap(colormap_name)
    
    def reset_to_default(self):
        """Reset to default colormap"""
        self.selector.reset_to_default()
