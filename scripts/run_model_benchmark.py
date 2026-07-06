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

from thz_isac.estimators import TARGET_NAMES, evaluate_predictions, make_model_zoo
from thz_isac.features import FEATURE_MODES, build_features
from thz_isac.physics_estimator import TemplateLeastSquaresEstimator
from thz_isac.synthetic_data import SyntheticDatasetConfig, generate_dataset


FAST_MODELS = [
    "linear",
    "ridge_0_1",
    "ridge_1",
    "ridge_10",
    "ridge_100",
    "pls_8",
    "pls_16",
    "knn_7",
    "random_forest",
    "extra_trees",
]

SLOW_MODELS = [
    "lasso_0_0001",
    "elasticnet_0_0001",
    "svr_rbf",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark THz ISAC estimators.")
    parser.add_argument("--samples", type=int, default=3500)
    parser.add_argument("--subcarriers", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--include-slow", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SyntheticDatasetConfig(
        n_samples=args.samples,
        n_subcarriers=args.subcarriers,
        random_seed=args.seed,
    )
    dataset = generate_dataset(config)
    indices = np.arange(config.n_samples)
    _, test_idx = train_test_split(indices, test_size=0.25, random_state=config.random_seed)

    model_names = FAST_MODELS + (SLOW_MODELS if args.include_slow else [])
    rows = []
    predictions = {}

    for feature_mode in FEATURE_MODES:
        X = build_features(dataset, feature_mode)
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            dataset.y,
            test_size=0.25,
            random_state=config.random_seed,
        )
        models = make_model_zoo(random_state=config.random_seed)
        for model_name in model_names:
            model = models[model_name]
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            metrics = evaluate_predictions(y_test, y_pred, model_name)
            metrics["feature_mode"] = feature_mode
            rows.append(metrics)
            predictions[(feature_mode, model_name)] = (y_test, y_pred)

    template = TemplateLeastSquaresEstimator(dataset.frequency_ghz)
    elevation_test = dataset.metadata.loc[test_idx, "elevation_deg"].to_numpy()
    y_template = template.predict_from_attenuation(dataset.attenuation_db[test_idx], elevation_test)
    template_metrics = evaluate_predictions(dataset.y[test_idx], y_template, "template_least_squares")
    template_metrics["feature_mode"] = "known_templates"
    rows.append(template_metrics)
    predictions[("known_templates", "template_least_squares")] = (dataset.y[test_idx], y_template)

    metrics = pd.concat(rows, ignore_index=True)
    summary = summarize_metrics(metrics)

    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = tables_dir / "model_benchmark_metrics.csv"
    summary_path = tables_dir / "model_benchmark_summary.csv"
    predictions_path = tables_dir / "best_model_predictions.csv"
    config_path = tables_dir / "model_benchmark_config.json"
    ranking_path = figures_dir / "model_benchmark_ranking.png"
    scatter_path = figures_dir / "best_model_scatter.png"

    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)

    best = summary.iloc[0]
    best_key = (best["feature_mode"], best["model"])
    best_true, best_pred = predictions[best_key]
    save_best_predictions(predictions_path, best_true, best_pred, best_key)
    plot_ranking(summary, ranking_path)
    plot_scatter(best_true, best_pred, best_key, scatter_path)

    config_path.write_text(
        json.dumps(
            {
                "config": config.__dict__,
                "feature_modes": FEATURE_MODES,
                "models": model_names,
                "ranking_metric": "mean_nrmse_range",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Model benchmark complete.")
    print(f"metrics: {metrics_path}")
    print(f"summary: {summary_path}")
    print(f"best predictions: {predictions_path}")
    print(f"ranking figure: {ranking_path}")
    print(f"scatter figure: {scatter_path}")
    print("Best row:")
    print(best.to_string())


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    target_ranges = {"gas_ppm": 120.0, "pm_ug_m3": 180.0}
    enriched = metrics.copy()
    enriched["nrmse_range"] = enriched.apply(
        lambda row: row["rmse"] / target_ranges[row["target"]],
        axis=1,
    )
    summary = (
        enriched.groupby(["feature_mode", "model"], as_index=False)
        .agg(
            mean_nrmse_range=("nrmse_range", "mean"),
            mean_r2=("r2", "mean"),
            mean_mae=("mae", "mean"),
            gas_rmse=("rmse", lambda s: float(s.iloc[0])),
            pm_rmse=("rmse", lambda s: float(s.iloc[1]) if len(s) > 1 else float("nan")),
        )
        .sort_values(["mean_nrmse_range", "mean_r2"], ascending=[True, False])
    )
    return summary


def save_best_predictions(
    output_path: Path,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    best_key: tuple[str, str],
) -> None:
    rows = []
    for idx in range(len(y_true)):
        rows.append(
            {
                "feature_mode": best_key[0],
                "model": best_key[1],
                "sample": idx,
                "true_gas_ppm": y_true[idx, 0],
                "pred_gas_ppm": y_pred[idx, 0],
                "true_pm_ug_m3": y_true[idx, 1],
                "pred_pm_ug_m3": y_pred[idx, 1],
            }
        )
    pd.DataFrame(rows).to_csv(output_path, index=False)


def plot_ranking(summary: pd.DataFrame, output_path: Path) -> None:
    top = summary.head(15).copy()
    labels = [f"{row.feature_mode}\n{row.model}" for row in top.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 6), dpi=160)
    ax.barh(np.arange(len(top)), top["mean_nrmse_range"])
    ax.set_yticks(np.arange(len(top)), labels=labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean normalized RMSE")
    ax.set_title("Best estimator configurations")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_scatter(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    best_key: tuple[str, str],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=160)
    for idx, target_name in enumerate(TARGET_NAMES):
        ax = axes[idx]
        true = y_true[:, idx]
        estimated = y_pred[:, idx]
        ax.scatter(true, estimated, s=12, alpha=0.55)
        lo = min(true.min(), estimated.min())
        hi = max(true.max(), estimated.max())
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=1)
        ax.set_title(target_name)
        ax.set_xlabel("true")
        ax.set_ylabel("estimated")
        ax.grid(True, alpha=0.25)
    fig.suptitle(f"{best_key[0]} / {best_key[1]}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    main()

