# Métricas

## Métricas de estimación

| Métrica | Uso |
| --- | --- |
| MAE | Error medio interpretable |
| RMSE | Penaliza errores grandes |
| R2 | Varianza explicada |
| Bias | Detecta sobreestimación sistemática |
| Error relativo | Importante para concentraciones bajas |

## Métricas de comunicación

| Métrica | Uso |
| --- | --- |
| SNR efectivo | Conecta sensing con enlace |
| Atenuación total | Evalúa viabilidad de link budget |
| Pérdida por atmósfera | Separa el canal físico de FSPL |
| Subportadoras útiles | Mide si hay ancho de banda informativo |

## Criterios de éxito

1. El estimador recupera tendencias correctas en datos sintéticos.
2. La estimación de gas depende de muescas y no de offset global.
3. La estimación de PM depende del slope suave con frecuencia.
4. Los errores aumentan de forma razonable al bajar SNR.
5. El modelo no aprende atajos obvios como elevación si se normaliza mal.

