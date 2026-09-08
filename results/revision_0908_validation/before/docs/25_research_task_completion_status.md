<!-- review-2026-09-05 -->
# Current interpretation: September 5, 2026

RESULT: Training-only Ridge has normalized RMSE 0.3474443 versus 0.3474789 for the training-mean predictor. Its difference is −0.00003458, with a 30-day block interval [−0.00010382, 0.00003264] that crosses zero. The 7-day sensitivity interval also crosses zero; no stable spectral gain is demonstrated. See the [current revision and evidence ledger](revision_review.md).

The earlier notes below are retained as historical records. Their original conclusions, uncertainty statements, test counts, and PDF hashes are superseded where the revision says so.

<!-- end-review-banner -->

# Research Task Completion Status

Updated on 2026 07 15 after probe optimization, the H2O control, and the preliminary real column study.

## Status Rules

| Status | Meaning |
| --- | --- |
| Completed for the current feasibility model | The implementation, tests, and study artifact exist, but the conclusion remains conditional on declared assumptions and simulated observations. |
| Partially completed | A working implementation exists, but a material physical calibration or integration gap remains. |
| Not completed | No implementation or evidence currently satisfies the task. |

## Overall Summary

| Task | Status | Current evidence | Main remaining gap |
| --- | --- | --- | --- |
| 1.1 Layered atmosphere | Completed for the current feasibility model | `physical_spectroscopy.py`, 24 layer run | Pollutant profiles are assumed rather than measured |
| 1.2 HITRAN extraction | Completed for the current feasibility model | 9,340 lines, HAPI validation table | Independent database and profile validation |
| 1.3 Voigt slant integration | Completed for the current feasibility model | Voigt, TIPS 2025, pressure and temperature integration | Refraction, spherical atmosphere, and measured columns |
| 1.4 PM Rayleigh model | Partially completed | Fine and coarse Rayleigh mass extinction | Particle properties and humidity response are not calibrated |
| 1.5 Native satellite columns | Partially completed | Ten ESA CCI CO and NO2 months plus domain aware column HITRAN model | Full period, profiles, averaging kernels, and validated higher atmosphere |
| 2.1 NTN link budget | Completed for the current feasibility model | Spherical Earth range, apertures, loss, noise | Real spectrum allocation and hardware validation |
| 2.2 Wideband CSI | Partially completed | Complex line of sight and pilot CSI module plus analytical observation model | Main study is simulated and has no measured channel data |
| 3.1 Spectral isolation | Completed for the current feasibility model | Gas design, background and PM nuisance projection, frequency ranking | No measured background or instrument response |
| 3.2 Estimators | Completed for the current feasibility model | Mean, validation selected Ridge, joint and mismatched WLS | Constrained nonlinear and measured data evaluation |
| 3.3 Probe design | Completed for the current feasibility model | D optimal placement, exact variance power allocation, calibration and stability sweeps | Hardware bands, fixed total resources, and correlated errors |
| 4.1 Analytical lower bound | Completed for the current feasibility model | Fisher information and CRB implementation | Bound depends on an uncalibrated residual error scenario |
| 4.2 Sensitivity | Completed for the current feasibility model | Elevation, pilots, power, probes, residual error sweeps | Atmosphere, instrument, and spectrum allocation sweeps |
| 4.3 Detection floors | Completed for the current feasibility model | Mass density, gas ppm, WHO scale comparison | Unequal averaging periods and no legal compliance validation |
| 4.4 Strong species control | Partially completed | Local H2O CRB with default and strict nuisance selections | Nonlinear held out retrieval and measured attenuation |

All proposal task groups now have a working feasibility implementation. Probe optimization improves the modeled bounds but does not change the negative reference conclusion. Native real CO and NO2 column variation also remains below the modeled floor. The local H2O bound is a positive information calculation control, not field validation.

## Task 1.1: Multi Layer Tropospheric Profile

### What was done

