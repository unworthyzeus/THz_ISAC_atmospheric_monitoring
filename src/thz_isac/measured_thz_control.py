"""Measured THz concentration calibration on the Hattori protein dataset.

The public dataset contains concentration dependent THz time domain
spectroscopy summaries for aqueous lysozyme and ovalbumin solutions.  Each
row is a concentration level and each spectral entry is a reported mean with
an adjacent standard deviation.  The raw replicate measurements are not
available, so this module treats concentration levels, not pseudo replicates,
as the independent observations.

This is a bounded positive control for measured THz spectroscopy.  It is not
an atmospheric pollutant experiment and it is not evidence that the project's
gas retrieval target is achievable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


DEFAULT_HIGH_BAND_MIN_THZ = 0.9
_FREQUENCY_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*THz", re.IGNORECASE)


@dataclass(frozen=True)
class MeasuredTHzConcentrationData:
    """One measured concentration series and its reported spectra."""

    analyte: str
    concentration_mg_ml: np.ndarray
    frequency_thz: np.ndarray
    absorption_coefficient: np.ndarray
    absorption_sd: np.ndarray


@dataclass(frozen=True)
class MeasuredTHzControlResult:
    """Descriptive monotonicity and leave one level out calibration metrics."""

    analyte: str
    concentration_count: int
    band_min_thz: float
    band_max_thz: float
    band_frequency_count: int
    spearman_rho: float
    spearman_pvalue: float
    loocv_rmse_mg_ml: float
    loocv_q05_q95_nrmse: float
    concentration_q05_q95_span_mg_ml: float
    band_signal: np.ndarray
    loocv_prediction_mg_ml: np.ndarray


def read_concentration_spectrum_csv(
    path: str | Path,
    *,
    analyte: str,
) -> MeasuredTHzConcentrationData:
    """Read a Fig3 or Fig4 CSV without inventing replicate observations."""

    frame = pd.read_csv(path, skiprows=1).dropna(axis=0, how="all")
    if frame.shape[1] < 3 or frame.shape[1] % 2 == 0:
        raise ValueError("Expected one concentration column and mean/SD spectral pairs.")

    mean_columns = list(frame.columns[1::2])
    sd_columns = list(frame.columns[2::2])
    frequencies = np.asarray([_parse_frequency(name) for name in mean_columns])
    if len(sd_columns) != len(mean_columns):
        raise ValueError("Every spectral mean must have an adjacent SD column.")

    concentration = _numeric_array(frame.iloc[:, 0], "concentration")
    absorption = _numeric_matrix(frame.loc[:, mean_columns], "spectral means")
    absorption_sd = _numeric_matrix(frame.loc[:, sd_columns], "spectral SD values")
    if np.any(absorption_sd < 0.0):
        raise ValueError("Spectral SD values must be nonnegative.")
    if len(concentration) < 4:
        raise ValueError("At least four concentration levels are required.")
    if len(np.unique(concentration)) != len(concentration):
        raise ValueError("Concentration levels must be unique.")
    if np.any(np.diff(frequencies) <= 0.0):
        raise ValueError("Spectral frequencies must be strictly increasing.")

    return MeasuredTHzConcentrationData(
        analyte=analyte,
        concentration_mg_ml=concentration,
        frequency_thz=frequencies,
        absorption_coefficient=absorption,
        absorption_sd=absorption_sd,
    )


def evaluate_high_band_control(
    data: MeasuredTHzConcentrationData,
    *,
    band_min_thz: float = DEFAULT_HIGH_BAND_MIN_THZ,
) -> MeasuredTHzControlResult:
    """Evaluate a fixed high band mean without frequency selection on labels.

    The default uses every reported channel from 0.9 THz upward.  The scalar
    band mean is deliberately fixed before examining target error.  Spearman
    correlation measures monotonic calibration.  A one feature ordinary
    least squares model is evaluated by leaving out each concentration level
    in turn.  The normalization span uses the full, explicitly reported set
    of concentration levels because this tiny positive control has no train,
    validation, and test partition.
    """

    band_min = float(band_min_thz)
    if not np.isfinite(band_min):
        raise ValueError("band_min_thz must be finite.")
    selected = data.frequency_thz >= band_min
    if not np.any(selected):
        raise ValueError("band_min_thz selects no measured frequencies.")

    signal = np.mean(data.absorption_coefficient[:, selected], axis=1)
    correlation = spearmanr(data.concentration_mg_ml, signal)
    rho = float(correlation.statistic)
    pvalue = float(correlation.pvalue)
    if not np.isfinite(rho) or not np.isfinite(pvalue):
        raise ValueError("The high band signal does not define a finite correlation.")

    prediction = _leave_one_level_out_linear_prediction(
        signal,
        data.concentration_mg_ml,
    )
    residual = prediction - data.concentration_mg_ml
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    q05, q95 = np.quantile(data.concentration_mg_ml, [0.05, 0.95])
    span = float(q95 - q05)
    if not span > 0.0:
        raise ValueError("Concentration Q05 to Q95 span must be positive.")

    return MeasuredTHzControlResult(
        analyte=data.analyte,
        concentration_count=len(data.concentration_mg_ml),
        band_min_thz=band_min,
        band_max_thz=float(np.max(data.frequency_thz[selected])),
        band_frequency_count=int(np.sum(selected)),
        spearman_rho=rho,
        spearman_pvalue=pvalue,
        loocv_rmse_mg_ml=rmse,
        loocv_q05_q95_nrmse=rmse / span,
        concentration_q05_q95_span_mg_ml=span,
        band_signal=signal,
        loocv_prediction_mg_ml=prediction,
    )


def frequency_monotonicity_table(
    data: MeasuredTHzConcentrationData,
) -> pd.DataFrame:
    """Return descriptive per frequency rank correlations."""

    rows = []
    for column_index, frequency in enumerate(data.frequency_thz):
        correlation = spearmanr(
            data.concentration_mg_ml,
            data.absorption_coefficient[:, column_index],
        )
        rows.append(
            {
                "analyte": data.analyte,
                "frequency_thz": float(frequency),
                "concentration_count": len(data.concentration_mg_ml),
                "spearman_rho": float(correlation.statistic),
                "spearman_pvalue": float(correlation.pvalue),
                "selection_role": "descriptive_only",
            }
        )
    return pd.DataFrame(rows)


def _leave_one_level_out_linear_prediction(
    signal: np.ndarray,
    concentration: np.ndarray,
) -> np.ndarray:
    predictions = np.empty(len(concentration), dtype=float)
    for held_out in range(len(concentration)):
        train = np.arange(len(concentration)) != held_out
        design = np.column_stack([np.ones(np.sum(train)), signal[train]])
        coefficients, *_ = np.linalg.lstsq(design, concentration[train], rcond=None)
        predictions[held_out] = coefficients[0] + coefficients[1] * signal[held_out]
    return predictions


def _parse_frequency(column_name: object) -> float:
    match = _FREQUENCY_PATTERN.search(str(column_name))
    if match is None:
        raise ValueError(f"Could not parse THz frequency from column {column_name!r}.")
    return float(match.group(1))


def _numeric_array(values: pd.Series, label: str) -> np.ndarray:
    array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(array).all():
        raise ValueError(f"{label} contains missing or nonnumeric values.")
    return array


def _numeric_matrix(values: pd.DataFrame, label: str) -> np.ndarray:
    matrix = values.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError(f"{label} contains missing or nonnumeric values.")
    return matrix
