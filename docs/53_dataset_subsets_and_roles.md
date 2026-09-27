# Dataset subsets and their roles

## Purpose and result

Audited the saved acquisition records, current physics inputs and historical data provenance so the supervisor presentation can identify exactly which parts of external datasets were used. Slides 40–44 now report source identity, subsets, filters and evidence boundaries. The current spectroscopy CSV hashes match the hashes retained in the physics manifest.

This audit changes documentation and the presentation, not the scientific experiments or reported recall. The current five VOC study uses controlled concentration scenarios. Its results are not predictions evaluated against UCI Beijing labels or paired field radio measurements.

## Inputs explained within each task

The current presentation places a visible explanation on every task's method slide, so the audience can understand the inputs while reading the method and results. [The task input module](../scripts/supervisor_task_sources.py) maintains these explanations and the presenter notes repeat them. The detailed appendix remains on slides 40–44.

| Task | Method slide | Inputs and their role |
| --- | ---: | --- |
| 1.1 Atmospheric profiles | 6 | NOAA IGRA Beijing snapshot: 521 soundings; January profile for the current grid and four selected months for earlier checks. Pressure, temperature and humidity drive propagation. ITU P.835 provides the standard case; pollutant vertical profiles are assumed. |
| 1.2 Molecular spectroscopy | 8 | HITRAN2024 via HAPI: 319,001 acquired lines, 25 isotope tables, 0–3000 GHz, five VOC targets and four interferents. Line parameters, masses and partition sums define gas absorption. |
| 1.3 Path attenuation | 10 | The same HITRAN inputs, ITU P.676 background and ITU/January IGRA states enter slant integration. Published water slopes near 380.197 GHz provide a separate physical check. |
| 1.4 Particulate extinction | 12 | Assumed size distributions, density and refractive index define mass extinction. Eight calcite sample and four blank recordings check transmission separately; they do not provide PM mass or size labels. |
| 2.1 Receiver budget | 14 | Task 1 propagation and ITU emission feed assumed orbit, power and noise scenarios. These determine SNR and time requirements; no measured RF chain dataset is used. |
| 2.2 Waveform chain | 16 | Generated QPSK/OFDM data: 16 raw frames check timing and decoding; simulated moments support recall trials. No measured CSI set is used. |
| 3.1 Joint inversion | 18 | HITRAN signatures and two PM modes form the inverse model. The standard atmosphere selects 16 bands and January IGRA checks weather transfer; there are no measured training labels. |
| 3.2 Payload estimator | 20 | Generated QPSK moments, 10,000 trials per null/positive class, controlled VOC and PM scenarios and the HITRAN/IGRA forward model estimate recall and mass error. Earlier three gas controls remain separate. |
| 4.1 Lower bounds | 23 | Analytical QPSK and magnitude likelihoods with unknown signal, noise and reference determine Fisher bounds. Historical three gas efficiency and the 20 s zero extra residual benchmark are model based. |
| 4.2 Global sensitivity | 25 | HITRAN/PM physics with standard and January IGRA atmospheres generate 288 settings and eight outputs: 2,304 rows across time, calibration and other variables. |
| 4.3 Detection reporting | 28 | Current positive/null trials and 480 retained metric rows support limits, recall and intervals. WHO 2021 PM levels are comparisons and declared concentration controls; no field compliance dataset is available. |

The revision adds provenance to the task narrative without adding new experiments. Independent receiver stability and paired concentration truth remain missing.

## Inputs to the current five VOC and PM study

### HITRAN2024 spectroscopy through HAPI

The receiver reads `data/raw/payload_bounds/lines.csv` and `results/receiver_design/voc_pm_extension/lines.csv`. These contain 287,737 and 31,264 acquired transitions respectively, for a combined **319,001 lines across 25 isotope tables and nine gases**. The acquisition window is 0–3000 GHz. There are **12,261 line centres within 220–330 GHz**, but this count is descriptive: the gas cross section calculation uses the acquired line profiles with no wing cutoff by default.

