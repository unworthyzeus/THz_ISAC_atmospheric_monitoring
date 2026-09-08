# Probe Optimization and H2O Positive Control

## Purpose

This note records the follow up experiments started after the chronological Ridge result reached mean normalized RMSE `0.347443`. It explains what was tried, why it was tried, what worked, what failed, what remains uncertain, and what should happen next.

The negative Ridge result is retained as the empirical baseline. It is not replaced by a more favorable metric. Ridge differs from the training period mean by only `0.0000354` normalized RMSE and both models have negative mean R2. That result remains evidence that the reference simulated pollutant spectra do not support useful multivariate regression.

## Questions

The follow up asks two separate questions:

1. Can physics based frequency placement and power allocation recover substantially more pollutant information without changing total transmit power?
2. Does the same declared model give a substantially tighter local CRB for a strong atmospheric species?

The first question tests the sensing design. The second is a positive control that helps distinguish a broken pipeline from weak pollutant signatures.

## Real and Modeled Evidence

Real inputs:

1. 9,340 processed HITRAN lines for CO, O3, SO2, NO2, H2O, and O2.
2. 383,585 complete UCI Beijing station hour records.
3. UCI temperature, pressure, and dew point values used to define atmospheric states.

Modeled evidence:

1. All THz attenuation observations.
2. Vertical gas and water profiles.
3. The LEO link, pilot variance, independent residual, and hardware assumptions.
4. Fisher information and CRB results.

No measured sub THz channel data are used. The positive control is therefore a modeled sensing control conditioned by real meteorology, not a field retrieval.

## Experiment 1: Physics Based Probe Placement

### What was done

`scripts/run_probe_optimization.py` builds a 1,024 point candidate grid from 60 to 400 GHz using the validated layered HITRAN model. It evaluates 16, 32, 64, 128, and 256 active probes.

For each tone count and scenario, the comparison keeps total transmit power fixed. Fewer active probes receive more equal power per probe. The methods are:

1. Evenly spaced probes with equal power.
2. Greedy regularized D optimal placement with equal power.
3. D optimal placement followed by continuous power allocation at 32 probes.

The selection matrix contains the four gas sensitivities plus offset, atmospheric background, fine PM, and coarse PM nuisance columns. Every parameter column is normalized before the greedy log determinant calculation, so the method is a column balanced joint gas and nuisance design. WHO scaling therefore does not influence selection. The selector uses physical sensitivities and declared noise variance without UCI pollutant labels or retrieval errors. Only the later continuous power allocation directly optimizes the nuisance projected gas determinant.

Fixed total transmit power is preserved. Total occupied probe bandwidth and the number of assumed independent residual samples are not fixed when probe count changes, so the tone count sweep is not a fixed resource comparison in every dimension.

### Why it was done

The former 256 point grid spends probes in weak or opaque regions. The informative frequency table showed concentration around CO near 345 GHz, O3 and SO2 near 357 to 359 GHz, and NO2 near 396 GHz. A fair design test should place probes around jointly informative windows while retaining nuisance identifiability.

### Reference result

The reference case remains 45 degrees elevation, 23 dBm total power, 30 pilots, and 0.63 dB independent residual standard deviation per probe.

| Target | Uniform 256 ratio | D optimal 256 ratio | Improvement factor | D optimal three sigma ratio |
| --- | ---: | ---: | ---: | ---: |
| CO | 20.847 | 11.549 | 1.805 | 34.647 |
| O3 | 280.845 | 184.670 | 1.521 | 554.010 |
| SO2 | 107.643 | 63.935 | 1.684 | 191.806 |
| NO2 | 2,579.942 | 1,664.559 | 1.550 | 4,993.677 |

Frequency placement produces a real information gain under the model, but it does not make the reference link useful at guideline concentration scales. CO remains 11.55 times its comparison scale at one sigma and 34.65 times at three sigma.

### Optimistic combined result

The optimistic scenario remains 15 degrees elevation, 33 dBm total power, 3,000 pilots, and zero residual error.

| Target | Uniform 256 ratio | D optimal 256 ratio | Improvement factor | D optimal three sigma ratio |
| --- | ---: | ---: | ---: | ---: |
| CO | 0.652 | 0.353 | 1.848 | 1.059 |
| O3 | 9.181 | 5.925 | 1.549 | 17.776 |
| SO2 | 4.350 | 2.594 | 1.677 | 7.783 |
| NO2 | 88.371 | 55.676 | 1.587 | 167.028 |

Optimized placement moves optimistic CO very close to a robust threshold, but it still misses at three sigma: `1.058832` times the WHO concentration scale. This is not a detection success. Every other gas remains well above one at one sigma.

### Calibration requirement

