# CO concentration, path length and detection requirements

Date: October 15, 2026.

## Purpose and current scenario

The user asked how the strongest CO feature compares with atmospheric loss, what concentration can be detected, and why the earlier path plot plateaued. The user then selected a 200 m path through CO enriched air and a total CO concentration upper bound of 1.5 ppm. The user is editing a separate Drive presentation copy; this update records the calculations and their interpretation in the repository. The existing exported presentation and speaking script retain their original 20 m example.

The model remains a uniform 296 K atmosphere at 101325 Pa, with water partial pressure 1000 Pa and no receiver noise in the forward calculation. The 1 ppm case is a normalization for sensitivity, not a measured or universally typical concentration. Concentrations up to 1.5 ppm are chosen study cases. The extent of an atmospheric plume and the distance that a particular beam traverses within it are different quantities.

## Concentration is relative to a reference

For a matched atmospheric reference, the additional absorption measures the CO enhancement, `delta_C = C_sample - C_reference`. A sample at 1.5 ppm against a reference at 0.1 ppm therefore contributes a 1.4 ppm enhancement. A sample at 0.15 ppm against that reference contributes 0.05 ppm. The 0.1 ppm reference is an explicitly chosen example, not a measured input.

For the same temperature, pressure and frequency, optical depth and decibel loss scale with concentration times gas path length. Thus 0.1 ppm enhancement over 200 m produces the same CO loss as 1 ppm enhancement over 20 m. For a nonuniform atmosphere the quantity is the path integral of cross section times excess molecular number density; simple concentration times distance scaling then needs the appropriate local density and spectroscopy.

