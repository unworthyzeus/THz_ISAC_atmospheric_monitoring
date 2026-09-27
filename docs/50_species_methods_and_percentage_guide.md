# Species, methods and interpretation of percentages

This guide accompanies the [complete remaining-work audit](49_completion_audit_and_fixes.md) and the [time/calibration results](51_joint_design_time_calibration_results.md). Every numerical claim is conditional on its frequency schedule, atmosphere, elevation, reference, time and calibration model. None of the new recall values is measured field performance.

## Each gas and its role

| Formula | Name | What is estimated or modeled here |
|---|---|---|
| H2CO | Formaldehyde | An aldehyde; one of the five jointly estimated organic gas enhancements. |
| CH3OH | Methanol | An alcohol; jointly estimated, with its own rotational line pattern and interference with other gases. |
| CH3CN | Acetonitrile, also called methyl cyanide | A nitrile; the strongest low-concentration candidate in the evaluated designs. Its favorable result must retain the calibration and time conditions. |
| CH3Cl | Chloromethane, also called methyl chloride | A halogenated organic gas added to the joint fit using both available HITRAN isotopologues. |
| HCOOH | Formic acid | A carboxylic acid added using two available HITRAN isotopologues. Its rotational intensities have additional model limitations described below. |
| CO | Carbon monoxide | An interfering gas with an unknown amplitude fitted as a nuisance parameter, not one of the five VOC outputs. |
| O3 | Ozone | An interfering gas; its spectrum can overlap the target information. |
| SO2 | Sulfur dioxide | An interfering gas with many rotational lines. |
| NO2 | Nitrogen dioxide | An interfering gas, also fitted rather than silently assumed absent. |
| H2O and O2 | Water vapor and oxygen | Dominant atmospheric absorption/emission background, modeled with the project's microwave atmosphere implementation. They are not VOC outputs. |
| CH4 | Methane | An earlier separate spectral control; it is not a sixth jointly validated gas in these new results. |

