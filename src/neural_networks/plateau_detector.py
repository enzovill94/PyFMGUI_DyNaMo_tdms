"""
Neural Network for Automated Plateau Detection in Tether Analysis

This module implements a deep learning model to automatically detect and classify
tethering plateaus in AFM force-extension curves.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from scipy.signal import resample
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PlateauDetectorNN(nn.Module):
    """
    Convolutional Neural Network for detecting plateaus in tether force curves.
    
    Architecture:
    - 1D Convolutional layers for feature extraction
    - Temporal attention mechanism
    - Classification head for plateau/non-plateau detection
    - Regression head for plateau boundaries
    """
    
    def __init__(self, input_size: int = 1000, hidden_dim: int = 128, num_conv_layers: int = 4):
        super(PlateauDetectorNN, self).__init__()
        
        self.input_size = input_size
        self.hidden_dim = hidden_dim
        
        # Feature extraction layers
        self.conv_layers = nn.ModuleList()
        self.conv_layers.append(nn.Conv1d(1, 32, kernel_size=7, padding=3))
        self.conv_layers.append(nn.Conv1d(32, 64, kernel_size=5, padding=2))
        self.conv_layers.append(nn.Conv1d(64, 128, kernel_size=3, padding=1))
        self.conv_layers.append(nn.Conv1d(128, 256, kernel_size=3, padding=1))
        
        # Batch normalization layers
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(32),
            nn.BatchNorm1d(64),
            nn.BatchNorm1d(128),
            nn.BatchNorm1d(256)
        ])
        
        # Pooling layers
        self.pool = nn.MaxPool1d(2)
        self.adaptive_pool = nn.AdaptiveAvgPool1d(64)
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(256, num_heads=8, batch_first=True)
        
        # Classification head (plateau/no plateau)
        self.classifier = nn.Sequential(
            nn.Linear(256 * 64, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Regression head for plateau boundaries
        self.boundary_regressor = nn.Sequential(
            nn.Linear(256 * 64, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, 4),  # start_time, end_time, start_force, end_force
            nn.Sigmoid()  # Output normalized values [0,1]
        )
        
        # Plateau count head
        self.count_regressor = nn.Sequential(
            nn.Linear(256 * 64, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, 1),
            nn.ReLU()  # Ensure positive count
        )
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length)
            
        Returns:
            Dictionary containing:
            - 'classification': Plateau probability [0,1]
            - 'boundaries': Plateau boundaries (start_time, end_time, start_force, end_force)
            - 'count': Estimated number of plateaus
        """
        batch_size = x.size(0)
        
        # Add channel dimension for conv1d
        if len(x.shape) == 2:
            x = x.unsqueeze(1)  # (batch_size, 1, sequence_length)
        
        # Feature extraction through conv layers
        for conv, bn in zip(self.conv_layers, self.batch_norms):
            x = conv(x)
            x = bn(x)
            x = F.relu(x)
            x = self.pool(x)
        
        # Adaptive pooling to fixed size
        x = self.adaptive_pool(x)  # (batch_size, 256, 64)
        
        # Attention mechanism
        x_att = x.permute(0, 2, 1)  # (batch_size, 64, 256)
        attended, _ = self.attention(x_att, x_att, x_att)
        x = attended.permute(0, 2, 1)  # Back to (batch_size, 256, 64)
        
        # Flatten for fully connected layers - use reshape instead of view for safety
        x_flat = x.reshape(batch_size, -1)
        
        # Generate outputs
        classification = self.classifier(x_flat)
        boundaries = self.boundary_regressor(x_flat)
        count = self.count_regressor(x_flat)
        
        return {
            'classification': classification.squeeze(-1),  # (batch_size,)
            'boundaries': boundaries,  # (batch_size, 4)
            'count': count.squeeze(-1)  # (batch_size,)
        }
    
    def predict_plateaus(self, force_data: np.ndarray, 
                        time_data: np.ndarray,
                        threshold: float = 0.5) -> List[Dict]:
        """
        Predict plateaus in force-extension data.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements
            threshold: Classification threshold for plateau detection
            
        Returns:
            List of plateau dictionaries with keys:
            - 'start_time', 'end_time': Plateau time boundaries
            - 'start_force', 'end_force': Plateau force boundaries
            - 'confidence': Classification confidence
            - 'length': Plateau length
            - 'avg_force': Average force in plateau
        """
        self.eval()
        
        try:
            with torch.no_grad():
                # Ensure data is properly shaped
                force_data = np.array(force_data, dtype=np.float32)
                time_data = np.array(time_data, dtype=np.float32)
                
                # Handle different input sizes by resampling to expected length
                if len(force_data) > 2048:
                    # Resample to model's expected input size
                    from scipy.signal import resample
                    force_data = resample(force_data, 2048)
                    time_data = resample(time_data, 2048)
                elif len(force_data) < 100:
                    # Too short, pad with zeros
                    target_length = 2048
                    force_padded = np.zeros(target_length, dtype=np.float32)
                    time_padded = np.zeros(target_length, dtype=np.float32)
                    force_padded[:len(force_data)] = force_data
                    time_padded[:len(time_data)] = time_data
                    force_data = force_padded
                    time_data = time_padded
                
                # Create tensor with proper shape
                force_tensor = torch.FloatTensor(force_data).unsqueeze(0)  # (1, length)
                
                # Get predictions
                outputs = self.forward(force_tensor)
                
                plateaus = []
                
                # Check if plateau is detected
                confidence = outputs['classification'].item()
                if confidence > threshold:
                    # Extract boundary information safely
                    boundaries_tensor = outputs['boundaries']
                    if len(boundaries_tensor.shape) > 1:
                        boundaries = boundaries_tensor[0].detach().cpu().numpy()  # Take first batch
                    else:
                        boundaries = boundaries_tensor.detach().cpu().numpy()
                    
                    count = max(1, int(outputs['count'].item()))
                    
                    # Ensure we have enough boundary values
                    if len(boundaries) >= 4:
                        # Denormalize boundaries
                        time_min, time_max = time_data.min(), time_data.max()
                        force_min, force_max = force_data.min(), force_data.max()
                        
                        start_time = boundaries[0] * (time_max - time_min) + time_min
                        end_time = boundaries[1] * (time_max - time_min) + time_min
                        start_force = boundaries[2] * (force_max - force_min) + force_min
                        end_force = boundaries[3] * (force_max - force_min) + force_min
                        
                        # Ensure proper ordering
                        if start_time > end_time:
                            start_time, end_time = end_time, start_time
                        
                        # Calculate plateau properties
                        plateau_mask = (time_data >= start_time) & (time_data <= end_time)
                        if plateau_mask.sum() > 0:
                            avg_force = force_data[plateau_mask].mean()
                            length = end_time - start_time
                            
                            plateau = {
                                'start_time': float(start_time),
                                'end_time': float(end_time),
                                'start_force': float(start_force),
                                'end_force': float(end_force),
                                'confidence': float(confidence),
                                'length': float(length),
                                'avg_force': float(avg_force)
                            }
                            
                            plateaus.append(plateau)
                
                return plateaus
                
        except Exception as e:
            print(f"Error in plateau prediction: {e}")
            return []


