"""
Training modules for neural networks.
"""

from .trainer import NeuralNetworkTrainer, create_trainer_from_config

__all__ = [
    'NeuralNetworkTrainer',
    'create_trainer_from_config'
]
