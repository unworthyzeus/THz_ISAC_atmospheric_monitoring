# Five requested tasks: results, evidence and remaining measurements

Date: 2026-09-23. The user requested all five follow-up areas and confirmed: **use public data and document the remaining measurement needs**. This report supersedes the progress note. The original two-page proposal is [I2R_proposal_THz_ISAC.pdf](../references/proposals/I2R_proposal_THz_ISAC.pdf).

**The computational assessment and deliverables for all five areas are complete. The programme has not demonstrated a calibrated atmospheric VOC/PM sensor or environmental compliance.** Public evidence now includes measured aerosol transmission and an independent published humidity comparison. Neither supplies paired atmospheric pollutant concentrations and radio observations. An unfavorable feasibility result is a completed assessment; it is not successful concentration retrieval.

## What was already done

The project progressed from atmospheric absorption and scattering models through simulated CSI, gas/PM inversion, nuisance-adjusted variance bounds, detection limits and communication resource comparisons. Historical ground-sensor prediction, satellite-column and stronger-species controls have different measurement domains; they do not demonstrate atmospheric VOC/PM radio inversion.

The latest model uses P.835-7 through 100 km, spherical refracted paths, P.676-13 absorption/emission, isotope-specific HITRAN Voigt profiles and full Mie distributions. Acquired spectroscopy contains 34 isotope tables and 31,474 in-band transitions. Beijing weather supplies 521 soundings and four selected seasonal profiles; pollutant height profiles remain assumed. Three isotope requests remain unavailable. [Report 38](38_full_model_completion.md) preserves methods, provenance and failures.

The first thermal quadrature comparison failed at 0.11596%. Finer layers reduced it to 0.00319% under the unchanged 0.1% criterion. [Report 39](39_thermal_convergence_audit.md) preserves the failure, correction and replay. Numerical convergence is not experimental calibration.

| Ideal broad-reference 10 s result | 95%-power detection limit, µg/m³ | ppm | Recall at 1 µg/m³ |
| --- | ---: | ---: | ---: |
| Formaldehyde | 56.21 | 0.04426 | 0.30% |
| Methanol | 131.24 | 0.09685 | 0.20% |
| Acetonitrile | 12.94 | 0.00745 | 0.20% |

These limits assume zero persistent residual/bias, an ideal multiband reference and a 1% family-wise false-positive budget across six outputs. Exact-response controls at the larger limits give 95.16%, 95.40% and 94.92% recall. These are internal simulation checks, not measured sensitivity. The grid attempted 36 configurations; 17 of 18 narrow E-band cases failed the information audit. Enormous PM limits and nonlinear fits at bounds remain negative results.

## 1. Environmental requirements assessment

Implemented and tested a domain/averaging/coverage/calibration/paired-reference gate. [Seven pollutant-period combinations](../results/five_task_closure/environmental_requirement_assessment.csv) separate modeled sensitivity from complete evidence. The gate does not issue legal certification.

