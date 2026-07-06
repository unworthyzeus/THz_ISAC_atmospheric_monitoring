# Datos y fuentes

## Referencias guardadas

Los PDF y páginas fuente están en:

```text
references/
```

La propuesta original está en:

```text
references/proposals/I2R_proposal_THz_ISAC.pdf
```

## HITRAN

Uso previsto:

1. Seleccionar gases objetivo.
2. Descargar o exportar líneas en 60 a 400 GHz.
3. Guardar una tabla local con frecuencia, intensidad, broadening y energía inferior.
4. Versionar la tabla procesada, no credenciales ni descargas privadas.

## Datos sintéticos

El pipeline actual genera datos en memoria. Si se necesita persistencia, usar:

```text
data/synthetic/
```

Campos esperados:

| Campo | Significado |
| --- | --- |
| `sample_id` | Identificador de muestra |
| `frequency_ghz` | Frecuencia de subportadora |
| `attenuation_db` | Atenuación simulada |
| `elevation_deg` | Elevación del satélite |
| `snr_db` | SNR nominal |
| `gas_ppm` | Concentración de gas sintética |
| `pm_ug_m3` | Concentración de partículas |

## Datos reales

No hay datos reales todavía. La ruta lógica es validar con datos de laboratorio o con simuladores atmosféricos si se consiguen.

