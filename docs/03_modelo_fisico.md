# Modelo físico inicial

## Señal observada

La observación básica será la amplitud de la CSI por subportadora:

```text
y(f) = H_dB(f) + ruido
```

Para el baseline sintético:

```text
H_dB(f) = constante de enlace - L_fspl(f) - L_gas(f) - L_pm(f)
```

En los estimadores iniciales se trabaja con atenuación relativa, quitando la media espectral para reducir el peso de pérdidas comunes.

## Absorción molecular

Modelo sintético:

```text
L_gas(f) = ppm * sum_i a_i * perfil_i(f)
```

Los perfiles actuales son Lorentzianos simplificados. En la versión real deberán venir de HITRAN, usando posición, intensidad y broadening dependiente de presión y temperatura.

## Partículas PM

Modelo inicial tipo Rayleigh:

```text
L_pm(f) = c_pm * PM * (f / f0)^4
```

Este modelo es razonable como primera aproximación para partículas mucho menores que la longitud de onda. Si el tamaño de partícula se acerca a la longitud de onda, habrá que pasar a Mie o a un modelo empírico calibrado.

## Geometría

El slant path se aproxima como:

```text
path = altura_troposfera / sin(elevación)
```

Esto captura la dependencia principal con el ángulo de elevación. Después convendrá integrar capa por capa.

## Ruido

El ruido se añade en dB como gaussiano. Es una aproximación simple para probar estimadores. Más adelante conviene simular ruido complejo sobre CSI y después convertir a amplitud.

## Variables objetivo

1. `gas_ppm`
2. `pm_ug_m3`

La concentración de gas sintética representa un gas objetivo agregado. En el modelo HITRAN habrá que escoger gases concretos.