`build_layered_zenith_attenuation_design()` creates 24 layers from the surface to 12 km. Temperature and pressure vary by layer, water is derived from UCI median dew point, oxygen is included as background, and target pollutants use declared exponential scale heights.

### Why it was done

Line strengths, broadening, molecular number density, and path length vary with altitude. A surface template scaled over 12 km cannot represent those effects.

### Result

The physical feasibility run uses UCI median surface temperature 287.55 K, pressure 101,040 Pa, and dew point 2.9 degrees Celsius, then integrates layer contributions before applying the elevation slant factor.

### Remaining work, risks, and next step

The pollutant scale heights of 1,500 m, water scale height of 2,000 m, and PM scale height of 1,000 m are assumptions. Surface station values are not column truth. Compare profiles with radiosondes, reanalysis, chemistry transport models, or bounded profile ensembles, and validate the standard atmosphere implementation against an independent reference.

## Task 1.2: HITRAN Line Data

### What was done

HAPI acquisition provides line positions, intensities, air and self broadening, temperature exponents, pressure shifts, lower state energy, isotopologue abundance, and molecular mass for CO, O3, SO2, NO2, H2O, and O2 between 60 and 400 GHz.

### Why it was done

Real spectroscopic parameters are required to replace invented peak losses and unit normalized templates.

### Result

The processed table contains 9,340 lines: 15 CO, 1,301 O3, 6,406 SO2, 1,536 NO2, 37 H2O, and 45 O2 lines. Input SHA256 is recorded in the physical feasibility manifest.

### Remaining work, risks, and next step

The table and local calculation share HITRAN as their source, so agreement with HAPI is not independent spectroscopic validation. Confirm isotopologue policy, database version, units, and selected bands against an independent tool or published absorption cases.

## Task 1.3: Voigt Profile and Slant Integration

### What was done

The local model applies TIPS 2025 partition sums, temperature adjusted intensities, pressure broadening, pressure shifts, Doppler widths, and a Voigt profile using the complex error function. Cross sections are converted to attenuation per surface mass concentration and integrated over the layered zenith column. A plane parallel secant factor supplies elevation dependence.

### Why it was done

Normalized Lorentzian shapes cannot support concentration detection floors in physical units.

### Result

CO, O3, SO2, NO2, H2O, and O2 all pass direct HAPI comparison on the reference grid. Peak relative errors are below `6.4e-7`, and normalized active grid RMSE values are below `1.6e-7`.

### Remaining work, risks, and next step

The HAPI check covers one surface condition and the same underlying database. The secant path omits refraction and spherical atmospheric curvature. Add profile case validation at multiple pressure and temperature states and compare path attenuation with independent software and ITU recommendations.

## Task 1.4: Particulate Matter Scattering

### What was done

The model converts assumed fine and coarse particle modes into Rayleigh mass extinction using particle diameter, density, and complex refractive index assumptions, then integrates them through a PM scale height. PM10 is represented with a fixed UCI median fine fraction for its optimistic bound.

### Why it was done

PM requires a frequency dependent physical coefficient rather than an arbitrary smooth power law.

### Result

The implementation produces traceable attenuation in dB per microgram per cubic meter. It also reveals that fine and coarse spectral columns have correlation `0.999999995`. The UCI Q95 scaled joint design has singular value ratio `2.61e-7`, so joint PM separation is practically nonidentifiable.

### Remaining work, risks, and next step

Refractive index, particle density, modal diameter, size distribution, shape, and humidity growth are not calibrated. The Rayleigh approximation may fail for large particles at the highest frequencies. Obtain aerosol optical properties, use Mie or distribution integrated scattering where required, and validate against laboratory or field attenuation data. Until then, PM results remain exploratory and optimistic.

## Task 2.1: NTN Link Budget

### What was done

`link_budget.py` implements spherical Earth LEO slant range, aperture gain, free space path loss, atmospheric loss, total transmit power divided across active probes, thermal noise, receiver noise figure, and implementation loss.

### Why it was done

An arbitrary SNR label cannot connect spectroscopy to pilot observation uncertainty.

### Result