[WHO 2021 guidance](https://www.who.int/publications/i/item/9789240034228) gives ambient PM2.5/PM10 daily concentration scales of 15/45 µg/m³ and annual means of 5/15 µg/m³. Daily interpretation requires the annual 99th-percentile context. Modeled 10 s limits exceed the daily scales by approximately **32.36 million times for fine PM and 2.45 million times for PM10**. Even optimistic continuous independent-noise daily extrapolation yields formal limits of 5.22 million and 1.19 million µg/m³. Such values diagnose missing information, not a validated high-concentration sensing range.

The [WHO formaldehyde reference](https://www.ncbi.nlm.nih.gov/books/NBK138711/) is **100 µg/m³ over 30 minutes indoors**. Outdoor slant measurements have the wrong domain even with a lower modeled limit. The ideal high-elevation pass covers only 139.73 s: 7.76% of 30 minutes and 0.162% of a day. The selected sources supply no applicable ambient methanol/acetonitrile limits; occupational limits are not substituted. Health concentration guidance is not itself an instrument-accuracy standard.

**Outcome:** assessment completed with explicit negative/unverified conclusions. Compliance is not established. A test verifies that favorable modeled sensitivity cannot override incompatible domain and coverage.

## 2. Practical radio and communication controls

Selected one engineering reference: **73.372–73.628 GHz**, 256 tones at 1 MHz spacing, one RF chain, 1/16 cyclic prefix and 30 pilots per 10,000-symbol frame. The [ITU reference](https://www.itu.int/dms_pub/itu-r/md/00/ca/cir/R00-CA-CIR-0251!!PDF-E.pdf) discusses 71–76 GHz space-to-Earth operation; this is not a spectrum licence. [VDI WR12 laboratory specifications](https://vadiodes.com/wp-content/uploads/2012/01/VDI-956_VNA-X_Typical_Performance_2022.03.17.pdf) cover the band, with typical 0.1 dB magnitude and 1.5-degree phase stability under stated warm, stable conditions. These are not satellite-receiver covariance or flight-modem measurements.

The new OFDM control generates a frame, adds a cyclic prefix and time-domain noise, estimates the channel from pilots and decodes **5,104,640 uncoded QPSK bits**. Stored physical-model SNR is used; static phase and residual CFO cases are declared sensitivities.

| Residual CFO after ideal common-phase tracking | Bit errors | Uncoded BER | Decisions with sensing reuse |
| --- | ---: | ---: | --- |
| 0 kHz | 12,700 | 0.2488% | Identical |
| 10 kHz | 12,891 | 0.2525% | Identical |
| 100 kHz | 34,540 | 0.6766% | Identical |

Uncoded payload rate is **480.44 Mbit/s**, distinct from previous theoretical information rates of 783.51 Mbit/s broad and 763.44 Mbit/s E-band. Read-only pilot reuse leaves resources and decoded bits unchanged under the same channel. Extra tuning, pilots and hardware are not free; useful sensing is a separate requirement.

Seventeen samples of an ideal 550 km overhead pass recompute background loss, sky noise, range and instantaneous power allocation. Above 45 degrees, the pass lasts **139.73 s**, averages **912.99 Mbit/s** and has a formal information integral of 127.58 Gbit. This is a 17-sample trapezoidal calculation, not a separate temporal-convergence claim or verified modem schedule. Sampled Doppler reaches **1.211 MHz**, changing by about **23.5 kHz/s**. Separate 1%-rate-loss limits are **29.01 kHz residual CFO** or **0.0526 rad RMS phase jitter**; they are not a combined error budget.

**Outcome:** retain the radio as a communication reference and **reject it as the current joint VOC/PM sensing design**. Measured RF/antenna/noise response, real tracking, coded throughput, weather availability, feasible sensing bands and coordination remain open. Evidence: [radio assessment](../results/five_task_closure/practical_radio_assessment.json), [waveform results](../results/five_task_closure/ofdm_waveform_controls.json), [pass](../results/five_task_closure/eband_moving_pass.csv).

## 3. PM information and material limitation

After removing all gas/background nuisance terms, fine/coarse response correlation is **0.9999999623**. Two nonnegative scenarios, (49, 41) and approximately (2.45, 98.13) µg/m³, differ by only **4.39 × 10⁻⁷ noise standard deviations** after optimal nuisance adjustment. Their conditional optimal equal-prior classification error is essentially 50%.

Fixing the other PM component still leaves standard errors near **29,106 and 35,722 µg/m³**: removing fine/coarse ambiguity does not cure weak absolute sensitivity. Hypothetical independent fine and total mass observations with 5 µg/m³ errors reduce fine/coarse errors to about 5 and 7.07 µg/m³. This improvement comes from auxiliary measurements, not THz information. It is a requirement sensitivity, not acquired data. See [diagnosis](../results/five_task_closure/pm_information_diagnosis.json) and [auxiliary requirements](../results/five_task_closure/pm_auxiliary_requirements.csv).

Acquired [S. Eliet's public calcite THz-TDS dataset](https://doi.org/10.57745/DLJEFW), version 1.0, released 2026, recorded September 11, 2023, Etalab 2.0. All **37 text files and three representative HDF5 files** passed repository checksums. Raw examples contain 1,000/1,000/1,001 timestamped traces; inspected metadata lack paired particle mass and size-distribution labels.

Reprocessed eight corrected sample means and four blanks for the one-metre dry-nitrogen cell. Forty-picosecond records give approximately **25 GHz native resolution**. Only four native bins near 300, 325, 350 and 375 GHz lie in both the declared useful range and our 60–400 GHz window. Log-amplitude interpolation accommodates maximum grid shifts of **0.00298 GHz**. Zero padding does not create independent resolution.

Field attenuation is −20 log10(|sample/reference|). Before/after blanks differ by up to **0.0900 dB**, versus less than 0.01 dB within either repeat pair. Apparent attenuation ranges from −0.0480 to 0.1014 dB; **42 of 64 values are negative** across both blank choices. They remain evidence of reference sensitivity, rather than being clipped into particle absorption. Source corrected means are used; raw examples establish schema, not a reconstruction of the authors' entire correction algorithm.

**Outcome:** PM information loss is quantified and real aerosol transmission is analyzed. Missing mass/size labels and drift prevent mass calibration. Dry-nitrogen calcite is not calibrated ambient aerosol. Acquired uncertainty summaries are not assumed to define joint spectral/time covariance. Evidence: [transmission](../results/five_task_closure/calcite_measured_transmission.csv), [drift](../results/five_task_closure/calcite_reference_drift.csv), [validation record](../results/five_task_closure/calcite_validation.json).

## 4. Independent public physical checks

Compared P.676 calculations with [Taleb et al., Scientific Reports (2023), Figure 8](https://www.nature.com/articles/s41598-023-47586-8). Published 380 GHz humidity/attenuation slopes are **0.033 ± 0.009 VNA** and **0.027 ± 0.009 THz-TDS**, in (dB/m)/(g/m³). No confidence-level interpretation is imposed on reported plus/minus values.

The comparison uses six temperatures from 20–45°C, the respective published pressures and a declared unsaturated humidity envelope, without reconstructing the authors' exact samples. The VNA-pressure mean slope is **0.03280**, with all six states inside its reported range. The TDS-pressure mean is **0.03413**, with some states outside that range. The discrepancy is retained; no parameter was fitted to force agreement. Raw water data are author-request only, so this is an aggregate background check. No message was sent. Evidence: [comparison](../results/five_task_closure/published_water_comparison.csv), [scope](../results/five_task_closure/published_water_validation.json).

| Other primary evidence screened | Decision |
| --- | --- |
| Public calcite dataset | Use four measured in-band transmission bins; no mass-calibration claim. |
| [Gudz et al., acetonitrile near 165 GHz](https://hal.science/hal-05294637v1/document) | Relevant in-band spectroscopy; low-pressure cells, fitted pressure interpretation and long scans do not validate ambient satellite sensing. Article acquired; no matched atmospheric dataset. |
| [Leeds methanol dataset](https://archive.researchdata.leeds.ac.uk/1249/) | Approximately 3.4 THz; excluded as outside 60–400 GHz. |
| Jena/HITRAN particle optics reviewed earlier | No suitable complete target-material coverage; no unsupported extrapolation into a measured PM calibration. |

[Source receipts](../results/five_task_closure/public_acquisition.json) and [additional receipts](../results/five_task_closure/additional_source_acquisition.json) preserve hashes and failed requests. WHO downloads encountered timeout/403/browser checks, recorded as unavailable downloads. Guideline values were checked against primary web sources. Not finding a suitable paired dataset in this bounded search is not proof that none exists anywhere.

**Outcome:** aggregate water and measured aerosol checks completed. Paired atmospheric VOC/PM validation, a measured error covariance, target-material calibration and satellite transfer remain open.

## 5. Manuscript and reproducibility package

Updated the active manuscript to **Limits of Sub-THz VOC and Particulate Sensing with Communication-Pilot Reuse**, covering expanded physics, negative feasibility findings, public measurements and the next experiment. Previous September 8 source/PDF are preserved in [paper/history/2026-09-08](../paper/history/2026-09-08). Current tables are generated from saved evidence; four figures show PM information, pass dynamics, water response and measured aerosol drift.

The current six-page deliverable is [the PDF](../output/pdf/thz_isac_pollutant_sensing_ieee.pdf), built from [main.tex](../paper/main.tex) and [current_study.tex](../paper/current_study.tex). README files and the historical ledger identify the current status. A concrete [measurement protocol](41_measurement_protocol.md) and [empty observation schema](../results/five_task_closure/paired_measurement_schema.csv) define required inputs. No experimental rows were invented.

Verification includes **198 passing tests**, source checksums, independent FFT/table replay, a separate nuisance least-squares PM calculation, detector/averaging arithmetic, pass symmetry/integration, deterministic waveform replay and manuscript checks. The final build has no unresolved references or overfull boxes; all six pages were visually inspected. [verification.json](../results/five_task_closure/verification.json) and [closure_manifest.json](../results/five_task_closure/closure_manifest.json) record the snapshot. Tests establish software behavior, not environmental truth.

The older `task_completion/completion_manifest.json` remains historical. Its scientific arrays and code are checked for preservation. The changed root README supersedes its older documentation hash; the old manifest is not rewritten to hide that change. The current manifest normalizes CRLF to LF only for source text (Python, Markdown, TeX and requirements) so Git checkout line endings do not masquerade as code changes. Data/PDF hashes remain exact bytes; normalized baselines also preserve the older source-code comparison across checkouts.

### Reproduction

Use Python 3.13, [the direct dependency snapshot](../requirements-closure-lock.txt), and `pdflatex` with IEEEtran. This is not a cross-platform transitive lock. Raw downloads are excluded from Git and fetched by script; inspection/replay results are retained. Reports 38–39 explain regeneration of earlier physics and the three failed isotope requests.

From the repository root in PowerShell:

```powershell
python -m pip install -r requirements-closure-lock.txt
$env:PYTHONPATH="$PWD\src;$PWD\scripts;$PWD"
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
python scripts/acquire_closure_inputs.py
python scripts/run_public_measurement_checks.py
python scripts/run_five_task_closure.py
python scripts/build_current_paper.py
python -m pytest -q
python scripts/verify_five_task_closure.py
```

Default verification checks saved hashes. Rebuilt PDF/plots may include timestamps; live endpoints may return changed metadata. After deliberate regeneration, review numerical/source changes, render and inspect the PDF, then use `python scripts/verify_five_task_closure.py --seal` to create a new reviewed snapshot. Do not silently reseal unexplained mismatches.

## Every task in the original proposal

There are **11 proposal tasks**. Optional 1.5/3.3/4.4 entries in the historical ledger are additional work, not original requirements. Status below concerns modeling/analysis, not a deployed sensor.

| Proposal task | Current outcome | Remaining qualification |
| --- | --- | --- |
| 1.1 Layered atmosphere | Implemented; standard plus measured weather | Pollutant height profiles and upper continuation are assumed. |
| 1.2 HITRAN extraction | Implemented, inventoried and checked | Three requests unavailable; uncertainty/broadening gaps. |
| 1.3 Voigt/Lorentz slant integration | Spherical refraction and numerical checks implemented | No measured atmospheric column/line-shape validation. |
| 1.4 Aerosol baseline | Rayleigh and full Mie distributions implemented | Target material, size and humidity response uncalibrated. |
| 2.1 Link parameterization | Budget, OFDM resources, noise and pass implemented | Hardware, tracking and availability unvalidated. |
| 2.2 CSI synthesis | Complex pilots and OFDM waveform control implemented | Atmospheric radio CSI remains simulated. |
| 3.1 Gas/PM separation | Nuisance projection and information audit implemented | Current E-band fails; PM signatures nearly indistinguishable. |
| 3.2 Estimators | Signed statistical and bounded nonlinear fits evaluated | Useful joint PM/measured VOC retrieval not demonstrated. |
| 4.1 Variance bound | Nuisance-adjusted bound/conditional attainability implemented | Noise, covariance and bias not field calibrated. |
| 4.2 Sensitivity | Elevation, noise, weather, profiles, resources and synchronization studied | Sweeps are not a measured population uncertainty model. |
| 4.3 Detection floors and standards | ppm/mass floors and requirement assessment completed | **Positive compliance verification not achieved.** |

The next necessary work is an observable sensing-band design and calibrated independent measurements. [The protocol](41_measurement_protocol.md) specifies instrument response, before/after blanks, gas truth, fine/coarse mass and size/composition, weather, geometry and averaging, with calibration separated from final evaluation. These physical inputs cannot be supplied by additional simulations or by relabelling optimizer convergence as measurement.
