# Metrics

## Estimation Metrics

| Metric | Use |
| --- | --- |
| MAE | Interpretable average error |
| RMSE | Penalizes large errors |
| R2 | Variance explained |
| Bias | Detects systematic overestimation or underestimation |
| Normalized RMSE | Allows gas and PM errors to be compared |

## Communication Metrics

| Metric | Use |
| --- | --- |
| Effective SNR | Connects sensing accuracy to link feasibility |
| Total attenuation | Checks link budget plausibility |
| Atmospheric attenuation | Separates sensing signature from path loss |
| Informative subcarriers | Measures useful spectral support |

## Success Criteria

1. Error decreases when physically relevant information is added.
2. Gas estimation depends on line features.
3. PM estimation depends on smooth spectral trend.
4. Error increases when SNR decreases.
5. Results remain valid on a held out test split.
6. Main claims use external data or published physical parameters.

