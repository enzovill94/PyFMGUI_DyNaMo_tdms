"""
Data preprocessing utilities for neural network training and inference.

This module handles data loading, preprocessing, and batch preparation
for training the plateau detection neural network.
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Tuple, Optional, Union
import pickle
import os
import logging
from .feature_extraction import TetherFeatureExtractor, normalize_force_data, resample_data

logger = logging.getLogger(__name__)


class TetherDataset(Dataset):
    """
    PyTorch Dataset for tether force-extension data.
    
    Handles loading and preprocessing of tether data for neural network training.
    """
    
    def __init__(self, 
                 data_list: List[Dict],
                 target_length: int = 1000,
                 normalize: bool = True,
                 normalization_method: str = 'zscore',
                 augment: bool = False):
        """
        Initialize dataset.
        
        Args:
            data_list: List of data dictionaries containing 'force', 'time', and labels
            target_length: Target sequence length for padding/resampling
            normalize: Whether to normalize force data
            normalization_method: Method for normalization
            augment: Whether to apply data augmentation
        """
        self.data_list = data_list
        self.target_length = target_length
        self.normalize = normalize
        self.normalization_method = normalization_method
        self.augment = augment
        
        self.feature_extractor = TetherFeatureExtractor()
        
        # Preprocess all data
        self.processed_data = []
        self._preprocess_data()
        
    def _preprocess_data(self):
        """Preprocess all data samples."""
        logger.info(f"Preprocessing {len(self.data_list)} samples...")
        
        for i, data_dict in enumerate(self.data_list):
            try:
                processed = self._preprocess_single_sample(data_dict)
                self.processed_data.append(processed)
            except Exception as e:
                logger.warning(f"Failed to preprocess sample {i}: {e}")
                continue
        
        logger.info(f"Successfully preprocessed {len(self.processed_data)} samples")
    
    def _preprocess_single_sample(self, data_dict: Dict) -> Dict:
        """Preprocess a single data sample."""
        force_data = np.array(data_dict['force'])
        time_data = np.array(data_dict['time'])
        
        # Resample to target length
        if len(force_data) != self.target_length:
            force_data, time_data = resample_data(force_data, time_data, self.target_length)
        
        # Normalize if requested
        norm_params = None
        if self.normalize:
            force_data, norm_params = normalize_force_data(force_data, self.normalization_method)
        
        # Create processed sample
        processed = {
            'force': force_data.astype(np.float32),
            'time': time_data.astype(np.float32),
            'normalization_params': norm_params,
            'original_length': len(data_dict['force'])
        }
        
        # Add labels if present
        if 'has_plateau' in data_dict:
            processed['has_plateau'] = data_dict['has_plateau']
        if 'plateau_boundaries' in data_dict:
            processed['plateau_boundaries'] = np.array(data_dict['plateau_boundaries'], dtype=np.float32)
        if 'plateau_count' in data_dict:
            processed['plateau_count'] = data_dict['plateau_count']
        
        return processed
    
    def __len__(self) -> int:
        return len(self.processed_data)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """Get a single sample."""
        sample = self.processed_data[idx]
        
        force_tensor = torch.FloatTensor(sample['force'])
        
        # Apply augmentation if enabled
        if self.augment and self.training:
            force_tensor = self._augment_sample(force_tensor)
        
        # Prepare targets
        targets = {}
        if 'has_plateau' in sample:
            targets['has_plateau'] = torch.tensor(sample['has_plateau'], dtype=torch.float32)
        if 'plateau_boundaries' in sample:
            targets['boundaries'] = torch.FloatTensor(sample['plateau_boundaries'])
        if 'plateau_count' in sample:
            targets['count'] = torch.tensor(sample['plateau_count'], dtype=torch.float32)
        
        return force_tensor, targets
    
    def _augment_sample(self, force_tensor: torch.Tensor) -> torch.Tensor:
        """Apply data augmentation to a force tensor."""
        # Gaussian noise
        if np.random.random() < 0.3:
            noise_std = 0.01 * torch.std(force_tensor)
            noise = torch.normal(0, noise_std, force_tensor.shape)
            force_tensor = force_tensor + noise
        
        # Scaling
        if np.random.random() < 0.2:
            scale_factor = np.random.uniform(0.95, 1.05)
            force_tensor = force_tensor * scale_factor
        
        # Offset
        if np.random.random() < 0.2:
            offset = np.random.uniform(-0.02, 0.02) * torch.std(force_tensor)
            force_tensor = force_tensor + offset
        
        return force_tensor


class TetherDataPreprocessor:
    """
    High-level data preprocessor for tether analysis.
    
    Handles batch processing of tether files and preparation
    for neural network training/inference.
    """
    
    def __init__(self, 
                 target_length: int = 1000,
                 normalize: bool = True,
                 normalization_method: str = 'zscore'):
        """
        Initialize preprocessor.
        
        Args:
            target_length: Target sequence length
            normalize: Whether to normalize data
            normalization_method: Normalization method
        """
        self.target_length = target_length
        self.normalize = normalize
        self.normalization_method = normalization_method
        self.feature_extractor = TetherFeatureExtractor()
    
    def prepare_training_data(self, 
                            labeled_data: List[Dict],
                            validation_split: float = 0.2,
                            batch_size: int = 32,
                            shuffle: bool = True) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation data loaders.
        
        Args:
            labeled_data: List of labeled data samples
            validation_split: Fraction of data for validation
            batch_size: Batch size for data loaders
            shuffle: Whether to shuffle training data
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Split data
        n_val = int(len(labeled_data) * validation_split)
        indices = np.random.permutation(len(labeled_data))
        
        train_data = [labeled_data[i] for i in indices[n_val:]]
        val_data = [labeled_data[i] for i in indices[:n_val]]
        
        # Create datasets
        train_dataset = TetherDataset(
            train_data, 
            target_length=self.target_length,
            normalize=self.normalize,
            normalization_method=self.normalization_method,
            augment=True
        )
        
        val_dataset = TetherDataset(
            val_data,
            target_length=self.target_length, 
            normalize=self.normalize,
            normalization_method=self.normalization_method,
            augment=False
        )
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=2,
            pin_memory=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=2,
            pin_memory=True
        )
        
        logger.info(f"Created training loader with {len(train_dataset)} samples")
        logger.info(f"Created validation loader with {len(val_dataset)} samples")
        
        return train_loader, val_loader
    
    def prepare_inference_data(self, 
                             force_data: np.ndarray,
                             time_data: np.ndarray) -> torch.Tensor:
        """
        Prepare single sample for inference.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements
            
        Returns:
            Preprocessed force tensor ready for model input
        """
        # Resample to target length
        if len(force_data) != self.target_length:
            force_data, _ = resample_data(force_data, time_data, self.target_length)
        
        # Normalize if requested
        if self.normalize:
            force_data, _ = normalize_force_data(force_data, self.normalization_method)
        
        # Convert to tensor and add batch dimension
        force_tensor = torch.FloatTensor(force_data).unsqueeze(0)
        
        return force_tensor
    
    def batch_prepare_files(self, 
                          file_paths: List[str],
                          load_function: callable) -> List[torch.Tensor]:
        """
        Batch prepare multiple files for inference.
        
        Args:
            file_paths: List of file paths
            load_function: Function to load force/time data from file
            
        Returns:
            List of preprocessed tensors
        """
        tensors = []
        
        for file_path in file_paths:
            try:
                force_data, time_data = load_function(file_path)
                tensor = self.prepare_inference_data(force_data, time_data)
                tensors.append(tensor)
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
                continue
        
        return tensors
    
    def create_synthetic_training_data(self, 
                                     n_samples: int = 1000,
                                     noise_level: float = 0.1) -> List[Dict]:
        """
        Create synthetic training data for initial model training.
        
        Args:
            n_samples: Number of synthetic samples to generate
            noise_level: Level of noise to add
            
        Returns:
            List of synthetic data samples with labels
        """
        synthetic_data = []
        
        for i in range(n_samples):
            # Generate synthetic force curve
            t = np.linspace(0, 10, self.target_length)
            
            # Random plateau parameters
            has_plateau = np.random.random() < 0.7  # 70% have plateaus
            
            if has_plateau:
                # Generate curve with plateau
                plateau_start = np.random.uniform(2, 4)
                plateau_end = np.random.uniform(6, 8)
                plateau_force = np.random.uniform(50, 200)
                
                force = np.zeros_like(t)
                
                # Pre-plateau region (increasing)
                pre_mask = t < plateau_start
                force[pre_mask] = plateau_force * (t[pre_mask] / plateau_start) ** 2
                
                # Plateau region
                plateau_mask = (t >= plateau_start) & (t <= plateau_end)
                force[plateau_mask] = plateau_force + np.random.normal(0, plateau_force*0.05, np.sum(plateau_mask))
                
                # Post-plateau region (decreasing or rupture)
                post_mask = t > plateau_end
                if np.sum(post_mask) > 0:
                    force[post_mask] = plateau_force * np.exp(-(t[post_mask] - plateau_end) * 2)
                
                # Normalized boundary coordinates [0,1]
                boundaries = np.array([
                    plateau_start / 10,  # start_time
                    plateau_end / 10,    # end_time  
                    0.3,                 # start_force (normalized)
                    0.7                  # end_force (normalized)
                ])
                
                plateau_count = 1
                
            else:
                # Generate curve without clear plateau
                force = np.random.exponential(50, len(t)) * np.exp(-t/5)
                boundaries = np.array([0.0, 0.0, 0.0, 0.0])
                plateau_count = 0
            
            # Add noise
            force += np.random.normal(0, noise_level * np.std(force), len(force))
            
            # Create sample dictionary
            sample = {
                'force': force,
                'time': t,
                'has_plateau': has_plateau,
                'plateau_boundaries': boundaries,
                'plateau_count': plateau_count
            }
            
            synthetic_data.append(sample)
        
        logger.info(f"Generated {n_samples} synthetic training samples")
        return synthetic_data
    
    def save_processed_data(self, 
                          data: List[Dict], 
                          filepath: str):
        """Save processed data to disk."""
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Saved processed data to {filepath}")
    
    def load_processed_data(self, filepath: str) -> List[Dict]:
        """Load processed data from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        logger.info(f"Loaded processed data from {filepath}")
        return data


def collate_fn(batch: List[Tuple[torch.Tensor, Dict]]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    """
    Custom collate function for batching tether data.
    
    Args:
        batch: List of (force_tensor, targets) tuples
        
    Returns:
        Batched tensors
    """
    force_tensors = []
    batched_targets = {}
    
    for force_tensor, targets in batch:
        force_tensors.append(force_tensor)
        
        for key, value in targets.items():
            if key not in batched_targets:
                batched_targets[key] = []
            batched_targets[key].append(value)
    
    # Stack force tensors
    batched_force = torch.stack(force_tensors)
    
    # Stack target tensors
    for key, value_list in batched_targets.items():
        batched_targets[key] = torch.stack(value_list)
    
    return batched_force, batched_targets
