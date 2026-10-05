# CH₃CN at 90°: worked calculation for a telecom audience

Slides 1–25 explain the experiment and derive the numerical receiver decision. Slides 26–32 provide calculation details and references.

The spectroscopic records are external physical data. The concentration profile and receiver observations are modeled; no orbital measurement is claimed.

## 1. How a gas concentration becomes a receiver decision

Assume a general telecommunications background. The question is how the project turns a concentration profile into a frequency dependent channel change, then estimates that concentration from noisy measurements. This is the same saved example as the earlier table, now with every physical and statistical step exposed. The spectroscopy records are real database inputs. The concentration profile, hardware and errors are model inputs; the receiver observations are simulated.

Acetonitrile at 90°: one complete numerical calculation
Actual HITRAN parameters, explicit arithmetic and a simulated receiver

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 2. What the four numbers in the original table mean

q is a controlled input; the other three quantities are deterministic predictions from that input. First derive 0.012181 dB from the actual spectroscopy and an assumed profile. Then derive the amplitude ratio. Finally add the modeled observation errors and calculate an estimate, which is 39.4247 µg/m³ for the saved draw. The reason for selecting 50.5814 is explained after deriving the detector.

| Number | Its role in the calculation |
| --- | --- |
| 50.5814 µg/m³ | Chosen true enhancement q for this simulated experiment |
| 0.012181 dB | Predicted extra attenuation of the first tone |
| 0.998599 | Predicted sample/reference amplitude ratio for that tone |
| 0.1401% | The same amplitude change expressed as a reduction |

The last three values follow from q and the molecular absorption model. None is a receiver estimate.

Conditions: q was chosen from the model’s 95% detection limit, before generating the observation. It is not a measured concentration.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 3. q describes an enhancement with a fixed vertical shape

The receiver senses an integrated path effect. It cannot independently estimate the concentration at every altitude from this one ray. Specifying an exponential shape reduces the unknown function to one scalar q. In the differential model q = 0 means no enhancement relative to the reference, not necessarily zero absolute CH3CN. The saved link budget treats baseline CH3CN attenuation as negligible. If the actual vertical shape is different, q remains a model dependent equivalent amplitude.

| Altitude z | Sample minus reference concentration |
| --- | --- |
| 0 m | 50.5814 µg/m³ |
| 500 m | 36.2432 µg/m³ |
| 1500 m | 18.6079 µg/m³ |
| 3000 m | 6.8454 µg/m³ |
| 5000 m | 1.8044 µg/m³ |

$$
\Delta c(z)=c_{\mathrm{sample}}(z)-c_{\mathrm{reference}}(z)=q\,e^{-z/(1500\ \mathrm m)}
$$

q is the unknown surface equivalent increase (µg/m³). The profile shape is assumed, not independently recovered.

Vertical mass column: (1500 m)q = 75,872.1 µg/m² = 75.8721 mg/m².

Conditions: The reference is a baseline acquisition, not necessarily gas free air. Other species are assumed unchanged.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 4. The fixed experiment used in all calculations

LEO links are a useful example throughout the complete sensing chain. The same inference framework can use terrestrial or UAV geometry. The 25 dBm and 7 dB values have a published LEO design precedent in TeraLink, rather than flight validation. Aperture efficiency, implementation loss, vertical profile and calibration covariance are assumptions. Zenith is the shortest geometric path at a fixed orbit height; it cannot persist for a finite acquisition without time dependent tracking corrections.

| Parameter | Value |
| --- | --- |
| Geometry | 550 km LEO satellite, 90° ground elevation |
| Spectrum | 230–240 GHz, 1,024 tones; first tone 230.004883 GHz |
| Total RF power and apertures | 25 dBm; 0.10 m transmit / 1.0 m receive; η = 0.65 |
| Noise and additional loss | 7 dB receiver noise figure; 5 dB implementation loss |
| Atmosphere and gas profile | ITU P.835 / P.676; CH₃CN scale height 1,500 m |
| Acquisition | 10 s reference + 10 s sample; 0.3% full pilot symbols |

Conditions: The static benchmark assumes ideal tracking. No source demonstrates this entire orbital configuration.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>
- <https://arxiv.org/html/2606.15410v1>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>
- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>

## 5. Step 1 · Mass concentration becomes molecular density

The code uses concentration_ug_m3_to_number_density_cm3, giving 1.466918558936 × 10^10 molecules/cm³ per 1 µg/m³. Multiplying by q and exp(−z/1500) gives the molecular density at every integration node. This is dimensional conversion, not a fitted parameter. Natural molar mass is used for mass concentration; isotopologue mass is used for Doppler broadening. HITRAN intensity already contains natural isotope abundance, so the abundance is not applied a second time.

