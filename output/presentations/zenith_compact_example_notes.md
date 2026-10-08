# Worked CH₃CN example, calculation recipe and receiver units

8 October 2026. Nine pages for a telecom audience. The underlying experiment is the saved 5 October calculation.

## 1. The experiment and the concentration we want

A 550 km LEO satellite directly overhead illuminates one atmospheric column. We look for extra acetonitrile (CH₃CN).

What the receiver is looking for

Gas molecules remove different amounts of power at different frequencies. We estimate how much the known CH₃CN absorption pattern has increased between two acquisitions.

Gas enhancement means Δc(z) = c_sample(z) − c_reference(z): extra CH₃CN above the reference atmosphere. It is simulated here, rather than measured pollution.

$$
\Delta c(z)=q\,e^{-z/(1500\,\mathrm m)}
$$

q is the surface equivalent concentration increase (µg/m³). The fixed 1,500 m profile lets one scalar describe the column; one ray cannot recover concentration at every height.

Example input: q = 50.5814 µg/m³ (18.6079 µg/m³ at 1,500 m). It was chosen for 95% predicted detection with an assumed 0.001 dB calibration residual. The receiver estimates q without knowing this input.

The specified link

| Setting | Value and meaning |
| --- | --- |
| Elevation | 90° at the receiver, shortest geometric path |
| Band and tones | 230–240 GHz across 1,024 tones |
| RF power | 25 dBm total average power across the band |
| Apertures | 0.10 m transmit / 1.0 m receive, efficiency 0.65 |
| Receiver | 7 dB noise figure, 5 dB implementation loss |
| Acquisition | 10 s reference + 10 s sample |

HITRAN supplies molecular line data, not the concentration q. This example chooses q using page 6's sensitivity calculation. A 3D image would need multiple rays and additional assumptions.

Conditions: Actual HITRAN data and ITU atmosphere models support the calculation. The gas profile, hardware and receiver observations are modeled.

LEO links are a useful example across the whole sensing chain. The same framework can use other link geometries. The hardware audit distinguishes a published LEO design precedent from terrestrial hardware and CW component demonstrations. None validates this combined orbital configuration. The gas enhancement is relative to a matched reference. Baseline CH3CN loss is negligible in the saved link budget. The selected input q comes from the conditional sensitivity calculation on page 6, rather than an ambient concentration measurement.

Sources:

