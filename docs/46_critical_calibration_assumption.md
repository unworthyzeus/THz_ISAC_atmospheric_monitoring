# Critical assumption: zero residual calibration error

Recorded September 27, 2026, at the user's request. This assumption must accompany favorable recall and detection limit claims in future summaries, figures, abstracts and presentations.

**The strongest reported results assume zero residual calibration error after correction. That accuracy has not been established by receiver measurements. These results are ideal calibrated benchmarks, not demonstrated field performance.**

## What zero means

Receiver thermal noise and finite reference uncertainty remain in the model. The zero assumption sets the additional differential spectral calibration residual to zero after reference subtraction and nuisance fitting. In the covariance model, `C = diag(Vsample + Vreference) + sigma_cal² K`, it sets `sigma_cal = 0`; it does not set `C = 0`.

Potential residual sources include changes in transmitter power, receiver gain, antenna pointing and instrumental frequency response. Modeled gain/background nuisance components are fitted. An arbitrary remaining spectral error is not automatically removed by that fit. Weather mismatch is an additional issue and is not represented by every calibration scenario.

The ideal case was evaluated to isolate the information available in the payload and compare M2M4 with likelihood information bounds. It does not demonstrate that a real receiver can maintain the required calibration stability.

## Quantitative effect retained with the results

These are **predicted recall** values from the same saved sensitivity study: acetonitrile enhancement of 1 µg/m³, standard atmosphere, 45° elevation, nominal receiver input noise, M2M4, 10 seconds reference plus 10 seconds sample, and the fixed 1% family false alarm budget across six outputs.

| Differential calibration residual standard deviation | Predicted recall | Predicted 95% power detection limit |
|---|---:|---:|
| 0 dB | 93.84% | 1.023 µg/m³ |
| 0.0001 dB | 92.55% | 1.046 µg/m³ |
| 0.001 dB | 25.17% | 2.021 µg/m³ |

A positive 0.001 dB power ratio deviation corresponds to approximately 0.023% in power, using `100 × (10^(0.001/10) − 1)`. This is an illustrative conversion of error magnitude. In the table, 0.001 dB specifies a standard deviation, not a fixed offset.

The nonzero scenarios use a zero mean correlated differential dB residual with exponential frequency correlation length 10 GHz. They are sensitivity assumptions, not measured receiver calibration statistics and not worst case guarantees against arbitrary systematic drift. Persistent systematic errors require the separate bounded bias analysis. More averaging does not eliminate persistent systematic error or a residual component held fixed over the acquisition window.

Sources: [exact extracted rows](../results/payload_bounds/calibration_caveat/critical_calibration_rows.csv), [conditions and source hashes](../results/payload_bounds/calibration_caveat/provenance.json), [full sensitivity CSV](../results/payload_bounds/sensitivity.csv), and [experiment protocol](../results/payload_bounds/protocol.json).

The earlier **99.955%** empirical recall uses 10 seconds with an exactly known reference and zero persistent residual. The earlier **93.800%** empirical recall uses a charged 10 + 10 second finite reference experiment. Both also require the zero residual assumption. They belong to different controls from the predicted 93.84% in this table and must retain their own resource and observation labels.

## What was changed and why

This note promotes a decisive modeling assumption to a prominent result qualification. The README, generated results report and paper now highlight it alongside favorable results. The underlying experiment arrays and metrics are unchanged; no new detection experiment was run for this documentation update.

## Remaining work and next steps

Measure reference/sample stability using the intended receiver, bands, timing and moving link normalization. Characterize spectral covariance, systematic drift and weather mismatch with independent calibration data. Freeze the correction and uncertainty model before evaluating separate transmissions with independent concentration truth. Rerun detection assessment using those measured errors and report both achievable performance and the ideal benchmark.

Until this is done, useful calibrated field recall, absolute concentration accuracy and environmental compliance remain unverified. A receiver noise simulation or an estimator close to its theoretical bound does not validate calibration stability.
