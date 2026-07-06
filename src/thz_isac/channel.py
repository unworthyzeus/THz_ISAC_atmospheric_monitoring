"""Channel synthesis for early THz ISAC atmospheric sensing experiments."""

from __future__ import annotations

import numpy as np

from .atmosphere import slant_path_km
from .constants import GHZ, SPEED_OF_LIGHT_M_S
from .spectral_lines import TOY_VOC_LINES, ToySpectralLine


def free_space_path_loss_db(distance_km: np.ndarray | float, frequency_ghz: np.ndarray) -> np.ndarray:
    """Free space path loss in dB."""
    distance_m = np.asarray(distance_km, dtype=float) * 1000.0
    freq_hz = np.asarray(frequency_ghz, dtype=float) * GHZ
    wavelength_m = SPEED_OF_LIGHT_M_S / freq_hz
    return 20.0 * np.log10(4.0 * np.pi * distance_m[..., None] / wavelength_m)


def lorentzian_profile(frequency_ghz: np.ndarray, center_ghz: float, width_ghz: float) -> np.ndarray:
    """Unit peak Lorentzian line profile."""
    x = (frequency_ghz - center_ghz) / max(width_ghz, 1e-9)
    return 1.0 / (1.0 + x * x)


def gas_absorption_db(
    frequency_ghz: np.ndarray,
    gas_ppm: np.ndarray,
    elevation_deg: np.ndarray,
    lines: list[ToySpectralLine] | None = None,
) -> np.ndarray:
    """Synthetic molecular absorption in dB."""
    if lines is None:
        lines = TOY_VOC_LINES
    frequency = np.asarray(frequency_ghz, dtype=float)
    gas = np.asarray(gas_ppm, dtype=float)
    path = slant_path_km(elevation_deg)
    profile = np.zeros_like(frequency)
    for line in lines:
        profile += line.strength_db_per_ppm_km * lorentzian_profile(
            frequency,
            line.center_ghz,
            line.width_ghz,
        )
    return gas[:, None] * path[:, None] * profile[None, :]


def pm_rayleigh_loss_db(
    frequency_ghz: np.ndarray,
    pm_ug_m3: np.ndarray,
    elevation_deg: np.ndarray,
    reference_ghz: float = 200.0,
    coefficient_db_per_ug_m3_km: float = 0.000015,
) -> np.ndarray:
    """Smooth PM loss with a Rayleigh-like fourth power trend."""
    frequency = np.asarray(frequency_ghz, dtype=float)
    pm = np.asarray(pm_ug_m3, dtype=float)
    path = slant_path_km(elevation_deg)
    spectral_shape = (frequency / reference_ghz) ** 4
    return pm[:, None] * path[:, None] * coefficient_db_per_ug_m3_km * spectral_shape[None, :]


def synthesize_attenuation_db(
    frequency_ghz: np.ndarray,
    gas_ppm: np.ndarray,
    pm_ug_m3: np.ndarray,
    elevation_deg: np.ndarray,
    snr_db: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Create synthetic atmospheric attenuation spectra."""
    gas_loss = gas_absorption_db(frequency_ghz, gas_ppm, elevation_deg)
    pm_loss = pm_rayleigh_loss_db(frequency_ghz, pm_ug_m3, elevation_deg)
    atmospheric_loss = gas_loss + pm_loss
    noise_std_db = 1.0 / np.sqrt(10.0 ** (np.asarray(snr_db) / 10.0))
    noise = rng.normal(0.0, noise_std_db[:, None], size=atmospheric_loss.shape)
    return atmospheric_loss + noise


def relative_spectrum(attenuation_db: np.ndarray) -> np.ndarray:
    """Remove sample mean to focus estimators on spectral shape."""
    return attenuation_db - attenuation_db.mean(axis=1, keepdims=True)

