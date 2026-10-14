# CO observability presentation

Date: October 14, 2026.

## Purpose and result

The user requested a presentation in a different aesthetic from the earlier decks. A 14 slide presentation now explains the restarted CO problem: 60 to 1000 GHz, a frequency and atmospheric path length matrix, and no receiver noise. It uses Georgia typography with ivory, charcoal and copper, spacious layouts and a decorative cover image.

The presentation has 12 main slides and two appendix slides. The main argument is that a matched reference isolates the additional chemical optical depth through `tau_c = -2 ln(|h| / |h_0|)`. Without constraints on the background atmosphere, the same channel permits multiple decompositions. Removing receiver noise does not eliminate physical line broadening or this ambiguity.

Files:

- [Editable PowerPoint](../output/presentations/co_observability_editorial_v2.pptx), including editable charts, tables and speaker notes.
- [Reading PDF](../output/presentations/co_observability_editorial_v2.pdf), preserving the slide appearance, with bookmarks and clickable references. Its slide content is rasterized; use the PowerPoint to edit or copy content.
- [Presenter notes](../output/presentations/co_observability_presenter_notes.md), including the complete scientific qualifications and references.

## Evidence and assumptions

The plots reuse the [saved CO calculation](59_restart_observability_2026_10_14.md) and the spectroscopic parameters in `results/restart_2026_10_14`. They do not introduce invented spectra. The example remains a chosen scenario: 1 ppm excess CO over a 20 m cloud, temperature 296 K, pressure 101325 Pa, water partial pressure 1000 Pa, and total path lengths up to 200 m. It assumes exact background and calibration.

The line profile comparison uses the first ground vibrational state CO transition from the saved HITRAN parameters at 1 and 0.1 atm. Profiles have equal integrated area and therefore compare broadening, not equal ppm samples at different pressures. The spectrum retains every second source sample and the samples at all eight principal line centers. The path curves retain every source length sample.

HITRAN supports line positions, strengths and broadening. JPL independently supports the principal CO line centers. ITU P.676 provides the atmospheric background. NIST supports the spectroscopy discussion. Source links appear in the slide notes and final references slide.

The numerical recovery uses the same forward assumptions for generation and inversion. It is a consistency result and does not establish experimental performance, a concentration threshold, or separation under uncertain atmospheric conditions. Minor isotopologues, non-Voigt corrections and explicit water perturber effects are outside this first calculation. The observable is a column enhancement relative to the reference; concentration requires cloud length or additional spatial information.

## Cover image provenance

The cover image was generated with the built-in image generation tool on October 14, 2026. It is decorative and carries no measured spectral information. The visual brief requested a widescreen abstract spectrum on warm charcoal, with ivory and copper light bands in the right third and empty space on the left for the title, without labels, axes or molecular diagrams.

The preserved asset is [spectral_cover.png](../output/presentations/co_observability_assets/spectral_cover.png). The original local generation was `C:/Users/guill/.codex/generated_images/01a13a97-8747-7d10-a6b7-9685106bd246/exec-74a3b690-47ae-4afa-8079-c1c597505f64.png`. Rebuilding uses the preserved asset and does not regenerate it.

## Reproduction

Run from the repository root, using the configured Codex Node runtime for the second command:

```powershell
python scripts/prepare_co_presentation.py
& 'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' scripts/build_co_observability_presentation.mjs
python scripts/package_co_presentation_pdf.py
```

The preparation script requires NumPy, SciPy and Pillow, and reads the installed Georgia font. The presentation builder uses the local Codex artifact runtime and presentation utilities. PDF packaging requires PyMuPDF. Runtime paths are local configuration and may need adjustment on another computer.

Intermediate numerical evidence and slide renders are placed under `tmp/co_observability_deck`. Set `CO_DECK_NAME` to a fresh `.pptx` filename when creating a subsequent revision; the PDF script uses the same stem. Keep the final source and output names aligned when updating links.

## Remaining work and next steps

The next research decision is how to obtain the reference channel: a controlled matched measurement or a model with explicitly constrained atmospheric and instrumental quantities. Then vary those uncertain quantities and test whether their spectral responses can reproduce a change in CO column. Only after that should the study extend to other gases, mixtures and angular dependence.
