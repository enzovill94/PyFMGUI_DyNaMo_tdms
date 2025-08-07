"""
Training utilities for plateau detection neural networks.

This module provides training loops, model evaluation, and training
management for the plateau detection system.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict, List, Tuple, Optional
import time
import logging
import os
from pathlib import Path
import json

from ..plateau_detector import PlateauDetectorNN, PlateauLoss
from ..utils.data_preprocessing import TetherDataPreprocessor

logger = logging.getLogger(__name__)


class NeuralNetworkTrainer:
    """
    Training manager for plateau detection neural networks.
    
    Handles model training, validation, checkpointing, and evaluation.
    """
    
    def __init__(self, 
                 model: PlateauDetectorNN,
                 device: str = 'auto',
                 save_dir: str = 'models'):
        """
        Initialize trainer.
        
        Args:
            model: PlateauDetectorNN model to train
            device: Device for training ('cpu', 'cuda', or 'auto')
            save_dir: Directory to save model checkpoints
        """
        self.model = model
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        
        # Set device
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.model.to(self.device)
        logger.info(f"Using device: {self.device}")
        
        # Training components
        self.criterion = PlateauLoss()
        self.optimizer = None
        self.scheduler = None
        
        # Training history
        self.training_history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': [],
            'epochs': []
        }
        
    def setup_optimizer(self, 
                       optimizer_type: str = 'adam',
                       learning_rate: float = 1e-3,
                       weight_decay: float = 1e-4,
                       **kwargs):
        """
        Setup optimizer for training.
        
        Args:
            optimizer_type: Type of optimizer ('adam', 'sgd', 'adamw')
            learning_rate: Learning rate
            weight_decay: Weight decay for regularization
            **kwargs: Additional optimizer parameters
        """
        if optimizer_type.lower() == 'adam':
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
                **kwargs
            )
        elif optimizer_type.lower() == 'sgd':
            self.optimizer = optim.SGD(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
                momentum=kwargs.get('momentum', 0.9),
                **kwargs
            )
        elif optimizer_type.lower() == 'adamw':
            self.optimizer = optim.AdamW(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported optimizer type: {optimizer_type}")
        
        logger.info(f"Setup {optimizer_type} optimizer with lr={learning_rate}")
    
    def setup_scheduler(self,
                       scheduler_type: str = 'step',
                       **kwargs):
        """
        Setup learning rate scheduler.
        
        Args:
            scheduler_type: Type of scheduler ('step', 'cosine', 'plateau')
            **kwargs: Scheduler parameters
        """
        if self.optimizer is None:
            raise RuntimeError("Must setup optimizer before scheduler")
        
        if scheduler_type.lower() == 'step':
            self.scheduler = optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=kwargs.get('step_size', 30),
                gamma=kwargs.get('gamma', 0.1)
            )
        elif scheduler_type.lower() == 'cosine':
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=kwargs.get('T_max', 100)
            )
        elif scheduler_type.lower() == 'plateau':
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode='min',
                patience=kwargs.get('patience', 10),
                factor=kwargs.get('factor', 0.5)
            )
        else:
            raise ValueError(f"Unsupported scheduler type: {scheduler_type}")
        
        logger.info(f"Setup {scheduler_type} scheduler")
    
    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Dictionary of training metrics
        """
        self.model.train()
        
        total_loss = 0.0
        total_samples = 0
        correct_predictions = 0
        loss_components = {'classification_loss': 0, 'boundary_loss': 0, 'count_loss': 0}
        
        for batch_idx, (force_data, targets) in enumerate(train_loader):
            # Move data to device
            force_data = force_data.to(self.device)
            for key in targets:
                targets[key] = targets[key].to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(force_data)
            
            # Calculate loss
            loss, loss_dict = self.criterion(outputs, targets)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Update metrics
            batch_size = force_data.size(0)
            total_loss += loss.item() * batch_size
            total_samples += batch_size
            
            # Classification accuracy
            predictions = (outputs['classification'] > 0.5).float()
            correct_predictions += (predictions == targets['has_plateau']).sum().item()
            
            # Accumulate loss components
            for key, value in loss_dict.items():
                if key in loss_components:
                    loss_components[key] += value * batch_size
        
        # Calculate averages
        avg_loss = total_loss / total_samples
        accuracy = correct_predictions / total_samples
        
        for key in loss_components:
            loss_components[key] /= total_samples
        
        metrics = {
            'loss': avg_loss,
            'accuracy': accuracy,
            **loss_components
        }
        
        return metrics
    
    def validate_epoch(self, val_loader: DataLoader) -> Dict[str, float]:
        """
        Validate for one epoch.
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Dictionary of validation metrics
        """
        self.model.eval()
        
        total_loss = 0.0
        total_samples = 0
        correct_predictions = 0
        loss_components = {'classification_loss': 0, 'boundary_loss': 0, 'count_loss': 0}
        
        with torch.no_grad():
            for force_data, targets in val_loader:
                # Move data to device
                force_data = force_data.to(self.device)
                for key in targets:
                    targets[key] = targets[key].to(self.device)
                
                # Forward pass
                outputs = self.model(force_data)
                
                # Calculate loss
                loss, loss_dict = self.criterion(outputs, targets)
                
                # Update metrics
                batch_size = force_data.size(0)
                total_loss += loss.item() * batch_size
                total_samples += batch_size
                
                # Classification accuracy
                predictions = (outputs['classification'] > 0.5).float()
                correct_predictions += (predictions == targets['has_plateau']).sum().item()
                
                # Accumulate loss components
                for key, value in loss_dict.items():
                    if key in loss_components:
                        loss_components[key] += value * batch_size
        
        # Calculate averages
        avg_loss = total_loss / total_samples
        accuracy = correct_predictions / total_samples
        
        for key in loss_components:
            loss_components[key] /= total_samples
        
        metrics = {
            'loss': avg_loss,
            'accuracy': accuracy,
            **loss_components
        }
        
        return metrics
    
    def train(self,
              train_loader: DataLoader,
              val_loader: DataLoader,
              num_epochs: int = 100,
              save_best: bool = True,
              early_stopping_patience: int = 20,
              print_every: int = 10) -> Dict[str, List]:
        """
        Full training loop.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader  
            num_epochs: Number of training epochs
            save_best: Whether to save best model
            early_stopping_patience: Patience for early stopping
            print_every: Print metrics every N epochs
            
        Returns:
            Training history dictionary
        """
        if self.optimizer is None:
            self.setup_optimizer()
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        logger.info(f"Starting training for {num_epochs} epochs...")
        
        for epoch in range(num_epochs):
            start_time = time.time()
            
            # Training phase
            train_metrics = self.train_epoch(train_loader)
            
            # Validation phase
            val_metrics = self.validate_epoch(val_loader)
            
            # Update learning rate
            if self.scheduler is not None:
                if isinstance(self.scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_metrics['loss'])
                else:
                    self.scheduler.step()
            
            # Record history
            self.training_history['train_loss'].append(train_metrics['loss'])
            self.training_history['val_loss'].append(val_metrics['loss'])
            self.training_history['train_acc'].append(train_metrics['accuracy'])
            self.training_history['val_acc'].append(val_metrics['accuracy'])
            self.training_history['epochs'].append(epoch + 1)
            
            # Print progress
            if (epoch + 1) % print_every == 0:
                epoch_time = time.time() - start_time
                logger.info(
                    f"Epoch {epoch+1}/{num_epochs} ({epoch_time:.2f}s) - "
                    f"Train Loss: {train_metrics['loss']:.4f}, "
                    f"Train Acc: {train_metrics['accuracy']:.4f}, "
                    f"Val Loss: {val_metrics['loss']:.4f}, "
                    f"Val Acc: {val_metrics['accuracy']:.4f}"
                )
            
            # Save best model
            if save_best and val_metrics['loss'] < best_val_loss:
                best_val_loss = val_metrics['loss']
                self.save_model('best_model.pth', epoch + 1, val_metrics)
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
        
        logger.info("Training completed!")
        return self.training_history
    
    def save_model(self, 
                   filename: str,
                   epoch: int,
                   metrics: Dict[str, float]):
        """
        Save model checkpoint.
        
        Args:
            filename: Filename for checkpoint
            epoch: Current epoch number
            metrics: Current metrics
        """
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict() if self.optimizer else None,
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'metrics': metrics,
            'training_history': self.training_history
        }
        
        filepath = self.save_dir / filename
        torch.save(checkpoint, filepath)
        logger.info(f"Saved model checkpoint to {filepath}")
    
    def load_model(self, filepath: str) -> Dict:
        """
        Load model checkpoint.
        
        Args:
            filepath: Path to checkpoint file
            
        Returns:
            Checkpoint dictionary
        """
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        if self.optimizer and 'optimizer_state_dict' in checkpoint:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        if self.scheduler and 'scheduler_state_dict' in checkpoint:
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        
        if 'training_history' in checkpoint:
            self.training_history = checkpoint['training_history']
        
        logger.info(f"Loaded model from {filepath}")
        return checkpoint
    
    def evaluate_model(self, test_loader: DataLoader) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Args:
            test_loader: Test data loader
            
        Returns:
            Test metrics
        """
        logger.info("Evaluating model...")
        test_metrics = self.validate_epoch(test_loader)
        
        logger.info(f"Test Results:")
        logger.info(f"  Loss: {test_metrics['loss']:.4f}")
        logger.info(f"  Accuracy: {test_metrics['accuracy']:.4f}")
        
        return test_metrics
    
    def save_training_history(self, filename: str = 'training_history.json'):
        """Save training history to JSON file."""
        filepath = self.save_dir / filename
        with open(filepath, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        logger.info(f"Saved training history to {filepath}")


def create_trainer_from_config(config: Dict) -> NeuralNetworkTrainer:
    """
    Create trainer from configuration dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured trainer instance
    """
    # Create model
    model_config = config.get('model', {})
    model = PlateauDetectorNN(
        input_size=model_config.get('input_size', 1000),
        hidden_dim=model_config.get('hidden_dim', 128)
    )
    
    # Create trainer
    trainer_config = config.get('trainer', {})
    trainer = NeuralNetworkTrainer(
        model=model,
        device=trainer_config.get('device', 'auto'),
        save_dir=trainer_config.get('save_dir', 'models')
    )
    
    # Setup optimizer
    optimizer_config = config.get('optimizer', {})
    trainer.setup_optimizer(
        optimizer_type=optimizer_config.get('type', 'adam'),
        learning_rate=optimizer_config.get('learning_rate', 1e-3),
        weight_decay=optimizer_config.get('weight_decay', 1e-4)
    )
    
    # Setup scheduler if specified
    if 'scheduler' in config:
        scheduler_config = config['scheduler']
        trainer.setup_scheduler(
            scheduler_type=scheduler_config.get('type', 'step'),
            **{k: v for k, v in scheduler_config.items() if k != 'type'}
        )
    
    return trainer
