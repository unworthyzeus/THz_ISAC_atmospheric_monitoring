# Riesgos

## Riesgo 1: líneas espectrales débiles

Puede que en 60 a 400 GHz los gases objetivo tengan líneas demasiado débiles para el SNR del enlace.

Mitigación: selección temprana de gases y cálculo de sensibilidad mínima con HITRAN.

## Riesgo 2: confundir PM con absorción gaseosa

Una tendencia suave puede ocultar muescas pequeñas.

Mitigación: usar separación de baseline, filtros de alta frecuencia y estimadores multisalida.

## Riesgo 3: link budget poco realista

Sub THz satelital exige antenas direccionales, pérdidas altas y potencia limitada.

Mitigación: documentar supuestos y hacer barridos de SNR en lugar de fijar un único escenario.

## Riesgo 4: demasiada física para el tiempo disponible

HITRAN, broadening, perfiles verticales y scattering pueden crecer rápido.

Mitigación: mantener un baseline simplificado funcionando y añadir complejidad por capas.

## Riesgo 5: resultados bonitos pero no defendibles

Un modelo de ML puede ajustarse a simulación sintética sin aportar insight.

Mitigación: comparar contra modelos lineales, coeficientes interpretables y bounds analíticos.

