# Logbook

## 2026 07 06: Initial Engineering Pipeline

### What was done

The research workspace was created, source papers were copied locally, and an initial toy CSI generator, linear regression baseline, Ridge baseline, SNR sweep, and model benchmark were implemented. A later external data benchmark combined UCI pollutant records with normalized templates derived from HITRAN line parameters.

### Why it was done

The early pipeline was needed to verify data flow, feature extraction, estimator evaluation, plot generation, and paper compilation before implementing the full physical study.

### Result

The best external data benchmark reported mean normalized RMSE `0.07793` and mean R2 `0.94523` for template projection followed by Ridge regression.

### Limitation discovered later

The generator and inverse features used the same normalized design, global label quantiles affected signal scaling, model selection used the test set, and the random split did not test temporal or station generalization. The result is therefore an engineering self consistency check, not evidence of pollutant detectability.

### Next step at that time

Replace normalized templates and invented loss scaling with calibrated spectroscopy, a declared link budget, safe data splits, estimation bounds, and detection floors.

## 2026 07 15: Scientific Audit

### What was done

The code, data, result tables, paper, and local references were audited. The audit reproduced the old headline, measured target correlations, checked the old spectral design, inspected data provenance, and identified test reuse and shared forward and inverse design.

### Why it was done

The proposal concerns physical estimation limits. A high regression score can be misleading when a simulator directly encodes the labels using a design that is also provided to the estimator.

### Result

The `0.07793` normalized RMSE and `0.94523` R2 headline was reclassified and superseded. The revised research question became whether physically calibrated pollutant attenuation is detectable under a declared NTN observation model.

### Risks and limitations

The project has no measured paired sub THz CSI and atmospheric truth. UCI values are surface station measurements rather than vertical column retrieval truth. HITRAN provides real gas spectroscopy but does not resolve aerosol physics or vertical pollutant profiles.

### Next steps

Implement a calibrated layered model, validate it against HAPI, derive the Fisher information and CRB, run declared sensitivity sweeps, and rebuild the IEEE paper around the physical result even if that result is negative.

## 2026 07 15: UCI Data Quality Audit

### What was done

The complete processed UCI table was audited for volume, keys, station coverage, target validity, PM ordering, meteorological consistency, distributions, and target correlations.

### Why it was done

Real labels can still create invalid conclusions if their missingness, physical consistency, or cross target correlations are not documented.

### Result

The processed table contains 383,585 complete case rows from 12 stations, with 91.163% retention from 420,768 source rows. It has no exact duplicates, no duplicate station hour keys, no nonpositive targets, and no dew point above temperature. There are 17,642 rows, or 4.599%, where PM10 is below PM2.5. The PM2.5 and PM10 Pearson correlation is 0.8846.

### Remaining work

Raw file missingness must still be audited by variable, station, and month. The PM ordering issue needs sensitivity analyses for exclusion, clipping, and uncertainty modeling.

### Risks and next steps

Strong real pollutant correlations can let a supervised model infer one target from another without resolving its spectral signature. Use chronological and station grouped splits, single target ablations, and physical identifiability analysis.

## 2026 07 15: Physical Spectroscopy, Link, CSI, and Bounds

### What was done

The following modules and validations were added:

1. Temperature adjusted HITRAN line intensities using TIPS 2025 partition sums.
2. Pressure broadening, pressure shift, Doppler broadening, and Voigt line shapes.
3. A 24 layer atmosphere from the surface to 12 km with pressure, temperature, water, oxygen, and assumed pollutant profiles.
4. A Rayleigh PM mass extinction model with separate fine and coarse modes.
5. A spherical Earth LEO link budget with aperture gains, free space loss, thermal noise, receiver noise figure, and implementation loss.
6. A complex line of sight channel and pilot averaged CSI simulator.
7. A heteroscedastic attenuation observation variance model, Fisher information, CRB, gas unit conversion, and weighted least squares helpers.
8. Chronological timestamp group train, validation, and test partitions.

### Why it was done

These changes remove the arbitrary unit peak gas scaling and provide a traceable path from real spectroscopy and real concentration scenarios to physical attenuation and estimation limits.

### Result