- [Hardware audit](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/docs/54_supervisor_revision_2026_10_05.md)
- [P.835](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en)
- [P.676](https://www.itu.int/rec/R-REC-P.676-13-202208-I)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)

## 2. Molecules, height and optical depth

The forward model adds the absorption of each altitude layer. Its inputs are a concentration profile and spectral line parameters.

What each quantity means

n(z) counts absorbing molecules per volume. For 1 µg/m³, n(0) = (10⁻⁶ / 41.053) Nₐ = 1.46692 × 10¹⁶ m⁻³, with Nₐ = 6.02214 × 10²³ mol⁻¹. The profile decreases with height.

σ(f,z) is effective absorption area per molecule. Each line contributes S × V: S is its integrated strength and V its shape across frequency. Temperature changes S and V. Pressure broadens and shifts V.

$$
\textstyle\alpha(f,z)=n(z)\sigma(f,z),\quad\tau(f)=\int_{z_g}^{z_s}\alpha(f,z)\,\mathrm dz
$$

α is absorption per unit distance. Optical depth τ adds it along the ray and has no units. Power transmission is exp(−τ). At τ = 1, 36.8% survives. Height enters through n, temperature, pressure and the endpoints.

Actual calculation at the first tone

f₀ = 230.004883 GHz. At z = 16.8826 m, T = 288.0403 K and p = 101,122.35 Pa:

| Calculation | Numerical value |
| --- | --- |
| One transition: σ = S(T) × V | (2.845759 × 10⁻²¹) × 0.4334214 = 1.233413 × 10⁻²¹ cm² |
| All retained transitions | σ₀ = 2.642246 × 10⁻²⁰ cm²/molecule |
| Density for 1 µg/m³ | n₁(z) = 1.450501 × 10¹⁰ molecules/cm³ |
| Integration weight | w = 4,283.1123 cm |
| This node: δτ = σ₀ n₁ w | δτ = 1.641537 × 10⁻⁶ |
| Sum all 114 altitude nodes | τ₀,₁ = 5.545084 × 10⁻⁵ for 1 µg/m³ |

97.17% of τ comes from below 5 km. Extra satellite height mainly adds free space loss.

Conditions: The height fractions and cross sections depend on the assumed profile, frequency and atmosphere. They are calculated values.

Cross section is an effective absorption area per molecule at one frequency, rather than its geometric size. The code converts mass concentration to molecular density using 41.053 g/mol. HITRAN line strength describes integrated absorption and the Voigt profile distributes it in wavenumber; pressure collisions and thermal motion broaden the line. Natural abundance is already included in HITRAN intensity. A real retained transition centered at 239.1379167 GHz contributes at the first tone through its broadened wing. The first quadrature node is 16.882621449 m with T=288.040263 K and p=101122.3515 Pa. The model sums 17,880 retained transitions and 114 altitude nodes to 100 km. Remaining CH3CN absorption to the satellite is negligible for the assumed exponential enhancement. The quadrature weight is an integration weight, not a measured physical slab.

Sources:

- [HITRAN](https://hitran.org/docs/definitions-and-units/)
- [HAPI](https://hitran.org/hapi/)
- [P.835](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en)
- [Height contributions](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/altitude_contributions.csv)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)

## 3. The four numbers in the example

With the profile fixed, q scales the extra optical depth. The predicted channel change follows from that accumulated absorption.

Numerical chain at 230.004883 GHz

| Quantity | Calculation and result |
| --- | --- |
| Chosen gas enhancement | q = 50.5813966 µg/m³ |
| Extra optical depth | τ₀ = q × 5.5450845 × 10⁻⁵ = 0.0028047812 |
| Extra molecular loss | ΔA₀ = (10 / ln 10) τ₀ = 0.0121810098 dB |
| Sample/reference amplitude | exp(−τ₀/2) = 0.9985985923 |
| Amplitude reduction | 100 × (1 − 0.9985985923) = 0.1401408% |

$$
\Delta A_k=a_kq,\quad a_0=0.0002408199585\ \mathrm{dB}/(\mathrm{\mu g/m^3})
$$

aₖ means the extra loss produced by 1 µg/m³ with this profile. It varies with frequency because each tone samples a different part of the gas spectrum.

The detector uses a pattern across frequency

The chart plots the predicted extra gas loss aₖq at all 1,024 saved frequencies.

The power transmission is exp(−τ₀) = 0.99719915: the added gas removes 0.2801% of the power. The amplitude change is smaller because power is proportional to magnitude squared.

Baseline oxygen/water loss at tone 0: 4.5477 dB.

Conditions: These are noiseless predictions for a chosen enhancement. The next page adds the modeled receiver errors.

The a coefficient is computed separately for each tone by the physical forward integral. It is a response per unit concentration, not a fitted gain. The trace gas approximation holds the line shape fixed while q changes. The 4.5477 dB background attenuation at the first tone includes oxygen and water and belongs to the baseline budget. The four familiar values refer to the first tone only. The chart displays the predicted extra loss across every saved tone. Both receiver acquisitions must be corrected for known geometric and instrument differences before using their ratio.

Sources:

- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)
- [HITRAN](https://hitran.org/docs/definitions-and-units/)

## 4. Pilots: known symbols that reveal the channel

A pilot is a transmitted complex symbol whose value the receiver already knows. It provides a reference for estimating channel gain.

How one known symbol becomes a measurement

X is a known unit magnitude pilot, R the received symbol, h the channel and W thermal noise. k labels the tone and m the repetition. Divide out X before averaging:

$$
\begin{aligned}R_{k,m}&=h_kX_{k,m}+W_{k,m}\\\widehat h_k&=(1/M)\textstyle\sum_{m=1}^{M}R_{k,m}/X_{k,m}\end{aligned}
$$

Noiseless illustration with h = 0.9985986:

| Known X | Received R | R / X |
| --- | --- | --- |
| 1 | 0.9985986 | 0.9985986 |
| j | 0.9985986 j | 0.9985986 |

The second pilot rotates by 90°. Dividing by j removes that known rotation. Both pilots reveal the same channel, so their corrected estimates can be averaged.

Independent noise falls as 1/√M in standard deviation. Persistent gain drift survives averaging.

The actual allocation and simulated observation

| Resource | Value in this example |
| --- | --- |
| One OFDM symbol | 102.4 ns useful + 10 ns CP = 112.4 ns |
| Pilot allocation | 30 full pilot symbols per 10,000 symbols (0.3%) |
| Every tone, each 10 s | 8,896 frames × 30 = M = 266,880 pilots |
| Thermal variance of ĥ₀ | 1 / (Mρ₀) = 3.89892 × 10⁻⁶<br>Pilot SNR ρ₀ = 0.961036 |

After tracking and normalization, tone 0 gives reference ĥ₀ and sample ĥ₁:

$$
\begin{aligned}\widehat h_{0,0}&=1.0009162403+j\,0.0004400251\\\widehat h_{1,0}&=1.0007326946-j\,0.0009412581\end{aligned}
$$

$$
-20\log_{10}(|\widehat h_{1,0}|/|\widehat h_{0,0}|)=0.0015899416\ \mathrm{dB}
$$

Conditions: Conditional example: ideal tracking, matched background, 20 s total and an assumed, unmeasured 0.001 dB calibration residual.

At tone k and repetition m, R_km = h_k X_km + W_km after timing, frequency and phase correction. X is a known unit magnitude pilot, R is the received complex symbol, h is the complex channel response and W is thermal noise. For equal energy pilots and independent noise, dividing by X and averaging is the least squares estimate of h. These are symbols deliberately known to the receiver, rather than decoded unknown payload. They sample the combined propagation and instrument response. They do not by themselves identify which part of a gain change came from the atmosphere. The two demonstration rows use the predicted normalized h = 0.9985985923 and no noise. They are an arithmetic illustration, not retained raw receiver samples. Multiplication by j rotates a pilot by 90 degrees. Dividing by its known j removes that rotation, leaving the same h. Averaging the raw R values without accounting for X would instead mix their phases. Timing, frequency and phase correction must also align the repetitions. With time varying LEO geometry, the saved model assumes ideal tracking and correction before the mean. This is a conditional equivalent complex noise simulation, not a measured or raw coded OFDM experiment.

The 9.765625 MHz tone spacing gives 102.4 ns useful duration. An assumed 10 ns cyclic prefix gives 112.4 ns total. Each 10 s acquisition contains floor[10/(10000 × 112.4e−9)] = 8,896 complete frames, with 30 full pilot symbols per frame, so M = 266,880 per tone per acquisition. Each full pilot symbol supplies a known symbol on every one of the 1,024 tones. M is not divided by 1,024. The pilot overhead is 30/10000 = 0.3%. In this model the remaining symbols do not contribute to the sensing estimate. With fixed M and independent thermal noise, the variance falls as 1/M and the standard deviation as 1/sqrt(M). Doubling M reduces thermal standard deviation by sqrt(2), not by two.

Reference per tone power is −97.59959675 dBm, noise is −97.42699177 dBm, giving rho0 = 0.9610356584. The physical noise model includes sky emission and receiver equivalent noise temperature. Noise figure is counted once. Normalized complex mean variance is 1/(M rho0) = 3.89892130e−6, with standard deviation 0.0013962309 per real or imaginary component. The two means shown are from saved seed 20261005. Their magnitudes are 1.0009163371 and 1.0007331373. Taking their ratio produces a loss of 0.0015899416 dB before the simulated calibration residual. A noisy estimate may lie above one even if the physical channel attenuates.

Sources:

- [Observations](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/complex_receiver_steps.csv)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)

## 5. Calibration error: a gain change can imitate gas

Calibration estimates and corrects the instrument response. The error is the response change left in the reference/sample comparison.

Two concrete examples

1. Receiver gain drops by 0.001 dB between acquisitions. With unchanged gas, the amplitude ratio becomes 0.9998848774 and the apparent loss is +0.001 dB.

At tone 0 alone, this would imply 0.001 / a₀ = 4.15248 µg/m³. If the error is constant across the band, our fit assigns it to gain offset b₀ instead of gas.

2. An error eₖ = aₖ × 1 µg/m³ has exactly the gas pattern. It imitates that concentration even across all tones. Independent calibration must constrain this ambiguity.

The residual in the saved simulation

Random thermal noise already affects the two pilot means. A separate persistent calibration draw contributes e₀ = −0.0020537566 dB:

$$
y_0=0.0015899416-0.0020537566=-0.0004638149\ \mathrm{dB}
$$

In measured data, calibration error is already present.

The fit allows simple gain changes

$$
y_k=a_kq+b_0+b_1u_k+\varepsilon_k,\quad A_{k,:}=[a_k\ 1\ u_k]
$$

| Tone k | aₖ × 10⁴ | Offset | Slope uₖ |
| --- | --- | --- | --- |
| 0 | 2.408200 | 1 | -0.500000 |
| 511 | 4.032712 | 1 | -0.000489 |
| 1023 | 7.500802 | 1 | 0.500000 |

Only 3 example rows are shown; the fit uses all 1,024. aₖ: dB/(µg/m³); uₖ: −0.5 to +0.5. b₀ is a common shift, b₁ a tilt; ε is the remaining error.

$$
C_{ij}(0)=\delta_{ij}v_i(0)+(0.001)^2 e^{-|f_i-f_j|/(10\,\mathrm{GHz})}
$$

vᵢ(0) = (20 / ln 10)² / (Mρ₀ᵢ) includes both acquisitions. C is 1,024 × 1,024 in dB². δᵢⱼ selects the diagonal. The second term models calibration errors shared across frequency.

Conditions: The 0.001 dB residual is an assumed standard deviation, not a measured accuracy or a maximum error. It does not shrink with pilot count.

A simple channel representation is h_meas,0(f) = g0(f) h_atm,0(f) and h_meas,1(f) = g1(f) h_atm,1(f). In a noise free comparison, measured loss = atmospheric loss − 20 log10|g1/g0|. Calibration estimates that instrumental ratio and removes it. Error is what remains after this correction, including transmitter power changes, receiver gain changes or antenna pointing changes. A known pilot reveals the combined channel and cannot separately tell whether weaker reception came from gas or hardware. In a physical measurement, this residual is already in the received data. We add e once to the simulated thermal loss to represent it, not as an extra processing step to be added to experimental data.

Example 1: an uncorrected 0.001 dB gain drop means sample/reference amplitude = 10^(−0.001/20) = 0.9998848774. It adds +0.001 dB measured loss even with unchanged gas. Naively using only tone zero would infer 0.001/a0 = 4.1524797 micrograms/m3. An exactly constant error across all tones lies in the offset column and is removed by the joint fit, so this is not a false detection prediction for the full algorithm. Example 2: an error e_k = a_k times 1 microgram/m3 has exactly the same frequency dependence as that amount of CH3CN. Spectral information alone cannot distinguish it. This is a deliberately constructed identifiability example, not a measured or claimed typical drift. Independent calibration is needed to bound such errors. The residual Gaussian model with standard deviation 0.001 dB can produce draws exceeding 0.001 dB. The saved first tone draw is −0.0020537566 dB, about −2.05 standard deviations.

A has 1,024 rows and three columns. Column a is the modeled gas pattern per concentration unit. The other columns represent a constant shift b0 and linear frequency trend b1, both in dB. They are nuisance parameters because they must be fitted to protect the gas estimate, although they are not the scientific quantity of interest. Only three rows are printed, but the calculation uses all tones. The gas pattern has components aligned with these simple gain changes, so fitting them also removes useful gas information. C(0) is the null covariance. The diagonal is each tone's variance, and the off diagonal entries describe shared error between frequencies. Independent thermal error appears only on the diagonal. The assumed calibration term has a 10 GHz correlation scale. C00 = 2.951528651e−4 dB2, so the first tone loss standard deviation is 0.0171800 dB. C0,1023 = 3.682388752e−7 dB2. The calibration term is not divided by M. The generalized least squares fit accounts for these correlations rather than counting every tone as independent.

Sources:

- [Observations](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/complex_receiver_steps.csv)
- [Matrices](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_single_compound/matrices.npz)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)

