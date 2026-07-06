# Resumen del proyecto

## Pregunta de investigación

¿Puede un enlace de comunicación sub THz de una red no terrestre estimar contaminantes atmosféricos usando la amplitud de la CSI sin degradar de forma apreciable la comunicación?

## Hipótesis inicial

La absorción molecular produce muescas espectrales relativamente localizadas, mientras que el material particulado produce una tendencia suave con la frecuencia. Si el enlace tiene suficiente SNR y ancho de banda, un estimador puede separar ambas contribuciones.

## Resultado mínimo defendible

Un simulador reproducible que muestre, bajo supuestos explícitos, qué combinaciones de SNR, ancho de banda, elevación y concentración permiten estimar:

1. Densidad de PM.
2. Concentración de un gas objetivo.
3. Suelo de detección en función de SNR y geometría.

## Resultado ambicioso

Un framework con:

1. Línea de base analítica.
2. Estimadores de ML simples y explicables.
3. Comparación con lower bounds tipo Cramér Rao.
4. Validación contra perfiles atmosféricos y líneas HITRAN reales.

## Enfoque elegido

Empezar por estimadores sencillos. Primero regresión lineal, después Ridge o PLS. Si eso no funciona en el escenario sintético, no tiene sentido saltar a modelos complejos.

