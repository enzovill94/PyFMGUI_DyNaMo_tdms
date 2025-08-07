"""
Integration example for neural network plateau detection in tether analysis GUI.

This script demonstrates how to integrate the PlateauDetectorNN with your
existing tether analysis workflow.
"""

import numpy as np
import torch
import sys
import os
from pathlib import Path
from typing import Dict, List

# Add the neural networks module to path
sys.path.append(str(Path(__file__).parent.parent))

from neural_networks.plateau_detector import PlateauDetectorNN, create_plateau_detector_model
from neural_networks.utils.data_preprocessing import TetherDataPreprocessor
from neural_networks.training.trainer import NeuralNetworkTrainer


class TetherAnalysisWithNN:
    """
    Enhanced tether analysis class that integrates neural network plateau detection.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize with optional pre-trained model.
        
        Args:
            model_path: Path to pre-trained model checkpoint
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.preprocessor = TetherDataPreprocessor(target_length=1000)
        
        # Load or create model
        if model_path and os.path.exists(model_path):
            self.load_pretrained_model(model_path)
        else:
            self.model = create_plateau_detector_model()
            self.model.to(self.device)
            print("Created new model - consider training or loading pre-trained weights")
    
    def load_pretrained_model(self, model_path: str):
        """Load a pre-trained model."""
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Create model with same architecture
        self.model = create_plateau_detector_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Loaded pre-trained model from {model_path}")
    
    def detect_plateaus_nn(self, 
                          force_data: np.ndarray, 
                          time_data: np.ndarray,
                          confidence_threshold: float = 0.5) -> Dict:
        """
        Detect plateaus using neural network.
        
        Args:
            force_data: Force measurements
            time_data: Time measurements  
            confidence_threshold: Minimum confidence for plateau detection
            
        Returns:
            Dictionary with plateau information and predictions
        """
        try:
            # Ensure data is numpy arrays
            force_data = np.array(force_data, dtype=np.float32)
            time_data = np.array(time_data, dtype=np.float32)
            
            # Check for valid data
            if len(force_data) == 0 or len(time_data) == 0:
                return {
                    'plateaus': [],
                    'num_plateaus': 0,
                    'has_plateau': False,
                    'error': 'Empty input data'
                }
            
            # Use the model's predict_plateaus method directly (it handles preprocessing)
            with torch.no_grad():
                predictions = self.model.predict_plateaus(
                    force_data, time_data, threshold=confidence_threshold
                )
            
            return {
                'plateaus': predictions,
                'num_plateaus': len(predictions),
                'has_plateau': len(predictions) > 0
            }
            
        except Exception as e:
            print(f"Neural network plateau detection error: {e}")
            return {
                'plateaus': [],
                'num_plateaus': 0,
                'has_plateau': False,
                'error': str(e)
            }
    
    def train_model_on_data(self, labeled_data: list, num_epochs: int = 50):
        """
        Train the model on labeled data.
        
        Args:
            labeled_data: List of labeled samples
            num_epochs: Number of training epochs
        """
        # Create trainer
        trainer = NeuralNetworkTrainer(self.model, device=str(self.device))
        trainer.setup_optimizer(learning_rate=1e-3)
        trainer.setup_scheduler('step', step_size=20, gamma=0.5)
        
        # Prepare data
        train_loader, val_loader = self.preprocessor.prepare_training_data(
            labeled_data, validation_split=0.2, batch_size=16
        )
        
        # Train
        history = trainer.train(
            train_loader, val_loader, 
            num_epochs=num_epochs, 
            print_every=10
        )
        
        return history
    
    def create_synthetic_training_data(self, n_samples: int = 500):
        """Create synthetic training data for initial training."""
        return self.preprocessor.create_synthetic_training_data(n_samples)


def integrate_with_gui_example():
    """
    Example of how to integrate with your existing GUI.
    
    This shows how you could modify your existing tether analysis
    to use neural network plateau detection.
    """
    
    # Initialize NN-enhanced analysis
    nn_analysis = TetherAnalysisWithNN()
    
    # Example: Simulate loading TDMS data (replace with your actual loading)
    def simulate_tdms_data():
        """Simulate loading TDMS data - replace with your actual function."""
        time = np.linspace(0, 10, 1000)
        # Simulate force curve with plateau
        force = np.zeros_like(time)
        force[200:600] = 100 + np.random.normal(0, 5, 400)  # Plateau region
        force[:200] = np.linspace(0, 100, 200) + np.random.normal(0, 2, 200)
        force[600:] = 100 * np.exp(-(time[600:] - 6) * 2) + np.random.normal(0, 3, 400)
        return force, time
    
    # Simulate data loading
    force_data, time_data = simulate_tdms_data()
    
    # Detect plateaus using neural network
    nn_results = nn_analysis.detect_plateaus_nn(force_data, time_data)
    
    print("Neural Network Results:")
    print(f"Number of plateaus detected: {nn_results['num_plateaus']}")
    print(f"Has plateau: {nn_results['has_plateau']}")
    
    for i, plateau in enumerate(nn_results['plateaus']):
        print(f"\nPlateau {i+1}:")
        print(f"  Time range: {plateau['start_time']:.2f} - {plateau['end_time']:.2f}s")
        print(f"  Average force: {plateau['avg_force']:.2f}")
        print(f"  Confidence: {plateau['confidence']:.3f}")
        print(f"  Length: {plateau['length']:.2f}s")
    
    return nn_results


def training_example():
    """
    Example of how to train the model with synthetic data.
    """
    print("Training example:")
    
    # Initialize analysis
    nn_analysis = TetherAnalysisWithNN()
    
    # Create synthetic training data
    print("Creating synthetic training data...")
    training_data = nn_analysis.create_synthetic_training_data(n_samples=1000)
    
    # Train model
    print("Training model...")
    history = nn_analysis.train_model_on_data(training_data, num_epochs=20)
    
    print("Training completed!")
    print(f"Final training accuracy: {history['train_acc'][-1]:.3f}")
    print(f"Final validation accuracy: {history['val_acc'][-1]:.3f}")
    
    return history


if __name__ == "__main__":
    print("Tether Analysis Neural Network Integration Example")
    print("=" * 50)
    
    # Run integration example
    print("\n1. Running integration example...")
    results = integrate_with_gui_example()
    
    # Run training example
    print("\n\n2. Running training example...")
    training_history = training_example()
    
    print("\n\nIntegration examples completed!")
    print("\nTo integrate with your GUI:")
    print("1. Import TetherAnalysisWithNN in your GUI script")
    print("2. Initialize it in your GUI class: self.nn_analysis = TetherAnalysisWithNN()")
    print("3. Call detect_plateaus_nn() with your force/time data")
    print("4. Use the results to enhance your existing plateau detection")
