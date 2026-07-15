"""Complex pilot CSI simulation for an auditable line of sight link."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import GHZ, SPEED_OF_LIGHT_M_S
from .link_budget import DEFAULT_EARTH_RADIUS_KM, aperture_gain_linear, leo_slant_range_km


@dataclass(frozen=True)
class LOSChannelConfig:
    """Geometry and gain inputs for a deterministic line of sight channel.

    Antenna gain can be calculated from two circular apertures or supplied as
    one combined power gain. The supplied gain excludes free space and
    atmospheric losses because those terms are calculated separately.
    """

    satellite_altitude_km: float
    elevation_deg: float
    tx_aperture_diameter_m: float | None = None
    rx_aperture_diameter_m: float | None = None
    tx_aperture_efficiency: float = 0.65
    rx_aperture_efficiency: float = 0.65
    supplied_link_power_gain_linear: np.ndarray | float | None = None
    earth_radius_km: float = DEFAULT_EARTH_RADIUS_KM

    def __post_init__(self) -> None:
        _require_positive_scalar("satellite_altitude_km", self.satellite_altitude_km)
        _require_finite_scalar("elevation_deg", self.elevation_deg)
        _require_positive_scalar("earth_radius_km", self.earth_radius_km)
        if not 0.0 <= self.elevation_deg <= 90.0:
            raise ValueError("elevation_deg must lie between 0 and 90 degrees")
        _require_efficiency("tx_aperture_efficiency", self.tx_aperture_efficiency)
        _require_efficiency("rx_aperture_efficiency", self.rx_aperture_efficiency)

        has_tx_aperture = self.tx_aperture_diameter_m is not None
        has_rx_aperture = self.rx_aperture_diameter_m is not None
        has_supplied_gain = self.supplied_link_power_gain_linear is not None
        if has_supplied_gain and (has_tx_aperture or has_rx_aperture):
            raise ValueError("supply either aperture diameters or link power gain, not both")
        if not has_supplied_gain and not (has_tx_aperture and has_rx_aperture):
            raise ValueError("both aperture diameters are required when link power gain is absent")
        if has_tx_aperture:
            _require_positive_scalar("tx_aperture_diameter_m", self.tx_aperture_diameter_m)
        if has_rx_aperture:
            _require_positive_scalar("rx_aperture_diameter_m", self.rx_aperture_diameter_m)
        if has_supplied_gain:
            gain = _finite_array(
                "supplied_link_power_gain_linear",
                self.supplied_link_power_gain_linear,
            )
            if np.any(gain <= 0.0):
                raise ValueError("supplied_link_power_gain_linear must be strictly positive")


@dataclass(frozen=True)
class LOSChannelResult:
    """Auditable terms used to construct the complex channel coefficient."""

    config: LOSChannelConfig
    frequency_ghz: np.ndarray
    frequency_hz: np.ndarray
    wavelength_m: np.ndarray
    slant_range_km: float
    free_space_amplitude: np.ndarray
    atmospheric_loss_db: np.ndarray
    atmospheric_amplitude: np.ndarray
    tx_aperture_gain_linear: np.ndarray | None
    rx_aperture_gain_linear: np.ndarray | None
    link_power_gain_linear: np.ndarray
    link_amplitude_gain: np.ndarray
    geometric_phase_rad: np.ndarray
    channel: np.ndarray
    gain_source: str

    @property
    def channel_power_gain_linear(self) -> np.ndarray:
        """Return the complete deterministic channel power gain."""
        return np.abs(self.channel) ** 2


@dataclass(frozen=True)
class PilotCSIConfig:
    """Pilot count, post channel SNR, and random seed.

    ``post_channel_snr_db`` is the noiseless received unit pilot power divided
    by circular complex noise power. It can be scalar or one value per tone.
    """

    post_channel_snr_db: np.ndarray | float
    n_pilots: int = 1
    random_seed: int | None = 0

    def __post_init__(self) -> None:
        _finite_array("post_channel_snr_db", self.post_channel_snr_db)
        if (
            isinstance(self.n_pilots, bool)
            or not isinstance(self.n_pilots, (int, np.integer))
            or self.n_pilots < 1
        ):
            raise ValueError("n_pilots must be a positive integer")
        if self.random_seed is not None and (
            isinstance(self.random_seed, bool)
            or not isinstance(self.random_seed, (int, np.integer))
            or self.random_seed < 0
        ):
            raise ValueError("random_seed must be a nonnegative integer or None")


@dataclass(frozen=True)
class PilotCSIResult:
    """Pilot observations, noise terms, and the averaged CSI estimate."""

    config: PilotCSIConfig
    true_channel: np.ndarray
    unit_pilots: np.ndarray
    noise_samples: np.ndarray
    received_pilots: np.ndarray
    post_channel_snr_db: np.ndarray
    post_channel_snr_linear: np.ndarray
    noise_variance_per_pilot: np.ndarray
    noise_component_standard_deviation: np.ndarray
    channel_estimate_variance: np.ndarray
    channel_estimate: np.ndarray
    clear_sky_reference_channel: np.ndarray | None
    estimated_atmospheric_loss_db: np.ndarray | None


@dataclass(frozen=True)
class PilotCSISimulationResult:
    """Deterministic LOS channel and its noisy pilot observation."""

    los_channel: LOSChannelResult
    pilot_csi: PilotCSIResult


def synthesize_los_channel(
    frequency_ghz: np.ndarray | float,
    config: LOSChannelConfig,
    atmospheric_loss_db: np.ndarray | float = 0.0,
) -> LOSChannelResult:
    """Synthesize a narrowband LOS coefficient at every supplied frequency.

    The coefficient uses spherical Earth range, Friis free space amplitude,
    atmospheric amplitude attenuation, antenna or supplied link gain, and the
    wrapped propagation phase convention ``exp(-j 2 pi f r / c)``.
    """
    frequency = _positive_vector("frequency_ghz", frequency_ghz)
    frequency_hz = frequency * GHZ
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency_hz
    slant_range_km = float(
        np.asarray(
            leo_slant_range_km(
                config.elevation_deg,
                config.satellite_altitude_km,
                config.earth_radius_km,
            )
        ).item()
    )
    distance_m = slant_range_km * 1_000.0

    atmospheric_loss = _broadcast_vector(
        "atmospheric_loss_db",
        atmospheric_loss_db,
        len(frequency),
    )
    if np.any(atmospheric_loss < 0.0):
        raise ValueError("atmospheric_loss_db must be nonnegative")

    if config.supplied_link_power_gain_linear is None:
        tx_gain = aperture_gain_linear(
            frequency,
            config.tx_aperture_diameter_m,
            config.tx_aperture_efficiency,
        )
        rx_gain = aperture_gain_linear(
            frequency,
            config.rx_aperture_diameter_m,
            config.rx_aperture_efficiency,
        )
        link_power_gain = tx_gain * rx_gain
        gain_source = "apertures"
    else:
        tx_gain = None
        rx_gain = None
        link_power_gain = _broadcast_vector(
            "supplied_link_power_gain_linear",
            config.supplied_link_power_gain_linear,
            len(frequency),
        )
        if np.any(link_power_gain <= 0.0):
            raise ValueError("supplied_link_power_gain_linear must be strictly positive")
        gain_source = "supplied_link_power_gain"

    free_space_amplitude = wavelength_m / (4.0 * np.pi * distance_m)
    atmospheric_amplitude = 10.0 ** (-atmospheric_loss / 20.0)
    link_amplitude_gain = np.sqrt(link_power_gain)
    total_amplitude = free_space_amplitude * atmospheric_amplitude * link_amplitude_gain

    phase_cycles = np.remainder(distance_m / wavelength_m, 1.0)
    geometric_phase_rad = -2.0 * np.pi * phase_cycles
    channel = total_amplitude * np.exp(1j * geometric_phase_rad)

    return LOSChannelResult(
        config=config,
        frequency_ghz=frequency,
        frequency_hz=frequency_hz,
        wavelength_m=wavelength_m,
        slant_range_km=slant_range_km,
        free_space_amplitude=free_space_amplitude,
        atmospheric_loss_db=atmospheric_loss,
        atmospheric_amplitude=atmospheric_amplitude,
        tx_aperture_gain_linear=tx_gain,
        rx_aperture_gain_linear=rx_gain,
        link_power_gain_linear=link_power_gain,
        link_amplitude_gain=link_amplitude_gain,
        geometric_phase_rad=geometric_phase_rad,
        channel=channel,
        gain_source=gain_source,
    )


def simulate_pilot_estimation(
    channel: np.ndarray,
    config: PilotCSIConfig,
    clear_sky_reference_channel: LOSChannelResult | np.ndarray | None = None,
) -> PilotCSIResult:
    """Send unit pilots through a complex channel and average the CSI estimate.

    Noise is circular complex Gaussian. For tone ``k``, its variance
    ``E[|n_k|^2]`` is ``|h_k|^2 / SNR_k``. Real and imaginary components each
    have half that variance.
    """
    true_channel = _complex_vector("channel", channel)
    if np.any(np.abs(true_channel) == 0.0):
        raise ValueError("channel magnitudes must be strictly positive")

    snr_db = _broadcast_vector(
        "post_channel_snr_db",
        config.post_channel_snr_db,
        len(true_channel),
    )
    with np.errstate(over="ignore", under="ignore"):
        snr_linear = 10.0 ** (snr_db / 10.0)
    if not np.all(np.isfinite(snr_linear)) or np.any(snr_linear <= 0.0):
        raise ValueError("post_channel_snr_db must produce a finite positive linear SNR")

    noise_variance = np.abs(true_channel) ** 2 / snr_linear
    component_std = np.sqrt(noise_variance / 2.0)
    observation_shape = (int(config.n_pilots), len(true_channel))
    rng = np.random.default_rng(config.random_seed)
    noise = component_std[None, :] * (
        rng.normal(size=observation_shape) + 1j * rng.normal(size=observation_shape)
    )
    unit_pilots = np.ones(observation_shape, dtype=complex)
    received_pilots = unit_pilots * true_channel[None, :] + noise
    channel_estimate = np.mean(np.conj(unit_pilots) * received_pilots, axis=0)

    clear_sky_reference = None
    attenuation_estimate = None
    if clear_sky_reference_channel is not None:
        if isinstance(clear_sky_reference_channel, LOSChannelResult):
            clear_sky_reference = clear_sky_reference_channel.channel.copy()
        else:
            clear_sky_reference = _complex_vector(
                "clear_sky_reference_channel",
                clear_sky_reference_channel,
            )
        if clear_sky_reference.shape != true_channel.shape:
            raise ValueError("clear_sky_reference_channel must match the channel shape")
        attenuation_estimate = estimate_relative_attenuation_db(
            channel_estimate,
            clear_sky_reference,
        )

    return PilotCSIResult(
        config=config,
        true_channel=true_channel,
        unit_pilots=unit_pilots,
        noise_samples=noise,
        received_pilots=received_pilots,
        post_channel_snr_db=snr_db,
        post_channel_snr_linear=snr_linear,
        noise_variance_per_pilot=noise_variance,
        noise_component_standard_deviation=component_std,
        channel_estimate_variance=noise_variance / config.n_pilots,
        channel_estimate=channel_estimate,
        clear_sky_reference_channel=clear_sky_reference,
        estimated_atmospheric_loss_db=attenuation_estimate,
    )


def simulate_pilot_csi(
    frequency_ghz: np.ndarray | float,
    los_config: LOSChannelConfig,
    pilot_config: PilotCSIConfig,
    atmospheric_loss_db: np.ndarray | float = 0.0,
    clear_sky_reference_channel: LOSChannelResult | np.ndarray | None = None,
) -> PilotCSISimulationResult:
    """Construct the LOS channel and simulate its pilot based CSI estimate."""
    los_channel = synthesize_los_channel(
        frequency_ghz,
        los_config,
        atmospheric_loss_db,
    )
    pilot_csi = simulate_pilot_estimation(
        los_channel.channel,
        pilot_config,
        clear_sky_reference_channel,
    )
    return PilotCSISimulationResult(los_channel=los_channel, pilot_csi=pilot_csi)


def estimate_relative_attenuation_db(
    channel_estimate: np.ndarray,
    clear_sky_reference_channel: np.ndarray,
) -> np.ndarray:
    """Estimate positive excess attenuation from a clear sky amplitude ratio."""
    estimate = _complex_vector("channel_estimate", channel_estimate)
    reference = _complex_vector("clear_sky_reference_channel", clear_sky_reference_channel)
    if estimate.shape != reference.shape:
        raise ValueError("channel_estimate and clear_sky_reference_channel must have equal shape")
    if np.any(np.abs(estimate) == 0.0) or np.any(np.abs(reference) == 0.0):
        raise ValueError("channel and clear sky reference magnitudes must be strictly positive")
    return 20.0 * np.log10(np.abs(reference) / np.abs(estimate))


def _finite_array(name: str, value: np.ndarray | float | None) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def _positive_vector(name: str, value: np.ndarray | float) -> np.ndarray:
    array = _finite_array(name, value)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError(f"{name} must be scalar or one dimensional")
    if np.any(array <= 0.0):
        raise ValueError(f"{name} must be strictly positive")
    return np.array(array, dtype=float, copy=True)


def _complex_vector(name: str, value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=complex)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite scalar or one dimensional vector")
    return np.array(array, dtype=complex, copy=True)


def _broadcast_vector(name: str, value: np.ndarray | float, length: int) -> np.ndarray:
    array = _finite_array(name, value)
    if array.ndim > 1:
        raise ValueError(f"{name} must be scalar or one dimensional")
    try:
        broadcast = np.broadcast_to(array, (length,))
    except ValueError as exc:
        raise ValueError(f"{name} with shape {array.shape} cannot broadcast to {length} tones") from exc
    return np.array(broadcast, dtype=float, copy=True)


def _require_positive_scalar(name: str, value: float | None) -> None:
    if value is None or not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be strictly positive")


def _require_finite_scalar(name: str, value: float) -> None:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_efficiency(name: str, value: float) -> None:
    if not np.isfinite(value) or not 0.0 < value <= 1.0:
        raise ValueError(f"{name} must lie in the interval (0, 1]")
