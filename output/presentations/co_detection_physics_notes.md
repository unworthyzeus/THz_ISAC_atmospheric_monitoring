## 1. Can we detect CO?

This presentation answers two questions: can we detect CO through the channel, and why is its absorption a smooth curve rather than a set of sharp bands? We begin with the physical mechanism, then connect it to the signal we would have to measure.

The active case is CO in h(f,l) from 60 to 1000 GHz, initially without receiver noise. The decorative cover image is reused from the previous presentation and represents no measured data. Quantitative examples use the saved HITRAN and ITU calculation.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 2. Can we detect it? The answer depends on what is known

Yes: in the ideal case, CO changes the channel and a perfectly matched reference lets us recover its added absorption. But if the atmosphere is completely unknown, the same observation can have several explanations. We have not yet established a practical detection limit.

This is conditional observability, not a hardware sensitivity result. It assumes a nonzero response, exact spectral and atmospheric knowledge, exact calibration and adequate numerical precision. The chosen concentration is an input to the example, not a minimum detectable concentration.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 3. The electric field can excite CO rotation

CO has a permanent electric dipole, so the wave’s electric field can drive changes in its rotational state. The energy difference sets the resonance frequency, and the allowed transitions give the sequence of line centers. This explains where the peaks occur, but not yet their width.

The electric dipole interaction is minus the dot product of dipole and field. NIST lists a nonzero CO ground state dipole. Here h_P is Planck constant, distinct from channel h, and B is in Hz. The rigid rotor is an approximation; centrifugal distortion shifts accurate frequencies. This is driven absorption in the weak field regime, not a literal classical molecule rotating at every incident frequency.

