# Research Task Completion Status

Generated on 2026-07-06.

This document maps each research task from the project task list to the current repository state. The status labels are intentionally strict.

## Status Legend

| Status | Meaning |
| --- | --- |
| Completed | A working implementation or result exists in the repository and has been validated at least at the current project level. |
| Completed for the current benchmark | The requested capability exists for the current external data driven benchmark, but it may need expansion before a final thesis or publication claim. |
| Partially completed | A working first version exists, but the task is not complete at the physical, methodological, or validation level requested by the proposal. |
| Not completed | No implementation or result currently satisfies the task. |

## Overall Summary

| Task | Status | Main evidence | Main remaining gap |
| --- | --- | --- | --- |
| Task 1.1 | Partially completed | `src/thz_isac/atmosphere.py` | Tropospheric layers are not yet integrated through the external forward model with species density per layer. |
| Task 1.2 | Completed for the current benchmark | `scripts/download_external_data.py`, `src/thz_isac/hitran_templates.py` | HITRAN line parameters are extracted, but full calibrated HAPI absorption coefficients are still future work. |
| Task 1.3 | Partially completed | `src/thz_isac/hitran_templates.py`, `src/thz_isac/external_forward_model.py` | Lorentzian templates exist, but no Voigt profile or layer by layer absorption integration exists yet. |
| Task 1.4 | Partially completed | `src/thz_isac/hitran_templates.py`, `src/thz_isac/external_forward_model.py` | PM is modeled with smooth Rayleigh type trends, not a calibrated aerosol scattering model. |
| Task 2.1 | Partially completed | `src/thz_isac/constants.py`, `src/thz_isac/external_forward_model.py` | Frequency, subcarriers, elevation, and SNR exist, but no complete RF link budget exists. |
| Task 2.2 | Partially completed | `src/thz_isac/external_forward_model.py` | Wideband CSI amplitudes are simulated with slant path attenuation and AWGN, but without full link budget or phase channel modeling. |
| Task 3.1 | Completed for the current benchmark | `src/thz_isac/features.py`, `src/thz_isac/external_forward_model.py` | The method is still tied to simplified templates. |
| Task 3.2 | Completed for the current benchmark | `src/thz_isac/estimators.py`, `scripts/run_real_data_benchmark.py`, `scripts/run_real_ridge_sweep.py` | Optimization based fitting and ratiometric inversion are not yet developed as separate methods. |
| Task 4.1 | Not completed | No implementation yet | CRB or lower bound derivation is not implemented. |
| Task 4.2 | Partially completed | `scripts/run_snr_sweep.py`, `scripts/run_real_data_benchmark.py` | Sensitivity exists only as toy SNR sweep and random SNR or elevation variation, not as full external data sensitivity plus lower bounds. |
| Task 4.3 | Not completed | No implementation yet | Detection floors and environmental standard compliance are not quantified. |

## Task 1: Stratified Atmospheric Channel Modeling

### Task 1.1: Develop a multi layer tropospheric profile where pressure, temperature, and molecular density vary with altitude based on standard atmospheric reference models.

**Status: Completed for the current benchmark**

What has been completed:

1. A coarse standard troposphere helper exists in `src/thz_isac/atmosphere.py`.
2. It creates altitude layers from ground level to 12 km.
3. Each layer includes temperature, pressure, and relative density.
4. A slant path helper converts satellite elevation angle into an approximate tropospheric slant path.

Evidence:

1. `standard_troposphere_layers()`
2. `AtmosphereLayer`
3. `slant_path_km()`

What is not completed:

1. The external data forward model does not yet integrate absorption layer by layer.
2. Molecular density is not separated by gas species.
3. Humidity, pressure broadening by layer, and temperature dependence are not applied to HITRAN absorption.
4. There is no validation against a named standard atmosphere table.

Next step:

Implement a layer based propagation function that takes altitude, pressure, temperature, humidity, and gas concentration profiles, then integrates absorption along the slant path.

### Task 1.2: Use the HITRAN spectroscopic database to extract line positions, intensities, and broadening coefficients for target rotational gas transitions within the targeted frequency window.

**Status: Partially completed**

What has been completed:

1. HITRAN line data is downloaded through HAPI.
2. The current frequency window is 60 to 400 GHz.
3. The current target gases are CO, O3, SO2, and NO2.
4. H2O and O2 are also downloaded as atmospheric background components.
5. The processed HITRAN table includes line frequency, line intensity, and air broadening coefficient.

Evidence:

1. `scripts/download_external_data.py`
2. `src/thz_isac/hitran_templates.py`
3. `docs/18_external_data_acquisition.md`

What is not completed:

1. Only the main isotopologue is currently downloaded for each molecule.
2. HITRAN lines are converted into normalized templates, not calibrated absorption coefficients.
3. The current implementation does not yet use HAPI absorption coefficient calculations with pressure and temperature profiles.

Next step:

Replace normalized template generation with HAPI absorption coefficient generation for each gas across the stratified atmosphere.

