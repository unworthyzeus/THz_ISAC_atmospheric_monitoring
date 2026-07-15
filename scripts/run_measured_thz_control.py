from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.measured_thz_control import (  # noqa: E402
    DEFAULT_HIGH_BAND_MIN_THZ,
    evaluate_high_band_control,
    frequency_monotonicity_table,
    read_concentration_spectrum_csv,
)


DATASETS = (
    ("lysozyme", "Fig3.csv"),
    ("ovalbumin", "Fig4.csv"),
)


def main() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw" / "measured_thz_control"
    result_dir = PROJECT_ROOT / "results" / "tables"
    acquisition_manifest_path = (
        result_dir / "measured_thz_control_acquisition_manifest.json"
    )
    if not acquisition_manifest_path.exists():
        raise FileNotFoundError(
            "Run scripts/download_measured_thz_control.py before this analysis."
        )
    acquisition_manifest = json.loads(
        acquisition_manifest_path.read_text(encoding="utf-8")
    )
    if acquisition_manifest.get("status") != "success":
        raise RuntimeError("Measured THz acquisition manifest is not successful.")

    summaries = []
    frequency_tables = []
    prediction_rows = []
    for analyte, filename in DATASETS:
        data = read_concentration_spectrum_csv(raw_dir / filename, analyte=analyte)
        result = evaluate_high_band_control(data)
        summaries.append(
            {
                "analyte": result.analyte,
                "concentration_count": result.concentration_count,
                "band_min_thz": result.band_min_thz,
                "band_max_thz": result.band_max_thz,
                "band_frequency_count": result.band_frequency_count,
                "spearman_rho": result.spearman_rho,
                "spearman_pvalue": result.spearman_pvalue,
                "loocv_rmse_mg_ml": result.loocv_rmse_mg_ml,
                "loocv_q05_q95_nrmse": result.loocv_q05_q95_nrmse,
                "concentration_q05_q95_span_mg_ml": (
                    result.concentration_q05_q95_span_mg_ml
                ),
            }
        )
        frequency_tables.append(frequency_monotonicity_table(data))
        for concentration, signal, prediction in zip(
            data.concentration_mg_ml,
            result.band_signal,
            result.loocv_prediction_mg_ml,
            strict=True,
        ):
            prediction_rows.append(
                {
                    "analyte": analyte,
                    "concentration_mg_ml": float(concentration),
                    "high_band_mean_absorption": float(signal),
                    "loocv_prediction_mg_ml": float(prediction),
                    "residual_mg_ml": float(prediction - concentration),
                }
            )

    summary = pd.DataFrame(summaries)
    frequency_table = pd.concat(frequency_tables, ignore_index=True)
    predictions = pd.DataFrame(prediction_rows)
    summary_path = result_dir / "measured_thz_control_summary.csv"
    frequency_path = result_dir / "measured_thz_control_frequency_monotonicity.csv"
    prediction_path = result_dir / "measured_thz_control_predictions.csv"
    summary.to_csv(summary_path, index=False)
    frequency_table.to_csv(frequency_path, index=False)
    predictions.to_csv(prediction_path, index=False)

    manifest = {
        "status": "success",
        "dataset_doi": "10.17632/dpw4svmdr8.1",
        "dataset_licence": "CC BY 4.0",
        "source_type": "real measured THz-TDS summary spectra",
        "scientific_scope": (
            "Aqueous protein concentration positive control, not atmospheric "
            "pollution and not a gas inversion result."
        ),
        "analysis_contract": {
            "fixed_high_band_min_thz": DEFAULT_HIGH_BAND_MIN_THZ,
            "fixed_high_band_max_thz": 1.3,
            "frequency_selection_uses_labels": False,
            "regressor": "one feature ordinary least squares",
            "evaluation": "leave one measured concentration level out",
            "normalization": "full sample concentration Q05 to Q95 span",
            "pseudo_replicates_created_from_sd": False,
        },
        "macro_loocv_q05_q95_nrmse": float(
            summary["loocv_q05_q95_nrmse"].mean()
        ),
        "mean_absolute_high_band_spearman_rho": float(
            np.abs(summary["spearman_rho"]).mean()
        ),
        "results": summaries,
        "limitations": [
            "Only six or seven concentration levels are available per protein.",
            "Files report means and standard deviations, not raw replicates.",
            "The descriptive per frequency table is not a validated selector.",
            "The task and normalization differ from the Beijing pollutant benchmark.",
        ],
        "outputs": [
            str(summary_path.relative_to(PROJECT_ROOT)),
            str(frequency_path.relative_to(PROJECT_ROOT)),
            str(prediction_path.relative_to(PROJECT_ROOT)),
        ],
    }
    manifest_path = result_dir / "measured_thz_control_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(summary.to_string(index=False))
    print(f"Macro LOOCV Q05 to Q95 NRMSE: {manifest['macro_loocv_q05_q95_nrmse']:.6f}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
