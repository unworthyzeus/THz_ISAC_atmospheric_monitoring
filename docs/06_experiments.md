# Experiments

## Toy Experiment 0

Purpose: verify that the software pipeline runs.

This experiment uses invented spectral lines and uniformly sampled pollutant labels. It is not scientific evidence.

Outputs:

1. `results/tables/baseline_metrics.csv`
2. `results/figures/baseline_scatter.png`

## Toy SNR Sweep

Purpose: verify that the estimator degrades when SNR decreases.

Outputs:

1. `results/tables/snr_sweep_metrics.csv`
2. `results/figures/snr_sweep.png`

## Toy Model Benchmark

Purpose: compare estimator plumbing and feature representations.

Outputs:

1. `results/tables/model_benchmark_metrics.csv`
2. `results/tables/model_benchmark_summary.csv`
3. `results/figures/model_benchmark_ranking.png`

## Real Data Experiment

Pending.

Required ingredients:

1. HITRAN line data.
2. Real pollutant concentration records.
3. Published PM attenuation model.
4. Held out test split.

