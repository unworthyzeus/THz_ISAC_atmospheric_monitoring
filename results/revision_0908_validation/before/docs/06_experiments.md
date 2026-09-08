# Experiments

> **Historical planning record:** This file describes the initial toy pipeline and an experiment plan that has since been completed and replaced. Current experiments and their measured versus synthetic evidence classes are recorded in `docs/34_multi_method_information_floor_study.md` and `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

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
