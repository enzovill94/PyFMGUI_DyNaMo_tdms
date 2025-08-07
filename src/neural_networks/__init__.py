"""
Neural Network modules for Tether Analysis

This package provides deep learning capabilities for:
- Automated plateau detection
"""

from .plateau_detector import PlateauDetectorNN
from .training.trainer import NeuralNetworkTrainer
from .utils.data_preprocessing import TetherDataPreprocessor
from .utils.feature_extraction import TetherFeatureExtractor

__all__ = [
    'PlateauDetectorNN',
    'NeuralNetworkTrainer',
    'TetherDataPreprocessor',
    'TetherFeatureExtractor',
]

__version__ = "1.0.0"
