from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.estimators import evaluate_predictions, make_model_zoo
from thz_isac.external_forward_model import (
    ExternalCSIDatasetConfig,
    generate_external_csi_dataset,
    predict_with_template_least_squares,
    template_projection_features,
)
from thz_isac.hitran_templates import load_hitran_lines


MODEL_NAMES = [
    "linear",
    "ridge_1",
    "ridge_10",
    "ridge_100",
    "pls_8",
    "pls_16",
    "knn_7",
    "random_forest",
    "extra_trees",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the external data driven benchmark.")
    parser.add_argument("--samples", type=int, default=20_000)
    parser.add_argument("--subcarriers", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hitran_path = PROJECT_ROOT / "data" / "processed" / "hitran" / "hitran_60_400GHz_lines.csv"
    air_path = PROJECT_ROOT / "data" / "processed" / "air_quality" / "beijing_air_quality_model_sample.csv.gz"
    if not hitran_path.exists() or not air_path.exists():
        raise RuntimeError("External data is missing. Run scripts/download_external_data.py first.")

    hitran_lines = load_hitran_lines(hitran_path)
    pollution = pd.read_csv(air_path)
    config = ExternalCSIDatasetConfig(
        n_samples=args.samples,
        n_subcarriers=args.subcarriers,
        random_seed=args.seed,
    )
    dataset = generate_external_csi_dataset(pollution, hitran_lines, config)
    indices = np.arange(len(dataset.y))
    train_idx, test_idx = train_test_split(indices, test_size=0.25, random_state=args.seed)

    feature_sets = {
        "path_normalized": dataset.path_normalized_db,
        "path_normalized_relative": dataset.path_normalized_db - dataset.path_normalized_db.mean(axis=1, keepdims=True),
        "template_projection": template_projection_features(dataset),
        "hybrid_path_template": np.column_stack(
            [
                dataset.path_normalized_db,
                template_projection_features(dataset),
            ]
        ),
        "path_normalized_context": np.column_stack(
            [
                dataset.path_normalized_db,
                dataset.metadata[["elevation_deg", "snr_db", "path_factor"]].to_numpy(),
            ]
        ),
    }

    rows = []
    skipped = []
    predictions = {}
    for feature_name, X in feature_sets.items():
        X_train = X[train_idx]
        X_test = X[test_idx]
        y_train = dataset.y[train_idx]
        y_test = dataset.y[test_idx]
        models = make_model_zoo(random_state=args.seed)
        for model_name in MODEL_NAMES:
            model = models[model_name]
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            except ValueError as exc:
                skipped.append({"feature_set": feature_name, "model": model_name, "reason": str(exc)})
                continue
            metrics = evaluate_predictions(y_test, y_pred, model_name, target_names=dataset.target_names)
            metrics["feature_set"] = feature_name
            rows.append(metrics)
            predictions[(feature_name, model_name)] = (y_test, y_pred)

    template_pred_all = predict_with_template_least_squares(dataset)
    template_metrics = evaluate_predictions(
        dataset.y[test_idx],
        template_pred_all[test_idx],
        "template_least_squares",
        target_names=dataset.target_names,
    )
    template_metrics["feature_set"] = "hitran_templates"
    rows.append(template_metrics)
    predictions[("hitran_templates", "template_least_squares")] = (dataset.y[test_idx], template_pred_all[test_idx])

    metrics = pd.concat(rows, ignore_index=True)
    summary = summarize(metrics, dataset.y, dataset.target_names)

    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    processed_dir = PROJECT_ROOT / "data" / "processed" / "real_data_csi"
    for path in [tables_dir, figures_dir, processed_dir]:
        path.mkdir(parents=True, exist_ok=True)

    metrics_path = tables_dir / "real_data_model_benchmark_metrics.csv"
    summary_path = tables_dir / "real_data_model_benchmark_summary.csv"
    skipped_path = tables_dir / "real_data_model_benchmark_skipped.csv"
    predictions_path = tables_dir / "real_data_best_predictions.csv"
    metadata_path = processed_dir / "real_data_csi_metadata.csv.gz"
    frequency_path = processed_dir / "real_data_frequency_ghz.csv"
    config_path = tables_dir / "real_data_model_benchmark_config.json"
    ranking_path = figures_dir / "real_data_model_ranking.png"
    scatter_path = figures_dir / "real_data_best_scatter.png"

    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(skipped).to_csv(skipped_path, index=False)
    dataset.metadata.to_csv(metadata_path, index=False, compression="gzip")
    pd.DataFrame({"frequency_ghz": dataset.frequency_ghz}).to_csv(frequency_path, index=False)

    best = summary.iloc[0]
    best_key = (best["feature_set"], best["model"])
    y_true, y_pred = predictions[best_key]
    save_predictions(predictions_path, y_true, y_pred, dataset.target_names, best_key)
    plot_ranking(summary, ranking_path)
    plot_best_scatter(y_true, y_pred, dataset.target_names, best_key, scatter_path)

    config_path.write_text(
        json.dumps(
            {
                "config": config.__dict__,
                "models": MODEL_NAMES,
                "feature_sets": list(feature_sets.keys()) + ["hitran_templates"],
                "data_sources": {
                    "hitran_lines": str(hitran_path),
                    "pollution_records": str(air_path),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Real data benchmark complete.")
    print(f"metrics: {metrics_path}")
    print(f"summary: {summary_path}")
    print(f"skipped: {skipped_path}")
    print(f"best predictions: {predictions_path}")
    print(f"ranking figure: {ranking_path}")
    print(f"scatter figure: {scatter_path}")
    print("Best row:")
    print(best.to_string())


def summarize(metrics: pd.DataFrame, y: np.ndarray, target_names: list[str]) -> pd.DataFrame:
    ranges = {
        name: max(float(np.percentile(y[:, idx], 95) - np.percentile(y[:, idx], 5)), 1.0)
        for idx, name in enumerate(target_names)
    }
    enriched = metrics.copy()
    enriched["nrmse_range"] = enriched.apply(lambda row: row["rmse"] / ranges[row["target"]], axis=1)
    summary = (
        enriched.groupby(["feature_set", "model"], as_index=False)
        .agg(
            mean_nrmse_range=("nrmse_range", "mean"),
            mean_r2=("r2", "mean"),
            mean_mae=("mae", "mean"),
            max_target_nrmse=("nrmse_range", "max"),
        )
        .sort_values(["mean_nrmse_range", "max_target_nrmse"], ascending=[True, True])
    )
    return summary


def save_predictions(
    output_path: Path,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_names: list[str],
    best_key: tuple[str, str],
) -> None:
    rows = []
    for idx in range(len(y_true)):
        row = {"feature_set": best_key[0], "model": best_key[1], "sample": idx}
        for target_idx, target_name in enumerate(target_names):
            row[f"true_{target_name}"] = y_true[idx, target_idx]
            row[f"pred_{target_name}"] = y_pred[idx, target_idx]
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_path, index=False)


def plot_ranking(summary: pd.DataFrame, output_path: Path) -> None:
    top = summary.head(12).copy()
    labels = [f"{row.feature_set}\n{row.model}" for row in top.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=160)
    ax.barh(np.arange(len(top)), top["mean_nrmse_range"])
    ax.set_yticks(np.arange(len(top)), labels=labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean normalized RMSE")
    ax.set_title("External data driven benchmark")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_best_scatter(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_names: list[str],
    best_key: tuple[str, str],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), dpi=160)
    for target_idx, target_name in enumerate(target_names):
        ax = axes.flat[target_idx]
        true = y_true[:, target_idx]
        pred = y_pred[:, target_idx]
        ax.scatter(true, pred, s=6, alpha=0.35)
        lo = min(true.min(), pred.min())
        hi = max(true.max(), pred.max())
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=1)
        ax.set_title(target_name)
        ax.set_xlabel("True")
        ax.set_ylabel("Estimated")
        ax.grid(True, alpha=0.25)
    fig.suptitle(f"{best_key[0]} / {best_key[1]}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    main()
