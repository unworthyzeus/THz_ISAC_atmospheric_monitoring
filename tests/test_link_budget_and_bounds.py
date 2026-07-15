from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.estimation_bounds import (  # noqa: E402
    crb_detection_floor,
    gas_detection_floor_ppm,
    gas_ppm_to_ug_m3,
    gas_ug_m3_to_ppm,
    linear_attenuation_crb,
    linear_gaussian_fisher_information,
    pilot_averaged_attenuation_variance_db2,
    weighted_least_squares,
)
from thz_isac.link_budget import (  # noqa: E402
    LEOLinkBudgetConfig,
    aperture_gain_dbi,
    compute_leo_link_budget,
    leo_slant_range_km,
    thermal_noise_power_dbm,
)


def _link_config() -> LEOLinkBudgetConfig:
    return LEOLinkBudgetConfig(
        satellite_altitude_km=600.0,
        tx_power_dbm=40.0,
        tx_aperture_diameter_m=0.20,
        rx_aperture_diameter_m=0.50,
        subcarrier_bandwidth_hz=1e6,
        receiver_noise_figure_db=5.0,
        implementation_loss_db=2.0,
        n_active_subcarriers=4,
    )


def test_leo_slant_range_has_zenith_limit_and_elevation_trend():
    ranges = leo_slant_range_km(np.array([10.0, 30.0, 90.0]), satellite_altitude_km=600.0)

    assert ranges[0] > ranges[1] > ranges[2]
    np.testing.assert_allclose(ranges[2], 600.0, rtol=0.0, atol=1e-10)


def test_aperture_gain_and_thermal_noise_reference_values():
    gains = aperture_gain_dbi(np.array([100.0, 200.0]), diameter_m=0.3, efficiency=0.65)
    noise_dbm_hz = thermal_noise_power_dbm(1.0, noise_temperature_k=290.0)

    np.testing.assert_allclose(gains[1] - gains[0], 20.0 * np.log10(2.0), atol=1e-12)
    np.testing.assert_allclose(noise_dbm_hz, -173.975, atol=0.01)


def test_link_budget_snr_improves_with_elevation_and_tracks_added_loss():
    config = _link_config()
    nominal = compute_leo_link_budget(
        frequency_ghz=np.array([140.0, 150.0]),
        elevation_deg=np.array([15.0, 80.0]),
        config=config,
    )
    attenuated = compute_leo_link_budget(
        frequency_ghz=np.array([140.0, 150.0]),
        elevation_deg=np.array([15.0, 80.0]),
        config=config,
        atmospheric_loss_db=7.0,
    )

    assert nominal.snr_db.shape == (2, 2)
    assert np.all(nominal.snr_db[1] > nominal.snr_db[0])
    np.testing.assert_allclose(nominal.snr_db - attenuated.snr_db, 7.0, atol=1e-12)
    np.testing.assert_allclose(nominal.tx_power_per_subcarrier_dbm, 40.0 - 10.0 * np.log10(4.0))
    np.testing.assert_allclose(nominal.snr_linear, 10.0 ** (nominal.snr_db / 10.0))


def test_pilot_variance_has_inverse_sqrt_count_and_snr_trends():
    variance_four = pilot_averaged_attenuation_variance_db2(100.0, 4)
    variance_sixteen = pilot_averaged_attenuation_variance_db2(100.0, 16)
    low_snr = pilot_averaged_attenuation_variance_db2(1.0, 16)
    high_snr = pilot_averaged_attenuation_variance_db2(1_000.0, 16)
    residual_floor = pilot_averaged_attenuation_variance_db2(
        100.0,
        16,
        residual_error_std_db=0.5,
    )

    expected_four = (10.0 / np.log(10.0)) ** 2 / 4.0 * (1.0 + 1.0 / 100.0) ** 2
    np.testing.assert_allclose(variance_four, expected_four, atol=1e-12)
    np.testing.assert_allclose(np.sqrt(variance_four / variance_sixteen), 2.0, atol=1e-12)
    np.testing.assert_allclose(residual_floor, variance_sixteen + 0.5**2, atol=1e-12)
    assert low_snr > high_snr


def test_heteroscedastic_diagonal_design_has_analytic_crb():
    design = np.eye(2)
    variance = np.array([4.0, 9.0])

    fisher = linear_gaussian_fisher_information(design, variance)
    result = linear_attenuation_crb(design, variance)

    np.testing.assert_allclose(fisher, np.diag([0.25, 1.0 / 9.0]))
    np.testing.assert_allclose(result.target_covariance, np.diag(variance))
    np.testing.assert_allclose(result.target_standard_deviation, np.array([2.0, 3.0]))
    np.testing.assert_allclose(crb_detection_floor(result), np.array([2.0, 3.0]))
    assert result.target_identifiable
    assert result.target_rank == 2


def test_nuisance_parameter_degrades_target_crb_by_schur_complement():
    target = np.arange(4.0)[:, None]
    nuisance = np.ones((4, 1))

    without_nuisance = linear_attenuation_crb(target, 1.0)
    with_nuisance = linear_attenuation_crb(target, 1.0, nuisance_design=nuisance)

    np.testing.assert_allclose(without_nuisance.target_variance, np.array([1.0 / 14.0]))
    np.testing.assert_allclose(with_nuisance.target_variance, np.array([1.0 / 5.0]))
    assert with_nuisance.target_standard_deviation[0] > without_nuisance.target_standard_deviation[0]
    assert with_nuisance.full_parameter_rank == 2
    assert np.isfinite(with_nuisance.target_condition_number)


def test_rank_deficient_target_design_reports_infinite_floor():
    target = np.column_stack([np.ones(5), np.ones(5)])
    result = linear_attenuation_crb(target, 1.0)

    assert not result.target_identifiable
    assert result.target_rank == 1
    assert np.isinf(result.target_standard_deviation).all()
    assert np.isinf(result.target_condition_number)


def test_gas_mass_ppm_conversion_round_trip_and_detection_floor():
    no2_molar_mass = 46.0055
    concentration_ug_m3 = 1_000.0
    ppm = gas_ug_m3_to_ppm(concentration_ug_m3, no2_molar_mass)
    recovered = gas_ppm_to_ug_m3(ppm, no2_molar_mass)

    np.testing.assert_allclose(ppm, 0.5319, rtol=2e-3)
    np.testing.assert_allclose(recovered, concentration_ug_m3, rtol=1e-12)
    np.testing.assert_allclose(
        gas_detection_floor_ppm(10.0, no2_molar_mass),
        gas_ug_m3_to_ppm(10.0, no2_molar_mass),
    )


def test_weighted_least_squares_recovers_linear_parameters_and_covariance():
    design = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    true_parameters = np.array([2.0, -1.0])
    variance = np.array([1.0, 4.0, 1.0])
    observations = design @ true_parameters

    result = weighted_least_squares(design, observations, variance)
    expected_covariance = np.linalg.inv(linear_gaussian_fisher_information(design, variance))

    np.testing.assert_allclose(result.estimate, true_parameters, atol=1e-12)
    np.testing.assert_allclose(result.covariance, expected_covariance, atol=1e-12)
    np.testing.assert_allclose(result.weighted_residual_sum_squares, 0.0, atol=1e-24)
    assert result.full_rank