At q = 50.5814, the surface molecular density is 7.419879e+17 molecules/m³.
HITRAN uses cm² per molecule, so the calculation converts density to cm⁻³ and path length to cm.

$$
\begin{gathered}n_1(0)=\frac{10^{-6}\ \mathrm{g/m^3}}{41.053\ \mathrm{g/mol}}\,(6.02214076\times10^{23})=1.46691856\times10^{16}\ \mathrm{m^{-3}}\\n(z;q)=q\,n_1(0)e^{-z/1500}\end{gathered}
$$

n₁: density for a numerical concentration of 1 µg/m³ · n(z;q): molecular density for the chosen q
41.053 g/mol: natural mixture molar mass · q is inserted numerically in µg/m³

This converts an environmental concentration into the number of absorbers seen by the wave.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://hitran.org/docs/definitions-and-units/>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/src/thz_isac/concentration_units.py>

## 6. Step 2 · One actual HITRAN transition

This is the largest individual contributor at the first tone and first altitude quadrature node, selected after evaluating all retained lines. It is not asserted to be the only relevant transition or a line centered on the tone. The molecule ID is 41 and local isotopologue ID is 1. The raw line wavenumber is 7.97678228 cm⁻¹, pressure shift is zero, and the actual record is exported with the derived contribution. Catalog range and line shape assumptions remain physical uncertainties.

| Catalog parameter | Saved value | Physical role |
| --- | --- | --- |
| Line center | 239.1379167 GHz | Transition frequency |
| S(296 K) | 2.616 × 10⁻²¹ cm/molecule | Integrated line strength |
| Air width γ_air | 0.1594 cm⁻¹/atm | Collision broadening |
| Lower state energy E″ | 47.8643 cm⁻¹ | Temperature dependence |
| Width temperature exponent | 0.71 | Temperature scaling of width |

This is one of 17,880 retained CH₃CN transitions. The calculation sums their contributions.

Conditions: The measured tone is at 230.004883 GHz. A transition contributes away from its center through its broadened shape.

Sources:

- <https://hitran.org/docs/definitions-and-units/>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/largest_line_contributions.csv>

## 7. Step 2 · A line shape gives absorption at our tone

The Voigt function is the convolution of Doppler and collision broadening. Here the Lorentz half width is 0.1621900503 cm⁻¹ and the Doppler standard deviation is 6.42862709 × 10^−6 cm⁻¹. Their values are used at the actual tone wavenumber. Multiplying the temperature corrected line strength by this function gives one cross section. The other transitions supply the remaining sum. The layer has no single universal cross section: pressure and temperature change it with altitude.

| At z = 16.8826 m | Value |
| --- | --- |
| Atmospheric state | T = 288.0403 K; p = 101,122.35 Pa |
| Temperature corrected strength S(T) | 2.845759 × 10⁻²¹ cm/molecule |
| Voigt value V at 230.004883 GHz | 0.4334214 cm |
| Sum over all retained lines: σ₀(z) | 2.642246 × 10⁻²⁰ cm²/molecule |

$$
\sigma_{\ell,0}=S_\ell(T)V_\ell(f_0;T,p)=(2.845759\times10^{-21})(0.4334214)=1.233413\times10^{-21}\ \mathrm{cm^2}
$$

σ_ℓ,₀: one transition’s absorption cross section at tone 0 · σ₀ = Σℓ σ_ℓ,₀
V is normalized over wavenumber. The temperature correction is worked out in the appendix.

Conditions: σ is calculated from line parameters and atmospheric state. It is not a measured satellite attenuation.

Sources:

- <https://hitran.org/docs/definitions-and-units/>
- <https://hitran.org/hapi/>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 8. Step 3 · One altitude node contributes optical depth

At zenith, the geometric path element equals the vertical element. The model uses order six Gauss quadrature over altitude intervals and inserts atmospheric layer boundaries, giving 114 nodes. The first node is at 16.882621449 m. Its number density is n1(0) exp(−16.882621449/1500). Its contribution in dB per unit q is 4.342944819 × 1.641537197735 × 10^−6 = 7.129105468153 × 10^−6. Numerical integration weights must not be interpreted as a measurement of the local gas profile.

| First quadrature node | Numerical value |
| --- | --- |
| Cross section σ₀ | 2.6422462 × 10⁻²⁰ cm²/molecule |
| Density n₁(z) for q = 1 µg/m³ | 1.4505008 × 10¹⁰ molecules/cm³ |
| Integration weight w | 42.831123 m = 4,283.1123 cm |

$$
\delta\tau_{0,1}=\sigma_0n_1w=(2.6422462\times10^{-20})(1.4505008\times10^{10})(4283.1123)=1.6415372\times10^{-6}
$$

