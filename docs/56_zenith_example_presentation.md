# A self contained presentation of the zenith example

5 October 2026. The presentation explains the acetonitrile example to a mathematically fluent audience with no prior knowledge of the project or radio engineering.

## Deliverables and purpose

- [PowerPoint presentation](../output/presentations/zenith_acetonitrile_tutorial_v2.pptx)
- [PDF reading copy](../output/presentations/zenith_acetonitrile_tutorial.pdf)
- [Presenter notes, equations and source links](../output/presentations/zenith_acetonitrile_presenter_notes.md)
- [LaTeX source for the equation assets](../output/presentations/zenith_acetonitrile_equations.tex)

The supervisor requested one compound at 90° with an intuitive explanation followed by the mathematical construction of the observations, matrices, acquisition time and detection decision. The presentation follows that order and introduces the application before assuming any project terminology. It explains ISAC, LEO, absorption, OFDM, pilots, bandwidth, decibel units and the difference between a reference and a sample. LEO links provide a useful example throughout the complete chain.

The deck has 38 slides. Slides 1–29 contain the main explanation. Slides 30–38 contain a numerical five tone calculation, spacing and power comparisons, calibration and motion limitations, and primary sources. The equations retain dimensions and units. Speaker notes explain the physical interpretation and assumptions behind the mathematics.

## Evidence and result

The presentation reads the saved experiment at research snapshot `b94f3fe`, including `baseline.json`, `tone_by_tone.csv`, `worked_observation.csv`, `worked_example.json`, `receiver_control.csv`, `ofdm_spacing.csv`, `sensitivity.csv` and `motion.csv`. It does not introduce a new physical dataset or replace measured spectra with invented curves.

With **20 s total acquisition, ideal tracking, the specified hardware, matched background and an assumed, unmeasured 0.001 dB differential calibration residual**, the predicted 95% acetonitrile enhancement concentration is **50.58 µg/m³**. The simulated response is **94.75%** at that concentration and **1.31%** at 1 µg/m³. The presentation distinguishes these conditional predictions and simulations from measured field performance. The five tone subset fails to detect the same worked sample and demonstrates the information lost by discarding most tones.

Hardware evidence retains its original scope: the [Sen et al. terrestrial experiment](https://www.nature.com/articles/s41928-022-00897-6), [TeraLink design preprint](https://arxiv.org/html/2606.15410v1) and [Cooper et al. source component](https://doi.org/10.1109/JMW.2025.3610360) do not jointly establish a qualified orbital modem with this bandwidth and calibration. The spectroscopy comes from [HITRAN](https://hitran.org/lbl/), the standard atmosphere from [ITU P.835](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en), and oxygen/water propagation from [ITU P.676](https://www.itu.int/rec/R-REC-P.676-13-202208-I). The [EMeRGe study](https://acp.copernicus.org/articles/23/1893/2023/index.html) provides atmospheric context, not a universal surface concentration. Each relevant slide carries source notes.

## File use and reproduction

Text, tables and the three charts are editable slide objects. The charts include workbook snapshots of the saved data, rounded to 14 significant digits for Excel compatibility. Equations are vector assets, with the editable LaTeX source supplied separately. The PDF preserves the rendered appearance and provides bookmarks. Its pages are images; use the companion Markdown notes for searchable text and clickable source links.

The generation scripts are:

```powershell
py -3.12 scripts/prepare_zenith_presentation.py
py -3.12 scripts/render_zenith_equations.py
# Run with the bundled Node runtime and @oai/artifact-tool dependencies.
# Set DECK_NAME to a fresh filename for a new revision.
node scripts/build_zenith_presentation.mjs
py -3.12 scripts/package_zenith_pdf.py
```

The builder accepts `PRESENTATION_SKILL_DIR`, `RUNTIME_NODE_MODULES` and `RUNTIME_PYTHON` environment overrides. Equation rendering uses the available `pdflatex` and PyMuPDF. Presentation preparation uses the saved research files and SciPy. The scripts keep draft files and slide renders under `tmp/zenith_deck`.

## Remaining work and limitations

No new field observation accompanies the presentation. Calibration covariance, linear OFDM output, full bandwidth hardware, moving link tracking and independent concentration truth still require measurement. The 90° geometry is an instantaneous benchmark. An arbitrary vertical concentration profile, chemical specificity in a changing mixture and multistatic 3D reconstruction remain outside this single compound result.

The next scientific step is to measure blank reference/sample stability with the intended instrument, freeze the error model, and test independent concentrations and atmospheric conditions. The [full walkthrough](55_zenith_single_compound_walkthrough.md), [supervisor response](54_supervisor_revision_2026_10_05.md) and [permanent calibration qualification](46_critical_calibration_assumption.md) retain the derivation and research limitations.
