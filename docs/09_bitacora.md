# Bitácora

## 2026 07 06

Se crea la carpeta de investigación y se copian las referencias descargadas.

Decisión inicial: trabajar el proyecto THz ISAC aunque tenga más riesgo teórico que UPSim. La razón es que puede producir un resultado más original y con una pregunta científica más clara.

Primer baseline elegido: regresión lineal multisalida sobre CSI sintética.

Pendiente inmediato:

1. Ejecutar `python scripts/run_baseline.py`.
2. Revisar métricas.
3. Elegir gases objetivo reales para HITRAN.
4. Decidir si el enfoque se centra en VOCs, PM o ambos.

Resultado del baseline 0:

1. El script ejecuta correctamente.
2. Los tests mínimos pasan.
3. Ridge con `alpha=10` consigue R2 aproximado de 0.58 para gas y 0.56 para PM en el modelo sintético.
4. El siguiente avance debería separar baseline suave y muescas antes de entrenar.
