# Real Satellite Column Feasibility

## Purpose

This note records the first feasibility experiment that uses real satellite gas column retrievals in their native units. It explains what was downloaded, why column data are better matched to a satellite path than surface concentration, what worked, what failed, what the preliminary result means, and what remains to be done.

The experiment addresses one of the largest limitations in the earlier study: UCI stations report local surface concentration, while a satellite link observes path integrated attenuation.

## Data Acquisition

### What was done

`scripts/download_column_smoke_data.py` first downloaded and inventoried three March 2013 ESA CCI files:

1. Merged IASI and MOPITT 1 degree total CO column.
2. Coarse OMI tropospheric NO2 parser test file.
3. OMI 1 degree tropospheric NO2 science grid.

All three anonymous downloads succeeded. Their byte sizes and SHA256 hashes are stored in `data/processed/column_smoke_data_manifest.json`.

`scripts/download_beijing_column_series.py` then downloaded the 1 degree CO and NO2 products for March through December 2013. It extracted the independently nearest cell to the declared Beijing reference point at 39.9 degrees north and 116.4 degrees east.

### Acquisition result

| Check | Result |
| --- | ---: |
| Months | 10 |
| Product month files expected | 20 |
| Product month files retrieved | 20 |
| Failures | 0 |
| Raw bytes | 194,098,326 |
| Raw size | 185.11 MiB |
| Extracted grid centre | 39.5 degrees north, 116.5 degrees east |
| Missing extracted fields | 0 |
| CO flag | 3 for all months, IASI and MOPITT |
| NO2 Level 3 QA | 1 for all months |

Every raw file has an individual SHA256 in `data/processed/columns/beijing_column_series_2013_manifest.json`. A repeat run resumed without downloading any file again.

### Source semantics

The CO field is the monthly daytime merged IASI and MOPITT total column in molecules per square centimetre. The NO2 field is the monthly OMI tropospheric vertical column in the same unit.

These are satellite retrieval products with uncertainties, sampling effects, and prior dependence. They are not direct truth, station measurements, or THz channel measurements.

## Real Column Distribution

The ten monthly retrievals give:

| Target | Domain | Median, molecules per square centimetre | Q05 to Q95 range | Median reported uncertainty | Uncertainty / range |
| --- | --- | ---: | ---: | ---: | ---: |
| CO | Total column | `3.317e18` | `1.361e18` | `1.411e17` | 0.1036 |
| NO2 | Tropospheric column | `1.304e16` | `1.863e16` | `1.657e15` | 0.0890 |

The sample is preliminary and too short for a climatology. The range is used only as the observed variation scale for this ten month experiment.

## Domain Aware Forward Model

### What was implemented

`src/thz_isac/column_spectroscopy.py` keeps the satellite columns in molecules per square centimetre. It does not convert them to surface mass concentration.

For each gas, a declared normalized vertical profile allocates the full column among pressure and temperature layers. HITRAN cross sections are evaluated per layer and integrated to produce dB per molecule per square centimetre. CO remains labeled as a total column and NO2 as a tropospheric column. Passing a column with the wrong domain raises an error.

The aggregate coefficient and an explicit layer optical depth calculation agree in unit tests. Eleven focused column tests pass.

### Declared profiles

The preliminary reference uses:

1. A 0 to 20 km atmosphere with 40 layers.
2. An 8 km exponential scale height for the CO total column.
3. A 1.5 km exponential scale height for the NO2 tropospheric column.
4. March through December 2013 UCI medians of 290.85 K, 100.75 kPa, and 6.9 degrees Celsius dew point for the background state.

The entire reported CO total column is forced into a normalized 0 to 20 km reference profile. The code does not discard column amount, but it cannot represent the true upper atmosphere distribution. The direction of the resulting spectral bias is unknown. The 4, 8, and 12 km scale height sweep tests this problem only partially.

## Failed 50 km Attempt

The first run requested a 50 km atmosphere for total CO. It failed at the existing physical model guard:

```text
ValueError: Top altitude must be in the interval (0, 20000] meters.
```

This guard was not bypassed. The validated atmosphere helper is a troposphere and lower stratosphere approximation, so silently extending it would create unsupported physics. The final preliminary run uses 20 km and records the forced CO profile domain explicitly.

## Feasibility Method

The target design contains CO total column and NO2 tropospheric column coefficients. Declared nuisance columns are:

1. Additive offset.
2. Full atmospheric background scale.
3. Surface O3 profile.
4. Surface SO2 profile.
5. Fine PM mode.
6. Coarse PM mode.

The experiment compares uniform and D optimal probes at 64, 128, and 256 active frequencies from a 512 point 60 to 400 GHz candidate grid. Total transmit power is fixed for every tone count.

The main metric is the one sigma column CRB divided by the real ten month Q05 to Q95 range. It is also divided by the median reported satellite retrieval uncertainty. No WHO surface concentration comparison is used for column units.

## Physical Signal Magnitudes

Across the real ten month Q05 to Q95 column range:

| Target | Peak zenith attenuation, dB | RMS zenith attenuation, dB | Peak frequency, GHz |
| --- | ---: | ---: | ---: |
| CO total column | 0.005973 | 0.000440 | 346.106 |
| NO2 tropospheric column | 0.0000654 | 0.0000152 | 395.342 |

The real column variation produces very small signals relative to the reference 0.63 dB residual scenario.

## Reference Result

At 45 degrees elevation, 23 dBm total power, 30 pilots, and 0.63 dB independent residual error, the 256 probe results are:

