from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.constants import GHZ, SPEED_OF_LIGHT_M_S  # noqa: E402
from thz_isac.link_budget import aperture_gain_linear  # noqa: E402
from thz_isac.pilot_csi import (  # noqa: E402
    LOSChannelConfig,
    PilotCSIConfig,
    estimate_relative_attenuation_db,
    simulate_pilot_csi,
    simulate_pilot_estimation,
    synthesize_los_channel,
)


def test_simulation_shapes_and_aperture_gain_terms():
    frequency_ghz = np.array([100.0, 140.0, 220.0, 300.0])
    los_config = LOSChannelConfig(
        satellite_altitude_km=600.0,
        elevation_deg=45.0,
        tx_aperture_diameter_m=0.20,
        rx_aperture_diameter_m=0.50,
    )
    pilot_config = PilotCSIConfig(
        post_channel_snr_db=np.array([10.0, 15.0, 20.0, 25.0]),
        n_pilots=8,
        random_seed=7,
    )

    result = simulate_pilot_csi(
        frequency_ghz,
        los_config,
        pilot_config,
        atmospheric_loss_db=np.array([0.0, 0.5, 1.0, 1.5]),
    )

    assert result.los_channel.channel.shape == (4,)
    assert result.los_channel.atmospheric_loss_db.shape == (4,)
    assert result.los_channel.gain_source == "apertures"
    assert result.pilot_csi.unit_pilots.shape == (8, 4)
    assert result.pilot_csi.noise_samples.shape == (8, 4)
    assert result.pilot_csi.received_pilots.shape == (8, 4)
    assert result.pilot_csi.channel_estimate.shape == (4,)
    np.testing.assert_array_equal(result.pilot_csi.unit_pilots, np.ones((8, 4)))

    expected_tx_gain = aperture_gain_linear(frequency_ghz, 0.20, 0.65)
    expected_rx_gain = aperture_gain_linear(frequency_ghz, 0.50, 0.65)
    np.testing.assert_allclose(result.los_channel.tx_aperture_gain_linear, expected_tx_gain)
    np.testing.assert_allclose(result.los_channel.rx_aperture_gain_linear, expected_rx_gain)
    np.testing.assert_allclose(
        result.los_channel.link_power_gain_linear,
        expected_tx_gain * expected_rx_gain,
    )
    assert result.pilot_csi.estimated_atmospheric_loss_db is None


def test_los_channel_has_expected_amplitude_and_geometric_phase():
    frequency_ghz = np.array([90.0, 150.0, 310.0])
    atmospheric_loss_db = np.array([0.0, 2.0, 7.0])
    supplied_power_gain = np.array([4.0, 9.0, 16.0])
    config = LOSChannelConfig(
        satellite_altitude_km=500.0,
        elevation_deg=90.0,
        supplied_link_power_gain_linear=supplied_power_gain,
    )

    result = synthesize_los_channel(frequency_ghz, config, atmospheric_loss_db)

    frequency_hz = frequency_ghz * GHZ
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency_hz
    distance_m = 500_000.0
    expected_amplitude = (
        wavelength_m
        / (4.0 * np.pi * distance_m)
        * 10.0 ** (-atmospheric_loss_db / 20.0)
        * np.sqrt(supplied_power_gain)
    )
    expected_phase = -2.0 * np.pi * np.remainder(distance_m / wavelength_m, 1.0)

    np.testing.assert_allclose(result.slant_range_km, 500.0, atol=1e-10)
    np.testing.assert_allclose(np.abs(result.channel), expected_amplitude, rtol=1e-13)
    np.testing.assert_allclose(result.geometric_phase_rad, expected_phase, atol=1e-12)
    np.testing.assert_allclose(
        result.channel / np.abs(result.channel),
        np.exp(1j * expected_phase),
        atol=1e-12,
    )
    np.testing.assert_allclose(result.channel_power_gain_linear, expected_amplitude**2)


def test_averaged_pilot_estimate_is_unbiased_at_high_snr():
    true_channel = np.array([0.8 + 0.3j, -0.4 + 0.9j, 1.2 - 0.7j])
    result = simulate_pilot_estimation(
        true_channel,
        PilotCSIConfig(post_channel_snr_db=80.0, n_pilots=256, random_seed=23),
    )

    np.testing.assert_allclose(result.channel_estimate, true_channel, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(
        result.channel_estimate - true_channel,
        result.noise_samples.mean(axis=0),
        atol=1e-15,
    )
    np.testing.assert_allclose(
        result.noise_variance_per_pilot,
        np.abs(true_channel) ** 2 / 1e8,
    )


def test_pilot_averaging_reduces_empirical_and_theoretical_noise():
    n_tones = 8_000
    true_channel = np.full(n_tones, 1.0 + 0.5j)
    one_pilot = simulate_pilot_estimation(
        true_channel,
        PilotCSIConfig(post_channel_snr_db=5.0, n_pilots=1, random_seed=101),
    )
    sixteen_pilots = simulate_pilot_estimation(
        true_channel,
        PilotCSIConfig(post_channel_snr_db=5.0, n_pilots=16, random_seed=202),
    )

    mse_one = np.mean(np.abs(one_pilot.channel_estimate - true_channel) ** 2)
    mse_sixteen = np.mean(np.abs(sixteen_pilots.channel_estimate - true_channel) ** 2)

    assert mse_one > 12.0 * mse_sixteen
    assert mse_one < 20.0 * mse_sixteen
    np.testing.assert_allclose(
        one_pilot.channel_estimate_variance,
        16.0 * sixteen_pilots.channel_estimate_variance,
    )


def test_clear_sky_reference_recovers_atmospheric_attenuation():
    frequency_ghz = np.array([120.0, 180.0, 260.0, 340.0])
    atmospheric_loss_db = np.array([0.5, 2.0, 4.5, 8.0])
    los_config = LOSChannelConfig(
        satellite_altitude_km=700.0,
        elevation_deg=35.0,
        supplied_link_power_gain_linear=np.array([2.0, 3.0, 4.0, 5.0]),
    )
    clear_sky = synthesize_los_channel(frequency_ghz, los_config)

    result = simulate_pilot_csi(
        frequency_ghz,
        los_config,
        PilotCSIConfig(post_channel_snr_db=110.0, n_pilots=64, random_seed=11),
        atmospheric_loss_db=atmospheric_loss_db,
        clear_sky_reference_channel=clear_sky,
    )

    exact_attenuation = estimate_relative_attenuation_db(
        result.los_channel.channel,
        clear_sky.channel,
    )
    np.testing.assert_allclose(exact_attenuation, atmospheric_loss_db, atol=1e-12)
    np.testing.assert_allclose(
        result.pilot_csi.estimated_atmospheric_loss_db,
        atmospheric_loss_db,
        atol=1e-4,
    )
    np.testing.assert_allclose(
        result.pilot_csi.clear_sky_reference_channel,
        clear_sky.channel,
    )