The screenshot supplied by the user is not used as a primary source for universal concentration ranges. [NASA's 2019 Amazon AIRS example](https://www.nasa.gov/centers-and-facilities/jpl/nasas-airs-maps-carbon-monoxide-from-brazil-fires/) shows a map at about 5.5 km altitude with color levels near 100, 120 and 160 ppbv and notes that local values can be higher. [NASA's 2018 California example](https://science.nasa.gov/photojournal/carbon-monoxide-transport-from-california-wildfires-july-30-august-7-2018/) uses a 200 ppbv upper color scale and also notes higher local values. These observations support the need to distinguish atmospheric conditions and averaging scales. They do not establish 1.5 ppm as a typical concentration or validate every range in the screenshot. The study retains 1.5 ppm as the user selected upper case.

## The strongest peak and atmospheric attenuation

The strongest modeled CO peak inside 60 to 1000 GHz is at 921.812 GHz. Its catalog center is 921.800 GHz; the small difference comes from the pressure shifted profile and summed line contributions. The calculations reuse the saved HITRAN parameters and ITU P.676 background. The source models and baseline assumptions are documented in [the restart note](59_restart_observability_2026_10_14.md).

At this peak, for a 200 m gas path:

| Quantity | Predicted value |
| --- | ---: |
| CO loss per 1 ppm enhancement | 0.0104802 dB |
| Background atmospheric loss over 200 m | 38.3868 dB |
| Atmospheric power transmission, excluding geometric loss | 0.01450% |
| Extra CO loss for 1.5 ppm against a zero CO reference | 0.0157203 dB |
| Extra CO loss for 1.5 ppm against a 0.1 ppm reference | 0.0146723 dB |

The CO contribution does not have to exceed the whole atmospheric loss. It must be distinguished from the residual error after the background and instrument response are accounted for, and sufficient received signal must remain. A large chemical peak alone does not identify the best measurement frequency. For comparison, the peaks near 691.482 and 806.663 GHz give 0.00553994 and 0.00794614 dB per ppm over 200 m, with atmospheric losses of about 12.98 and 17.76 dB. The optimal operating band also depends on transmitter power, antenna gain, receiver response, bandwidth and calibration.

The background values in this table are the ITU oxygen and water model, including its continuum terms. A reference containing 0.1 ppm CO would also have about 0.001048 dB of CO absorption at this peak; that shared reference contribution cancels in the matched ratio.

All eight peaks are in [the peak comparison](../results/co_detection_requirements_200m_2026_10_15/peak_comparison.csv). The [absolute and reference concentration table](../results/co_detection_requirements_200m_2026_10_15/absolute_and_reference_concentrations.csv) gives the concentration interpretation explicitly.

## What concentration can be detected

In the exact noiseless model with exact background and calibration, every positive CO column with a nonzero response is mathematically observable. There is no positive minimum concentration in that idealization. A practical threshold requires an error model; a physical spectrum alone cannot supply one.

The model does supply a quantitative sensitivity requirement. At the strongest peak:

`extra_loss_dB = 0.0104802 * enhancement_ppm * gas_length_m / 200`.

To make the phrase "reliably detectable" explicit, consider one preselected frequency and a positive CO signal. Assume that the final differential loss error is Gaussian with known standard deviation sigma, zero mean and no systematic bias. This sigma includes reference uncertainty and any residual atmospheric or instrumental error represented by that model; it is not merely the receiver noise specification. At a 1% false alarm probability per test and 95% detection probability, the required signal is:

`signal / sigma >= Phi_inverse(0.99) + Phi_inverse(0.95) = 3.97120`.

Consequently, for 200 m:

| CO enhancement | CO signal near 921.812 GHz | Maximum residual standard deviation for the stated criterion |
| --- | ---: | ---: |
| 0.01 ppm | 0.0001048 dB | 0.0000264 dB |
| 0.05 ppm | 0.0005240 dB | 0.0001320 dB |
| 0.10 ppm | 0.0010480 dB | 0.0002639 dB |
| 1.00 ppm | 0.0104802 dB | 0.0026390 dB |

For example, if the final residual standard deviation were 0.001 dB, the conditional limit would be 0.3789 ppm enhancement, or 0.4789 ppm total against a 0.1 ppm reference. If it were 0.0001 dB, those values would be 0.03789 and 0.13789 ppm. These error levels are chosen inputs, not demonstrated equipment capabilities. Persistent bias, uncertain error distributions, frequency searches and searches over multiple chemicals require different criteria. The separate [loss resolution table](../results/co_detection_requirements_200m_2026_10_15/conditional_ppm_thresholds.csv) treats its inputs as already reliable resolvable losses, not as standard deviations; it must not be confused with this statistical table.

The 1.5 ppm total case against a 0.1 ppm reference requires sigma no greater than about 0.003695 dB under the same Gaussian criterion. This is an engineering requirement, not an experimental detection claim.

## Separating CO from atmospheric changes

At the strongest peak, changing one uniform atmospheric parameter at a time gives the same additional loss as 1 ppm added CO over 200 m with approximately:

- A water partial pressure increase of 0.2537 Pa from 1000 Pa.
- A temperature decrease of 0.02340 K from 296 K.
- A total pressure increase of 39.55 Pa from 101325 Pa.

These are model sensitivities, not required accuracies for every possible retrieval. A single frequency cannot distinguish these changes. Multiple frequencies can use their different spectral shapes.

A new local calculation evaluates 301 frequencies at 0.1 GHz spacing from 906.812 to 936.812 GHz. The nuisance responses are derivatives with respect to uniform water partial pressure, temperature and total pressure, plus constant and linear calibration terms in dB. Their normalized response matrix has rank five; adding CO increases the rank to six. About 0.733 of the CO response norm remains outside their span, under equal frequency weights. This establishes local independence for this explicitly constrained model. It is not a detection probability, fraction of recovered concentration, global uniqueness proof, mixture result or measured sensitivity. Arbitrary frequency dependent calibration or unconstrained atmospheric profiles can destroy that identifiability. Strong atmospheric absorption in parts of this window also limits what a real instrument can measure.

## Why the previous curve plateaued

The original example explicitly set a cloud start at 20 m and an end at 40 m in [the calculation](../scripts/restart_co_observability.py). It used `gas_length = clip(total_length - 20, 0, 20)`. Consequently, the extra CO loss stayed zero before 20 m, grew from 20 to 40 m, and became constant after 40 m. Those endpoints were chosen illustration parameters. No physical law makes all absorption stop after 20 m.

The revised 200 m gas path contains added CO throughout the plotted 0 to 200 m interval. Its CO loss keeps growing throughout that interval. Background atmospheric absorption and geometric loss also grow. [The comparison figure](../results/co_detection_requirements_200m_2026_10_15/co_path_extent_comparison.png) contrasts the two geometries using the same spectroscopy and 1 ppm enhancement. The original PDF and numerical arrays place the old plateau at 40 m. The user's converted chart screenshot has differently positioned axis labels; the original export was not altered during this numerical follow up.

The loss accumulation follows [Beer–Lambert absorption](https://hitran.org/docs/cross-sections-definitions/). The line strengths and profiles use [HITRAN](https://hitran.org/docs/definitions-and-units/) and the atmospheric calculation uses [ITU P.676-13](https://www.itu.int/rec/R-REC-P.676/en).

## Replacement values for the 200 m presentation example

The saved [200 m evidence](../results/co_detection_physics_200m_2026_10_15/evidence.json) is normalized to 1 ppm enhancement. Near 345.796 GHz the CO loss becomes 0.000796602 dB. The change in water partial pressure from 1000 to 1010 Pa over the same 200 m still gives 0.0186961 dB, so the ratio becomes 23.47, rather than the old 234.70. These values change again with the CO enhancement: they must not be relabeled as a different concentration without rescaling. Amplitude transmission must be recomputed exponentially rather than multiplied by the path length ratio.

The 1.5 ppm total case with 0.1 ppm reference instead gives 0.00111524 dB extra CO loss at this frequency, and a humidity comparison ratio of about 16.76. The original 1 ppm over 20 m numbers remain preserved in the previous presentation record.

## Reproduction, checks and next steps

Run from the repository root with NumPy, SciPy, Matplotlib and Pillow:

```powershell
python scripts/prepare_co_detection_physics_200m.py
python scripts/quantify_co_detection_requirements.py --cloud-length-m 20
python scripts/quantify_co_detection_requirements.py --cloud-length-m 200
```

The 200 m calculation is the default. The 20 m output is retained for comparison. CSV files and JSON summaries include source hashes, scenario assumptions, conditional criteria and limitations. Checks reproduce the earlier catalog center losses, verify path scaling, test the Gaussian operating point analytically, check finite difference stability, solve the equivalent atmospheric changes with the nonlinear ITU model, and verify the local rank increment. The corrected path comparison figure was visually inspected.

The next research step is to select concentration and spatial profiles from a relevant measured plume dataset, and specify a constrained atmospheric and calibration model for the intended link. A receiver and link model or measured repeatability is then needed to turn the sensitivity requirements into an achievable concentration limit. The current result supports conditional CO observability, not general detection of arbitrary chemicals or mixtures. The single main isotopologue Voigt model, trace gas broadening approximation, fixed reference temperature and unvalidated far wings remain limitations.
