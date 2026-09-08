# Physical Feasibility Results

## Purpose

This document is the canonical record of the 2026 07 15 physical feasibility study. It explains what was implemented, why it was needed, which inputs are real, which observations are simulated, what results were obtained, what failed, what remains uncertain, and what should be done next.

The study asks whether ambient CO, O3, SO2, NO2, PM2.5, and PM10 at concentrations observed in Beijing can produce resolvable excess attenuation in a sub THz LEO link.

## Executive Result

The declared reference configuration is not sensitive enough for WHO health guideline scale retrieval. Every one sigma CRB floor is above its target guideline concentration scale, from 20.8 times for CO to more than 100,000 times for PM2.5. The empirical Ridge model is numerically close to predicting the training period mean, their later conditional paired row bootstrap interval includes zero, and direct physical weighted least squares is dominated by noise.

This is a conditional negative result, not a universal impossibility theorem. An optimistic combined stress test with lower elevation, more pilots, higher power, and zero residual error puts the CO one sigma floor at 0.649 times its 24 h WHO guideline concentration. The same CO result is 1.948 times the guideline at three sigma, so it is not a robust detection success. All other targets remain above their guideline scales even at one sigma.

Follow up work preserves this baseline rather than replacing it. Column balanced D optimal placement improves the reference 256 probe gas floors by 1.52 to 1.81 times, but optimized CO remains 11.55 times its guideline concentration scale at one sigma. Optimistic optimized CO reaches 0.353 at one sigma and still misses at three sigma with a ratio of 1.059. A native ESA CCI column experiment remains negative by factors 82.9 for real CO variation and 5,476 for real NO2 variation at the reference link. See `docs/31_probe_optimization_and_h2o_positive_control.md` and `docs/32_real_satellite_column_feasibility.md`.

## What Was Done

1. Audited all 383,585 processed UCI station hour records.
2. Read 9,340 real HITRAN spectroscopic lines for the four target gases plus H2O and O2.
3. Implemented temperature adjusted intensities, pressure effects, Doppler broadening, and Voigt cross sections.
4. Integrated absorption through 24 atmospheric layers from the surface to 12 km.
5. Implemented an exploratory Rayleigh PM mass extinction model.
6. Implemented a spherical Earth LEO link budget.
7. Implemented complex line of sight channel and pilot averaged CSI building blocks.
8. Implemented an attenuation observation variance, Fisher information, CRB, gas ppm conversion, and weighted least squares.
9. Implemented chronological grouped train, validation, and test partitions.
10. Generated reference detection floors, three sigma values, informative frequencies, one factor sensitivity sweeps, an optimistic combined stress test, and an originally held out simulated observation benchmark.
11. Validated local molecular cross sections against HAPI.
12. Ran 32 repository tests and targeted Ruff checks on all new files.

## Why It Was Done

The former project headline came from a simplified generator that normalized every gas to an equal peak and an inverse feature path that used the same design. That experiment tested software self consistency but not physical detectability.

The new study starts with signal magnitudes in physical units. It asks whether the Jacobian supplied by real spectroscopy carries enough information under a declared link and pilot error model before optimizing a regressor.

## Evidence and Provenance

### Real external inputs

| Input | Use | Size | Identifier |
| --- | --- | ---: | --- |
| UCI Beijing Multi Site Air Quality | Surface pollutant scenarios and meteorology | 383,585 complete case rows | DOI `10.24432/C5RK5G` |
| HITRAN processed line table | Molecular line parameters | 9,340 lines | HAPI acquisition from HITRAN |

Input hashes:

| Input | SHA256 |
| --- | --- |
| `beijing_air_quality_clean.csv.gz` | `39d6ceee9d66824bccf68553293a490199084299174496db51fac42bcbc543f0` |
| `hitran_60_400GHz_lines.csv` | `7d063e4036da3d3e5b75128ff954bc9d80159e63d1831c4bbf75a99bfdaeded8` |

The UCI data are real surface measurements. The HITRAN parameters are real spectroscopy. Neither source contains measured sub THz CSI paired with the pollutant observations.

### Assumed model components

1. Exponential pollutant scale height: 1,500 m.
2. Water scale height: 2,000 m.
3. PM scale height: 1,000 m.
4. Fine and coarse PM particle diameter, density, and refractive index.
5. Reference link hardware and allocation parameters.
6. Independent residual error standard deviation per tone.

### Simulated components

1. Pollutant excess attenuation spectra generated from UCI labels and the physical design.
2. Pilot attenuation observations and their random error.
3. Complex line of sight CSI in the tested building block.
4. Estimator predictions made from simulated observations.

