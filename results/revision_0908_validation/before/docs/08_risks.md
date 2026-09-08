# Risks

## Weak Lines

Some target gases may not have useful lines in the 60 to 400 GHz band.

Mitigation: inspect HITRAN line availability before committing to a gas.

## PM And Gas Confounding

Smooth PM attenuation can hide weak gas notches.

Mitigation: use baseline separation and report uncertainty.

## Unrealistic Link Budget

Sub THz satellite links may require very high antenna gains and favorable elevation.

Mitigation: report SNR sweeps instead of a single optimistic point.

## Synthetic Overclaiming

Simulation based on invented parameters can produce impressive but meaningless errors.

Mitigation: use HITRAN and public air quality data for main results.

## Excessive Scope

HITRAN, atmospheric layers, scattering, and estimation bounds can grow quickly.

Mitigation: keep the first real data pipeline minimal and reproducible.

