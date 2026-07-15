"""Validate project Voigt cross sections against the HAPI reference implementation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hapi import absorptionCoefficient_Voigt, db_begin  # noqa: E402
from thz_isac.physical_spectroscopy import (  # noqa: E402
    GHZ_PER_WAVENUMBER,
    REFERENCE_PRESSURE_PA,
    molecular_cross_section_cm2_per_molecule,
)


TEMPERATURE_K = 287.55
PRESSURE_PA = 101_040.0
FREQUENCY_MIN_GHZ = 60.0
FREQUENCY_MAX_GHZ = 400.0
GRID_POINTS = 256
ACTIVE_PEAK_FRACTION = 1.0e-4
PEAK_RELATIVE_ERROR_THRESHOLD = 1.0e-5
NORMALIZED_RMSE_THRESHOLD = 1.0e-5
HAPI_WAVENUMBER_WING_CM_1 = 100.0

MOLECULE_IDS = {
    "CO": 5,
    "O3": 3,
    "SO2": 9,
    "NO2": 10,
    "H2O": 1,
    "O2": 7,
}


def main() -> None:
    processed_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "hitran"
        / "hitran_60_400GHz_lines.csv"
    )
    raw_dir = PROJECT_ROOT / "data" / "raw" / "hitran"
    output_path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "physical_spectroscopy_hapi_validation.csv"
    )
    _require_input_data(processed_path, raw_dir)

    lines = pd.read_csv(processed_path)
    missing_molecules = sorted(set(MOLECULE_IDS).difference(lines["molecule"].unique()))
    if missing_molecules:
        raise RuntimeError(
            "Processed HITRAN data is missing required molecules: "
            + ", ".join(missing_molecules)
        )

    frequency_ghz = np.linspace(FREQUENCY_MIN_GHZ, FREQUENCY_MAX_GHZ, GRID_POINTS)
    wavenumber_cm_1 = frequency_ghz / GHZ_PER_WAVENUMBER
    pressure_atm = PRESSURE_PA / REFERENCE_PRESSURE_PA

    rows = []
    previous_directory = Path.cwd()
    try:
        os.chdir(raw_dir)
        db_begin(str(raw_dir))
        for molecule, molecule_id in MOLECULE_IDS.items():
            project_cross_section = molecular_cross_section_cm2_per_molecule(
                lines,
                frequency_ghz,
                molecule,
                temperature_k=TEMPERATURE_K,
                pressure_pa=PRESSURE_PA,
            )
            hapi_wavenumber, hapi_cross_section = absorptionCoefficient_Voigt(
                Components=((molecule_id, 1),),
                SourceTables=f"{molecule}_main_60_400GHz",
                Environment={"p": pressure_atm, "T": TEMPERATURE_K},
                WavenumberGrid=wavenumber_cm_1,
                WavenumberWing=HAPI_WAVENUMBER_WING_CM_1,
                IntensityThreshold=0.0,
                HITRAN_units=True,
                Diluent={"air": 1.0},
            )
            rows.append(
                _comparison_row(
                    molecule=molecule,
                    line_count=int((lines["molecule"] == molecule).sum()),
                    frequency_ghz=frequency_ghz,
                    requested_wavenumber_cm_1=wavenumber_cm_1,
                    project_cross_section=project_cross_section,
                    hapi_wavenumber_cm_1=np.asarray(hapi_wavenumber, dtype=float),
                    hapi_cross_section=np.asarray(hapi_cross_section, dtype=float),
                )
            )
    finally:
        os.chdir(previous_directory)

    validation = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(output_path, index=False)

    display_columns = [
        "molecule",
        "project_peak_cross_section_cm2_per_molecule",
        "hapi_peak_cross_section_cm2_per_molecule",
        "peak_relative_error",
        "normalized_rmse_active",
        "active_grid_points",
        "passed",
    ]
    print("Physical spectroscopy validation complete.")
    print(f"Output: {output_path}")
    print(validation[display_columns].to_string(index=False))

    failed = validation.loc[~validation["passed"], "molecule"].tolist()
    if failed:
        raise SystemExit(
            "Physical spectroscopy validation failed for: " + ", ".join(failed)
        )


def _require_input_data(processed_path: Path, raw_dir: Path) -> None:
    missing = []
    if not processed_path.is_file():
        missing.append(str(processed_path))
    for molecule in MOLECULE_IDS:
        table_name = f"{molecule}_main_60_400GHz"
        for suffix in (".data", ".header"):
            path = raw_dir / f"{table_name}{suffix}"
            if not path.is_file():
                missing.append(str(path))
    if missing:
        formatted = "\n".join(f"  {path}" for path in missing)
        raise FileNotFoundError(
            "Required HITRAN inputs are missing. Run "
            "'python scripts/download_external_data.py' first.\n"
            f"Missing paths:\n{formatted}"
        )


def _comparison_row(
    *,
    molecule: str,
    line_count: int,
    frequency_ghz: np.ndarray,
    requested_wavenumber_cm_1: np.ndarray,
    project_cross_section: np.ndarray,
    hapi_wavenumber_cm_1: np.ndarray,
    hapi_cross_section: np.ndarray,
) -> dict[str, float | int | bool | str]:
    if hapi_wavenumber_cm_1.shape != requested_wavenumber_cm_1.shape or not np.allclose(
        hapi_wavenumber_cm_1,
        requested_wavenumber_cm_1,
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise RuntimeError(f"HAPI returned an unexpected wavenumber grid for {molecule}.")
    if project_cross_section.shape != frequency_ghz.shape:
        raise RuntimeError(f"Project cross section has an unexpected shape for {molecule}.")
    if not np.isfinite(project_cross_section).all() or not np.isfinite(hapi_cross_section).all():
        raise RuntimeError(f"Nonfinite cross sections encountered for {molecule}.")

    project_peak_index = int(np.argmax(project_cross_section))
    hapi_peak_index = int(np.argmax(hapi_cross_section))
    project_peak = float(project_cross_section[project_peak_index])
    hapi_peak = float(hapi_cross_section[hapi_peak_index])
    if hapi_peak <= 0.0:
        raise RuntimeError(f"HAPI returned a nonpositive peak cross section for {molecule}.")

    active = hapi_cross_section > ACTIVE_PEAK_FRACTION * hapi_peak
    if not np.any(active):
        raise RuntimeError(f"No active HAPI grid points found for {molecule}.")
    peak_relative_error = abs(project_peak - hapi_peak) / hapi_peak
    normalized_rmse = float(
        np.sqrt(np.mean((project_cross_section[active] - hapi_cross_section[active]) ** 2))
        / hapi_peak
    )
    peak_passed = peak_relative_error <= PEAK_RELATIVE_ERROR_THRESHOLD
    rmse_passed = normalized_rmse <= NORMALIZED_RMSE_THRESHOLD

    return {
        "molecule": molecule,
        "hitran_line_count": line_count,
        "temperature_k": TEMPERATURE_K,
        "pressure_pa": PRESSURE_PA,
        "grid_points": GRID_POINTS,
        "frequency_min_ghz": FREQUENCY_MIN_GHZ,
        "frequency_max_ghz": FREQUENCY_MAX_GHZ,
        "project_peak_cross_section_cm2_per_molecule": project_peak,
        "hapi_peak_cross_section_cm2_per_molecule": hapi_peak,
        "project_peak_frequency_ghz": float(frequency_ghz[project_peak_index]),
        "hapi_peak_frequency_ghz": float(frequency_ghz[hapi_peak_index]),
        "peak_relative_error": float(peak_relative_error),
        "active_peak_fraction": ACTIVE_PEAK_FRACTION,
        "active_grid_points": int(np.sum(active)),
        "normalized_rmse_active": normalized_rmse,
        "peak_relative_error_threshold": PEAK_RELATIVE_ERROR_THRESHOLD,
        "normalized_rmse_threshold": NORMALIZED_RMSE_THRESHOLD,
        "peak_passed": bool(peak_passed),
        "rmse_passed": bool(rmse_passed),
        "passed": bool(peak_passed and rmse_passed),
    }


if __name__ == "__main__":
    main()
