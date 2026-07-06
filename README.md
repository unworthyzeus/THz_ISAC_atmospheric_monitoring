# THz ISAC Atmospheric Monitoring

Repositorio de trabajo para el proyecto:

**Estimation Limits of Atmospheric Monitoring with Integrated Sensing and Communication in Sub THz Non Terrestrial Networks**

La idea central es estudiar si un enlace satelital sub THz puede reutilizar su información de canal para estimar contaminantes atmosféricos. El primer objetivo práctico es construir una cadena reproducible:

1. Modelo atmosférico estratificado.
2. Síntesis de CSI en banda ancha.
3. Separación entre absorción molecular y baseline de scattering por partículas.
4. Estimadores iniciales de concentración de gas y PM.
5. Métricas de error y límites de detectabilidad.

El código inicial usa un modelo sintético. Las líneas espectrales incluidas son marcadores de juguete, no datos reales de HITRAN. Sirven para validar el pipeline antes de conectar la base de datos espectroscópica.

## Estructura

| Ruta | Uso |
| --- | --- |
| `docs/` | Planificación, metodología, riesgos y notas de lectura |
| `src/thz_isac/` | Código Python del simulador y estimadores |
| `scripts/` | Entrypoints para ejecutar experimentos |
| `data/` | Datos sintéticos y procesados |
| `results/` | Tablas, figuras y métricas |
| `references/` | Propuesta, papers y páginas fuente |

## Primer experimento

Desde esta carpeta:

```powershell
python scripts/run_baseline.py
```

El script genera datos sintéticos, entrena regresión lineal y Ridge, y guarda métricas y figuras en `results/`.

Para un primer barrido de SNR:

```powershell
python scripts/run_snr_sweep.py
```

## Próximo paso científico

Sustituir las líneas espectrales sintéticas por consultas a HITRAN para gases objetivo. Hasta que eso esté hecho, cualquier resultado numérico debe interpretarse como prueba de ingeniería del pipeline, no como conclusión física.