The local Voigt implementation passed comparison against HAPI for CO, O3, SO2, NO2, H2O, and O2 on the 256 point reference grid. Peak relative errors were below `6.4e-7`, and normalized active grid RMSE values were below `1.6e-7`.

The full test suite passed:

```text
32 passed
```

A targeted Ruff check of all new physical, audit, and test files passed with no findings.

### Remaining work

The layered profile still uses assumed exponential pollutant scale heights. The PM particle properties remain exploratory. The complex CSI module is tested but the main bound experiment uses its analytical pilot attenuation variance rather than Monte Carlo complex CSI samples.

### Risks and next steps

Validate layer profiles and background attenuation against independent propagation recommendations. Add instrument response, frequency calibration error, atmospheric profile mismatch, and measured clear sky reference uncertainty.

## 2026 07 15: Physical Feasibility Experiment

### What was done

`scripts/run_physical_feasibility.py` combined the full UCI concentration distribution with 9,340 processed HITRAN lines. It generated calibrated signatures, a reference link budget, Fisher bounds, WHO guideline comparisons, sensitivity sweeps, informative frequency rankings, and a chronological 20,000 record simulated attenuation benchmark.

The reference configuration uses 256 probes from 60 to 400 GHz, 24 atmospheric layers, a 550 km satellite, 23 dBm total transmit power, 0.50 m and 0.30 m apertures, 1 MHz per tone, 45 degrees elevation, 30 pilots, and an assumed independent residual error of 0.63 dB standard deviation per tone. That residual value is borrowed as a scenario from adjacent literature and is not calibrated for this link.

### Why it was done

This experiment directly tests whether the signal magnitudes supported by real spectroscopy and real concentration scenarios can overcome a declared observation uncertainty.

### Result

The UCI ninety fifth percentile peak excess attenuations at 45 degrees are 0.0319 dB for CO, 0.00484 dB for O3, 0.0152 dB for SO2, 0.00113 dB for NO2, 0.000123 dB for PM2.5, and 0.000136 dB for fixed composition PM10. All are below the assumed 0.63 dB independent residual per tone standard deviation.

The one sigma detection floor divided by the corresponding WHO 2021 health guideline is 20.8 for CO, 281.0 for O3, 107.7 for SO2, 2,577.1 for NO2, 100,887.7 for PM2.5, and 35,137.9 for PM10. These ratios compare a one burst bound with health guidelines defined over 8 h or 24 h. They are scale comparisons for this declared model and link, not compliance or equivalent averaging period results.

Fine and coarse PM signatures have correlation `0.999999995`, and the UCI ninety fifth percentile scaled joint design has a smallest to largest singular value ratio of `2.61e-7`. Joint fine and coarse PM retrieval is practically nonidentifiable.

One factor sensitivity sweeps were supplemented with an optimistic combined stress test: 15 degrees elevation, 3,000 pilots, zero residual per tone error, 33 dBm total transmit power, and 256 probes. Only CO crosses below the WHO concentration scale at a one sigma ratio of 0.649. Its three sigma ratio is 1.948, so this is not a robust detection success. O3, SO2, NO2, PM2.5, and PM10 remain above their guideline scales at one sigma by factors 9.19, 4.35, 88.20, 3,538.13, and 1,232.29. This is not a proposed deployment, and its one burst versus 8 h or 24 h comparison is not a compliance result.

### Estimator result and Ridge grid correction

The first Ridge validation grid ended at alpha `10,000`, and that boundary value was selected. This was recorded as a failed hyperparameter search because a boundary optimum does not bracket the solution.

The grid was expanded through alpha `100,000,000`. The rerun selected the interior value alpha `100,000`, with validation mean normalized RMSE `0.348912`. On the originally held out chronological test period, Ridge mean normalized RMSE was `0.347443` and mean R2 was `-0.08293`, almost identical to the training period mean baseline at `0.347479` and `-0.08316`. This confirms that regularized regression does not recover useful pollutant information from the simulated physical observations. Later diagnostic extensions reused this test period.

### Failures and corrections recorded during the work

