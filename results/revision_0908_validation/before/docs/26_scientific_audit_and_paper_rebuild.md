# Scientific Audit and IEEE Paper Rebuild Record

> **Historical audit snapshot:** This file records the audit that invalidated the former two page manuscript and `0.07793` headline. The current ten page paper, final evidence classes, and complete provenance boundary are recorded in `paper/main.tex`, `docs/34_multi_method_information_floor_study.md`, and `docs/35_data_provenance_and_synthetic_evidence_audit.md`.

## Record Metadata

- Audit date: 2026-07-15
- Project: THz ISAC atmospheric monitoring
- Audited manuscript: `paper/main.tex`
- Audited PDF: `paper/build/main.pdf`
- Audited code: the external data acquisition, forward model, feature, estimator, benchmark, and Ridge sweep paths under `scripts/` and `src/thz_isac/`
- Audited local literature: all seven PDFs under `sources/` and the proposal under `references/proposals/`
- Audit mode: scientific and reproducibility review, followed by an online check of primary source records
- Change scope: this Markdown record only

## Executive Decision

The current repository contains a working semi-synthetic engineering pipeline, real external concentration records, real spectroscopic line parameters, deterministic benchmark outputs, and a compilable two page IEEE style manuscript.

The current mean test value of (R^2 = 0.9452) is **not a publication level pollutant sensing result**. It is an **engineering self consistency baseline** for a simulator and inverse model that share the same label scaled templates. It shows that the implemented data flow can encode a pollutant vector into a simplified spectrum and approximately recover that vector under the same assumptions. It does not establish identifiability under an independent physical model, generalization to unseen environmental episodes, performance on measured channel data, or a real detection limit.

The current paper should therefore be treated as an extended engineering note. A final IEEE paper requires a leakage safe evaluation protocol, calibrated atmospheric and link physics, independent forward and inverse models, sensitivity analysis, estimation bounds, detection floors, and measured link validation or an explicit semi-synthetic scope.

## What Was Checked

### Manuscript and rendering

1. The title, abstract, claims, equations, method description, result table, figures, limitations, conclusion, and bibliography in `paper/main.tex`.
2. The two rendered pages in `paper/build/main.pdf` and the existing page images in `paper/build/`.
3. Page count, paper size, embedded fonts, figure legibility, equation fit, and reference visibility.

### Data and provenance

1. The UCI Beijing Multi-Site Air Quality download and cleaning path in `scripts/download_external_data.py`.
2. The local raw archive, clean table, 50,000 row model sample, and 20,000 row benchmark sample.
3. HITRAN line downloads for CO, O3, SO2, NO2, H2O, and O2.
4. Molecule IDs, isotopologue IDs, frequency conversion, line counts, and processed file hashes.
5. The distinction between real labels and simulated CSI.

### Scientific implementation

1. HITRAN template construction in `src/thz_isac/hitran_templates.py`.
2. PM trend construction, path scaling, nuisance background, and noise injection in `src/thz_isac/external_forward_model.py`.
3. Template projection and direct template least squares.
4. The benchmark model zoo and metric calculations.
5. The random train and test split, model selection path, Ridge alpha sweep, and normalization procedure.
6. Target correlations, spectral design conditioning, timestamp overlap, and nonphysical predictions.

### Literature and citations

1. The scope and publication metadata of each local PDF.
2. Whether each paper supports the claim for which it is used.
3. DOI and primary record availability for the IEEE papers.
4. Official HITRAN2024, HAPI, UCI, and arXiv records available online on 2026-07-15.

## Why This Audit Was Necessary

The proposal is about estimation limits of atmospheric monitoring from sub-THz non-terrestrial links. A high regression score can be misleading when the same forward templates, label based scaling, nuisance assumptions, and path normalization are known to the inverse estimator. The audit therefore separated four questions:

1. Does the software pipeline execute and produce deterministic artifacts?
2. Does the current experiment constitute a valid held out machine learning evaluation?
3. Does the forward model represent physically calibrated satellite CSI?
4. Do the reported metrics support real atmospheric sensing or only simulator self consistency?

This separation is essential before investing in a larger IEEE manuscript or making claims about practical detection capability.

## Confirmed Working Items

### External data acquisition

1. The UCI archive downloads and expands successfully.
2. The cleaner retains 383,585 complete rows from 12 stations after removing rows with missing required fields.
3. The project stores a deterministic 50,000 row sample using random seed 7.
4. The official UCI record confirms 420,768 original hourly observations, 12 stations, the March 2013 to February 2017 period, missing values, and pollutant units of micrograms per cubic metre.
5. The UCI dataset DOI in the manuscript is correct.

### Spectroscopic data

