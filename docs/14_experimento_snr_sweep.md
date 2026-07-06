# Experimento SNR sweep

## Objetivo

Medir cómo se degrada la estimación de gas y PM cuando baja el SNR.

## Comando

```powershell
python scripts/run_snr_sweep.py
```

## Salidas

```text
results/tables/snr_sweep_metrics.csv
results/figures/snr_sweep.png
```

## Interpretación esperada

Si el pipeline tiene sentido, R2 debería subir con SNR y RMSE debería bajar. Si no ocurre, puede haber un problema de simulación, normalización o fuga de variables.

## Limitación actual

El barrido usa líneas espectrales sintéticas. Sirve para validar la maquinaria experimental, no para afirmar sensibilidad física real.

## Resultado inicial

Con `ridge_alpha_10`, el resultado mejora al subir SNR:

| SNR dB | R2 gas | R2 PM | RMSE gas | RMSE PM |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.41 | 0.33 | 26.92 | 42.29 |
| 20 | 0.57 | 0.58 | 22.83 | 33.54 |
| 45 | 0.64 | 0.64 | 20.99 | 30.97 |

La tendencia es razonable, pero el techo de R2 sigue siendo moderado. Esto apunta a que el siguiente trabajo no es meter un modelo más grande, sino mejorar la separación física entre muescas moleculares y baseline de partículas.
