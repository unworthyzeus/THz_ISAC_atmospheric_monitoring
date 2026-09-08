<!-- review-2026-09-05 -->
# Current interpretation: September 5, 2026

RESULT: Training-only Ridge has normalized RMSE 0.3474443 versus 0.3474789 for the training-mean predictor. Its difference is −0.00003458, with a 30-day block interval [−0.00010382, 0.00003264] that crosses zero. The 7-day sensitivity interval also crosses zero; no stable spectral gain is demonstrated. See the [current revision and evidence ledger](revision_review.md).

The earlier notes below are retained as historical records. Their original conclusions, uncertainty statements, test counts, and PDF hashes are superseded where the revision says so.

<!-- end-review-banner -->

# IEEE Paper Build and Visual Validation

## What was done

The former two page draft was replaced and then expanded into a nine page IEEE conference paper titled:

> Estimation Limits for Ambient Pollutant Sensing From Simulated Sub THz NTN Attenuation

The final paper integrates the physical reference result, optimized probe placement, the H2O local control, the native ESA CCI column stress test, the exact metric audit, ten receiver noise seed stability, a separate causal ground sensor forecast, and the idealized tenfold noise sensitivity. It was compiled with the bundled Tectonic tool, rendered to page images, and inspected page by page.

## Why it was done

The old draft presented a superseded shared template regression result as its headline and did not expose the real versus simulated evidence boundary. The rebuilt paper needed to document calibrated spectroscopy, link assumptions, Fisher bounds, failed estimator evidence, real column data, optimization limits, and all major claim boundaries. PDF rendering was required because valid LaTeX does not guarantee readable equations, tables, or float placement.

## Reproducible build

```powershell
python C:\Users\guill\.codex\plugins\cache\openai-bundled\latex\0.2.4\scripts\compile_latex.py C:\Research\THz_ISAC_atmospheric_monitoring\paper\main.tex --compiler tectonic --output-directory C:\Research\THz_ISAC_atmospheric_monitoring\paper\build --json
```

The repository build is `paper/build/main.pdf`. A stable final copy is `output/pdf/thz_isac_pollutant_sensing_ieee.pdf`.

| Property | Value |
| --- | --- |
| Pages | 9 |
| File size | 379,308 bytes |
| SHA256 | `6a0478c37c28b1a2484afa2d5e8fd0303c16abbfd032537b52f9bf8a1ed58f5d` |
| Compiler | Bundled Tectonic 0.16.9 |
| Final compile exit code | 0 |

The two PDF copies have the same SHA256.

## Scientific corrections made during paper review

1. The CO column description was corrected. The code assigns the entire reported total column to normalized weights inside 0 to 20 km. It omits the real upper atmosphere distribution, not column amount, and the bias direction is unknown.
2. The H2O abstract and results now distinguish the 0.290 degree default result, the 2.541 degree failure after adding background scale to that design, and the 0.848 degree result after strict nuisance aware reselection.
3. Frequency selection is documented as column balanced joint gas and nuisance D optimal design. It is not WHO weighted or nuisance projected.
4. The separate 32 probe power allocator is explicitly documented as WHO scaled and nuisance projected.
5. The probe variance, regularization scale, total power accounting, H2O finite difference, and nuisance sets are now stated in the method.
6. HAPI is described as a reference implementation check using the same HITRAN records, not independent physical validation.
7. The ten satellite months are described with a sample quantile span rather than implying a stable population distribution.
8. The spectroscopy limitations now include minor isotopologues, out of band wings, line mixing, continua, and the lack of an end to end ITU-R P.676 comparison.
9. Every headline regression value is named as the macro training Q05 to Q95 normalized RMSE rather than generic RMSE.
10. The test period is described as originally held out and later reused for diagnostic extensions. The full period atmosphere and PM medians are disclosed as transductive scenario lookahead.
11. The paired row bootstrap is reported as failing to resolve a difference, not as an equivalence or indistinguishability test.
12. The LMMSE is identified as a training prior posterior mean and is separated from supervised Ridge and label free physical WLS.
13. The `0.104507` causal forecast is separated from THz inversion, and `0.031486` is labeled only as an idealized numerical sensitivity point.

## Visual inspection result

All nine final pages were rendered at 150 pixels per inch and inspected. The inspection covered title and abstract density, text flow, equations, all five tables, the physical signature figure, captions, citations, clipping, overflow, and final column balance.