| Role | Molecule | Retained HITRAN local isotope IDs | Acquired lines | Centres in 220–330 GHz |
| --- | --- | --- | ---: | ---: |
| Target | H2CO | 1, 2, 3 | 12,147 | 151 |
| Target | CH3OH | 1 | 4,663 | 467 |
| Target | CH3CN | 1 | 17,880 | 1,078 |
| Target | CH3Cl | 1, 2 | 12,824 | 670 |
| Target | HCOOH | 1, 2 | 18,440 | 401 |
| Interferent | CO | 1–6 | 773 | 27 |
| Interferent | O3 | 1–5 | 93,018 | 3,199 |
| Interferent | SO2 | 1–4 | 139,086 | 5,562 |
| Interferent | NO2 | 1 | 20,170 | 706 |

The forward model consumes line positions, strengths, air broadening, lower state energies, temperature exponents and pressure shifts. HAPI supplies isotope masses and partition sums. HITRAN intensities already contain natural isotope abundance. These are external spectroscopic parameters assembled from measurement and theory, not measured channel observations.

The historical 34 isotope tables and 304,416 transition inventory is a different catalog snapshot. It should not replace the actual current input totals above. CH3Br, C2H4, CH3F and CH3I were screened but were not added to the current retrieval: their reviewed published line coverage lies outside the acquired window.

