# Acetonitrile at 90°: presenter notes

Research snapshot b94f3fe. All physical detection results are conditional predictions or simulations, not measured field performance.

Audience: mathematically fluent readers with no project or radio engineering background. Slides 1–29 form the main explanation. Slides 30–38 provide arithmetic, sensitivity and sources.

## 1. Detecting acetonitrile at 90° elevation

This example concerns a prespecified increase in acetonitrile relative to a reference. All observations in the worked example are simulations driven by published physical models and acquired HITRAN parameters. The underlying research snapshot is b94f3fe, dated 5 October 2026. No measured orbital detection is claimed.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 2. A communication link as a sensing experiment

No prior project knowledge is assumed. Radio frequency, abbreviated RF, refers here to the electromagnetic signal sent by the transmitter. At 235 GHz the wavelength is about 1.28 mm, in the subterahertz range used by the project. The satellite is a concrete way to illustrate the entire inference chain. The question is whether the small additional gas signature survives spreading loss, ordinary atmospheric absorption, receiver noise and instrument drift. The example uses known pilot symbols for sensing and leaves the unknown data symbols unused.

Condition: This is a proposed sensing use of the link. Useful atmospheric detection still needs experimental validation.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 3. The detection question

Explain the difference between detecting an enhancement and measuring an absolute background concentration. The reference is a finite, noisy acquisition. Other gases remain unchanged in this first example. A positive decision means consistency with the chosen CH3CN template under these assumptions, not proven chemical specificity in an unknown mixture.

Condition: One path does not recover an arbitrary vertical profile or a 3D image.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 4. Why a molecule can change a radio signal

Absorption is a reduction of the power in the directly received signal. The receiver is not photographing molecules or collecting a reflected image. HITRAN is a spectroscopic database that supplies line frequencies, intensities and broadening data. The calculation combines those data with pressure and temperature along the path. A Voigt line shape convolves Doppler broadening and collision broadening. This slide introduces the physical mechanism; the later integral specifies the model mathematically.

Condition: Other molecules can have overlapping signatures. The first example assumes their concentrations do not change.

Sources:

- <https://hitran.org/lbl/>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 5. Many frequencies in one transmitted signal

Frequency is oscillations per second. GHz means 10^9 Hz. The center frequency says where the band lies, while bandwidth says how wide it is. Orthogonal means the chosen tones have zero cross inner product over the useful symbol interval in the ideal synchronized model. Known pilots let the receiver infer amplitude and phase changes without knowing the gas concentration. A short cyclic prefix is included between useful intervals to accommodate channel delay spread. Doppler shifts from motion and phase noise disturb ideal separation. The receiver also carries data, but this teaching calculation uses only the known pilots.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 6. How to read the radio power units

For the same impedance, power is proportional to the square of amplitude. This explains 20 log10 for field amplitude versus 10 log10 for power. Negative dBm means less than 1 mW, not negative power. Antenna gain describes concentrating radiation or collecting an incoming wave, not amplifier output. A link budget is simply the accounting from total transmit power to received power after all gains and losses. Dividing a fixed total power among K equal tones subtracts 10 log10(K) dB per tone. RF average power, electrical input power and radar pulse peak power are distinct.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 7. What the receiver is trying to distinguish

Reference means the baseline transmission. Sample means the transmission after a specified concentration enhancement. Both acquisitions have finite thermal noise. The values here are derived from the saved first tone, not invented illustrative observations. The molecular amplitude ratio is 10^(−a_k q/20). The worked sample concentration is a deliberately chosen simulation input, not a claim about typical background air. The detector later combines all frequencies and accounts for uncertainty rather than interpreting this one tone alone.

Condition: This is the predicted molecular effect for the assumed profile, before adding noise. It is not a measured change.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_observation.csv>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 8. The intuition

The molecular template is calculated from spectroscopy, not drawn by hand. Thermal averaging reduces random receiver uncertainty. Persistent calibration errors do not disappear simply by collecting more pilots. Unknown gain offset and gain slope are fitted so that they do not automatically count as gas.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 9. The 90° geometry