δτ₀,₁: dimensionless optical depth contribution at tone 0 for 1 µg/m³
The weight is a Gauss quadrature weight, not the thickness of a physical uniform slab.

Repeat this product at each altitude node and add the contributions.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/quadrature_first_tone.csv>

## 9. Step 3 · Adding the atmosphere gives the tone sensitivity

Each displayed row sums the exact quadrature contributions in that altitude interval, not a midpoint approximation. The 0–100 km total is 5.545084465494345 × 10^−5 optical depth per unit q. Multiplication by 10/ln10 gives 2.40819958505 × 10^−4 dB/(µg/m³), matching the earlier saved tone table to floating point precision. The full list of 114 nodes retains the temperature, pressure, cross section, molecular density and weight.

| Altitude interval | Optical depth for q = 1 µg/m³ | Attenuation sensitivity (dB per µg/m³) |
| --- | --- | --- |
| 0–0.5 km | 1.6389001e-05 | 7.1176528e-05 |
| 0.5–1 km | 1.1583791e-05 | 5.0307766e-05 |
| 1–2 km | 1.3936792e-05 | 6.0526719e-05 |
| 2–3 km | 6.9036665e-06 | 2.9982243e-05 |
| 3–5 km | 5.0671830e-06 | 2.2006496e-05 |
| 5–100 km | 1.5704107e-06 | 6.8202070e-06 |

Sum: τ₀,₁ = 5.5450845 × 10⁻⁵ → a₀ = (10 / ln 10) τ₀,₁ = 0.00024081996 dB/(µg/m³)

Conditions: The vertical profile and atmospheric state determine this coefficient. It is not a universal CH₃CN constant.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/altitude_contributions.csv>

## 10. Step 4 · The chosen concentration gives 0.012181 dB

This is the missing multiplication behind the second row in the screenshot. Line strengths and cross sections determine a0, while q sets the magnitude of the extra gas column. This linearity is in optical depth and dB attenuation under the fixed trace gas line shape. The complex channel amplitude itself changes exponentially. Background cancellation assumes the reference and sample atmosphere are matched after correction.

The 4.5477 dB oxygen/water loss belongs to the baseline link budget.
The 0.012181 dB value is the additional loss caused by this CH₃CN enhancement.

$$
\begin{gathered}\Delta A_0=a_0q=(0.0002408199585)(50.5813966)=0.01218100983\ \mathrm{dB}\\\tau_0(q)=q\tau_{0,1}=(50.5813966)(5.545084465\times10^{-5})=0.002804781165\end{gathered}
$$

ΔA₀: extra CH₃CN attenuation at the first tone · τ₀: corresponding dimensionless optical depth

The concentration multiplies a sensitivity computed from real spectral parameters and an assumed path profile.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 11. Step 5 · Absorption predicts the amplitude change

Beer attenuation gives a power factor exp(−τ), hence an amplitude factor exp(−τ/2). The result is deterministic for the chosen concentration and physical model. It contains no receiver noise yet. The total received sample power at this tone becomes −97.61177776 dBm compared with the reference −97.59959675 dBm. The baseline channel magnitude is normalized to one for the next receiver calculation.

The ratio concerns channel magnitude after known geometric and instrument corrections.
The power ratio is 0.99719915. The stated 0.1401% is an amplitude reduction.

$$
\begin{gathered}\frac{|h_{1,0}|}{|h_{0,0}|}=e^{-\tau_0/2}=10^{-\Delta A_0/20}=10^{-0.01218100983/20}=0.9985985923\\100\left(1-\frac{|h_{1,0}|}{|h_{0,0}|}\right)=0.1401407692\%\end{gathered}
$$

h₀,₀: reference channel at tone 0 · h₁,₀: sample channel at tone 0, before measurement error

These are the third and fourth rows of the screenshot, now derived from the gas column.

Conditions: A predicted change of 0.1401% is not yet evidence that a receiver can resolve it.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://hitran.org/docs/definitions-and-units/>

## 12. Step 6 · Observation time fixes the averaging gain

This slide specifies the actual resources without teaching OFDM. The two schedules occupy 19.998208 seconds of complete frames, leaving 0.001792 seconds unused. A full pilot symbol measures all 1024 tones simultaneously. Sensing does not use the unknown payload symbols here. The 90 degree geometry is a snapshot approximation, and waiting for comparable reference conditions is additional operational time.

| Resource | Calculation |
| --- | --- |
| Tone spacing and useful symbol | 10 GHz / 1,024 = 9.765625 MHz; Tᵤ = 102.4 ns |
| Transmitted symbol | 102.4 ns + 10 ns assumed CP = 112.4 ns |
| Frame | 10,000 symbols, with 30 full pilot symbols |
| Frames in each 10 s acquisition | floor[10 / (10,000 × 112.4 ns)] = 8,896 |
| Pilots per tone in each acquisition | M = 8,896 × 30 = 266,880 |