The reference link uses a 550 km satellite, 23 dBm total transmit power, 0.50 m transmit aperture, 0.30 m receive aperture, 1 MHz per probe, 6 dB receiver noise figure, and 5 dB implementation loss. At 45 degrees, slant range is 749.1 km and median SNR is 14.97 dB. Of 256 probes, 206 exceed 5 dB.

### Remaining work, risks, and next step

The 60 to 400 GHz samples are multiband feasibility probes, not one contiguous OFDM waveform. Pointing loss, polarization, regulatory masks, hardware bandwidth, Doppler tracking, phase noise, and rain or cloud loss are absent. Define realistic disjoint allocations and validate the budget with actual hardware and propagation constraints.

## Task 2.2: Wideband CSI and Noise

### What was done

`pilot_csi.py` synthesizes a complex line of sight coefficient with Friis amplitude, atmospheric attenuation, aperture or supplied gain, and geometric phase. It transmits unit pilots through circular complex Gaussian noise, averages channel estimates, and can recover attenuation relative to a clear sky channel. The feasibility script uses an analytical pilot attenuation variance with SNR and an assumed independent residual per tone term.

### Why it was done

The project needs an auditable connection between a physical link coefficient, pilot averaging, and the attenuation observation used by estimators and bounds.

### Result

Tests confirm channel amplitude and phase, aperture gains, unbiased high SNR estimation, inverse pilot count variance scaling, and clear sky attenuation recovery. The main 20,000 record benchmark simulates attenuation observations from real UCI labels and calibrated physical columns.

### Remaining work, risks, and next step

No measured CSI is used. The main CRB run assumes independent tone errors and a 0.63 dB residual standard deviation scenario borrowed from adjacent literature; it is not calibrated for this link. Integrate the complex simulator into a Monte Carlo study, include correlated calibration and phase errors, and validate against measured clear sky and polluted cases.

## Task 3.1: Spectral Isolation

### What was done

The physical design separates four gas columns from H2O and O2 background and two PM columns. CRB calculations project background and PM nuisance subspaces while jointly estimating gases. Single target Fisher contributions rank informative frequencies.

### Why it was done

Gas lines must be distinguished from smooth PM and strong atmospheric background rather than inferred only through label correlations.

### Result

The gas target design has full rank four in the reference CRB. The leading single target frequencies are near 345.33 GHz for CO, 358.67 GHz for O3, 357.33 GHz for SO2, and 396.00 GHz for NO2. PM peaks at 400 GHz in the current grid but its two modes are nearly collinear.

### Remaining work, risks, and next step

The nuisance model is deterministic and does not include instrument response or uncertain atmospheric states. Test frequency subsets under realistic allocations and include profile, line, calibration, and background covariance.

## Task 3.2: Estimator Evaluation

### What was done

The feasibility benchmark compares a training period mean, Ridge selected only on validation data, joint physical weighted least squares, oracle gas weighted least squares after removing true PM, and a deliberately mismatched gas design. It uses a chronological timestamp grouped 60%, 20%, and 20% split. The follow up audit adds target specific Ridge, training prior LMMSE, paired bootstrap uncertainty, ten receiver noise seed stability, nonlinear and multitask candidates, exact causal lags, and context plus spectrum ablations.

### Why it was done

The old random split and test selected model comparison overstated performance. A chronological validation protocol and independent mismatch case are required to judge whether the physical signal carries information.

### Result

The first Ridge grid selected alpha `10,000` at its upper boundary and was rejected as incomplete. The expanded grid selects alpha `100,000` on validation data. The originally held out test macro normalized RMSE is `0.347443` with mean R2 `-0.08293`, effectively the same as the training period mean at `0.347479` and `-0.08316`. The exact audit reproduces the Ridge value within `2.22e-16`, and the conditional paired row bootstrap interval for Ridge minus the mean includes zero. A training prior LMMSE reaches only `0.347435`. Frozen multitask ElasticNet and histogram boosting are worse than Ridge across ten receiver noise seeds. Physical WLS errors are orders of magnitude larger and about half its predictions are negative. Follow up diagnostics reuse the test period, while full period atmosphere and PM medians make the reference scenario transductive rather than strictly leakage free.