Angles must be defined: ground elevation, satellite off nadir angle and Earth central angle differ. The example sets the ground elevation to 90 degrees. A 550 km orbit is a chosen geometry, not a retrieved orbit. The physical atmosphere occupies only part of the 550 km propagation path. Coverage values and moving geometry are retained in the research note.

Condition: This is a static zenith benchmark. A real satellite keeps moving during acquisition.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>

## 10. What the hardware sources demonstrate

Sen et al. is experimental terrestrial evidence. TeraLink is a proposed space link with qualification work ongoing. Cooper et al. reports a frequency multiplier source, not a complete wideband satellite modem. RF average power, peak radar power and electrical power are different quantities. Increasing the simulated power to 1 W or 10 W is only an engineering sensitivity, not a demonstrated payload capability.

Condition: The sources do not demonstrate the full bandwidth, linear output, tracking and calibration together.

Sources:

- <https://www.nature.com/articles/s41928-022-00897-6>
- <https://arxiv.org/html/2606.15410v1>
- <https://doi.org/10.1109/JMW.2025.3610360>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 11. The chosen link budget inputs

G = η(πDf/c)². A 1 m ground reflector also appears in the TeraLink design analysis, with 60% efficiency there; this example uses an assumed 65%. The 10 cm equivalent circular transmit aperture is not an assertion that the published 9 × 9 cm horn array has this exact geometry. Calculated uniform aperture beamwidths are about 0.7455 degrees for transmit and 0.07455 degrees for receive. Both pointing and surface accuracy matter.

Condition: The linear average power available for OFDM after amplifier backoff remains unverified.

Sources:

- <https://arxiv.org/html/2606.15410v1>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/antennas.csv>

## 12. The OFDM frequency grid

The tone centers are 230 GHz + (k+1/2)Δf for k from 0 to 1023. Thus the first center is 230.0048828125 GHz and the last is 239.9951171875 GHz. The cyclic prefix is a short copy of the end of the symbol placed at its beginning to accommodate channel delay spread; its duration here is assumed. A frame is a repeated schedule of 10,000 symbols. Residual frequency error is another design assumption. This is not a validated hardware waveform. Unknown data symbols are not used for sensing in this tutorial. The spacing appendix explains the comparison.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/ofdm_spacing.csv>

## 13. Twenty seconds include the reference

Each acquisition transmits 88,960,000 complete symbols. The two acquisitions leave 0.001792 s unused because only complete frames count. The reference is not exact and is not free. Ideal correction of delay, phase, Doppler and gain is assumed over these windows; a static 90 degree path cannot literally persist for twenty seconds in a LEO pass.

Equation:

$$
M=\left\lfloor\frac{10\ \mathrm{s}}{10{,}000\times112.4\ \mathrm{ns}}\right\rfloor\!\times30=266{,}880
$$

M is the number of known pilot observations per tone, per acquisition.

Condition: Waiting for comparable geometry, calibration and reference availability adds operational time.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 14. The molecular template comes from spectroscopy

17,880 retained CH3CN transitions from local isotope ID 1 are used. Their acquired line centers span 2.77489–2003.4586 GHz, and the model includes the acquired line wings. Natural isotope abundance is already included in HITRAN line intensity. HAPI Voigt and TIPS2025 supply temperature dependence. At q = 1 µg/m³, n1(0) is approximately 1.467 × 10^16 molecules/m³ using molar mass 41.053 g/mol. HAPI cross sections in cm² require density in cm⁻³ and path in cm. The mass column is approximately 1500q µg/m². ITU oxygen/water attenuation is modeled separately without duplicating these contributions in HITRAN.

Equation:

$$
c(z)=q e^{-z/H_g},\quad H_g=1500\ \mathrm{m}\qquad a_k=\frac{10}{\ln 10}\int_0^{100\ \mathrm{km}}\sigma_k(z)n_1(z)\,dz
$$

q: surface equivalent enhancement (µg/m³) · σₖ: effective absorption area per molecule
n₁: molecular density for q = 1 µg/m³ · aₖ: dB per (µg/m³). Use consistent length units in the integral.

Condition: The vertical shape is assumed. The model does not measure concentration at each height.

Sources:

- <https://hitran.org/lbl/>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/physics_provenance.json>

## 15. The acetonitrile spectral pattern

