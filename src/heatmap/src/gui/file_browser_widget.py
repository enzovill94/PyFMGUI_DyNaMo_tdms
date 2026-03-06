#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Browser Widget - Browse and select PSNEX map folders
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QFileDialog, QLabel,
                             QGroupBox, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.data_loader import DataLoader


class FileBrowserWidget(QWidget):
    """Widget for browsing and selecting PSNEX map folders"""
    
    # Signals
    folder_selected = pyqtSignal(str)  # Emits folder path when selected
    folders_added = pyqtSignal(list)  # Emits list of folders when added
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.data_loader = DataLoader()
        self.current_folders = []
        
        self.setupUI()
        
    def setupUI(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Group box
        group = QGroupBox("PSNEX Map Folders")
        group_layout = QVBoxLayout(group)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.on_add_folder)
        button_layout.addWidget(self.add_folder_btn)
        
        self.add_multiple_btn = QPushButton("Add Multiple")
        self.add_multiple_btn.clicked.connect(self.on_add_multiple)
        button_layout.addWidget(self.add_multiple_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove_folder)
        button_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.on_clear_all)
        button_layout.addWidget(self.clear_btn)
        
        group_layout.addLayout(button_layout)
        
        # Folder list
        self.folder_list = QListWidget()
        self.folder_list.itemClicked.connect(self.on_folder_clicked)
        self.folder_list.setAlternatingRowColors(True)
        group_layout.addWidget(self.folder_list)
        
        # Status label
        self.status_label = QLabel("No folders loaded")
        group_layout.addWidget(self.status_label)
        
        layout.addWidget(group)
        
    def on_add_folder(self):
        """Add single folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select PSNEX Map Folder",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.add_folder(folder)
    
    def on_add_multiple(self):
        """Add multiple folders from parent directory"""
        parent_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Parent Directory Containing PSNEX Maps",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if parent_dir:
            # Find all PSNEX folders
            folders = self.data_loader.find_psnex_folders(parent_dir)
            
            if folders:
                for folder in folders:
                    self.add_folder(folder, emit_signal=False)
                
                self.folders_added.emit(folders)
                self.update_status()
                QMessageBox.information(
                    self,
                    "Folders Added",
                    f"Added {len(folders)} PSNEX map folders"
                )
            else:
                QMessageBox.warning(
                    self,
                    "No Folders Found",
                    "No PSNEX map folders found in the selected directory"
                )
    
    def add_folder(self, folder_path, emit_signal=True):
        """Add folder to list"""
        if folder_path in self.current_folders:
            return
        
        # Validate folder
        validation = self.data_loader.validate_folder(folder_path)
        
        # Create list item
        item = QListWidgetItem(os.path.basename(folder_path))
        item.setData(Qt.UserRole, folder_path)
        
        # Set color based on validation
        if validation['valid']:
            item.setForeground(Qt.black)
            item.setToolTip(f"Valid: {validation['csv_count']} CSV, {validation['tdms_count']} TDMS files")
        else:
            item.setForeground(Qt.red)
            item.setToolTip(f"Invalid: {', '.join(validation['errors'])}")
        
        self.folder_list.addItem(item)
        self.current_folders.append(folder_path)
        
        self.update_status()
        
        if emit_signal:
            self.folders_added.emit([folder_path])
    
    def on_remove_folder(self):
        """Remove selected folder"""
        current_item = self.folder_list.currentItem()
        if current_item:
            folder_path = current_item.data(Qt.UserRole)
            row = self.folder_list.row(current_item)
            self.folder_list.takeItem(row)
            if folder_path in self.current_folders:
                self.current_folders.remove(folder_path)
            self.update_status()
    
    def on_clear_all(self):
        """Clear all folders"""
        self.folder_list.clear()
        self.current_folders.clear()
        self.update_status()
    
    def on_folder_clicked(self, item):
        """Handle folder click"""
        folder_path = item.data(Qt.UserRole)
        self.folder_selected.emit(folder_path)
    
    def update_status(self):
        """Update status label"""
        count = len(self.current_folders)
        if count == 0:
            self.status_label.setText("No folders loaded")
        elif count == 1:
            self.status_label.setText("1 folder loaded")
        else:
            self.status_label.setText(f"{count} folders loaded")
    
    def get_current_folders(self):
        """Get list of current folders"""
        return self.current_folders.copy()
    
    def get_selected_folder(self):
        """Get currently selected folder"""
        current_item = self.folder_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