There is no field validation in this study.

## UCI Data Quality Result

The complete data audit found:

| Check | Result |
| --- | ---: |
| Source rows | 420,768 |
| Complete case rows | 383,585 |
| Complete case retention | 91.163% |
| Stations | 12 |
| Retained timestamps | 34,821 |
| Exact duplicates | 0 |
| Duplicate station hour keys | 0 |
| PM10 below PM2.5 | 17,642 rows, 4.599% |
| Dew point above temperature | 0 |
| Nonpositive target values | 0 |

The PM ordering violations are excluded before decomposing PM10 into fine and coarse mass for the 20,000 record estimator benchmark. The complete table is retained for concentration quantiles and gas calculations.

Real target correlations are large. PM2.5 and PM10 have Pearson correlation 0.8846, CO and PM2.5 have correlation 0.7922, and NO2 and PM2.5 have correlation 0.6707. These correlations can help supervised prediction without proving direct spectral identification.

## Spectroscopy and Atmosphere Method

For every HITRAN transition and atmospheric layer, the model:

1. Adjusts line intensity from the HITRAN reference temperature using TIPS 2025 partition sums and lower state energy.
2. Applies air and self pressure broadening and pressure shift.
3. Calculates Doppler broadening from molecular mass and layer temperature.
4. Evaluates a normalized Voigt profile with the complex error function.
5. Converts cross section in square centimetres per molecule to extinction for layer number density.
6. Integrates layer attenuation over the vertical column.
7. Applies a plane parallel slant factor from satellite elevation.

The UCI median surface state is 287.55 K, 101,040 Pa, and 2.9 degrees Celsius dew point. H2O and O2 are modeled as frequency dependent background rather than fixed offsets.

## Spectroscopy Validation

`scripts/validate_physical_spectroscopy.py` compares the local cross sections with HAPI for all modeled molecules at the UCI median surface condition on the 256 point reference grid.

| Molecule | HITRAN lines | Peak relative error | Normalized active grid RMSE | Passed |
| --- | ---: | ---: | ---: | --- |
| CO | 15 | `4.44e-8` | `4.68e-9` | Yes |
| O3 | 1,301 | `6.38e-7` | `1.56e-7` | Yes |
| SO2 | 6,406 | `3.61e-7` | `1.58e-7` | Yes |
| NO2 | 1,536 | `5.13e-7` | `1.25e-7` | Yes |
| H2O | 37 | `5.63e-7` | `6.69e-8` | Yes |
| O2 | 45 | `4.08e-7` | `6.74e-8` | Yes |

Both acceptance thresholds are `1e-5`. This confirms correct local reproduction of HAPI at the tested condition. It is not independent validation of HITRAN, the atmospheric profile, or field attenuation.

## PM Method and Identifiability

The PM model uses Rayleigh mass extinction for an assumed fine mode and coarse mode. Total PM10 is represented by a fixed composition combination using the UCI median PM2.5 fraction of PM10, 0.7681, for an optimistic single parameter bound.

The fine and coarse spectral columns have correlation `0.999999995`. After scaling the six target columns by UCI ninety fifth percentile concentrations, the smallest to largest singular value ratio is `2.61e-7`.

Therefore:

1. Joint fine and coarse PM retrieval is practically nonidentifiable in the current design.
2. The PM2.5 bound is an optimistic single fine mode bound.
3. The PM10 bound is an optimistic fixed composition bound.
4. Neither value proves that independent PM fractions can be estimated.

## Reference Link and Observation Model

| Parameter | Reference value |
| --- | ---: |
| Frequency probes | 256 points from 60 to 400 GHz |
| Satellite altitude | 550 km |
| Elevation | 45 degrees |
| Total transmit power | 23 dBm |
| Transmit aperture diameter | 0.50 m |
| Receive aperture diameter | 0.30 m |
| Aperture efficiencies | 0.65 |
| Bandwidth per probe | 1 MHz |
| Receiver noise figure | 6 dB |
| Receiver temperature | 290 K |
| Implementation loss | 5 dB |
| Pilot count | 30 |
| Independent residual standard deviation per tone | 0.63 dB |

The 256 samples are multiband feasibility probes. They are not a single contiguous OFDM allocation spanning 60 to 400 GHz.

The spherical Earth slant range is 749.1 km. Median SNR is 14.97 dB, its fifth percentile is minus 70.80 dB, its ninety fifth percentile is 20.64 dB, and 206 probes exceed 5 dB. Highly absorbed tones receive negligible statistical weight.

For tone `k`, the attenuation error variance is:

