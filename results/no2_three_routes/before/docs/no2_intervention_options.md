# NO2 intervention options

## What was checked and why

**RESULT:** Six idealized additional-information cases were evaluated on the existing 202 probes to identify which interventions could reduce the NO₂ persistent-bias floor. These are hypothetical information ablations of the stored physical model, not newly measured data. The atmospheric discrepancy case removes the complete archived error matrix; it is a stronger oracle than measuring surface temperature alone. [Protocol](../results/no2_intervention_audit/protocol.json), [script](../scripts/no2_intervention_audit.py).

## Quantitative findings

At the assumed persistent spectral-error radius of 0.0001 dB, the represented-model noise-free lower bounds are:

| Ideal additional knowledge | Rounded lower bound |
| --- | ---: |
| Current estimator constraints | 1.984 |
| Entire archived atmospheric discrepancy subtracted exactly, original linear nuisance still unknown | 1.361 |
| Other gas concentrations known, atmospheric discrepancy retained | 1.581 |
| Linear nuisance coefficients known, atmospheric discrepancy retained | 1.340 |
| Atmospheric discrepancy and other gas concentrations known, original linear nuisance still unknown | 1.341 |
| All modeled non-NO₂ quantities known exactly | 0.532 |

**RESULT:** The entries are rounded displays of the recorded primal/dual calculations. The very favorable last row is an oracle, not a proposed achievable receiver. [Exact records](../results/no2_intervention_audit/oracle_floors.csv), [serialized dual certificates](../results/no2_intervention_audit/certificates.json).

**RESULT:** With the current information constraints, the numerical noise-free unit-bias crossing occurs at a calibration radius near 0.0000401774 dB. Its low endpoint uses a numerically feasible primal; this is not a physical receiver tolerance certified with intervals. Noise requires additional margin. [Bisection trace](../results/no2_intervention_audit/calibration_crossing.csv), [scope](../results/no2_intervention_audit/summary.json).

**RESULT:** The earlier finite-resource grid gives worst NO₂ replay RMSE 0.992965 at radius 0.00001 dB, ten million ideal simultaneous pilots and zero independent random residual. At the same radius, sequential −1 dBm 260–400 GHz acquisition gives 7.025 at ten seconds and 2.369 at one hundred seconds. Reducing persistent bias therefore does not by itself fix the sequential receiver's noise budget. These reuse the existing 64 atmospheric stress states. [Complete finite-resource table](../results/continuation_calibration/summary.csv).

## Recommended experiments

1. **INFERENCE: Differential acquisition is the first intervention to test.** Alternate or interleave reference and sample observations through a shared receiver. If a persistent spectral error is identical at both times, subtraction cancels it exactly: `(y_t − y_0) = D(θ_t − θ_0) + N(β_t − β_0) + (n_t − n_0)`. A changing forward model adds its own difference error. Independent equal observation noise doubles the variance, and residual calibration drift must be measured. The resulting target is a concentration change; absolute concentration additionally needs an independently known baseline with propagated uncertainty. This proposal changes the observation model assumed by the existing lower bound. [Current error equation and lower-bound scope](../paper/continuation_results.tex).
2. **INFERENCE: Characterize the actual spectral drift before choosing its uncertainty set.** Fit gain, spectral slope and any repeatable instrumental structure using separate calibration observations, then bound the residual on an untouched period. The current box permits arbitrary shapes, including the one most confusable with NO₂. A physically justified structured error model might be less restrictive. An offset alone is already eliminated by the existing nuisance model, and narrowing the box without measurements is not an improvement. [Existing nuisance model](../paper/main.tex), [required calibration records](continuation_measurement_protocol.md).
3. **SELF-DERIVED / INFERENCE: Redesign the spectral observations and allocation.** Recompute the HITRAN forward model on a finer grid around candidate NO₂ features, include line and nearby control frequencies, and optimize dwell at the same total time, energy and retuning cost. Dropping some of the existing 202 probes cannot lower the optimal noise-free floor: extend a subset estimator by zero coefficients to obtain an admissible full-grid estimator. New frequencies can change identifiability; time allocation can change variance. Neither improvement has yet been demonstrated for the new design. [Original coefficient/probe provenance](../results/continuation_calibration/manifest.json), [subset argument recorded with the audit](../results/no2_intervention_audit/summary.json).

## External reference or alternative modality

**SOURCE STATEMENT:** Womack et al. demonstrate an optical NO₂ instrument using a 457 nm LED and cavity enhancement, with laboratory precision of 43 ppt at one second and 7 ppt at thirty seconds, and UAV profiles between ground level and 110 m. These are optical in situ measurements, not sub-THz slant-column retrieval. [Published PDF](https://amt.copernicus.org/articles/15/6643/2022/amt-15-6643-2022.pdf), physical pp. 1 and 6–7, abstract and Sections 5.3–5.4.

**INFERENCE:** An independent optical instrument could provide NO₂ baseline or validation measurements while THz supplies the communication channel and other conditional sensing targets. The experiment would need matched sampling and path/profile treatment; point concentration cannot silently stand in for a satellite-path column. This would be a hybrid system or external reference, not a demonstration that THz alone retrieves NO₂. [Source measurement geometry](https://amt.copernicus.org/articles/15/6643/2022/amt-15-6643-2022.pdf), physical pp. 6–7, Section 5.4; [project evidence boundary](../paper/main.tex).

## What remains

The next bounded computational task is a differential-observation model with an explicit drift/noise budget, followed by an independently frozen denser-frequency and dwell design. The present note prioritizes those tasks; it does not report them as completed. The acquisition hardware, measured drift structure, independent NO₂ truth and transfer from relative to absolute concentration remain required external evidence. [Acquisition protocol](continuation_measurement_protocol.md).
