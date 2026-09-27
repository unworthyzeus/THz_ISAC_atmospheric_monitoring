# Continuation evidence, September 8, 2026

## What was done and why

The continuation tests the remaining claim boundary and records the result in the current manuscript's continuation section. **RESULT:** At assumed persistent error ±0.0001 dB, the exact represented-LP NO₂ bias lower bound is 1.9837335 with all 202 probes, above the unit target. The calibration-aware ten-million-pilot stress-replay error improves from 3.385 to 2.425 but remains above one. Evidence: [summary.csv](../results/continuation_calibration/summary.csv), [resources.csv](../results/continuation_calibration/resources.csv), [floors.csv](../results/continuation_calibration_floor/floors.csv), [certificates.json](../results/continuation_calibration_floor/certificates.json).

## Interpretation and limitations

**INFERENCE:** The guarantee covers the represented normalized linear constraints and finite atmospheric hull plus a spectral error box. It does not certify uncertain physical coefficients or nonlinear/prior-assisted estimators. The 64 atmospheric states are reused stress data; radio attenuation and receiver noise remain modeled. The precise scope and calculation are recorded in the [current continuation section](../paper/continuation_results.tex).

## What remains and next step

**INFERENCE:** Measure persistent spectral error and covariance over actual sweeps, with synchronized pollutant truth and a calibration period separate from final evaluation. This is an outstanding requirement, not completed validation; see the [claim boundary](../paper/continuation_results.tex).

The original incoming files remain in the portfolio [continuation snapshot](../../../00_research_portfolio/results/continuation_0908/before_manifest.json). The current PDF and test/render records are linked from the [portfolio continuation report](../../../00_research_portfolio/docs/09_continuation_0908.md).