For the fixed optimized 256 probe optimistic design, one sigma CO remains below its comparison scale only while the independent residual standard deviation is at most `0.222792 dB`. Its three sigma ratio is already `1.058832` at zero residual, so no nonnegative residual can make it pass the three sigma comparison under the remaining assumptions.

At the reference geometry and pilot count, all four gases remain above one even at zero residual. Better calibration alone cannot close the reference gap.

### Power allocation result

Continuous power allocation was tested on the 32 probes selected by D optimal placement. The optimizer uses the full pilot variance, including the residual floor, and preserves fixed total power.

The allocation converged in every scenario, but its benefit over equal power on the same selected frequencies was small:

1. Reference gains range from `1.0017` for CO to `1.0169` for O3.
2. Zero residual reference gains range from `1.0016` to `1.0181`.
3. Optimistic gains range from `1.0043` to `1.0434`.

This result is useful even though the gains are modest. Frequency placement is the dominant design improvement in the tested setup. Once good probes are chosen, the independent residual and pilot variance floors limit the value of redistributing power.

### Stability check

The reference 256 probe selection was repeated with regularization values `1e-6`, `1e-9`, and `1e-12`. All three runs selected exactly the same frequencies and produced identical reported gas ratios. The result is not sensitive to the tested regularization range.

### What worked

1. The 1,024 point candidate grid built in about 11 seconds and remained finite.
2. Fixed total power accounting was preserved for every tone count.
3. D optimal selection was deterministic and passed focused unit tests.
4. Every tested gas remained algebraically identifiable.
5. Frequency placement improved all four gas floors in every main scenario.
6. The calibration sweep separated residual limited and pilot limited cases.

### What failed or did not help enough

1. No optimized reference case reached a one sigma ratio below one.
2. Optimistic CO still missed the three sigma scale comparison by 5.9 percent at zero residual.
3. O3, SO2, and NO2 remained infeasible in the optimistic combined case.
4. Continuous power allocation produced only small gains after frequency selection.
5. The selected frequencies remain conceptual multiband probes without an instrument bandpass, synthesizer, antenna bandwidth, or regulatory allocation.

## Experiment 2: H2O Positive Control

### What was done

`scripts/run_h2o_positive_control.py` uses only the chronological training period to define the local state. The training medians are 4.0 degrees Celsius dew point, 289.15 K, and 100,870 Pa. A central HITRAN finite difference with a 0.25 degree step produces the local attenuation derivative in dB per degree Celsius.

The target parameter is surface dew point mapped through a fixed 2 km H2O scale height. It is a proxy for the modeled water column, not a direct column observation.

The control evaluates three nuisance cases:

1. Target only.
2. Offset, four pollutant gas spectra, and two PM spectra.
3. The same nuisances plus an unknown scale on the nominal H2O and O2 background.

Two D optimal selections are used. The default design omits the unknown background scale, while the strict design includes it during selection.

### Result at 256 probes

| Selection | Nuisance case | One sigma floor, degrees C | Three sigma floor, degrees C |
| --- | --- | ---: | ---: |
| D optimal default | Target only | 0.144 | 0.433 |
| D optimal default | Offset, gases, and PM | 0.290 | 0.871 |
| D optimal default | Added background scale | 2.541 | 7.623 |
| D optimal strict | Target only | 0.146 | 0.438 |
| D optimal strict | Offset, gases, and PM | 0.298 | 0.893 |
| D optimal strict | Added background scale | 0.848 | 2.543 |

The declared model gives a sub degree local H2O CRB. Under the default nuisance model, the three sigma floor is below 1 degree Celsius. Under the stricter background scale nuisance, selection that explicitly includes that nuisance gives a one sigma floor of 0.848 degrees Celsius and a three sigma floor of 2.543 degrees Celsius. This is an information bound, not a demonstrated estimator or measured retrieval.

The test period dew point fifth to ninety fifth percentile range is about 42.7 degrees Celsius. The strict one sigma floor is about 1.99 percent of that spread. This demonstrates that the physical pipeline can contain strong local information when the target spectrum is large.

The full Fisher matrix condition number is around `1e11`, so numerical stability was checked explicitly. Sweeping the pseudoinverse cutoff from `1e-10` through `1e-15` changes the strict one sigma floor by less than 0.2 percent and does not change identifiability.

### A selection failure that was retained

The default D optimal selection performs poorly when an unknown background scale is added after selection: its strict floor is 2.541 degrees Celsius, worse than the 1.126 degree uniform result. This is an objective mismatch, not evidence that D optimal design is universally harmful. Reoptimizing with the background scale in the selection design reduces the floor to 0.848 degrees Celsius.

This failure is important because it shows that an omitted nuisance can invalidate an apparently optimized sensing design.

### Local linearity and state transfer

The positive control CRB is local. Its linearization was checked at plus and minus one and three times the reported 256 probe floor while holding the conditioning temperature and pressure fixed.

