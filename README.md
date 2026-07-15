# THz ISAC Atmospheric Monitoring

This repository studies the estimation limits of atmospheric pollutant sensing from sub THz non terrestrial network channel observations.

The canonical detailed record of where every dataset came from, which observations are simulated, which scores use real measurements, and which claims are supported is `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

## Current Scientific Conclusion

The completed physical feasibility study gives a negative result for the declared reference link. Pollutant signatures derived from HITRAN and real UCI concentration scenarios are much smaller than the pilot attenuation uncertainty. At 45 degrees elevation, 30 pilots, and an assumed independent residual error of 0.63 dB standard deviation per tone, every one sigma detection floor is above its WHO 2021 health guideline comparison level. The 0.63 dB value is a scenario assumption borrowed from adjacent literature and is not calibrated for this sub THz pollutant link.

| Target | One sigma floor | WHO 2021 guideline | Floor divided by guideline |
| --- | ---: | ---: | ---: |
| CO | 83,015 micrograms per cubic meter | 4,000 | 20.8 |
| O3 | 28,099 micrograms per cubic meter | 100 | 281.0 |
| SO2 | 4,308 micrograms per cubic meter | 40 | 107.7 |
| NO2 | 64,427 micrograms per cubic meter | 25 | 2,577.1 |
| PM2.5 | 1,513,315 micrograms per cubic meter | 15 | 100,887.7 |
| PM10 | 1,581,204 micrograms per cubic meter | 45 | 35,137.9 |

The WHO values are health guidelines with different averaging periods. Comparing one burst CRB values with 8 h or 24 h health guidelines is only a scale comparison, not a legal compliance test or like for like averaging period evaluation.

Physics based probe placement improves the reference 256 probe gas floors by factors from 1.52 to 1.81 while preserving total transmit power. The optimized reference CO ratio is still 11.55 at one sigma and 34.65 at three sigma. In the optimistic combined stress test at 15 degrees elevation, 3,000 pilots, zero residual error, and 33 dBm, optimized CO reaches 0.353 at one sigma but remains 1.059 at three sigma. All other gases remain above their scales.

A new native column experiment uses ten months of real ESA CCI Beijing retrievals rather than converting surface concentrations through a scale height. With D optimal 256 probes, the reference CO total column floor is 82.9 times the ten month sample quantile span and the NO2 tropospheric column floor is 5,476 times its span. Even the optimistic combined case remains above those spans by factors 2.70 and 180. The full reported CO column is forced into a normalized 0 to 20 km reference profile, so the missing upper atmosphere distribution creates a bias of unknown sign. The THz observations are still modeled.

The declared model also gives a sub degree local H2O CRB: 0.290 degrees Celsius at one sigma with offset, gas, and PM nuisance, or 0.848 degrees with an additional background scale nuisance and a design optimized for it. This is a positive information calculation control, not a demonstrated estimator or measured retrieval. Transfer to real humidity distribution tails requires a nonlinear model conditioned on temperature and pressure.

The originally held out Ridge macro training Q05 to Q95 normalized RMSE is reproduced exactly at `0.3474434442`. A 216 case advanced inversion diagnostic leaves the declared residual retaining THz result at `0.3474661497`, while its most optimistic zero residual, context assisted sensitivity with fixed total power and no per tone cap reaches `0.2390996644`. A stronger strictly causal ground forecast reaches `0.0954845662`, and strict all six channel station network reconstruction reaches `0.088889959`. A separately labeled single channel repair task reaches `0.074855260` when the other five current query channels remain available, meeting the revised `0.08` target without being presented as THz inversion. Within the frozen exact physics LMMSE sensitivity, the declared design needs at least a `5,918` fold modeled noise standard deviation reduction to target `0.08`, equivalent under ideal independence to about 35.0 million repeated spectra. This is an information gap diagnostic, not achieved sensor performance. Follow up comparisons reuse the test period, and the reference forward scenario uses full period atmospheric medians, so these extensions are diagnostic rather than a strict leakage free inductive evaluation.

A real measured THz positive control now uses the CC BY Mendeley dataset `10.17632/dpw4svmdr8.1`. All 10 files are hash verified. Fixed 0.9 to 1.3 THz aqueous protein features give absolute Spearman correlations of `0.893` and `1.000`, but leave one concentration out macro normalized RMSE is `0.199270`. This confirms real spectral monotonicity on a small laboratory task, not atmospheric pollution sensing.

The earlier `0.07793` mean normalized RMSE and `0.94523` mean R2 result is superseded as the project headline. It remains an engineering self consistency check in which a simplified generator and inverse feature path share normalized templates. It does not demonstrate physical detectability.

## Evidence Classification

| Component | Status |
| --- | --- |
| Beijing pollutant and meteorological records | Real UCI measurements, 383,585 complete case station hour rows |
| Beijing CO and NO2 columns | Real ESA CCI Level 3 retrievals, ten matched monthly 1 degree cells for March through December 2013 |
| Spectroscopic line parameters | Real HITRAN data, 9,340 lines for four target gases plus H2O and O2 |
| Molecular absorption | Calibrated line by line Voigt calculation, checked against HAPI at the reference surface condition |
| Vertical pollutant and column profiles | Assumed exponential scale heights; total CO is forced into a normalized 0 to 20 km profile |
| PM scattering | Exploratory Rayleigh mass extinction model with assumed particle properties |
| NTN observations and CSI | Simulated; no paired measured sub THz CSI is used |
| Detection floors | Analytical CRB values under the declared simulated observation model |
| Measured THz positive control | Real Mendeley aqueous protein THz TDS summaries, 13 concentration levels across two proteins; not atmospheric |
| Aura MLS measured signal route | Official Level 1 radiance and Level 2 CO and O3 metadata resolved; granule acquisition blocked pending Earthdata authentication |

Synthetic observations are acceptable here only as a transparent feasibility experiment grounded in public measurements, spectroscopic parameters, and declared assumptions. They are not field validation.

## Reproduce the Study

Install the dependencies, then run from the repository root:

```powershell
python scripts/download_external_data.py
python scripts/run_data_quality_audit.py
python scripts/validate_physical_spectroscopy.py
python scripts/run_physical_feasibility.py
python scripts/run_probe_optimization.py
python scripts/run_h2o_positive_control.py
python scripts/download_column_smoke_data.py
python scripts/download_beijing_column_series.py
python scripts/run_real_column_feasibility.py
python scripts/run_rmse_metric_audit.py
python scripts/run_spectral_model_stability.py
python scripts/run_auxiliary_nowcasting.py
python scripts/run_advanced_thz_inversion.py
python scripts/run_causal_forecasting_v2.py
python scripts/run_spatial_fusion_benchmark.py
python scripts/run_single_channel_repair_benchmark.py
python scripts/download_measured_thz_control.py
python scripts/run_measured_thz_control.py
python scripts/check_aura_mls_access.py
python -m pytest tests -q
```

The physical run produces:

1. Calibrated pollutant signature summaries.
2. Informative frequency rankings.
3. Link budget diagnostics.
4. Fisher information and one sigma detection floors.
5. Sensitivity sweeps for elevation, pilot count, transmit power, active tone count, and assumed independent residual error.
6. A chronological train, validation, and test estimator benchmark using simulated attenuation and real UCI labels.

The original assumptions, input hashes, dependency versions, split dates, and selected Ridge alpha are stored in `results/tables/physical_feasibility_config.json`. Follow up manifests in `results/tables/` include `probe_optimization_manifest.json`, `h2o_positive_control_manifest.json`, `real_column_feasibility_manifest.json`, `rmse_metric_audit_manifest.json`, `spectral_model_stability_manifest.json`, `auxiliary_nowcasting_manifest.json`, `advanced_thz_inversion_manifest.json`, `causal_forecasting_v2_manifest.json`, `spatial_fusion_manifest.json`, `single_channel_repair_manifest.json`, `measured_thz_control_manifest.json`, and `aura_mls_access_manifest.json`.

## Reference Study Configuration

The current study uses 256 frequency probes from 60 to 400 GHz, 24 atmospheric layers from the surface to 12 km, a 550 km satellite, 23 dBm total transmit power, 0.50 m transmit and 0.30 m receive apertures, 1 MHz per tone, and 45 degrees elevation. These are multiband feasibility probes, not one contiguous 340 GHz OFDM allocation.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `docs/` | Research decisions, audits, methods, failures, results, risks, and task status |
| `src/thz_isac/` | Spectroscopy, atmosphere, link, CSI, bounds, evaluation, and estimator modules |
| `scripts/` | Reproducible data, validation, and experiment entry points |
| `data/` | Raw and processed external data, ignored by Git and regenerated by scripts |
| `results/` | Tables and figures generated by the experiments |
| `sources/` | Local research papers used as project sources |
| `paper/` | IEEE style paper source and compiled output |

The final IEEE paper is `paper/build/main.pdf`, with source in `paper/main.tex`. The main baseline record is `docs/28_physical_feasibility_results.md`. Optimized probes and the H2O control are documented in `docs/31_probe_optimization_and_h2o_positive_control.md`. Real column acquisition and feasibility are recorded in `docs/30_real_column_dataset_options.md` and `docs/32_real_satellite_column_feasibility.md`. The metric audit and tenfold investigation are documented in `docs/33_tenfold_rmse_reduction_study.md`. The advanced THz, causal forecast, station network, single channel repair, real sensor calibration, measured THz control, and all new failures are consolidated in `docs/34_multi_method_information_floor_study.md`. The complete data provenance and synthetic evidence audit is `docs/35_data_provenance_and_synthetic_evidence_audit.md`. The data quality findings are in `docs/27_data_quality_audit.md`, and the audit that invalidated the former headline is in `docs/26_scientific_audit_and_paper_rebuild.md`.

## Remaining Scientific Work

The software tasks required for the current feasibility study are implemented. The main remaining research work is external validation and uncertainty reduction:

1. Obtain measured, paired sub THz channel and atmospheric reference data.
2. Replace assumed pollutant and satellite column profiles with measured or assimilated vertical profiles and a validated higher atmosphere model.
3. Calibrate PM refractive index, size distribution, density, shape, and humidity growth.
4. Evaluate realistic disjoint communication and sensing bands under regulatory constraints.
5. Validate the link and atmospheric model against ITU recommendations and independent propagation tools.
6. Repeat temporal and station holdout experiments with profile and instrument mismatch.
7. Replace the one row per timestamp deterministic sample with all eligible rows or repeated station and time stratified samples.
8. Validate one primary pilot likelihood through Monte Carlo simulation.
9. Acquire a bounded Aura MLS Level 1 radiance sample through authorized Earthdata access and build a pressure matched measured signal control.

Until those steps are complete, the defensible claim is that the declared reference configuration is not sensitive enough under the stated model, not that ambient pollutants can be retrieved from a real operational NTN link.