- [dipole](https://cccbdb.nist.gov/diplistx.asp)
- [rotor](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules)
- [jpl](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat)

## 4. Collisions interrupt the molecular phase

Collisions perturb the molecular environment and interrupt the phase of its response to the field. A response that loses coherence quickly cannot have an infinitely sharp frequency. In the simple Lorentz model, the first CO line at one atmosphere corresponds to an effective coherence time of about 66 picoseconds.

A(t) is an exponential coherence envelope, not a measurement of the instantaneous electric field. The Lorentz HWHM in Hz obeys gamma = 1/(2 pi T2). The plotted T2 values are inferred from the HITRAN air width and linear pressure scaling. T2 is not generally the mean time between collisions or the population lifetime; phase can be lost without population relaxation. No independent time domain experiment is claimed.

- [dephasing](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2009/c9108a344550e61973b5ecb4379cdf1e_MIT5_74s09_lec09.pdf)
- [coherence](https://ocw.mit.edu/courses/5-35-introduction-to-experimental-chemistry-fall-2012/18a908091e0258ba553794ac1cd0a517_MIT5_35F12_Module_1LS2.pdf)
- [hitran](https://hitran.org/docs/definitions-and-units/)

## 5. Thermal motion gives different Doppler shifts

Even at one temperature, molecules have different velocities along the beam, so they see slightly different frequencies through the Doppler effect. The thermal velocity distribution produces a Gaussian profile. For this CO transition at 296 kelvin, its full width is about 0.268 megahertz.

The nonrelativistic shift uses the velocity component along the ray; its sign depends on the chosen direction. The Gaussian standard deviation is f0 sqrt(k_B T/m)/c. The displayed curve is normalized in MHz and uses the main CO isotopologue mass, not an invented width. Random thermal motion is part of the gas physics, even when receiver noise is excluded.

- [broadening](https://physics.nist.gov/Pubs/AtSpec/node20.html)
- [mats](https://pages.nist.gov/MATS/MATS%20Summary.html)

## 6. At atmospheric pressure, collisions set most of the width

The Voigt profile combines Lorentz broadening from collisions with Gaussian broadening from thermal motion. Here, pressure broadening is about eighteen thousand times larger than the Doppler width, so collisions dominate. Increasing pressure spreads the same normalized line area over a wider frequency range.

The asterisk denotes convolution, not pointwise multiplication. These are FWHM comparisons for the first line at 296 K; they do not apply universally to all species, pressures or frequencies. Pressure also shifts the center slightly. More accurate line profiles can be required for precision retrievals, especially outside isolated line cores.

- [hitran](https://hitran.org/docs/definitions-and-units/)
- [mats](https://pages.nist.gov/MATS/MATS%20Summary.html)

## 7. Why the curve in your image is smooth

The curve in the original image was calculated for acetonitrile, not CO. It adds broadened line contributions through an atmosphere whose pressure and temperature change with height, so the result can look smooth across a small frequency window. That smooth appearance does not by itself prove continuum absorption or identify the gas.

The plotted numbers reproduce gas_db_per_ug_m3 times the saved true_q_ug_m3 from the historical example. They are used solely to explain the supplied image. The generating calculation uses Voigt line cross sections integrated over altitude. No transition by transition decomposition is presented, and no old detection threshold or performance claim is reused. True continuum terms such as water continuum and collision induced absorption are separate model contributions.

- [oldcurve](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/scripts/prepare_zenith_compact_slides.py)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [continuum](https://hitran.org/mtckd/)
- [cia](https://hitran.org/cia/)

## 8. Three physical steps connect a molecule to the channel

We first add the individual molecular lines to obtain the absorption cross section. We then multiply by molecular density and integrate along the path to obtain optical depth. Beer-Lambert converts optical depth into transmission: the exponent is minus tau for power and minus tau over two for channel amplitude.

The path integral runs from 0 to l. S and V must use the same frequency or wavenumber convention and V must be normalized in that variable. The implementation evaluates HITRAN quantities in wavenumber units. This is a dilute gas, weak probe absorption model. Under fixed local temperature and pressure, tau_c = sigma(f) N_c(l). Background gas loss, geometry and instrument response multiply the chemical field transmission.

- [beer](https://hitran.org/docs/cross-sections-definitions/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [hitran](https://hitran.org/docs/definitions-and-units/)

## 9. CO provides a sequence of spectral features

The CO model produces eight main rotational features between 60 and 1000 gigahertz. Their heights differ because transition strengths, level populations and linewidths differ. We should compare the whole spectral pattern with the background, rather than assume that the tallest peak is automatically the best sensing band.

This curve reuses the 1 ppm, 20 m scenario, all 146 retained HITRAN main isotopologue transitions and the saved reference temperature of 296 K. A millidecibel equals 0.001 dB. The graph is not measured data and its higher frequency peaks do not account for receiver performance or large background loss. Minor isotopologues add further features.

- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
- [jpl](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat)
- [mats](https://pages.nist.gov/MATS/MATS%20Summary.html)

## 10. Observe the chemical loss through a channel ratio

We measure the channel at each frequency and path length, then compare it with a matched reference without the added CO. Dividing their magnitudes removes the shared channel factors, and the logarithm gives the extra CO optical depth. If the reference contains ambient CO, we retrieve the enhancement above that reference.

The calibrated magnitude model is |h| = |g h_fs| exp[-(tau_m+tau_c)/2]. A matched reference cancels g, h_fs and tau_m. The result is chemical magnitude transmission, not a complete reconstruction of molecular dispersion or phase. An exactly known physical background can replace a reference measurement only to the accuracy of its assumptions.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [beer](https://hitran.org/docs/cross-sections-definitions/)

## 11. Path length changes the gas column that the wave crosses

Changing the path length tells us how much of the gas cloud the wave has crossed. Here the extra CO loss increases only between 20 and 40 metres, then becomes constant. The integrated signal gives a gas column; concentration also requires the cloud length or additional spatial information.

The saved matrix has different frequencies and actual path lengths, not repeated observations of one fixed link. For nested paths through a stationary medium, changes of optical depth with l reveal newly traversed segments. Receivers all beyond the cloud see the same added column. Geometric and atmospheric loss still grow outside the cloud. This does not constitute tomography.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)

## 12. The predicted signal is small, even when it is identifiable

At 115 gigahertz, the amplitude change in this example is only about 0.33 parts per million. It grows at higher CO lines, but some of those frequencies also suffer much greater atmospheric loss. These numbers tell us the signal scale an instrument would have to resolve; they do not demonstrate that an instrument can resolve it.

Relative amplitude drop is 10^6 times (1 - |h|/|h0|), distinct from the input 1 ppm molecular mole fraction. Atmospheric losses exclude geometric loss. Rows are evaluated at unshifted catalog centers. The 576 GHz row illustrates nearly 100 dB of modeled atmospheric loss across 200 m, so an exact ratio in arithmetic does not prove a measurable received signal. No gain, power, bandwidth or calibration specification is chosen.

- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)

## 13. A small atmospheric mismatch can dominate the CO loss

At the 345.8 gigahertz CO line, a one percent increase in water partial pressure over the full path changes the loss about 235 times more than our CO cloud does. This is a chosen sensitivity example, not a measured humidity error. It shows why we must model the background, while different spectral shapes may still allow the two effects to be separated.

Computed as 0.2 km times [gamma(1010 Pa water) - gamma(1000 Pa water)] using ITU P.676 at fixed total pressure and temperature. The residual is 0.0186961339 dB; the CO contribution is 0.0000796602409 dB. The 1% change refers to water partial pressure, not one percentage point of relative humidity. This is a deterministic perturbation, not a distribution, threshold or proof of nonidentifiability.

- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 14. CO must be distinguishable from atmospheric changes

With a completely free atmospheric spectrum, there are many ways to divide the total loss between air and CO. If we constrain the atmosphere to known physical parameters, we can instead compare their effects across frequency. CO is distinguishable only when its response cannot be reproduced by the allowed background changes.

After known geometry and gain are removed, r=-2 ln|h/(g h_fs)|. The transformation tau_m to tau_m+q and tau_c to tau_c-q leaves r unchanged whenever both remain admissible. For a local parameterized model, the CO response must lie outside the span of the atmospheric and instrumental derivative responses. Multiple frequencies help only with appropriate constraints; the sensitivity calculation on slide 13 is not a joint retrieval test.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 15. What we can conclude now

Our answer is yes under the stated ideal assumptions: the added CO absorption is observable through the reference ratio. Its smooth spectral shape is caused by finite molecular coherence and thermal motion around discrete transitions. The next step is to quantify reference accuracy and test whether CO remains distinguishable before making a practical detection claim.

The next controlled test needs a known gas column, matched reference acquisitions and measured instrumental stability. Modeling should then vary specified atmospheric parameters and examine response independence or retrieval errors. Other chemicals can be assessed individually after CO, then in mixtures. Species without an in band distinguishable response cannot be identified by this absorption measurement alone; catalog absence is not proof of zero physical absorption.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 16. Appendix: the law behind the smooth line

The continuous profile follows directly from the frequency response of a decaying molecular coherence. An exponential decay produces a Lorentzian, whose width grows as the coherence time becomes shorter. Adding the distribution of Doppler shifts gives the Voigt profile, without introducing receiver noise.

For t >= 0, the real part of the integral of exp(-t/T2) exp[i2 pi Delta f t] is T2/[1+(2 pi Delta f T2)^2]. Normalization gives the displayed L with HWHM gamma. This is an isolated resonance approximation near the line; a full causal molecular response also includes dispersion and may require line mixing and more accurate far wing treatment. Energy conservation is not abandoned: this is the response of moving, interacting molecules, not infinitely long lived isolated levels.

- [coherence](https://ocw.mit.edu/courses/5-35-introduction-to-experimental-chemistry-fall-2012/18a908091e0258ba553794ac1cd0a517_MIT5_35F12_Module_1LS2.pdf)
- [dephasing](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2009/c9108a344550e61973b5ecb4379cdf1e_MIT5_74s09_lec09.pdf)
- [mats](https://pages.nist.gov/MATS/MATS%20Summary.html)

## 17. Sources and numerical evidence

The molecular explanation is supported by NIST and MIT spectroscopy references. The numbers use HITRAN line parameters, JPL line positions and an ITU atmospheric model, with the assumptions recorded in the project. They are model predictions, not field measurements.

New sources were checked on October 15, 2026. The numerical source files were acquired for the October 14 restart. New calculations, source hashes and limitations are in results/co_detection_physics_2026_10_15 and scripts/prepare_co_detection_physics.py. The first CO example remains the common source of the channel and gas column. This deck and its speaking script do not claim validation in a measurement instrument.

- [dipole](https://cccbdb.nist.gov/diplistx.asp)
- [rotor](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules)
- [coherence](https://ocw.mit.edu/courses/5-35-introduction-to-experimental-chemistry-fall-2012/18a908091e0258ba553794ac1cd0a517_MIT5_35F12_Module_1LS2.pdf)
- [dephasing](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2009/c9108a344550e61973b5ecb4379cdf1e_MIT5_74s09_lec09.pdf)
- [hitran](https://hitran.org/docs/definitions-and-units/)
- [mats](https://pages.nist.gov/MATS/MATS%20Summary.html)
- [broadening](https://physics.nist.gov/Pubs/AtSpec/node20.html)
- [jpl](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat)
- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)
- [beer](https://hitran.org/docs/cross-sections-definitions/)
- [continuum](https://hitran.org/mtckd/)
- [cia](https://hitran.org/cia/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
- [oldcurve](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/scripts/prepare_zenith_compact_slides.py)
