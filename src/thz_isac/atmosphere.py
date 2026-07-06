"""Simple atmosphere helpers for early experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AtmosphereLayer:
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    relative_density: float


def standard_troposphere_layers(
    n_layers: int = 24,
    top_altitude_m: float = 12_000.0,
) -> list[AtmosphereLayer]:
    """Return a coarse standard troposphere profile."""
    altitudes = np.linspace(0.0, top_altitude_m, n_layers)
    layers: list[AtmosphereLayer] = []
    for altitude_m in altitudes:
        temperature_k = 288.15 - 0.0065 * altitude_m
        pressure_pa = 101_325.0 * (temperature_k / 288.15) ** 5.255
        relative_density = pressure_pa / 101_325.0 * 288.15 / temperature_k
        layers.append(
            AtmosphereLayer(
                altitude_m=float(altitude_m),
                temperature_k=float(temperature_k),
                pressure_pa=float(pressure_pa),
                relative_density=float(relative_density),
            )
        )
    return layers


def slant_path_km(elevation_deg: np.ndarray | float, troposphere_height_km: float = 12.0) -> np.ndarray:
    """Approximate the tropospheric slant path for a satellite elevation angle."""
    elevation = np.asarray(elevation_deg, dtype=float)
    elevation = np.clip(elevation, 2.0, 90.0)
    return troposphere_height_km / np.sin(np.deg2rad(elevation))

