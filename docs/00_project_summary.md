<!-- review-2026-09-05 -->
# Current interpretation: September 5, 2026

RESULT: Training-only Ridge has normalized RMSE 0.3474443 versus 0.3474789 for the training-mean predictor. Its difference is −0.00003458, with a 30-day block interval [−0.00010382, 0.00003264] that crosses zero. The 7-day sensitivity interval also crosses zero; no stable spectral gain is demonstrated. See the [current revision and evidence ledger](revision_review.md).

The earlier notes below are retained as historical records. Their original conclusions, uncertainty statements, test counts, and PDF hashes are superseded where the revision says so.

<!-- end-review-banner -->

# Project Summary

## Research Question

Can a sub THz non terrestrial communication downlink estimate atmospheric pollutants from channel state information amplitudes while preserving the communication function?

## Initial Hypothesis

Molecular absorption creates localized spectral notches, while particulate matter creates a smoother frequency dependent baseline. If the link has enough bandwidth, spectral resolution, and SNR, an estimator should be able to separate these two effects.

## Minimum Defensible Result

A reproducible simulation framework based on external physical data that estimates:

1. PM concentration.
2. Gas concentration for one or more target gases.
3. Detection floors as a function of SNR, bandwidth, and satellite elevation.

## Ambitious Result

A full framework containing:

1. A line by line absorption model from HITRAN.
2. A particulate matter attenuation model from published Rayleigh or Mie scattering theory.
3. Simple, interpretable estimators.
4. Machine learning baselines.
5. A lower bound analysis such as CRB or BCRB.

## Current Direction

The toy synthetic pipeline remains available only to test software. The actual research path must use external data and published models.
