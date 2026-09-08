# Real Data Benchmark Iteration

## What Happened

The first real data benchmark completed with external data driven spectra.

Best result before hybrid features:

| Feature set | Model | Mean normalized RMSE | Mean R2 |
| --- | --- | ---: | ---: |
| `path_normalized` | `ridge_10` | 0.0797 | 0.943 |

Per target, Ridge performed well across gases and PM. The direct template least squares estimator worked for gas features but performed poorly for PM because PM2.5 and PM10 are represented by similar smooth spectral trends.

## Why A Hybrid Feature Was Added

The new `template_projection` feature projects each spectrum onto HITRAN gas templates, PM templates, and nuisance background terms.

This is not target leakage. The projection uses only:

1. HITRAN line templates.
2. Rayleigh type PM templates.
3. The observed spectrum.

The labels are used only by the supervised estimator after the projection.

## Issue Found

`template_projection` has only eight features. `PLSRegression(n_components=16)` is invalid for that feature set.

## Fix

The benchmark now skips incompatible model and feature combinations and writes them to:

```text
results/tables/real_data_model_benchmark_skipped.csv
```

## Next Step

Rerun the benchmark and compare whether `template_projection` or `hybrid_path_template` reduces the error below the previous Ridge baseline.