class PlateauLoss(nn.Module):
    """
    Custom loss function for plateau detection training.
    
    Combines:
    - Binary cross-entropy for classification
    - MSE for boundary regression
    - MSE for count prediction
    """
    
    def __init__(self, classification_weight: float = 1.0, 
                 boundary_weight: float = 0.5, 
                 count_weight: float = 0.3):
        super(PlateauLoss, self).__init__()
        self.classification_weight = classification_weight
        self.boundary_weight = boundary_weight
        self.count_weight = count_weight
        
        self.bce_loss = nn.BCELoss()
        self.mse_loss = nn.MSELoss()
        
    def forward(self, outputs: Dict[str, torch.Tensor], 
                targets: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Calculate combined loss.
        
        Args:
            outputs: Model outputs
            targets: Ground truth targets
            
        Returns:
            Combined loss tensor
        """
        # Classification loss
        cls_loss = self.bce_loss(outputs['classification'], targets['has_plateau'].float())
        
        # Boundary loss (only for samples with plateaus)
        has_plateau = targets['has_plateau'].bool()
        if has_plateau.sum() > 0:
            boundary_loss = self.mse_loss(
                outputs['boundaries'][has_plateau], 
                targets['boundaries'][has_plateau]
            )
            count_loss = self.mse_loss(
                outputs['count'][has_plateau], 
                targets['count'][has_plateau].float()
            )
        else:
            boundary_loss = torch.tensor(0.0, device=outputs['classification'].device)
            count_loss = torch.tensor(0.0, device=outputs['classification'].device)
        
        # Combined loss
        total_loss = (self.classification_weight * cls_loss + 
                     self.boundary_weight * boundary_loss + 
                     self.count_weight * count_loss)
        
        return total_loss, {
            'classification_loss': cls_loss.item(),
            'boundary_loss': boundary_loss.item(),
            'count_loss': count_loss.item(),
            'total_loss': total_loss.item()
        }


def create_plateau_detector_model(input_size: int = 1000, 
                                hidden_dim: int = 128) -> PlateauDetectorNN:
    """
    Factory function to create a plateau detector model.
    
    Args:
        input_size: Input sequence length
        hidden_dim: Hidden layer dimension
        
    Returns:
        Initialized PlateauDetectorNN model
    """
    model = PlateauDetectorNN(input_size=input_size, hidden_dim=hidden_dim)
    
    # Initialize weights
    def init_weights(m):
        if isinstance(m, nn.Conv1d) or isinstance(m, nn.Linear):
            nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
    
    model.apply(init_weights)
    
    logger.info(f"Created PlateauDetectorNN with input_size={input_size}, hidden_dim={hidden_dim}")
    
    return model
