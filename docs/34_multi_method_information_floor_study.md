<!-- review-2026-09-05 -->
# Current interpretation: September 5, 2026

RESULT: Training-only Ridge has normalized RMSE 0.3474443 versus 0.3474789 for the training-mean predictor. Its difference is −0.00003458, with a 30-day block interval [−0.00010382, 0.00003264] that crosses zero. The 7-day sensitivity interval also crosses zero; no stable spectral gain is demonstrated. See the [current revision and evidence ledger](revision_review.md).

The earlier notes below are retained as historical records. Their original conclusions, uncertainty statements, test counts, and PDF hashes are superseded where the revision says so.

<!-- end-review-banner -->

# Multi Method Information Floor Study

The complete source by source provenance, synthetic evidence boundary, hash ledger, data quality implications, and submission citation corrections are recorded in `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

In this document, `unbounded power allocation` means fixed total transmit power with no per tone allocation cap. It does not mean unlimited total transmit power, and the resulting optimizer may concentrate almost all of the fixed budget on one effective tone.

## Purpose

This note continues the normalized RMSE investigation after the practical simulated THz spectral Ridge result was fixed at `0.3474434442`. The user first requested `0.03`, then accepted `0.08` when the result is at a defensible information limit. Neither threshold changes the metric, targets, rows, or chronological split.

The acceptance rule is therefore:

1. A method may meet the numerical objective when its chronological test macro normalized RMSE is at most `0.08` under the unchanged Beijing contract.
2. A method that does not meet `0.08` may still be a useful result when the available information is stated exactly and an information limit or stable empirical plateau is demonstrated.
3. A different inference task must keep its own label. Forecasting, station network reconstruction, single channel repair, retrospective smoothing, and sensor calibration are not renamed as THz inversion.

## Frozen Beijing Metric Contract

The six targets are CO, O3, SO2, NO2, PM2.5, and PM10. For target `j`,

```text
D_j = Q95(y_train,j) - Q05(y_train,j)
NRMSE_j = RMSE_j / D_j
headline = mean_j(NRMSE_j)
```

The denominators use the training period only. The current benchmark uses 12,000 training rows, 4,000 validation rows, and 4,000 chronological test rows from the deterministic 20,000 row sample. Validation chooses model and design settings. The test block is evaluated only after a choice is frozen. Because this test block was reported in earlier work, every new result is diagnostic rather than a pristine confirmation.

## Information Classes

| Class | Information available at inference | Claim boundary |
| --- | --- | --- |
| Same time simulated THz inversion | Simulated current attenuation and a training prior | Primary physical task, but the received signal is modeled rather than measured |
| Context assisted simulated THz | Simulated current attenuation, station, calendar, and current weather | Not satellite only retrieval |
| Strict causal forecast | Station, calendar, weather, and exact past ground labels | Requires a functioning ground monitor history |
| Contemporaneous station network reconstruction | Current other station pollutant measurements, exact past query station labels, weather, and context | All six current query station pollutant values are hidden |
| Single channel repair | One current query station pollutant is hidden while the other five current channels may remain available | Repair of one failed channel, not full station reconstruction |
| Retrospective repair | Past and future neighboring measurements may be used | Offline smoothing, not real time inference |
| Independent field sensor calibration | Real sensor array responses mapped to reference analyzers | Different city, targets, units, and instrument class |

## Advanced Same Time THz Inversion

The advanced branch evaluated 216 frozen combinations of training or context priors, pilot power or coherent CSI likelihoods, equal or optimized power, multiple probe objectives, nuisance projection, and optional nonnegative posterior estimates. The rows, targets, split, and denominators were unchanged.

| Case | Test macro normalized RMSE | Interpretation |
| --- | ---: | --- |
| Existing spectral Ridge | 0.347443444151 | Current reference |
| Declared pilot power likelihood with residual error | 0.347466149724 | Slightly worse than Ridge |
| Coherent CSI sensitivity with residual retained | 0.347458420227 | Unvalidated likelihood sensitivity, still worse than Ridge |
| Coherent CSI, zero residual, equal power | 0.322726833195 | Optimistic sensitivity |
| Coherent CSI, zero residual, power bounded to four times equal allocation | 0.308334054837 | Optimistic bounded power sensitivity |
| Coherent CSI, zero residual, unbounded power | 0.277119776997 | Correlation exploiting, effectively concentrated power |
| Context assisted, zero residual, bounded power | 0.256927544406 | Current weather and station context included |
| Context assisted, zero residual, unbounded power | 0.239099664387 | Most optimistic single snapshot case |

The context only Ridge control is `0.275561` on test. Applying the predeclared nonnegative constraint to context alone gives `0.273834305758`. Under the declared residual retaining THz likelihood, the validation selected context update is `0.273833603668` on test but worsens validation by `6.65e-6`; its test gain of `7.02e-7` is unresolved. The lower `0.239100` result requires both zero residual error and unbounded power concentration and is not current hardware performance.

No residual retaining THz only design improves the existing Ridge reference. The credible conclusion remains that the declared single snapshot is prior limited.

## THz Information Required for 0.08 and 0.03

The frozen exact physics linear Gaussian model was also used as a sensitivity calculation. Validation selected the global diagonal noise scale needed to meet each requested value, and the test score was then evaluated once. The minimum information budgets found across the relevant candidate class are:

| Scenario | Target | Noise standard deviation reduction | Ideal independent repeats | Pilot symbols | Diagnostic test score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Declared training prior | 0.08 | 5,918.011 times | 35,022,859 | 1,050,685,770 | 0.075397 |
| Declared training prior | 0.03 | 63,393.396 times | 4,018,722,623 | 120,561,678,702 | 0.026465 |
| Coherent CSI with residual retained | 0.08 | 3,830.323 times | 14,671,372 | 440,141,169 | 0.075359 |
| Coherent CSI with residual retained | 0.03 | 41,111.046 times | 1,690,118,071 | 50,703,542,137 | 0.026461 |
| Zero residual optimistic design | 0.08 | 478.545 times | 229,006 | 6,870,172 | 0.074273 |
| Zero residual optimistic design | 0.03 | 6,897.653 times | 47,577,613 | 1,427,328,379 | 0.026272 |
| Context plus zero residual | 0.08 | 405.130 times | 164,130 | 4,923,911 | 0.076232 |
| Context plus zero residual | 0.03 | 6,642.562 times | 44,123,627 | 1,323,708,803 | 0.026082 |

This is a formal posterior information calculation only within the frozen linear Gaussian assumptions. The repeat interpretation requires independent stationary errors, exact forward physics, and no calibration drift. It is not an achieved receiver result.

## Stronger Strictly Causal Forecast

The second causal branch uses 189 features built only from station identity, calendar, current weather, and same station, cross target, rolling, city, and cross station pollutant observations strictly before the query time. The feature audit requires a minimum pollutant offset of one hour and mutates current and future labels to confirm that features remain identical.

Validation chooses one model per target. The frozen composite uses Extra Trees for CO, SO2, and PM10, histogram boosting for O3 and NO2, and deeper histogram boosting for PM2.5.

| Model | Validation macro normalized RMSE | Test macro normalized RMSE | Mean test R2 |
| --- | ---: | ---: | ---: |
| One hour causal base | 0.097266 | 0.104799 | 0.898520 |
| Frozen causal v2 composite | 0.084527 | 0.095484566 | 0.915126 |

The new model improves the earlier causal result but does not meet `0.08`. Test normalized RMSE by target is CO `0.140921`, O3 `0.070646`, SO2 `0.072850`, NO2 `0.100993`, PM2.5 `0.085137`, and PM10 `0.102360`. Exact one hour lag coverage is 97.8 percent on test.

The complete fixed candidate validation macros cluster from `0.08521` to `0.08569`, but the frozen composite rises to `0.09548` on the later test period. This is an empirical model plateau and distribution shift diagnostic, not a formal lower bound. The one hour innovation scale is also saved per target; the learned model approaches or improves it for five targets but is slightly worse for CO on test.

## Strict Contemporaneous Station Network Reconstruction

The real Beijing station network was used to reconstruct all six current pollutants at one query station. Every current query station pollutant was masked before donor pivots or aggregates were computed. A sentinel test changes those hidden values to an extreme number and confirms that no feature changes. Up to 11 current donor stations are available, and the exact one hour query lag has 97.8 percent coverage on test.

The validation selected station and target specific network change Ridge model gives:

| Split | Macro normalized RMSE |
| --- | ---: |
| Validation | 0.075012396 |
| Chronological test | 0.088889959 |

Its mean test R2 is `0.924539`. Test normalized RMSE by target is CO `0.135563`, O3 `0.062810`, SO2 `0.071945`, NO2 `0.096332`, PM2.5 `0.074185`, and PM10 `0.092506`. All six validation target choices independently selected the same model.

This method misses `0.08` by `0.008889959`. The validation to test gap is `0.013878` and prevents the `0.0750` validation number from being presented as achieved performance. It improves over the fixed network delta reference by `0.005882`; a paired row bootstrap gives a 95 percent interval of `[0.004307, 0.007724]` for that improvement. A post hoc per target oracle over every attempted candidate still composes the same `0.088889959` result. This supports an empirical floor near `0.089` for the attempted family, not a universal information bound. The method is also substantially better than exact one hour persistence at about `0.11646` and the earlier multilag forecast at `0.10451`.

## Real Time Single Channel Repair

A separate real Beijing experiment hides only target channel `j` at the query station. The other five current pollutant channels remain available, together with exact past values, the current donor station network, current weather, station identity, and calendar context. A sentinel leakage test changes the hidden current target by an extreme value and confirms that the feature matrix and prediction do not change.

Validation selected one candidate independently for each target. CO, NO2, PM2.5, and PM10 use global Ridge; O3 uses histogram boosting; and SO2 uses station specific delta Ridge.

| Model | Validation macro normalized RMSE | Test macro normalized RMSE | Mean test R2 |
| --- | ---: | ---: | ---: |
| Validation selected single channel composite | 0.062929 | 0.074855260 | 0.942388 |
| Global Ridge | 0.066166 | 0.077448 | 0.934580 |
| Histogram boosting | 0.069436 | 0.078562 | 0.937445 |
| Station specific delta Ridge | 0.065633 | 0.080362 | 0.936086 |
| Strict one hour network delta reference | 0.083364 | 0.094772 | 0.915890 |

The validation selected composite meets the unchanged `0.08` objective by `0.005144740`. Test normalized RMSE by target is CO `0.114947`, O3 `0.056464`, SO2 `0.070437`, NO2 `0.082558`, PM2.5 `0.057853`, and PM10 `0.066872`. CO remains the limiting target, but the unweighted six target macro passes.

This is a practical result only when one sensor channel fails while the other five current pollutant channels and the station network remain available. It is not full station reconstruction, causal forecasting from pollutant history alone, or THz inversion.

## Real UCI Field Sensor Calibration Control

An additional real field sensor control used the UCI Air Quality dataset from an Italian city. The downloaded ZIP SHA256 is:

```text
d4a64013fb385288a8a48d9d193ca7079b2e1bbddf6f8d458feb8c08ab2b8a2a
```

After excluding the `-200` missing value marker and requiring all targets, five metal oxide sensor channels, temperature, relative humidity, and absolute humidity, 6,941 complete timestamped rows remained. The split was chronological: 4,164 training, 1,388 validation, and 1,389 test rows. All reference target columns were excluded from the features.

| Model | Validation macro normalized RMSE | Test macro normalized RMSE |
| --- | ---: | ---: |
| Histogram boosting, leaf 10 | 0.197321 | 0.161160 |
| Histogram boosting, leaf 20 | 0.197769 | 0.161635 |
| Extra Trees, leaf 2 | 0.157616 | 0.146500 |
| Extra Trees, leaf 5 | 0.158081 | 0.157334 |
| Per target validation composite | not a single macro choice | 0.150830 |

The best four target macro result is `0.146500`, so this dataset does not meet `0.08`. Benzene alone reaches `0.008916` on test, but CO, NOx, and NO2 remain at `0.110476`, `0.137678`, and `0.317581` in the best Extra Trees macro model. A single easy analyte must not be used to hide the harder channels or to claim a four target success.

## Real Measured THz Positive Control

The CC BY 4.0 Mendeley dataset `10.17632/dpw4svmdr8.1` provides real THz time domain spectroscopy summary spectra for aqueous lysozyme and ovalbumin concentration series. The working anonymous listing route was:

```text
https://data.mendeley.com/public-api/datasets/dpw4svmdr8/files?folder_id=root&version=1
```

All 10 files were downloaded and their local SHA256 hashes match the hashes reported by the repository. No standard deviation pseudo replicates were created. A fixed 0.9 to 1.3 THz band was chosen without consulting concentration labels, its five frequency values were averaged, and ordinary least squares was evaluated by leaving one measured concentration level out.

| Analyte | Concentration levels | Spearman rho | Two sided p value | Leave one out Q05 to Q95 NRMSE |
| --- | ---: | ---: | ---: | ---: |
| Lysozyme | 7 | -0.892857 | 0.006807 | 0.271841 |
| Ovalbumin | 6 | -1.000000 | 0.000000 | 0.126700 |

The macro normalized RMSE is `0.199270`. The mean absolute Spearman correlation is `0.946429`, so this is a positive control for a strong monotonic relation in real measured THz spectra. It does not meet `0.08`, has only six or seven concentration levels per protein, and is not atmospheric pollution, gas phase spectroscopy, a LEO link, or the Beijing metric.

## Exploratory Retrospective Diagnostics

The following exploratory checks use the same real Beijing records and unchanged denominators but are offline information controls rather than causal estimators:

| Method | Test macro normalized RMSE |
| --- | ---: |
| Exact average of the same station values at one hour before and one hour after | 0.070752393 |
| Learned single channel repair with past and future lags plus the other five current channels | 0.066060783 |
| Learned retrospective repair with station network context | 0.066932546 |

These values cross `0.08`, but they use future information and therefore cannot be substituted for THz inversion, causal forecasting, or online station reconstruction. Their value is to show that the requested numerical accuracy is compatible with this dataset when neighboring ground truth is available on both sides of a missing observation.

## Execution Failures and Warnings

1. A first UCI field calibration sweep used 300 tree ensembles and exceeded the five minute shell limit before buffered output was returned. The process was terminated and no score from that run was accepted. The reduced explicitly timed sweep above completed in 178.2 seconds.
2. Four `RuntimeWarning: Mean of empty slice` messages occurred in the first retrospective averaging diagnostic when every requested neighbor was missing. Training means were used as fallbacks. Later reusable feature code suppresses only the expected all missing row warnings while preserving missing values and donor counts.
3. Wider symmetric interpolation using two or three hours was worse than the exact one hour neighbor average, reaching about `0.08150` and `0.09052` with spatial context. More smoothing is not automatically better during abrupt pollution changes.
4. Causal averages of lags 1, 2, and 3 reached only `0.13670`, and linear extrapolation from the last two hours reached `0.15088`.
5. A same time mean across other stations reached only about `0.14380`. Station identity and network change modeling are necessary for the stronger `0.08889` result.
6. Two older Mendeley API routes returned HTTP 401, and an initial HTML download inspection timed out. The later public listing route succeeded with HTTP 200. All three endpoint outcomes are retained in `measured_thz_control_acquisition_manifest.json` rather than deleting the failed attempts.
7. A 268 feature histogram boosting attempt over all 219,558 eligible training period rows completed CO at validation normalized RMSE `0.116633`, then failed under resource pressure while allocating the second target after 291.3 seconds. No test evaluation was performed.
8. Causal training windows restricted to the most recent 365 or 730 days were worse than full period sample training on validation.
9. The first independent artifact audit queried a human readable spatial model label rather than its stored machine identifier and raised an `IndexError` on an empty selection. The audit was corrected to `validation_selected_per_target_fusion` and then passed every numerical and PDF hash assertion.
10. One wrapper intended only to shorten LaTeX compiler output contained a malformed JavaScript regular expression and stopped before invoking the compiler. The unchanged compile command was rerun without that parser and succeeded.
11. The IEEE evidence table produces small underfull box warnings and one 0.552 point overfull box warning. Visual inspection at 150 pixels per inch confirms that the table remains inside its column and readable. The final reference page was rebalanced at reference 10.

## Interpretation

The `0.08` threshold is reached by real time single channel repair at `0.074855` and by retrospective real ground sensor repair, not by current simulated THz inversion. Strict all channel station network reconstruction approaches the threshold at `0.08889` and exhibits a clear validation to test shift. The declared THz likelihood remains at approximately `0.34746`; this is the strongest formal evidence of an information limited regime because the exact physics posterior calculation directly quantifies the missing measurement information.

For learned alternatives, the phrase information floor is used cautiously. Agreement among persistence, causal models, network change models, and validation plateaus is empirical evidence of an information plateau for the tested features and time period, not a theorem about the Bayes error.

## Reproduction Artifacts

The advanced THz branch is reproduced with:

```powershell
python scripts/run_advanced_thz_inversion.py
```

Primary artifacts are:

1. `results/tables/advanced_thz_inversion_attempts.csv`
2. `results/tables/advanced_thz_inversion_metrics.csv`
3. `results/tables/advanced_thz_inversion_probes.csv`
4. `results/tables/advanced_thz_inversion_power_optimization.csv`
5. `results/tables/advanced_thz_inversion_information_budget_screening.csv`
6. `results/tables/advanced_thz_inversion_requirements.csv`
7. `results/tables/advanced_thz_inversion_manifest.json`

The strict network branch is reproduced with:

```powershell
python scripts/run_spatial_fusion_benchmark.py
```

The single channel repair branch is reproduced with:

```powershell
python scripts/run_single_channel_repair_benchmark.py
```

Its primary artifacts are:

1. `results/tables/single_channel_repair_summary.csv`
2. `results/tables/single_channel_repair_metrics.csv`
3. `results/tables/single_channel_repair_validation.csv`
4. `results/tables/single_channel_repair_predictions.csv`
5. `results/tables/single_channel_repair_manifest.json`
6. `results/spatial_fusion_experiment_log.md`
7. `results/single_channel_repair_experiment_log.md`

The measured THz positive control is reproduced with:

```powershell
python scripts/download_measured_thz_control.py
python scripts/run_measured_thz_control.py
```

Its primary artifacts are:

1. `results/tables/measured_thz_control_acquisition_manifest.json`
2. `results/tables/measured_thz_control_manifest.json`
3. `results/tables/measured_thz_control_summary.csv`
4. `results/tables/measured_thz_control_frequency_monotonicity.csv`
5. `results/tables/measured_thz_control_predictions.csv`

The causal v2 branch is reproduced with:

```powershell
python scripts/run_causal_forecasting_v2.py
```

Its primary artifacts are:

1. `results/tables/causal_forecasting_v2_summary.csv`
2. `results/tables/causal_forecasting_v2_metrics.csv`
3. `results/tables/causal_forecasting_v2_innovation.csv`
4. `results/tables/causal_forecasting_v2_attempts.csv`
5. `results/tables/causal_forecasting_v2_failures.csv`
6. `results/tables/causal_forecasting_v2_manifest.json`