Every plotted value is taken from tone_by_tone.csv. A gain offset and linear gain slope can explain parts of this pattern. The estimator therefore uses the part that remains after projecting out those nuisance directions. The displayed curve is the model for the assumed exponential vertical profile.

Condition: Calculated absorption from external line parameters, not a measured satellite spectrum.

Sources:

- <https://hitran.org/lbl/>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/tone_by_tone.csv>

## 16. One tone: the complete power accounting

These values describe the reference, with enhancement q = 0. A sample enhancement subtracts a_k q dB additionally. The total average RF power must be divided among all active tones. Gain is a power gain. The first tone is shown for auditable arithmetic, while the simulation recomputes all frequency dependent terms for every tone.

Sources:

- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/tone_by_tone.csv>

## 17. Receiver noise determines the pilot uncertainty

The integrated atmosphere contributes attenuation and thermal emission. The receiver noise temperature convention uses the 290 K reference temperature, but atmospheric sky temperature is calculated independently. Antenna spillover and hardware thermal losses require more detailed measurements for a real terminal. The reference SNR across the full band is between −0.1874 and −0.1657 dB.

Equation:

$$
T_e=T_0\left(10^{NF/10}-1\right),\qquad N_k=k_B(T_{\mathrm{sky},k}+T_e)\Delta f,\qquad\rho_{r,k}=P_{r,k}/N_k
$$

NF: receiver added noise, expressed as a noise figure (7 dB) · T₀ = 290 K · Tₑ: equivalent noise temperature
T_sky: sky brightness temperature (K) · k_B: Boltzmann constant · Nₖ: noise power (W) · ρ: signal to noise ratio

Condition: Sky emission and receiver noise are counted once. Noise figure is not applied twice.

Sources:

- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/tone_by_tone.csv>

## 18. The observation matrices

Each W_r,k,m is independent circular complex Gaussian noise with expected squared magnitude N_k. With unit pilots, |h_r,k|² is received power. This equation defines the physical observation model. The implementation draws exact coherent Gaussian pilot means as sufficient statistics, avoiding storage of the huge Y matrices. It does not run a full 10 GHz waveform, IFFT, cyclic prefix, synchronization or payload decoder.

Equation:

$$
\mathbf Y_r=\operatorname{diag}(\mathbf h_r)\mathbf X_r+\mathbf W_r,\qquad r\in\{0,1\}
$$

r = 0: reference · r = 1: sample · k: tone · m: pilot · |hᵣ,ₖ|² = received power with unit pilots

Condition: Delay, phase and carrier frequency corrections are ideal in this observation model.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 19. Averaging produces one channel estimate per tone

The complex mean distribution is exact for the stated independent Gaussian pilot model. Its use avoids simulating 273 million complex samples per acquisition. The minimum coherent mean SNR exceeds 255,000 under the baseline, which supports the subsequent log amplitude delta approximation. This mathematical reduction does not demonstrate the stability or tracking of a physical receiver.

Equation:

$$
\widehat h_{r,k}=\frac{1}{M}\sum_{m=1}^M Y_{r,k,m}X_{r,k,m}^{*},\qquad\widehat h_{r,k}\sim\mathcal{CN}\!\left(h_{r,k},\frac{N_k}{M}\right)
$$

M = 266,880 pilots per tone in each acquisition · *: complex conjugate
CN: circular complex Gaussian distribution, with stated complex variance

Condition: Persistent spectral calibration error survives this averaging.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 20. The reference ratio becomes an attenuation vector

The factor is 20 because the ratio uses field amplitude. Equivalently, the power ratio uses 10 log10. The modeled calibration residual enters this differential dB vector once per reference/sample pair. Weather mismatch can add a structured bias and is not automatically canceled.

Equation:

$$
y_k=-20\log_{10}\!\left(\frac{|\widehat h_{1,k}|}{|\widehat h_{0,k}|}\right),\qquad \mathbf y\in\mathbb R^{1024}
$$

yₖ: differential attenuation (dB) · ĥ₀: reference channel estimate · ĥ₁: sample channel estimate

Condition: An amplitude equalizer that removes the molecular pattern would also remove the sensing evidence.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 21. The design matrix separates gas from gain changes

