# Real Data Inputs and Physical Feasibility Results

## Result Status

This document supersedes the former `0.07793` mean normalized RMSE headline. The current main result is a physical detectability study with real UCI concentration scenarios, real HITRAN line parameters, calibrated gas spectroscopy, a declared NTN link, simulated attenuation observations, and analytical estimation bounds.

The main result is negative: the declared reference configuration does not support WHO guideline scale retrieval for any of the six reported pollutants.

## What Was Run

```powershell
python scripts/run_data_quality_audit.py
python scripts/validate_physical_spectroscopy.py
python scripts/run_physical_feasibility.py
```

The feasibility script produced calibrated signal summaries, informative frequency rankings, a reference link budget, Fisher information and CRB values, sensitivity sweeps, and a chronological estimator benchmark that was originally held out.

## Why It Was Run

The old benchmark answered whether a simplified simulator could encode and recover pollutant labels using a shared normalized template design. It did not answer whether real spectroscopic signatures are large enough to estimate under a plausible observation model.

The new study addresses signal magnitude and lower bounds before treating machine learning accuracy as physical evidence.

## Evidence Classification

| Evidence | Classification |
| --- | --- |
| Pollutant concentrations and meteorology | Real measurements from the UCI Beijing Multi Site Air Quality dataset, DOI `10.24432/C5RK5G` |
| Molecular line positions, intensities, broadening, shifts, and lower state energies | Real HITRAN line data |
| Molecular absorption coefficients | Calculated with a local Voigt implementation and checked against HAPI |
| Pollutant vertical profiles | Assumed exponential profiles |
| PM particle properties | Exploratory assumptions in a Rayleigh mass extinction model |
| Wideband attenuation and CSI | Simulated, with no paired measured sub THz channel data |
| Detection floors | Analytical one sigma CRB values conditional on the model and link assumptions |

## Input Data Results

The processed UCI table contains 383,585 complete case station hour rows from 12 sites. It retains 91.163% of the 420,768 source rows. It has no duplicate station hour keys and no nonpositive targets. There are 17,642 PM ordering violations where PM10 is below PM2.5, so those records are excluded from fine and coarse PM decomposition in the simulated estimator benchmark.

The HITRAN table contains 9,340 lines from 60 to 400 GHz:

| Molecule | Line count |
| --- | ---: |
| CO | 15 |
| H2O | 37 |
| NO2 | 1,536 |
| O2 | 45 |
| O3 | 1,301 |
| SO2 | 6,406 |

## Physical Model and Validation

The physical design uses temperature adjusted line intensities, TIPS 2025 partition sums, pressure broadening and shift, Doppler broadening, Voigt line shapes, and 24 layer vertical integration. UCI median temperature, pressure, and dew point define the reference surface condition.

The local cross sections were compared directly with HAPI on the 256 point reference grid for all six molecules. Every molecule passed peak relative error and normalized active grid RMSE thresholds of `1e-5`. The largest peak relative error was below `6.4e-7`, and the largest normalized active grid RMSE was below `1.6e-7`.

This validates the local line shape calculation at the tested reference condition. It does not validate pollutant vertical profiles, particulate matter, the link budget, or field retrieval.

## Reference Configuration

| Parameter | Value |
| --- | ---: |
| Frequency probes | 256 points from 60 to 400 GHz |
| Atmospheric layers | 24 from 0 to 12 km |
| Pollutant scale height | 1,500 m |
| Water scale height | 2,000 m |
| PM scale height | 1,000 m |
| Satellite altitude | 550 km |
| Elevation | 45 degrees |
| Total transmit power | 23 dBm |
| Transmit aperture | 0.50 m |
| Receive aperture | 0.30 m |
| Bandwidth per probe | 1 MHz |
| Receiver noise figure | 6 dB |
| Implementation loss | 5 dB |
| Pilots | 30 |
| Assumed independent residual standard deviation per tone | 0.63 dB |

The probes are a multiband feasibility grid. They must not be described as one contiguous 340 GHz OFDM allocation.

At 45 degrees, the spherical Earth slant range is 749.1 km. Median link SNR is 14.97 dB, its fifth percentile is minus 70.80 dB because some atmospheric lines are opaque, its ninety fifth percentile is 20.64 dB, and 206 of 256 probes exceed 5 dB.

## Calibrated Signal Magnitudes

At the UCI ninety fifth percentile concentration and 45 degrees elevation:

