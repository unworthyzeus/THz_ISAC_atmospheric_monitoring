# Restart: observing chemical absorption in h(f, l)

Date: October 14, 2026. First species: CO, as selected by the user.

## Active scope

This brief replaces the previous research plan and task lists. The general objective is to establish which chemicals can be distinguished through their effects on a propagation channel between **60 and 1000 GHz**. The immediate question for the supervisor meeting next week is:

> How can we observe the chemical attenuation factor a_c in the channel h(f, l), and what must be known to separate it from atmospheric attenuation?

Start with one gas, multiple frequencies and path lengths, and no receiver noise. Later, examine other gases individually, then mixtures. An angular coordinate can be added later as h(f, l, theta). Previous detector performance, communication designs, satellite geometry and proposal tasks are historical material, not requirements of this restart.

## Main result

For a calibrated channel magnitude and an exactly matched reference h_0 containing the same geometry and background atmosphere,

\[
|a_c(f,l)|=\frac{|h(f,l)|}{|h_0(f,l)|},\qquad
\tau_c(f,l)=-2\ln\frac{|h(f,l)|}{|h_0(f,l)|}.
\]

Thus chemical absorption is observable as an additional optical depth or loss. **The reference, or equivalent independent knowledge of the background, is the essential information.** If both atmospheric and chemical attenuation are unrestricted unknown functions, h alone cannot determine their individual factors, even with zero noise.

This is an identifiability result. It does not establish a practical detection limit or experimental sensitivity.

## 1. Define the channel and the distances first

Use s for position along the ray, l for atmospheric path length, and d for total transmitter to receiver distance. In a horizontal terrestrial example entirely inside the atmosphere, d = l. In other geometries they need not be equal.

The absorption only magnitude model is

\[
|h(f,l)|=|g(f,l)|\,|h_{\rm fs}(f,d)|
\exp[-\tau_m(f,l)/2]\exp[-\tau_c(f,l)/2],
\]

\[
\tau_m(f,l)=\int_0^l\alpha_m(f,s)\,ds,\qquad
\tau_c(f,l)=\int_0^l\alpha_c(f,s)\,ds.
\]