## 6. Solve for concentration and make the decision

Fit yₖ = aₖq + b₀ + b₁uₖ + εₖ to all 1,024 tones. q is the concentration increase (µg/m³); b₀ and b₁ are gain offset and slope (dB).

G = AᵀC⁻¹A (3 × 3): weighted overlap between the gas, offset and slope templates.
g = AᵀC⁻¹y (3 × 1): weighted match of those templates to the 1,024 observed losses.

| Normal equation | Expanded equation: Gθ = g, with θ = [q, b₀, b₁]ᵀ |
| --- | --- |
| 1. Concentration q | 0.301344020 q + 458.463514 b₀ + 127.082723 b₁ = 15.066265191 |
| 2. Gain offset b₀ | 458.463513671 q + 983654.579709 b₀ − 223.779287 b₁ = 22141.401031152 |
| 3. Gain slope b₁ | 127.082722926 q − 223.779287 b₀ + 198502.414349 b₁ = 7023.360955313 |

Minimize J = (y − Aθ)ᵀC⁻¹(y − Aθ). Rows set ∂J/∂q = 0, ∂J/∂b₀ = 0 and ∂J/∂b₁ = 0. Coefficients are rounded.

The estimate after fitting gain

Eliminating b₀ and b₁ leaves information Iq = 0.006169586 and weighted evidence tq = 0.243233919 for the gas. Their ratio gives:

