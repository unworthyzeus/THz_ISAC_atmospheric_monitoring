# A compact presentation of the zenith sensing example

8 October 2026.

The v5 presentation has six explanatory pages, a seventh page containing the numerical calculation recipe, an eighth page explaining RF units and interference, and a ninth page explaining why the fit uses all tones. It assumes a telecom background and explains the quantities specific to this sensing experiment, with numerical substitutions and sources.

## Deliverables and purpose

- [Editable PowerPoint v5](../output/presentations/zenith_compact_example_v5.pptx).
- [Reading PDF with source links](../output/presentations/zenith_compact_example.pdf).
- [Complete text, equations, examples and source notes](../output/presentations/zenith_compact_example_notes.md).
- [LaTeX equation source](../output/presentations/zenith_compact_example_equations.tex).

The user requested fewer pages with more meaning behind the words, detailed pilot and calibration examples, and an extra slide showing exactly how the final result is computed. The preceding [34 page worked presentation](57_zenith_worked_calculation.md) remains available. This compact version reuses the same saved physical calculation and simulated receiver observation.

## What the pages explain

1. The LEO example, reference and sample acquisitions, fixed vertical profile and concentration parameter q.
2. Molecular density, cross section, height dependent absorption and optical depth, with an actual altitude node calculation.
3. The numerical chain from q to extra optical depth, attenuation, amplitude ratio and amplitude reduction.
4. Known pilot symbols, division by the transmitted value, coherent averaging, the acquisition resource count and the saved complex channel estimates.
5. Calibration error, two explicit ways it can imitate absorption, the observed loss vector, the design matrix and the covariance.
6. The actual three by three system, its concentration estimate, uncertainty, threshold and conditional sensitivity.
7. The calculation in execution order, including elimination of the two gain parameters and the numerical decision.
8. Absolute power in dBm, linear complex pilot samples, loss in dB, covariance in dB², and the additional model needed for interference.
9. What the full spectrum adds compared with one tone: joint concentration and gain estimation, noise combination, and the remaining calibration ambiguity.

## V5 equation identities, gas enhancement and use of all tones

Slide 6 replaces the coefficient-only table with the three expanded normal equations and identifies the fit direction behind each row. It defines q as the surface equivalent CH₃CN concentration increase, G = AᵀC⁻¹A as the 3 by 3 matrix of weighted template overlaps, and g = AᵀC⁻¹y as the three-entry vector of weighted matches to the observed losses. The three rows set the derivatives of the weighted residual objective with respect to q, b₀ and b₁ to zero. All rows use all 1,024 observations, and all three parameters are solved jointly. The notes give the residual form of each equation. Coefficients and scientific results come from the same saved arrays; this revision changes their explanation.

Slide 1 now states that gas enhancement is the sample-minus-reference concentration increase, rather than total ambient concentration. The input q = 50.5814 µg/m³ is simulated and was chosen for the model's 95% predicted detection target under the assumed, unmeasured 0.001 dB calibration residual. It is not an ambient pollution measurement or a concentration obtained from HITRAN; HITRAN supplies the spectroscopic response.

Slide 5 explicitly labels its three displayed rows as examples from the full 1,024-row matrix. Slide 9 explains that one tone gives one equation for three unknowns in this fit, while distinct spectral templates across the band permit joint estimation. Repeated pilots are already averaged within each tone; the subsequent covariance-weighted fit combines all tone losses without collapsing their frequency pattern into one mean. A plain mean cannot separate gas from an unknown common gain shift. Multiple tones combine independent noisy observations, with correlations accounted for by C. This is an identifiability explanation, not a quantified superiority claim over an optimized single-tone design: total transmit power is fixed and divided among tones. Calibration error proportional to the gas template remains indistinguishable from gas. Measuring calibration stability and making a controlled, equal-resource comparison remain future work.

