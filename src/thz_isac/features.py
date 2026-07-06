"""Feature construction for atmospheric estimators."""

from __future__ import annotations

import numpy as np

from .atmosphere import slant_path_km
from .channel import relative_spectrum
from .synthetic_data import SyntheticDataset


def polynomial_baseline(spectra: np.ndarray, frequency_ghz: np.ndarray, degree: int = 4) -> np.ndarray:
    """Fit a polynomial baseline to each spectrum."""
    freq = np.asarray(frequency_ghz, dtype=float)
    x = 2.0 * (freq - freq.min()) / (freq.max() - freq.min()) - 1.0
    design = np.vander(x, N=degree + 1, increasing=True)
    coef, *_ = np.linalg.lstsq(design, spectra.T, rcond=None)
    return (design @ coef).T


def build_features(dataset: SyntheticDataset, mode: str) -> np.ndarray:
    """Build feature matrices for the requested representation."""
    elevation = dataset.metadata["elevation_deg"].to_numpy()
    snr = dataset.metadata["snr_db"].to_numpy()
    path = slant_path_km(elevation)
    attenuation_per_km = dataset.attenuation_db / path[:, None]

    if mode == "relative":
        return relative_spectrum(dataset.attenuation_db)
    if mode == "relative_context":
        context = np.column_stack([elevation, snr, path])
        return np.column_stack([relative_spectrum(dataset.attenuation_db), context])
    if mode == "path_normalized":
        return attenuation_per_km
    if mode == "path_normalized_relative":
        return relative_spectrum(attenuation_per_km)
    if mode == "baseline_residual":
        baseline = polynomial_baseline(attenuation_per_km, dataset.frequency_ghz, degree=4)
        residual = attenuation_per_km - baseline
        return np.column_stack([baseline, residual])
    if mode == "physics_combo":
        baseline = polynomial_baseline(attenuation_per_km, dataset.frequency_ghz, degree=4)
        residual = attenuation_per_km - baseline
        context = np.column_stack([elevation, snr, path])
        return np.column_stack([attenuation_per_km, baseline, residual, context])
    raise ValueError(f"Unknown feature mode: {mode}")


FEATURE_MODES = [
    "relative",
    "relative_context",
    "path_normalized",
    "path_normalized_relative",
    "baseline_residual",
    "physics_combo",
]

