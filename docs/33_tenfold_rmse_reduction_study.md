<!-- review-2026-09-05 -->
# Current interpretation: September 5, 2026

RESULT: Training-only Ridge has normalized RMSE 0.3474443 versus 0.3474789 for the training-mean predictor. Its difference is −0.00003458, with a 30-day block interval [−0.00010382, 0.00003264] that crosses zero. The 7-day sensitivity interval also crosses zero; no stable spectral gain is demonstrated. See the [current revision and evidence ledger](revision_review.md).

The earlier notes below are retained as historical records. Their original conclusions, uncertainty statements, test counts, and PDF hashes are superseded where the revision says so.

<!-- end-review-banner -->

# Tenfold RMSE Reduction Study

## Purpose

This note records the work started after the originally held out Ridge result reached a macro training Q05 to Q95 normalized RMSE of `0.3474434442`. The requested objective was to divide that value by ten while preserving the current metric contract.

The resulting target is:

```text
0.3474434442 / 10 = 0.0347443444
```

The target was treated as an engineering objective, not as permission to change the split, remove difficult targets, alter the normalization denominator, or use test labels during selection.

## Metric and Evidence Contract

For target `j`, the denominator is the training period fifth to ninety fifth percentile span:

```text
D_j = Q95(y_train,j) - Q05(y_train,j)
NRMSE_j = RMSE_j / D_j
headline = mean_j(NRMSE_j)
```

The headline is an unweighted mean over CO, O3, SO2, NO2, PM2.5, and PM10. The existing study uses 12,000 training rows, 4,000 validation rows, and 4,000 chronological test rows from a deterministic 20,000 row sample. The test period was untouched for the original benchmark and is reused only for diagnostic follow up comparisons.

Real evidence remains:

1. 383,585 complete UCI Beijing station hour records.
2. 9,340 processed HITRAN line records.
3. Real meteorological fields in the UCI records.

Modeled evidence remains:

1. Every sub THz attenuation observation.
2. The vertical atmosphere and pollutant profiles.
3. The LEO link, pilot error, and independent residual assumptions.

No measured, paired sub THz channel and pollutant truth dataset is used by the completed estimators.

## Exact Metric Audit

The reported Ridge metric was rebuilt from the hashed inputs. The reproduction was exact to floating point precision:

| Quantity | Value |
| --- | ---: |
| Reported Ridge mean normalized RMSE | 0.34744344415083983 |
| Reproduced Ridge mean normalized RMSE | 0.34744344415084005 |
| Absolute difference | 2.22e-16 |
| Training period mean baseline | 0.3474788618078087 |
| Ridge minus mean | -0.0000354176569686 |

No split overlap, train scaler or denominator leakage, or test based Ridge alpha selection was found. The StandardScaler and target ranges use training data only, and Ridge alpha uses validation data only. The reference atmosphere and PM composition use full period medians, so the experiment includes declared scenario lookahead and is not a strict leakage free inductive evaluation. Later diagnostic extensions also reuse the originally held out test block.

A paired bootstrap with 2,000 fixed test row resamples gave a 95 percent interval of `[-0.000150307, 0.000076415]` for Ridge minus the mean baseline. The interval includes zero. This bootstrap is conditional on the fixed model, split, and simulated noise and does not preserve temporal dependence.

Reducing every current per target RMSE by ten would imply a mean R2 of about `0.98917`. This is not a small incremental improvement over the current negative mean R2.

## Sampling Diagnostic

The deterministic sample selects every eighteenth or nineteenth eligible row after sorting by time and station. It retains exactly 20,000 unique timestamps, so it keeps one station at each selected timestamp and discards simultaneous station structure.

| Sampling case | Training mean test normalized RMSE |
| --- | ---: |
| Current deterministic 20,000 row sample | 0.347479 |
| All 365,943 eligible rows | 0.340532 |
| Twenty random 20,000 row samples, mean | 0.346271 |
| Twenty random samples, standard deviation | 0.005792 |
| Twenty random samples, range | 0.330793 to 0.353585 |

