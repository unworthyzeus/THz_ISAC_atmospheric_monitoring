"""Column normalized HITRAN attenuation for satellite gas products.

Satellite retrievals commonly report vertical columns in molecules per square
centimetre, whereas :mod:`thz_isac.physical_spectroscopy` starts from a
surface mass concentration and an assumed vertical decay. This module keeps
the satellite quantity in its native units. A declared vertical profile
allocates the measured column among pressure and temperature layers, then the
layer dependent HITRAN cross sections are integrated.

Column domain is part of every gas key. This matters because, for example,
the ESA CCI merged CO product is a total column while the ESA CCI OMI NO2
product is a tropospheric column. The domain label records that distinction;
it does not claim that the supplied atmosphere extends far enough to represent
a total atmospheric column. Model top and vertical profile remain explicit
forward model assumptions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

from .physical_spectroscopy import (
    DB_PER_NEPER,
    AtmosphereProfile,
    molecular_cross_section_cm2_per_molecule,
)


class ColumnDomain(str, Enum):
    """Vertical domain declared by a gas column product."""

    TOTAL_COLUMN = "total_column"
    TROPOSPHERIC_COLUMN = "tropospheric_column"


@dataclass(frozen=True)
class GasColumnKey:
    """Identify a molecular column without discarding its vertical domain."""

    molecule: str
    column_domain: ColumnDomain | str

    def __post_init__(self) -> None:
        molecule = self.molecule
        if not isinstance(molecule, str) or not molecule.strip():
            raise ValueError("Molecule must be a nonempty string.")
        if molecule != molecule.strip():
            raise ValueError("Molecule must not contain leading or trailing whitespace.")
        try:
            domain = ColumnDomain(self.column_domain)
        except (TypeError, ValueError) as exc:
            supported = [domain.value for domain in ColumnDomain]
            raise ValueError(f"Column domain must be one of {supported}.") from exc
        object.__setattr__(self, "column_domain", domain)


@dataclass(frozen=True)
class GasColumnProfile:
    """Declare how one satellite column is distributed among model layers.

    Exactly one of ``normalized_layer_weights`` and ``scale_height_m`` must be
    supplied. Explicit weights are column fractions and must already be
    nonnegative and sum to one. A scale height generates midpoint quadrature
    weights proportional to ``exp(-altitude / scale_height) * layer_thickness``.
    """

    molecule: str
    column_domain: ColumnDomain | str
    normalized_layer_weights: np.ndarray | None = None
    scale_height_m: float | None = None

    @property
    def key(self) -> GasColumnKey:
        """Return the domain aware key for this profile."""

        return GasColumnKey(self.molecule, self.column_domain)


@dataclass(frozen=True)
class ColumnAttenuationDesign:
    """Layer resolved attenuation coefficients for vertical gas columns.

    ``attenuation_db_per_molecule_cm2`` has shape ``(frequency, gas)`` and
    represents dB divided by a column amount in molecules per square
    centimetre. Multiplying a column by the corresponding coefficient returns
    attenuation in dB.

    ``layer_cross_section_cm2_per_molecule`` has shape
    ``(layer, frequency, gas)`` and ``normalized_layer_weights`` has shape
    ``(layer, gas)``. They are retained so callers can audit the layer
    integration rather than relying on an opaque aggregate coefficient.
    """

    frequency_ghz: np.ndarray
    column_keys: tuple[GasColumnKey, ...]
    attenuation_db_per_molecule_cm2: np.ndarray
    normalized_layer_weights: np.ndarray
    layer_cross_section_cm2_per_molecule: np.ndarray
    atmosphere: AtmosphereProfile

    @property
    def gas_names(self) -> tuple[str, ...]:
        """Return gas names in design matrix column order."""

        return tuple(key.molecule for key in self.column_keys)

    @property
    def column_domains(self) -> tuple[ColumnDomain, ...]:
        """Return column domains in design matrix column order."""

        return tuple(key.column_domain for key in self.column_keys)

    def layer_columns_molecules_cm2(
        self,
        columns_molecules_cm2: Mapping[GasColumnKey, float],
    ) -> np.ndarray:
        """Allocate declared columns to layers in molecules per square centimetre."""

        values = self._column_vector(columns_molecules_cm2)
        return self.normalized_layer_weights * values[None, :]

    def attenuation_db(
        self,
        columns_molecules_cm2: Mapping[GasColumnKey, float],
    ) -> np.ndarray:
        """Calculate attenuation from aggregate per column coefficients."""

        values = self._column_vector(columns_molecules_cm2)
        return self.attenuation_db_per_molecule_cm2 @ values

    def direct_layer_attenuation_db(
        self,
        columns_molecules_cm2: Mapping[GasColumnKey, float],
    ) -> np.ndarray:
        """Calculate attenuation by explicitly summing layer optical depths."""

        layer_columns = self.layer_columns_molecules_cm2(columns_molecules_cm2)
        optical_depth = np.einsum(
            "lfg,lg->f",
            self.layer_cross_section_cm2_per_molecule,
            layer_columns,
        )
        return DB_PER_NEPER * optical_depth

    def _column_vector(
        self,
        columns_molecules_cm2: Mapping[GasColumnKey, float],
    ) -> np.ndarray:
        if not isinstance(columns_molecules_cm2, Mapping):
            raise TypeError("Columns must be a mapping keyed by GasColumnKey.")
        key_to_index = {key: index for index, key in enumerate(self.column_keys)}
        values = np.zeros(len(self.column_keys), dtype=float)
        for key, raw_value in columns_molecules_cm2.items():
            if not isinstance(key, GasColumnKey):
                raise TypeError("Every column mapping key must be a GasColumnKey.")
            if key not in key_to_index:
                configured_domains = [
                    configured.column_domain.value
                    for configured in self.column_keys
                    if configured.molecule == key.molecule
                ]
                if configured_domains:
                    raise ValueError(
                        f"Column domain mismatch for {key.molecule}: configured "
                        f"{configured_domains}, received {key.column_domain.value}."
                    )
                raise ValueError(f"Column key {key} is not configured in this design.")
            value = float(raw_value)
            if not np.isfinite(value) or value < 0.0:
                raise ValueError("Column amounts must be finite and nonnegative.")
            values[key_to_index[key]] = value
        return values


def build_column_attenuation_design(
    hitran_lines: pd.DataFrame,
    frequency_ghz: np.ndarray,
    gas_profiles: Sequence[GasColumnProfile],
    *,
    atmosphere: AtmosphereProfile,
    partition_sum_version: int = 2025,
) -> ColumnAttenuationDesign:
    """Build a domain aware HITRAN design for vertical satellite columns.

    The supplied atmosphere defines the modeled layers. Each profile allocates
    one complete declared column among those layers. A ``total_column`` label
    is therefore metadata and a consistency guard, not an implicit extension
    of a tropospheric atmosphere to the top of the atmosphere.
    """

    frequency = _validate_frequency_grid(frequency_ghz)
    _validate_atmosphere(atmosphere)
    profiles = tuple(gas_profiles)
    if not profiles:
        raise ValueError("At least one gas column profile is required.")
    if not all(isinstance(profile, GasColumnProfile) for profile in profiles):
        raise TypeError("Every gas profile must be a GasColumnProfile.")

    keys = tuple(profile.key for profile in profiles)
    if len(set(keys)) != len(keys):
        raise ValueError("Gas column keys must be unique.")
    molecules = [key.molecule for key in keys]
    if len(set(molecules)) != len(molecules):
        raise ValueError("A molecule may appear only once in a column design.")

    weights = np.column_stack(
        [_profile_weights(profile, atmosphere) for profile in profiles]
    )
    gas_cross_sections = []
    for key in keys:
        layer_cross_sections = np.vstack(
            [
                molecular_cross_section_cm2_per_molecule(
                    hitran_lines,
                    frequency,
                    key.molecule,
                    temperature_k=float(temperature_k),
                    pressure_pa=float(pressure_pa),
                    partition_sum_version=partition_sum_version,
                )
                for temperature_k, pressure_pa in zip(
                    atmosphere.temperature_k,
                    atmosphere.pressure_pa,
                    strict=True,
                )
            ]
        )
        gas_cross_sections.append(layer_cross_sections)
    cross_sections = np.stack(gas_cross_sections, axis=2)
    coefficients = DB_PER_NEPER * np.einsum(
        "lfg,lg->fg",
        cross_sections,
        weights,
    )
    if not np.isfinite(coefficients).all() or np.any(coefficients < 0.0):
        raise FloatingPointError("Column attenuation coefficients are nonfinite or negative.")

    return ColumnAttenuationDesign(
        frequency_ghz=frequency.copy(),
        column_keys=keys,
        attenuation_db_per_molecule_cm2=coefficients,
        normalized_layer_weights=weights,
        layer_cross_section_cm2_per_molecule=cross_sections,
        atmosphere=atmosphere,
    )


def _profile_weights(
    profile: GasColumnProfile,
    atmosphere: AtmosphereProfile,
) -> np.ndarray:
    explicit = profile.normalized_layer_weights
    scale_height = profile.scale_height_m
    if (explicit is None) == (scale_height is None):
        raise ValueError(
            f"{profile.molecule} must declare exactly one of normalized layer "
            "weights and scale height."
        )

    n_layers = atmosphere.altitude_m.size
    if explicit is not None:
        weights = np.asarray(explicit, dtype=float)
        if weights.ndim != 1 or weights.shape != (n_layers,):
            raise ValueError(
                f"{profile.molecule} layer weights must have shape ({n_layers},)."
            )
        if not np.isfinite(weights).all() or np.any(weights < 0.0):
            raise ValueError("Normalized layer weights must be finite and nonnegative.")
        if not np.isclose(np.sum(weights), 1.0, rtol=0.0, atol=1.0e-10):
            raise ValueError("Normalized layer weights must sum to one.")
        return weights.copy()

    height = float(scale_height)
    if not np.isfinite(height) or height <= 0.0:
        raise ValueError("Scale height must be finite and positive.")
    log_weights = (
        -atmosphere.altitude_m / height
        + np.log(atmosphere.layer_thickness_m)
    )
    log_weights -= np.max(log_weights)
    weights = np.exp(log_weights)
    weight_sum = np.sum(weights)
    if not np.isfinite(weight_sum) or weight_sum <= 0.0:
        raise FloatingPointError("Exponential profile weights could not be normalized.")
    return weights / weight_sum


def _validate_frequency_grid(frequency_ghz: np.ndarray) -> np.ndarray:
    frequency = np.asarray(frequency_ghz, dtype=float)
    if frequency.ndim != 1 or frequency.size == 0:
        raise ValueError("Frequency grid must be a nonempty one dimensional array.")
    if not np.isfinite(frequency).all() or np.any(frequency <= 0.0):
        raise ValueError("Frequencies must be finite and positive.")
    return frequency


def _validate_atmosphere(atmosphere: AtmosphereProfile) -> None:
    if not isinstance(atmosphere, AtmosphereProfile):
        raise TypeError("Atmosphere must be an AtmosphereProfile.")
    arrays = (
        atmosphere.altitude_m,
        atmosphere.layer_thickness_m,
        atmosphere.temperature_k,
        atmosphere.pressure_pa,
    )
    if any(np.asarray(values).ndim != 1 for values in arrays):
        raise ValueError("Atmosphere properties must be one dimensional arrays.")
    sizes = {np.asarray(values).size for values in arrays}
    if len(sizes) != 1 or not sizes or next(iter(sizes)) == 0:
        raise ValueError("Atmosphere properties must have the same nonzero length.")
    if not all(np.isfinite(values).all() for values in arrays):
        raise ValueError("Atmosphere properties must be finite.")
    if np.any(atmosphere.altitude_m < 0.0):
        raise ValueError("Atmosphere altitudes must be nonnegative.")
    if np.any(np.diff(atmosphere.altitude_m) <= 0.0):
        raise ValueError("Atmosphere altitudes must be strictly increasing.")
    if np.any(atmosphere.layer_thickness_m <= 0.0):
        raise ValueError("Atmosphere layer thicknesses must be positive.")
    if np.any(atmosphere.temperature_k <= 0.0):
        raise ValueError("Atmosphere temperatures must be positive.")
    if np.any(atmosphere.pressure_pa <= 0.0):
        raise ValueError("Atmosphere pressures must be positive.")
