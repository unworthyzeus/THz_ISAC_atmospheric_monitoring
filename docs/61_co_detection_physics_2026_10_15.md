# CO detectability and the physical origin of absorption

Date: October 15, 2026.

## Purpose and deliverables

The user requested another English presentation in the same editorial aesthetic, focused on two questions: whether CO can be detected, and what physically makes absorption vary smoothly with frequency. The user also requested a matching speaking script. The new presentation keeps the ivory, charcoal and copper palette and Georgia typography, with 15 main slides and two supporting slides.

- [Editable PowerPoint](../output/presentations/co_detection_physics_v2.pptx), including six native charts, two native tables, editable equation text and full speaker notes.
- [Presentation PDF](../output/presentations/co_detection_physics_v2.pdf), with 17 bookmarked pages and six clickable source links. Slide content is rasterized to preserve the reviewed appearance; use the PowerPoint for editing.
- [English speaking script](../output/pdf/co_detection_physics_speaking_script.pdf), with three pages and 821 spoken words, a few sentences per slide and the central optical depth equation. Its text is selectable and its fonts are embedded.
- [Scientific notes](../output/presentations/co_detection_physics_notes.md), including the same spoken text, detailed qualifications and source links.

The decorative cover reuses the existing asset. Its generation provenance is recorded in [the previous presentation record](60_co_observability_presentation.md#cover-image-provenance). No decorative image represents measured data.

## Scientific result

CO is observable in the stated ideal case: a matched reference without the added CO removes the shared geometric, atmospheric and instrument factors. For field amplitude, the additional optical depth is

\[
\tau_c(f,l)=-2\ln\left(\frac{|h(f,l)|}{|h_0(f,l)|}\right).
\]

This assumes exact atmospheric knowledge or a genuinely matched reference, exact calibration, a nonzero response and adequate numerical precision. It recovers a column enhancement relative to the reference. A concentration additionally requires the cloud length or a spatial model. It is not a measured or practical detection limit. With a completely unrestricted unknown atmospheric spectrum, the decomposition is not unique even without receiver noise.

The physical explanation starts with CO's permanent electric dipole and its rotational energy levels. Their allowed energy differences set the line centers. Collisions perturb molecular coherence; a simple exponential decay yields a Lorentz absorption profile. Thermal velocities give Doppler shifts and a Gaussian distribution. Their convolution is the Voigt profile. Smooth wings and overlapping lines therefore remain in a noiseless channel. An infinitely sharp ideal transition would be a delta peak, not a rectangular band. This line shape model is an approximation near isolated resonances; precise far wings and line mixing may need more complete physics.

For the first CO line near 115.271 GHz, using the saved HITRAN parameters at 296 K and 1 atm:

| Quantity | Calculated value |
| --- | ---: |
| Lorentz full width at half maximum | 4.814667 GHz |
| Doppler full width at half maximum | 0.268461 MHz |
| Ratio of Lorentz to Doppler width | 17,934 |
| Effective coherence time inferred from the Lorentz width | 66.1125 ps |

The coherence time is derived from the same linewidth through `gamma = 1/(2 pi T2)`, where gamma is the half width in Hz. It is not an independently measured time, the population lifetime, or necessarily the mean time between collisions. The pressure comparison holds integrated profile area fixed; it does not compare equal ppm samples at different pressures.

## Signal scale and atmospheric sensitivity

The numerical scenario reuses the [restart calculation](59_restart_observability_2026_10_14.md): 1 ppm added CO over a cloud from 20 to 40 m, a total atmospheric path up to 200 m, 296 K, total pressure 101325 Pa, and reference water partial pressure 1000 Pa. There is no receiver noise, and background and calibration are exact in the ideal inversion. The CO model retains 146 main isotopologue HITRAN transitions with centers up to 3000 GHz. Only the displayed measurement band is 60 to 1000 GHz.

At the catalog center near 115.271 GHz, the predicted relative amplitude drop is 0.333 ppm. Here ppm describes the fractional field amplitude change, not the molecular mole fraction. Some higher CO lines have larger responses but also substantially greater atmospheric attenuation. For example, modeled atmospheric loss near 576.268 GHz over 200 m is about 99.53 dB, before geometric loss. An exact numerical ratio does not demonstrate a measurable received signal.

A new deterministic sensitivity example increases water partial pressure from 1000 to 1010 Pa at fixed total pressure and temperature over the full 200 m path. Near 345.796 GHz, the ITU model gives a loss change of 0.0186961 dB, compared with 0.0000796602 dB for the selected CO cloud, a ratio of about 235. This is a chosen 1% change in water partial pressure, not one percentage point of relative humidity, a measured error, an uncertainty distribution, or a detection threshold. The two spectral patterns may still be separable. No joint retrieval or independence test is claimed.

Values, assumptions and input hashes are preserved in [the manifest](../results/co_detection_physics_2026_10_15/manifest.json), [the signal table](../results/co_detection_physics_2026_10_15/signal_and_humidity_scales.csv) and [the plotting evidence](../results/co_detection_physics_2026_10_15/evidence.json).

## What the user's original curve represents

The attached 230 to 240 GHz curve can be reconstructed from the historical CH3CN calculation. Its values are `gas_db_per_ug_m3` from `results/zenith_single_compound/tone_by_tone.csv` multiplied by `true_q_ug_m3` from `results/zenith_worked_steps/worked_steps.json`, as used by `scripts/prepare_zenith_compact_slides.py`.

The presentation labels this as a historical modeled acetonitrile curve. It explains the smooth response through broadened line contributions integrated through an atmosphere whose pressure and temperature vary with altitude. No transition by transition decomposition is supplied, and no old detector performance claim is reused. A smooth curve alone neither identifies the gas nor proves a separate physical continuum. Water continuum and collision induced absorption are distinct contributions in a complete atmospheric model.

## Sources

Primary references were checked on October 15, 2026. The numerical input data were acquired for the October 14 restart.

- [NIST molecular dipoles](https://cccbdb.nist.gov/diplistx.asp) and [diatomic rotational spectroscopy](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules): CO coupling and transition structure.
- [MIT spectroscopy lecture](https://ocw.mit.edu/courses/5-35-introduction-to-experimental-chemistry-fall-2012/18a908091e0258ba553794ac1cd0a517_MIT5_35F12_Module_1LS2.pdf) and [MIT dephasing lecture](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2009/c9108a344550e61973b5ecb4379cdf1e_MIT5_74s09_lec09.pdf): finite coherence and line shapes.
- [HITRAN definitions](https://hitran.org/docs/definitions-and-units/), [cross section definitions](https://hitran.org/docs/cross-sections-definitions/) and [NIST MATS](https://pages.nist.gov/MATS/MATS%20Summary.html): line parameters, profiles and absorption.
- [JPL CO catalog](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat): independent line positions.
- [ITU P.676-13](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf): atmospheric attenuation.
- [HITRAN water continuum](https://hitran.org/mtckd/) and [collision induced absorption](https://hitran.org/cia/): distinction from a visually smooth sum of broadened lines.

## Reproduction and verification

Run these scripts in order from the repository root. Use a Python environment with NumPy, SciPy and Pillow for preparation, PyMuPDF for the presentation PDF, and ReportLab and pypdf for the speaking script.

```powershell
python scripts/prepare_co_detection_physics.py
& 'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' scripts/build_co_detection_physics.mjs
python scripts/package_co_detection_physics_pdf.py
& 'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/build_co_detection_physics_script.py
```

The builder uses the configured Codex artifact runtime and presentation utilities. It reads installed Georgia font metrics. These machine specific paths may need adjustment elsewhere. Set `CO_PHYSICS_DECK_NAME` to a fresh `.pptx` filename for later revisions; the reading PDF uses the same stem. The source builder writes the shared slide records under `tmp/co_detection_physics_deck`, which the speaking script reads to keep the two aligned.

Numerical checks verify the normalized Doppler integral, linewidth and coherence relation, reproduction of the saved atmospheric baseline, and conversion between amplitude and decibel loss. The finalized PPTX passed package, layout, font, native chart workbook and import checks. All slide renders were visually reviewed, including corrected superscripts and subscripts. The PDF checks verify 17 slide pages, bookmarks and six reference links, and the speaking script checks verify all 17 spoken passages across three pages. All script pages were rendered and visually reviewed.

Equations are assembled from editable native text objects with positioned subscripts and superscripts. They are not raster screenshots or native Office equation objects. Native PowerPoint opening and Google Slides conversion were not tested; the reading PDF preserves the reviewed appearance.

## Remaining work, limitations and next steps

The main open task is to specify how the reference is obtained and how accurately atmospheric and instrument terms are known. The next modeling step is to constrain those quantities, vary them, and test whether the CO response is independent of their allowed changes across the chosen frequencies and lengths. The next measurement step requires a known gas column, matched acquisitions and measured instrument stability.

The current calculation excludes minor isotopologues, detailed non-Voigt effects, and a complete model of experimental uncertainty. It treats magnitude attenuation, not full molecular dispersion or angular reconstruction. It provides no hardware detection threshold or experimental verification. Other chemicals should be assessed individually after CO, followed by mixtures and later angular dependence. A species without a distinguishable response in the measured band cannot be identified by this absorption measurement alone.