$$
\widehat q=t_q/I_q=39.4247\ \mathrm{\mu g/m^3}
$$

The same solve gives b̂₀ = 0.00413651 dB and b̂₁ = 0.01014643 dB. The true input was 50.5814 µg/m³. Observation errors explain the difference.

The threshold and its meaning

$$
\begin{aligned}s_0&=I_q^{-1/2}=12.73128\ \mathrm{\mu g/m^3}\\q_{\rm th}&=2.32635\,s_0=29.61738\ \mathrm{\mu g/m^3}\end{aligned}
$$

Φ(z) = P(Z ≤ z), where Z is standard normal: mean 0, SD 1.
Φ⁻¹(0.99) = 2.32635: the cutoff with 99% below, 1% above.
Under q = 0, q̂/s₀ is standard normal in the assumed model.

39.4247 > 29.6174: this draw detects an enhancement.
At q = 50.5814, predicted response is 95%, simulated 94.75%.
At 1 µg/m³, simulated response is 1.31%.

Conditions: Conditional example: ideal tracking, matched background, 20 s total and an assumed, unmeasured 0.001 dB calibration residual.
No atmospheric detection measurement or 3D reconstruction is established by this example.

The entries displayed in G and g are rounded, so calculations use the saved full precision arrays. Solving gives qhat=39.4246755529, b0=0.0041365093 dB and b1=0.0101464333 dB. To see where the q uncertainty comes from, partition the two gain parameters as b. The Schur complement is Iq=Gqq−Gqb Gbb^−1 Gbq=0.301344020469−0.295174434664=0.006169585805. The remaining score is tq=gq−Gqb Gbb^−1 gb=15.066265190809−14.823031272136=0.243233918673, so qhat=tq/Iq. Iq has units (µg/m³)^−2 and tq has units (µg/m³)^−1. The standard deviation under the null is 1/sqrt(Iq). A 1% one sided false alarm rate for this prespecified compound uses the standard normal 99th percentile 2.326347874. The input q95 solves q95=qth+1.644853627 s1(q95), using s1=12.7452164389 and the alternative covariance under the same fixed estimator. In 10,000 simulated pairs, response is 94.75% at this input and only 1.31% at 1 µg/m³. Both remain conditional on the unmeasured calibration residual, matched atmosphere and ideal tracking. The next physical step is to measure blank stability and test independently measured concentrations. A detection here means a statistically significant enhancement of the prespecified template within the model, not exact concentration or unique identification in a changing gas mixture.