The nuisance matrix B = [1,u] has dimension 1024 × 2. Fitting nuisance terms costs information but avoids attributing simple gain changes to gas. A different changing gas or an arbitrary nonlinear calibration error can still imitate part of a. The appendix lists every entry for a five tone subset.

Equation:

$$
\begin{gathered}\mathbf y=\mathbf A\boldsymbol\theta+\boldsymbol\varepsilon,\qquad\mathbf A=\begin{bmatrix}\mathbf a&\mathbf 1&\mathbf u\end{bmatrix}\in\mathbb R^{1024\times3}\\\boldsymbol\theta=\begin{bmatrix}q&b_0&b_1\end{bmatrix}^{T},\qquad u_k=\frac{f_k-\bar f}{f_{\max}-f_{\min}}\end{gathered}
$$

a: molecular template [dB per (µg/m³)] · q: enhancement (µg/m³) · ε: remaining measurement error (dB)
b₀: gain offset (dB) · b₁: gain slope coefficient (dB) · u: dimensionless, spanning −0.5 to +0.5

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 22. The covariance includes both measurements

The log ratio variance is a high coherent mean SNR approximation. rho_1,k(q) = rho_0,k × 10^(−a_k q/10). C(q) is thus slightly concentration dependent. The calibration covariance already describes a differential residual, so it must not be doubled or divided by M again. The detector fixes its weights using C(0), while positive concentration power calculations evaluate C(q).

Equation:

$$
\begin{gathered}\mathbf C(q)=\operatorname{diag}(v_k(q))+\sigma_{\mathrm{cal}}^2\mathbf R,\quad R_{ij}=e^{-|f_i-f_j|/(10\ \mathrm{GHz})}\\v_k(q)=\frac{(20/\ln10)^2}{2M}\left[\rho_{0,k}^{-1}+\rho_{1,k}(q)^{-1}\right]\end{gathered}
$$

C: 1,024 × 1,024 covariance in dB² · vₖ: thermal variance of the log ratio
ρ₀, ρ₁: linear per pilot SNR · σ_cal = 0.001 dB: assumed differential residual standard deviation

Condition: The 0.001 dB residual and its frequency correlation are assumptions, not receiver measurements.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 23. Whitening and removal of nuisance directions

The code uses Cholesky solves and an SVD basis, not explicit matrix inverses. L is 1024 × 1024, B and Q are 1024 × 2, and r is 1024 × 1. Whitening means the null noise covariance becomes identity. Projection onto the orthogonal complement of the nuisance span provides the generalized least squares concentration estimator.

Equation:

$$
\begin{gathered}\mathbf C(0)=\mathbf L\mathbf L^T,\quad\widetilde{\mathbf y}=\mathbf L^{-1}\mathbf y,\quad\widetilde{\mathbf a}=\mathbf L^{-1}\mathbf a,\quad\widetilde{\mathbf B}=\mathbf L^{-1}\mathbf B\\\mathbf r=(\mathbf I-\mathbf Q\mathbf Q^T)\widetilde{\mathbf a}\end{gathered}
$$

L: Cholesky factor of null (q = 0) covariance · B = [1,u] · Q: orthonormal basis for columns of L⁻¹B
r: the whitened molecular pattern after removing gain offset and slope

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 24. One row of weights estimates concentration

A positive or negative H entry is expected because the filter rejects nuisance directions. Ha differs from one by 5.55 × 10^−16 and the maximum magnitude of HB is 9.56 × 10^−13 in the saved arrays. These are algebraic checks, not experimental validation. The null standard deviation includes both finite acquisitions and the assumed persistent covariance.

Equation:

$$
\widehat q=\frac{\mathbf r^T\widetilde{\mathbf y}}{\mathbf r^T\mathbf r}=\mathbf H\mathbf y,\qquad\mathbf H=\frac{\mathbf r^T\mathbf L^{-1}}{\mathbf r^T\mathbf r},\qquad s_0^2=\mathbf H\mathbf C(0)\mathbf H^T
$$

H: 1 × 1,024 concentration weights [(µg/m³)/dB] · q̂: estimated enhancement (µg/m³)
s₀: null standard deviation of q̂ (µg/m³)

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/verification.json>

