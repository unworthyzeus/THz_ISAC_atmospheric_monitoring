# Detailed supervisor presentation

## Purpose and work completed

Created a 44 slide English presentation based on research snapshot `461a3ba` and the original proposal PDF. Each of the eleven original tasks receives method and result slides. The expanded presentation includes twenty equations compiled from LaTeX, editable PowerPoint tables, an editable recall chart, numerical evidence blocks, speaker notes and source references.

The presentation explains the problem, physical model, receiver, inversion, bounds, improvements, failed controls and remaining experimental requirements. It retains five VOCs, PM2.5, coarse PM and derived PM10 throughout the common global comparison. Historical pilot versus payload results are separated from the current five gas receiver.

## Delivered results

- `output/presentations/sub_thz_isac_supervisor_review_v7_datasets.pptx`: current presentation with vector equation assets, notation legends and detailed dataset provenance.
- `output/presentations/sub_thz_isac_supervisor_review_datasets.pdf`: current reading copy made from final reviewed slide renders, with slide bookmarks.
- `output/presentations/supervisor_presenter_notes.md`: detailed presenter notes and evidence paths.
- `output/presentations/supervisor_equations.tex`: exact LaTeX equation source.

The current VOC result table includes recall at 1 microgram per cubic metre, missed detections, nominal 95% response concentrations, empirical recall at those concentrations, binomial intervals and relative concentration RMSE. Separate slides report time and calibration sensitivity, the 288 condition global grid and low PM recalls.

The notation revision adds a bottom legend to each of the twenty formula slides. Each legend defines that slide's symbols, indices, operators and applicable units. Definitions distinguish reused letters such as concentration and the speed of light, wavenumber and Boltzmann's constant, and the gas constant and propagation distance. The corresponding definitions also appear in the presenter notes. The other nineteen slides retain their content and layout. Earlier delivered versions remain available for reference.

The dataset revision appends five provenance slides, with an overview pointer on slide 5. They identify the current HITRAN input pools, exact NOAA soundings, external water and calcite checks, historical Beijing filters and other laboratory or field controls. [The dataset ledger](53_dataset_subsets_and_roles.md) preserves the details and distinguishes evaluated data from metadata-only options.

## Scientific boundaries

No new scientific experiments were run for this presentation. Favorable recall remains conditional on the displayed receiver, atmosphere, acquisition time and unmeasured calibration assumptions. Zero additional calibration residual still retains thermal noise and finite reference uncertainty. No useful joint PM retrieval, full operational receiver validation or measured field recall is established.

PowerPoint content remains editable except for the rendered equation assets. The PDF is an image based reading copy; the companion notes preserve searchable text and LaTeX. Native desktop PowerPoint execution was not tested.

## Reproduction

Run `scripts/audit_supervisor_datasets.py`, then `scripts/prepare_supervisor_presentation.py` and `scripts/render_supervisor_equations.py`. Use the bundled Node runtime to run `scripts/build_supervisor_presentation.mjs`, with `DECK_NAME` set to a fresh output filename. Review the final slide renders before running `scripts/package_supervisor_pdf.py`. The builder records private package validation and final rendering material under `tmp/supervisor_deck/`.

## Remaining work and next steps

Discuss the calibration and receiver requirements with the supervisor, then acquire independent stability and concentration truth measurements. Recompute the conditional comparisons with measured covariance before making a field performance claim. Update this presentation when that evidence becomes available.