These are the three weighted least-squares normal equations, not three individual tone measurements. q is the surface equivalent increase in CH3CN mass concentration relative to the matched reference, in micrograms/m3. Define theta = [q, b0, b1]^T, A = [a, 1, u] and residual r = y - A theta. The vector a contains the modeled gas absorption per concentration unit; 1 represents a common gain shift and u a normalized frequency trend. The vector y contains 1,024 observed differential losses and C = C(0) their assumed covariance. G = A^T C^-1 A is a 3 by 3 matrix of weighted overlaps between these templates. Its diagonal entries measure template strength under this weighting, while off-diagonal entries describe overlap between fit directions. Lowercase g = A^T C^-1 y is a three-entry vector of weighted matches between the templates and observed losses. Neither G nor g is a gas concentration; q is the unknown concentration component.

Minimize J(theta) = r^T C^-1 r with the fixed null covariance. Setting the derivative with respect to q to zero gives a^T C^-1 r = 0; the derivative with respect to b0 gives 1^T C^-1 r = 0; and the derivative with respect to b1 gives u^T C^-1 r = 0. Together these say G theta = g. Every row contains information from all 1,024 tones, and all three unknowns must be solved together. The labels identify which derivative produced each row, not a separate one-variable solve.

Expanded numerical normal equations (rounded for display):
0.301344020 q + 458.463514 b₀ + 127.082723 b₁ = 15.066265191
458.463513671 q + 983654.579709 b₀ − 223.779287 b₁ = 22141.401031152
127.082722926 q − 223.779287 b₀ + 198502.414349 b₁ = 7023.360955313

Normal distribution notation: Phi(z) = P(Z <= z) for a standard normal variable Z with mean zero and standard deviation one. Phi takes a cutoff and returns the probability below it. Phi inverse takes a probability and returns the cutoff. Phi inverse(0.99) = 2.326347874, so P(Z > 2.326347874) = 0.01. The inverse superscript denotes the inverse function, not a reciprocal. Phi(0.99) itself is approximately 0.838913, which is a different operation. Under the no-enhancement hypothesis q = 0, qhat/s0 has a standard normal distribution in the assumed model. Multiplying the cutoff by s0 therefore gives the concentration threshold with a nominal one-sided 1% false-alarm probability. This does not mean a detection has a 99% probability of being correct.

