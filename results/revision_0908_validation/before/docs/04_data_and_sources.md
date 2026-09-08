# Data And Sources

> **Historical planning record:** This file predates the completed external data acquisition and physical study. Its pending language is retained to show the original plan. The canonical current provenance record is `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

## Saved References

Local copies of papers and source pages are stored under:

```text
references/
```

The proposal is stored at:

```text
references/proposals/I2R_proposal_THz_ISAC.pdf
```

## HITRAN Data

Planned use:

1. Download line by line parameters for selected gases.
2. Restrict the frequency range to 60 to 400 GHz.
3. Store processed line tables under `data/processed/hitran/`.
4. Record molecule IDs, isotopologue IDs, wavenumber limits, and download date.

## Air Quality Data

The project needs real pollutant concentration labels. A suitable dataset should include:

1. PM2.5 or PM10.
2. At least one HITRAN gas such as CO, O3, SO2, or NO2.
3. Timestamped observations.
4. Clear units.

## Toy Synthetic Data

The previous toy synthetic data remains in `data/synthetic/`.

It is retained only for software tests and should not be used as main evidence in the IEEE paper.

## Real Data Status

External data acquisition is the next active task.
