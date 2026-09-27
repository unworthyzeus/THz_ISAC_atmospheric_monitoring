# Measurement protocol required for external validation

This is a proposed acquisition and acceptance protocol, not a completed experiment. **INFERENCE:** The new modeled result makes persistent spectral calibration and actual sweep resources necessary inputs to a defensible retrieval claim. The quantitative motivation is the [represented-model lower-bound table](../results/continuation_calibration_floor/floors.csv) and the [resource accounting](../results/continuation_calibration/resources.csv).

## Freeze before final evaluation

1. Define the target as surface concentration or path-integrated column, with units, averaging interval and reference-instrument uncertainty. **INFERENCE:** A surface record cannot validate a slant column without a measured profile or an explicitly validated conversion; the present profile is a modeling assumption. [Current model and evidence boundary](../paper/main.tex).
2. Fix the actual instrument, frequency list, transmit power at the relevant reference plane, sweep order, dwell, retuning and integration time. Measure delivered power and receiver behavior instead of substituting a typical catalog number. **SOURCE STATEMENT:** The manufacturer provides typical test-port specifications for the 260–400 GHz extender; it does not characterize this proposed LEO receiver. [VDI official specification table, WM-710 row](https://vadiodes.com/vna-extenders-vnax/), [extracted source record and access limitation](../results/continuation_calibration/source_record.json).
3. Allocate distinct calibration and final evaluation periods before fitting the estimator. Determine background/profile uncertainty and calibration bounds using calibration data only, then freeze the estimator, covariance rule and acceptance criterion. **INFERENCE:** Reusing final attenuation truth to select the error envelope would remove the intended external test. [Current design and stress-replay protocol](../results/continuation_calibration/protocol.json).

## Required synchronized records

Store sweep ID, calibration/evaluation split, UTC start/end, frequency in GHz, per-tone dwell and pilot count, measured power and its reference plane, reference and sample receiver readings, derived attenuation in dB, quality flags and calibration version. At the same averaging interval store target concentration/column, units and uncertainty, temperature, pressure, humidity, path geometry and the vertical-profile measurements or assumptions. Preserve raw readings so the attenuation and quality decisions can be recomputed. **INFERENCE:** These fields are needed to instantiate the forward mean, random covariance, persistent bias and acquisition time separately. [Estimator and acquisition equations](../paper/continuation_results.tex).

## Calibration and acceptance analysis

Repeated reference observations across the full sweep and over the relevant duration should estimate frequency covariance and distinguish repeatable drift from independent fluctuations. The box radius in the current paper is an assumed stress parameter, not a measured bound or a confidence region. If measured error is structured, compare a separately justified structured set with the box rather than quietly narrowing it after observing final retrieval outcomes. **INFERENCE:** The support-function formula and unbiased-linear lower bound can then be recomputed for the frozen set. [Risk formula and certificate scope](../paper/continuation_results.tex), [serialized certificates](../results/continuation_calibration_floor/certificates.json).

Evaluate error against independent synchronized truth on every retained final interval, report missing/failed sweeps in the denominator, and propagate reference-instrument uncertainty. Prespecify error normalization, averaging period, aggregate and worst-condition metrics, acceptable failure rate and resource budget. **INFERENCE:** The current unit threshold uses concentration magnitude references and does not itself supply a field acceptance specification. [Evidence and fixed physical model](../paper/main.tex).

## Current status

No synchronized attenuation/truth dataset meeting this protocol was acquired in this continuation. Hardware measurement, independent calibration and final external evaluation remain outstanding. The [bounded source search](continuation_source_search.md) records the access attempts and explains why nearby optical or laboratory examples were not substituted for this evidence.