Sources:

- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)
- [Repeated trials](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_single_compound/receiver_control.csv)
- [Hardware audit](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/docs/54_supervisor_revision_2026_10_05.md)

## 7. The complete calculation in execution order

Inputs: atmospheric model, pilot observations and assumed error covariance. The arithmetic uses the full precision arrays.

1. Build the gas template from the layers

n₁(z) is the molecular density for q = 1 µg/m³. Sum absorption at every altitude node ℓ:

$$
\textstyle a_k=(10/\ln10)\sum_\ell\sigma(f_k,z_\ell)n_1(z_\ell)w_\ell
$$

a₀ = 0.0002408199585 dB/(µg/m³).

2. Form the observed loss on each tone

$$
\begin{aligned}\widehat h_{r,k}&=(1/M)\textstyle\sum_m R_{r,k,m}/X_{k,m},\quad r\in\{0,1\}\\y_k&=-20\log_{10}(|\widehat h_{1,k}|/|\widehat h_{0,k}|)+e_k\end{aligned}
$$

r = 0 reference, r = 1 sample. Add e only when simulating it. Here y₀ = −0.0004638149 dB.

3. Compress 1,024 observations into G and g

$$
\begin{aligned}A&=[\mathbf a\ \mathbf1\ \mathbf u],\quad C=C(0)\ \text{on page 5}\\G&=A^TC^{-1}A,\qquad g=A^TC^{-1}\mathbf y\end{aligned}
$$

uₖ = (fₖ − mean f)/(max f − min f). G is 3 × 3.

4. Eliminate the two gain parameters

Partition G and g into q and b = [b₀, b₁]ᵀ:

$$
\begin{aligned}I_q&=G_{qq}-G_{qb}G_{bb}^{-1}G_{bq}\\t_q&=g_q-G_{qb}G_{bb}^{-1}g_b\end{aligned}
$$

Iq = 0.3013440205 − 0.2951744347 = 0.0061695858
tq = 15.0662651908 − 14.8230312721 = 0.2432339187

5. Compute concentration and uncertainty

$$
\begin{aligned}\widehat q&=t_q/I_q=39.42467555\ \mathrm{\mu g/m^3}\\s_0&=I_q^{-1/2}=12.73127783\ \mathrm{\mu g/m^3}\end{aligned}
$$

s₀ is the standard deviation when q = 0.

6. Compare with the detection threshold

$$
\begin{aligned}q_{\rm th}&=\Phi^{-1}(0.99)s_0=29.61738111\ \mathrm{\mu g/m^3}\\\widehat q&=39.4247>q_{\rm th}\quad\Rightarrow\quad\text{detection}\end{aligned}
$$

Φ⁻¹(0.99) = 2.32635: 99% below, 1% above. See page 6.

Conditions: Conditional example: ideal tracking, matched background, 20 s total and an assumed, unmeasured 0.001 dB calibration residual.
The 1% threshold applies to this prespecified compound and the stated error model.

This slide is an execution recipe connecting the physical forward model to the saved detection result. Step 1 computes a loss template per 1 microgram/m3 of surface equivalent enhancement. n1 is the height dependent density for that unit enhancement. The quadrature uses consistent centimetre units for sigma, density and weights. Step 2 divides each unit magnitude pilot out of the received complex observation and averages corrected values for reference and sample separately. The e term is included only to simulate calibration residuals. In measured channel estimates the residual is already embedded. Step 3 uses u_k=(f_k−mean f)/(max f−min f). A is 1024 by 3, y is 1024 by 1, C=C(0) is 1024 by 1024, G is 3 by 3 and g is 3 by 1. The null covariance on page 5 uses v_k(0)=(20/ln10)^2/(M rho0k), including both acquisitions. The weighted least squares objective is (y−A theta)^T C^−1 (y−A theta). Its derivative gives G theta = g. Numerically, solve with Cholesky factors rather than explicitly inverting C.

