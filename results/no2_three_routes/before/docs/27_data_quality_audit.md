# Data Quality Audit

## Purpose

This audit assesses whether the processed UCI Beijing Multi Site Air Quality records are trustworthy enough to provide pollutant labels and meteorological context for the THz ISAC experiments.

The audit covers the processed dataset, not measured CSI. It evaluates data grain, completeness, uniqueness, domain consistency, station and temporal coverage, target distributions, and target correlations. It also identifies how data quality can affect gas and particulate matter inference.

## Dataset And Grain

| Property | Value |
| --- | --- |
| Source | UCI Beijing Multi Site Air Quality dataset |
| DOI | `10.24432/C5RK5G` |
| Processed input | `data/processed/air_quality/beijing_air_quality_clean.csv.gz` |
| Intended grain | One monitoring station and one hourly timestamp per row |
| Candidate key | `datetime`, `station` |
| Retained rows | 383,585 |
| Columns | 17 |
| Stations | 12 |
| Time start | 2013 03 01 00:00:00 |
| Time end | 2017 02 28 23:00:00 |
| Distinct retained timestamps | 34,821 |
| Target variables | CO, O3, SO2, NO2, PM2.5, and PM10 in micrograms per cubic meter |

The processed dataset is a complete case table. Rows missing any required pollutant or meteorological field were removed before this audit. The expected source volume is 420,768 station hour rows, so 383,585 retained rows correspond to **91.163% complete case retention**. The filter removed 37,183 rows, or 8.837% of the expected source volume.

## Reproducibility

Run from the repository root:

```powershell
python scripts/run_data_quality_audit.py --input data/processed/air_quality/beijing_air_quality_clean.csv.gz
```

The input SHA256 recorded in `results/tables/data_quality_manifest.json` is:

```text
39d6ceee9d66824bccf68553293a490199084299174496db51fac42bcbc543f0
```

The generated evidence files and their SHA256 values are:

| File | SHA256 |
| --- | --- |
| `results/tables/data_quality_manifest.json` | `060a795449f634835661901f0310c50913c0fb1396eeff7033800fb32ec1078d` |
| `results/tables/data_quality_station_coverage.csv` | `c614f403f68cff02199cf51aa1fd871dd30f3623f3cd472cd6b4411740345bd8` |
| `results/tables/data_quality_summary.csv` | `de67d6aa3c2da905181dbc0e3eca053484ac8da48a664ef909ba73f411d45549` |
| `results/tables/data_quality_target_correlations.csv` | `2ba2f6a8f957005e704c4ff84f1652efc57399475a28486126f41faf605f56d5` |
| `results/tables/data_quality_target_summary.csv` | `4f18e6a183b53114b50651114b0ddfef69a4f8ebf0a784d2c106149b362387d8` |

These hashes make the processed input and reported outputs inspectable. They do not prove that the raw upstream archive is unchanged because the raw archive hash is not part of this audit manifest.

## Checks Performed

| Quality dimension | Check | Result |
| --- | --- | --- |
| Volume | Processed rows against 420,768 expected source rows | 383,585 rows retained, 91.163% |
| Schema | Required timestamp, station, meteorology, and target columns | Present in the processed table |
| Uniqueness | Exact duplicate rows | 0 |
| Uniqueness | Duplicate `datetime`, `station` keys | 0 |
| Coverage | Distinct stations | 12 |
| Coverage | Distinct retained timestamps | 34,821 |
| Consistency | PM10 below PM2.5 | 17,642 rows, 4.599% |
| Consistency | Dew point above temperature | 0 rows |
| Validity | Nonpositive target values | 0 values |
| Distribution | Count, mean, standard deviation, minimum, maximum, fifth percentile, median, and ninety fifth percentile | Generated for all six targets |
| Dependence | Pearson target correlation matrix | Generated for all six targets |

## Findings

### Finding 1: PM Mass Ordering Is Inconsistent

**Severity:** High for physically constrained PM inference
**Confidence:** High

PM10 should normally include the PM2.5 mass fraction at the same station and timestamp. However, **17,642 of 383,585 rows have PM10 below PM2.5**, a rate of **4.599%**.

Likely causes include independent PM2.5 and PM10 instruments, calibration differences, measurement uncertainty, rounding, or source quality control rules. The audit evidence does not identify which cause applies to each row.

This matters because a physical two mode PM model should use:

```text
fine_mass = PM2.5
coarse_mass = max(PM10 - PM2.5, 0)
```

Without this transformation, PM2.5 mass is counted once in the fine mode and again inside total PM10. Without clipping or another documented correction, 4.599% of rows produce negative coarse mass, which is physically impossible. Clipping is defensible as a first sensitivity case, but it creates a point mass at zero and can bias the inferred coarse mode.

