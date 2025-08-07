"""
Feature extraction utilities for tether analysis neural networks.

This module provides functions to extract meaningful features from
AFM force-extension curves for neural network training and inference.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import scipy.signal
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class TetherFeatureExtractor:
    """
    Feature extractor for tether force-extension data.
    
    Extracts both statistical and signal processing features
    that are relevant for plateau detection and analysis.
    """
    
    def __init__(self, window_size: int = 50, overlap: float = 0.5):
        """
        Initialize feature extractor.
        
        Args:
            window_size: Size of sliding window for local features
            overlap: Overlap fraction between windows
        """
        self.window_size = window_size
        self.overlap = overlap
        self.step_size = int(window_size * (1 - overlap))
        
    def extract_statistical_features(self, force_data: np.ndarray) -> Dict[str, float]:
        """
        Extract basic statistical features from force data.
        
        Args:
            force_data: Force measurements
            
        Returns:
            Dictionary of statistical features
        """
        features = {}
        
        # Basic statistics
        features['mean'] = np.mean(force_data)
        features['std'] = np.std(force_data)
        features['min'] = np.min(force_data)
        features['max'] = np.max(force_data)
        features['range'] = features['max'] - features['min']
        features['median'] = np.median(force_data)
        
        # Quartiles and IQR
        q25, q75 = np.percentile(force_data, [25, 75])
        features['q25'] = q25
        features['q75'] = q75
        features['iqr'] = q75 - q25
        
        # Distribution shape
        features['skewness'] = stats.skew(force_data)
        features['kurtosis'] = stats.kurtosis(force_data)
        
        # Coefficient of variation
        features['cv'] = features['std'] / features['mean'] if features['mean'] != 0 else 0
        
        return features
    
    def extract_signal_features(self, force_data: np.ndarray, 
                              time_data: Optional[np.ndarray] = None,
                              sampling_rate: float = 1000.0) -> Dict[str, float]:
        """
        Extract signal processing features.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements (optional)
            sampling_rate: Sampling rate in Hz
            
        Returns:
            Dictionary of signal features
        """
        features = {}
        
        # First and second derivatives
        force_diff1 = np.diff(force_data)
        force_diff2 = np.diff(force_diff1)
        
        features['diff1_mean'] = np.mean(force_diff1)
        features['diff1_std'] = np.std(force_diff1)
        features['diff1_max'] = np.max(np.abs(force_diff1))
        
        features['diff2_mean'] = np.mean(force_diff2)
        features['diff2_std'] = np.std(force_diff2)
        features['diff2_max'] = np.max(np.abs(force_diff2))
        
        # Zero crossings
        zero_crossings = np.where(np.diff(np.sign(force_data - np.mean(force_data))))[0]
        features['zero_crossings'] = len(zero_crossings)
        features['zero_crossing_rate'] = len(zero_crossings) / len(force_data)
        
        # Peak detection
        peaks, _ = scipy.signal.find_peaks(force_data, height=np.mean(force_data))
        valleys, _ = scipy.signal.find_peaks(-force_data, height=-np.mean(force_data))
        
        features['num_peaks'] = len(peaks)
        features['num_valleys'] = len(valleys)
        features['peak_rate'] = len(peaks) / len(force_data)
        
        # Energy and power features
        features['energy'] = np.sum(force_data**2)
        features['power'] = features['energy'] / len(force_data)
        features['rms'] = np.sqrt(np.mean(force_data**2))
        
        # Spectral features (if sampling rate is known)
        if sampling_rate > 0:
            freqs, psd = scipy.signal.welch(force_data, fs=sampling_rate, nperseg=min(256, len(force_data)//4))
            
            # Dominant frequency
            dominant_freq_idx = np.argmax(psd[1:]) + 1  # Skip DC component
            features['dominant_frequency'] = freqs[dominant_freq_idx]
            features['dominant_power'] = psd[dominant_freq_idx]
            
            # Spectral centroid
            features['spectral_centroid'] = np.sum(freqs * psd) / np.sum(psd)
            
            # Spectral bandwidth
            centroid = features['spectral_centroid']
            features['spectral_bandwidth'] = np.sqrt(np.sum(((freqs - centroid)**2) * psd) / np.sum(psd))
        
        return features
    
    def extract_plateau_features(self, force_data: np.ndarray, 
                                time_data: np.ndarray) -> Dict[str, float]:
        """
        Extract features specifically relevant to plateau detection.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements
            
        Returns:
            Dictionary of plateau-specific features
        """
        features = {}
        
        # Local stability analysis using sliding windows
        windows = self._get_windows(force_data)
        window_stds = [np.std(window) for window in windows]
        window_means = [np.mean(window) for window in windows]
        
        features['min_window_std'] = np.min(window_stds)
        features['mean_window_std'] = np.mean(window_stds)
        features['std_window_std'] = np.std(window_stds)
        
        # Plateau-like regions (low variance windows)
        stable_threshold = np.percentile(window_stds, 25)  # Bottom quartile
        stable_windows = np.array(window_stds) < stable_threshold
        
        features['stable_window_fraction'] = np.mean(stable_windows)
        features['max_stable_sequence'] = self._max_consecutive_true(stable_windows)
        
        # Force level consistency
        if len(window_means) > 1:
            features['force_level_std'] = np.std(window_means)
            features['force_trend'] = np.polyfit(range(len(window_means)), window_means, 1)[0]
        else:
            features['force_level_std'] = 0
            features['force_trend'] = 0
        
        # Rupture-like events (sudden force drops)
        force_drops = np.diff(force_data)
        large_drops = force_drops < -3 * np.std(force_drops)
        features['num_rupture_events'] = np.sum(large_drops)
        features['rupture_event_rate'] = features['num_rupture_events'] / len(force_data)
        
        # Time-based features
        if len(time_data) > 1:
            duration = time_data[-1] - time_data[0]
            features['total_duration'] = duration
            features['sampling_rate'] = len(time_data) / duration if duration > 0 else 0
        
        return features
    
    def extract_all_features(self, force_data: np.ndarray, 
                           time_data: Optional[np.ndarray] = None,
                           sampling_rate: float = 1000.0) -> Dict[str, float]:
        """
        Extract comprehensive feature set.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements (optional)
            sampling_rate: Sampling rate in Hz
            
        Returns:
            Dictionary containing all extracted features
        """
        features = {}
        
        # Statistical features
        stat_features = self.extract_statistical_features(force_data)
        features.update({f'stat_{k}': v for k, v in stat_features.items()})
        
        # Signal features
        signal_features = self.extract_signal_features(force_data, time_data, sampling_rate)
        features.update({f'signal_{k}': v for k, v in signal_features.items()})
        
        # Plateau features
        if time_data is not None:
            plateau_features = self.extract_plateau_features(force_data, time_data)
            features.update({f'plateau_{k}': v for k, v in plateau_features.items()})
        
        return features
    
    def _get_windows(self, data: np.ndarray) -> List[np.ndarray]:
        """Get sliding windows from data."""
        windows = []
        for i in range(0, len(data) - self.window_size + 1, self.step_size):
            windows.append(data[i:i + self.window_size])
        return windows
    
    def _max_consecutive_true(self, boolean_array: np.ndarray) -> int:
        """Find maximum consecutive True values in boolean array."""
        if len(boolean_array) == 0:
            return 0
        
        max_count = 0
        current_count = 0
        
        for value in boolean_array:
            if value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count


def normalize_force_data(force_data: np.ndarray, 
                        method: str = 'zscore') -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Normalize force data for neural network input.
    
    Args:
        force_data: Raw force measurements
        method: Normalization method ('zscore', 'minmax', 'robust')
        
    Returns:
        Tuple of (normalized_data, normalization_params)
    """
    params = {}
    
    if method == 'zscore':
        mean = np.mean(force_data)
        std = np.std(force_data)
        normalized = (force_data - mean) / (std + 1e-8)
        params = {'mean': mean, 'std': std, 'method': 'zscore'}
        
    elif method == 'minmax':
        min_val = np.min(force_data)
        max_val = np.max(force_data)
        range_val = max_val - min_val
        normalized = (force_data - min_val) / (range_val + 1e-8)
        params = {'min': min_val, 'max': max_val, 'range': range_val, 'method': 'minmax'}
        
    elif method == 'robust':
        median = np.median(force_data)
        mad = np.median(np.abs(force_data - median))
        normalized = (force_data - median) / (mad + 1e-8)
        params = {'median': median, 'mad': mad, 'method': 'robust'}
        
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    return normalized, params


def denormalize_force_data(normalized_data: np.ndarray, 
                          params: Dict[str, float]) -> np.ndarray:
    """
    Denormalize force data using stored parameters.
    
    Args:
        normalized_data: Normalized force measurements
        params: Normalization parameters from normalize_force_data
        
    Returns:
        Denormalized force data
    """
    method = params['method']
    
    if method == 'zscore':
        return normalized_data * params['std'] + params['mean']
    elif method == 'minmax':
        return normalized_data * params['range'] + params['min']
    elif method == 'robust':
        return normalized_data * params['mad'] + params['median']
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def resample_data(force_data: np.ndarray, 
                 time_data: np.ndarray,
                 target_length: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resample force and time data to target length.
    
    Args:
        force_data: Force measurements
        time_data: Time measurements
        target_length: Desired output length
        
    Returns:
        Tuple of (resampled_force, resampled_time)
    """
    if len(force_data) == target_length:
        return force_data, time_data
    
    # Create new time points
    new_time = np.linspace(time_data[0], time_data[-1], target_length)
    
    # Interpolate force data
    new_force = np.interp(new_time, time_data, force_data)
    
    return new_force, new_time