1. A Windows `rg` command used a path wildcard that was not expanded. It returned no usable search. The search was corrected with an `rg -g` file filter.
2. Some extracted PDF searches returned exit code 1 because the selected pattern or text encoding did not match. The files were then searched with PowerShell `Select-String` and narrower literal terms.
3. An early vector diagnostic attempted to combine 512 elements with the 256 point physical grid and failed broadcasting. The diagnostic was corrected to use indices compatible with the 256 point design. The final sensitivity study uses 64, 128, and 256 active probes.
4. The initial Ridge grid ended at its upper boundary. It was expanded by four decades, and the final selected alpha is internal to the tested grid.
5. A repository wide Ruff check reported 18 `E402` findings in legacy scripts and `tests/test_synthetic_pipeline.py` because those files insert the local `src` path before imports. The new physical and audit files pass a targeted Ruff check. The legacy findings remain cleanup work and did not cause test failures.
6. A pandas result inspection exceeded its initial 10 second command timeout. The same read only inspection completed with a 60 second timeout and did not require a data or code change.

### What remains to be done

1. Obtain measured paired channel and atmospheric truth data.
2. Replace assumed pollutant vertical profiles with observations or assimilation products.
3. Calibrate aerosol size, refractive index, density, and humidity response.
4. Evaluate realistic disjoint spectrum allocations rather than treating 60 to 400 GHz as a contiguous waveform.
5. Add station holdout and repeated temporal window validation.
6. Compare the model with independent atmospheric propagation software and ITU recommendations.

### Main risk

The largest risk is interpreting an analytical bound from a transparent but assumed model as field performance. The current conclusion is conditional: under the declared model and reference link, the pollutant signatures are too weak for guideline scale sensing.

### Next steps

Use the negative result as the central IEEE paper finding, expose every assumption and input hash, and prioritize measured channel validation and uncertainty reduction instead of further optimizing regressors on the same simulated observations.

## 2026-07-15: IEEE paper compilation and visual validation

### What was done

The initial rebuilt IEEE paper was compiled with the bundled Tectonic 0.16.9 tool into a seven page PDF. Every page was rendered and inspected. The first render exposed a cramped evidence table and an unbalanced reference page. The table labels and widths were revised. This build was later superseded by the eight page follow up recorded at the end of this log.

### Result

The final PDF is `paper/build/main.pdf`, has SHA256 `2f7fe7e36d42094d73fa127a49996f9f30eb9c9801760f763597c11319ea9106`, and compiled with exit code 0. The final pass has no overfull box warning and no unresolved cross reference after the automatic rerun. The remaining font substitution and underfull box warnings were visually inspected and do not clip content.

### Failure and correction

The bundled `pdftoppm.cmd` wrapper could not find its expected Poppler runtime. Rendering was completed with the installed MiKTeX `pdftocairo.exe`. Full details are recorded in `docs/29_ieee_paper_build_and_visual_validation.md`.

### Remaining risk and next step

A venue PDF compliance check is still required before formal submission. The scientific next step remains measured channel and atmospheric profile validation.

## 2026 07 15: Probe Optimization and H2O Control

### What was done and why

The `0.347443` Ridge normalized RMSE was preserved as a failed empirical baseline. A 1,024 point HITRAN candidate grid was then used for column balanced joint gas and nuisance D optimal selection at 16 through 256 probes. Total transmit power was fixed across tone counts. Continuous power allocation was tested at 32 probes with the full pilot variance.

A separate H2O control used chronological training medians and a HITRAN central finite difference in surface dew point. Default and strict nuisance designs were evaluated so that the strict selector included the unknown background scale it needed to distinguish.

### Result

At 256 probes, optimized placement reduces the reference gas floor ratios to 11.549 for CO, 184.670 for O3, 63.935 for SO2, and 1,664.559 for NO2. These are improvements of 1.52 to 1.81 times over uniform placement but remain negative.

Optimistic CO reaches 0.352944 at one sigma and 1.058832 at three sigma. The three sigma comparison still fails even at zero residual. A finite one sigma residual threshold of 0.222792 dB was found for that fixed optimistic design.

Power allocation converged but added only 0.2 to 4.3 percent improvement over equal power on the same 32 frequencies. Frequency placement was the larger effect. Probe selection was identical for regularization values from `1e-6` through `1e-12`.

