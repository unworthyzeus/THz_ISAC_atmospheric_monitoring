# Validation and Repository State

Updated on 2026 07 15 after the physical feasibility run. Paper compilation and visual inspection remain a separate final gate after the manuscript rewrite.

## What Was Validated

1. The processed UCI table was audited at full size.
2. The local HITRAN Voigt calculation was compared with HAPI for every modeled molecule.
3. The physical feasibility pipeline was run from real UCI and HITRAN inputs through tables and figures.
4. The expanded Ridge validation sweep was rerun after the first grid selected its upper boundary.
5. The complete unit test suite was run.
6. The new physical, audit, and test files were checked with Ruff.
7. The repository state and untracked artifacts were inspected without deleting user files or committing changes.

## Why Validation Was Necessary

The former high regression score was produced by a shared normalized generator and inverse design. The new main conclusion depends instead on calibrated signal magnitudes, declared observation uncertainty, link geometry, and Fisher information. Each layer requires a reproducible check, and simulated observations must remain distinct from measured input data.

## Data Quality Command

```powershell
python scripts/run_data_quality_audit.py --input data/processed/air_quality/beijing_air_quality_clean.csv.gz
```

Result:

1. 383,585 complete case rows and 17 columns.
2. 91.163% complete case retention from 420,768 source rows.
3. 12 stations and 34,821 retained timestamps.
4. No exact duplicates and no duplicate station hour keys.
5. 17,642 PM ordering violations, or 4.599% of retained rows.
6. No dew point above temperature and no nonpositive target values.

The complete audit and its limitations are in `docs/27_data_quality_audit.md`.

## Spectroscopy Validation Command

```powershell
python scripts/validate_physical_spectroscopy.py
```

Result:

1. CO, O3, SO2, NO2, H2O, and O2 all passed.
2. The largest peak relative error against HAPI was below `6.4e-7`.
3. The largest normalized active grid RMSE was below `1.6e-7`.
4. Both acceptance thresholds were `1e-5`.

This checks the local cross section calculation at the UCI median surface condition. It does not validate the vertical profile, particulate matter model, link, or retrieval against measurements.

## Physical Feasibility Command

```powershell
python scripts/run_physical_feasibility.py
```

Result:

1. Physical signature, informative frequency, one and three sigma detection floor, sensitivity, Ridge validation, and estimator metric tables were written under `results/tables/`.
2. Four result figures were written under `results/figures/`.
3. All four gas target columns were identifiable within the declared joint gas CRB.
4. Every reference floor was above its WHO 2021 health guideline scale comparison.
5. Fine and coarse PM signatures were practically nonidentifiable.
6. The expanded Ridge grid selected alpha `100,000` on validation data.
7. Ridge test mean normalized RMSE `0.347443` and mean R2 `-0.08293` were effectively the same as the training period mean baseline at `0.347479` and `-0.08316`.

The observation variance includes an assumed independent residual error of 0.63 dB standard deviation per tone. This value is a borrowed scenario assumption and is not calibrated for this link. The WHO ratios compare one burst CRB values with 8 h or 24 h health guidelines and are not compliance claims.

The sensitivity table also contains an optimistic combined stress test at 15 degrees, 3,000 pilots, zero residual error, 33 dBm, and 256 probes. CO reaches 0.649 times its guideline concentration at one sigma but 1.948 times at three sigma. All other targets remain above their scales. This is not a robust detection or deployment result, but it prevents a universal impossibility interpretation.

## Input Integrity

`results/tables/physical_feasibility_config.json` records:

| Input | SHA256 |
| --- | --- |
| Processed UCI table | `39d6ceee9d66824bccf68553293a490199084299174496db51fac42bcbc543f0` |
| Processed HITRAN table | `7d063e4036da3d3e5b75128ff954bc9d80159e63d1831c4bbf75a99bfdaeded8` |

The manifest also stores row and line counts, UCI median surface conditions, atmosphere and link configuration, observation variance equation, PM diagnostics, WHO scale values and averaging periods, split dates, random seed, selected Ridge alpha, dependency versions, and known limitations.

## Test Suite

Command:

```powershell
python -m pytest tests -q
```

Result:

```text
................................                                         [100%]
32 passed
```

The suite covers the legacy engineering pipeline plus chronological splitting, spectroscopy, the link budget, bounds, complex line of sight channel synthesis, pilot averaging, and clear sky attenuation recovery.

## Static Analysis

The targeted command for the newly added files passed:

```powershell
python -m ruff check scripts/run_data_quality_audit.py scripts/run_physical_feasibility.py scripts/validate_physical_spectroscopy.py src/thz_isac/estimation_bounds.py src/thz_isac/evaluation_protocol.py src/thz_isac/link_budget.py src/thz_isac/physical_spectroscopy.py src/thz_isac/pilot_csi.py tests/test_evaluation_protocol.py tests/test_link_budget_and_bounds.py tests/test_physical_spectroscopy.py tests/test_pilot_csi.py
```

Result:

```text
All checks passed!
```

A repository wide Ruff command still fails with 18 `E402` findings in legacy scripts and `tests/test_synthetic_pipeline.py`. Those files insert the local `src` directory before module imports. The findings are recorded cleanup work and did not cause the test suite to fail.

## Ridge Grid Failure and Correction

The first physical Ridge grid covered alpha `0.01` through `10,000`. The validation optimum was `10,000`, its upper boundary. A boundary optimum does not show that the search brackets the best regularization, so that grid was treated as incomplete.

The rerun extended the grid through `100,000,000`. It selected the internal value `100,000`, with validation mean normalized RMSE `0.348912`. Only after this selection was the originally held out chronological test period first reported. Later diagnostic extensions reuse that period and are explicitly nonconfirmatory.

