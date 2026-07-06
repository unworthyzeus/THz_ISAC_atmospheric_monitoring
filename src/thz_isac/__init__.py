"""Tools for sub THz ISAC atmospheric monitoring experiments."""

from .synthetic_data import SyntheticDatasetConfig, generate_dataset
from .estimators import train_linear_baselines, evaluate_predictions

__all__ = [
    "SyntheticDatasetConfig",
    "generate_dataset",
    "train_linear_baselines",
    "evaluate_predictions",
]