No equation, table, caption, or body text is clipped. The native column and optimized gas tables remain readable at normal page scale. An IEEE reference trigger before item 2 produces a balanced final page with the complete 14 item bibliography.

## What worked

1. Tectonic resolved all packages and produced the PDF reproducibly.
2. Cross references resolved after the automatic second pass.
3. The final pass resolves every cross reference. Its only overfull box is a visually harmless 0.552 point count cell in the compact evidence table.
4. The title and abstract were shortened after independent review.
5. Three redundant result plots were removed while their tables and numerical discussion were retained.
6. The final PDF is nine pages and visually coherent without shrinking body text.
7. Python PDF parsing confirms nine pages, no encryption, no unresolved `??` markers, no tool tokens, and all 23 used font resources embedded.

## Failures and corrections

1. Automatic compilation first preferred MiKTeX `latexmk`, which failed because its Perl script engine was unavailable. Explicit bundled Tectonic compilation succeeded.
2. The bundled `pdftoppm.cmd` wrapper pointed to a missing runtime path. Calling the installed Poppler executable in its actual `Library/bin` directory rendered all pages successfully.
3. The runtime did not include `pdffonts` or `pdftotext`. Python `pypdf` replaced those checks and confirmed extracted text and embedded font resources.
4. A broad recursive search for the missing PDF utilities timed out after 30 seconds and produced noisy output. It was abandoned in favor of the bounded Python check.
5. The first evidence table used labels that collided visually. Shorter labels and revised widths fixed it.
6. Earlier revisions produced a sparse last reference page. An IEEE reference trigger before bibliography item 2 balanced the final nine page manuscript.
7. The first pass of each Tectonic compile reports temporarily undefined references. The build script reruns TeX, and the final pass resolves them.
8. Tectonic reports Times font shape substitutions, underfull table cells, and one 0.552 point overfull table cell. Page rendering confirmed that none causes clipping or unreadable text.
9. A repository wide Ruff command still reports 18 legacy `E402` findings. The scoped check for all 34 new Python files passes and the full test suite remains green.

## Remaining warnings and risks

Tectonic reports local Times font shape substitutions and underfull box warnings. The rendered pages were checked and remain readable, and every used font resource is embedded. A target venue PDF validator is still required before submission because camera ready rules are external to this repository.

The scientific risks remain larger than the layout risks:

1. No measured sub THz CSI is used.
2. The 0.63 dB independent residual per tone value is borrowed and uncalibrated for this link.
3. WHO scales have 8 h or 24 h averaging periods and are not one burst detection standards.
4. Satellite retrievals are coarse monthly products, not synchronized truth.
5. Surface and column vertical profiles remain assumed.
6. The 60 to 400 GHz candidates are not a realizable contiguous allocation.

## Next steps

1. Run the PDF through the chosen venue compliance checker.
2. Add measured or laboratory calibrated attenuation before making a positive sensing claim.
3. Replace assumed profiles with measured or assimilated vertical states.
4. Keep the conditional negative conclusion and the optimistic CO boundary case in every revision.

## Superseding Multi Method Paper Build

The multi method extension supersedes the nine page artifact above. The manuscript now includes the advanced THz information budget, causal forecast v2, strict station network reconstruction, successful single channel repair, and real measured Mendeley THz positive control.

Bundled Tectonic 0.16.9 compiled the final source to 10 letter size pages. Every page was rendered at 150 pixels per inch. The new evidence table and Beijing information class table are readable, all content stays inside the columns, and no equation, citation, or paragraph is clipped. The old reference trigger at item 2 initially produced a sparse final page. Removing it and triggering at item 10 balances references 5 through 9 against references 10 through 15 on the last page.

Python PDF parsing confirms:

1. 10 pages with nonempty extracted text on every page.
2. Zero replacement characters and no placeholder or tool tokens.
3. Every headline `0.074855`, `0.088890`, `0.095485`, and `5,918` is present.
4. The Mendeley DOI and all 15 references are present.
5. All 23 used font resources are embedded.

The final build and delivery files are both 382,220 bytes and byte identical. Their SHA256 is:

```text
38ea364c78f720603b89495b0a355530392b6b9ae7d44920604e59c6fc741674
```

Additional retained operational failures are one malformed JavaScript expression in an output shortening wrapper, which stopped before the compiler ran, and a first reference rebalance that removed the old trigger but still left the final page one sided. Direct compilation and the item 10 trigger corrected both without changing scientific content.