The declared H2O model gives a 0.290 degree Celsius one sigma local bound with offset, gas, and PM nuisance. Adding an unknown background scale gives 0.848 degrees when that nuisance is included during selection. These are local CRBs, not measured retrievals.

### Failures and corrections

1. The first H2O selection omitted the strict background scale objective and transferred poorly to that nuisance case. A separate strict selector reduced the floor from 2.541 to 0.848 degrees Celsius.
2. The first humidity tail diagnostic held temperature at 16 degrees Celsius while setting dew point to 21.9 degrees Celsius, which was supersaturated and unphysical. It was replaced with one and three sigma local checks plus real paired temperature and pressure state transfer.
3. The documentation initially described selection as WHO weighted. Column normalization cancels that scaling, so it was corrected to column balanced joint gas and nuisance D optimal selection.
4. Fixed power does not hold occupied bandwidth or the number of independent residual samples fixed. This resource caveat was added.

### Remaining work, risks, and next steps

Local H2O nonlinearity is below 8.2 percent at the strict three sigma displacement, but transferring the fixed reference model to real distribution tail states gives 35 to 97 percent relative error. A nonlinear model conditioned on record specific temperature and pressure is required. Probe design still omits bandpass, frequency error, correlated calibration, regulation, and hardware bandwidth. The next step is robust multi state band selection and measured attenuation.

## 2026 07 15: Real ESA CCI Column Experiment

### What was done and why

Official ESA CCI monthly CO total column and OMI tropospheric NO2 column products were selected because their 2013 to 2017 coverage overlaps the actual UCI Beijing record. Sentinel 5P was rejected because it has no temporal overlap.

Three March 2013 parser files and twenty 1 degree product months from March through December 2013 were downloaded anonymously. Every file was hashed. The nearest cell to the declared Beijing point is 39.5 degrees north and 116.5 degrees east.

A domain aware column forward model was implemented in molecules per square centimetre. CO remains labeled as a total column and NO2 as a tropospheric column. A preliminary CRB compares modeled THz floors with the real ten month Q05 to Q95 column variation and reported satellite uncertainty.

### Result

All 20 product month downloads succeeded with no missing fields. The raw files occupy 185.11 MiB. CO flags indicate both IASI and MOPITT for every month, and NO2 Level 3 QA equals one for every month.

The real column ranges are `1.361e18 molecules cm-2` for CO and `1.863e16 molecules cm-2` for NO2. With reference D optimal 256 probes, the one sigma floors are 82.886 and 5,476.265 times those ranges. Even without nuisance columns they remain 76.962 and 2,772.992 times the ranges.

In the optimistic combined case, the D optimal floors remain 2.696 times the real CO variation and 179.969 times the real NO2 variation. Native real columns therefore do not rescue the sensing result.

### Failure and correction

The first total CO run requested a 50 km atmosphere. The validated helper rejected it because its supported top is 20 km. The guard was retained. The preliminary run forces the full reported CO column into a normalized 0 to 20 km profile. It therefore omits the true upper atmosphere distribution rather than column amount, and the bias direction is unknown. Sweeping the CO scale height from 4 to 12 km changes its reference ratio from 107.1 to 74.7 but does not change the negative conclusion.

### Remaining work, risks, and next steps

The ten month series is preliminary, the products are retrievals rather than truth, and the 1 degree cell cannot represent individual stations. The CO total column needs a validated higher atmosphere and real profile data. The next step is to add averaging kernels and CAMS or another profile source, then repeat robust selection across monthly atmospheric states. Measured THz attenuation remains the decisive missing evidence.

## 2026 07 15: Final Follow Up Paper and Validation

### What was done

The optimized probe, H2O control, and native ESA CCI column results were integrated into `paper/main.tex`. The paper method now states the D optimal regularization, tone count dependent variance, fixed total power rule, WHO scaled 32 probe power objective, H2O finite difference, native column domains, and the March through December column atmosphere state.

An independent numerical and wording review checked every headline value against the generated CSV and JSON artifacts. The CO profile description was corrected to state that the complete reported total column is forced into a normalized 0 to 20 km profile. This omits the true upper atmosphere distribution rather than column amount, so the bias direction is unknown.

The H2O numerical stability artifact was regenerated through the main script. Pseudoinverse cutoffs from `1e-10` through `1e-15` change the strict one sigma floor by less than 0.2 percent.

