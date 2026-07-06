"""External data driven CSI generation.

The spectra are simulated, but the pollutant labels come from a public air
quality dataset and the gas spectral templates come from HITRAN line data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .atmosphere import slant_path_km
from .constants import DEFAULT_MAX_FREQ_GHZ, DEFAULT_MIN_FREQ_GHZ, DEFAULT_SUBCARRIERS
from .hitran_templates import hitran_template, rayleigh_pm_template


TARGET_COLUMNS = [
    "CO_ug_m3",
    "O3_ug_m3",
    "SO2_ug_m3",
    "NO2_ug_m3",
    "PM2_5_ug_m3",
    "PM10_ug_m3",
]

GAS_TO_MOLECULE = {
    "CO_ug_m3": "CO",
    "O3_ug_m3": "O3",
    "SO2_ug_m3": "SO2",
    "NO2_ug_m3": "NO2",
}


@dataclass(frozen=True)
class ExternalCSIDatasetConfig:
    n_samples: int = 20_000
    n_subcarriers: int = DEFAULT_SUBCARRIERS
    min_freq_ghz: float = DEFAULT_MIN_FREQ_GHZ
    max_freq_ghz: float = DEFAULT_MAX_FREQ_GHZ
    elevation_deg_range: tuple[float, float] = (15.0, 80.0)
    snr_db_range: tuple[float, float] = (20.0, 45.0)
    reference_elevation_deg: float = 45.0
    gas_peak_loss_db: float = 0.34
    pm25_peak_loss_db: float = 0.22
    pm10_peak_loss_db: float = 0.34
    background_peak_loss_db: float = 0.08
    random_seed: int = 7


@dataclass(frozen=True)
class ExternalCSIDataset:
    frequency_ghz: np.ndarray
    attenuation_db: np.ndarray
    path_normalized_db: np.ndarray
    y: np.ndarray
    target_names: list[str]
    metadata: pd.DataFrame
    design_per_unit: np.ndarray
    background_template: np.ndarray


def generate_external_csi_dataset(
    pollution: pd.DataFrame,
    hitran_lines: pd.DataFrame,
    config: ExternalCSIDatasetConfig = ExternalCSIDatasetConfig(),
) -> ExternalCSIDataset:
    """Generate CSI amplitudes from external pollution records and HITRAN templates."""
    rng = np.random.default_rng(config.random_seed)
    data = pollution.dropna(subset=TARGET_COLUMNS).copy()
    if len(data) > config.n_samples:
        data = data.sample(n=config.n_samples, random_state=config.random_seed)
    data = data.reset_index(drop=True)

    frequency_ghz = np.linspace(config.min_freq_ghz, config.max_freq_ghz, config.n_subcarriers)
    elevation = rng.uniform(*config.elevation_deg_range, size=len(data))
    snr_db = rng.uniform(*config.snr_db_range, size=len(data))
    reference_path = slant_path_km(config.reference_elevation_deg)
    path_factor = slant_path_km(elevation) / reference_path

    target_quantiles = data[TARGET_COLUMNS].quantile(0.95).replace(0, 1.0)
    design = []
    attenuation_per_reference_path = np.zeros((len(data), len(frequency_ghz)), dtype=float)

    for column, molecule in GAS_TO_MOLECULE.items():
        template = hitran_template(hitran_lines, frequency_ghz, molecule)
        scale_per_unit = config.gas_peak_loss_db / float(target_quantiles[column])
        design.append(scale_per_unit * template)
        attenuation_per_reference_path += data[column].to_numpy()[:, None] * scale_per_unit * template[None, :]

    pm25_template = rayleigh_pm_template(frequency_ghz, power=4.0)
    pm10_template = rayleigh_pm_template(frequency_ghz, power=3.2)
    pm25_scale = config.pm25_peak_loss_db / float(target_quantiles["PM2_5_ug_m3"])
    pm10_scale = config.pm10_peak_loss_db / float(target_quantiles["PM10_ug_m3"])
    design.append(pm25_scale * pm25_template)
    design.append(pm10_scale * pm10_template)
    attenuation_per_reference_path += data["PM2_5_ug_m3"].to_numpy()[:, None] * pm25_scale * pm25_template[None, :]
    attenuation_per_reference_path += data["PM10_ug_m3"].to_numpy()[:, None] * pm10_scale * pm10_template[None, :]

    background = _background_attenuation(hitran_lines, frequency_ghz, config.background_peak_loss_db)
    attenuation_per_reference_path += background[None, :]

    clean_attenuation = attenuation_per_reference_path * path_factor[:, None]
    noise_std_db = 1.0 / np.sqrt(10.0 ** (snr_db / 10.0))
    attenuation_db = clean_attenuation + rng.normal(0.0, noise_std_db[:, None], clean_attenuation.shape)
    path_normalized_db = attenuation_db / path_factor[:, None]

    metadata = data.copy()
    metadata["elevation_deg"] = elevation
    metadata["snr_db"] = snr_db
    metadata["path_factor"] = path_factor

    return ExternalCSIDataset(
        frequency_ghz=frequency_ghz,
        attenuation_db=attenuation_db,
        path_normalized_db=path_normalized_db,
        y=data[TARGET_COLUMNS].to_numpy(),
        target_names=TARGET_COLUMNS,
        metadata=metadata,
        design_per_unit=np.column_stack(design),
        background_template=background,
    )


def predict_with_template_least_squares(dataset: ExternalCSIDataset) -> np.ndarray:
    """Estimate target concentrations from known external templates."""
    coeffs = template_projection_features(dataset)
    pred = coeffs[:, : len(dataset.target_names)]
    return np.maximum(pred, 0.0)


def template_projection_features(dataset: ExternalCSIDataset) -> np.ndarray:
    """Project spectra onto target templates plus nuisance background terms."""
    nuisance = np.column_stack(
        [
            dataset.background_template,
            np.ones_like(dataset.background_template),
        ]
    )
    design = np.column_stack([dataset.design_per_unit, nuisance])
    pinv = np.linalg.pinv(design)
    return dataset.path_normalized_db @ pinv.T


def _background_attenuation(hitran_lines: pd.DataFrame, frequency_ghz: np.ndarray, peak_loss_db: float) -> np.ndarray:
    background = np.zeros_like(frequency_ghz, dtype=float)
    for molecule in ["H2O", "O2"]:
        template = hitran_template(hitran_lines, frequency_ghz, molecule)
        background += 0.5 * peak_loss_db * template
    return background