Step 4 partitions G and g into concentration q and gain parameters b=(b0,b1). Gqq is a scalar, Gqb is 1 by 2, Gbb is 2 by 2 and gb is 2 by 1. Eliminating b gives the scalar Schur complement Iq=Gqq−Gqb Gbb^−1 Gbq. This measures information left about concentration after the same data also estimate gain. It is small because much of the smooth gas pattern overlaps the gain offset and slope. Eliminating the same fitted gain from the right side gives tq=gq−Gqb Gbb^−1 gb. From full precision arrays, Iq=0.3013440204690398−0.29517443466363735=0.006169585805402444, tq=15.066265190809268−14.823031272135776=0.24323391867349287. Their units are (micrograms/m3)^−2 and (micrograms/m3)^−1.

Step 5 yields qhat=tq/Iq=39.4246755529 micrograms/m3 and null standard deviation s0=1/sqrt(Iq)=12.7312778289 micrograms/m3. Equivalently, solve the three by three system on page 6 directly. Then b_hat=Gbb^−1(gb−Gbq qhat). Step 6 tests qhat against Phi^−1(0.99)s0=2.3263478740×12.7312778289=29.6173811110 micrograms/m3 for a one sided 1% false alarm criterion. Phi is the standard normal cumulative distribution function. Since 39.4247 exceeds 29.6174, this draw declares an enhancement. The concentration estimate remains uncertain and differs from the chosen true input 50.5814. The sensitivity target used to choose that input is a separate calculation on page 6.

Sources:

- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)
- [Observations](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/complex_receiver_steps.csv)
- [Matrices](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_single_compound/matrices.npz)

## 8. Units for power, pilot noise and calibration

Absolute RF power, normalized complex pilot samples and attenuation errors describe different quantities and use different units.

Power and pilot noise at tone 0

| Quantity | Value and unit |
| --- | --- |
| Total transmit power | 25 dBm = 0.31623 W |
| Transmit power per tone | -5.1030 dBm |
| Received reference power | -97.5996 dBm |
| Noise in one tone | -97.4270 dBm |
| SNR ρ₀ = Psignal / Pnoise | 0.96104 linear = −0.17260 dB |
| Pilot-mean variance<br>E|δh|² = 1/(Mρ₀) | 3.89892 × 10⁻⁶<br>Normalized, dimensionless |
| Thermal loss SD | 0.01715 dB<br>Reference + sample |

Total covariance C₀₀ = 0.000295153 dB².
Pilot samples use linear complex amplitudes. Average R/X first, then take −20 log₁₀ of the sample/reference magnitude ratio to obtain loss in dB.

Why a calibration error can be tiny in dB

dBm specifies power relative to 1 mW. dB specifies a ratio. A drop from −97.5996 to −97.6006 dBm is 0.001 dB of extra loss.

| Assumed residual SD | Relative power SD | Amplitude SD |
| --- | --- | --- |
| 0.001 dB (this example) | ≈ 0.0230% | ≈ 0.0115% |
| 0.0001 dB (earlier design) | ≈ 0.00230% | ≈ 0.00115% |

Small-error conversions: σP/P ≈ (ln 10 / 10) σdB and σ|h|/|h| ≈ (ln 10 / 20) σdB. These are standard deviations, not maximum errors or measured stability.

Interference needs a separate power model

For independent additive interference, add noise and interference powers in watts: SINR = Psignal / (Pnoise + Pinterference). Coherent interference can instead bias pilots. This example has no separate interference term.

Conditions: The unit conversions are consistent. Achieving the assumed calibration stability remains unverified. Additional interference is not modeled here.

dBm is 10 log10(P / 1 mW), an absolute power level. A power ratio uses 10 log10(P1/P0) dB. The difference between two power levels in dBm is in dB. A magnitude ratio uses 20 log10(|h1|/|h0|) when power is proportional to magnitude squared under the same normalization. The sensing observable is a positive loss, so it uses a minus sign. The complex pilot equation R = hX + W is evaluated in normalized linear amplitude units, never by adding dBm levels. All displayed received/noise powers refer to one 9.765625 MHz tone. Total 25 dBm is split across 1024 active tones. Noise power is k_B times system temperature times tone bandwidth, in watts. SNR rho is the received/noise power ratio. With M = 266880 independent pilots, E|delta h|^2 = 1/(M rho), dimensionless, and each real/imaginary component has half that variance. The differential logarithmic loss includes independent noise in both reference and sample. At q = 0 its thermal variance is (20/ln10)^2/(M rho) in dB squared. Adding sigma_cal squared gives the diagonal of C; off-diagonal calibration covariance is sigma_cal squared times the frequency correlation. Calibration is already differential, so it is not multiplied by two or divided by M. Its small-error relative power standard deviation is approximately (ln10/10) sigma_cal and its amplitude standard deviation approximately (ln10/20) sigma_cal. The numbers 0.0001 and 0.001 are in dB, not linear fractional errors. The earlier five-gas design assumes 0.0001 dB, while this separate zenith pilot example assumes 0.001 dB. These are assumed stability levels and cannot be made less demanding by changing the label to dBm. Additive independent interference would require a power I in watts and SINR = P_signal/(P_noise + P_interference); dBm powers must first be converted to watts before summation. Pilot-correlated or coherent interference may bias the channel estimate and requires its own model. The present example includes thermal noise and correlated multiplicative calibration error but no separate interference process.