### Why it was done

The 0.347443 Ridge normalized RMSE is poor because it is numerically almost identical to the training mean baseline and both mean R2 values are negative. A later conditional paired row bootstrap interval for their difference includes zero, but this is not an equivalence test. The paper needed to preserve that failure while testing whether physically motivated frequency design, a stronger absorber, or path integrated real targets changed the conclusion.

### Result

At that checkpoint, the IEEE PDF was eight pages. It compiled with Tectonic 0.16.9, every page was rendered at 150 pixels per inch, and no content was clipped. Its SHA256 was `51d92b4636b02583ffff8ebc35dca71a285687c1a6b0fb7599a9d35db40d6b04`. This artifact was later superseded by the nine page RMSE extension build recorded below.

The full test suite at that checkpoint passed:

```text
77 passed
```

The scoped Ruff check covering all new source modules, scripts, and tests passes. The final stable PDF copy is `output/pdf/thz_isac_pollutant_sensing_ieee.pdf`.

### Failures and corrections

1. The first H2O regeneration command used a short timeout and was stopped. The same script completed in 49.1 seconds with an appropriate timeout and wrote the numerical stability table.
2. A repository wide Ruff check reported 18 legacy `E402` import placement findings. No unrelated legacy files were rewritten; the new file scope passes.
3. Intermediate paper revisions reached nine pages with a sparse reference page. Several manual reference balancing attempts and the `balance` package worsened pagination.
4. Manual balancing was removed. Three plots that duplicated tables were omitted from the paper, while their generated artifacts remain in `results/figures/`. The final paper fits eight readable pages.
5. Independent review found that calling the 20 km CO treatment an optimistic truncation assigned an unsupported bias direction. The paper, README, task list, and real column note were corrected.
6. The same review found that frequency selection and power allocation used different objectives. The paper now distinguishes unweighted joint column balanced selection from the separate WHO scaled, nuisance projected power allocation.

### Remaining work

1. Obtain measured paired sub THz attenuation and atmospheric truth.
2. Replace fixed profiles with measured or assimilated vertical states and averaging kernels.
3. Validate full background attenuation against ITU-R P.676 or an independent propagation implementation.
4. Add regulatory band, bandpass, frequency calibration, and correlated error constraints to probe design.
5. Run a venue PDF compliance checker before submission.

### Risks and next steps

The best modeled result is still only a local Fisher bound. Optimized CO crosses its WHO comparison scale at one sigma only in a combined optimistic scenario and remains above it at three sigma. The real column result is unit consistent but uses only ten satellite months and an assumed profile. The next research effort should target robust multi state band selection and measured calibration rather than more flexible regressors on the same simulated observations.

## 2026 07 15: Tenfold RMSE Reduction Study

### What was done and why

The current Ridge macro training Q05 to Q95 normalized RMSE was audited and reproduced before testing a requested tenfold target of `0.0347443444`. The audit checked split membership, scaling, target denominators, alpha selection, sampling, atmosphere state use, observation variance, and uncertainty in the difference from the training mean.

Three reproducible experiment branches were then added:

1. Training prior LMMSE, target specific Ridge, bootstrap, sampler sensitivity, pilot likelihood sensitivity, and an idealized noise requirement.
2. Frozen nonlinear and multitask spectral estimators evaluated across ten modeled receiver noise seeds.
3. Calendar, weather, exact causal pollutant lags, persistence, and context plus spectrum ablations.

NASA CMR was also queried for a real Aura MLS radiance control using `ML1RADG`, `ML2CO`, and `ML2O3` version 005 products for 1 March 2013.

### Result

The existing `0.3474434442` result was reproduced with an absolute difference of `2.22e-16`. No split overlap, train scaler or denominator leakage, or test based Ridge selection was found. The reference atmosphere and PM composition use full period medians, however, so the protocol contains declared scenario lookahead and is not a strict leakage free inductive evaluation. Ridge improves on the training mean by only `0.0000354`, and a conditional paired row bootstrap 95 percent interval from `-0.0001503` to `0.0000764` includes zero.

