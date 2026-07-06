from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.estimators import collect_metrics, train_linear_baselines
from thz_isac.synthetic_data import SyntheticDatasetConfig, generate_dataset


def main() -> None:
    snr_values = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
    rows = []
    for snr_db in snr_values:
        config = SyntheticDatasetConfig(
            n_samples=2000,
            n_subcarriers=256,
            snr_db_range=(float(snr_db), float(snr_db)),
            random_seed=7,
        )
        dataset = generate_dataset(config)
        result = train_linear_baselines(dataset.X, dataset.y, random_state=config.random_seed)
        metrics = collect_metrics(result)
        metrics["snr_db"] = snr_db
        rows.append(metrics)

    sweep = pd.concat(rows, ignore_index=True)
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = tables_dir / "snr_sweep_metrics.csv"
    sweep.to_csv(metrics_path, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=160)
    for target in ["gas_ppm", "pm_ug_m3"]:
        best = sweep[(sweep["target"] == target) & (sweep["model"] == "ridge_alpha_10")]
        axes[0].plot(best["snr_db"], best["r2"], marker="o", label=target)
        axes[1].plot(best["snr_db"], best["rmse"], marker="o", label=target)

    axes[0].set_title("R2 frente a SNR")
    axes[0].set_xlabel("SNR dB")
    axes[0].set_ylabel("R2")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].set_title("RMSE frente a SNR")
    axes[1].set_xlabel("SNR dB")
    axes[1].set_ylabel("RMSE")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()

    fig.tight_layout()
    figure_path = figures_dir / "snr_sweep.png"
    fig.savefig(figure_path)
    plt.close(fig)

    print("SNR sweep complete.")
    print(f"metrics: {metrics_path}")
    print(f"figure: {figure_path}")


if __name__ == "__main__":
    main()