Here g is the instrument and antenna response left outside the geometric model; it is assumed known, corrected or identical in the reference for the first case. Each alpha is a **power** absorption coefficient in 1/m. Optical depth tau is dimensionless. Amplitude transmission is exp(-tau/2), whereas power transmission is exp(-tau). The power law is the Beer–Lambert relation; [HITRAN's cross section definition](https://hitran.org/docs/cross-sections-definitions/) gives the equivalent logarithmic transmission relation.

For unit gain antennas in far field free space,

\[
|h_{\rm fs}|=\frac{c_0}{4\pi f d},\quad
G_{\rm fs}=|h_{\rm fs}|^2,\quad
L_{\rm fs}=1/G_{\rm fs}.
\]

Therefore a positive path loss L_fs is divided out as a loss, not multiplied into h as though it were a transmission factor. The supervisor's product P a_m a_c is valid once all three factors use the same amplitude or power convention. P also generally depends on frequency.

If h denotes the full complex channel, propagation phase and molecular dispersion also belong in the model. The current calculation addresses |h|, sufficient for the absorption question. It does not claim to reconstruct molecular phase.

For a dilute gas under fixed local conditions,

\[
\alpha_c(f,s)=n_c(s)\,\sigma_c(f;T(s),p(s),\text{bath composition}),
\]

where n_c is number density and sigma_c is cross section. With constant T and p,

\[
\tau_c(f,l)=\sigma_c(f)N_c(l),\qquad N_c(l)=\int_0^l n_c(s)ds.
\]

N_c is a column amount. A single integrated path generally identifies this column rather than concentration and cloud thickness separately. For a uniform cloud N_c = n_c L_cloud, so those two factors require additional information to separate.

## 2. Three ways to supply the atmospheric information

| Approach | What is needed | What can be recovered |
| --- | --- | --- |
| Matched reference | Same path, instrument response, T, p and water vapor, with a known reference gas column | Change in chemical optical depth; absolute optical depth only if reference gas contribution is known |
| Known physical background | Geometry, calibration, atmospheric state along the path and a suitable propagation model | Chemical residual relative to that background model |
| Joint inference | Parameterized atmosphere, molecular spectra and enough independent spectral or spatial information | Gas and background parameters only if their effects can be distinguished |

For the matched reference,

\[
h_0:\quad |h_0|=|g|\,|h_{\rm fs}|e^{-\tau_m/2},
\qquad
\Delta A_c=-20\log_{10}(|h|/|h_0|)
=\frac{10}{\ln 10}\tau_c.
\]

Equivalently, for normalized received power gain G = |h|^2, use -ln(G/G_0) to obtain tau_c. A reference containing ambient CO yields an enhancement relative to that ambient CO, not proof of absolute zero CO before the cloud.

For a modeled background,

\[
\widehat{\tau}_c=-2\ln\left|\frac{h}{g h_{\rm fs}}\right|-\widehat{\tau}_m.
\]

Under ideal calibration its error is tau_m - estimated tau_m. Zero receiver noise does not remove that model error.

[ITU Recommendation P.676-13, Annex 1](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf) provides an oxygen and water based background calculation up to 1000 GHz, including additional continuum terms. Its approximate Annex 2 methods have a narrower frequency range. The model still needs pressure, temperature and water vapor along the path; a standard atmosphere is an assumption about those inputs. Some minor atmospheric species are omitted. Use an explicitly selected background model and avoid counting its oxygen, water and continuum absorption a second time with a separate model.

## 3. Why zero noise does not guarantee separation

After removing known geometry and gain, the observation is

\[
r(f,l)=-2\ln|h/(g h_{\rm fs})|=\tau_m(f,l)+\tau_c(f,l).
\]

Replacing the pair by (tau_m + q, tau_c - q) leaves r unchanged for any q that respects the allowed model and nonnegativity constraints. In particular, an unrestricted atmospheric term can absorb the entire chemical term. More frequencies do not solve an unrestricted functional decomposition.

If the atmosphere instead belongs to a known parameterized family, local changes obey

\[
\delta\mathbf r=\mathbf J_m\delta\boldsymbol\theta_m+
\mathbf s_c\delta N_c.
\]

The target column is locally distinguishable if its spectral response s_c is not in the span of the uncertain atmospheric responses J_m. This is a local condition; it does not prove global uniqueness of a nonlinear fit. For several gases, write r = tau_m(theta) + S N and inspect whether each target adds an independent column after accounting for the background. A visible line alone does not establish unique molecular identification in an unspecified mixture.

In the ideal exact model, an arbitrarily small nonzero column with a distinct nonzero response is observable in principle. A practical minimum concentration needs specified measurement precision, calibration, environmental uncertainty and an error criterion. Even without receiver noise, line parameters and the background may remain uncertain. Mathematical nonzero line wings should not be used to declare every gas practically detectable everywhere.

## 4. What the l dimension adds

H[i,j] represents h(f_i,l_j). The index j must correspond to a genuinely different path length, not repeated samples of the same link. Options include a controlled variable path cell or receivers at known positions along a common ray.

For nested paths through the same stationary medium,

\[
\partial_l\tau_c(f,l)=\alpha_c(f,l).
\]

Differences between neighboring path lengths isolate the newly traversed segment. For a uniform cloud between positions s_a and s_b,

\[
\tau_c(f,l)=n_c\sigma_c(f)\max(0,\min(l,s_b)-s_a).
\]

It is zero before the cloud, grows inside it, and remains constant after it. Added distance outside the cloud still changes free space and atmospheric loss. A set of receivers all beyond the same cloud supplies the same chemical column under this homogeneous model. Different paths that are not nested do not justify the derivative formula.

At fixed T and p, the chemical optical depth matrix factors as sigma(f) N(l), so its rank is at most one for one gas. This does not make an unknown atmosphere automatically separable: another homogeneous absorber also has an outer product structure. Distinct spectra or independent background constraints remain necessary.

## 5. Why discrete transitions produce smooth absorption

The center frequency of a transition is set by an energy difference,

\[
f_{ij}=(E_j-E_i)/h_{\rm P}.
\]

Discrete allowed energies do not imply a rectangular absorption band. The hypothetical infinitely sharp line would be a delta peak at its center, not a step with constant absorption over an interval.

Real resonances have finite coherence times. As a simple derivation, a decaying molecular polarization exp(-t/T_2) exp(i 2 pi f_0 t) has an absorptive frequency response proportional to

\[
\Re\int_0^\infty e^{-t/T_2}e^{i2\pi(f-f_0)t}dt
=\frac{T_2}{1+[2\pi(f-f_0)T_2]^2}.
\]

This is a continuous Lorentzian response, with half width gamma = 1/(2 pi T_2). Collisions shorten coherence and alter the molecular environment. Thermal velocities produce a distribution of Doppler shifts. Natural lifetime broadening also exists, but typically does not set atmospheric microwave linewidths. These are physical effects, not receiver noise; setting receiver noise to zero leaves them present. [NIST's discussion of line broadening](https://physics.nist.gov/Pubs/AtSpec/node20.html) distinguishes the principal broadening mechanisms.

An initial local line model is

\[
\sigma_c(f;T,p)=\sum_j S_j^{(f)}(T)\,V_j(f-f_j;T,p),
\qquad\int V_j(f)df=1,
\]

\[
V=L*G,\qquad
L(\Delta f)=\frac{1}{\pi}\frac{\gamma}{\Delta f^2+\gamma^2}.
\]

L represents collision dominated broadening, G represents thermal Doppler broadening, and their convolution is the Voigt profile. Neighboring broadened lines can overlap. The instrument may smooth the measured spectrum further. A smooth spectrum need not contain an additional physical continuum.

There are also genuine continuum contributions, including collision induced absorption and water vapor continuum terms. They must be distinguished from the mere fact that a line profile is continuous. The [HITRAN CIA collection](https://hitran.org/cia/) and [MT_CKD continuum documentation](https://hitran.org/mtckd/) describe separate data and models for these contributions. Line wing and continuum conventions must be compatible when combining them.

Voigt is a starting approximation. Detailed microwave work may need appropriate frequency dependent line shapes, line mixing and more accurate collision physics. [NIST MATS](https://pages.nist.gov/MATS/MATS%20Summary.html) documents richer profiles and how pressure, temperature and bath composition affect their parameters. This example does not validate extrapolated far wings.

## 6. What law to learn

There are three connected pieces, not a single law that predicts all of the spectrum:

| Question | Physical description |
| --- | --- |
| Where are transitions allowed? | Molecular energy levels, transition moments and selection rules |
| How strong and wide is each feature? | Populations, transition strengths, collisions, Doppler broadening and a line profile |
| How does absorption affect the channel? | Beer–Lambert propagation integrated along the path |

For CO in its ground vibrational state, the simplest rigid rotor gives E_J = h_P B J(J+1) with B expressed in Hz, and absorption has J to J+1 transitions near 2 B (J+1). Centrifugal distortion makes the sequence slightly nonuniform. The [NIST diatomic formulation](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules) gives the corresponding corrected rotational frequencies and selection rules.

[JPL's CO catalog](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat) places the first eight ground state lines at approximately **115.271, 230.538, 345.796, 461.041, 576.268, 691.473, 806.652 and 921.800 GHz**. These are line centers, not certified usable sensing bands. Other isotopologues have additional features. JPL line positions and intensities alone are insufficient for an atmospheric width model.

The numerical example downloads HITRAN positions, strengths, air widths and shifts. At its chosen 296 K, tabulated reference strengths can be used directly. For other temperatures, use the partition function and population correction rather than keeping S fixed. [HITRAN parameter definitions](https://hitran.org/docs/definitions-and-units/) document these quantities and their units.

HITRAN uses wavenumber in cm^-1: f_GHz = 29.9792458 times wavenumber. The example evaluates profiles in wavenumber units. If converting a normalized profile to frequency, transform its normalization and integrated strength consistently; replacing the horizontal axis alone is not sufficient for an integral calculation.

## 7. The attached curve

The exact figure title occurs in [prepare_zenith_compact_slides.py](../scripts/prepare_zenith_compact_slides.py), where the ordinate is the saved gas response per concentration multiplied by a chosen concentration. Its input comes from [run_zenith_tutorial.py](../scripts/run_zenith_tutorial.py), which sums Voigt cross sections for **acetonitrile, CH3CN**, integrated over a specified altitude profile.

It is a predicted differential gas loss over 230–240 GHz, not an experimental spectrum and not a CO curve. The molecular line profiles, their overlap and integration through varying pressure and temperature explain why the generating model can produce a broad smooth feature. The figure alone cannot show which individual transition contributes how much, establish a physical continuum, or validate its far wing treatment. No old detector performance is carried into the new example.

## 8. Reproducible first CO example

Run from the project root:

```powershell
python scripts/restart_co_observability.py
```

Add `--check-hapi` to compare five spectral cross sections against the separate [HAPI implementation](https://hitran.org/hapi/) using the same physical assumptions. That optional verification requires HAPI and gives a maximum relative difference of approximately 1.44e-13 in the saved run. Agreement between implementations checks the calculation; it does not validate those assumptions against an experiment.

Required libraries: NumPy, SciPy and Matplotlib; HAPI is needed only if the saved HITRAN source file is absent. The example fetches public HITRAN data for molecule 5, isotopologue 1, with line centers from 0 to 3000 GHz, and independently checks the eight in band ground state centers against JPL. The wide catalog includes contributions from transitions centered outside the observation band. It does not establish convergence of remote wing physics.

Chosen, unmeasured scenario: homogeneous T = 296 K, p = 101325 Pa, water partial pressure = 1000 Pa; d = l; l from 1 to 200 m; a 1 ppm excess CO cloud between 20 and 40 m. The background is exactly known ITU P.676; instrument response is exact; receiver noise is absent. CO uses the dilute trace limit of air broadened Voigt profiles and the main isotopologue, with HITRAN's reference abundance weighting. Minor isotopologues, explicit water perturber corrections and non-Voigt effects are omitted.

The matrix has 4717 frequencies by 200 lengths. Its saved quantities are |h|, |h_0|, |a_c|, true tau_c and recovered tau_c. The plots are [frequency and length overview](../results/restart_2026_10_14/co_observability.png) and [path length behavior](../results/restart_2026_10_14/co_path_length.png). Machine readable outputs include [line examples](../results/restart_2026_10_14/co_line_examples.csv), [matrices](../results/restart_2026_10_14/channel_matrices.npz) and [source hashes and checks](../results/restart_2026_10_14/manifest.json).

At the unshifted 115.271 GHz line center, this chosen 1 ppm over 20 m scenario gives approximately 2.89e-6 dB of additional loss and |a_c| = 0.9999996673. At 230.538 GHz it gives 2.33e-5 dB. These are forward predictions for a chosen column, not detection limits. A taller peak at a higher frequency is not automatically preferable once atmospheric loss and real measurement limits are considered.

The first line's air broadened half width at 296 K and 1 atm is about 2.407 GHz, so its Lorentz full width is approximately 4.815 GHz. This makes the distinction between a discrete center and a finite absorption profile concrete. The pressure comparison plot holds integrated profile area fixed to isolate the broadening mechanism; it is not a comparison of equal ppm gas samples at different pressures.

The inversion recovers tau_c with maximum absolute numerical error below 6e-16 and recovers the selected concentration to below 1e-8 ppm error. Other checks verify normalized line area, agreement with JPL centers to better than 0.2 MHz, zero chemical loss before the cloud, a constant chemical column after the cloud, and the ambiguity of an unrestricted background. The manifest records the actual errors.

This is a consistency calculation using the same forward assumptions in generation and inversion. It is not an independent validation of the physical model. Some water resonances produce extremely small nonzero channel magnitudes in this ideal calculation. Computing their exact ratio does not demonstrate that an instrument could measure those magnitudes.

## 9. What was done and what remains

**What was done:** reset the active scope; derived the observable, amplitude and power conventions, and separation conditions; explained line broadening and the attached curve; obtained fresh CO line data; generated a noiseless frequency and length matrix and verified its inversion.

**Why:** to answer the new supervisor question before choosing a detector or making detectability claims.

**Result obtained:** chemical optical depth is recoverable relative to a matched or known background. Arbitrary atmosphere and chemical factors are not separately identifiable. The CO example demonstrates the algebra and the finite width of real transitions under an explicit model.

**Remaining work for the meeting:** decide how the reference would be acquired; specify what is actually known about T, p, humidity, background CO, geometry and cloud thickness; then repeat the CO inversion with uncertain atmospheric parameters. A comparison with an alternative forward model or controlled measurement is needed before judging physical accuracy.

**Risks and limitations:** reference mismatch, unknown instrumental response, atmospheric model errors, uncertain broadening and remote wings, minor isotopologues, and unmeasurably weak received signals. These are separate from receiver noise. Gas clouds here mean dilute gas mixtures; droplets or particles would introduce other propagation mechanisms.

**Next steps:** first identify whether CO remains distinguishable from the allowed background variations. Then apply the same analysis to other named gases one at a time. Only after that, assess mixtures through independence of their spectral responses. Introduce angles after the path geometry and the meaning of l are settled. Do not classify a chemical as absent or undetectable merely because a chosen catalog has no in band line entry.

## Suggested meeting statement

> In the noiseless case, we can observe chemical absorption as the logarithmic ratio between a channel containing the cloud and a matched atmospheric reference. Without that reference, or a constrained atmospheric model, the two attenuation factors are not uniquely separable. Discrete molecular transitions produce continuous absorption profiles because their coherence is finite and molecules move and collide. CO provides a first concrete case: model its known transitions over 60–1000 GHz, vary the traversed cloud length, and determine which background quantities must be known for its column to remain identifiable.