### Remaining work, risks, and next step

The deterministic 20,000 row sample retains one station at each selected timestamp, so repeated station and time stratified samples, all row evaluation, station holdout, and fresh time windows remain. Bayesian linear inference is now evaluated and does not rescue the result. Estimator complexity should not be used to hide a signal below the bound. First validate the forward and error model, then evaluate constrained inference under independent measured or mismatched data.

## Task 3.3: Tenfold RMSE Reduction Investigation

### What was done

The requested target was fixed at `0.0347443444`, one tenth of the reported Ridge metric. Spectral only estimators, receiver noise seed stability, causal context models, and an idealized global noise sensitivity were evaluated without changing the metric denominator or chronological split.

### Why it was done

A lower numerical error is useful only if it comes from additional measurement information rather than leakage, changed normalization, test tuning, removed targets, or a different inference task.

### Result

No reference spectral model reaches the target. The ten seed Ridge mean is `0.347476`; frozen multitask ElasticNet and histogram boosting reach `0.347741` and `0.347583`. A multilag forecast with true past ground measurements reaches `0.104507`, but it is not satellite only THz inversion. Context plus simulated spectrum is slightly worse than context alone.

Within the frozen exact physics, diagonal noise, training prior LMMSE sensitivity, the target threshold appears only after validation selects a global noise standard deviation multiplier of `2.4778e-5`. This is a reduction by a factor of `40,358` and corresponds to `1.629 billion` ideal independent repeated spectra. The resulting idealized numerical test point is `0.031486`. This is not a realizable sensor result or the current RMSE.

### Remaining work, risks, and next step

Resolve pilot power versus coherent CSI variance, repeat the study with better sampling and fresh time blocks, and obtain measured radiances. NASA CMR resolves a paired Aura MLS Level 1 radiance and Level 2 CO and O3 path, but granule access is blocked pending Earthdata authentication. Aura MLS would be a limb profile control rather than Beijing surface truth.

## Task 3.4: Multi Method 0.08 Information Study

### What was done

The same six targets, sample, chronological periods, and training quantile denominators were retained while separating five inference classes: same time simulated THz inversion, strictly causal forecasting, all channel station reconstruction, single channel repair, and a measured laboratory THz positive control.

### Why it was done

The revised objective accepts `0.08` or a defensible information limit. Reaching the number is useful only when the information available at inference is explicit and the result is not relabeled as a different sensing task.

### Result

The declared advanced THz result remains `0.347466`, while an optimistic context assisted unbounded power sensitivity reaches `0.239100`. The declared exact model needs at least a 5,918 fold noise standard deviation reduction to target `0.08`.

The causal v2 forecast reaches `0.095485`. Strict reconstruction with all six current query channels hidden reaches an empirical attempted family floor near `0.088890`. Single channel repair reaches `0.074855` and meets the revised objective because the other five current query channels remain available. The real measured Mendeley THz protein control is strongly monotonic but reaches `0.199270` macro on its separate leave one concentration out task.

### Remaining work, risks, and next step

Confirm the learned alternatives on a fresh city or untouched future window. Single channel repair depends on healthy colocated channels and a functioning donor network. It does not rescue atmospheric THz inversion. The measured protein control has only six or seven concentration levels and is neither gas phase nor atmospheric.

## Task 4.1: Analytical Estimation Bound

### What was done

`estimation_bounds.py` implements pilot averaged attenuation variance, weighted Fisher information, nuisance projection, CRB covariance, rank and conditioning diagnostics, one sigma floors, weighted least squares, and gas mass concentration to ppm conversion.

### Why it was done

An analytical bound tests detectability without relying on a particular learned estimator and exposes nonidentifiability before model tuning.

### Result