## Paper Validation Result

The July 6 two page PDF was replaced. The final nine page manuscript now includes optimized probes, the H2O control, native ESA CCI columns, the exact metric audit, ten seed spectral stability, the causal forecast control, and the idealized tenfold sensitivity. It was compiled with:

```powershell
python C:\Users\guill\.codex\plugins\cache\openai-bundled\latex\0.2.4\scripts\compile_latex.py C:\Research\THz_ISAC_atmospheric_monitoring\paper\main.tex --compiler tectonic --output-directory C:\Research\THz_ISAC_atmospheric_monitoring\paper\build --json
```

The command exited successfully with bundled Tectonic after the automatic MiKTeX path failed for lack of a Perl script engine. All nine pages were rendered at 150 pixels per inch and inspected for clipped equations, unreadable tables, incorrect figures, citation defects, and stale claims. The final PDF SHA256 is `6a0478c37c28b1a2484afa2d5e8fd0303c16abbfd032537b52f9bf8a1ed58f5d`. Python PDF parsing confirms nine pages, no encryption, no unresolved references or tool tokens in extracted text, and all used font resources embedded. Full build and visual validation details are in `docs/29_ieee_paper_build_and_visual_validation.md`.

## Repository State

At this checkpoint, the new modules, scripts, tests, documentation, tables, figures, and final paper are working tree changes. No commit or push was performed. The duplicate proposal file `I2R_proposal_THz_ISAC (1).pdf` was already untracked and was preserved. Temporary PDF extraction and rendering files under `tmp/` were removed after final paper inspection without touching user source files.

Raw and processed external datasets remain ignored because the acquisition and preparation scripts regenerate them. Tracked research results should include enough configuration and hashes to identify the exact ignored inputs.

## Remaining Validation Risks

1. No measured paired sub THz CSI is available.
2. Surface UCI records are not vertical pollutant column truth.
3. Pollutant scale heights are assumptions.
4. PM properties and humidity response are not calibrated.
5. The 0.63 dB independent residual per tone value is not calibrated here.
6. The 60 to 400 GHz probes are not one realistic contiguous allocation.
7. HAPI agreement is not independent validation of the underlying HITRAN database.
8. The paper cannot claim compliance from unequal averaging period ratios.
9. The total CO column is forced into a normalized 0 to 20 km profile, so its unknown upper atmosphere distribution remains a model risk.

## Next Steps

1. Resolve or explicitly accept the legacy Ruff import findings.
2. Run the final PDF through the target venue compliance checker before submission.
3. Add independent propagation validation and measured channel evidence.
4. Repeat the study with vertical profile, PM, instrument, and station or time shift uncertainty.

## 2026 07 15 Final RMSE Extension Validation

The three new experiment drivers were rerun from the hashed real UCI and HITRAN inputs. The audit reproduced `0.347443444150840`, the ten seed stability study again rejected both frozen confirmatory candidates, and the causal multilag forecast reproduced `0.1045070875` while remaining a separate ground history task.

Final validation results:

1. `python -m pytest -q`: 111 passed.
2. Ruff over all 34 new Python files: no violations.
3. `py_compile` over the same 34 files: no failures.
4. `git diff --check`: no whitespace errors; only expected LF to CRLF notices.
5. Tectonic: nine page PDF built successfully after the automatic MiKTeX `latexmk` attempt failed because Perl was unavailable.
6. Visual inspection: all nine 150 pixel per inch renders passed for clipping, overlap, blank pages, figures, tables, citations, and column flow.
7. Delivery PDF: 379,308 bytes, SHA256 `6a0478c37c28b1a2484afa2d5e8fd0303c16abbfd032537b52f9bf8a1ed58f5d`, byte identical to `paper/build/main.pdf`.

Operational failures were retained rather than hidden: an undersized five second audit timeout, the unavailable MiKTeX Perl engine, the broken `pdftoppm.cmd` path, missing `pdffonts` and `pdftotext` utilities, and one broad dependency search timeout. Each was followed by a bounded successful path. None changes the scientific result.

## 2026 07 15 Multi Method 0.08 Extension Validation

The final multi method extension adds advanced THz inversion, causal forecasting v2, strict station network reconstruction, single channel repair, and a real measured THz positive control. Numerical artifacts were independently read back and checked against the manuscript headlines.

Final validation results:

1. `python -m pytest tests -q`: 135 passed in 4.30 seconds.
2. Scoped Ruff over all 16 new source, script, and test files: no violations.
3. Python compilation over the same files: no failures.
4. Artifact assertions: advanced THz `0.347466` and `0.239100`, causal `0.095485`, strict spatial `0.088890`, repair `0.074855`, and measured THz `0.199270` all match their generated manifests and tables.
5. `git diff --check`: no whitespace errors; expected LF to CRLF notices only.
6. Tectonic 0.16.9: 10 page IEEE PDF built successfully.
7. Visual inspection: all pages rendered at 150 pixels per inch; no clipping, overlap, blank content page, unreadable table, or broken citation.
8. PDF parsing: 10 letter size pages, no replacement characters or placeholder tokens, and every used font resource embedded.
9. Delivery PDF: 382,220 bytes, SHA256 `38ea364c78f720603b89495b0a355530392b6b9ae7d44920604e59c6fc741674`, byte identical to `paper/build/main.pdf`.

Newly retained operational failures include the initial five minute field calibration timeout, an all training row causal resource failure, two Mendeley HTTP 401 routes before the successful public endpoint, a wrong audit display label, and one malformed output parsing regular expression. Scientific failures and operational failures are separated in `docs/34_multi_method_information_floor_study.md`.
