#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager Module
Handles saving and loading of analysis sessions
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List


class SessionManager:
    """Manage analysis sessions - save/load state and data"""
    
    def __init__(self):
        self.current_session = None
        self.session_file = None
        
    def create_session(self, map_folder: str, parameters: Dict) -> Dict:
        """
        Create a new session
        
        Parameters:
        -----------
        map_folder : str
            Path to map folder
        parameters : Dict
            Analysis parameters
            
        Returns:
        --------
        Session dictionary
        """
        session = {
            'created': datetime.now().isoformat(),
            'map_folder': map_folder,
            'parameters': parameters,
            'roi_data': None,
            'statistics': None,
            'exports': []
        }
        self.current_session = session
        return session
    
    def save_session(self, session_path: str, 
                     map_data: Optional[Dict] = None,
                     roi_df: Optional[pd.DataFrame] = None,
                     statistics: Optional[Dict] = None) -> bool:
        """
        Save current session to file
        
        Parameters:
        -----------
        session_path : str
            Path to save session file
        map_data : Dict, optional
            Map data dictionary
        roi_df : DataFrame, optional
            ROI data
        statistics : Dict, optional
            ROI statistics
            
        Returns:
        --------
        bool: Success status
        """
        try:
            if self.current_session is None:
                raise ValueError("No active session to save")
            
            # Update session data
            self.current_session['last_saved'] = datetime.now().isoformat()
            if statistics:
                self.current_session['statistics'] = statistics
            
            # Create session directory if needed
            session_dir = os.path.dirname(session_path)
            if session_dir and not os.path.exists(session_dir):
                os.makedirs(session_dir)
            
            # Save session metadata
            session_json = session_path.replace('.csv', '_session.json') if session_path.endswith('.csv') else session_path + '_session.json'
            with open(session_json, 'w') as f:
                json.dump(self.current_session, f, indent=2)
            
            # Save ROI data if available
            if roi_df is not None and len(roi_df) > 0:
                roi_csv_path = session_path if session_path.endswith('.csv') else session_path + '_roi_data.csv'
                roi_df.to_csv(roi_csv_path, index=False)
                self.current_session['roi_data_file'] = roi_csv_path
            
            self.session_file = session_json
            return True
            
        except Exception as e:
            print(f"Error saving session: {str(e)}")
            return False
    
    def load_session(self, session_path: str) -> Dict:
        """
        Load session from file
        
        Parameters:
        -----------
        session_path : str
            Path to session file (.json or .csv)
            
        Returns:
        --------
        Dictionary with session data and loaded DataFrames
        """
        try:
            # Determine session JSON path
            if session_path.endswith('_session.json'):
                session_json = session_path
            elif session_path.endswith('.csv'):
                session_json = session_path.replace('.csv', '_session.json')
            else:
                session_json = session_path + '_session.json'
            
            # Load session metadata
            if os.path.exists(session_json):
                with open(session_json, 'r') as f:
                    self.current_session = json.load(f)
                self.session_file = session_json
            else:
                # Create minimal session from CSV
                self.current_session = {
                    'created': datetime.now().isoformat(),
                    'loaded_from_csv': True,
                    'csv_file': session_path
                }
            
            # Load ROI data if available
            roi_df = None
            if 'roi_data_file' in self.current_session and os.path.exists(self.current_session['roi_data_file']):
                roi_df = pd.read_csv(self.current_session['roi_data_file'])
            elif session_path.endswith('.csv') and os.path.exists(session_path):
                roi_df = pd.read_csv(session_path)
            
            return {
                'session': self.current_session,
                'roi_data': roi_df,
                'success': True
            }
            
        except Exception as e:
            return {
                'session': None,
                'roi_data': None,
                'success': False,
                'error': str(e)
            }
    
    def update_session_parameter(self, param_name: str, param_value):
        """Update a parameter in current session"""
        if self.current_session is None:
            raise ValueError("No active session")
        
        if 'parameters' not in self.current_session:
            self.current_session['parameters'] = {}
        
        self.current_session['parameters'][param_name] = param_value
    
    def add_export_record(self, export_type: str, export_path: str):
        """Record an export in the session"""
        if self.current_session is None:
            return
        
        if 'exports' not in self.current_session:
            self.current_session['exports'] = []
        
        self.current_session['exports'].append({
            'timestamp': datetime.now().isoformat(),
            'type': export_type,
            'path': export_path
        })
    
    def get_recent_sessions(self, directory: str, max_count: int = 10) -> List[Dict]:
        """
        Find recent session files in directory
        
        Parameters:
        -----------
        directory : str
            Directory to search
        max_count : int
            Maximum number of sessions to return
            
        Returns:
        --------
        List of session info dictionaries
        """
        sessions = []
        
        if not os.path.exists(directory):
            return sessions
        
        # Find all session JSON files
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('_session.json'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            session_data = json.load(f)
                        
                        sessions.append({
                            'path': file_path,
                            'created': session_data.get('created'),
                            'last_saved': session_data.get('last_saved'),
                            'map_folder': session_data.get('map_folder'),
                            'file': file
                        })
                    except:
                        continue
        
        # Sort by last_saved or created date
        sessions.sort(key=lambda x: x.get('last_saved') or x.get('created', ''), reverse=True)
        
        return sessions[:max_count]