Both the reference and sample are noisy: 10 s + 10 s, not a free or exact reference.

Conditions: Ideal phase, frequency, delay and gain tracking is assumed throughout each moving acquisition.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 13. Step 7 · One tone remains uncertain after averaging

The expected signal at this tone is 0.012181 dB, while the null standard deviation after both acquisitions is 0.017180 dB. Even with perfectly known gain this is not a reliable single tone detection. With an unknown gain offset, a single tone cannot distinguish attenuation from a gain change at all. The normalized real and imaginary noise components each have standard deviation 0.001396230873. Multiple frequencies are essential for both uncertainty reduction and separation from nuisance gain changes.

| First tone | Numerical value |
| --- | --- |
| Reference SNR per pilot, linear | ρ₀ = 0.961035658 |
| Complex mean variance, normalized channel | 1 / (Mρ₀) = 3.8989213e-06 |
| Thermal variance of the reference/sample log ratio | v₀(0) = 2.9415287e-04 dB² |
| Total null variance after calibration term | C₀₀ = 2.9515287e-04 dB² |

$$
v_0(0)=\frac{(20/\ln10)^2}{2M}\left(\frac1{\rho_0}+\frac1{\rho_0}\right),\qquad\sqrt{C_{00}}=0.0171800\ \mathrm{dB}
$$

C₀₀ = v₀(0) + (0.001 dB)² · The log ratio variance uses a high coherent mean SNR approximation.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 14. Step 8 · The saved receiver draw does not equal its mean

Exactly replay the original random generator draw: z_r,k = (u+jv)/sqrt(2Mρ0,k), h0 = 1+z0 and h1 = 10^(−a q/20)+z1. The model then adds one correlated differential dB calibration draw per pair. Each displayed magnitude is calculated from both complex components. The final y0 equals the stored observation to numerical precision. This addresses the difference between the deterministic table and what a receiver could actually return.

| Normalized complex pilot means, simulated | Value |
| --- | --- |
| Reference ĥ₀,₀ | 1.0009162403 + j 0.0004400251 |
| Sample ĥ₁,₀ | 1.0007326946 − j 0.0009412581 |
| Magnitudes |ĥ₀,₀| and |ĥ₁,₀| | 1.0009163371 and 1.0007331373 |
| Persistent differential calibration draw e₀ | −0.0020537566 dB |

$$
y_0=-20\log_{10}\!\left(\frac{1.0007331373}{1.0009163371}\right)-0.0020537566=0.0015899416-0.0020537566=-0.0004638149\ \mathrm{dB}
$$

The mean sample amplitude is 0.9985985923, but the noisy pilot mean can be larger. Seed: 20261005.

A positive gas enhancement can produce a negative observed attenuation at one noisy tone.

Conditions: These are simulated complex observations with the stated noise and calibration model, not field measurements.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/complex_receiver_steps.csv>

## 15. Step 9 · The detector uses the complete observed spectrum

All 1024 plotted observations are retained from the original saved simulation. The true template is shown for explanation, but the estimator does not receive q. It receives y, the template a calculated for one unit of concentration, a covariance model, and nuisance directions. Frequencies share a persistent correlated calibration error, so simply treating every sample as independent would overstate the information.

Input to estimation: y has 1,024 entries. The first is −0.0004638 dB, not the predicted +0.012181 dB.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 16. Step 10 · The design matrix encodes gas and gain changes

The molecular column is generated by the same physical integration at every tone. The other columns permit a constant and linear spectral gain error. They stop these simple instrument changes from automatically being called gas. All three columns must be fitted jointly. The table scales only a by 10^4 for readability; calculations use unscaled a. Allowing more nuisance directions can reduce sensitivity further.

| Tone index k | aₖ [10⁻⁴ dB/(µg/m³)] | Offset column | Slope uₖ |
| --- | --- | --- | --- |
| 0 | 2.408200 | 1 | -0.500000 |
| 255 | 2.804245 | 1 | -0.250733 |
| 511 | 4.032712 | 1 | -0.000489 |
| 767 | 6.489083 | 1 | 0.249756 |
| 1023 | 7.500802 | 1 | 0.500000 |

$$
\mathbf y=\mathbf A\boldsymbol\theta+\boldsymbol\varepsilon,\quad\mathbf A=[\mathbf a\ \mathbf1\ \mathbf u]\in\mathbb R^{1024\times3},\quad\boldsymbol\theta=[q\ b_0\ b_1]^T
$$