| Target | Uniform floor / real range | D optimal floor / real range | D optimal three sigma / range | D optimal floor / retrieval uncertainty |
| --- | ---: | ---: | ---: | ---: |
| CO total column | 120.536 | 82.886 | 248.659 | 799.701 |
| NO2 tropospheric column | 7,243.856 | 5,476.265 | 16,428.796 | 61,559.063 |

Even the ideal calculation without nuisance columns remains far above the real variation: 76.962 times for CO and 2,772.992 times for NO2 with D optimal 256 probes.

The result is therefore not caused only by the nuisance basis. The signal variation itself is too weak under the reference observation model.

## Optimistic Combined Result

At 15 degrees elevation, 33 dBm, 3,000 pilots, and zero residual error:

| Target | Uniform floor / real range | D optimal floor / real range | D optimal three sigma / range | D optimal floor / retrieval uncertainty |
| --- | ---: | ---: | ---: | ---: |
| CO total column | 3.975 | 2.696 | 8.087 | 26.008 |
| NO2 tropospheric column | 245.229 | 179.969 | 539.907 | 2,023.044 |

Neither real column target reaches the observed variation scale, even at one sigma. This is stricter than the earlier optimistic surface concentration CO result because the real monthly total column variation is small relative to the required THz floor.

## CO Profile Sensitivity

The reference D optimal 256 frequencies were held fixed while the assumed CO scale height changed:

| CO scale height, m | CO floor / real range | NO2 floor / real range |
| ---: | ---: | ---: |
| 4,000 | 107.122 | 5,488.610 |
| 8,000 | 82.886 | 5,476.265 |
| 12,000 | 74.745 | 5,471.651 |

The CO conclusion changes materially with the assumed vertical profile but remains negative by at least 74.7 times in the tested reference cases. NO2 is nearly unchanged because its profile is held fixed.

## What Worked

1. Anonymous official ESA CCI acquisition completed for 20 of 20 product months.
2. All raw files have hashes and resumable local paths.
3. The CO and NO2 products use the same 1 degree grid centre.
4. Quality, uncertainty, count, and cloud fields were retained.
5. Native column units and different vertical domains remained explicit.
6. Aggregate and direct layer attenuation calculations passed unit tests.
7. Both targets remained algebraically identifiable in every reported CRB.
8. D optimal placement improved both target floors.

## What Failed or Remained Negative

1. The unsupported 50 km atmosphere request failed and was replaced by an explicit normalized 0 to 20 km CO profile with unknown bias direction.
2. Real column targets did not rescue the sensing claim.
3. Reference D optimal CO remains 82.9 times the real monthly variation scale.
4. Reference D optimal NO2 remains more than 5,400 times the real variation scale.
5. The optimistic combined case still misses CO by 2.70 times and NO2 by 180 times at one sigma.
6. Satellite retrieval uncertainty is much smaller than the modeled THz retrieval floor.

## Interpretation

Using real path integrated targets removes the surface to column unit mismatch, but it does not make the declared link sensitive enough. The result is a unit consistent negative stress test for CO and NO2 under the declared profiles.

This is still not field validation. The target columns are real retrievals, while the THz observations are modeled. The ten month sample and assumed vertical profiles prevent a broad impossibility statement.

## Risks and Limitations

1. Only ten monthly values are used.
2. A 1 degree satellite cell cannot represent individual urban stations.
3. Satellite products contain retrieval uncertainty, averaging kernels, cloud sampling, and prior dependence.
4. CO is a total column but the forward model stops at 20 km.
5. Both vertical profiles are assumed.
6. The above tropopause atmosphere is simplified.
7. The nuisance covariance remains frequency independent after normalization.
8. The independent residual error assumption can be optimistic.
9. No measured THz attenuation or instrument bandpass is used.

## What Remains to Be Done

1. Extend the column series through the complete 2013 to 2017 UCI period or use a justified representative sample plan.
2. Add averaging kernels and retrieval quality filters to the column interpretation.
3. Use CAMS or another profile source to replace exponential vertical shapes.
4. Implement a validated higher atmosphere model before interpreting a full CO total column.
5. Evaluate robust probe selection across monthly temperature, humidity, and profile states.
6. Add correlated calibration errors and instrument frequency response.
7. Acquire measured sub THz attenuation for any positive sensing validation.

## Next Steps

1. Add this result to the IEEE paper as the real column stress test.
2. Keep the central conclusion negative and distinguish real targets from modeled observations.
3. Treat the forced 0 to 20 km CO profile as preliminary and do not assign a known bias direction.
4. Prioritize profile data and hardware calibration over more complex regressors.

## Reproduction

```powershell
python scripts/download_column_smoke_data.py
python scripts/download_beijing_column_series.py
python scripts/run_real_column_feasibility.py
python -m pytest tests -q
```

Primary artifacts:

1. `data/processed/column_smoke_data_manifest.json`
2. `data/processed/columns/beijing_column_series_2013.csv`
3. `data/processed/columns/beijing_column_series_2013_manifest.json`
4. `results/tables/real_column_statistics.csv`
5. `results/tables/real_column_signatures.csv`
6. `results/tables/real_column_detection_floors.csv`
7. `results/tables/real_column_profile_sensitivity.csv`
8. `results/tables/real_column_selected_frequencies.csv`
9. `results/tables/real_column_feasibility_manifest.json`
10. `results/figures/real_column_detection_floor.png`