The special spectral average is q̂ = wᵀy, with wᵀ equal to the first row of (AᵀC⁻¹A)⁻¹AᵀC⁻¹. Its signed weights preserve the gas response (wᵀa = 1), cancel offset (wᵀ1 = 0) and cancel slope (wᵀu = 0), while minimizing wᵀCw under the assumed covariance. Slide 9 states these conditions and distinguishes this operation from pilot averaging within each tone. This estimator remains conditional on the specified signal and calibration model.

## V4 formula compatibility, normal quantile and unit review

The v3 package stored 17 SVG formulas with blank one-pixel PNG fallback images. Viewers that used the fallback could show empty formula regions. The builder now rasterizes the original vector formulas at four times their intrinsic resolution and embeds complete PNGs. The LaTeX sources remain available. Slide 6 explains `Phi(z) = P(Z <= z)` and `Phi^-1(0.99) = 2.32635`, the standard-normal cutoff with 99% below and 1% above. Slide 7 links back to that explanation. The inverse denotes a quantile function; `Phi(0.99)` itself is approximately 0.838913.

The receiver unit review independently recomputed the transmit-power split, received link budget, thermal noise `k_B T B`, linear SNR, normalized complex pilot variance, differential logarithmic covariance and detection threshold from the saved arrays across all 1,024 tones. At tone zero, received reference power is −97.59959675 dBm, noise power is −97.42699177 dBm in 9.765625 MHz, and linear SNR is 0.96103566. After 266,880 pilots per acquisition, normalized complex-mean variance is 3.8989213 × 10⁻⁶. Differential thermal loss SD is 0.01715089 dB, and adding the assumed 0.001 dB calibration residual gives total SD 0.01718001 dB. The replayed covariance differs from the saved array by at most 3.47 × 10⁻¹⁸ dB². The 13 existing zenith tutorial tests pass.

There is no dBm/dB labeling error in these equations. Absolute power uses dBm; attenuation and gain changes use dB. The small-error relative power SD corresponding to 0.001 dB is approximately 0.0230%, and the earlier design's 0.0001 dB corresponds to 0.00230%. Both are assumed calibration stability levels. Renaming them as dBm or treating the same numbers as linear fractions would change their meaning. These interpretations follow the linked [RF unit reference](https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gettingstarted/content/concepts_decibels.htm).

This example contains thermal noise and correlated calibration error, with no separate additive-interference process. Independent interference requires summing noise and interference powers in watts before computing SINR; coherent or pilot-correlated interference may cause bias. No interference performance claim or new sensing experiment is introduced. Remaining work is to measure calibration stability and interference with the intended receiver, then update the covariance and validate the frozen detector against independent concentration measurements.

## Pilot and calibration examples

A pilot is a complex symbol whose transmitted value the receiver knows. After synchronization, the assumed observation is R = hX + W. For equal energy unit magnitude pilots, dividing each observation by X removes the known transmitted modulation. Averaging the resulting values estimates the channel h. With the noiseless normalized channel h = 0.9985985923, pilots X = 1 and X = j yield received values 0.9985985923 and j0.9985985923. Both divisions recover the same h. These two rows illustrate arithmetic, rather than presenting measured samples.

The example allocates 30 full pilot OFDM symbols in each 10,000 symbol frame. Each full pilot symbol supplies one known value on every tone. In each 10 s acquisition, floor[10/(10,000 × 112.4 ns)] = 8,896 complete frames give 266,880 pilots **per tone**. This count applies separately to reference and sample. Independent thermal variance scales as 1/M, while standard deviation scales as 1/√M. A persistent gain change survives averaging. Known pilots estimate the combined propagation and instrument response, so an independent calibration model is still needed to separate them.

Calibration estimates and corrects the instrumental response. Error is the uncorrected differential response in the reference/sample comparison. With a multiplicative instrument response g, the loss error is −20 log₁₀|g₁/g₀| after accounting for the applied correction.

