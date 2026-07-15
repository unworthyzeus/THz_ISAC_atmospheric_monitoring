# Single Channel Repair Experiment Log

## Task contract

This is a separate sensor repair diagnostic. When pollutant channel j is being
repaired, the current query station value of j is masked while the other five
current pollutant channels at that station are available. This is easier than
the strict all six masked reconstruction task and must not replace its result.
It is not forecasting or THz inversion.

The diagnostic preserves the real dataset, deterministic 20,000 rows,
chronological periods, and strict training Q05 to Q95 denominators. Every
configuration and target component is selected using validation labels only.

## Results that worked

The validation selected targetwise repair reaches a test macro normalized RMSE
of 0.074855 and a test mean R squared of 0.942388. It therefore reaches the
0.08 repair target. The strict all six masked result remains 0.088890.

| Target | Selected validation component | RMSE in micrograms per cubic metre | Normalized RMSE |
| --- | --- | ---: | ---: |
| CO | Global Ridge | 344.842150 | 0.114947 |
| O3 | Histogram boosting | 10.445757 | 0.056464 |
| SO2 | Station delta Ridge | 4.719280 | 0.070437 |
| NO2 | Global Ridge | 8.833749 | 0.082558 |
| PM2.5 | Global Ridge | 12.672797 | 0.057853 |
| PM10 | Global Ridge | 17.654146 | 0.066872 |

The complete repair candidates produced:

| Approach | Validation macro normalized RMSE | Test macro normalized RMSE |
| --- | ---: | ---: |
| Validation selected targetwise repair | 0.062929 | 0.074855 |
| Global Ridge | 0.066166 | 0.077448 |
| Histogram boosting | 0.069436 | 0.078562 |
| Station delta Ridge | 0.065633 | 0.080362 |
| Strict one hour delta reference | 0.083364 | 0.094772 |

The repair composite improves on the strict delta reference by 0.019917 macro
normalized RMSE. A paired bootstrap with 1,000 resamples gives a 95 percent
interval from 0.016818 to 0.023721 in favour of repair.

## Leakage and selection checks

For each of the six target designs, the repaired current target diagonal is
missing. The other five current query channels are present by contract. The
sentinel test confirms that changing repaired channel j to 999,999 cannot
change the feature design used to predict j.

All six selected components exactly equal the lowest validation error candidate
for their target. Test labels were not used for model, hyperparameter, or
component selection. The focused strict and repair suite has 8 passing tests,
and Ruff and Python compilation pass.

## Limitation and information requirement

The score of 0.074855 applies only when five current pollutant measurements are
still healthy at the query station. It requires those five values, current
donor station pollutants, current weather, exact past measurements, synchronized
station clocks, and a fitted historical model. It cannot support an all six
channels missing claim or a THz inversion claim.

The exact machine readable record is in
`results/tables/single_channel_repair_manifest.json`.