```text
variance_k = (10 / ln(10))^2 / Np * (1 + 1 / SNR_k)^2 + sigma_residual^2
```

The residual is assumed independent between tones. The 0.63 dB value is borrowed as a scenario from adjacent satellite ISAC literature. It is not measured or calibrated for this sub THz pollutant link and should not be interpreted as a tone correlated error.

## Estimation Bound

For linear excess attenuation design `D`, diagonal observation covariance `Sigma`, and projected nuisance columns, the gas Fisher information is the weighted Gram matrix of the nuisance orthogonalized design. The CRB is its inverse when the target design is identifiable. A one sigma floor is the square root of a covariance diagonal. The reported three sigma value is three times that floor.

The four gas target columns have rank four in the reference joint gas calculation. Algebraic rank does not imply practical sensitivity because the column magnitudes remain very small.

## Physical Signal Magnitudes

At 45 degrees and the UCI ninety fifth percentile concentration:

| Target | UCI Q95, micrograms per cubic meter | Peak excess attenuation, dB | RMS excess attenuation, dB | Peak frequency, GHz | Peak divided by 0.63 dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| CO | 3,500 | 0.031856 | 0.003223 | 345.33 | 0.0506 |
| O3 | 177 | 0.004837 | 0.001182 | 358.67 | 0.00768 |
| SO2 | 59 | 0.015169 | 0.003762 | 357.33 | 0.0241 |
| NO2 | 117 | 0.001134 | 0.000269 | 396.00 | 0.00180 |
| PM2.5 | 242 | 0.000123 | 0.0000769 | 400.00 | 0.000195 |
| PM10 | 279 | 0.000136 | 0.0000848 | 400.00 | 0.000215 |

All peak signals are below the assumed residual per tone standard deviation. The residual comparison is illustrative because the full CRB also uses pilot noise, spectral diversity, nuisance projection, and tone specific SNR.

## Reference Detection Floors

| Target | One sigma floor, micrograms per cubic meter | Three sigma floor | One sigma gas floor, ppm | One sigma ratio | Three sigma ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| CO | 83,015 | 249,046 | 71.88 | 20.754 | 62.261 |
| O3 | 28,099 | 84,297 | 14.19 | 280.991 | 842.972 |
| SO2 | 4,308 | 12,923 | 1.632 | 107.689 | 323.067 |
| NO2 | 64,427 | 193,280 | 33.95 | 2,577.065 | 7,731.194 |
| PM2.5 | 1,513,315 | 4,539,946 | Not applicable | 100,887.688 | 302,663.064 |
| PM10 | 1,581,204 | 4,743,612 | Not applicable | 35,137.868 | 105,413.603 |

The ratio denominator is the WHO 2021 concentration guideline: CO 4,000 micrograms per cubic meter over 24 h, O3 100 over 8 h, SO2 40 over 24 h, NO2 25 over 24 h, PM2.5 15 over 24 h, and PM10 45 over 24 h.

These are scale comparisons between one burst bounds and health guidelines with longer averaging periods. They are not like for like temporal metrics, legal limits, compliance verification, or evidence that a satellite estimates an 8 h or 24 h mean.

## Informative Frequencies

The strongest single target Fisher contributions occur near:

| Target | Highest ranked frequency, GHz | Background attenuation, dB | Link SNR, dB |
| --- | ---: | ---: | ---: |
| CO | 345.33 | 5.33 | 17.98 |
| O3 | 358.67 | 10.99 | 12.66 |
| SO2 | 357.33 | 9.84 | 13.77 |
| NO2 | 396.00 | 18.95 | 5.55 |
| PM2.5 | 400.00 | 12.23 | 12.36 |
| PM10 | 400.00 | 12.23 | 12.36 |

Single target ranking does not account for every joint nuisance interaction or spectrum regulation. It identifies candidate regions for a later realistic band selection study.

## One Factor Sensitivity

The one factor sweeps vary one input around the reference case:

1. Elevation: 15, 30, 45, 60, and 80 degrees.
2. Pilots: 30, 300, and 3,000.
3. Total transmit power: 13, 23, and 33 dBm.
4. Active probes: 64, 128, and 256 with total power divided fairly.
5. Independent residual standard deviation per tone: 0, 0.10, and 0.63 dB.

Key results:

1. Lower elevation improves pollutant path sensitivity more than it harms median SNR under the plane parallel model. At 15 degrees, the CO ratio is 10.36, still above one.
2. Increasing pilots to 3,000 reduces the CO ratio to 12.78 with other reference settings fixed.
3. Increasing total power to 33 dBm reduces the CO ratio to 20.41 because the residual term dominates.
4. Increasing probes from 64 to 256 improves every target through more spectral information.
5. Setting residual error to zero with other reference settings fixed reduces the CO ratio to 16.39.

