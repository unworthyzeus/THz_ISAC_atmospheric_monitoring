from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.experiments import run_baseline_experiment
from thz_isac.synthetic_data import SyntheticDatasetConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the initial THz ISAC synthetic baseline.")
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--subcarriers", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SyntheticDatasetConfig(
        n_samples=args.samples,
        n_subcarriers=args.subcarriers,
        random_seed=args.seed,
    )
    outputs = run_baseline_experiment(PROJECT_ROOT, config)
    print("Baseline complete.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()