| Selection and nuisance | Displacement | Largest relative RMS error across signs | Largest RMS error, dB | Error / 0.63 dB |
| --- | --- | ---: | ---: | ---: |
| D optimal default, offset plus gas and PM | One sigma, 0.290 degrees C | 0.91% | 0.00151 | 0.00239 |
| D optimal default, offset plus gas and PM | Three sigma, 0.871 degrees C | 2.74% | 0.01372 | 0.02178 |
| D optimal strict, added background scale | One sigma, 0.848 degrees C | 2.67% | 0.01247 | 0.01979 |
| D optimal strict, added background scale | Three sigma, 2.543 degrees C | 8.18% | 0.11578 | 0.18377 |

The local approximation is adequate near the bound scale under fixed temperature and pressure.

Transfer to real distribution tails remains poor. Records near training Q05 pair dew point minus 19.6 degrees Celsius with median temperature 0.1 degrees Celsius and pressure 1,023.0 hPa. Records near Q95 pair dew point 21.9 degrees Celsius with median temperature 25.2 degrees Celsius and pressure 998.3 hPa. Applying the reference linear model to those paired states gives RMS errors from 5.41 to 6.64 dB and relative errors from 35.4% to 96.5%, depending on selection.

Therefore the local CRB must not be presented as a full range dew point estimator. A nonlinear model conditioned on record specific temperature and pressure is required across the observed humidity range.

## Interpretation

The two experiments sharpen the earlier negative result:

1. The signal processing design was not optimal. Better frequency placement improves pollutant Fisher bounds by about 1.5 to 1.85 times at 256 probes.
2. That gain is not enough for the reference pollutant problem.
3. The same declared model gives a sub degree local H2O bound, which is a positive information calculation control but not a measured retrieval.
4. Nuisance assumptions determine which probe design is optimal.
5. Local CRBs cannot substitute for a nonlinear held out retrieval across a broad atmospheric distribution.

The main conclusion remains negative for the declared multi pollutant reference link, but the paper can now explain where useful signal processing gains exist and why they still do not close the physical gap.

## Risks and Limitations

1. Received attenuation is modeled, not measured.
2. Frequency candidates assume exact HITRAN line locations and no instrument response.
3. Independent probe residuals can overstate the gain from adding probes.
4. Selection is optimized for one median atmosphere and can shift under humidity, temperature, pressure, and calibration changes.
5. D optimality balances a determinant and does not minimize every individual target floor.
6. The 32 probe power result is a local continuous optimization, not a global hardware design.
7. The H2O target is surface dew point under a fixed vertical profile, not a measured path column.
8. The H2O finite difference is local and fails across the distribution tails.
9. WHO values remain scale comparisons with different averaging periods.
10. Probe count changes total occupied bandwidth and the number of independent residual samples even though total transmit power is fixed.

## What Remains to Be Done

1. Add instrument bandpass and frequency offset robustness to selection.
2. Optimize contiguous, disjoint, hardware feasible sensing bands.
3. Repeat selection across a training distribution of atmospheric states rather than one median state.
4. Include correlated calibration covariance rather than independent residuals.
5. Implement a nonlinear H2O retrieval and evaluate it on chronologically held out real dew point states with modeled attenuation.
6. Replace surface concentration scale heights with real satellite columns and measured or reanalysis profiles.
7. Obtain measured sub THz attenuation before making a positive sensing claim.

## Next Steps

1. Use the optimized probe result as a bounded signal processing improvement in the IEEE paper.
2. Retain the negative reference conclusion and the optimistic CO three sigma miss.
3. Use H2O only as a labeled positive control with an explicit local range caveat.
4. Start the real ESA CCI CO and NO2 column experiment documented in `docs/30_real_column_dataset_options.md`.
5. Treat any frequency plan as conceptual until bandpass, regulation, calibration, and hardware constraints are included.

## Reproduction

```powershell
python scripts/run_probe_optimization.py
python scripts/run_h2o_positive_control.py
python -m pytest tests -q
```

Primary artifacts:

1. `results/tables/probe_optimization_summary.csv`
2. `results/tables/probe_selected_frequencies.csv`
3. `results/tables/probe_power_allocation.csv`
4. `results/tables/probe_calibration_requirements.csv`
5. `results/tables/probe_regularization_sensitivity.csv`
6. `results/tables/probe_optimization_manifest.json`
7. `results/tables/h2o_positive_control_summary.csv`
8. `results/tables/h2o_positive_control_frequencies.csv`
9. `results/tables/h2o_positive_control_linearity.csv`
10. `results/tables/h2o_positive_control_manifest.json`
11. `results/tables/h2o_positive_control_numerical_stability.csv`
12. `results/figures/probe_optimization_comparison.png`
13. `results/figures/probe_power_allocation.png`
14. `results/figures/h2o_positive_control.png`
