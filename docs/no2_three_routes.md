# NO2 differential, calibration and frequency design

## What was done and why

**SOURCE STATEMENT:** The available I2R document is a two-page proposal. It asks for layered atmospheric modeling, HITRAN line shapes, simulated CSI, ratiometric/optimization inversion and sensitivity bounds. It contains no repeated receiver calibration dataset. [I2R proposal](../references/proposals/I2R_proposal_THz_ISAC.pdf), physical pp. 1–2, Tasks 1–4.

**RESULT:** Implemented and evaluated all three requested computational routes: temporal and spectral differences; a structured calibration uncertainty model and a real-record characterization interface; and directly recalculated fine-grid frequency/dwell design. The 30 primary designs have fixed 10/100 s charged acquisition budgets, one active −1 dBm tone, integer 1 μs pilots and assumed 1 ms retuning. All 71 original band probes remain in the 424-point fine candidate set. [Frozen protocol](../results/no2_three_routes/design/protocol.json), [implementation](../src/thz_isac/no2_design.py), [physical provenance](../results/no2_three_routes/physical/manifest.json).

## Results

| Design at 100 s | Worst design RMSE / 25 μg/m³ |
| --- | ---: |
| 71 / equal / box | 3.513 |
| 71 / optimized / box | 2.501 |
| 424 / equal / box | 3.509 |
| 424 / optimized / box | 2.340 |
| 424 / optimized / polynomial | 1.283 |
| 424 / optimized / poly + residual | 1.363 |
| 424 / differential / stable | 2.571 |
| 424 / differential / poly + residual | 2.578 |

**RESULT:** These are achieved conditional risks, not measured concentration errors. The equal-dwell fine grid alone makes little difference; optimizing dwell makes the main improvement. Fine-grid independent spectral error of ±0.0001 dB still has an exact represented-LP noise-free lower bound of 1.923285, above the unit target. [All 30 results](../results/no2_three_routes/design/summary.csv), [resources](../results/no2_three_routes/design/resources.csv), [floor certificates](../results/no2_three_routes/requirements/floor_certificates.json), [independent checks](../results/no2_three_routes/verification/checks.json).

**SELF-DERIVED:** Differencing cancels only identical persistent calibration. Independent radius-ε errors leave a radius-2ε difference error. At equal total time, two independent half-budget readings give four times the noise variance. They estimate concentration changes; an absolute estimate requires a baseline and its uncertainty. Complete spectral differencing with the full induced covariance leaves GLS information unchanged when the original offset is already a nuisance. [Derivation](../paper/no2_three_routes.tex), [spectral control](../results/no2_three_routes/design/spectral_difference_control.json), [analytic tests](../tests/test_no2_design.py).

**RESULT / INFERENCE:** Declaring calibration to lie in smooth polynomial modes is a stronger assumption. Each mode receives one third of the pointwise budget remaining after a residual box; the total set is a subset of the original box. The mixed model requires the arbitrary residual to be bounded by 0.00001 dB, which has not been measured. With the frozen 100 s operators, pure polynomial and mixed calibration reach the design target at sufficient acquisition times of 181.798 and 248.809 s. These are constructive conditional times, not minimum necessary times. The mixed case radiates 0.1973 J; receiver electrical power is excluded. [Time calculation and traces](../results/no2_three_routes/requirements/fixed_design_time.csv), [uncertainty-set definition](../paper/no2_three_routes.tex).

**RESULT:** The mixed structured fine design gives worst error 1.291 on 16 new modeled states at 100 s with nominal covariance. For the 24 hourly real-weather pairs, its worst absolute atmospheric bias is 3.201, while the stable-calibration differential estimator has worst change bias 0.411. Its noise SD is 2.399 and pair RMSE is 2.434, so canceling atmospheric drift does not restore feasibility at this budget. The absolute and change estimates are distinct targets. [Complete evaluation](../results/no2_three_routes/evaluation/summary.csv), [pair metadata](../results/no2_three_routes/evaluation/pair_metadata.csv), [model-state metadata](../results/no2_three_routes/evaluation/new_state_metadata.csv).