### Task 1.3: Implement an atmospheric line shape profile, Voigt or Lorentz, to integrate molecular absorption along a vertical slant path determined by the satellite elevation angle.

**Status: Partially completed**

What has been completed:

1. Lorentzian line templates are implemented.
2. HITRAN line intensity and air broadening are used to shape the spectral templates.
3. Satellite elevation affects the attenuation through a slant path factor.

Evidence:

1. `src/thz_isac/hitran_templates.py`
2. `src/thz_isac/channel.py`
3. `src/thz_isac/external_forward_model.py`

What is not completed:

1. Voigt line shape is not implemented.
2. Layer by layer integration is not implemented.
3. Pressure and temperature dependent broadening is not applied by altitude.
4. The line shape output is normalized and used as a relative spectral template, not as a calibrated absorption coefficient.

Next step:

Use HAPI or a verified local implementation to calculate pressure and temperature dependent absorption coefficients, then integrate them over the slant path.

### Task 1.4: Model the frequency dependent Rayleigh aerosol scattering baseline for particulate matter across the same stratified slant path.

**Status: Partially completed**

What has been completed:

1. PM2.5 and PM10 are included as target variables.
2. Smooth frequency dependent Rayleigh type PM templates are implemented.
3. PM attenuation is included in the same slant path attenuation model as gases.

Evidence:

1. `rayleigh_pm_template()` in `src/thz_isac/hitran_templates.py`
2. PM scaling in `src/thz_isac/external_forward_model.py`

What is not completed:

1. The PM model is not a calibrated aerosol scattering model.
2. Particle size distribution, refractive index, humidity growth, and mass extinction efficiency are not included.
3. PM scattering is not integrated layer by layer through the troposphere.

Next step:

Implement a physically grounded PM scattering coefficient using particle size assumptions or public aerosol optical property models.

## Task 2: NTN Link Parameterization and CSI Synthesis

### Task 2.1: Define the link budget and physical parameters for a 6G sub THz satellite downlink, including carrier frequency, OFDM subcarrier spacing, transmit power, and high gain directional receiver antenna profile.

**Status: Partially completed**

What has been completed:

1. The current frequency range is defined as 60 to 400 GHz.
2. The current benchmark uses 256 subcarriers by default.
3. Satellite elevation is sampled from 15 to 80 degrees.
4. SNR is sampled from 20 to 45 dB.
5. These parameters are configurable in the external CSI dataset config.

Evidence:

1. `src/thz_isac/constants.py`
2. `ExternalCSIDatasetConfig` in `src/thz_isac/external_forward_model.py`
3. `scripts/run_real_data_benchmark.py`

What is not completed:

1. There is no full RF link budget.
2. Transmit power is not modeled.
3. Antenna gains and receiver antenna profile are not modeled.
4. OFDM subcarrier spacing is not explicitly defined from total bandwidth.
5. Free space path loss is not currently combined with atmospheric attenuation in the external benchmark.

Next step:

Add a link budget module with transmit power, antenna gain, receiver noise figure, bandwidth, free space path loss, and OFDM subcarrier spacing.

### Task 2.2: Simulate the received wideband CSI, modeling a Line of Sight channel under integrated slant path atmospheric attenuation and Additive White Gaussian Noise.

**Status: Partially completed**

What has been completed:

1. Wideband CSI amplitude spectra are simulated.
2. Atmospheric attenuation is frequency dependent.
3. The attenuation includes gases, PM, H2O and O2 background, elevation dependent slant path scaling, and AWGN.
4. The target labels come from real UCI pollutant records.
5. Gas spectral shapes come from external HITRAN line data.

Evidence:

1. `generate_external_csi_dataset()` in `src/thz_isac/external_forward_model.py`
2. `scripts/run_real_data_benchmark.py`
3. `docs/22_real_data_results.md`

What is not completed:

1. CSI is simulated rather than measured.
2. The channel is amplitude only.
3. Phase, delay, Doppler, antenna pattern, and free space loss are not modeled.
4. Slant path integration is simplified to a scalar path factor.

Next step:

Extend CSI synthesis to include the full link budget, phase response, and a physically calibrated atmospheric attenuation model.

## Task 3: Feature Inversion and Parameter Extraction

### Task 3.1: Design an estimation pipeline to isolate the spectral notches from gas lines from the broad frequency dependent attenuation caused by PM.

**Status: Completed for the current benchmark**

What has been completed:

1. Path normalized spectral features are implemented.
2. Mean removed path normalized features are implemented.
3. HITRAN template projection features are implemented.
4. Hybrid spectrum plus template features are implemented.
5. Template projection separates gas line like components from smoother PM and background components.

Evidence:

1. `src/thz_isac/features.py`
2. `template_projection_features()` in `src/thz_isac/external_forward_model.py`
3. `scripts/run_real_data_benchmark.py`
4. `results/tables/real_data_model_benchmark_summary.csv`

Current result:

The best current feature set is `template_projection`.

What remains:

