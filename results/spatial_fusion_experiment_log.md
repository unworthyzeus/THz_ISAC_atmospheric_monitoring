# Spatial Fusion Experiment Log

## Task contract

This benchmark is contemporaneous ground sensor network reconstruction. It is
not forecasting, THz inversion, or satellite retrieval. At every query station
and timestamp, all six current query pollutant values are masked before donor
pivots and aggregates are built. Current pollutant measurements from the other
stations and exact past query measurements are allowed.

The frozen protocol uses the same real Beijing dataset, deterministic 20,000
query rows, 12,000 training rows, 4,000 validation rows, 4,000 test rows, and
training Q05 to Q95 denominators as the earlier experiments. All model and
component choices use validation labels only.

## Results that worked

The station and target specific delta Ridge model was selected on validation.
Its validation macro normalized RMSE is 0.075012 and its frozen test macro
normalized RMSE is 0.088890. The test mean R squared is 0.924539.

The strict test normalized RMSE values are:

| Target | RMSE in micrograms per cubic metre | Normalized RMSE |
| --- | ---: | ---: |
| CO | 406.688501 | 0.135563 |
| O3 | 11.619857 | 0.062810 |
| SO2 | 4.820309 | 0.071945 |
| NO2 | 10.307495 | 0.096332 |
| PM2.5 | 16.250149 | 0.074185 |
| PM10 | 24.421473 | 0.092506 |

The selected model improves on the one hour network delta transfer control by
0.005882 macro normalized RMSE. A paired bootstrap with 1,000 resamples gives a
95 percent interval from 0.004307 to 0.007724 in favour of the selected model.

Leakage checks passed. The 120,000 forbidden query target cells are missing,
the maximum donor count is 11 for a 12 station network, and replacing every
query target with the sentinel value 999,999 leaves every strict feature
unchanged. Exact one hour query lag coverage is 97.8 percent on test.

## Approaches that did not reach 0.08

| Approach | Validation macro normalized RMSE | Test macro normalized RMSE |
| --- | ---: | ---: |
| Station and target delta Ridge | 0.075012 | 0.088890 |
| One hour network delta transfer | 0.083364 | 0.094772 |
| Spatial and causal histogram boosting | 0.085068 | 0.093442 |
| Spatial and causal Ridge | 0.091167 | 0.097388 |
| Spatial and causal Extra Trees | 0.111601 | 0.114343 |
| Spatial and causal PLS | 0.116862 | 0.120312 |
| Spatial only Ridge | 0.136070 | 0.133077 |
| Other station current mean | 0.146416 | 0.143787 |
| Training period mean | 0.348932 | 0.347479 |

Even a diagnostic post hoc choice of the best attempted strict candidate for
each test target gives the same 0.088890 macro value. This is an empirical
floor for the attempted model and information family, not a theoretical lower
bound. The 0.013878 validation to test increase also indicates temporal
generalization error.

## Resolved execution failures

The first full run failed with a Pandas recursion error because a feature
bundle containing the frame itself had been attached to the frame metadata.
Passing the feature bundle explicitly removed the reference cycle.

An exploratory oversized histogram boosting run exited unsuccessfully. It was
excluded and replaced by the bounded final grid.

An exploratory full period station model produced no valid response rows due
to an indexing mismatch. It was excluded from the reported candidates.

## Information required at inference

The strict model requires the query station identity and timestamp, current
pollutants from other available ground stations, current weather, exact past
query and donor measurements at the declared lags, synchronized station clocks,
and a model fitted on historical ground sensor data. It cannot be described as
independent THz sensing because it consumes current ground sensor pollutants.

The exact machine readable record is in
`results/tables/spatial_fusion_manifest.json`.
