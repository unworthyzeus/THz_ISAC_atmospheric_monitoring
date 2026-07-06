# Pivot To Real Data

## Reason

The project should not present invented synthetic data as its main result.

The toy baseline is now treated as an engineering check:

1. It verifies code execution.
2. It verifies estimators and plots.
3. It does not support scientific claims.
4. It will not be the central result of the IEEE paper.

## New Rule

Main results must use external data or external physical parameters:

1. HITRAN spectroscopic line data.
2. Real pollutant concentration datasets.
3. Standard atmosphere models.
4. Published propagation and scattering models.

## Selected External Sources

### HITRAN

Use:

1. Line positions.
2. Intensities.
3. Broadening coefficients.
4. Candidate gases such as CO, O3, SO2, and NO2.

Project frequency range:

```text
60 to 400 GHz
```

Wavenumber conversion:

```text
wavenumber_cm^-1 = frequency_GHz / 29.9792458
```

### Public Air Quality Dataset

Use:

1. PM2.5 or PM10 records.
2. Gas concentration records.
3. Real temporal concentration distributions.

## Allowed Simulation

Allowed:

1. Simulated CSI using HITRAN lines.
2. PM attenuation from published Rayleigh or Mie models.
3. Real concentration records as labels.
4. Held out test evaluation.

Not allowed as main evidence:

1. Invented spectral lines.
2. Uniform random pollutant labels.
3. Toy template results presented as physical results.

## Updated Success Criterion

1. External data downloaded and documented.
2. HITRAN based forward model works.
3. Reproducible real data benchmark exists.
4. IEEE paper uses only external data driven results.

