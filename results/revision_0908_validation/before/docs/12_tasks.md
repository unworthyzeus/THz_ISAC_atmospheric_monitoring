# Tasks

Updated on 2026 07 15 after probe optimization, the H2O control, the preliminary real column study, the tenfold investigation, the multi method 0.08 information study, and the detailed data provenance audit.

## Completed for the Current Feasibility Study

1. Audit the old external data benchmark and reclassify the `0.07793` normalized RMSE result as simulator self consistency evidence.
2. Audit all 383,585 retained UCI records for completeness, keys, physical consistency, station coverage, target distributions, and correlations.
3. Record input hashes and dependency versions in generated manifests.
4. Replace normalized gas templates with temperature and pressure dependent Voigt cross sections derived from 9,340 HITRAN lines.
5. Validate the local spectroscopy calculation against HAPI for CO, O3, SO2, NO2, H2O, and O2.
6. Integrate gas absorption through 24 atmospheric layers with temperature, pressure, water, oxygen, and declared exponential pollutant profiles.
7. Implement an exploratory Rayleigh PM mass extinction model for fine and coarse modes.
8. Implement a spherical Earth LEO link budget with aperture gains, free space loss, thermal noise, receiver noise figure, and implementation loss.
9. Implement complex line of sight channel and pilot averaged CSI building blocks.
10. Implement grouped chronological train, validation, and test partitions with an initially untouched test period, then label later reuse as diagnostic.
11. Implement Fisher information, CRB, one sigma mass concentration floors, and gas ppm conversion.
12. Run sensitivity sweeps for elevation, pilot count, transmit power, active probe count, and assumed independent residual error.
13. Compare detection floors with WHO 2021 health guidelines while explicitly excluding legal compliance claims.
14. Run a chronological 20,000 record simulated attenuation benchmark with mean, validation selected Ridge, oracle weighted least squares, and mismatched weighted least squares estimators.
15. Expand the Ridge alpha grid after the first search selected its upper boundary. The final validation selection is alpha `100,000`.
16. Generate physical signature, detection floor, sensitivity, estimator, and informative frequency artifacts.
17. Implement deterministic column balanced D optimal probe placement with fixed total transmit power comparisons.
18. Test continuous power allocation with the full pilot variance at 32 selected probes.
19. Run residual calibration and D optimal regularization stability checks.
20. Implement a local H2O dew point positive control with default and strict nuisance designs.
21. Replace an unphysical fixed temperature humidity tail diagnostic with local one and three sigma checks plus paired real meteorological state transfer.
22. Research real atmospheric column products and reject Sentinel 5P as temporally unmatched to the current UCI record.
23. Download, hash, inventory, and extract 20 official ESA CCI CO and NO2 product months for Beijing from March through December 2013.
24. Implement a domain aware HITRAN column forward model in molecules per square centimetre.
25. Run the preliminary native CO total column and NO2 tropospheric column CRB study.
26. Retain the failed 50 km atmosphere request and use the validated 20 km limit with an explicit forced CO profile whose bias direction is unknown.
27. Run the expanded full test suite successfully.
28. Add an H2O Fisher pseudoinverse stability sweep and preserve its numerical condition diagnostics.
29. Reproduce the `0.3474434442` Ridge metric from the hashed inputs and audit its split, scaling, denominator, and selection logic.
30. Quantify Ridge uncertainty with a paired bootstrap and show that its difference from the mean baseline is unresolved.
31. Add training prior LMMSE, target specific Ridge, sampler sensitivity, and pilot likelihood sensitivity cases.
32. Freeze and evaluate multitask and nonlinear spectral candidates across ten fixed modeled receiver noise seeds.
33. Implement exact causal pollutant lag features, auxiliary weather models, persistence, and context plus spectrum ablations.
34. Quantify the validation selected ideal noise reduction needed to reach the requested `0.0347443444` target.
35. Resolve official Aura MLS Level 1 radiance and Level 2 CO and O3 metadata through NASA CMR and record the Earthdata authentication blocker.
36. Evaluate 216 advanced THz prior, likelihood, probe, power, nuisance, and constraint cases without changing the Beijing metric contract.
37. Quantify the minimum declared, residual retaining, optimistic, and context assisted information budgets for both `0.08` and `0.03`.
38. Implement a 189 feature strictly causal forecast with current and future target mutation tests; improve test normalized RMSE from `0.104507` to `0.095485`.
39. Implement strict contemporaneous station network reconstruction with all six current query pollutant values masked; reach `0.088890` and document the empirical attempted family plateau.
40. Implement single channel repair with only target `j` hidden; reach `0.074855` on the unchanged six target test macro while requiring the other five current query channels.
41. Download and hash verify all 10 files in the real measured Mendeley THz protein dataset, retain two failed API routes, and run a fixed band positive control without pseudo replicates.
42. Evaluate a real UCI field sensor calibration control, record its best four target macro of `0.146500`, and prevent the easy benzene channel from being reported as a macro success.
43. Consolidate all successful and failed multi method attempts in `docs/34_multi_method_information_floor_study.md`.
44. Audit every external source, headline result, and major experiment branch as measured, measurement derived, semi synthetic, fully synthetic, artificially masked, or derived; record hashes, transformations, RMSE claim boundaries, quality risks, and reproducibility gaps in `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

## Final Output Completed

1. Rebuilt the IEEE paper around the conditional negative physical feasibility result, optimized probes, the H2O control, and real ESA CCI columns.
2. Compiled the revised eight page PDF with Tectonic and visually inspected every rendered page.
3. Corrected evidence table width, native column wording, method reproducibility, redundant figures, and final reference balance after visual and independent review.
4. Completed the final documentation and repository state review in `docs/29_ieee_paper_build_and_visual_validation.md`.
5. Rebuilt the manuscript with the advanced THz information budget, causal forecast, strict station reconstruction, successful single channel repair, and real measured THz positive control.
6. Compiled and visually inspected the final 10 page IEEE PDF; all 135 tests, scoped Ruff, Python compilation, artifact assertions, embedded font checks, and whitespace checks pass.
7. Added a canonical source by source provenance and synthetic evidence audit, linked it from the current study and README, and marked outdated planning notes as historical.

## Next Research Tasks

1. Obtain measured paired sub THz channel estimates and atmospheric reference measurements.
2. Validate background attenuation and layer profiles against independent propagation software and ITU recommendations.
3. Replace exponential pollutant scale heights with measured, assimilated, or bounded vertical profiles.
4. Calibrate PM particle size distributions, complex refractive index, density, nonsphericity, and humidity growth.
5. Quantify instrument response, frequency offset, clear sky reference uncertainty, and calibration drift.
6. Evaluate disjoint usable sensing bands under realistic spectrum allocations instead of treating 60 to 400 GHz as a contiguous waveform.
7. Repeat evaluation with station holdout, multiple chronological windows, and environment shift tests.
8. Evaluate constrained nonnegative and Bayesian estimators only after independent physical validation.
9. Add measured channel evidence or retain the explicit simulated observation scope in every claim.
10. Extend the real column series or define a justified representative sample plan.
11. Add satellite averaging kernels and profile data to the column forward model.
12. Replace the local H2O linear bound with nonlinear inference conditioned on record specific temperature and pressure.
13. Replace the one row per timestamp deterministic sample with all eligible rows or repeated station and time stratified samples.
14. Validate either pilot power averaging or coherent complex CSI as the primary observation likelihood through Monte Carlo simulation.
15. Evaluate the improved `0.095485` auxiliary forecast on a fresh external period and keep it separate from THz inversion.
16. Obtain authorized Earthdata access and run a bounded real Aura MLS radiance retrieval control.
17. Investigate calibrated limb or occultation geometry as a physically different sensing architecture.
18. Correct the ESA CCI CO and NO2 dataset authors, DOI, and version wording in the IEEE references before submission.
19. Add dedicated tracked reproduction scripts, manifests, metrics, and predictions for the Italian field calibration and retrospective repair controls.
20. Publish an immutable data and code release with a repository URL or archive DOI and stronger HITRAN release pinning.

## Conditional Research Decision

Probe placement was optimized as a bounded signal processing test and improved gas floors by about 1.5 to 1.85 times at 256 probes. It did not rescue the reference configuration. Ridge remains numerically close to the training period mean and their conditional paired row bootstrap interval includes zero. The advanced declared residual retaining THz result is `0.347466`, while the most optimistic context assisted sensitivity with fixed total power and no per tone cap is `0.239100`. The declared exact model needs at least a 5,918 fold modeled noise standard deviation reduction to target `0.08`. A strictly causal ground forecast reaches `0.095485`, and all six masked station reconstruction reaches `0.088890`; neither is THz inversion. Single channel repair reaches `0.074855` only because the other five current query channels remain available. The real measured THz protein control is strongly monotonic but reaches macro normalized RMSE `0.199270` on a separate small laboratory task. Further estimator complexity must not be used to hide the atmospheric physical gap. A positive atmospheric sensing claim still requires measured attenuation and calibrated uncertainty.

## Operational Work Not Authorized by the Research Task

No commit, push, deployment, or external publication action is implied by this task list. Those actions require an explicit user request.