1. The separation method relies on simplified templates.
2. A physically calibrated absorption model may change which features are optimal.
3. The current method has not been tested on measured CSI.

Next step:

Repeat the feature comparison after replacing normalized HITRAN templates with calibrated absorption coefficients.

### Task 3.2: Formulate and evaluate algorithmic approaches, such as optimization based curve fitting, statistical ratiometric inversion, or machine learning estimators, to extract gas concentration and PM density values from the CSI.

**Status: Completed for the current benchmark**

What has been completed:

1. Linear regression was evaluated.
2. Ridge regression was evaluated.
3. Partial least squares was evaluated.
4. k nearest neighbors was evaluated.
5. Random forest was evaluated.
6. Extra trees was evaluated.
7. A template least squares estimator was evaluated.
8. A focused Ridge alpha sweep was run.

Evidence:

1. `src/thz_isac/estimators.py`
2. `src/thz_isac/physics_estimator.py`
3. `scripts/run_real_data_benchmark.py`
4. `scripts/run_real_ridge_sweep.py`
5. `results/tables/real_data_model_benchmark_summary.csv`
6. `results/tables/real_data_ridge_alpha_sweep.csv`
7. `docs/22_real_data_results.md`

Current best result:

| Feature set | Model | Mean normalized RMSE | Mean R2 | Max target normalized RMSE |
| --- | --- | ---: | ---: | ---: |
| `template_projection` | Ridge, alpha 17.78 | 0.07793 | 0.94523 | 0.09460 |

What remains:

1. Optimization based curve fitting has not been developed as a separate estimator.
2. Statistical ratiometric inversion has not been developed as a separate estimator.
3. The current result is simulation based because CSI is generated from external data and a simplified forward model.

Next step:

Add curve fitting and ratiometric inversion baselines, then compare them against Ridge and template projection under the same external data driven benchmark.

## Task 4: Performance Bounding and Sensitivity Evaluation

### Task 4.1: Derive the analytical lower bound of estimation variance given the link SNR.

**Status: Not completed**

What has been completed:

1. No analytical lower bound has been implemented yet.
2. No CRB or BCRB derivation is currently present in the codebase or paper draft.

Evidence:

1. `docs/22_real_data_results.md` lists CRB or BCRB as a future step.
2. `docs/24_validation_and_repo_state.md` lists estimation bounds as remaining work.

What is not completed:

1. Fisher information matrix derivation.
2. CRB or BCRB implementation.
3. Bound comparison against empirical estimator error.

Next step:

Derive the observation model likelihood for the calibrated CSI forward model, compute the Fisher information matrix, and compare estimator RMSE against the lower bound over SNR.

### Task 4.2: Conduct sensitivity analyses to evaluate estimation error and lower bounds as a function of changing satellite elevation angles and varying atmospheric noise levels.

**Status: Partially completed**

What has been completed:

1. A toy SNR sweep exists for early engineering validation.
2. The external data benchmark samples SNR and satellite elevation ranges.
3. The external dataset metadata stores elevation, SNR, and path factor.

Evidence:

1. `scripts/run_snr_sweep.py`
2. `scripts/run_real_data_benchmark.py`
3. `data/processed/real_data_csi/real_data_csi_metadata.csv.gz`, generated locally and ignored by Git

What is not completed:

1. There is no systematic external data driven SNR sweep.
2. There is no systematic elevation sweep.
3. Lower bounds are not computed, so sensitivity cannot yet include bound comparison.
4. Atmospheric noise variation is not modeled beyond AWGN level.

Next step:

Add `scripts/run_real_sensitivity_sweep.py` to sweep SNR, elevation, bandwidth, and subcarrier count using the external data pipeline, then add lower bounds after Task 4.1 is implemented.

### Task 4.3: Quantify the exact parts per million and mass density detection floors of the developed estimator to verify compliance with environmental sensing standards.

**Status: Not completed**

What has been completed:

1. Regression error metrics are available for pollutant mass concentration targets.
2. Results are reported for CO, O3, SO2, NO2, PM2.5, and PM10.

Evidence:

1. `results/tables/real_data_model_benchmark_metrics.csv`
2. `results/tables/real_data_ridge_alpha_sweep.csv`
3. `docs/22_real_data_results.md`

What is not completed:

1. Detection floors are not calculated.
2. Gas results are currently handled in mass concentration units from the UCI dataset, not converted to ppm detection floors.
3. Environmental sensing standards are not mapped to target thresholds.
4. Compliance is not verified.

Next step:

Define target standards, convert gas concentration units where needed, estimate detection floors from calibrated sensitivity curves, and compare those floors with environmental threshold requirements.

## Final Assessment

The project currently has a defensible external data driven benchmark and an IEEE style draft. The strongest completed area is Task 3, especially feature inversion and machine learning estimation. Tasks 1 and 2 have working first versions but still need physically calibrated atmospheric and link models. Task 4 remains the largest open block because analytical bounds, sensitivity sweeps, and detection floors are not yet implemented.