Recommended remediation:

1. Preserve an explicit `pm_order_violation` flag.
2. Report results for at least three policies: retain and clip coarse mass, exclude inconsistent rows, and model measurement uncertainty.
3. Never treat PM2.5 and total PM10 as two independent additive mass components.
4. Add an automated test that reports the violation count and rate without silently deleting records.

### Finding 2: Complete Case Filtering Is Material And Uneven By Station

**Severity:** Medium
**Confidence:** High for the measured rates, medium for the missingness mechanism

The complete case filter retains **91.163%** of expected source rows and removes 37,183 rows. Station retention ranges from **86.704% at Dongsi** to **94.616% at Nongzhanguan**, a spread of 7.911 percentage points.

The processed table no longer contains the missing rows, so this audit cannot determine which variables caused each removal or whether missingness clusters around pollution episodes, weather, stations, or time periods. If the missingness is not random, complete case modeling can underrepresent particular sites or environmental regimes.

Recommended remediation:

1. Audit the raw station files before complete case filtering.
2. Produce missingness rates by variable, station, month, and year.
3. Compare pollutant distributions before and after each filtering rule when labels are available.
4. Consider target specific datasets rather than requiring every target and meteorological variable to be present for every model.
5. Add station level completeness monitoring with a documented historical range rather than an arbitrary universal threshold.

### Finding 3: Strong Real Target Correlations Create An Inference Shortcut

**Severity:** High analytical risk
**Confidence:** High

The correlations are real properties of the retained UCI observations rather than generated labels. The complete Pearson matrix is:

| Target | CO | O3 | SO2 | NO2 | PM2.5 | PM10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CO | 1.0000 | -0.3152 | 0.5344 | 0.7054 | 0.7922 | 0.7039 |
| O3 | -0.3152 | 1.0000 | -0.1664 | -0.4767 | -0.1516 | -0.1148 |
| SO2 | 0.5344 | -0.1664 | 1.0000 | 0.5007 | 0.4817 | 0.4663 |
| NO2 | 0.7054 | -0.4767 | 0.5007 | 1.0000 | 0.6707 | 0.6537 |
| PM2.5 | 0.7922 | -0.1516 | 0.4817 | 0.6707 | 1.0000 | 0.8846 |
| PM10 | 0.7039 | -0.1148 | 0.4663 | 0.6537 | 0.8846 | 1.0000 |

The **PM2.5 and PM10 correlation is 0.8846**. PM2.5 also correlates with CO at 0.7922 and NO2 at 0.6707. These relationships are plausible for common pollution sources and meteorological conditions, but they complicate interpretation of estimator accuracy.

For PM inference, a supervised estimator can exploit population covariance to predict one PM target from another pollutant signature even when the fine and coarse PM spectral components are weak or nearly indistinguishable. A random row split preserves these correlations in training and test data. High held out accuracy under that split therefore does not prove that CSI independently identifies PM2.5 and coarse PM mass.

Recommended remediation:

1. Use temporal and station grouped train, validation, and test partitions.
2. Report single target and multi target models separately.
3. Run feature and label ablations that remove gas information when evaluating PM identifiability.
4. Report the condition number and correlation of the physical PM design columns.
5. Include a distribution shift test across stations and seasons.
6. Interpret correlated target prediction as contextual assistance, not direct spectral identification.

### Finding 4: Target Distributions Are Strongly Right Tailed

**Severity:** Medium
**Confidence:** Medium because the audit does not distinguish valid episodes from sensor anomalies

| Target | Fifth percentile | Median | Ninety fifth percentile | Maximum |
| --- | ---: | ---: | ---: | ---: |
| CO | 200 | 900 | 3,500 | 10,000 |
| O3 | 2 | 45 | 177 | 1,071 |
| SO2 | 2 | 7 | 59 | 500 |
| NO2 | 8 | 43 | 117 | 290 |
| PM2.5 | 6 | 55 | 242 | 844 |
| PM10 | 11 | 82 | 279 | 999 |

The maxima are substantially above the ninety fifth percentiles. These values may represent genuine severe pollution episodes, valid station differences, or sensor issues. The current evidence is insufficient to classify them.

This shape affects models and metrics. Mean squared error is sensitive to the upper tail, while scaling forward model attenuation from a global concentration percentile can make results depend on the sampled concentration distribution rather than physical absorption coefficients.

Recommended remediation:

1. Inspect upper tail records against neighboring hours and stations.
2. Report robust metrics alongside RMSE.
3. Run sensitivity with and without confirmed anomalous measurements.
4. Do not remove extreme pollution episodes solely because they are statistically rare.

### Finding 5: Keys And Basic Domain Rules Pass