Training prior LMMSE reaches `0.347435328`, while target specific Ridge reaches `0.347437733`. Across ten receiver noise seeds, Ridge averages `0.347475512`. Frozen multitask ElasticNet and histogram boosting are worse at `0.347740593` and `0.347582559`. The initially favorable single seed boosting and composite results do not survive the stability test.

The best causal auxiliary model uses exact past ground labels and reaches `0.104507088`, a 69.9 percent lower error than spectral Ridge; the Ridge error is 3.32 times as large. It remains 3.01 times above the requested target. This is a forecast with ground monitor history, not improved THz inversion. Adding the simulated spectrum to calendar and weather context changes fixed test normalized RMSE from `0.275559548` to `0.275559818`, so it does not improve this ablation.

Within the frozen exact physics, diagonal noise, training prior LMMSE sensitivity, the numerical threshold appears only after reducing every modeled observation noise standard deviation by a factor of `40,358`. The validation selected factor gives an idealized numerical test point of `0.031485838`, but its independence interpretation requires about `1.629 billion` repeated spectra. This is an information gap diagnostic, not achieved current RMSE or hardware performance.

### Failures and corrections

1. A first city aggregate pandas diagnostic selected columns twice and failed with `IndexError`. The corrected other station mean baseline reached only `0.142874`.
2. A single histogram boosting noise seed appeared better than Ridge. Nine additional fixed seeds rejected the apparent gain.
3. The exploratory per target composite improved the primary seed but was slightly worse than Ridge across ten seeds.
4. Pilot power averaging and coherent CSI averaging imply different high SNR variances. Both were retained as explicitly different sensitivity cases; neither approaches the target.
5. Anonymous Aura MLS ranged downloads returned HTTP 401 and header probes returned HTTP 403. The metadata path works, but granule access requires a free Earthdata Login. No partial Level 1 file was retained.
6. No reference spectral estimator, nonlinear model, context model, or causal forecast met the tenfold objective.
7. The first final audit rerun was interrupted after five seconds by an undersized command timeout. The next run completed in 17.9 seconds and reproduced every headline value.

### Remaining work, risks, and next steps

The deterministic sample retains only one row at each selected timestamp, and random sample baseline variation is much larger than the Ridge gain. Future evaluation should use all eligible rows or repeated station and time stratified samples, block bootstrap intervals, fresh chronological windows, and one validated pilot likelihood.

The causal forecast requires past ground truth and must remain separate from same time THz inversion. Aura MLS offers real measured submillimeter radiances but represents limb profiles, not Beijing surface pollution, and its Level 2 products are retrievals rather than independent truth. The next measured signal step requires authorized access, a bounded one day acquisition, HDF5 and calibration validation, and a pressure matched retrieval definition.

Full results, limitations, artifacts, and reproduction commands are recorded in `docs/33_tenfold_rmse_reduction_study.md`.

### Final validation and IEEE paper

All three new experiment drivers were rerun successfully. The full test suite reports 111 passed, Ruff and `py_compile` pass over all 34 new Python files, and `git diff --check` has no whitespace errors.

The IEEE manuscript now states the exact macro metric, diagnostic test reuse, full period scenario lookahead, training prior LMMSE role, forecast versus inversion boundary, and idealized sensitivity status. Bundled Tectonic produced a nine page PDF. All pages were rendered at 150 pixels per inch and inspected without clipping, overlap, blank pages, or unreadable tables. The build and delivery copies are byte identical with SHA256 `6a0478c37c28b1a2484afa2d5e8fd0303c16abbfd032537b52f9bf8a1ed58f5d`.

The automatic MiKTeX compile path failed because its Perl engine was unavailable, the `pdftoppm.cmd` wrapper pointed to a missing path, and `pdffonts` plus `pdftotext` were absent. Explicit Tectonic, the actual Poppler executable, and bounded Python PDF parsing completed the work. A broad fallback utility search also timed out and was abandoned. These operational failures are recorded in detail in `docs/29_ieee_paper_build_and_visual_validation.md`.

## 2026 07 15: Multi Method 0.08 Information Study

### Objective and contract

The numerical objective was relaxed from `0.03` to `0.08` when a defensible information limit is reached. The six Beijing targets, deterministic 20,000 row sample, chronological 60, 20, and 20 percent periods, and training Q05 to Q95 denominators remained unchanged. Every result is labeled by its inference information so that forecasting, station reconstruction, channel repair, and retrospective smoothing are not presented as THz inversion.