All four gas parameters are algebraically identifiable in the reference joint gas model, but their one sigma floors are much larger than UCI ambient concentrations and WHO health guideline comparison levels. PM joint retrieval is practically nonidentifiable.

### Remaining work, risks, and next step

The bound is conditional on a linear design, independent tone errors, and the declared residual scenario. Add correlated nuisance covariance, profile priors, instrument calibration parameters, and BCRB analysis only after those distributions are justified.

## Task 4.2: Sensitivity Analysis

### What was done

The study sweeps elevations 15, 30, 45, 60, and 80 degrees; 30, 300, and 3,000 pilots; 13, 23, and 33 dBm total transmit power; 64, 128, and 256 active probes; and residual per tone standard deviations 0, 0.10, and 0.63 dB.

### Why it was done

The feasibility conclusion must be tested against controllable link and observation variables rather than one arbitrary operating point.

### Result

No one factor scenario reaches a floor to guideline ratio of one. Lower elevation improves pollutant path sensitivity more than its SNR loss in this model. More pilots and power saturate because of the residual term. Even with that residual set to zero while other reference settings remain fixed, the CO ratio is 16.39 and the other targets are worse.

An optimistic combined stress test uses 15 degrees elevation, 3,000 pilots, zero residual per tone error, 33 dBm total power, and 256 probes. Its one sigma ratios are 0.649 for CO, 9.190 for O3, 4.350 for SO2, 88.204 for NO2, 3,538.135 for PM2.5, and 1,232.290 for PM10. Only CO crosses the health guideline concentration scale at one sigma. Its three sigma ratio is 1.948, so it is not a robust detection success. This prevents a universal impossibility conclusion, but the scenario is not a proposed deployment or compliance test.

### Remaining work, risks, and next step

Frequency windows, allocation constraints, weather, profile uncertainty, instrument response, and error correlation are not swept. Expand the study only with defensible ranges and preserve the total power accounting across probe counts.

## Task 4.3: Detection Floors and Health Guideline Scale

### What was done

The reference CRB is reported in micrograms per cubic meter for all targets and ppm for gases. Values are compared with WHO 2021 health guideline levels and their 8 h or 24 h averaging periods.

### Why it was done

Dimensionless regression scores do not show whether an instrument can resolve environmentally relevant concentration changes.

### Result

| Target | One sigma floor, micrograms per cubic meter | Floor divided by WHO guideline |
| --- | ---: | ---: |
| CO | 83,015 | 20.8 |
| O3 | 28,099 | 281.0 |
| SO2 | 4,308 | 107.7 |
| NO2 | 64,427 | 2,577.1 |
| PM2.5 | 1,513,315 | 100,887.7 |
| PM10 | 1,581,204 | 35,137.9 |

### Remaining work, risks, and next step

The bound describes one pilot burst, while WHO values use 8 h or 24 h averages. The ratios are scale comparisons, not compliance tests and not equivalent averaging period performance. Calibrate temporal averaging, drift, correlation, and field accuracy before discussing environmental compliance.

## Final Assessment

The repository now implements every proposal task at least to the level required for a transparent physical feasibility study. Optimized pollutant signatures remain too weak under the declared link and observation assumptions, the declared advanced THz estimate remains at `0.347466`, real CO and NO2 column variation remains below the modeled floor, and PM modes are practically nonidentifiable. The exact declared model requires at least a 5,918 fold modeled noise standard deviation reduction to target `0.08`.

Real ground sensor methods are useful but answer different questions. The causal forecast reaches `0.095485`, strict station reconstruction reaches `0.088890`, and single channel repair reaches `0.074855` when five current colocated channels are still healthy. The measured THz protein control confirms a real monotonic spectral response but not atmospheric retrieval.

The project is complete as a documented feasibility and signal processing study, including a compiled IEEE paper, reproducible artifacts, successful and failed attempts, and explicit claim boundaries. It is not complete as a validated atmospheric sensing system. That next phase requires paired measured channel evidence, independent atmosphere and link validation, real vertical profiles, calibrated aerosol physics, realistic spectrum allocations, and uncertainty models.