**Severity:** No current failure
**Confidence:** High

The audit found zero exact duplicate rows and zero duplicate `datetime`, `station` keys. It also found zero nonpositive pollutant values and zero cases where dew point exceeds temperature.

This supports the intended station hour grain and avoids duplicate weighting in the current experiments. These checks should remain automated because a future source refresh or changed join could reintroduce duplicate keys or invalid values.

## Temporal And Station Coverage

The retained data span the full documented endpoints from 2013 03 01 through 2017 02 28. The theoretical interval contains 35,064 hourly timestamps. The processed data contain at least one complete station record for 34,821 timestamps, or 99.307% of the theoretical timestamps. There are 243 timestamps with no retained complete record at any station under this assumption.

The generated audit reports aggregate station coverage:

| Station | Complete rows | Complete case rate |
| --- | ---: | ---: |
| Dongsi | 30,402 | 86.704% |
| Shunyi | 30,587 | 87.232% |
| Wanliu | 30,737 | 87.660% |
| Dingling | 31,399 | 89.548% |
| Aotizhongxin | 31,876 | 90.908% |
| Huairou | 31,955 | 91.133% |
| Guanyuan | 32,328 | 92.197% |
| Gucheng | 32,615 | 93.016% |
| Changping | 32,774 | 93.469% |
| Wanshouxigong | 32,829 | 93.626% |
| Tiantan | 32,907 | 93.848% |
| Nongzhanguan | 33,176 | 94.616% |

The current outputs do not contain monthly or daily completeness trends. They therefore cannot show whether missing periods are isolated, seasonal, contiguous, or associated with high pollution episodes. This is an explicit audit gap rather than evidence that no temporal anomaly exists.

## Likely Causes And Impacted Uses

| Issue | Likely cause | Impacted use |
| --- | --- | --- |
| PM10 below PM2.5 | Independent instruments, calibration, uncertainty, rounding, or source quality control | Fine and coarse PM decomposition, physical attenuation synthesis, detection floor estimates |
| Uneven complete case retention | Station outages, missing pollutant channels, or missing meteorology | Station generalization, seasonal coverage, representativeness |
| Strong target correlations | Common sources, chemistry, weather, and location | Multi target regression, PM identifiability, interpretation of held out accuracy |
| Long upper tails | Severe pollution episodes, station differences, or sensor anomalies | Loss functions, normalized errors, attenuation scaling, detection floor analysis |
| No duplicate keys | Current processing preserves station hour grain | Reliable row counts and split construction |

## Recommended Automated Tests

1. Assert that `datetime`, `station` is unique.
2. Assert that the expected 12 station names remain present.
3. Assert that all required target and meteorological columns exist with numeric types after parsing.
4. Assert positive target values and dew point not above temperature.
5. Measure PM ordering violations and fail only if a documented tolerance is exceeded; always publish the count and rate.
6. Measure completeness by station and calendar month, with alerts based on historical coverage.
7. Record the raw archive hash, processed input hash, script commit, row count, and filtering rules in a tracked manifest.
8. Compare target quantiles and correlations across data refreshes to identify schema, unit, or distribution changes.
9. Validate that train, validation, and test partitions do not share the same station hour key and that grouped split rules are respected.
10. Run PM inference sensitivity for clipped, excluded, and uncertainty modeled PM ordering violations.

## Assumptions And Open Questions

1. The expected 420,768 source rows and 35,064 hours per station are treated as correct baselines.
2. Timestamps are assumed to represent consistent Beijing local hourly observations. Timezone metadata was not validated by the generated audit.
3. The processed table is already complete case filtered, so missingness causes cannot be reconstructed from this file alone.
4. Pollutant units are accepted from the processed UCI mapping and were not independently reconciled against raw source metadata in this audit.
5. The PM ordering rule assumes synchronized, colocated PM10 and PM2.5 measurements where PM10 includes the fine fraction.
6. Pearson correlations describe linear dependence in the retained observations. They do not establish causality or prove target leakage by themselves.
7. Extreme target values are not classified as errors without station and temporal corroboration.
8. This audit evaluates label and context data quality. It does not validate the physical spectroscopy model, simulated CSI, link budget, or environmental compliance claims.

## Overall Assessment

The processed dataset has a clean station hour key, broad four year coverage, valid positive targets, and no basic meteorological contradiction. It is suitable as a documented source of real pollutant scenarios.

It is not sufficient by itself to validate independent multi pollutant inference. The 8.837% complete case loss, uneven station coverage, 4.599% PM ordering violation rate, strong PM2.5 and PM10 correlation, and broader pollutant correlations must be handled explicitly in the data split, PM representation, sensitivity analysis, and interpretation of estimator results.