Chemical names and database identifiers follow [HITRAN's molecule metadata](https://www.hitran.org/docs/molec-meta/). “VOC” is shorthand for the selected organic gas targets here, not a declaration that every chemical falls within every regulatory definition.

The additional screened candidates are **CH3Br (bromomethane), C2H4 (ethylene), CH3F (fluoromethane), and CH3I (iodomethane)**. Their published HITRAN2024 line lists start above the requested 0–3000 GHz acquisition window. The retained [coverage review](../results/joint_receiver_revision/missing_spectroscopy_review.json) distinguishes this catalog gap from a physical absence of absorption. Adding any of these to quantitative retrieval still requires usable microwave line strengths, atmospheric broadening and validation.

An isotopologue is a molecular form with a different isotope composition, such as chlorine-35 versus chlorine-37. HITRAN line intensities already include natural isotope abundance. Multiplying those intensities by abundance again would incorrectly weaken the modeled spectrum. Total mass concentration uses the natural-mixture molar mass; Doppler broadening uses the individual isotope mass.

## Each PM quantity

Particulate matter is a population of particles, not one gas or one chemical. The size cuts refer to **aerodynamic diameter**, which accounts for settling behavior and depends on density and shape. They are not automatically equal to the physical sphere diameter used in an electromagnetic calculation.

| Output or fraction | Definition and role in the model |
|---|---|
| PM1 | Cumulative mass below 1 µm aerodynamic diameter. The exploratory model only includes the truncated 0.03–1 µm part; it does not model smaller particles. |
| PM1 to PM2.5 fraction | Disjoint mass between 1 and 2.5 µm. It can be added to modeled PM1 to obtain the modeled fine mass. |
| PM2.5, fine PM | Mass below 2.5 µm. The main two-mode calculation represents a truncated 0.03–2.5 µm distribution with assumed fine-particle properties. |
| Coarse PM | Disjoint mass between 2.5 and 10 µm. This is the second independently fitted PM mass in the main calculation. |
| PM10 | Fine plus coarse mass. It includes PM2.5, so treating both as independent disjoint particle populations would double count fine particles. |

For PM10, the correct variance is `Var(fine) + Var(coarse) + 2 Cov(fine, coarse)`. Its false-alarm threshold is included in the eight-output family even though it is a derived quantity. The attempted three-bin fit is retained as a rejected numerical result; it does not provide validated PM1 estimates.

The current fine mode assumes density 1500 kg/m³, physical lognormal median 0.5 µm, geometric standard deviation 1.7 and refractive index 1.5 + 0.01i. The coarse mode assumes 1800 kg/m³, median 4 µm, geometric standard deviation 1.6 and index 1.53 + 0.01i. Aerodynamic bounds are converted before integration. These are inherited exploratory material assumptions, **not measured composition-specific properties**. They do not establish separate soot, salt, organic aerosol or mineral-dust identification. The PM profile decays with an assumed 1000 m scale height.

## From physical parameters to a received signal

1. **Atmospheric layers.** Pressure, temperature and water vary with height using a standard atmosphere or an existing public January weather sounding. The ray is refracted through spherical layers. Gas enhancements use an assumed 1500 m vertical scale height. A recovered value is therefore a surface-equivalent enhancement under that profile, not a direct point measurement at the ground.
2. **Gas absorption.** HITRAN positions, strengths, air broadening, pressure shifts, temperature exponents and partition functions generate a Voigt profile at each layer. The Voigt profile combines Doppler broadening and pressure broadening. Layer cross sections, number densities and path lengths give dimensionless optical depth, which is converted to dB. Beer–Lambert propagation converts this attenuation into received power.
3. **Particle extinction.** Full spherical Mie scattering and absorption are integrated over the size distribution and normalized by dry particle mass. The smaller-particle Rayleigh limit supplies a useful check and explains the weak size information. Particle composition, shape and humidity growth remain uncalibrated.
4. **Noise and the radio link.** Atmospheric emission, receiver noise, antenna gains, path loss and transmit power determine each tone's SNR. The candidate uses one sequential RF chain, sixteen 16 MHz blocks, sixteen 1 MHz tones per block, a cyclic prefix and the existing pilot schedule. Power, reference time, settling and complete frames are all charged.
5. **An independent reference.** Half of the reported total acquisition time is reference transmission and half is sample transmission. Both have thermal uncertainty and both carry communication payload. Time waiting between orbital passes is outside this transmission-time budget. Unknown reference abundance prevents an absolute concentration claim.

Catalog parameters are not uniformly direct measurements. In particular, the [HITRAN2024 paper, page 31](https://hitran.org/media/refs/HITRAN-2024.pdf) describes formic-acid rotational strengths computed using experimentally determined dipole moments. It does not provide measured absolute rotational intensities. The reported receiver intervals do not include all spectroscopy uncertainty.

## Why payload moments improve the sensing information

For QPSK with unit symbol magnitude, write the received symbol as `y = sqrt(S) x + w`, where `S` is signal power and complex Gaussian noise has power `V`. Unknown common phase does not change its magnitude. The second and fourth power moments satisfy

`M2 = S + V`, and `M4 = S² + 4 S V + 2 V²`.

Thus `S² = 2 M2² − M4`. The implementation applies the finite-sample correction before taking the square root and then the logarithmic ratio to the reference. This is the established **M2M4 estimator**, not a new estimator invented in this project. It uses the ordinary constant-modulus payload in addition to the much smaller pilot subset. It estimates the noise contribution instead of assuming the total received energy is all signal.

M2M4 requires the stated modulation/noise model. Changing to arbitrary QAM, unmodeled interference, nonlinear RF distortion or severe intercarrier interference can change its moments. A successful QPSK simulation is not validation for every modem. Invalid moment inversions are failures; they are not clipped into successful detections.

The large response experiments sample the joint asymptotic distribution of the two sample moments and apply the nonlinear inversion. They do not generate every raw OFDM sample. Separate raw IFFT/CP, timing, Doppler, pilot tracking and coded-packet controls test bounded waveform cases. Those raw controls are not a Monte Carlo field recall estimate.

## How gases and particles are fitted together

The linearized attenuation model is `a = D c + N beta + e`. Columns of `D` are the five gas and two PM signatures. Columns of `N` describe gain offset/slope, background amplitude and the four interfering gases. Generalized least squares uses the full spectral covariance, projects out nuisance components and returns a signed concentration estimate `c_hat = H a`.

The numerical checks require `H D` to reproduce the target identity after scaling and `H N` to reject nuisance directions. The implementation uses whitening and an SVD, avoiding the conditioning penalty of forming normal equations. Targets that fail rank or numerical checks are rejected. Forcing estimates to be positive would change the statistical model and cannot create missing information.

The full QPSK and magnitude Fisher bounds in the preceding study explain the information available under the likelihood. M2M4 was already close to the bound in the reference state. The new improvement comes from choosing more informative frequencies while retaining the same acquisition resources, not from claiming an impossible estimator gain.

## Time and calibration jointly determine the 95% limit

For a fixed frequency design, the local covariance is

`C(t, sigma_cal) = diag(Vsample(t/2) + Vreference(t/2)) + sigma_cal² K`.

`K` has exponential 10 GHz frequency correlation in the nominal study. The thermal terms decrease with the number of retained payload symbols. The additional calibration residual is held fixed within an acquisition and drawn once between independent simulated acquisitions. It **does not decrease once per symbol**. Longer observation therefore cannot remove this persistent covariance floor.

The table axes are **2, 20 and 100 seconds total**, and **0, 0.0001 and 0.001 dB residual standard deviation**. Zero is the ideal additional-residual benchmark; thermal and reference uncertainty remain. Nonzero entries are assumptions, not measured receiver specifications. Random standard deviation is also not a worst-case systematic bound. A constant spectral bias, uncertain atmospheric background and uncalibrated relative hop gains require additional controls.

With eight outputs and a 1% family false-alarm budget, each one-sided test uses `z = Phi^-1(1 − 0.01/8)`. If the local standard deviation is `s_j`, the approximate recall at concentration `c_j` is `Phi(c_j/s_j − z)`. The local 95% power scale is `(z + 1.64485) s_j`. It changes whenever time, calibration, SNR, atmosphere or the other fitted species change.

For the reported response limit, the calculation goes further: positive gas absorption changes SNR and therefore the estimator variance. It solves `c95 = z s_null + 1.64485 s_positive(c95)` before running the response trials. The equation is restricted to at most 1 dB added absorption. If no valid solution exists there, the result is **no valid 95% limit in the evaluated domain**, rather than a claimed detection at an enormous extrapolated PM concentration.

An arbitrary bounded error `|b_i| ≤ epsilon` produces a worst-case target bias `B_j = epsilon ||H_j||_1`. Protecting both the null threshold and the adverse positive case adds `2 B_j` to the local concentration requirement. This is why an assumed small random residual alone does not guarantee performance under drift.

## Read the percentages correctly

| Quantity | Definition and interpretation |
|---|---|
| Recall or detection probability | `100 TP/(TP+FN)`: the percentage of present targets detected at the stated concentration and operating condition. |
| Miss rate | `100 FN/(TP+FN) = 100 − recall`. A 0.2% recall means approximately 99.8% of positives are missed. |
| False-alarm rate | Percentage of absent controls incorrectly detected, reported per target and for any detection in the full family. |
| Specificity | `100 − false-alarm rate`. High specificity alone can coexist with nearly useless recall. |
| Precision | `100 TP/(TP+FP)`. Here it is reported for an artificial 50% positive prevalence; it is not expected field precision. |
| F1 | Harmonic mean of precision and recall, also dependent on the stated evaluation prevalence. |
| Balanced accuracy | Average of recall and specificity. A detector that misses everything can score approximately 50%. |
| Relative concentration bias | `100 mean(c_hat−c)/c`: a signed systematic error percentage. It is not a detection probability. |
| Relative concentration RMSE | `100 sqrt(mean((c_hat−c)²))/c`: includes bias and random estimation error. It can exceed 100%, especially for PM. |
| Negative estimates | Percentage of signed concentration estimates below zero. Retained as a diagnostic instead of hidden through clipping. |
| Exact 95% confidence interval | Binomial interval describing finite simulation uncertainty in a measured simulation fraction. It is distinct from a 95% detection target and does not include uncertain physics or calibration. |

The low-concentration VOC comparisons use 1, 5 and 10 µg/m³. PM comparisons use declared mass values with the same time/calibration grid. Low recalls remain visible to at least two decimal places, and zero observed hits are accompanied by a nonzero confidence upper bound. The 95% rows state the actual concentration required and its empirical recall; a simulated 94.8% or 95.2% is reported as observed rather than forced to 95.00%.

Gas ppm values are surface-equivalent mole fractions computed from the local pressure, temperature and natural molar mass: `ppm = c_ug_m3 R T/(p M_g_mol)`. PM has mass units and no meaningful gas ppm conversion. A short slant-path enhancement and a daily ambient ground-level health metric are different observables. This study does not establish compliance.

## Why useful PM remains missing

For a small sphere with wave number `k`, radius `r`, density `rho` and `q = (m²−1)/(m²+2)`, the leading mass-normalized Rayleigh terms are proportional to `3 k Im(q)/rho` for absorption and `2 k⁴ r³ |q|²/rho` for scattering. With the assumed frequency-independent material index, these have smooth frequency shapes. A fitted gain slope removes the leading linear absorption shape; multiple size modes share the leading scattering shape and differ mainly in amplitude.

At sub-THz wavelengths, these micrometer particles are very small. Full Mie terms can technically break the degeneracy, but their useful information is extremely weak in this study. This explains both the poor mass limits and the unstable extra size split. More averaging or a more elaborate optimizer cannot by itself make nearly indistinguishable signatures reliable. Independent size/composition information, another informative observable or a different validated sensing design is still required.
