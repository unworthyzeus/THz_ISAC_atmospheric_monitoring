# Measurement protocol for the remaining experimental milestones

Date: 2026-09-23. This protocol makes the remaining measurements and acceptance decisions explicit. The user confirmed that no private paired data or laboratory setup is currently available. No experimental rows are invented, and this document is not a completed measurement campaign.

## What was prepared and why

The proposed study needs to distinguish a useful concentration measurement from a fitted value, a shared simulator assumption, or an unobserved calibration offset. The protocol separates hardware characterization, controlled species measurements, atmospheric transfer and a final independent evaluation.

## Hardware and frequency acquisition

The explicit communication reference is one 256 MHz OFDM block centred at 73.5 GHz, with 256 tones at 1 MHz spacing, 1/16 cyclic prefix and 30 required pilots per 10,000 symbols. This fits within a WR12 laboratory characterization band and the studied 71-76 GHz downlink reference. Its evaluated joint sensing performance is inadequate; this is a rejected sensing configuration, not a deployment recommendation.

Before selecting any broader sensing implementation, measure complex gain, absolute frequency accuracy, receiver noise, differential spectral drift, phase noise, antenna patterns, pointing sensitivity, polarization response and tuning/settling time. Measure each with timestamped source/reference configurations and instrument identifiers. Manufacturer dynamic range at a 10 Hz resolution bandwidth must not be substituted for a 1 MHz communication noise figure. Manufacturer stability limits are not a noise probability distribution.

The new 1% communication-rate-loss limits of approximately 29.01 kHz residual CFO or 0.0526 rad RMS phase jitter are separate model sensitivities. A real tracking design must allocate a joint budget and demonstrate it during changing Doppler; the ideal pass has sampled Doppler up to 1.211 MHz and about 23.5 kHz/s rate of change. The 139.73 s high-elevation pass is the time available to the modeled single pass, not 1,800 s.

For controlled laboratory checking of the public aerosol overlap, a 260-400 GHz VNA extender covers the four public measurement bins. Use finer sampling to characterize the instrument, but do not imply that resampling the existing 40 ps traces increases their approximately 25 GHz independent resolution. A sequential VNA acquisition is a separate characterization experiment, not simultaneous communication-pilot reuse.

## Required paired observations

Record the following before attempting concentration validation:

| Group | Required fields and purpose |
| --- | --- |
| Identity | Campaign, independent sample, instrument/calibration identifiers and file/source hashes. |
| Time | UTC start/end, per-frequency acquisition time, path synchronization and averaging interval. |
| Radio | Frequency, complex received/reference pilot or S21, power, bandwidth, pilot count, phase/timing corrections and their uncertainty. |
| Geometry | Path length, elevation, antenna position/pointing and line-of-sight verification. |
| Weather | Pressure, temperature, relative/absolute humidity with calibration and spatial sampling. |
| Gas truth | Independent H2CO, CH3OH and CH3CN reference concentrations, units, averaging time, detection floor and uncertainty. A molecular-line fit to the same radio data is not independent truth. |
| PM truth | Independently measured fine/coarse dry mass, mass-reference method, particle-size distribution, composition, density/shape information and humidity growth. Optical constants must cover the tested frequency window. |
| Blanks | Before/after blank and reference recordings, repeat measurements, fouling checks and drift across the complete acquisition. |
| Atmospheric mapping | Independent vertical profiles or column truth and documented transformation to the measured quantity. Surface labels alone are insufficient for a slant-column validation. |

The machine-readable header template is [paired_measurement_schema.csv](../results/five_task_closure/paired_measurement_schema.csv). It intentionally contains no observations. Multiple frequency rows belong to one observation ID; uncertainty/independence is assessed at the observation or campaign level, not by treating tones as independent environmental cases.

## Frozen evaluation design

1. Define the measurement quantity first: controlled-cell concentration, atmospheric column, or surface-air concentration with a separately validated profile mapping. Do not compare outdoor slant estimates against an indoor guideline.
2. Use independent calibration campaigns to estimate frequency response, residual covariance and persistent drift. Retain before/after blank discrepancies instead of fitting them away using final evaluation labels.
3. Freeze preprocessing, nuisance basis, frequency/power allocation, concentration range, detector thresholds, time coverage and exclusions before final evaluation. Split by independent campaign and time; do not random-split repeated traces of one sample.
4. Use the existing declared family-wise false-positive budget of 1% across six outputs and 95% detection power for the candidate limits. Report sensitivity, false positives and confidence intervals at several independently prepared concentrations, including blanks. Precision must use and disclose the actual evaluation prevalence.
5. Report signed bias, MAE/RMSE in physical units, confidence-interval coverage, fit boundaries, residual diagnostics and out-of-domain failures. Percentage error at zero truth is undefined. Keep nonlinear-boundary estimates separate from unconstrained Gaussian error bounds.
6. Test several plausible weather, composition and vertical-profile states with separately measured inputs. A model must not be recalibrated on the final evaluation campaign and then presented as a held-out result.
7. For the communication comparison, preserve the same hardware, channel, coded payload, transmit energy, mandatory pilots and scheduling. Compare decoded payload/BER or block-error rate, actual throughput, latency and availability. Resource equality alone is not modem performance.
8. For environmental comparisons, produce the required concentration average and coverage, including the annual percentile context for daily PM guidance. Do not extrapolate a stationary single pass into continuous daily coverage. WHO guidance is not itself a legal instrument certification.

There is no fabricated minimum sample count. Choose the number of independent positive and blank observations before collection using the desired confidence precision and false-positive/power targets. The existing 5,000 simulated draws per class are not 5,000 independent environmental samples.

## Result, limitations and next steps

The evaluation design, required schema, applicable-domain checks and current negative decisions are now concrete and reviewable. Public calcite data lack mass/size labels; published water data are aggregate, with raw data available on author request. No suitable paired atmospheric VOC/PM validation data were acquired in this bounded search. These experimental milestones therefore remain open. The next necessary input is a dataset meeting the table above or actual access to a calibrated measurement setup, followed by a preregistered independent evaluation.
