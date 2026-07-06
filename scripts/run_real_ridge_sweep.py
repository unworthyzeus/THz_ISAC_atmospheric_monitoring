from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.external_forward_model import ExternalCSIDatasetConfig, generate_external_csi_dataset, template_projection_features
from thz_isac.hitran_templates import load_hitran_lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a focused Ridge alpha sweep for external data spectra.")
    parser.add_argument("--samples", type=int, default=20_000)
    parser.add_argument("--subcarriers", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hitran_path = PROJECT_ROOT / "data" / "processed" / "hitran" / "hitran_60_400GHz_lines.csv"
    air_path = PROJECT_ROOT / "data" / "processed" / "air_quality" / "beijing_air_quality_model_sample.csv.gz"
    hitran_lines = load_hitran_lines(hitran_path)
    pollution = pd.read_csv(air_path)
    config = ExternalCSIDatasetConfig(
        n_samples=args.samples,
        n_subcarriers=args.subcarriers,
        random_seed=args.seed,
    )
    dataset = generate_external_csi_dataset(pollution, hitran_lines, config)
    train_idx, test_idx = train_test_split(np.arange(len(dataset.y)), test_size=0.25, random_state=args.seed)

    feature_sets = {
        "path_normalized": dataset.path_normalized_db,
        "template_projection": template_projection_features(dataset),
        "hybrid_path_template": np.column_stack([dataset.path_normalized_db, template_projection_features(dataset)]),
    }
    alphas = np.logspace(-3, 3, 25)
    target_ranges = {
        name: max(float(np.percentile(dataset.y[:, idx], 95) - np.percentile(dataset.y[:, idx], 5)), 1.0)
        for idx, name in enumerate(dataset.target_names)
    }

    rows = []
    for feature_name, X in feature_sets.items():
        X_train = X[train_idx]
        X_test = X[test_idx]
        y_train = dataset.y[train_idx]
        y_test = dataset.y[test_idx]
        for alpha in alphas:
            model = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=float(alpha)))])
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            per_target = []
            for target_idx, target_name in enumerate(dataset.target_names):
                rmse = mean_squared_error(y_test[:, target_idx], pred[:, target_idx]) ** 0.5
                per_target.append(rmse / target_ranges[target_name])
            rows.append(
                {
                    "feature_set": feature_name,
                    "alpha": float(alpha),
                    "mean_nrmse_range": float(np.mean(per_target)),
                    "max_nrmse_range": float(np.max(per_target)),
                    "mean_r2": float(np.mean([r2_score(y_test[:, i], pred[:, i]) for i in range(y_test.shape[1])])),
                }
            )

    results = pd.DataFrame(rows).sort_values(["mean_nrmse_range", "max_nrmse_range"])
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    results_path = tables_dir / "real_data_ridge_alpha_sweep.csv"
    figure_path = figures_dir / "real_data_ridge_alpha_sweep.png"
    results.to_csv(results_path, index=False)
    plot_alpha_sweep(results, figure_path)

    print("Ridge alpha sweep complete.")
    print(f"results: {results_path}")
    print(f"figure: {figure_path}")
    print("Best row:")
    print(results.iloc[0].to_string())


def plot_alpha_sweep(results: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    for feature_name, group in results.sort_values("alpha").groupby("feature_set"):
        ax.semilogx(group["alpha"], group["mean_nrmse_range"], marker="o", label=feature_name)
    ax.set_xlabel("Ridge alpha")
    ax.set_ylabel("Mean normalized RMSE")
    ax.set_title("External data Ridge alpha sweep")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    main()

