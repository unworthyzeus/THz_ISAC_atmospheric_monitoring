import numpy as np
import pytest
from thz_isac.evidence_closure import (requirement_assessment, tds_transfer,
    projected_design, covariance_from_information_rows, conditional_power, ofdm_qpsk_control)


def test_favorable_limit_cannot_override_domain_and_coverage():
    result = requirement_assessment(reference_domain="indoor", measured_domain="slant column",
        averaging_s=1800, covered_s=140, paired_reference=False, calibrated=False,
        limit_ug_m3=100, modeled_lod_ug_m3=10)
    assert result["modeled_sensitivity_sufficient"]
    assert not result["evidence_complete"] and not result["compliance_demonstrated"]
    assert "measurement_domain_mismatch" in result["reasons"]
    assert "averaging_period_not_covered" in result["reasons"]


def test_tds_amplitude_to_power_db_and_frequency_units():
    t = np.arange(1000) * .04
    pulse = np.exp(-((t - 20) / .6) ** 2)
    result = tds_transfer(t, pulse * .5, pulse)
    selected = (result["frequency_ghz"] >= 300) & (result["frequency_ghz"] <= 400)
    np.testing.assert_allclose(result["attenuation_db"][selected], 20 * np.log10(2))
    assert result["resolution_ghz"] == pytest.approx(25)


def test_tds_rejects_nonuniform_grid():
    with pytest.raises(ValueError, match="Uniform"):
        tds_transfer([0, 1, 2, 4], [1, 2, 3, 4], [2, 3, 4, 5])


def test_nuisance_and_auxiliary_information():
    x = np.arange(8.)
    p = projected_design(np.c_[x, x], np.ones((8, 1)), np.eye(8))
    with pytest.raises(ValueError, match="Unidentifiable"):
        covariance_from_information_rows(p)
    covariance = covariance_from_information_rows(np.vstack((p, [1, 0])))
    assert covariance[0, 0] == pytest.approx(1)
    np.testing.assert_allclose(covariance, np.linalg.inv(np.vstack((p, [1, 0])).T @ np.vstack((p, [1, 0]))))


def test_declared_detection_limit_has_required_power():
    from scipy.stats import norm
    limit = (norm.isf(.01 / 6) + norm.ppf(.95)) * 3
    assert conditional_power(limit, 3) == pytest.approx(.95)


def test_ofdm_high_snr_and_read_only_reuse():
    result = ofdm_qpsk_control(np.full(32, 100.), frame_symbols=100, pilot_symbols=10, cp_samples=4)
    assert result["uncoded_ber"] == 0 and result["identical_decisions"]
    assert result["payload_bits"] == 90 * 32 * 2


def test_ofdm_noise_is_not_silently_absent():
    result = ofdm_qpsk_control(np.full(32, .3), frame_symbols=500, pilot_symbols=30, cp_samples=4)
    assert .1 < result["uncoded_ber"] < .5