1. The local processed HITRAN table contains 9,340 line records between 60 and 400 GHz.
2. The wavenumber conversion, 2.001 to 13.343 inverse centimetres, is numerically correct.
3. The processed table contains line position, line intensity, Einstein A coefficient, air and self broadening, lower state energy, temperature exponent, and pressure shift.
4. The current download uses the main isotopologue for each molecule, as stated in the manuscript.
5. Local line counts are:

| Molecule | Role | Line count |
| --- | --- | ---: |
| CO | target | 15 |
| O3 | target | 1,301 |
| SO2 | target | 6,406 |
| NO2 | target | 1,536 |
| H2O | nuisance background | 37 |
| O2 | nuisance background | 45 |

### Engineering pipeline

1. The external data benchmark uses a fixed random seed and writes its configuration, metrics, summaries, predictions, metadata, frequency grid, and figures.
2. The feature and estimator pipeline runs for linear regression, Ridge, partial least squares, nearest neighbours, random forest, extra trees, and direct template least squares.
3. The selected benchmark result can be reproduced from the checked local artifacts.
4. The focused Ridge sweep confirms that the selected development result is numerically flat over a broad range of alpha values.
5. The paper states that CSI is simulated and does not claim field validation. This limitation is correct and must remain prominent.

### Paper build

1. `paper/main.tex` compiles under the recorded Tectonic command.
2. The resulting PDF has two US Letter pages.
3. Equations, the table, figures, and references are visible with no clipping or overlap.
4. All PDF fonts are embedded.

## Classification of the Existing 0.945 Result

### Correct classification

The result must be described as follows:

> In a semi-synthetic engineering self consistency benchmark, in which real UCI concentration vectors were encoded using normalized HITRAN derived templates and recovered with features built from the same template design, template projection followed by Ridge regression achieved mean (R^2 = 0.9452) and mean 5th to 95th percentile normalized RMSE of 0.0779 on one random development split.

### Claims that the result does not support

The result does not demonstrate:

1. Recovery from measured channel state information.
2. Generalization to an unseen station, year, pollution episode, city, or atmospheric column.
3. A calibrated relationship between surface concentration and path integrated absorption.
4. A physically valid particulate matter scattering coefficient.
5. A realistic satellite link budget or OFDM waveform.
6. Robustness to pressure, temperature, humidity, line parameter, gain, phase, Doppler, multipath, or hardware mismatch.
7. A pollutant detection floor, Cramer-Rao bound, or environmental standards compliance.

### Reproduced per-target development metrics

All concentration errors below are in micrograms per cubic metre. Normalized RMSE uses the full generated dataset's 5th to 95th percentile range, which is itself a protocol limitation.

| Target | MAE | RMSE | Normalized RMSE | (R^2) |
| --- | ---: | ---: | ---: | ---: |
| CO | 172.8477 | 265.8633 | 0.0806 | 0.9474 |
| O3 | 8.2483 | 12.4223 | 0.0710 | 0.9512 |
| SO2 | 3.6546 | 5.4869 | 0.0946 | 0.9285 |
| NO2 | 3.8650 | 5.9365 | 0.0540 | 0.9721 |
| PM2.5 | 14.5690 | 22.3290 | 0.0942 | 0.9198 |
| PM10 | 12.7001 | 19.7717 | 0.0732 | 0.9523 |

The improvement over path normalized spectra is 0.00173 absolute mean normalized RMSE, approximately 2.18 percent relative. No repeated split, confidence interval, or paired significance analysis currently establishes that this difference is stable.

## Failed or Invalid Scientific Claims

### 1. The test set is used for model selection

`scripts/run_real_data_benchmark.py` evaluates the model zoo on the test split, sorts the test metrics, and selects the first row as the best configuration. The broad run produces 45 completed configurations. `scripts/run_real_ridge_sweep.py` then evaluates 25 alpha values for each of three feature sets on the same deterministic split, adding 75 development comparisons.

There is no separate validation set and no nested cross validation. Therefore, the terms "best test performance" and "held out test" are invalid as final evaluation language. The current partition is a development split.

### 2. The random split does not test temporal or spatial generalization

The 20,000 generated records use a random 75/25 split. Audit measurements show:

| Check | Result |
| --- | ---: |
| Test rows | 5,000 |
| Test rows with an exact timestamp also present in training | 33.52% |
| Test dates represented in training | 100% |
| Stations represented in both partitions | 12 of 12 |

This protocol permits the same regional pollution episode to occur on both sides of the split. A year blocked and station blocked evaluation is required.

### 3. Full dataset target values influence the simulator and metric scale

The forward model computes each target's 95th percentile before splitting and uses it to set the attenuation per concentration unit. The metric code also computes the 5th to 95th percentile normalization range from all 20,000 generated labels. Test labels therefore influence both signal construction and metric normalization.