| Target | UCI Q95, micrograms per cubic meter | Peak excess attenuation, dB | Peak frequency, GHz | Peak divided by 0.63 dB |
| --- | ---: | ---: | ---: | ---: |
| CO | 3,500 | 0.031856 | 345.33 | 0.0506 |
| O3 | 177 | 0.004837 | 358.67 | 0.00768 |
| SO2 | 59 | 0.015169 | 357.33 | 0.0241 |
| NO2 | 117 | 0.001134 | 396.00 | 0.00180 |
| PM2.5 | 242 | 0.000123 | 400.00 | 0.000195 |
| PM10 | 279 | 0.000136 | 400.00 | 0.000215 |

All peak signatures are below the assumed independent residual per tone standard deviation. Most are smaller by two to four orders of magnitude. The 0.63 dB value is borrowed as a scenario from adjacent literature and is not calibrated for this sub THz pollutant link.

## Detection Floors

The gas values use a joint four gas CRB with background and PM spectral nuisance columns. PM2.5 is an optimistic single fine mode bound. PM10 assumes a fixed UCI median fine fraction of 0.7681. These PM bounds are optimistic because freely separating fine and coarse modes is practically nonidentifiable.

| Target | One sigma floor, micrograms per cubic meter | Gas floor, ppm | WHO 2021 guideline | Floor divided by guideline |
| --- | ---: | ---: | ---: | ---: |
| CO | 83,015 | 71.88 | 4,000, 24 h | 20.8 |
| O3 | 28,099 | 14.19 | 100, 8 h | 281.0 |
| SO2 | 4,308 | 1.632 | 40, 24 h | 107.7 |
| NO2 | 64,427 | 33.95 | 25, 24 h | 2,577.1 |
| PM2.5 | 1,513,315 | Not applicable | 15, 24 h | 100,887.7 |
| PM10 | 1,581,204 | Not applicable | 45, 24 h | 35,137.9 |

WHO 2021 values are health guideline comparison levels with target specific averaging periods. The CRB is for one pilot burst. The ratios are scale comparisons across unequal averaging periods and do not verify regulatory compliance.

## Sensitivity Results

The full table is `results/tables/physical_sensitivity.csv`.

1. At 15 degrees elevation, the longer pollutant path improves the floor despite lower median SNR. The best CO ratio in the elevation sweep is still 10.36, and every other target remains much worse.
2. Increasing pilots from 30 to 3,000 reduces the CO ratio from 20.75 to 12.78, but the assumed residual term causes strong saturation.
3. Increasing total transmit power from 23 to 33 dBm reduces the CO ratio only from 20.75 to 20.41 because the assumed residual term dominates.
4. Increasing active probes from 64 to 256 improves every floor even though total power is divided across more probes. The extra spectral information outweighs the per probe SNR loss in this grid.
5. Even with residual per tone standard deviation set to zero, the reference CO ratio is 16.39 and all other targets remain far above one.

The one factor sweeps do not identify a floor to guideline ratio below one.

An additional optimistic combined stress test uses 15 degrees elevation, 3,000 pilots, zero residual per tone error, 33 dBm total power, and 256 probes. It is not a proposed deployment. Its one sigma ratios are:

| Target | Optimistic one sigma floor, micrograms per cubic meter | One sigma ratio | Three sigma ratio |
| --- | ---: | ---: | ---: |
| CO | 2,597 | 0.649 | 1.948 |
| O3 | 919 | 9.190 | 27.570 |
| SO2 | 174 | 4.350 | 13.050 |
| NO2 | 2,205 | 88.204 | 264.612 |
| PM2.5 | 53,072 | 3,538.135 | 10,614.404 |
| PM10 | 55,453 | 1,232.290 | 3,696.869 |

Only CO crosses the health guideline concentration scale at one sigma in this combined stress test, but its three sigma ratio is 1.948. This is not a robust detection success. The result prevents a universal impossibility claim, but it does not demonstrate operational CO sensing: the residual is set to zero, the geometry and pilot count are optimistic, and a single burst is still compared with a 24 h health guideline.

## Originally Held Out Estimator Benchmark

The estimator benchmark uses 20,000 deterministic records sorted by timestamp and station. The split contains 12,000 training records, 4,000 validation records, and 4,000 records in a test period that was untouched for the original benchmark. Later robustness and model diagnostics reuse this period and are not confirmatory. The forward atmosphere and PM composition use full period medians as declared transductive scenario parameters. The benchmark excludes the 17,642 full dataset rows where PM10 is below PM2.5 before sampling.

