"""Synthetic data generation for baseline estimators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .channel import relative_spectrum, synthesize_attenuation_db
from .constants import DEFAULT_MAX_FREQ_GHZ, DEFAULT_MIN_FREQ_GHZ, DEFAULT_SUBCARRIERS


@dataclass(frozen=True)
class SyntheticDatasetConfig:
    n_samples: int = 2000
    n_subcarriers: int = DEFAULT_SUBCARRIERS
    min_freq_ghz: float = DEFAULT_MIN_FREQ_GHZ
    max_freq_ghz: float = DEFAULT_MAX_FREQ_GHZ
    gas_ppm_range: tuple[float, float] = (0.0, 120.0)
    pm_ug_m3_range: tuple[float, float] = (0.0, 180.0)
    elevation_deg_range: tuple[float, float] = (15.0, 80.0)
    snr_db_range: tuple[float, float] = (20.0, 45.0)
    random_seed: int = 7


@dataclass(frozen=True)
class SyntheticDataset:
    frequency_ghz: np.ndarray
    X: np.ndarray
    y: np.ndarray
    metadata: pd.DataFrame
    attenuation_db: np.ndarray


def generate_dataset(config: SyntheticDatasetConfig = SyntheticDatasetConfig()) -> SyntheticDataset:
    """Generate spectra and targets for regression experiments."""
    rng = np.random.default_rng(config.random_seed)
    frequency_ghz = np.linspace(config.min_freq_ghz, config.max_freq_ghz, config.n_subcarriers)

    gas_ppm = rng.uniform(*config.gas_ppm_range, size=config.n_samples)
    pm_ug_m3 = rng.uniform(*config.pm_ug_m3_range, size=config.n_samples)
    elevation_deg = rng.uniform(*config.elevation_deg_range, size=config.n_samples)
    snr_db = rng.uniform(*config.snr_db_range, size=config.n_samples)

    attenuation_db = synthesize_attenuation_db(
        frequency_ghz=frequency_ghz,
        gas_ppm=gas_ppm,
        pm_ug_m3=pm_ug_m3,
        elevation_deg=elevation_deg,
        snr_db=snr_db,
        rng=rng,
    )
    X = relative_spectrum(attenuation_db)
    y = np.column_stack([gas_ppm, pm_ug_m3])
    metadata = pd.DataFrame(
        {
            "sample_id": np.arange(config.n_samples),
            "gas_ppm": gas_ppm,
            "pm_ug_m3": pm_ug_m3,
            "elevation_deg": elevation_deg,
            "snr_db": snr_db,
        }
    )
    return SyntheticDataset(
        frequency_ghz=frequency_ghz,
        X=X,
        y=y,
        metadata=metadata,
        attenuation_db=attenuation_db,
    )