- A remaining 0.001 dB gain drop produces an amplitude ratio of 0.9998848774 and an apparent +0.001 dB loss with unchanged gas. Dividing by the first tone coefficient alone would imply 4.15248 µg/m³. The full fit absorbs an exactly constant error into its gain offset, so this single tone calculation is not a false detection prediction for the full detector.
- An error eₖ = aₖ × 1 µg/m³ exactly imitates that concentration across every tone. Spectral observations alone cannot identify its origin. This is a constructed identifiability example, not a measured drift or an assertion that typical drift takes that shape.

The **assumed, unmeasured 0.001 dB** calibration residual specifies a standard deviation, not a fixed bias or an error bound. Its saved first tone draw is −0.0020537566 dB. The simulated thermal loss of +0.0015899416 dB plus that draw gives y₀ = −0.0004638149 dB. In physical measurements this residual is already in the measured channel, so one must not add a second calibration error term during processing.

## Result and evidence

The saved full precision normal equations give q̂ = 39.42467555 µg/m³ and null standard deviation s₀ = 12.73127783 µg/m³. The selected one sided 1% false alarm criterion gives q_th = 29.61738111 µg/m³. The simulated observation exceeds this threshold. This remains conditional on ideal tracking, matched background, 20 s total acquisition and an **assumed, unmeasured 0.001 dB** residual.

Under those same conditions, the selected input q = 50.58139660 µg/m³ is the predicted 95% response concentration. The retained 10,000 simulated trials yield 94.75% response there and 1.31% at 1 µg/m³. No new experiment or sensitivity result is introduced by this presentation revision.

Sources are attached to every page and expanded in the notes:

- [HITRAN definitions and units](https://hitran.org/docs/definitions-and-units/) and [HAPI](https://hitran.org/hapi/) support the molecular line calculations.
- [ITU P.835-7](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en) supplies the standard atmosphere and [ITU P.676-13](https://www.itu.int/rec/R-REC-P.676-13-202208-I) supports background propagation and emission.
- The [hardware and supervisor response](54_supervisor_revision_2026_10_05.md) records the scope of each published hardware precedent.
- [Saved numerical steps](../results/zenith_worked_steps/worked_steps.json), [complex observations](../results/zenith_worked_steps/complex_receiver_steps.csv), [normal equations](../results/zenith_worked_steps/normal_equations.npz) and [repeated trial results](../results/zenith_single_compound/receiver_control.csv) supply the numerical example.

The slides pin repository source URLs to commit d4a25c4 so the cited inputs remain identifiable after this documentation update.

## Reproduction

From the repository root, using the same Python and bundled Node dependencies as the [earlier presentation](56_zenith_example_presentation.md):

```powershell
$env:DECK_PROFILE = 'compact'
py -3.12 scripts/prepare_zenith_compact_slides.py
py -3.12 scripts/render_zenith_equations.py
# Use a new filename for each revision.
$env:DECK_NAME = 'zenith_compact_example_v6.pptx'
node scripts/build_zenith_compact_slides.mjs
py -3.12 scripts/package_zenith_pdf.py
```

The preparation step reads the saved experiment and checks the pilot count, complex noise variance, pilot division example, calibration conversion, observed loss and matrix solution. Tables and the spectrum chart remain native PowerPoint objects, including the chart's data workbook. Equations retain vector and LaTeX source, while the PowerPoint embeds complete PNG images for compatibility. The PDF reproduces the nine slide images with page bookmarks and source hyperlinks. Its searchable text companion is the Markdown notes file.

## Limitations and next steps

The known pilot values do not establish a calibrated hardware chain. The fixed 90° path over 20 s assumes ideal corrections for satellite motion. The height profile, instrument residual covariance, line wing treatment and matched atmospheric background are modeling assumptions. The fitted gain coefficients can absorb spectral components of noise and are not independent measurements of hardware drift.

Measure paired blank stability and its covariance with the intended receiver and acquisition timing, then evaluate independently measured gas concentrations with a frozen calibration procedure. Height profile recovery, changing mixtures and multiple receiver imaging need new identifiable models and evidence. The presentation makes the existing conditional calculation easier to follow, while those scientific requirements remain open.
