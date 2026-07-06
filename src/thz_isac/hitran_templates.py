"""HITRAN derived spectral templates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .channel import lorentzian_profile


GHZ_PER_WAVENUMBER = 29.9792458


def load_hitran_lines(path) -> pd.DataFrame:
    """Load processed HITRAN lines."""
    return pd.read_csv(path)


def hitran_template(
    lines: pd.DataFrame,
    frequency_ghz: np.ndarray,
    molecule: str,
    min_width_ghz: float = 0.05,
) -> np.ndarray:
    """Create a normalized spectral template from HITRAN line positions and intensities."""
    selected = lines[lines["molecule"] == molecule].copy()
    if selected.empty:
        raise ValueError(f"No HITRAN lines found for molecule {molecule}")

    max_intensity = selected["line_intensity"].max()
    if max_intensity <= 0:
        raise ValueError(f"Nonpositive HITRAN intensities for molecule {molecule}")

    template = np.zeros_like(frequency_ghz, dtype=float)
    for row in selected.itertuples(index=False):
        width_ghz = max(float(row.gamma_air) * GHZ_PER_WAVENUMBER, min_width_ghz)
        strength = float(row.line_intensity) / max_intensity
        template += strength * lorentzian_profile(
            frequency_ghz,
            float(row.frequency_ghz),
            width_ghz,
        )

    peak = template.max()
    if peak > 0:
        template = template / peak
    return template


def rayleigh_pm_template(frequency_ghz: np.ndarray, power: float = 4.0) -> np.ndarray:
    """Create a normalized Rayleigh type PM trend."""
    freq = np.asarray(frequency_ghz, dtype=float)
    template = (freq / freq.max()) ** power
    return template / template.max()

