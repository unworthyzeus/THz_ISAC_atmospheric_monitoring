# External Data Acquisition

## Purpose

The project moved away from invented synthetic inputs. This note documents the external data sources that will drive the next benchmark and the IEEE paper draft.

## Source 1: HITRAN

HITRAN is used for real spectroscopic line parameters in the project band.

Frequency band:

```text
60 to 400 GHz
```

Equivalent wavenumber range:

```text
2.001 to 13.343 cm^-1
```

Downloaded molecules:

| Molecule | HITRAN ID | Role |
| --- | ---: | --- |
| O3 | 3 | target gas |
| CO | 5 | target gas |
| SO2 | 9 | target gas |
| NO2 | 10 | target gas |
| H2O | 1 | background gas |
| O2 | 7 | background gas |

The current download uses the main isotopologue for each molecule.

## Source 2: UCI Beijing Multi Site Air Quality

The UCI dataset provides real hourly pollutant concentration records from 12 monitoring sites in Beijing between 2013 03 01 and 2017 02 28.

Fields used:

1. PM2.5.
2. PM10.
3. SO2.
4. NO2.
5. CO.
6. O3.
7. Meteorological variables.

The dataset DOI is `10.24432/C5RK5G`.

## Script

Command:

```powershell
python scripts/download_external_data.py
```

Expected outputs:

```text
data/processed/hitran/hitran_60_400GHz_lines.csv
data/processed/air_quality/beijing_air_quality_clean.csv.gz
data/processed/air_quality/beijing_air_quality_model_sample.csv.gz
data/processed/external_data_summary.json
```

## Why This Is Better Than The Toy Dataset

The old toy dataset used invented spectral lines and uniformly sampled labels.

The new pipeline uses:

1. Real line positions and intensities from HITRAN.
2. Real pollutant concentration distributions from measured air quality records.
3. A forward model that can be inspected and replaced with more detailed physics.

## Remaining Limitations

1. CSI is still simulated.
2. The first HITRAN download uses only the main isotopologue.
3. Absolute absorption scaling still needs careful physical calibration.
4. PM attenuation still needs a published scattering model implementation.

