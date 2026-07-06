"""Physics informed estimators for the synthetic atmospheric model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .atmosphere import slant_path_km
from .channel import lorentzian_profile
from .spectral_lines import TOY_VOC_LINES


def gas_template_per_ppm_km(frequency_ghz: np.ndarray) -> np.ndarray:
    """Return the synthetic gas attenuation template per ppm and km."""
    frequency = np.asarray(frequency_ghz, dtype=float)
    template = np.zeros_like(frequency)
    for line in TOY_VOC_LINES:
        template += line.strength_db_per_ppm_km * lorentzian_profile(
            frequency,
            line.center_ghz,
            line.width_ghz,
        )
    return template


def pm_template_per_ug_m3_km(frequency_ghz: np.ndarray) -> np.ndarray:
    """Return the synthetic PM attenuation template per microgram per cubic meter and km."""
    frequency = np.asarray(frequency_ghz, dtype=float)
    return 0.000015 * (frequency / 200.0) ** 4


@dataclass
class TemplateLeastSquaresEstimator:
    """Closed form estimator using the known synthetic gas and PM templates."""

    frequency_ghz: np.ndarray
    nonnegative: bool = True

    def __post_init__(self) -> None:
        gas = gas_template_per_ppm_km(self.frequency_ghz)
        pm = pm_template_per_ug_m3_km(self.frequency_ghz)
        self.design_ = np.column_stack([gas, pm])
        self.pinv_ = np.linalg.pinv(self.design_)

    def fit(self, X, y=None):
        """Fit is present for scikit style compatibility."""
        return self

    def predict_from_attenuation(self, attenuation_db: np.ndarray, elevation_deg: np.ndarray) -> np.ndarray:
        """Estimate gas ppm and PM from attenuation spectra."""
        path = slant_path_km(elevation_deg)
        attenuation_per_km = attenuation_db / path[:, None]
        estimate = attenuation_per_km @ self.pinv_.T
        if self.nonnegative:
            estimate = np.maximum(estimate, 0.0)
        return estimate

