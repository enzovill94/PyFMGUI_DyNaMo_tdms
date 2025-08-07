# Neural Network Plateau Detection for Tether Analysis

This module provides deep learning capabilities for automated plateau detection in AFM tether analysis. The neural network can automatically identify tethering plateaus in force-extension curves, predict plateau boundaries, and assess plateau quality.

## Features

- **Automated Plateau Detection**: Convolutional neural network with attention mechanism for detecting plateaus in force curves
- **Boundary Prediction**: Regression head for predicting precise plateau start/end times and forces
- **Quality Assessment**: Confidence scoring for detected plateaus
- **Feature Extraction**: Comprehensive feature extraction from force-extension data
- **Training Framework**: Complete training pipeline with data preprocessing and model management

## Architecture

The `PlateauDetectorNN` uses a multi-head architecture:

1. **Feature Extraction**: 1D convolutional layers with batch normalization
2. **Attention Mechanism**: Multi-head attention for temporal dependencies
3. **Classification Head**: Binary classification (plateau/no plateau)
4. **Regression Head**: Plateau boundary prediction (start_time, end_time, start_force, end_force)
5. **Count Head**: Estimation of number of plateaus

## Quick Start

### 1. Basic Usage

```python
from neural_networks.plateau_detector import create_plateau_detector_model
from neural_networks.utils.data_preprocessing import TetherDataPreprocessor
import numpy as np

# Create model and preprocessor
model = create_plateau_detector_model()
preprocessor = TetherDataPreprocessor()

# Load your force/time data
force_data = np.array([...])  # Your force measurements
time_data = np.array([...])   # Your time measurements

# Detect plateaus
plateaus = model.predict_plateaus(force_data, time_data)

for plateau in plateaus:
    print(f"Plateau: {plateau['start_time']:.2f}s - {plateau['end_time']:.2f}s")
    print(f"Confidence: {plateau['confidence']:.3f}")
```

### 2. Integration with Existing GUI

```python
from neural_networks.integration_example import TetherAnalysisWithNN

class YourTetherGUI:
    def __init__(self):
        # Your existing initialization
        ...
        
        # Add neural network analysis
        self.nn_analysis = TetherAnalysisWithNN()
    
    def analyze_file_with_nn(self, force_data, time_data):
        """Enhanced analysis with neural network plateau detection"""
        
        # Your existing analysis
        traditional_results = self.your_existing_analysis(force_data, time_data)
        
        # Neural network analysis
        nn_results = self.nn_analysis.detect_plateaus_nn(force_data, time_data)
        
        # Combine results
        combined_results = {
            'traditional': traditional_results,
            'neural_network': nn_results,
            'consensus': self.combine_results(traditional_results, nn_results)
        }
        
        return combined_results
```

### 3. Training on Your Data

```python
from neural_networks.training.trainer import NeuralNetworkTrainer
from neural_networks.utils.data_preprocessing import TetherDataPreprocessor

# Prepare your labeled data
labeled_data = [
    {
        'force': force_array_1,
        'time': time_array_1,
        'has_plateau': True,
        'plateau_boundaries': [start_time, end_time, start_force, end_force],
        'plateau_count': 1
    },
    # ... more samples
]

# Setup training
preprocessor = TetherDataPreprocessor()
train_loader, val_loader = preprocessor.prepare_training_data(labeled_data)

model = create_plateau_detector_model()
trainer = NeuralNetworkTrainer(model)
trainer.setup_optimizer(learning_rate=1e-3)

# Train
history = trainer.train(train_loader, val_loader, num_epochs=100)
```

## Model Outputs

The neural network provides three types of outputs:

1. **Classification**: Probability that the curve contains a plateau (0-1)
2. **Boundaries**: Normalized coordinates for plateau boundaries [start_time, end_time, start_force, end_force]
3. **Count**: Estimated number of plateaus in the curve

## Data Format

### Input Data
- **Force data**: 1D numpy array of force measurements
- **Time data**: 1D numpy array of time measurements
- Data is automatically resampled to 1000 points and normalized

### Training Labels
For training, provide labeled data with:
- `has_plateau`: Boolean indicating plateau presence
- `plateau_boundaries`: Array of [start_time, end_time, start_force, end_force] (normalized 0-1)
- `plateau_count`: Number of plateaus (integer)

## Synthetic Data Generation

For initial training without labeled data:

```python
from neural_networks.utils.data_preprocessing import TetherDataPreprocessor

preprocessor = TetherDataPreprocessor()
synthetic_data = preprocessor.create_synthetic_training_data(n_samples=1000)

# Train on synthetic data first, then fine-tune on real data
```

## Model Configuration

### Default Architecture
- Input size: 1000 points (automatically resampled)
- Conv layers: 32, 64, 128, 256 channels
- Attention heads: 8
- Hidden dimension: 128

### Customization
```python
from neural_networks.plateau_detector import PlateauDetectorNN

# Custom model
model = PlateauDetectorNN(
    input_size=2000,    # Longer sequences
    hidden_dim=256,     # Larger hidden layers
    num_conv_layers=5   # More conv layers
)
```

## Training Configuration

```python
# Training configuration example
config = {
    'model': {
        'input_size': 1000,
        'hidden_dim': 128
    },
    'optimizer': {
        'type': 'adam',
        'learning_rate': 1e-3,
        'weight_decay': 1e-4
    },
    'scheduler': {
        'type': 'step',
        'step_size': 30,
        'gamma': 0.1
    },
    'trainer': {
        'device': 'auto',
        'save_dir': 'models'
    }
}

from neural_networks.training.trainer import create_trainer_from_config
trainer = create_trainer_from_config(config)
```

## File Structure

```
neural_networks/
├── __init__.py                 # Main module exports
├── plateau_detector.py         # Core neural network model
├── integration_example.py      # Integration examples
├── utils/
│   ├── __init__.py
│   ├── feature_extraction.py   # Feature extraction utilities
│   └── data_preprocessing.py   # Data preprocessing and datasets
└── training/
    ├── __init__.py
    └── trainer.py              # Training management
```

## Dependencies

The neural network module requires:
- PyTorch (≥1.9.0)
- NumPy
- SciPy
- scikit-learn (optional, for additional metrics)

Install with:
```bash
pip install torch torchvision numpy scipy
```

## Performance Tips

1. **GPU Acceleration**: Use CUDA if available for faster training/inference
2. **Batch Processing**: Process multiple files in batches for efficiency
3. **Model Caching**: Save and reuse trained models
4. **Data Preprocessing**: Normalize and resample data consistently

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**: Reduce batch size or model size
2. **Poor Performance**: Ensure data is properly normalized and resampled
3. **Training Instability**: Reduce learning rate or add gradient clipping

### Debugging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.INFO)

# Check model outputs
outputs = model(force_tensor)
print(f"Classification: {outputs['classification']}")
print(f"Boundaries: {outputs['boundaries']}")
print(f"Count: {outputs['count']}")
```

## Future Improvements

- Multi-plateau detection and segmentation
- Uncertainty quantification
- Real-time processing optimization
- Transfer learning from related domains
- Automated hyperparameter tuning

## Contributing

To contribute to the neural network module:

1. Follow the existing code structure
2. Add comprehensive docstrings
3. Include unit tests for new features
4. Update this README for new functionality

## References

- Convolutional Neural Networks for Time Series Analysis
- Attention Mechanisms in Deep Learning
- AFM Force Spectroscopy Analysis Methods