## 25. A fixed threshold turns the estimate into a decision

s1(q) = sqrt(H C(q) H^T), with H frozen at the null. Gaussian power is 1 − Φ((τ−q)/s1(q)). This yields 50.5813965969 µg/m³, while the constant variance shortcut yields 50.5584696236. The detection threshold is not itself a 95% sensitivity limit. Repeated searches across species, bands or time windows require a false alarm policy beyond this single test.

Equation:

$$
H_0:q=0,\quad H_1:q>0,\qquad\widehat q>\underbrace{z_{0.99}s_0}_{\tau}=2.32635\times12.7313=29.6174\ \mathrm{\mu g/m^3}
$$

τ: decision threshold · z₀.₉₉: standard normal 99th percentile · false alarm target α = 1%
s₁(q) = √[H C(q) Hᵀ]: standard deviation when the enhancement is q, using the fixed null weights H

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 26. One simulated observation crosses the threshold

The true q was fixed at the analytical 95% power concentration before drawing the observation. Random seed 20261005. The estimate differs from truth because this is one noisy draw. A successful example does not establish 95% empirical performance. The figure contains all 1024 tones and includes the saved persistent calibration residual. This is simulated evidence, not a measured spectrum.

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_example.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_observation.csv>

## 27. Repeated simulations retain the failed low concentration case

At q = 0 the simulation gives 113 detections out of 10,000. At q = 1, 131/10,000. At q = 50.5814, 9475/10,000. Intervals are the saved 95% binomial intervals. Simulated complex pilot means test the analytical approximation within the same physical and error model. They do not validate an orbital receiver or measured calibration statistics.

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/receiver_control.csv>

## 28. The result does not establish background monitoring

The EMeRGe article uses a winter IAGOS reference from selected aircraft data during 2012–2016. This is not a universal surface concentration. Conversion uses 1 ppbv = 1.73623578 µg/m³ at 288.15 K and 101325 Pa. The comparison is contextual: a selected atmospheric mixing ratio and a modeled differential amplitude with an assumed profile are different observables. Do not describe this benchmark as demonstrated ambient pollution detection.

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://acp.copernicus.org/articles/23/1893/2023/index.html>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>

## 29. What is needed for a physical demonstration

The present evidence supports a conditional computational example. Future work on molecular scattering must distinguish molecular absorption and emission from elastic scattering, and molecular effects from refractive index turbulence. Multiple receivers alone do not guarantee 3D identifiability. A tomography forward model would use ray lengths and spectral coefficients across voxels and needs adequate angular diversity. The supervisor revision includes a nonresonant scattering screen and a corrected PM extinction analysis.

Condition: This tutorial models direct transmission. Molecular scattering and multistatic imaging need a separate feasibility study.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 30. Appendix · Every entry of a five tone design matrix

The selected zero based tone indices are 0, 255, 511, 767 and 1023. Values come directly from worked_example.json. The full precision arrays are saved there and in matrices.npz. Values displayed here are rounded, so manual reconstruction has rounding error.

Equation:

$$
\mathbf y_5=\mathbf A_5\begin{bmatrix}q&b_0&b_1\end{bmatrix}^{T}+\boldsymbol\varepsilon_5,\qquad\mathbf A_5\in\mathbb R^{5\times3}
$$

The table scales only the a column by 10⁴ for readability. Use its original units in the calculation.

Condition: This subset is only an arithmetic illustration. The main result uses all 1,024 tones.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_example.json>

## 31. Appendix · The five tone covariance matrix

For example C00 = 0.00029515286513673 dB². The displayed diagonal value is 2.951529 because the table is in units of 10^−4 dB². The first and last off diagonal entry is 3.68238873913915 × 10^−7 dB². The five tone estimator must be recomputed using A5 and C5; simply taking five entries of the full H is not the same estimator.

Condition: Assumed, unmeasured 0.001 dB differential calibration residual · 20 s total acquisition

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_example.json>

## 32. Appendix · Multiplication gives the five tone estimate