Evidence: [machine readable audit](../results/presentation_source_audit/dataset_subsets.json), [current physics manifest](../results/joint_receiver_revision/physics_manifest.json), [base acquisition](../results/payload_bounds/spectroscopy_acquisition.json), [extension acquisition](../results/receiver_design/voc_pm_extension/acquisition.json), [input assembly](../scripts/joint_receiver_support.py), [cross section calculation](../src/thz_isac/physical_spectroscopy.py), and [HITRAN](https://hitran.org).

### NOAA IGRA soundings

Source: Beijing station **CHM00054511**, the [2026 year to date archive](https://www.ncei.noaa.gov/pub/data/igra/data/data-y2d/CHM00054511-data-beg2026.txt.zip), acquired on 23 September 2026. The retained parser output contains **103,322 levels across 521 soundings**. This is a frozen acquisition snapshot, not a complete year.

The selection rule was the first complete sounding reaching at least 20 km in January, April, July and September, declared before spectroscopy evaluation.

| Selected sounding, UTC | Measured levels | Top above station | Use |
| --- | ---: | ---: | --- |
| 1 January 2026, 00:00 | 226 | 36.97 km | Current common global grid and earlier tests |
| 1 April 2026, 00:00 | 160 | 28.76 km | Earlier seasonal sensitivity |
| 1 July 2026, 00:00 | 203 | 32.34 km | Earlier seasonal sensitivity |
| 1 September 2026, 00:00 | 189 | 34.95 km | Earlier seasonal sensitivity and numerical checks |

Pressure, temperature and water profiles drive propagation. Above each measured top, a model continues the atmosphere to 100 km. The current global grid uses the January profile and the standard atmosphere. The selected frequency design used the standard atmosphere. None of these soundings provides VOC/PM concentration labels or paired radio observations.

Evidence: [weather selection](../results/task_completion/weather_selection.json), [source acquisition](../results/task_completion/source_acquisition.json), and [receiver atmosphere assembly](../scripts/receiver_design_physics.py).

### Reference models and assumptions

ITU-R P.835 supplies the reference atmosphere and ITU-R P.676 supplies the oxygen/water background and related thermal calculation. These are published models, not observation datasets. Particle size distributions, material density, complex refractive index and vertical concentration profiles are model assumptions. The PM component does not use measured mass labels from the calcite data below.

## External physical checks

**Water vapour:** [Scientific Reports paper, DOI 10.1038/s41598-023-47586-8](https://doi.org/10.1038/s41598-023-47586-8), Figure 8 and methods. The retained comparison uses aggregate absorption slopes at 380.197353 GHz: VNA 0.033 ± 0.009 and TDS 0.027 ± 0.009 (dB/m)/(g/m³). Raw measurement series are unavailable in this audit. The quoted plus/minus ranges are not reinterpreted as confidence intervals. The mean VNA comparison lies within the reported range; the mean TDS comparison does not. See [retained water check](../results/five_task_closure/published_water_validation.json).

**Calcite aerosol THz-TDS:** [Recherche Data Gouv, DOI 10.57745/DLJEFW](https://doi.org/10.57745/DLJEFW), version 1.0, calcite particles resuspended in dry nitrogen on a 1 m path. The analysis uses eight sample recordings and four blank recordings. It retains four native frequency bins near 300, 325, 350 and 375 GHz, with approximately 25 GHz native resolution. Native FFTs and the geometric mean of two blanks produce 64 transmission rows. The files have no mass concentration or particle size distribution labels. Before/after reference differences have RMS 0.047225 dB, but this is a separate experimental diagnostic, not a universal calibration covariance or a measurement of the proposed receiver's stability. See [calcite validation](../results/five_task_closure/calcite_validation.json) and [dataset metadata](../results/five_task_closure/calcite_dataset_metadata.json).

## Historical datasets and separate controls

These sources were used in earlier branches. Their data must not be presented as the labels for the current five VOC recall experiments.

| Source | Part actually used | Branch and limitation |
| --- | --- | --- |
| [UCI Beijing Multi Site Air Quality, 10.24432/C5RK5G](https://doi.org/10.24432/C5RK5G) | Twelve sites, 1 March 2013 to 28 February 2017. 420,768 raw station hours. 383,585 complete cases, then 365,943 after removing 17,642 rows with PM10 below PM2.5. | Principal historical six pollutant benchmark. Select 20,000 deterministic evenly spaced rows after sorting by timestamp and station, then split 12,000 / 4,000 / 4,000 chronologically. Atmospheric THz observations remain simulated. |
| ESA CCI IASI/MOPITT CO and OMI NO2 Level 3 products | Ten paired monthly rows from March to December 2013, from twenty files. Both products use the grid centre at 39.5° N, 116.5° E nearest the declared Beijing point. | Measured radiance derived column retrievals for native column feasibility. These are not direct truth or THz measurements. Quality and uncertainty fields were retained. |
| [Mendeley protein THz-TDS, 10.17632/dpw4svmdr8.1](https://doi.org/10.17632/dpw4svmdr8.1) | Ten files downloaded, but only Fig3.csv and Fig4.csv scored: seven lysozyme and six ovalbumin concentration levels. Five frequency values from 0.9 to 1.3 THz. | Separate aqueous laboratory control. Reported means and SDs, with one concentration level held out at a time and no pseudo replicates. |
| [UCI Air Quality, 10.24432/C59K5F](https://doi.org/10.24432/C59K5F) | 9,358 raw hourly rows from March 2004 to February 2005 in an unnamed Italian city. 6,941 complete rows after excluding −200 missing values. Split 4,164 / 1,388 / 1,389 chronologically. | Earlier four target analyzer calibration using five metal oxide sensors and weather. Not THz. The historical audit records a weaker reproduction trail without a dedicated committed scoring manifest. |

The Beijing cleaner uses CO, O3, SO2, NO2, PM2.5, PM10, temperature, pressure, dew point, rain and wind speed, together with station and timestamp. Wind direction is not retained. Its normalization uses the training Q95 minus Q05 span. Later work reused a known test period, so it is not an untouched external test. Ground sensor repair additionally masks real channels artificially and is a different task from remote THz sensing.

NASA Aura MLS was investigated through metadata, but no granules were acquired or scored in the retained branch. It is not an evaluated dataset. WHO recommendations supply comparison values, not observations. Early toy generators are software controls and do not support physical claims.

Evidence: [historical provenance audit](35_data_provenance_and_synthetic_evidence_audit.md), [column manifest](../results/tables/real_column_feasibility_manifest.json), and [protein manifest](../results/tables/measured_thz_control_manifest.json).

## Reproduction, limitations and next steps

Run `python scripts/audit_supervisor_datasets.py` to regenerate the compact subset audit from the retained spectroscopy caches and manifests. Raw caches under `data/raw/` are intentionally excluded from Git; acquisition scripts and manifests document them. Then rebuild the presentation as described in [the presentation record](52_supervisor_presentation.md).

The audit establishes which data were used, not their experimental suitability for every claim. No paired measured atmospheric THz, VOC and PM concentration dataset validates current recall. Next, acquire independent blank/reference and concentration truth measurements with weather, geometry and instrument metadata, keeping calibration and evaluation data separate.