**RESULT / LIMITATION:** Eleven of 24 pairs have a visited frequency below 5 dB under modeled real weather. The nominal design regime therefore fails in part of this stress set. The weather-dependent covariance replay reaches 26.280 for mixed structured absolute retrieval and 47.243 for stable differences, but those magnitudes extrapolate the coherent approximation and are not validated performance predictions. The physical model uses observed surface weather with assumed profiles and a repeated fixed slant geometry, not synchronized THz observations. [Evaluation protocol](../results/no2_three_routes/evaluation/protocol.json), [full per-state outcomes](../results/no2_three_routes/evaluation/errors.csv).

## Calibration characterization and remaining evidence

**SOURCE STATEMENT:** Bjarnason et al. use separate sample and reference spectra and propagate both noise contributions; their apparatus also exhibits source repeatability and tuning limitations. Its gas, band and laboratory hardware differ from this proposal. It supports measuring these effects, not transferring a drift amplitude or polynomial model to our receiver. [NIST primary PDF](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=32980), physical p. 2, Eqs. 4–6; pp. 5–6, Section 5.A and Fig. 4; p. 8, tuning-repeatability discussion.

**IMPLEMENTATION:** The characterization CLI accepts actual repeated reference measurements as a long CSV with `time`, `frequency_ghz`, `error_db`. Error means observed minus known reference. It rejects missing or duplicate frequency/time samples, uses chronological 60/20/20 percent timestamp splits, fits a training-only mean spectrum and fixed-degree polynomial basis, and reports heldout residual and joint-envelope coverage. Training maxima are descriptive and do not guarantee future coverage. A reference's own uncertainty must be recorded and propagated; none is supplied here. [CLI](../scripts/characterize_receiver_calibration.py), [implementation and tests](../tests/test_no2_design.py).

```powershell
python scripts/characterize_receiver_calibration.py C:/path/to/reference_sweeps.csv --output results/measured_receiver_calibration --degree 2
```

**INFERENCE / NEXT STEP:** With HITRAN and I2R alone, route 2 can specify and test calibration requirements but cannot establish measured drift. The most promising tested computational direction is jointly optimized dwell with a justified small structured residual. It still needs receiver measurements, a humidity-aware acquisition rule, geometry control and synchronized concentration/column truth. Temporal differencing is useful for relative change and bias cancellation, with an explicit noise and reference cost. [Current manuscript analysis](../paper/no2_three_routes.tex), [measured-data requirements](continuation_measurement_protocol.md).

## Verification, provenance and failed attempts

**RESULT:** An independent verifier recomputes 30 design rows, 1952 stress outcomes, every target/nuisance identity, integer allocation and energy budget, and both exact rational dual certificates. Eight new analytic tests cover covariance, dwell, drift structure and calibration split leakage. Initial import-environment and fixed-allocation solver failures were retained; the final design consistently evaluates the jointly optimized operator after dwell rounding. No stress outcome selected the estimator or uncertainty model. An evaluation started prematurely after the first failed design run was stopped before error outcomes were computed or inspected, then restarted after all designs passed. [Verification](../results/no2_three_routes/verification/checks.json), [initial attempts](../results/no2_three_routes/attempts/initial_design/explanation.json), [final discretization decision](../results/no2_three_routes/attempts/whitened_fixed_reoptimization/explanation.json).

CPU, software versions, runtime, sampled memory and input/output hashes are recorded in separate physical/design/evaluation/requirements/verification manifests. The incoming manuscript and documentation were copied before editing. [Before snapshot](../results/no2_three_routes/before), [frequency schedule](../results/no2_three_routes/report/frequency_schedule_100s.csv), [figure](../results/no2_three_routes/report/no2_routes.pdf).
