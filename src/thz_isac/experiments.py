"""Experiment runners for the initial project baseline."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .estimators import TARGET_NAMES, collect_metrics, train_linear_baselines
from .synthetic_data import SyntheticDatasetConfig, generate_dataset


def run_baseline_experiment(project_root: Path, config: SyntheticDatasetConfig) -> dict[str, Path]:
    """Run the synthetic regression baseline and save outputs."""
    dataset = generate_dataset(config)
    train_result = train_linear_baselines(dataset.X, dataset.y, random_state=config.random_seed)
    metrics = collect_metrics(train_result)

    tables_dir = project_root / "results" / "tables"
    figures_dir = project_root / "results" / "figures"
    synthetic_dir = project_root / "data" / "synthetic"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = tables_dir / "baseline_metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    metadata_path = synthetic_dir / "baseline_metadata.csv"
    dataset.metadata.to_csv(metadata_path, index=False)

    frequency_path = synthetic_dir / "baseline_frequency_ghz.csv"
    pd.DataFrame({"frequency_ghz": dataset.frequency_ghz}).to_csv(frequency_path, index=False)

    predictions = []
    for model_name, model in train_result.models.items():
        y_pred = model.predict(train_result.X_test)
        for row_idx in range(len(y_pred)):
            predictions.append(
                {
                    "model": model_name,
                    "sample": row_idx,
                    "true_gas_ppm": train_result.y_test[row_idx, 0],
                    "pred_gas_ppm": y_pred[row_idx, 0],
                    "true_pm_ug_m3": train_result.y_test[row_idx, 1],
                    "pred_pm_ug_m3": y_pred[row_idx, 1],
                }
            )
    predictions_path = tables_dir / "baseline_predictions.csv"
    pd.DataFrame(predictions).to_csv(predictions_path, index=False)

    scatter_path = figures_dir / "baseline_scatter.png"
    _plot_scatter(train_result, scatter_path)

    config_path = tables_dir / "baseline_config.json"
    config_path.write_text(json.dumps(config.__dict__, indent=2), encoding="utf-8")

    return {
        "metrics": metrics_path,
        "predictions": predictions_path,
        "scatter": scatter_path,
        "metadata": metadata_path,
        "frequency": frequency_path,
        "config": config_path,
    }


def _plot_scatter(train_result, output_path: Path) -> None:
    model = train_result.models["ridge_alpha_1"]
    pred = model.predict(train_result.X_test)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=160)
    for idx, target_name in enumerate(TARGET_NAMES):
        ax = axes[idx]
        true = train_result.y_test[:, idx]
        estimated = pred[:, idx]
        ax.scatter(true, estimated, s=12, alpha=0.55)
        lo = min(true.min(), estimated.min())
        hi = max(true.max(), estimated.max())
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=1)
        ax.set_title(target_name)
        ax.set_xlabel("true")
        ax.set_ylabel("estimated")
        ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)