Data based preprocessing must be fitted on training data only. Preferably, signal scaling must come from physical absorption or scattering coefficients rather than label quantiles.

### 4. Forward and inverse models share the same design

The forward model creates each spectrum as a linear combination of target templates. `template_projection_features()` constructs a matrix from the same per-unit templates and applies its pseudoinverse. This is an inverse crime: the estimator is given the exact basis used by the generator.

The final benchmark must generate observations with a higher fidelity independent model and invert them using a deliberately mismatched lower fidelity model.

### 5. Particulate matter is not identifiable in the current design

The PM2.5 and PM10 templates use powers 4.0 and 3.2 and have correlation 0.996. The six target template design has condition number approximately 200.4. Direct template least squares produces (R^2=-0.942) for PM2.5 and (R^2=-0.059) for PM10, while Ridge produces 0.920 and 0.952.

The rise is consistent with Ridge exploiting correlations in the Beijing labels rather than independently resolving two PM scattering signatures. Relevant target correlations include:

| Pair | Pearson correlation |
| --- | ---: |
| PM2.5 and PM10 | 0.888 |
| CO and PM2.5 | 0.790 |
| CO and PM10 | 0.706 |
| NO2 and PM2.5 | 0.673 |
| NO2 and PM10 | 0.659 |

The current experiment cannot support a claim of independent PM2.5 and PM10 retrieval.

### 6. Gas sensitivity is arbitrarily equalized

Each gas is assigned a 0.34 dB peak contribution at its observed 95th percentile. Per-species template normalization discards absolute differences in HITRAN line strengths and abundance sensitivity. The experiment therefore makes each gas similarly observable by design.

### 7. The PM model is not a calibrated Rayleigh model

The current PM trends omit particle size distributions, complex refractive index, density, shape, humidity growth, and conversion between mass concentration and particle number. PM10 uses an (f^{3.2}) trend, which is not the Rayleigh (f^4) scattering law. The term "Rayleigh type" is acceptable only as a disclosure that the trend is heuristic, not as a physical validation statement.

### 8. Surface records are not atmospheric column densities

The UCI values are surface mass concentrations at urban monitoring stations. The simulator treats each value as if it scales a 12 km slant path uniformly. It does not convert gas mass concentration to mixing ratio or molecular number density, and it does not specify vertical pollutant profiles. This is a major mismatch between the real records and the satellite path interpretation.

### 9. Water vapour and oxygen nuisance terms are fixed

H2O and O2 are included as a fixed 0.08 dB nuisance background. The available UCI temperature, pressure, and dew point fields are not used to vary humidity, broadening, or path absorption. This removes a principal confounder that a real inversion must handle.

### 10. The noise is not a physical CSI AWGN model

The implementation adds independent Gaussian noise directly in dB with standard deviation (1 / \sqrt{10^{\mathrm{SNR}/10}}). Complex receiver noise should be applied to complex channel samples after the link budget, followed by channel estimation and amplitude conversion. The current dB noise is an engineering perturbation only.

### 11. The simulated link is not yet an NTN link budget

The external benchmark omits satellite range, free space path loss, transmit power, antenna patterns and gains, receiver bandwidth, noise figure, phase, Doppler, oscillator error, atmospheric emission, and multipath. The frequency grid contains 256 points over 340 GHz, equivalent to 1.33 GHz spacing. It should be called a sampled spectral grid, not a deployable contiguous OFDM waveform.

### 12. Some estimates are physically impossible

The selected Ridge estimator is unconstrained and returns negative concentrations:

| Target | Negative prediction rate | Minimum prediction |
| --- | ---: | ---: |
| CO | 1.70% | -1279.55 |
| O3 | 7.04% | -52.77 |
| SO2 | 8.82% | -25.53 |
| NO2 | 0.74% | -17.48 |
| PM2.5 | 3.36% | -28.28 |
| PM10 | 0.90% | -26.76 |

The final estimator comparison must include nonnegative least squares, constrained optimization, or an appropriate positive target transform, and it must report constraint violation rates.

## Real Data Provenance

### UCI Beijing Multi-Site Air Quality

