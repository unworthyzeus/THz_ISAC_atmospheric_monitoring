# SNR Sweep Experiment

## Goal

Measure whether estimator error increases as SNR decreases in the toy pipeline.

## Command

```powershell
python scripts/run_snr_sweep.py
```

## Outputs

```text
results/tables/snr_sweep_metrics.csv
results/figures/snr_sweep.png
```

## Initial Result

With `ridge_alpha_10`, the toy benchmark improved as SNR increased.

| SNR dB | Gas R2 | PM R2 | Gas RMSE | PM RMSE |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.41 | 0.33 | 26.92 | 42.29 |
| 20 | 0.57 | 0.58 | 22.83 | 33.54 |
| 45 | 0.64 | 0.64 | 20.99 | 30.97 |

## Limitation

These numbers come from the toy synthetic model. They are useful only for software validation.