The random sample standard deviation is about 164 times the reported Ridge improvement over the mean baseline. This does not invalidate the current fixed test result, but it prevents the tiny Ridge difference from being interpreted as a stable sensing gain.

## Spectral Only Estimator Attempts

The same chronological labels, simulated spectrum, target normalization, and test period were retained. The broad exploratory search included partial least squares, multitask ElasticNet, PCA plus nearest neighbours, random Fourier features, random forests, extra trees, target specific histogram boosting, multilayer perceptrons, and per target Ridge. The reproducible stability study froze the strongest nonlinear and multitask candidates, then repeated observation generation with ten fixed receiver noise seeds.

| Spectral method | Mean test normalized RMSE | Interpretation |
| --- | ---: | --- |
| Training period mean | 0.347478862 | No spectrum |
| Current Ridge, primary seed | 0.347443444 | Reproduced reference |
| Target specific Ridge, primary seed | 0.347437733 | Negligible gain |
| Training prior LMMSE, primary seed | 0.347435328 | Negligible gain |
| Ridge, ten seed mean | 0.347475512 | Stability reference |
| Frozen multitask ElasticNet, ten seed mean | 0.347740593 | Worse than Ridge, zero wins |
| Frozen histogram boosting, ten seed mean | 0.347582559 | Worse than Ridge, one win |
| Exploratory validation composite, ten seed mean | 0.347478290 | Slightly worse than Ridge, four wins |

The single primary seed histogram boosting result of `0.347365848` initially looked better. It beat Ridge in only one of ten receiver noise seeds and had a worse ten seed mean. The exploratory composite reached `0.347322314` on the primary seed but was also slightly worse than Ridge on average and carries validation multiplicity. Neither is accepted as an improvement.

The prior whitened measurement information eigenvalues range from approximately `2.12e-17` to `7.19e-4`, all well below one. Across tones, the maximum training signal standard deviation divided by declared noise standard deviation is only `0.01117`, with a median of `0.000638`. More flexible regressors cannot reliably extract information that is not present at useful strength.

## Causal Context and Forecasting Attempts

Calendar, station, current weather, and exact past pollutant measurements were tested separately from the same time spectral inversion. Exact pollutant lags use the same station at 1, 2, 3, 6, 24, and 168 hours before the query. The lag builder rejects current or future times and records missing indicators.

| Method | Validation normalized RMSE | Test normalized RMSE | Test mean R2 |
| --- | ---: | ---: | ---: |
| Seasonal month and hour climatology | 0.345613 | 0.323164 | 0.020219 |
| Calendar and station Ridge | 0.335644 | 0.321672 | 0.078840 |
| Calendar and current weather HGB | 0.262450 | 0.266979 | 0.213293 |
| Exact one hour persistence | 0.116879 | 0.116463 | 0.877306 |
| Multilag HGB with true past labels | 0.101570 | 0.104507 | 0.898966 |

The multilag model has 69.9 percent lower error than spectral Ridge; the Ridge error is 3.32 times as large. It remains `3.01` times above the requested target.

This result changes the inference problem. The original task is current simulated THz attenuation to current concentrations. The multilag model uses past verified ground labels to predict current concentrations. It is a causal forecast only when those ground measurements arrive before inference, and it is not a satellite only THz retrieval.

A context ablation shows that the simulated spectrum does not improve the fixed test macro normalized RMSE after calendar and weather inputs:

| Inputs | Test normalized RMSE |
| --- | ---: |
| Calendar and current weather Ridge | 0.275559548 |
| Calendar, weather, and simulated spectrum | 0.275559818 |

The spectrum worsens test normalized RMSE by `2.70e-7`, which is numerical scale variation rather than physical value.

## Pilot Observation Model Sensitivity