The initial Ridge grid ended at alpha `10,000`, and the optimum lay on that boundary. That run was not accepted as a completed search. The expanded grid spans `0.01` through `100,000,000` and selects the interior value alpha `100,000` using validation data only.

| Model | Mean test normalized RMSE | Mean test R2 | Interpretation |
| --- | ---: | ---: | --- |
| Training period mean | 0.347479 | -0.08316 | No signal baseline |
| Ridge selected on validation | 0.347443 | -0.08293 | Numerically close to mean; conditional bootstrap interval includes zero |
| Oracle gas WLS with true PM removed | 157.696 | -440,072.7 | Physical inverse dominated by noise |
| Mismatched gas WLS with true PM removed | 207.575 | -761,726.0 | Model mismatch worsens failure |

The Ridge test score is only `0.0000354` lower in mean normalized RMSE than the mean baseline, and both have negative mean R2. The final broad regularization is consistent with shrinkage toward target means rather than useful spectral recovery.

Direct physical WLS produces negative estimates for about half the cases, as expected for an unconstrained estimator when the signal is far below noise. Nonnegative constraints could remove invalid signs, but they cannot create missing information.

## PM Identifiability

The fine and coarse PM spectral columns have correlation `0.999999995`. After scaling all target columns by UCI ninety fifth percentile concentrations, the smallest to largest singular value ratio is `2.61e-7`. The present frequency response therefore does not robustly distinguish fine from coarse PM.

The optimistic PM2.5 and fixed composition PM10 CRBs are reported only to quantify scale. They are not evidence that two independent PM parameters are retrievable.

## Superseded Result

The former best result was:

| Feature set | Model | Mean normalized RMSE | Mean R2 |
| --- | --- | ---: | ---: |
| Shared template projection | Ridge, alpha 17.78 | 0.07793 | 0.94523 |

It used real UCI labels and real HITRAN line parameters, but gas templates were normalized to equal peak loss, label quantiles affected scaling, the forward and inverse paths shared the same design, and the test set was reused for selection. It is preserved as an engineering regression test only.

## What Remains

1. Measured paired channel and atmospheric truth data.
2. Independent validation of background attenuation and layer integration.
3. Realistic pollutant vertical profile uncertainty.
4. Calibrated PM optical properties and humidity response.
5. Instrument and clear sky reference uncertainty.
6. Real spectrum allocations and usable sensing bands.
7. Station holdout, repeated time windows, and external environment evaluation.

## Main Risks

The CRB is conditional on a linearized model, declared noise equation, assumed scale heights, and an exploratory PM model. The UCI surface values are not direct atmospheric columns. A different instrument or geometry may change the result. None of those caveats makes the current result positive; they define what must be validated before extrapolating it.

## Next Steps

Use the negative result as the IEEE paper thesis, preserve the exact model manifest and hashes, validate against independent propagation tools, and prioritize measured channel evidence before further machine learning optimization.

## Multi Method Real Data Extension

The unchanged Beijing chronological metric was reused for three ground sensor information classes:

| Information class | Test macro normalized RMSE | Boundary |
| --- | ---: | --- |
| Strictly causal forecast v2 | 0.095485 | Pollutant features are at least one hour old |
| Strict station reconstruction | 0.088890 | All six current query pollutant channels are masked |
| Single channel repair | 0.074855 | Only target `j` is masked; the other five current query channels are available |

The single channel result meets `0.08`, but it is a sensor repair result and cannot replace the strict reconstruction or THz inversion score. Mutation tests confirm that forbidden current targets cannot change the corresponding features.

A separate CC BY Mendeley dataset supplies real measured THz TDS summary spectra for aqueous lysozyme and ovalbumin. All 10 files were acquired anonymously and hash verified. A fixed 0.9 to 1.3 THz band gives absolute Spearman correlations `0.893` and `1.000`; leave one concentration out normalized RMSE is `0.272` and `0.127`, or `0.199270` macro. This is measured THz evidence, but it is a small protein concentration positive control rather than atmospheric or gas phase validation.

Full methods, failures, endpoint outcomes, and reproduction artifacts are recorded in `docs/34_multi_method_information_floor_study.md`.