Compute H5 with the same whiten/project method using A5 and C5, then form the dot product with y5. The true enhancement is still 50.5814 µg/m³. Discarding almost all tones gives a much larger uncertainty and this failed decision. The 1024 tone estimate was 39.4247 µg/m³ with threshold 29.6174. The full arrays, not rounded slide values, produce the saved results.

Equation:

$$
\widehat q_5=\mathbf H_5\mathbf y_5=171.7494,\quad s_{0,5}=165.1163,\quad\tau_5=384.1179\ \mathrm{\mu g/m^3}
$$

H₅ weights have units (µg/m³)/dB. Both q̂₅ and s₀,₅ are in µg/m³.

Condition: 20 s total · ideal tracking · assumed, unmeasured 0.001 dB calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/worked_example.json>

## 33. Appendix · The spacing comparison

All four candidates keep 10 GHz total bandwidth and 25 dBm total RF power. The CP is always 10 ns. ICI is intercarrier interference from the stated residual carrier frequency offset, using a separate analytical screening calculation. The ideal q95 results do not incorporate ICI. Residual 100 kHz and the 0.1% cap are illustrative choices; phase noise and measured channel delay spread remain unknown. Therefore this is a limited trade study, not a global optimum or complete waveform validation.

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/ofdm_spacing.csv>

## 34. Appendix · More RF power helps, conditionally

All points use the same 10 cm transmit and 1 m receive apertures, 65% efficiencies, 7 dB NF, and 5 dB implementation loss. The 17 dBm point illustrates an 8 dB reduction relative to the 25 dBm design anchor; it is not a required OFDM backoff specification. 30 dBm is 1 W and 40 dBm is 10 W. These last cases are unproven hardware sensitivity scenarios, not demonstrated wideband orbital transmitters. Neither increased power nor averaging removes arbitrary systematic error.

Condition: 20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/sensitivity.csv>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 35. Appendix · Calibration and background change the result

The first three rows use the positive concentration covariance in the saved power and calibration sweep. The last row is explicitly a local constant covariance approximation from background_nuisance.json, so it should not be presented as exactly the same finite q root calculation. A 1% water partial pressure change at fixed temperature and total pressure produces about +0.579 µg/m³ blank bias under the original nuisance model; a +1 K change at fixed total and water partial pressures produces −0.750 µg/m³. These are selected perturbations, not a distribution of real weather or an exhaustive robustness test.

Condition: 20 s total · ideal tracking · every calibration level is assumed and unmeasured

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/sensitivity.csv>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/background_nuisance.json>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/weather_mismatch.csv>

## 36. Appendix · The satellite moves during a measurement

These are a circular 550 km overhead pass geometry screen using the repository motion model. Doppler signs follow the receding satellite after zenith convention. The calculation omits a full orbit and ground rotation model. At ±5 s around zenith, elevation is about 86.05 degrees. Even near zenith the phase evolves rapidly; an instantaneous zero radial speed does not imply a constant channel over the measurement.

Condition: The static sensitivity calculation assumes ideal tracking. It does not establish moving link performance.

Sources:

- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/motion.csv>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>

## 37. Sources · Hardware and atmospheric context

The full clickable source URLs are listed below. Hardware sources support only their stated evidence scope. The EMeRGe/IAGOS background reference is contextual, not a universal ground concentration.

Sources:

- <https://www.nature.com/articles/s41928-022-00897-6>
- <https://arxiv.org/html/2606.15410v1>
- <https://doi.org/10.1109/JMW.2025.3610360>
- <https://acp.copernicus.org/articles/23/1893/2023/index.html>

## 38. Sources · Physics and reproducible calculations

Exact links follow. matrices.npz stores the full A, C and H arrays. worked_example.json stores all entries for the five tone example. manifest.json records inputs, outputs and package versions. HAPI/HITRAN acquisition requirements and the full run command are in docs/55. Presentation preparation reads saved outputs and does not invent a new physical dataset.

Sources:

- <https://hitran.org/lbl/>
- <https://www.itu.int/rec/R-REC-P.835-7-202408-I/en>
- <https://www.itu.int/rec/R-REC-P.676-13-202208-I>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/55_zenith_single_compound_walkthrough.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/docs/54_supervisor_revision_2026_10_05.md>
- <https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/b94f3fe/results/zenith_single_compound/manifest.json>