### Results

The advanced same time THz branch evaluated 216 frozen cases. The declared residual retaining training prior result is `0.347466150`, slightly worse than the original Ridge `0.347443444`. Zero residual equal power, bounded power, and no per tone cap sensitivities reach `0.322726833`, `0.308334055`, and `0.277119777`. Total transmit power remains fixed in every case. The most optimistic context assisted result without a per tone cap is `0.239099664`, but it concentrates the fixed power budget and is not current hardware performance.

Within the frozen exact physics posterior calculation, the minimum declared information budget that targets `0.08` needs a 5,918.011 fold noise standard deviation reduction, about 35.0 million ideal independent repeats, or 1.05 billion pilot symbols. Targeting `0.03` needs a 63,393.396 fold reduction and 4.02 billion ideal repeats. These are sensitivity calculations rather than achieved THz scores.

The strictly causal v2 forecast reaches validation `0.084527171` and test `0.095484566`, improving the earlier `0.104507088` score by 8.63 percent. It remains above `0.08` and its validation candidate cluster near `0.0852` does not transfer intact to the test period.

Strict contemporaneous station network reconstruction masks all six current query station pollutants and reaches validation `0.075012396` and test `0.088889959`. Its paired bootstrap improvement over the fixed network delta reference is `0.005882` with 95 percent interval `[0.004307, 0.007724]`. A post hoc per target oracle over the attempted family remains at the same score, supporting an empirical plateau near `0.089` rather than a universal bound.

The separate single channel repair task masks only target `j` and permits the other five current query channels. Its validation selected composite reaches test `0.074855260` with mean R2 `0.942388`, so it meets the revised `0.08` objective. CO remains the hardest target at `0.114947`; O3, SO2, NO2, PM2.5, and PM10 reach `0.056464`, `0.070437`, `0.082558`, `0.057853`, and `0.066872`. This is a ground sensor fault repair result, not THz inversion or full station recovery.

A real measured THz control was added from Mendeley DOI `10.17632/dpw4svmdr8.1`. All 10 CC BY files pass repository hash checks. A fixed label independent 0.9 to 1.3 THz feature gives Spearman correlations `-0.893` and `-1.000` for lysozyme and ovalbumin. Leave one concentration out normalized RMSE is `0.272` and `0.127`, or `0.199270` macro. This is a strong monotonic small sample control, not atmospheric pollution sensing.

The real UCI Italian field sensor calibration control retains 6,941 complete rows and excludes every reference target from its features. Its best four target macro is `0.146500`, although benzene alone reaches `0.008916`. The macro failure is retained so that one easy analyte cannot be presented as a multi target success.

### Failures and corrections

1. The first field calibration sweep exceeded the five minute shell limit before returning buffered output. A smaller timed sweep completed in 178.2 seconds.
2. Four all missing row warnings occurred in the first retrospective averaging diagnostic. Training means supplied the fallback, and reusable code now handles the expected missing rows without hiding donor counts.
3. Wider retrospective smoothing, causal lag averaging, linear extrapolation, and other station means were all worse than the final models.
4. A 268 feature all training row causal HGB run stopped under resource pressure after CO and never opened the test set.
5. Two older Mendeley API routes returned HTTP 401. The documented anonymous public listing route returned HTTP 200 and enabled verified acquisition.
6. The first independent artifact audit used the wrong display label for the strict spatial composite and raised `IndexError`. The corrected machine identifier audit passed.
7. One LaTeX output shortening wrapper had a malformed JavaScript regular expression and stopped before invoking the compiler. The compiler was rerun directly and succeeded.
8. The first 10 page PDF inherited an obsolete reference break at item 2. Removing it and triggering at item 10 balanced the final reference page.

### Final validation and paper

The full suite reports `135 passed`. Scoped Ruff and Python compilation pass for all newly added advanced THz, causal, spatial, repair, and measured THz files. The independent artifact audit confirms every headline and the delivery PDF hash. `git diff --check` passes.

