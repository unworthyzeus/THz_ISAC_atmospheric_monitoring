# Experimentos

## Experimento 0

Objetivo: comprobar que el pipeline funciona.

Configuración:

| Parámetro | Valor inicial |
| --- | --- |
| Frecuencia mínima | 60 GHz |
| Frecuencia máxima | 400 GHz |
| Subportadoras | 256 |
| Muestras | 2000 |
| SNR | 20 a 45 dB |
| Elevación | 15 a 80 grados |

Modelos:

1. LinearRegression.
2. Ridge.

Resultados:

1. Métricas CSV.
2. Scatter plot de real contra predicho.
3. Coeficientes por frecuencia.

## Experimento 1

Barrido de SNR:

```text
SNR = 0, 5, 10, 15, 20, 25, 30, 40 dB
```

Medir cuándo el error se vuelve inaceptable.

## Experimento 2

Barrido de elevación:

```text
elevación = 10 a 85 grados
```

Evaluar si el slant path bajo mejora sensibilidad o degrada demasiado la comunicación.

## Experimento 3

Número de subportadoras:

```text
32, 64, 128, 256, 512
```

Sirve para conectar resolución espectral con detectabilidad.