Five displayed rows are selected from all 1,024. uₖ = (fₖ − mean(f)) / (max(f) − min(f)).
b₀: common gain change (dB) · b₁: spectral gain slope coefficient (dB) · ε: remaining observation error (dB)

A contains known model responses. The unknowns are q and the two gain coefficients.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 17. Step 11 · The covariance encodes which errors average down

The residual describes the reference/sample difference, so it is added once, not once for each acquisition. The null covariance assumes the two per pilot SNR values are equal. Under a positive enhancement the sample is weaker, slightly increasing its variance. The actual log amplitude observations are not exactly Gaussian; the high coherent mean SNR supports the delta approximation and the saved Monte Carlo control checks it within the model.

For example: C₀₀ = 2.95152865 × 10⁻⁴ dB², while C₀,₁₀₂₃ = 3.68238874 × 10⁻⁷ dB².
The estimator fixes its weights using C(0). Detection probability at q > 0 uses the corresponding C(q).

$$
\begin{gathered}\mathbf C(q)=\operatorname{diag}(v_k(q))+10^{-6}\mathbf R,\qquad R_{ij}=e^{-|f_i-f_j|/(10\ \mathrm{GHz})}\\v_k(q)=\frac{(20/\ln10)^2}{2M}\left[\rho_{0,k}^{-1}+\rho_{1,k}(q)^{-1}\right],\quad\rho_{1,k}(q)=\rho_{0,k}10^{-a_kq/10}\end{gathered}
$$

C is 1,024 × 1,024 in dB². Its thermal term includes reference and sample noise.
10⁻⁶ dB² is the assumed differential calibration variance; it is not divided by M.

Conditions: The calibration covariance is an explicit unmeasured assumption, not an estimate obtained from these data.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 18. Step 12 · Weighted regression estimates the unknowns

This is generalized least squares under the stated covariance. The saved production estimator uses Cholesky solves and SVD projection, avoiding explicit inverses. The worked replay computes G and g using Cholesky solves and solves the small system. Its q agrees with the original estimator H y. The normal equations are shown because they expose every coefficient in a compact numerical example, not because explicit matrix inversion is recommended.

The fit seeks the concentration whose spectral shape best explains y after allowing gain offset and slope.
The next slide gives every entry of the resulting three dimensional system.

$$
\widehat{\boldsymbol\theta}=\arg\min_{\boldsymbol\theta}(\mathbf y-\mathbf A\boldsymbol\theta)^T\mathbf C(0)^{-1}(\mathbf y-\mathbf A\boldsymbol\theta),\qquad\mathbf G\widehat{\boldsymbol\theta}=\mathbf g
$$

G = Aᵀ C(0)⁻¹ A, a 3 × 3 matrix · g = Aᵀ C(0)⁻¹ y, a 3 × 1 vector
θ̂ = [q̂, b̂₀, b̂₁]ᵀ · C(0)⁻¹ accounts for unequal noise and cross frequency correlation

The receiver does not divide each observed tone by aₖ and average the answers.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 19. Step 12 · The full spectrum reduces to this numerical system

Use the displayed system to reproduce the estimate, allowing for rounded coefficients. The full precision G, g and theta are saved in normal_equations.npz and worked_steps.json. The effective information is Gqq − Gqb Gbb^−1 Gbq, which is much smaller than Gqq. A and C are both necessary to construct this system; y appears only in g.

| Equation row | Coefficient of q | Coefficient of b₀ | Coefficient of b₁ | Right side g |
| --- | --- | --- | --- | --- |
| 1 | 0.301344020 | 458.463514 | 127.082723 | 15.066265191 |
| 2 | 458.463513671 | 983654.579709 | -223.779287 | 22141.401031152 |
| 3 | 127.082722926 | -223.779287 | 198502.414349 | 7023.360955313 |

$$
\begin{bmatrix}G_{qq}&\mathbf G_{qb}\\\mathbf G_{bq}&\mathbf G_{bb}\end{bmatrix}\begin{bmatrix}\widehat q\\\widehat{\mathbf b}\end{bmatrix}=\begin{bmatrix}g_q\\\mathbf g_b\end{bmatrix}
$$

The matrix columns correspond to different parameter units: q in µg/m³, b₀ and b₁ in dB.
All values use all 1,024 tones. Displayed coefficients are rounded; source arrays retain full precision.

The small q coefficient alone is not the usable information: much of the gas pattern resembles gain changes.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/normal_equations.npz>

## 20. Step 13 · Eliminating gain terms gives the concentration

This is the scalar Schur complement of the two gain parameters. It is algebraically equivalent to the whiten and project construction in the source tutorial. The subtraction removes the component of the molecular column that can be explained by a constant and a spectral slope. Rounding the two terms too aggressively before subtraction can lose precision, so the script uses full precision throughout. The inferred b coefficients are fitted nuisance values; they are not independent instrument calibration measurements.