The reference analytical variance follows pilot power averaging and retains a high SNR chi squared floor. The complex channel simulator instead coherently averages deterministic complex CSI. A high SNR delta method coherent CSI sensitivity was therefore added.

| Observation and estimator case | Test normalized RMSE |
| --- | ---: |
| Pilot power training prior LMMSE with 0.63 dB residual | 0.347435328 |
| Coherent CSI training prior LMMSE with 0.63 dB residual | 0.347382212 |
| Coherent CSI LMMSE with zero residual | 0.345600408 |

The observation model mismatch must be resolved before claiming a calibrated receiver likelihood. The more favorable coherent cases still do not approach `0.034744`.

## Idealized Noise Requirement

A training prior LMMSE model was frozen. Validation data then selected the largest common multiplier on every diagonal noise standard deviation that met the fixed target. The test value was computed once within this diagnostic at that selected multiplier, but the period had already been reported in the original benchmark.

| Quantity | Value |
| --- | ---: |
| Selected noise standard deviation multiplier | 2.47781756e-5 |
| Required standard deviation reduction | 40,358.10 times |
| Validation normalized RMSE | 0.0347443444 |
| Test normalized RMSE | 0.0314858376 |
| Ideal independent repeat equivalent | 1.629 billion |
| Equivalent at 30 pilots per repeat | 48.86 billion pilot symbols |

This is the only completed same task experiment below the numerical target, and it is a sensitivity calculation rather than a practical improvement. It scales every noise component, assumes exact forward physics, and treats all errors as independent and stationary. Calibration drift, background error, profile mismatch, and residual hardware error will not generally average this way. The target was also set after the original test headline was known, so the result is not an unbiased hardware requirement.

## Real Aura MLS Radiance Route

NASA Common Metadata Repository queries successfully resolved a real measured signal route for 1 March 2013:

1. `ML1RADG` version 005 calibrated Aura Microwave Limb Sounder filter bank radiances.
2. `ML2CO` version 005 operational CO profile retrievals.
3. `ML2O3` version 005 operational O3 profile retrievals.

The exact collection concept identifiers, granule names, dates, URLs, and reported sizes are stored in `results/tables/aura_mls_access_manifest.json`. Aura MLS is a limb sounder and therefore offers real submillimeter radiance evidence, but its upper troposphere and higher atmosphere profiles are not Beijing surface pollutant truth. Level 2 products are retrievals derived from the instrument observations and are not independent labels.

Anonymous ranged downloads returned HTTP 401, and header probes returned HTTP 403 in the reproducible Python check. NASA GES DISC requires a free Earthdata Login user account for file downloads. No credentials were present, requested, stored, or printed, and no partial Level 1 granule was retained. This branch is documented as blocked data acquisition, not as a completed retrieval experiment.

## Execution Failures and Corrections

1. The first exploratory city aggregate command selected an already selected pandas group twice and raised an `IndexError`. The command was corrected. The other station mean baseline reached only `0.142874`, so it did not solve the target.
2. A direct anonymous Aura MLS download attempt returned HTTP 401. It was replaced by a bounded CMR metadata and one byte access checker that leaves no large partial file.
3. A single histogram boosting noise realization appeared better than Ridge. The ten seed stability run rejected that apparent gain.
4. A validation selected per target composite appeared better on the primary seed. Its ten seed mean was worse than Ridge, so it remains exploratory.
5. The tenfold target was not reached by any reference spectral estimator, nonlinear model, context model, or causal forecast.
6. Within the frozen exact physics, diagonal noise, training prior LMMSE sensitivity, the numerical threshold appears only after a noise standard deviation reduction by a factor of 40,358. That point must not be reported as achieved current RMSE or sensor performance.
7. The first final audit rerun was interrupted after five seconds by an undersized command timeout. The next run completed in 17.9 seconds and reproduced all headline values.
8. Automatic paper compilation selected MiKTeX `latexmk` and failed because its Perl engine was unavailable. Explicit bundled Tectonic succeeded.
9. The `pdftoppm.cmd` wrapper pointed to a missing runtime path. The bounded direct Poppler executable rendered all nine pages.
10. `pdffonts` and `pdftotext` were absent, and a broad fallback search timed out. Python PDF parsing completed the text and embedded font checks.

