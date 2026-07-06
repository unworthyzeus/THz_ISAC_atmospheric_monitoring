# Plan de trabajo

## Semana 1

1. Ordenar literatura y referencias.
2. Implementar simulador sintético de CSI.
3. Crear baseline de regresión lineal para gas y PM.
4. Generar primeras métricas de MAE, RMSE y R2.
5. Identificar qué gases tienen líneas útiles en 60 a 400 GHz.

## Semana 2

1. Integrar perfiles atmosféricos por capas.
2. Añadir geometría de slant path con elevación satelital.
3. Separar explícitamente pérdidas de comunicación y firma atmosférica.
4. Añadir Ridge, Lasso y PLS.
5. Empezar notas para sección de metodología.

## Semana 3

1. Conectar HITRAN o una extracción exportada desde HITRANonline.
2. Seleccionar gases objetivo realistas.
3. Sustituir líneas sintéticas por líneas reales.
4. Barrido de SNR, ancho de banda y número de subportadoras.
5. Crear primeras figuras de detectabilidad.

## Semana 4

1. Derivar o implementar un CRB inicial.
2. Comparar error empírico contra bound.
3. Estudiar sensibilidad a elevación y ruido.
4. Documentar límites y supuestos.
5. Preparar una mini presentación interna.

## Entregables tempranos

1. `results/tables/baseline_metrics.csv`
2. `results/figures/baseline_scatter.png`
3. `docs/03_modelo_fisico.md`
4. `docs/05_estimadores_ml.md`
5. `docs/10_preguntas_abiertas.md`