The same solve gives b̂₀ = 0.00413651 dB and b̂₁ = 0.01014643 dB.
The true simulated q was 50.5814 µg/m³. The estimate is different because this observation contains error.

$$
\begin{gathered}I_q=G_{qq}-\mathbf G_{qb}\mathbf G_{bb}^{-1}\mathbf G_{bq}=0.3013440205-0.2951744347=0.006169585805\\t_q=g_q-\mathbf G_{qb}\mathbf G_{bb}^{-1}\mathbf g_b=15.0662651908-14.8230312721=0.243233918673\\\widehat q=t_q/I_q=39.42467555\ \mathrm{\mu g/m^3}\end{gathered}
$$

I_q: information for q after removing the gain nuisance terms [(µg/m³)⁻²]
t_q: remaining weighted evidence for q [(µg/m³)⁻¹]

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 21. Step 14 · The estimate exceeds a prespecified threshold

The threshold is fixed from the null model before inspecting the observation. The unconstrained signed estimator is used for the test; truncating negative estimates to zero would change its null distribution. This one successful random draw does not itself show 95% detection probability. The threshold and a 95% power concentration are different quantities.

The decision says the observed pattern is inconsistent with no enhancement under this model.
It does not establish exact concentration, unique chemical identity in a changing mixture, or field performance.

$$
\begin{gathered}s_0=I_q^{-1/2}=12.73127783\ \mathrm{\mu g/m^3}\\\tau=z_{0.99}s_0=(2.326347874)(12.73127783)=29.61738111\ \mathrm{\mu g/m^3}\\\widehat q=39.42467555>29.61738111\quad\Longrightarrow\quad\text{detection}\end{gathered}
$$

H₀: q = 0 · H₁: q > 0 · s₀: standard deviation under H₀
τ: threshold for 1% false alarm probability for this one prespecified compound and decision

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 22. Why the chosen q was 50.5814 µg/m³

The equation is implicit because s1 depends slightly on q through sample SNR. The code solves it numerically; evaluating at its solution gives the arithmetic displayed here. The constant variance approximation would give 50.5585 µg/m³. This explains the otherwise arbitrary looking number in the screenshot. It does not imply this is an environmentally typical concentration.

This concentration was selected from the analytical sensitivity calculation before the random receiver draw.
It is a controlled simulation input. It was neither measured in the atmosphere nor estimated from the sample.

$$
\begin{gathered}\Pr(\widehat q>\tau\mid q)=0.95\quad\Longleftrightarrow\quad q-\tau=z_{0.95}s_1(q)\\q_{95}=29.61738111+(1.644853627)(12.74521644)=50.58139660\ \mathrm{\mu g/m^3}\end{gathered}
$$

s₁(q) = √[H C(q) Hᵀ] · H is the first row of G⁻¹ Aᵀ C(0)⁻¹, so q̂ = H y.
z₀.₉₅: standard normal 95th percentile · these weights are fixed under the null.

The threshold is 29.6174 µg/m³. Achieving 95% predicted response requires a larger true enhancement.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 23. Repeated observations show success and failure rates

The counts are 113/10000 under q=0, 131/10000 at q=1 and 9475/10000 at q=50.5814. The exact binomial intervals describe Monte Carlo uncertainty, not uncertainty in hardware calibration, spectroscopy or real weather. The observations use complex pilot means, rather than directly drawing a Gaussian concentration estimate.

10,000 simulated reference/sample pairs at each concentration, using the same fixed threshold.

| True q (µg/m³) | Predicted response | Simulated response | 95% interval |
| --- | --- | --- | --- |
| 0 | 1.00% | 1.13% | 0.93–1.36% |
| 1 | 1.23% | 1.31% | 1.10–1.55% |
| 50.5814 | 95.00% | 94.75% | 94.29–95.18% |

1 µg/m³ is not reliably detected: the simulated response is only 1.31%, near the false alarm rate.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/receiver_control.csv>

## 24. What is real, assumed and simulated in this example

The EMeRGe/IAGOS contextual reference is 145 pptv, equivalent to about 0.252 µg/m³ at 288.15 K and 101325 Pa. It is not a universal ground concentration or a concentration profile measurement for this example. Real detection requires independently measured concentration, blank stability and a tested moving receiver. Multiple ground receivers would require adequate ray diversity and an identifiable tomographic model. LEO is a useful example for the full chain, not evidence that every proposed sensing mode is feasible.