No one factor case reaches a ratio below one.

## Optimistic Combined Stress Test

The combined stress test is:

| Parameter | Value |
| --- | ---: |
| Elevation | 15 degrees |
| Pilots | 3,000 |
| Independent residual error | 0 dB |
| Total transmit power | 33 dBm |
| Active probes | 256 |

This scenario combines favorable settings and removes the residual term. It is an optimistic stress test, not a proposed deployment.

| Target | One sigma floor, micrograms per cubic meter | One sigma ratio | Three sigma ratio |
| --- | ---: | ---: | ---: |
| CO | 2,597 | 0.649 | 1.948 |
| O3 | 919 | 9.190 | 27.570 |
| SO2 | 174 | 4.350 | 13.050 |
| NO2 | 2,205 | 88.204 | 264.612 |
| PM2.5 | 53,072 | 3,538.135 | 10,614.404 |
| PM10 | 55,453 | 1,232.290 | 3,696.869 |

Only CO falls below its guideline concentration scale at one sigma, but it rises above the scale at three sigma. This rules out a universal statement that no parameter combination can ever approach a guideline scale. It does not establish a robust CO detector because zero residual error, 3,000 pilots, favorable geometry, and unequal temporal averaging are optimistic.

## Chronological Estimator Benchmark

The benchmark uses 20,000 deterministic records sampled after excluding PM ordering violations. Records are sorted by timestamp and station, then divided into 12,000 training, 4,000 validation, and 4,000 rows in a test period that was untouched for the original benchmark. Later robustness diagnostics reuse that period. Training ends at `2015-09-10 01:00:00`, and validation ends at `2016-06-03 04:00:00`. The fixed forward atmosphere and PM composition use full period medians and are therefore declared transductive scenario choices rather than training only estimates.

The simulated observation is a linear combination of calibrated gas and PM columns plus random attenuation error from the reference variance model. The labels are real UCI values; the attenuation observations are simulated.

### Ridge grid failure and correction

The first alpha grid ended at `10,000`, which was selected at the boundary. That search failed to bracket the regularization optimum and was not accepted as final.

The expanded grid runs from `0.01` to `100,000,000`. It selects alpha `100,000` on validation data with mean normalized RMSE `0.348912`. The test set is used only after selection.

### Test result

| Model | Targets | Mean normalized RMSE | Mean R2 | Mean negative prediction rate |
| --- | ---: | ---: | ---: | ---: |
| Training period mean | 6 | 0.347479 | -0.08316 | 0 |
| Ridge selected on validation | 6 | 0.347443 | -0.08293 | 0 |
| Oracle joint physical WLS | 6 | 5,753,644.9 | approximately minus `9.56e14` | 0.5006 |
| Oracle gas WLS with true PM removed | 4 | 157.696 | approximately minus `4.40e5` | 0.5009 |
| Mismatched gas WLS with true PM removed | 4 | 207.575 | approximately minus `7.62e5` | 0.5008 |

Ridge improves mean normalized RMSE over the mean baseline by only `0.0000354`, and both mean R2 values are negative. Strong regularization shrinks predictions toward target means. It does not recover useful pollutant information from the reference simulated physical observations.

Direct WLS is unbiased only in an ideal linear sense. Its variance is enormous at these signal levels, producing negative estimates in about half of cases. A nonnegative constraint would remove invalid signs but cannot create information missing from the observation.

## Superseded Self Consistency Benchmark

The former headline was mean normalized RMSE `0.07793` and mean R2 `0.94523` from shared template projection and Ridge regression.

It remains useful as a software regression check because it confirms that the old simulator can encode and approximately decode a label vector. It is not used as main scientific evidence because:

1. Gas templates were normalized to equal peak loss.
2. Global label quantiles influenced signal scaling and metric normalization.
3. The generator and inverse features shared the same design.
4. The random split did not test temporal or station shift.
5. Test data were used in model and alpha selection.
6. PM prediction could exploit real target correlations despite weak PM identifiability.

## What Worked

1. Full UCI data audit and manifest generation.
2. HITRAN data loading and unit conversion.
3. Layered Voigt absorption with HAPI agreement.
4. LEO link and complex pilot CSI unit tests.
5. Fisher and CRB calculations with rank diagnostics.
6. Chronological disjoint splits.
7. Reference and sensitivity artifact generation.
8. Expanded validation selected Ridge grid.
9. Full test suite: 32 passing tests.
10. Targeted Ruff check: no findings in new files.

