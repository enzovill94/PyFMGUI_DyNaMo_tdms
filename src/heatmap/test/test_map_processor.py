#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for Map Processor module
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add the heatmap/src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
heatmap_src_dir = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, heatmap_src_dir)

# Now import from core.map_processor directly
from core.map_processor import MapProcessor

class TestMapProcessor:
    """Test cases for MapProcessor class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = MapProcessor()
        
    def test_initialization(self):
        """Test MapProcessor initialization"""
        assert self.processor.current_map_data is None
        assert self.processor.current_params is None
        assert self.processor.current_dataframe is None
        assert self.processor.roi_data is None
        
    def test_create_2d_array_from_dataframe(self):
        """Test 2D array creation from dataframe"""
        # Create test data
        test_df = {
            'x_index': np.array([0, 1, 0, 1]),
            'y_index': np.array([0, 0, 1, 1]),
            'z_height_um_zero': np.array([1.0, 2.0, 3.0, 4.0])
        }
        
        test_params = {'map_x_pix': 2, 'map_y_pix': 2}
        
        result = self.processor.create_2d_array_from_dataframe(
            test_df, 
            value_key='z_height_um_zero',
            params=test_params
        )
        
        assert result.shape == (2, 2)
        assert isinstance(result, np.ndarray)
        
    def test_extract_roi_data_empty_pixels(self):
        """Test ROI extraction with empty pixel list"""
        # Setup some dummy data
        self.processor.current_map_data = {
            'map_tdms': np.ones((10, 10)),
            'x_axis': np.arange(10),
            'y_axis': np.arange(10)
        }
        self.processor.current_dataframe = {'test': 'data'}
        
        roi_pixels = []
        roi_df = self.processor.extract_roi_data(roi_pixels)
        
        assert len(roi_df) == 0
        assert isinstance(roi_df, pd.DataFrame)
        
    def test_get_roi_statistics_no_data(self):
        """Test statistics with no ROI data"""
        stats = self.processor.get_roi_statistics()
        assert stats == {}
        
    def test_get_roi_statistics_with_data(self):
        """Test statistics calculation"""
        # Create test ROI data
        self.processor.roi_data = pd.DataFrame({
            'x_pixel': [0, 1, 2],
            'y_pixel': [0, 1, 2],
            'z_value': [1.0, 2.0, 3.0]
        })
        
        stats = self.processor.get_roi_statistics()
        
        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert stats['mean'] == 2.0
        assert stats['min'] == 1.0
        assert stats['max'] == 3.0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
