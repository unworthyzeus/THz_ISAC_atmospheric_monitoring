"""Synthetic spectral lines used before HITRAN integration.

These are toy markers. They are not HITRAN line positions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToySpectralLine:
    center_ghz: float
    width_ghz: float
    strength_db_per_ppm_km: float


TOY_VOC_LINES = [
    ToySpectralLine(center_ghz=91.0, width_ghz=1.8, strength_db_per_ppm_km=0.0006),
    ToySpectralLine(center_ghz=183.0, width_ghz=2.5, strength_db_per_ppm_km=0.0009),
    ToySpectralLine(center_ghz=278.0, width_ghz=3.0, strength_db_per_ppm_km=0.0007),
    ToySpectralLine(center_ghz=337.0, width_ghz=2.0, strength_db_per_ppm_km=0.0005),
]