Sources:

- [RF units](https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gettingstarted/content/concepts_decibels.htm)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)
- [Observations](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/complex_receiver_steps.csv)

## 9. Why use all 1,024 tones instead of one?

The extra loss changes with frequency. That pattern helps separate the gas contribution from a common gain shift and a gain slope.

One tone: one loss, three unknowns

At one frequency, the observation model is
yₖ = aₖq + b₀ + b₁uₖ + εₖ.

A weaker signal can come from extra gas, a common gain change, or a frequency slope. One scalar observation cannot determine all three unknowns.

Even without noise, any chosen q and b₁ can be matched by setting b₀ = yₖ − aₖq − b₁uₖ. Independent knowledge of the gain terms would be needed to infer q from that tone alone.

A plain average of all 1,024 losses gives one number. Gas and a common gain change can both shift that mean; averaging discards the spectral shape that helps distinguish them.

Our special average: a weighted spectral fit

q̂ = Σₖ wₖyₖ uses all 1,024 tone losses.
Weights depend on the gas pattern a and error covariance C; they need not sum to one.

| Weight constraint | What it does |
| --- | --- |
| Σₖ wₖaₖ = 1 | Preserves the gas concentration q |
| Σₖ wₖ = 0 | Cancels a common gain offset b₀ |
| Σₖ wₖuₖ = 0 | Cancels the gain slope b₁ |

Some weights are negative to cancel gain changes. Subject to these constraints, the fit chooses weights that minimize predicted variance wᵀCw, accounting for noise and correlations.

Before this fit, each tone averages 266,880 pilots. More tones do not guarantee a √1,024 improvement: total 25 dBm power is split across the tones.

Conditions: Conditional example: ideal tracking, matched background, 20 s total and an assumed, unmeasured 0.001 dB calibration residual.
A calibration error with exactly the gas spectrum remains indistinguishable from gas, even with all tones.

This slide explains identifiability in the existing three-parameter fit, without introducing a new experiment or a quantitative performance comparison against an optimized single-tone design. One tone supplies one scalar loss y_k for three unknowns q, b0 and b1. Its design matrix has rank at most one, so concentration cannot be identified jointly with both unconstrained gain parameters from that tone alone. If gain offset and slope were independently known, one tone with nonzero gas response could estimate q. Across the full band, A = [a, 1, u] has 1,024 rows; the known gas spectral variation provides a fit direction distinct from the constant and slope columns. The weighted least-squares estimator combines tones using the assumed covariance, including correlations. More tones can supply additional spectral information and independent noise averaging, but do not imply a universal sqrt(1024) improvement. The total 25 dBm transmit power is split across the tones. Reallocating all power to one tone would change its SNR and requires a separate constrained comparison. Broad, smooth gas signatures can still overlap strongly with gain trends, reducing the information left for q. An error proportional to the gas template is structurally indistinguishable from gas in this spectral model. Calibration and the stated covariance remain essential.

The special average is a signed linear combination of the tone losses, not an ordinary mean. The weighted least-squares solution is theta_hat = (A^T C^-1 A)^-1 A^T C^-1 y. Taking its first row gives qhat = w^T y, with w^T = [1, 0, 0] (A^T C^-1 A)^-1 A^T C^-1. The weights satisfy w^T a = 1, w^T 1 = 0 and w^T u = 0, so the expected gas response is q and the fitted common offset and slope cancel. Among linear unbiased estimators under the assumed covariance, these weights minimize w^T C w. Their units are (micrograms/m3)/dB, since y is in dB and q is a concentration. Their sum is zero, not one, and some weights must be negative. Independent pilot repetition is averaged first within each tone; this spectral combination is a subsequent operation. A calibration residual aligned with a passes through exactly like gas and cannot be rejected by these constraints.

Sources:

- [Matrices](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_single_compound/matrices.npz)
- [Numerical steps](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/results/zenith_worked_steps/worked_steps.json)
- [Hardware audit](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/d4a25c4/docs/54_supervisor_revision_2026_10_05.md)
