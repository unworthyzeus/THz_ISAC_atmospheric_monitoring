# Resultado baseline 0

## Ejecución

Comando:

```powershell
python scripts/run_baseline.py
```

Salida principal:

```text
results/tables/baseline_metrics.csv
results/tables/baseline_predictions.csv
results/figures/baseline_scatter.png
```

## Métricas

| Modelo | Objetivo | MAE | RMSE | R2 | Bias |
| --- | --- | ---: | ---: | ---: | ---: |
| LinearRegression | gas_ppm | 18.90 | 23.52 | 0.55 | 1.28 |
| LinearRegression | pm_ug_m3 | 27.53 | 35.77 | 0.52 | 1.25 |
| Ridge alpha 1 | gas_ppm | 18.83 | 23.38 | 0.55 | 1.29 |
| Ridge alpha 1 | pm_ug_m3 | 27.36 | 35.50 | 0.53 | 1.27 |
| Ridge alpha 10 | gas_ppm | 18.46 | 22.72 | 0.58 | 1.29 |
| Ridge alpha 10 | pm_ug_m3 | 26.53 | 34.15 | 0.56 | 1.35 |

## Lectura rápida

El baseline no está ciego: recupera parte de la señal sintética. Pero el ajuste todavía es moderado, con R2 alrededor de 0.55. Esto tiene sentido porque la simulación mezcla SNR, elevación, gas y PM, mientras que el modelo solo recibe el espectro relativo.

Ridge mejora un poco frente a regresión lineal pura. Esto sugiere colinealidad entre subportadoras, algo esperable en espectros densos.

## Acciones siguientes

1. Añadir elevación y SNR como features auxiliares, pero controlando que no sustituyan a la firma espectral.
2. Probar baseline correction con polinomio para aislar muescas.
3. Entrenar un estimador para PM usando solo componentes suaves y otro para gas usando espectro residual.
4. Hacer barrido de SNR para encontrar suelo de detección.
5. Integrar líneas HITRAN reales antes de interpretar valores absolutos.