- Primary record: [UCI Beijing Multi-Site Air Quality](https://archive.ics.uci.edu/dataset/501/beijingmultisiteairqualitydata)
- Dataset DOI: [10.24432/C5RK5G](https://doi.org/10.24432/C5RK5G)
- Creator citation: S. Chen, "Beijing Multi-Site Air Quality," UCI Machine Learning Repository, 2017.
- Original observations: 420,768 hourly rows.
- Period: 2013-03-01 through 2017-02-28.
- Stations: 12.
- Project complete-case rows: 383,585.
- Project deterministic model sample: 50,000 rows, seed 7.
- Current benchmark sample: 20,000 rows, seed 7.
- Pollutant units: micrograms per cubic metre for PM2.5, PM10, SO2, NO2, CO, and O3.
- Scientific status: real measured surface concentration labels and meteorological records.
- Important limitation: no measured THz or sub-THz CSI is synchronized with these labels.

### HITRAN

- Primary database: [HITRANonline](https://hitran.org/)
- Official citation policy: [HITRAN citation policy](https://hitran.org/citepolicy/)
- Official edition record: [HITRAN publications](https://hitran.org/docs/hitran-papers/)
- HAPI record: [HITRAN Application Programming Interface](https://hitran.org/hapi/)
- Local query band: 60 to 400 GHz.
- Local query species: CO, O3, SO2, NO2, H2O, and O2.
- Local isotopologues: main isotopologue only.
- Local processed line count: 9,340.
- Local creation date: 2026-07-06.
- Scientific status: real spectroscopic line parameters.
- Important limitation: the simulator uses normalized line templates, not calibrated absorption coefficients.

The official HITRAN site states that data served in 2026 correspond to HITRAN2024 and that updates may be applied to that edition. The local files were created after HITRAN2024 became current, so HITRAN2024 is the most likely edition. This is an inference because the local acquisition summary does not store an edition identifier or remote update revision. Future downloads must record the edition, access timestamp, HAPI version, query parameters, and source response hash.

### Local artifact hashes

SHA256 hashes recorded on 2026-07-15:

| Artifact | SHA256 |
| --- | --- |
| `data/raw/air_quality/beijing_multi_site_air_quality_data.zip` | `B04DA438B2F331AC0FFD45AEBDFEC0D20D2367FEB5F6948C4B1F7CE1191E33C4` |
| `data/processed/air_quality/beijing_air_quality_clean.csv.gz` | `39D6CEEE9D66824BCCF68553293A490199084299174496DB51FAC42BCBC543F0` |
| `data/processed/air_quality/beijing_air_quality_model_sample.csv.gz` | `70E3B938F44B2FB43206EABC3B6EF28CF9A848121301DA05A8D9EE856B596396` |
| `data/processed/hitran/hitran_60_400GHz_lines.csv` | `7D063E4036DA3D3E5B75128FF954BC9D80159E63D1831C4BBF75A99BFDAEDED8` |
| `results/tables/real_data_model_benchmark_summary.csv` | `0ED21E20DE017ABF72B61B22C5D5E6B25A44D318D265DB2EC5255A2B06B74C49` |
| `results/tables/real_data_best_predictions.csv` | `DE3CA9B0E5250EEF2DA8EC8D1AF83830C7C827CC58A2287E945962C7E2FCEA0E` |
| `paper/main.tex` | `C608FA478911FE00247112A50F8B44BD0FA983E3E09239DB592D7D37DEAB5598` |
| `paper/build/main.pdf` | `CB2102B5391A1341877D7EBCF89AB60B433D9744329565F98C5267B6E27CC000` |

The raw and processed data directories are ignored by Git. Reproducing the paper from a fresh clone therefore requires rerunning acquisition and verifying the resulting hashes or publishing a versioned data manifest.

## Exact Reproducibility Commands

Run all commands from the repository root.

### Recorded environment

```text
Python 3.12.10
numpy 2.4.4
pandas 2.2.3
scikit-learn 1.8.0
matplotlib 3.9.0
hitran-api 1.3.0.0
ucimlrepo 0.0.7
```

`requirements.txt` currently has no version pins. A lock file or fully pinned environment is required before final publication.

### Acquire external data

```powershell
python scripts/download_external_data.py
```

### Reproduce the current engineering self consistency baseline

```powershell
python scripts/run_real_data_benchmark.py --samples 20000 --subcarriers 256 --seed 7
python scripts/run_real_ridge_sweep.py --samples 20000 --subcarriers 256 --seed 7
```

### Run repository tests

```powershell
python -m pytest -q
```

### Rebuild the current IEEE draft

```powershell
python C:\Users\guill\.codex\plugins\cache\openai-bundled\latex\0.2.4\scripts\compile_latex.py C:\Research\THz_ISAC_atmospheric_monitoring\paper\main.tex --compiler tectonic --output-directory C:\Research\THz_ISAC_atmospheric_monitoring\paper\build --json
```

### Verify the split overlap

```powershell
@'
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

root = Path.cwd()
sys.path.insert(0, str(root / "src"))
from thz_isac.external_forward_model import ExternalCSIDatasetConfig, generate_external_csi_dataset
from thz_isac.hitran_templates import load_hitran_lines

pollution = pd.read_csv(root / "data/processed/air_quality/beijing_air_quality_model_sample.csv.gz")
lines = load_hitran_lines(root / "data/processed/hitran/hitran_60_400GHz_lines.csv")
dataset = generate_external_csi_dataset(
    pollution,
    lines,
    ExternalCSIDatasetConfig(n_samples=20000, n_subcarriers=256, random_seed=7),
)
train_idx, test_idx = train_test_split(
    np.arange(len(dataset.y)), test_size=0.25, random_state=7
)
timestamp = pd.to_datetime(dataset.metadata["datetime"])
day = timestamp.dt.date
train_timestamp = set(timestamp.iloc[train_idx])
train_day = set(day.iloc[train_idx])
print("test_rows", len(test_idx))
print("test_rows_with_timestamp_in_train", timestamp.iloc[test_idx].isin(train_timestamp).mean())
print("test_rows_with_date_in_train", day.iloc[test_idx].isin(train_day).mean())
print("train_stations", sorted(dataset.metadata.iloc[train_idx]["station"].unique()))
print("test_stations", sorted(dataset.metadata.iloc[test_idx]["station"].unique()))
'@ | python -
```

### Verify design conditioning and PM template ambiguity

```powershell
@'
from pathlib import Path
import sys
import numpy as np
import pandas as pd

root = Path.cwd()
sys.path.insert(0, str(root / "src"))
from thz_isac.external_forward_model import ExternalCSIDatasetConfig, generate_external_csi_dataset
from thz_isac.hitran_templates import load_hitran_lines

pollution = pd.read_csv(root / "data/processed/air_quality/beijing_air_quality_model_sample.csv.gz")
lines = load_hitran_lines(root / "data/processed/hitran/hitran_60_400GHz_lines.csv")
dataset = generate_external_csi_dataset(
    pollution,
    lines,
    ExternalCSIDatasetConfig(n_samples=20000, n_subcarriers=256, random_seed=7),
)
singular_values = np.linalg.svd(dataset.design_per_unit, compute_uv=False)
print("condition_number", singular_values[0] / singular_values[-1])
print("template_correlation")
print(np.round(np.corrcoef(dataset.design_per_unit.T), 3))
print("target_correlation")
print(dataset.metadata[dataset.target_names].corr().round(3))
'@ | python -
```

### Verify negative predictions

```powershell
@'
import pandas as pd

predictions = pd.read_csv("results/tables/real_data_best_predictions.csv")
for column in [name for name in predictions if name.startswith("pred_")]:
    values = predictions[column]
    print(column, "negative_fraction", (values < 0).mean(), "minimum", values.min())
'@ | python -
```

### Verify hashes

```powershell
Get-FileHash -Algorithm SHA256 `
  data\raw\air_quality\beijing_multi_site_air_quality_data.zip, `
  data\processed\air_quality\beijing_air_quality_clean.csv.gz, `
  data\processed\air_quality\beijing_air_quality_model_sample.csv.gz, `
  data\processed\hitran\hitran_60_400GHz_lines.csv, `
  results\tables\real_data_model_benchmark_summary.csv, `
  results\tables\real_data_best_predictions.csv, `
  paper\main.tex, `
  paper\build\main.pdf
```

## Critical Limitations to Carry Into Every Paper Draft

1. The channel amplitudes are simulated, not measured.
2. The target concentrations are measured at ground stations, not integrated along a satellite path.
3. HITRAN line parameters are real, but the current spectra are normalized templates rather than absorption coefficients.
4. The generator and feature projector share the same spectral basis.
5. Gas sensitivity is set by arbitrary equal peak loss and label quantiles.
6. PM2.5 and PM10 are represented by strongly collinear heuristic trends.
7. H2O and O2 background terms do not vary with the recorded meteorology.
8. Atmospheric pressure, temperature, density, and humidity are not integrated by layer.
9. The 12 km cosecant path approximation omits Earth curvature and species profiles.
10. The model omits the satellite link budget and complex CSI estimation process.
11. Random record splitting does not test temporal, station, city, or atmospheric regime transfer.
12. The same test split is used to compare models and select Ridge alpha.
13. Metric normalization uses the full generated label table.
14. The selected unconstrained estimator returns negative concentrations.
15. No uncertainty interval, repeated split, calibration result, sensitivity surface, CRB, BCRB, or detection floor is available.
16. The dependency file is not pinned and the external data are ignored by Git.

## Revised Paper Thesis

### Current defensible thesis

The current work demonstrates a reproducible semi-synthetic engineering pipeline that combines real surface pollution records with real spectroscopic line parameters to test signal processing and inversion code. It identifies template projection as a useful development baseline within a self-consistent simulator and exposes the identifiability and evaluation problems that must be solved before physical claims are possible.

### Target thesis for the final IEEE paper

The final paper should investigate the estimation limits of pollutant related molecular absorption and particulate attenuation from realistic multi-band NTN channel observations. It should combine calibrated line by line absorption, physically grounded aerosol scattering, stratified slant path integration, a complete link and channel estimation model, leakage safe real environmental data splits, independent forward and inverse models, and CRB or BCRB analysis. The central result should be error and detection floor versus SNR, elevation, bandwidth, frequency window, and atmospheric uncertainty, with measured link validation where available.

### Recommended title direction

`Estimation Limits of Semi-Synthetic Atmospheric Sensing from Sub-THz NTN Channel Measurements Using HITRAN and Real Air-Quality Records`

Use "measurements" only after measured channel data are introduced. Until then, use "simulated channel amplitudes" or "semi-synthetic channel signatures."

## Required Experiments Before Paper Finalization

### Priority 0: Valid evaluation protocol

1. Create immutable sample identifiers and split manifests.
2. Use chronological partitions, for example training years, a validation year, and a final untouched test interval.
3. Add leave-one-station-out evaluation and, if another city is acquired, leave-one-city-out evaluation.
4. Fit every scaler, percentile, projection calibration, and hyperparameter on training or validation data only.
5. Use nested grouped cross validation for model and alpha selection.
6. Repeat the complete protocol across seeds and report confidence intervals.
7. Preserve the final test set until model and paper decisions are frozen.

### Priority 1: Calibrated molecular absorption

1. Generate absorption coefficients with HAPI using the exact HITRAN edition.
2. Compare Lorentz, Voigt, and any selected speed dependent profile under documented pressure and temperature conditions.
3. Convert gas mass concentrations into mixing ratio and number density with explicit molecular weights and atmospheric state.
4. Use a stratified atmosphere with species density, pressure, temperature, and humidity by altitude.
5. Integrate optical depth along an Earth geometry aware slant path.
6. Include isotopologue and line parameter uncertainty.
7. Validate absorption against an independent implementation or published reference curves.

### Priority 2: Physically grounded particulate matter

1. Define particle size distributions for PM2.5 and PM10.
2. Specify complex refractive index, material density, shape assumptions, and humidity growth.
3. Convert mass concentration to number distribution.
4. Apply Rayleigh only where particle diameter is sufficiently smaller than wavelength and use Mie treatment outside that regime.
5. Quantify whether PM2.5 and PM10 are distinguishable in each frequency window.
6. If they remain unidentifiable, estimate total aerosol loading or a lower dimensional particle parameter instead of two nominal PM labels.

### Priority 3: NTN and CSI signal model

1. Select realistic disjoint communication and sensing windows rather than one continuous 60 to 400 GHz waveform.
2. Add orbit altitude, slant range, free space loss, transmit power, antenna gain and beam pattern, receiver noise figure, bandwidth, and atmospheric emission.
3. Define an implementable OFDM or multitone grid with subcarrier spacing and pilot allocation.
4. Generate complex frequency response, add complex AWGN, and estimate CSI through pilots.
5. Add phase noise, Doppler, gain uncertainty, calibration error, and pointing error in controlled ablations.
6. Separate deterministic path loss from the differential spectral observables used for sensing.

### Priority 4: Independent inversion and identifiability

1. Generate data with a higher fidelity model than the estimator uses.
2. Add line position, intensity, width, atmospheric profile, and instrument mismatch between generator and inverse model.
3. Compare nonnegative least squares, constrained nonlinear curve fitting, ratiometric inversion, Ridge, partial least squares, and nonlinear models.
4. Compute singular values, condition number, variance inflation, Fisher information, and parameter correlations.
5. Run gas-only, PM-only, nuisance-only, leave-one-template-out, and shuffled-correlation ablations.
6. Create counterfactual target combinations that break Beijing co-pollutant correlations.
7. Report nonphysical prediction and constraint activation rates.

### Priority 5: Bounds, sensitivity, and detection floors

1. Derive the observation likelihood and Fisher information matrix.
2. Compute CRB and, if environmental priors are used, BCRB.
3. Compare empirical estimator variance with the bound.
4. Sweep SNR, elevation, selected windows, bandwidth, subcarrier count, integration time, and pilot fraction.
5. Sweep pressure, temperature, humidity, vertical profiles, line uncertainty, aerosol model, and calibration error.
6. Define gas detection floors in mixing ratio and mass concentration and PM floors in mass concentration.
7. Compare floors with named environmental monitoring thresholds only after unit conversion and calibration are validated.

### Priority 6: Real channel evidence

1. Acquire synchronized measured attenuation or CSI and environmental labels if a suitable sub-THz dataset exists.
2. If direct pollutant CSI is unavailable, perform a controlled laboratory or channel sounder experiment with known gas path length and concentration.
3. Use the rain paper's real satellite link validation as a methodological reference, not as direct sub-THz pollutant evidence.
4. Keep a strict label of semi-synthetic evidence until measured channel observations enter the evaluation.

## IEEE Paper Rebuild Plan

The existing two page manuscript is a useful outline, not a final paper. Rebuild it after the Priority 0 through Priority 5 results exist.

### Required structure

1. Introduction with the exact research gap, scope, and three to five verifiable contributions.
2. Related work separated into differential absorption sensing, THz atmospheric propagation, opportunistic NTN sensing, and estimation bounds.
3. System and signal model with units, geometry, link budget, and observation likelihood.
4. External data and provenance with download dates, hashes, licences, and split policy.
5. Calibrated atmospheric and aerosol model.
6. Inversion methods and estimation bounds.
7. Experimental protocol, baselines, ablations, and statistical analysis.
8. Results by target and by operating condition.
9. Measured data validation or an explicit semi-synthetic validation section.
10. Limitations, reproducibility, and ethical claim boundaries.
11. Conclusion tied only to demonstrated evidence.

### Figures and tables to replace or add

1. Replace the current near-tied model ranking with a pipeline and system geometry figure.
2. Add calibrated absorption and scattering spectra with selected sensing windows.
3. Add an identifiability plot showing singular values or parameter correlation.
4. Add RMSE and bound versus SNR and elevation.
5. Add robustness surfaces for atmospheric and model mismatch.
6. Replace code style scatter labels such as `PM2_5_ug_m3` with publication notation and units.
7. Add uncertainty intervals and a zero lower bound to concentration plots.
8. Replace duplicate Ridge rows in the main table with per-target physical error, normalized error, confidence interval, and bound gap.

## Verified Primary Citations

Verification date: 2026-07-15. Local PDF metadata and text were checked first. Online links below point to DOI resolvers, official repositories, official database records, or arXiv primary records.

### Core data and spectroscopy

1. I. E. Gordon, L. S. Rothman, R. J. Hargreaves, F. M. Gomez, T. Bertin, C. Hill, et al., "The HITRAN2024 Molecular Spectroscopic Database," *Journal of Quantitative Spectroscopy and Radiative Transfer*, vol. 353, Art. 109807, 2026. [DOI 10.1016/j.jqsrt.2026.109807](https://doi.org/10.1016/j.jqsrt.2026.109807). The [official HITRAN citation policy](https://hitran.org/citepolicy/) requires citation of the database edition used.
2. R. V. Kochanov, I. E. Gordon, L. S. Rothman, P. Wcislo, C. Hill, and J. S. Wilzewski, "HITRAN Application Programming Interface: A Comprehensive Approach to Working With Spectroscopic Data," *Journal of Quantitative Spectroscopy and Radiative Transfer*, vol. 177, pp. 15-30, 2016. [DOI 10.1016/j.jqsrt.2016.03.005](https://doi.org/10.1016/j.jqsrt.2016.03.005). Also listed by the [official HAPI page](https://hitran.org/hapi/).
3. S. Chen, "Beijing Multi-Site Air Quality," UCI Machine Learning Repository, 2017. [DOI 10.24432/C5RK5G](https://doi.org/10.24432/C5RK5G). [Official UCI dataset record](https://archive.ics.uci.edu/dataset/501/beijingmultisiteairqualitydata).

### Directly relevant propagation and ISAC sources

1. S. Aliaga, M. Lanzetti, V. Petrov, A. Vizziello, P. Gamba, and J. M. Jornet, "Analysis of Integrated Differential Absorption Radar and Subterahertz Satellite Communications Beyond 6G," *IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing*, vol. 17, pp. 19243-19259, 2024. [DOI 10.1109/JSTARS.2024.3480816](https://doi.org/10.1109/JSTARS.2024.3480816). Local file: `sources/THz_ISAC_Aliaga_2024_DAR_SubTHz_Satellite_Beyond_6G.pdf`.
2. Z. Yang, W. Gao, and C. Han, "A Universal Attenuation Model of Terahertz Wave in Space-Air-Ground Channel Medium," *IEEE Open Journal of the Communications Society*, vol. 5, pp. 2333-2342, 2024. [DOI 10.1109/OJCOMS.2024.3386759](https://doi.org/10.1109/OJCOMS.2024.3386759). Local file: `sources/THz_ISAC_Yang_2024_Universal_Attenuation_Model.pdf`.
3. H. Dong and O. B. Akan, "Martian Dust Storm Detection With THz Opportunistic Integrated Sensing and Communication in the Internet of Space (IoS)," *IEEE Internet of Things Journal*, vol. 13, no. 1, pp. 582-594, 2026. [DOI 10.1109/JIOT.2025.3624590](https://doi.org/10.1109/JIOT.2025.3624590). The local file is an earlier arXiv manuscript; final journal metadata is recorded in the local proposal.
4. H. Dong and O. B. Akan, "DebriSense: THz-Based Integrated Sensing and Communications (ISAC) for Debris Detection and Classification in the Internet of Space (IoS)," *IEEE Transactions on Wireless Communications*, vol. 24, no. 11, pp. 9282-9295, 2025. [DOI 10.1109/TWC.2025.3572276](https://doi.org/10.1109/TWC.2025.3572276). [University of Cambridge accepted record](https://www.repository.cam.ac.uk/items/c3bf1ff8-785c-4a71-9e30-802692f3b969).

### Estimation bounds and adjacent NTN sensing

1. H. Dong, H. Wang, H. Cai, O. T. Baydas, and O. B. Akan, "Rain Rate Estimation Bounds and Weather-Adaptive Pilot Allocation for LEO Satellite ISAC," arXiv:2604.10830, 2026. [Primary arXiv record](https://arxiv.org/abs/2604.10830). This is a relevant CRB and BCRB methodology source, but its Ku band rain results must not be numerically transferred to sub-THz pollutants.
2. H. Wang, H. Dong, H. Cai, and O. B. Akan, "Environment-to-Link ISAC with Space-Weather Sensing for Ka-Band LEO Downlinks," arXiv:2601.00820. [Primary arXiv record](https://arxiv.org/abs/2601.00820). This supports same-link environmental sensing and robust time blocked evaluation, not pollutant retrieval.
3. H. Dong and O. B. Akan, "CisLunarSense: Opportunistic ISAC for Debris Detection at the Lunar Gateway," arXiv:2604.10807, 2026. [Primary arXiv record](https://arxiv.org/abs/2604.10807). This is peripheral to atmospheric retrieval and should not displace a more direct source in a short paper.

### Citation scope notes

1. Aliaga et al. support differential absorption sensing of water vapour and joint satellite communication, not direct retrieval of the six current pollutants.
2. Yang et al. support the need for molecular, Rayleigh, Mie, particle distribution, and altitude dependent modeling. They do not validate the current (f^{3.2}) PM10 trend.
3. The Martian dust paper supports opportunistic THz environmental sensing in simulation and explicitly depends on dust particle properties. It is not Earth field validation.
4. DebriSense and CisLunarSense concern debris rather than atmospheric composition.
5. The rain paper provides an estimation bound workflow and real link validation example in a different frequency and target regime.
6. HAPI is the software citation. HITRAN2024 is the required data edition citation. Both are needed.

## Risks

1. The most serious scientific risk is publishing a self consistency score as evidence of real sensing.
2. The strongest numerical risk is PM non-identifiability hidden by target correlations.
3. The strongest data risk is temporal and station overlap across the random split.
4. The strongest physics risk is arbitrary label based attenuation scaling.
5. The strongest reproducibility risk is unpinned dependencies and ignored external data.
6. The strongest paper risk is expanding the current narrative before the evaluation and physics gates are fixed.
7. The strongest scope risk is calling the entire 60 to 400 GHz grid a sub-THz downlink or an OFDM carrier set.

## Next Steps

1. Freeze and test a chronological and station grouped evaluation protocol before running another model comparison.
2. Replace label percentile scaling with calibrated HAPI absorption coefficients and train-only transformations.
3. Decide whether PM2.5 and PM10 are physically distinguishable; otherwise revise the target parameterization.
4. Implement the complete link and complex CSI observation model.
5. Add independent forward and inverse models and controlled mismatch sweeps.
6. Implement constrained physical baselines before higher complexity machine learning.
7. Derive the Fisher information and CRB or BCRB only after the observation model is calibrated.
8. Add real measured channel evidence or retain explicit semi-synthetic language throughout.
9. Rerun all experiments with fixed manifests, environment lock, hashes, repeated grouped splits, and uncertainty intervals.
10. Rebuild the IEEE manuscript only after the critical experiments have passed their acceptance criteria.

## Acceptance Criteria for the Next Paper Draft

The next manuscript may report a final performance result only when all of the following are true:

1. The final test records were never used for feature design, scaling, model selection, or hyperparameter selection.
2. Temporal and station separation is explicit and verified from a saved split manifest.
3. The forward model uses calibrated units and stores all physical parameters.
4. Forward and inverse models are not identical and mismatch robustness is reported.
5. PM identifiability is demonstrated or the PM target is reduced to an identifiable parameter.
6. Results include per-target physical errors, confidence intervals, constraints, and negative prediction rates.
7. SNR, elevation, frequency window, bandwidth, and atmospheric uncertainty sweeps are complete.
8. CRB or BCRB and empirical estimator error are compared under the same observation model.
9. Every external dataset, database edition, source version, licence, access time, and hash is recorded.
10. The title and abstract state whether channel observations are measured or simulated.