## What Failed or Was Corrected

1. The old high score failed the scientific audit as a physical sensing claim and was superseded.
2. The first Ridge grid selected its upper boundary and was expanded by four decades.
3. An early 512 element vector diagnostic failed against the 256 point design and was corrected. The final probe sweep uses 64, 128, and 256 points.
4. A Windows `rg` path wildcard did not expand and was replaced by an `rg -g` file filter.
5. Some PDF text searches returned no match because of pattern or encoding issues and were repeated with literal PowerShell searches.
6. A repository wide Ruff check still reports 18 legacy `E402` import placement findings. New files pass targeted checking, and all tests pass.

## Risks and Limitations

1. No paired measured sub THz CSI and pollutant truth are available.
2. UCI surface measurements are not vertical column densities.
3. Pollutant, water, and PM vertical profiles are assumed.
4. PM optical properties and size distributions are exploratory.
5. The 0.63 dB independent residual value is borrowed and uncalibrated for this link.
6. Independent tone residuals may be optimistic if real calibration errors are correlated.
7. The frequency grid is not a regulatory or hardware feasible contiguous allocation.
8. Plane parallel slant scaling omits atmospheric curvature and refraction.
9. Rain, cloud, pointing, polarization, oscillator, phase noise, and instrument response are absent.
10. HAPI comparison is not independent validation of HITRAN.
11. WHO comparisons use different averaging periods and cannot establish compliance.
12. PM single parameter floors are optimistic because joint PM modes are nearly collinear.
13. The optimistic combined scenario sets residual error to zero and should not be read as an achievable operating point.

## What Remains to Be Done

1. Acquire or create a field campaign with paired sub THz channel estimates, clear sky references, meteorology, vertical profiles, and independent pollutant instruments.
2. Validate atmospheric background and slant integration against independent software and ITU recommendations.
3. Replace fixed scale heights with measured or probabilistic profiles.
4. Calibrate PM refractive index, size distribution, density, shape, and humidity growth.
5. Model instrument bandpass, frequency calibration, channel drift, correlated residuals, and clear sky reference uncertainty.
6. Select realistic disjoint sensing bands with total power, bandwidth, hardware, and regulation constraints.
7. Repeat temporal tests across multiple windows and add station holdout and external region evaluation.
8. Add constrained and Bayesian estimators after physical uncertainty distributions are justified.
9. Derive a BCRB only when priors are traceable to data.
10. Reassess whether PM should be one total mass parameter, a fixed composition parameter, or removed from the retrieval claim.

## Next Steps

1. Use the reference negative result and optimistic CO boundary case as the central IEEE paper findings.
2. State real inputs, simulated observations, and assumptions in the abstract and every result interpretation.
3. Preserve the exact configuration manifest, input hashes, tables, and figures.
4. Prioritize measured validation and residual calibration before further regressor optimization.
5. Treat any future positive claim as requiring independent channel evidence, robust three sigma or probability of detection analysis, matched averaging periods, and external validation.

## Reproduction Commands

```powershell
python scripts/run_data_quality_audit.py
python scripts/validate_physical_spectroscopy.py
python scripts/run_physical_feasibility.py
python -m pytest tests -q
```

Primary artifacts:

1. `results/tables/data_quality_manifest.json`
2. `results/tables/physical_spectroscopy_hapi_validation.csv`
3. `results/tables/physical_feasibility_config.json`
4. `results/tables/physical_signature_summary.csv`
5. `results/tables/physical_informative_frequencies.csv`
6. `results/tables/physical_detection_floors.csv`
7. `results/tables/physical_sensitivity.csv`
8. `results/tables/physical_ridge_validation.csv`
9. `results/tables/physical_estimator_metrics.csv`
10. `results/figures/physical_signatures.png`
11. `results/figures/physical_detection_floor_vs_guideline.png`
12. `results/figures/physical_sensitivity.png`
13. `results/figures/physical_estimator_benchmark.png`

## Final Interpretation

Real spectroscopy and real concentration scenarios do not rescue the reference link from weak observability. The dominant result is a large gap between physical pollutant signatures and the declared observation error. The optimistic combined case shows that CO can approach its health guideline concentration scale at one sigma only when several favorable assumptions are combined, but it fails the three sigma comparison and does not match the 24 h averaging period.

The scientifically defensible conclusion is therefore bounded and conditional: the reference sub THz NTN observation model is inadequate for guideline scale retrieval of the six pollutants, while a highly optimistic CO case deserves targeted future measurement rather than a positive deployment claim.
