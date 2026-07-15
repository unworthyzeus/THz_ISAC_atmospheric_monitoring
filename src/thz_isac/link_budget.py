"""Auditable line of sight link budget helpers for a LEO sub THz link."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import GHZ, SPEED_OF_LIGHT_M_S


BOLTZMANN_J_K = 1.380649e-23
DEFAULT_EARTH_RADIUS_KM = 6_371.0


@dataclass(frozen=True)
class LEOLinkBudgetConfig:
    """Physical and receiver parameters for a per subcarrier link budget.

    ``tx_power_dbm`` is the total power across ``n_active_subcarriers``. When
    that count is omitted, the number of supplied frequency samples is used.
    ``implementation_loss_db`` can collect pointing, polarization, feeder,
    and other losses that are not represented separately.
    """

    satellite_altitude_km: float
    tx_power_dbm: float
    tx_aperture_diameter_m: float
    rx_aperture_diameter_m: float
    subcarrier_bandwidth_hz: float
    tx_aperture_efficiency: float = 0.65
    rx_aperture_efficiency: float = 0.65
    receiver_noise_figure_db: float = 5.0
    receiver_noise_temperature_k: float = 290.0
    implementation_loss_db: float = 0.0
    earth_radius_km: float = DEFAULT_EARTH_RADIUS_KM
    n_active_subcarriers: int | None = None

    def __post_init__(self) -> None:
        _require_finite_scalar("tx_power_dbm", self.tx_power_dbm)
        _require_positive_scalar("satellite_altitude_km", self.satellite_altitude_km)
        _require_positive_scalar("tx_aperture_diameter_m", self.tx_aperture_diameter_m)
        _require_positive_scalar("rx_aperture_diameter_m", self.rx_aperture_diameter_m)
        _require_positive_scalar("subcarrier_bandwidth_hz", self.subcarrier_bandwidth_hz)
        _require_positive_scalar("receiver_noise_temperature_k", self.receiver_noise_temperature_k)
        _require_positive_scalar("earth_radius_km", self.earth_radius_km)
        _require_efficiency("tx_aperture_efficiency", self.tx_aperture_efficiency)
        _require_efficiency("rx_aperture_efficiency", self.rx_aperture_efficiency)
        _require_nonnegative_scalar("receiver_noise_figure_db", self.receiver_noise_figure_db)
        _require_nonnegative_scalar("implementation_loss_db", self.implementation_loss_db)
        if self.n_active_subcarriers is not None:
            if isinstance(self.n_active_subcarriers, bool) or self.n_active_subcarriers < 1:
                raise ValueError("n_active_subcarriers must be a positive integer")
            if int(self.n_active_subcarriers) != self.n_active_subcarriers:
                raise ValueError("n_active_subcarriers must be a positive integer")


@dataclass(frozen=True)
class LEOLinkBudgetResult:
    """Intermediate and final terms from a per subcarrier link budget."""

    frequency_ghz: np.ndarray
    elevation_deg: np.ndarray
    slant_range_km: np.ndarray
    tx_gain_dbi: np.ndarray
    rx_gain_dbi: np.ndarray
    free_space_path_loss_db: np.ndarray
    atmospheric_loss_db: np.ndarray
    tx_power_per_subcarrier_dbm: float
    noise_power_per_subcarrier_dbm: float
    received_power_dbm: np.ndarray
    snr_db: np.ndarray

    @property
    def snr_linear(self) -> np.ndarray:
        """Return the per subcarrier SNR as a linear power ratio."""
        return 10.0 ** (self.snr_db / 10.0)


def leo_slant_range_km(
    elevation_deg: np.ndarray | float,
    satellite_altitude_km: float,
    earth_radius_km: float = DEFAULT_EARTH_RADIUS_KM,
) -> np.ndarray:
    """Return spherical Earth slant range from a surface terminal to a LEO satellite."""
    _require_positive_scalar("satellite_altitude_km", satellite_altitude_km)
    _require_positive_scalar("earth_radius_km", earth_radius_km)
    elevation = _finite_array("elevation_deg", elevation_deg)
    if np.any((elevation < 0.0) | (elevation > 90.0)):
        raise ValueError("elevation_deg must lie between 0 and 90 degrees")

    elevation_rad = np.deg2rad(elevation)
    orbital_radius_km = earth_radius_km + satellite_altitude_km
    range_km = np.sqrt(
        orbital_radius_km**2 - (earth_radius_km * np.cos(elevation_rad)) ** 2
    ) - earth_radius_km * np.sin(elevation_rad)
    return range_km


def aperture_gain_linear(
    frequency_ghz: np.ndarray | float,
    diameter_m: float,
    efficiency: float = 0.65,
) -> np.ndarray:
    """Return parabolic aperture power gain on a linear scale."""
    _require_positive_scalar("diameter_m", diameter_m)
    _require_efficiency("efficiency", efficiency)
    frequency = _positive_array("frequency_ghz", frequency_ghz) * GHZ
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency
    return efficiency * (np.pi * diameter_m / wavelength_m) ** 2


def aperture_gain_dbi(
    frequency_ghz: np.ndarray | float,
    diameter_m: float,
    efficiency: float = 0.65,
) -> np.ndarray:
    """Return parabolic aperture power gain in dBi."""
    return 10.0 * np.log10(aperture_gain_linear(frequency_ghz, diameter_m, efficiency))


def free_space_path_loss_db(
    distance_km: np.ndarray | float,
    frequency_ghz: np.ndarray | float,
) -> np.ndarray:
    """Return free space path loss using broadcast compatible inputs."""
    distance_m = _positive_array("distance_km", distance_km) * 1_000.0
    frequency_hz = _positive_array("frequency_ghz", frequency_ghz) * GHZ
    return 20.0 * np.log10(4.0 * np.pi * distance_m * frequency_hz / SPEED_OF_LIGHT_M_S)


def thermal_noise_power_dbm(
    bandwidth_hz: np.ndarray | float,
    noise_temperature_k: float = 290.0,
    noise_figure_db: float = 0.0,
) -> np.ndarray:
    """Return receiver thermal noise power including noise figure."""
    bandwidth = _positive_array("bandwidth_hz", bandwidth_hz)
    _require_positive_scalar("noise_temperature_k", noise_temperature_k)
    _require_nonnegative_scalar("noise_figure_db", noise_figure_db)
    thermal_watt = BOLTZMANN_J_K * noise_temperature_k * bandwidth
    return 10.0 * np.log10(thermal_watt / 1e-3) + noise_figure_db


def compute_leo_link_budget(
    frequency_ghz: np.ndarray | float,
    elevation_deg: np.ndarray | float,
    config: LEOLinkBudgetConfig,
    atmospheric_loss_db: np.ndarray | float = 0.0,
) -> LEOLinkBudgetResult:
    """Compute received power and SNR for every elevation and frequency pair.

    Returned link matrices have shape ``(n_elevations, n_frequencies)``.
    Atmospheric loss may be scalar, frequency only, or broadcast compatible
    with that matrix.
    """
    frequency = np.atleast_1d(_positive_array("frequency_ghz", frequency_ghz)).astype(float)
    elevation = np.atleast_1d(_finite_array("elevation_deg", elevation_deg)).astype(float)
    if frequency.ndim != 1 or elevation.ndim != 1:
        raise ValueError("frequency_ghz and elevation_deg must be scalars or one dimensional")

    slant_range = leo_slant_range_km(
        elevation,
        satellite_altitude_km=config.satellite_altitude_km,
        earth_radius_km=config.earth_radius_km,
    )
    tx_gain = aperture_gain_dbi(
        frequency,
        config.tx_aperture_diameter_m,
        config.tx_aperture_efficiency,
    )
    rx_gain = aperture_gain_dbi(
        frequency,
        config.rx_aperture_diameter_m,
        config.rx_aperture_efficiency,
    )
    fspl = free_space_path_loss_db(slant_range[:, None], frequency[None, :])
    atmospheric_loss = _broadcast_nonnegative_loss(
        atmospheric_loss_db,
        (len(elevation), len(frequency)),
    )

    n_active = config.n_active_subcarriers or len(frequency)
    tx_power_per_subcarrier = config.tx_power_dbm - 10.0 * np.log10(n_active)
    noise_power = float(
        thermal_noise_power_dbm(
            config.subcarrier_bandwidth_hz,
            config.receiver_noise_temperature_k,
            config.receiver_noise_figure_db,
        )
    )
    received_power = (
        tx_power_per_subcarrier
        + tx_gain[None, :]
        + rx_gain[None, :]
        - fspl
        - atmospheric_loss
        - config.implementation_loss_db
    )
    snr_db = received_power - noise_power

    return LEOLinkBudgetResult(
        frequency_ghz=frequency,
        elevation_deg=elevation,
        slant_range_km=slant_range,
        tx_gain_dbi=tx_gain,
        rx_gain_dbi=rx_gain,
        free_space_path_loss_db=fspl,
        atmospheric_loss_db=atmospheric_loss,
        tx_power_per_subcarrier_dbm=float(tx_power_per_subcarrier),
        noise_power_per_subcarrier_dbm=noise_power,
        received_power_dbm=received_power,
        snr_db=snr_db,
    )


def per_subcarrier_snr_db(
    frequency_ghz: np.ndarray | float,
    elevation_deg: np.ndarray | float,
    config: LEOLinkBudgetConfig,
    atmospheric_loss_db: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Return only the SNR matrix from :func:`compute_leo_link_budget`."""
    return compute_leo_link_budget(
        frequency_ghz,
        elevation_deg,
        config,
        atmospheric_loss_db,
    ).snr_db


def _finite_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def _positive_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = _finite_array(name, value)
    if np.any(array <= 0.0):
        raise ValueError(f"{name} must be strictly positive")
    return array


def _require_positive_scalar(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be strictly positive")


def _require_finite_scalar(name: str, value: float) -> None:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_nonnegative_scalar(name: str, value: float) -> None:
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be nonnegative")


def _require_efficiency(name: str, value: float) -> None:
    if not np.isfinite(value) or not 0.0 < value <= 1.0:
        raise ValueError(f"{name} must lie in the interval (0, 1]")


def _broadcast_nonnegative_loss(value: np.ndarray | float, shape: tuple[int, int]) -> np.ndarray:
    loss = _finite_array("atmospheric_loss_db", value)
    if np.any(loss < 0.0):
        raise ValueError("atmospheric_loss_db must be nonnegative")
    try:
        return np.array(np.broadcast_to(loss, shape), dtype=float, copy=True)
    except ValueError as exc:
        raise ValueError(
            f"atmospheric_loss_db with shape {loss.shape} cannot broadcast to {shape}"
        ) from exc