| Evidence category | What belongs to it |
| --- | --- |
| External physical inputs | Actual HITRAN records; published ITU atmospheric models |
| Design assumptions | 550 km geometry; hardware configuration; exponential gas enhancement |
| Unmeasured error assumption | 0.001 dB differential residual and its spectral covariance |
| Simulated observation | Complex pilot means, calibration draw and resulting y |
| Not demonstrated | Measured atmospheric detection, ambient sensitivity or 3D reconstruction |

The calculation is concrete and reproducible. It is not an orbital measurement.

Conditions: A selected aircraft background reference is about 0.252 µg/m³, far below this conditional enhancement limit.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>
- <https://acp.copernicus.org/articles/23/1893/2023/index.html>

## 25. The original table, now with its calculation attached

This closes the requested explanation of the screenshot. The deterministic chain and statistical inverse are different operations. The forward model computes a pattern from a chosen concentration; the receiver fit estimates concentration from noisy observations without knowing the chosen value. That distinction is necessary to avoid confusing the simulated truth, predicted attenuation and retrieved concentration.

| Quantity | How the value is obtained | Result |
| --- | --- | --- |
| Chosen enhancement | Solve the 95% power equation, then set the simulation input | 50.5814 µg/m³ |
| Extra absorption at tone 0 | (0.0002408199585) × 50.5813966 | 0.012181 dB |
| Sample/reference amplitude | 10^(−0.01218100983 / 20) | 0.998599 |
| Amplitude reduction | 100 × (1 − 0.9985985923) | 0.1401% |

After adding the modeled errors and fitting all tones: q̂ = 39.4247 µg/m³ > threshold 29.6174 → detection.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 26. Appendix · Temperature correction for the actual line

The partition sums come from HAPI TIPS2025. The Boltzmann factor uses the lower state energy, and the last factor corrects stimulated emission. Width is also adjusted: γ = 0.1594 × (101122.3515/101325) × (296/288.040263)^0.71 = 0.1621900503 cm⁻¹. The saved source uses the second radiation constant defined in physical_spectroscopy.py. All factors are calculated at the first actual quadrature node, not at a rounded atmospheric state.

Q(296) / Q(T) = 88658.97016 / 83172.06723 = 1.065970501.
S(T) = 2.616 × 10⁻²¹ × 1.065970501 × 0.993591393 × 1.027087331 = 2.845759 × 10⁻²¹ cm/molecule.

$$
S(T)=S(296)\frac{Q(296)}{Q(T)}\exp\!\left[-c_2E^{\prime\prime}\left(\frac1T-\frac1{296}\right)\right]\frac{1-e^{-c_2\widetilde\nu/T}}{1-e^{-c_2\widetilde\nu/296}}
$$

Q(T): molecular partition sum · E″ = 47.8643 cm⁻¹ · ν̃ = 7.97678228 cm⁻¹
c₂: second radiation constant (cm K) · T = 288.040263 K

The line strength changes with state populations and stimulated emission before the profile is applied.

Sources:

- <https://hitran.org/docs/definitions-and-units/>
- <https://hitran.org/hapi/>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 27. Appendix · Power and noise at the first tone

Received power equals per tone power plus both antenna gains minus free space, background and implementation loss. Noise uses kB(Tsky+Te)Δf, with Tsky = 177.831 K and Te = 290(10^(7/10)−1). The noise figure is not counted twice. More exact values are saved in tone_by_tone.csv. The 25 dBm is the total average RF power across all tones, not per tone or electrical input power.

| Link budget term | Value |
| --- | --- |
| Transmit power per tone | 25 − 10 log₁₀(1024) = −5.1030 dBm |
| Transmit + receive gains | 45.7705 + 65.7705 dBi |
| Free space + background + implementation loss | 194.4898 + 4.5477 + 5.0000 dB |
| Reference / sample received power | −97.5996 / −97.6118 dBm |
| Noise power in one tone | −97.4270 dBm |
| Reference per pilot SNR | −0.172605 dB = 0.96103566 linear |

Conditions: The extra 0.012181 dB CH₃CN loss belongs only to the sample in this enhancement model.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/tone_by_tone.csv>

## 28. Appendix · Five actual rows of the covariance

Each row and column is indexed by the original tone number. Multiply each displayed entry by 10^−4 dB² to obtain the covariance value. The diagonal includes both thermal and persistent calibration variance. Selecting only these tones requires recalculating the estimator using the corresponding A rows and this submatrix. Taking five entries from the full H would not produce the five tone estimator.

This is a submatrix of the full null covariance, not a new error model.

