# Ridge Alpha Sweep Plan

## Why This Sweep Exists

The broad external data benchmark found that Ridge with HITRAN template projection features currently gives the lowest mean normalized RMSE.

The broad benchmark only tested a few Ridge values. A focused alpha sweep is faster and more precise.

## Feature Sets Tested

1. `path_normalized`.
2. `template_projection`.
3. `hybrid_path_template`.

## Alpha Range

The sweep uses:

```text
alpha = logspace(-3, 3, 25)
```

## Command

```powershell
python scripts/run_real_ridge_sweep.py
```

## Outputs

```text
results/tables/real_data_ridge_alpha_sweep.csv
results/figures/real_data_ridge_alpha_sweep.png
```

## Expected Use

The best alpha from this sweep should define the Ridge configuration used in the paper results table.