Bundled Tectonic 0.16.9 compiled a 10 page IEEE manuscript. Every page was rendered at 150 pixels per inch and inspected. No clipping, overlap, blank content page, unreadable table, broken glyph, replacement character, or unembedded font resource was found. The build and delivery copies are byte identical with SHA256:

```text
38ea364c78f720603b89495b0a355530392b6b9ae7d44920604e59c6fc741674
```

The consolidated methods, exact information contracts, successes, failures, and reproduction commands are in `docs/34_multi_method_information_floor_study.md`.

## 2026 07 15: Data Provenance and Synthetic Evidence Audit

### Question

The project was reviewed to answer exactly where each dataset came from and whether any of the reported data or observations are synthetic.

### Work completed

Every headline result and every major current or legacy experiment branch was traced through its source files, download scripts, manifests, forward models, masking rules, evaluation splits, and result artifacts. External official records were reconciled with the local documentation for UCI Beijing, HITRAN2024, ESA CCI CO, ESA CCI OMI NO2, the Mendeley measured THz protein data, and the UCI Italian field sensor data.

The audit separates real measured values, measurement derived satellite retrievals, real reference parameters, semi synthetic observations, fully synthetic toy data, artificial masking, and derived outputs. It maps each headline RMSE to its exact evidence class and records the atmospheric forward assumptions, link assumptions, leakage risks, data quality limitations, hashes, Git behavior, and reproduction commands.

### Main conclusion

The central atmospheric study is semi synthetic. UCI pollutant labels and weather are real, and HITRAN line parameters are real external reference data, but all atmospheric THz attenuation observations, receiver errors, and link responses are simulated. No paired measured atmospheric sub THz CSI is used.

The `0.074855260` result is based on real UCI Beijing ground measurements with one current sensor channel artificially hidden. It requires the other five current colocated pollutant channels, donor station measurements, weather, and historical values. It is a ground sensor repair result, not THz inversion.

The Mendeley positive control is the only completed result using real measured THz spectra. It uses summary absorption spectra for seven lysozyme and six ovalbumin concentration levels and reaches macro normalized RMSE `0.199270`. It is a small aqueous protein laboratory task and cannot validate atmospheric sensing.

### Documentation corrections

The official ESA CCI CO citation should name Maya George and Cathy Clerbaux and include DOI `10.5285/6242532d87d442a3acf0171d35c02e56`. The official NO2 citation should name Isidora Anglou, I. A. Glissenaar, K. F. Boersma, and H. Eskes and clarify the difference between the current release wording and `fv1.0` filenames. The paper should also state explicitly that the scored Mendeley files contain reported means and standard deviations rather than raw replicates.

Independent review corrected four documentation issues. The forward model uses only a subset of the fields retained in the HITRAN table. Auxiliary nowcasting, spectral stability, probe optimization, H2O, and ESA column controls now have explicit provenance rows. The detailed ESA per file hash manifest is local but ignored by Git. `Unbounded power allocation` means fixed total power without a per tone cap, not unlimited total transmit power.

The Italian field calibration and retrospective repair controls are real data analyses but lack dedicated tracked reproduction scripts and result manifests. Raw and processed external data remain intentionally ignored by Git, so a fresh clone must rerun acquisition. The HITRAN processed hash fixes the analyzed table, but the download path does not pin an immutable remote server revision.

### Canonical record

The full audit is `docs/35_data_provenance_and_synthetic_evidence_audit.md`. It is linked from `README.md` and `docs/34_multi_method_information_floor_study.md`. The outdated pending language in `docs/04_data_and_sources.md` and `docs/06_experiments.md`, and the former two page paper state in `docs/26_scientific_audit_and_paper_rebuild.md`, are now labeled explicitly as historical.

### Validation and one corrected check

All cited local paths exist. The UCI and HITRAN counts, physical sample count, PM exclusion count, headline RMSE values, column month count, and current file hashes reconcile with the saved manifests. `git diff --check` passes for the edited tracked files.

The first PowerShell consistency command compared parsed JSON floating point values with exact literal equality and reported final digit differences caused by PowerShell numeric formatting. It did not identify a result mismatch. The check was corrected to use tolerance `1e-12` for metrics and exact equality for counts and hashes. The corrected audit returned `PROVENANCE_NUMERIC_AND_HASH_AUDIT_OK`.