## What Worked

1. The original metric was reproduced exactly from the hashed inputs.
2. Split overlap, train scaling and denominator, and validation only Ridge selection checks passed. Full period scenario medians remain disclosed lookahead.
3. Training prior LMMSE, target specific Ridge, nonlinear stability, and paired bootstrap checks now have saved, tested implementations.
4. Exact causal lag construction is tested against current and future label leakage.
5. The multilag forecast gives a meaningful auxiliary monitoring control at `0.104507`, while remaining clearly separated from THz inversion.
6. The noise requirement converts the performance target into a quantitative information gap.
7. Official NASA metadata identify a real submillimeter radiance branch suitable for future measured signal work once access is authorized.
8. The revised nine page IEEE manuscript compiles, has byte identical build and delivery copies, embeds every used font resource, and passes complete visual inspection.

## Risks and Limitations

1. Every completed pollutant attenuation estimator still uses simulated observations.
2. The same previously reported chronological test period was reused for robustness extensions.
3. The ten noise seeds vary modeled receiver noise only, not city, atmosphere, geometry, profile, or hardware.
4. The row bootstrap ignores temporal and station dependence.
5. The deterministic sample discards simultaneous station structure.
6. The auxiliary forecast depends on verified past ground measurements.
7. Aura MLS measures limb radiance profiles rather than ambient surface concentration and requires instrument specific calibration and quality handling.
8. The ideal repeat count assumes independence that is unlikely for systematic calibration and model errors.
9. Full period atmosphere and PM composition medians introduce scenario lookahead, so a future inductive benchmark must estimate them from training data only.

## Next Steps

1. Keep `0.347443` as the primary spectral Ridge result and `0.034744` as an unmet objective.
2. Repeat the spectral benchmark with all eligible rows or repeated station and time stratified samples, block bootstrap intervals, and fresh chronological windows.
3. Select one primary pilot likelihood, either power averaging or coherent complex CSI, and validate its dB variance through Monte Carlo simulation.
4. Use train only atmosphere state estimates in any future learned benchmark and preserve the existing reference state as a clearly declared scenario.
5. Obtain authorized Earthdata access, download one bounded Aura MLS day, hash and inventory the HDF5 products, then define a pressure matched profile retrieval control.
6. Evaluate the multilag forecast on a fresh external time period before treating `0.104507` as confirmatory.
7. Investigate a physically different measurement architecture, such as calibrated limb or occultation geometry, rather than adding more regressors to the same weak nadir observation.
8. Require paired measured sub THz data before making a positive ambient pollutant retrieval claim.

## Reproduction

```powershell
python scripts/run_rmse_metric_audit.py
python scripts/run_spectral_model_stability.py
python scripts/run_auxiliary_nowcasting.py
python scripts/check_aura_mls_access.py
python -m pytest tests -q
```

Primary artifacts:

1. `results/tables/rmse_metric_audit_summary.csv`
2. `results/tables/rmse_metric_audit_details.csv`
3. `results/tables/rmse_metric_audit_manifest.json`
4. `results/tables/spectral_model_stability_summary.csv`
5. `results/tables/spectral_model_stability_detailed.csv`
6. `results/tables/spectral_model_stability_manifest.json`
7. `results/tables/auxiliary_nowcasting_metrics.csv`
8. `results/tables/auxiliary_nowcasting_ablation.csv`
9. `results/tables/auxiliary_nowcasting_lag_coverage.csv`
10. `results/tables/auxiliary_nowcasting_validation.csv`
11. `results/tables/auxiliary_nowcasting_manifest.json`
12. `results/tables/aura_mls_access_manifest.json`