| C / 10⁻⁴ dB² | 0 | 255 | 511 | 767 | 1023 |
| --- | --- | --- | --- | --- | --- |
| 0 | 2.951529 | 0.007796 | 0.006071 | 0.004728 | 0.003682 |
| 255 | 0.007796 | 2.947224 | 0.007788 | 0.006065 | 0.004724 |
| 511 | 0.006071 | 0.007788 | 2.947702 | 0.007788 | 0.006065 |
| 767 | 0.004728 | 0.006065 | 0.007788 | 2.952581 | 0.007788 |
| 1023 | 0.003682 | 0.004724 | 0.006065 | 0.007788 | 2.961572 |

The off diagonal elements carry the assumed correlation between spectral errors.

Conditions: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 29. Appendix · A five tone dot product can be checked by hand

These are the same five observations extracted from the full simulated spectrum. The weights are recomputed for only these five tones while allowing the same gain offset and slope. The entries and their products show a literal matrix multiplication. Its large uncertainty means the estimate 171.7494 is not persuasive evidence, even though it is larger than the full spectrum estimate. Source values retain full precision; the displayed products use full precision before rounding.

| Tone k | Observed yₖ (dB) | Five tone weight H₅,ₖ | Product H₅,ₖ yₖ |
| --- | --- | --- | --- |
| 0 | -0.000463815 | 4942.686 | -2.292492 |
| 255 | 0.025099503 | -4201.176 | -105.447434 |
| 511 | -0.031417175 | -5681.920 | 178.509866 |
| 767 | 0.018701897 | 4215.931 | 78.845915 |
| 1023 | 0.030551022 | 724.479 | 22.133560 |

Sum = 171.7494 µg/m³; standard deviation = 165.1163; threshold = 384.1179 → no detection.

Conditions: This discards 1,019 tones. The main detector uses all 1,024, with the same assumed 0.001 dB residual and 20 s total.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>

## 30. Appendix · Hardware evidence keeps its original scope

Transmit power values must refer to the same quantity when comparing hardware: average linear OFDM output differs from peak pulse power and electrical supply power. The published design and laboratory references are meaningful anchors but cannot prove the whole assumed measurement chain. The research note retains antenna dimensions, pointing, surface tolerance, motion and power comparisons.

| Source | Useful evidence | What it does not establish |
| --- | --- | --- |
| Sen et al., Nature Electronics | 200 mW at 210–240 GHz, terrestrial link | Orbital operation |
| TeraLink, 2026 preprint | 25 dBm, 7 dB NF, proposed LEO system | Flight validation of this example |
| Cooper et al., JMW | >400 mW CW at 240 GHz | A complete 10 GHz OFDM modem |

The selected parameters have physical references, but combined bandwidth, calibration and tracking remain unverified.

Conditions: 1 W and 10 W transmit cases elsewhere in the repository are sensitivity scenarios, not qualified payload specifications.

Sources:

- <https://www.nature.com/articles/s41928-022-00897-6>
- <https://arxiv.org/html/2606.15410v1>
- <https://doi.org/10.1109/JMW.2025.3610360>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 31. Sources · Spectroscopy and atmospheric state

These are primary method and context references. The HITRAN table is an external physical input; the code adds the declared geometry, concentration profile and receiver error assumptions. See the linked source audit for each claim boundary. HAPI version in the retained experiment is 1.3.0.0.

HITRAN: actual CH₃CN line records, units, temperature correction and absorption model. hitran.org/docs/definitions-and-units/
HAPI and TIPS2025: partition functions used in the spectral calculation. Kochanov et al., JQSRT 177 (2016), DOI 10.1016/j.jqsrt.2016.03.005.
ITU P.835-7 (2024): standard atmospheric state. ITU P.676-13 (2022): oxygen/water propagation and emission.
EMeRGe / IAGOS context: ACP 23, 1893 (2023), DOI 10.5194/acp-23-1893-2023.

Sources:

- <https://hitran.org/docs/definitions-and-units/>
- <https://hitran.org/hapi/>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>
- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>
- <https://acp.copernicus.org/articles/23/1893/2023/index.html>

## 32. Sources · Every numerical step is saved

The numerical replay starts from the original experiment snapshot b94f3fe and does not alter the main scientific result. The data directory is results/zenith_worked_steps. The physical forward sum and the complex random draw are independently replayed, then compared against the saved outputs. The first tone sensitivity, whole spectrum estimate and uncertainty agree. Equations and slide source values are drawn from these files.

worked_steps.json contains the values substituted in the equations.
quadrature_first_tone.csv and altitude_contributions.csv expose the complete atmospheric integral.
complex_receiver_steps.csv records both complex pilot means and the final observation at every tone.
normal_equations.npz stores G, g and θ̂; the original matrices.npz contains the full A, C and H.

Reproduce with scripts/calculate_zenith_worked_steps.py. The saved source hashes are in manifest.json.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/worked_steps.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/results/zenith_worked_steps/manifest.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/scripts/calculate_zenith_worked_steps.py>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
