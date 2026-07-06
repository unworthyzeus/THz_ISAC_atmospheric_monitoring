# Estimadores de ML

## Principio

Empezar por modelos que se puedan explicar. Si la física produce firmas casi lineales tras normalización espectral, una regresión lineal debería dar un baseline razonable.

## Baseline 1: Regresión lineal

Entrada:

```text
vector de atenuación relativa por frecuencia
```

Salida:

```text
[gas_ppm, pm_ug_m3]
```

Ventajas:

1. Fácil de interpretar.
2. Rápida de entrenar.
3. Permite ver qué frecuencias pesan más.

Limitaciones:

1. Sensible a colinealidad.
2. Puede fallar si hay mezcla no lineal fuerte.
3. No impone positividad.

## Baseline 2: Ridge

Mismo input y output, con regularización L2.

Debe ayudar si hay muchas subportadoras cercanas y correlacionadas.

## Candidatos siguientes

1. Lasso para seleccionar frecuencias.
2. PLS para manejar espectros correlacionados.
3. Random Forest como baseline no lineal.
4. Red pequeña solo si los modelos simples fallan de forma informativa.

## Métricas

1. MAE.
2. RMSE.
3. R2.
4. Error relativo cerca del suelo de detección.
5. Sesgo frente a elevación.

