# Supervisor presentation notes

Research snapshot: 461a3ba. Each task has method and result slides.


## Slide 1: Sub-THz atmospheric sensing



What worked, how we achieved it, and what remains unresolved

Guillem Moreno Garcia
Universitat Politècnica de Catalunya
Supervisor research review · 27 September 2026





This review describes the research snapshot at commit 461a3ba. Sensing performance remains conditional simulation. The original proposal contains eleven numbered subtasks.


Sources: docs/49_completion_audit_and_fixes.md, I2R_proposal_THz_ISAC (1).pdf


## Slide 2: Problem statement



Can a satellite communication downlink also detect gas and particle concentration changes using the same transmitted signal?

The proposal covers 60–400 GHz. Gas rotational lines provide spectral structure. Small particles produce a much smoother extinction signature.

The intended outcome combines useful recall, defensible concentration limits and an acceptable communication cost.


Equation: Observation = pollutant attenuation + atmospheric background + instrument error + noise


The practical question is whether pollutant information survives the other unknowns.


LaTeX:

```latex
\underbrace{\mathbf a}_{\text{observation}}=\underbrace{\mathbf D\mathbf c}_{\text{pollutants}}+\underbrace{\mathbf N\boldsymbol\beta}_{\text{background and instrument}}+\underbrace{\mathbf e}_{\text{noise}}
```


Additional evidence: Frequency scope = 60–400 GHz; Satellite altitude = 550 km; Current outputs = 5 VOCs + 3 PM; Family false alarms = 1% budget


Notation legend:

a: measured attenuation vector (dB)
D: target spectral response matrix
c: target concentrations (µg/m³)

N: background / instrument response matrix
β: nuisance parameter vector
D c and N β: attenuation contributions (dB)

e: measurement error vector (dB)
Bold letters: vectors or matrices
Matrix products sum spectral contributions



A correct forward model alone does not establish a useful environmental sensor.




Sources: I2R_proposal_THz_ISAC (1).pdf, docs/49_completion_audit_and_fixes.md


## Slide 3: What we have achieved

A completed computational assessment with a conditional VOC improvement


Achievement | Evidence | Boundary
Physical model | Layered gas, particle, ray and thermal calculations | Conditional atmospheric and material assumptions
VOC detection | CH₃CN recall 97.67% at 1 µg/m³ | 20 s total and assumed 0.0001 dB residual
Engineering comparison | Sequential bands and moving coded-frame controls | RF specifications remain unmeasured
Failure diagnosis | PM information, gain drift and communication cost quantified | Useful joint VOC/PM retrieval remains open


Additional evidence: CH₃CN interval = 97.36–97.96%; Family false alarms = 0.79%; Band-selection gain = 40.27 percentage points



The 97.67% result uses the selected five-gas design with matched reference weather, 45° elevation, 23 dBm and 6 dB noise figure.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. 10,000 positive trials and 10,000 null trials. Exact recall interval 97.355–97.957%. Family false alarms 0.79%. All five gases and two PM masses remain unknown.


Sources: docs/51_joint_design_time_calibration_results.md, docs/49_completion_audit_and_fixes.md


## Slide 4: The original eleven tasks




Task | Original requirement | Current outcome
1.1 | Stratified atmosphere | Implemented with standard and measured weather
1.2 | Spectroscopic inputs | Five target VOCs and traceable catalog gaps
1.3 | Line shape and slant integration | Voigt profiles and refracted spherical paths
1.4 | Particle extinction baseline | Rayleigh and Mie models, negative retrieval finding
2.1 | Link and radio parameters | Explicit sequential receiver and resource budget
2.2 | Simulated CSI | AWGN and bounded moving waveform controls
3.1 | Spectral separation | Joint inference with nuisance projection
3.2 | Concentration inversion | Payload moments and signed statistical estimates
4.1 | Variance lower bounds | Nuisance-aware likelihood and Fisher bounds
4.2 | Sensitivity | Common VOC/PM multivariable comparisons
4.3 | Detection floors and standards | Conditional limits, no positive compliance claim


Additional evidence: Physical subtasks = 4; Radio subtasks = 2; Inversion subtasks = 2; Performance subtasks = 3





Each numbered task receives method and result slides. Task 3.2 lists statistical, optimization and ML methods as alternatives. A neural network is not a mandatory missing requirement.


Sources: I2R_proposal_THz_ISAC (1).pdf, docs/49_completion_audit_and_fixes.md


## Slide 5: Evidence and operating conditions




Evidence | What it supports | What it cannot establish
HITRAN / ITU models | External physical parameters | Measured atmospheric radio performance
NOAA weather soundings | Actual weather profiles at selected times | Paired VOC/PM concentration truth
Monte Carlo responses | Conditional recall and concentration errors | Field recall under unknown model error
Raw coded OFDM frames | Bounded modem and synchronization checks | Full mission or continuous trajectory validation
Public water / calcite data | Limited independent physical checks | Calibrated joint VOC and PM retrieval


Additional evidence: Trials per class = 10,000; Current MC cases = 12; Reference / sample = 10 s / 10 s at 20 s; Measured field recall = Unavailable



Every favorable result needs its time, calibration, concentration and receiver assumptions.

Default current comparison: Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. Calibration standard deviation denotes an additional differential spectral residual after reference subtraction. Zero residual is ideal. Nonzero residuals are also unmeasured assumptions.


Sources: paper/current_study.tex, docs/50_species_methods_and_percentage_guide.md


## Slide 6: Task 1.1 · Stratified atmosphere



Implemented ITU-R P.835 reference layers through 100 km and NOAA IGRA measured weather profiles.

Interpolated temperature and log pressure / water vapor across height. Explicitly modeled the continuation above each sounding.


Equation: nₛ(z) = cₛ,₀ Nₐ / Mₛ · exp(−z/Hₛ)
P(z), T(z), water(z) determine the local spectrum


nₛ is molecular number density. Use consistent mass units for cₛ,₀ and molar mass Mₛ. Hₛ is an assumed concentration scale height.


LaTeX:

```latex
\begin{aligned}n_s(z)&=\frac{c_{s,0}N_A}{M_s}\exp\!\left(-\frac{z}{H_s}\right),\\[4pt] \text{local spectrum}&\;\text{depends on }P(z),\;T(z),\;\rho_{\mathrm{H_2O}}(z)\end{aligned}
```


Additional evidence: Soundings parsed = 521; Vertical levels = 103,322; Gas scale height = 1,500 m; PM scale height = 1,000 m


Notation legend:

s: gas species index
z: altitude (m)
n_s(z): molecular number density (m⁻³)
c_s,0: surface mass concentration (kg/m³)

N_A: Avogadro constant (mol⁻¹)
M_s: gas molar mass (kg/mol)
H_s: assumed concentration scale height (m)
exp: exponential function

P(z): atmospheric pressure (Pa)
T(z): atmospheric temperature (K)
ρ_H₂O(z): water vapour mass density (kg/m³)
Convert µg/m³ to kg/m³ before substitution

The channel responds to vertical weather variation instead of using one homogeneous slab.

The assumed pollutant profile does not become measured truth because the weather profile is measured.




Sources: paper/current_study.tex, docs/50_species_methods_and_percentage_guide.md, src/thz_isac/atmosphere.py


## Slide 7: Task 1.1 · Results and profile uncertainty




Equation: c(z) = c₀ exp(−z/H)  ⇒  retrieved c₀ depends on H


The reported concentration is a surface-equivalent enhancement under the chosen profile.


LaTeX:

```latex
c(z)=c_0\exp\!\left(-\frac{z}{H}\right)\qquad\Longrightarrow\qquad\widehat c_0\text{ depends on the assumed }H
```


Component | Implemented result | Remaining uncertainty
Weather archive | 103,322 levels from 521 soundings | Only selected dates enter sensing comparisons
Seasonal cases | January, April, July and September examples | Four profiles do not describe a population
Measured profile tops | 28.8–37.0 km above the station | Upper continuation follows a model
Gas / PM scale height | 1,500 m / 1,000 m | Unknown real pollutant distributions


Additional evidence: Atmosphere top = 100 km; Earlier weather cases = 4 months; Newest exact grid = 2 atmospheres


Notation legend:

c(z): mass concentration at altitude z
c₀: surface mass concentration
c and c₀ use the same mass / volume units

z: altitude (m)
H: assumed concentration scale height (m)
exp: exponential function

ĉ₀: estimated surface mass concentration
Hat: estimated quantity
⇒: implication under the assumed profile



Absolute ground concentration still requires baseline abundance and a validated column-to-surface mapping.

The newest exact receiver comparison uses standard atmosphere and the existing January sounding. Older broader sensitivity studies include the other months. Do not imply that all four profiles enter the newest 288-condition grid.


Sources: paper/current_study.tex, docs/50_species_methods_and_percentage_guide.md


## Slide 8: Task 1.2 · Spectroscopic extraction



Acquired line positions, strengths, pressure shifts, air broadening and temperature exponents from HITRAN.

Used isotope-specific masses and partition functions. Preserved line-source hashes and failed acquisition requests.


Equation: σₛ(ν,z) = Σℓ Sℓ(T(z)) Vℓ(ν − νℓ − δℓP(z))


σₛ is molecular cross section. Sℓ is line strength and Vℓ is the normalized Voigt profile for local temperature and pressure.


LaTeX:

```latex
\sigma_s(\nu,z)=\sum_{\ell\in s}S_\ell\!\left(T(z)\right)\,V_\ell\!\left[\nu-\nu_\ell-\delta_\ell P(z);\,T(z),P(z)\right]
```


Additional evidence: Current target gases = 5; Interfering gases = 4; Historical isotope tables = 34; Historical 60–400 GHz lines = 31,474


Notation legend:

s: species index, ℓ: spectral line index
ν: spectral frequency, ν_ℓ: line centre
z: altitude (m)
σ_s: molecular absorption cross section (m²)

S_ℓ(T): integrated line strength at T
V_ℓ: normalized Voigt line profile
S_ℓ × V_ℓ has cross section units
Use matching spectral units for S_ℓ and V_ℓ

T(z): atmospheric temperature (K)
P(z): atmospheric pressure
δ_ℓ: line shift per unit pressure
δ_ℓ P(z): pressure shift in frequency units

The joint receiver now includes five organic gas targets and four interfering gases.

HITRAN strengths already include natural isotope abundance. Applying it twice would understate absorption.

Voigt Doppler width uses isotope mass. Reported mass concentration uses the natural-mixture molar mass. HCOOH rotational intensities involve dipole-based calculations and do not remove spectroscopy uncertainty.


Sources: docs/50_species_methods_and_percentage_guide.md, https://hitran.org/media/refs/HITRAN-2024.pdf, https://www.hitran.org/docs/molec-meta/


## Slide 9: Task 1.2 · Every target gas and catalog gap

CO, O₃, SO₂ and NO₂ enter as interferents. H₂O and O₂ enter the atmospheric background.


Target | Chemical identity | Current sensing result
H₂CO | Formaldehyde, an aldehyde | Weak recall at 1 µg/m³
CH₃OH | Methanol, an alcohol | Weak recall at 1 µg/m³
CH₃CN | Acetonitrile, a nitrile | Strongest low-concentration candidate
CH₃Cl | Chloromethane, a halogenated gas | Improves at higher concentration
HCOOH | Formic acid, a carboxylic acid | Largest current 95% concentration limit


Additional evidence: Formaldehyde 95% limit = 7.846 µg/m³; Acetonitrile 95% limit = 0.927 µg/m³; Formic acid 95% limit = 30.550 µg/m³



CH₃Br, C₂H₄, CH₃F and CH₃I lack suitable lines in the acquired HITRAN window. This does not prove zero absorption.

VOC is the project shorthand for these selected organic gases, not a universal regulatory classification. The retained coverage review uses HITRAN2024 Table 1, page 7. Additional candidates need usable microwave strengths and pressure broadening before quantitative inference.


Sources: docs/50_species_methods_and_percentage_guide.md, results/joint_receiver_revision/missing_spectroscopy_review.json


## Slide 10: Task 1.3 · Voigt profiles and slant propagation



Combined Doppler and pressure broadening at each atmospheric layer.

Integrated along a spherical refracted ray connecting receiver and satellite. Used atmospheric interfaces and numerical quadrature.


Equation: Aₛ(ν) = (10 / ln 10) ∫ray nₛ(z) σₛ(ν,z) ds
Pout / Pin = 10^(−A/10)       b = n(r) r sin ζ


A is power attenuation in dB. b is the spherical ray invariant and ζ is the local zenith angle.


LaTeX:

```latex
\begin{aligned}A_s(\nu)&=\frac{10}{\ln 10}\int_{\mathrm{ray}}n_s(z)\,\sigma_s(\nu,z)\,\mathrm ds,\\[4pt]\frac{P_{\mathrm{out}}}{P_{\mathrm{in}}}&=10^{-A/10},\qquad b=n(r)\,r\sin\zeta\end{aligned}
```


Additional evidence: Current elevations = 30°, 45°, 60°, 90°; Numerical tolerance = 0.1% RMS; Gas convergence = 0.00381% RMS; Background convergence = 0.00200% RMS


Notation legend:

s: gas species, ν: frequency
A_s and A: power attenuation (dB)
n_s: molecular number density (m⁻³)
σ_s: molecular cross section (m²)

ds: differential path length along ray (m)
P_in and P_out: input and output power (W)
z: altitude (m)
ln: natural logarithm

b: conserved spherical ray invariant (m)
n(r): refractive index at radial distance r
r: distance from Earth’s centre (m)
ζ: local zenith angle

Elevation changes both the optical path and the received SNR.

A secant factor applied after vertical integration cannot represent all refracted path effects.




Sources: paper/current_study.tex, docs/50_species_methods_and_percentage_guide.md


## Slide 11: Task 1.3 · Numerical convergence and thermal correction




Equation: Tsky = Σᵢ Jν(Tᵢ)(1 − e^(−τᵢ)) e^(−Σⱼ<ᵢ τⱼ) + transmitted space term


Layer emission contributes receiver noise as well as attenuation.


LaTeX:

```latex
T_{\mathrm{sky}}=\sum_i J_\nu(T_i)\left(1-e^{-\tau_i}\right)e^{-\sum_{j<i}\tau_j}+J_\nu(T_{\mathrm{space}})e^{-\sum_i\tau_i}
```


Quantity | Relative RMS difference | Interpretation
Gas integration | 0.00381% | Below the declared 0.1% numerical tolerance
PM integration | 0.0225% | Below the declared tolerance
Atmospheric background | 0.00200% | Below the declared tolerance
Thermal calculation, initial | 0.11596% | Failed and triggered refinement
Thermal calculation, refined | 0.00319% | Passed without relaxing the tolerance


Additional evidence: Lower-atmosphere refinement = 100 m steps; Above 20 km = 500 m steps; Separate September check = 0.05304% RMS


Notation legend:

T_sky: equivalent sky noise temperature (K)
ν: frequency (Hz)
T_i: physical temperature of layer i (K)

J_ν(T): Planck brightness temperature (K)
τ_i: dimensionless optical depth of layer i
i: emitting layer, j: intervening layer

j < i: layers between layer i and receiver
T_space: space background temperature (K)
exp(−τ): power transmission through a layer



These are numerical checks on the tested grid. They do not measure atmospheric model error.

An independent recursive transfer reproduced the refined brightness. Earlier seasonal weather calculations use order two and only September has its own separate order check. Current selected-tone calculations inherit declared quadrature. Do not claim convergence for every possible weather realization.


Sources: paper/current_study.tex, docs/45_payload_bounds_results.md


## Slide 12: Task 1.4 · Rayleigh and Mie particle models



Integrated spherical Mie extinction over truncated lognormal particle size distributions and normalized it by dry mass.

Converted aerodynamic size cuts to physical particle dimensions using the assumed density and shape model.


Equation: κext = ∫ Cext(r) p(r) dr / ∫ (4πρr³/3) p(r) dr
Rayleigh: κabs ≈ 3k Im(q)/ρ     κsca ≈ 2k⁴r³|q|²/ρ


q = (m² − 1)/(m² + 2). k is wave number, m complex refractive index, ρ density and r sphere radius.


LaTeX:

```latex
\begin{aligned}\kappa_{\mathrm{ext}}&=\frac{\int C_{\mathrm{ext}}(r)\,p(r)\,\mathrm dr}{\int \frac{4\pi}{3}\rho r^3p(r)\,\mathrm dr},\\[4pt]\kappa_{\mathrm{abs}}&\simeq\frac{3k\,\mathrm{Im}(q)}{\rho},\qquad\kappa_{\mathrm{sca}}\simeq\frac{2k^4r^3|q|^2}{\rho}\end{aligned}
```


Additional evidence: Fine density = 1,500 kg/m³; Coarse density = 1,800 kg/m³; Fine index = 1.5 + 0.01i; Coarse index = 1.53 + 0.01i


Notation legend:

κ_ext, κ_abs, κ_sca: mass coefficients
Extinction, absorption, scattering (m²/kg)
C_ext(r): particle extinction cross section (m²)
p(r): particle number distribution in radius
r: physical particle radius (m)

ρ: particle material density (kg/m³)
k = 2π/λ: electromagnetic wavenumber (m⁻¹)
λ: wavelength in the surrounding medium (m)
q = (m² − 1)/(m² + 2): contrast factor
m: complex relative refractive index

Im(q): imaginary part of q
|q|²: squared complex magnitude
dr: radius integration element (m)
≃: Rayleigh approximation for small particles
The two final terms describe one radius r

Rayleigh and full Mie agree closely in this particle-size and frequency regime.

Material refractive index, shape, composition and humidity response remain assumptions.




Sources: docs/50_species_methods_and_percentage_guide.md, paper/current_study.tex


## Slide 13: Task 1.4 · PM definitions and the negative result




Equation: Var(PM10) = Var(fine) + Var(coarse) + 2 Cov(fine, coarse)


The fine model truncates below 0.03 µm. PM10 includes PM2.5, so they are not disjoint particle populations.


LaTeX:

```latex
\mathrm{Var}(\mathrm{PM}_{10})=\mathrm{Var}(c_{\mathrm{fine}})+\mathrm{Var}(c_{\mathrm{coarse}})+2\,\mathrm{Cov}(c_{\mathrm{fine}},c_{\mathrm{coarse}})
```


Output | Mass represented | Current result
PM1 | Below 1 µm aerodynamic diameter | Exploratory extra split fails numerical separation
PM2.5 | Fine mass below 2.5 µm | No useful mass retrieval in the tested grid
Coarse PM | Disjoint 2.5–10 µm mass | Nearly collinear with the fine-mode signature
PM10 | Fine plus coarse mass | Includes their covariance, no valid 95% limit


Additional evidence: Fine Rayleigh/Mie difference = 0.00086% RMS; Coarse difference = 0.0201% RMS; Three-bin inverse identity error = 0.508, rejected


Notation legend:

PM₁₀: total fine plus coarse mass (µg/m³)
c_fine: modeled PM2.5 mass (µg/m³)
c_coarse: modeled 2.5–10 µm mass (µg/m³)

Var: variance of a concentration estimate
Cov: covariance between the two estimates
All variance terms have units (µg/m³)²

Fine and coarse bins are disjoint
PM₁₀ = c_fine + c_coarse
Their covariance must enter the total error



A gain slope removes much of smooth Rayleigh absorption. Shared scattering shapes leave extremely weak size information.

Fine assumptions: density 1500 kg/m³, median physical size 0.5 µm, geometric spread 1.7, refractive index 1.5 + 0.01i. Coarse: 1800 kg/m³, 4 µm, 1.6, 1.53 + 0.01i. Rayleigh/Mie RMS differences are 0.00086% fine and 0.0201% coarse in the earlier physical check. Three-bin scaled inverse identity error is approximately 0.508 and fails the gate.


Sources: docs/50_species_methods_and_percentage_guide.md, docs/48_expanded_voc_pm_and_20s_calibration.md


## Slide 14: Task 2.1 · Link budget and sequential receiver



Specified a 550 km downlink, 23 dBm active transmit power, 0.50 / 0.30 m apertures and a nominal 6 dB noise figure.

Replaced the ideal simultaneous broad reference with one RF chain hopping across sixteen 16 MHz blocks within 220–330 GHz.


Equation: Pr(ν) = Pt(ν) Gt(ν) Gr(ν) [λ/(4πR)]² 10^(−A(ν)/10) / Limpl
SNR(ν) = Pr(ν) / {kB[Tsky(ν) + T₀(F − 1)]}


R is range, F the linear noise factor and Limpl the linear implementation loss. Receiver noise figure enters once.


LaTeX:

```latex
\begin{aligned}P_r(\nu)&=\frac{P_t(\nu)G_t(\nu)G_r(\nu)}{L_{\mathrm{impl}}}\left(\frac{\lambda}{4\pi R}\right)^2 10^{-A(\nu)/10},\\[4pt]\mathrm{SNR}(\nu)&=\frac{P_r(\nu)}{kB\left[T_{\mathrm{sky}}(\nu)+T_0(F-1)\right]}\end{aligned}
```


Additional evidence: Power / noise figure = 23 dBm / 6 dB; Implementation loss = 5 dB; Instantaneous bandwidth = 16 MHz; Settling per hop = 1 ms


Notation legend:

ν: frequency (Hz), λ: wavelength (m)
P_t, P_r: transmit and received power (W)
G_t, G_r: antenna power gains (linear)
L_impl: implementation loss (linear)
R: propagation distance (m)

A(ν): atmospheric attenuation (dB)
SNR: signal to noise power ratio (linear)
k: Boltzmann constant (J/K)
B: receiver noise bandwidth (Hz)
T_sky: sky noise temperature (K)

T₀: receiver noise reference temperature (K)
F: receiver noise factor (linear)
F = 10^(noise figure in dB / 10)
T₀(F − 1): receiver noise temperature (K)
Gains and losses must be converted from dB

Each block has sixteen 1 MHz tones. CP, pilots, full frames, reference time and retuning all consume the time budget.

23 dBm across the selected bands and 6 dB receiver noise are unverified RF requirements.




Sources: docs/50_species_methods_and_percentage_guide.md, docs/47_receiver_design_and_calibration.md


## Slide 15: Task 2.1 · Resources and communication cost




Equation: Rate = time-weighted Σk Δf log₂(1 + SNRk)


The comparison uses equal instantaneous bandwidth, power and CP/pilot overhead. Both reference and sample carry payload.


LaTeX:

```latex
\overline R=\sum_b\frac{t_b}{t_{\mathrm{total}}}\sum_{k\in b}\Delta f\log_2\!\left(1+\mathrm{SNR}_k\right)
```


Quantity | Current result
Total reference + sample time | 20 s, split equally
Actual frame transmission / retuning | 19.72 s / 0.032 s
Instantaneous bandwidth / RF chains | 16 MHz / one
Selected schedule Gaussian rate | 109.52 Mbit/s
Best tested fixed block Gaussian rate | 128.31 Mbit/s
Rate loss against that fixed block | 14.64%


Additional evidence: Selected center range = 224–318.67 GHz; Pilot / frame symbols = 30 / 10,000; CP / useful symbol = 1 / 16


Notation legend:

R̄: average Gaussian information rate (bit/s)
b: selected frequency block index
k: tone index within block b

t_b: transmission time in block b (s)
t_total: total acquisition time (s)
t_b / t_total: block’s time fraction

Δf: bandwidth per tone (Hz)
SNR_k: tone signal to noise ratio (linear)
log₂: base two logarithm



Zero architecture cost is not established. Gaussian rate is different from coded QPSK throughput.

Best fixed block among tested candidates is centered at 224 GHz. This is not a global optimum over every possible communications design. The older 1.382% number isolates schedule counts and must not replace the full 14.64% comparison.


Sources: results/joint_receiver_revision/communication_tradeoff.json, docs/51_joint_design_time_calibration_results.md


## Slide 16: Task 2.2 · CSI and raw waveform simulation



Generated complex line-of-sight observations with frequency-dependent attenuation and additive complex Gaussian noise.

Added raw IFFT/CP frames, timing acquisition, Doppler correction, pilot tracking and coded packet checks.


Equation: yk = hk xk + wk       wk ~ CN(0,Vk)
x[n] = IFFT{Xk}       hk contains path gain, phase and absorption


Separate raw frames test modem behavior. Large recall experiments draw joint sample moments and apply nonlinear inversion.


LaTeX:

```latex
\begin{aligned}y_k&=h_kx_k+w_k,\qquad w_k\sim\mathcal{CN}(0,V_k),\\[4pt]x[n]&=\operatorname{IFFT}\{X_k\}\end{aligned}
```


Additional evidence: Blocks / tones per block = 16 / 16; Frame length = 10,000 symbols; Pilots per frame = 30; Acquisition CFO stress = 100 kHz


Notation legend:

k: tone index, n: time sample index
x_k: transmitted tone symbol
y_k: received tone symbol
h_k: complex channel coefficient

w_k: additive complex receiver noise
V_k: noise variance in symbol power units
CN(0,V_k): circular complex Gaussian noise
Its real / imaginary variances are V_k / 2

X_k: frequency domain OFDM symbols
x[n]: transmitted time domain samples
IFFT: inverse fast Fourier transform
h_k scales amplitude and rotates phase

The simulation connects physical channel attenuation to a bounded moving receiver.

The large recall study does not generate every raw waveform sample for every Monte Carlo trial.




Sources: docs/50_species_methods_and_percentage_guide.md, results/joint_receiver_revision/scope_boundaries.json


## Slide 17: Task 2.2 · What the waveform controls establish




Equation: fD ≈ (vr / c) fc


Narrowband Doppler correction addresses carrier shift. Wideband time scaling requires additional receiver modeling.


LaTeX:

```latex
f_D\simeq\frac{v_r}{c}\,f_c
```


Control | Retained result | Boundary
Selected-frequency coverage | 16 fresh raw frames | One frequency spot check per selected block
Timing acquisition | 16 / 16 correct | Bounded integer timing model
Passive sensing | Identical decoded outputs in every case | Comparison uses the same scheduled modem
Coded information errors | 1,391 errors | Across 2,826,240 information bits
Full mission dynamics | Still open | Fractional timing, clock drift and time dilation


Additional evidence: Information bits = 2,826,240; Information bit errors = 1,391; Raw coded bit error rate = 0.0492%


Notation legend:

f_D: Doppler frequency shift (Hz)
f_c: carrier frequency (Hz)

v_r: signed radial relative velocity (m/s)
c: speed of light (m/s)

≃: first order narrowband approximation
The shift sign follows the velocity convention



Oscillator noise, pointing, multipath and realistic reference availability remain open.

These spot checks support bounded communication behavior, not a measured field recall or a continuous complete orbital pass. Selected_raw_frames.csv retains packet counts and residual CFO.


Sources: results/joint_receiver_revision/selected_raw_frames.csv, results/joint_receiver_revision/scope_boundaries.json


## Slide 18: Task 3.1 · Joint spectral isolation



Fitted all five gas signatures and two PM modes simultaneously.

Whitened the observation covariance and projected out gain offset/slope, atmospheric background and four interfering gases.


Equation: a = D c + N β + e       C = Cov(e)
P = I − QN QNᵀ       ĉ = H a


D contains target signatures. N contains nuisance signatures. QN spans the whitened nuisance space. An SVD constructs H.


LaTeX:

```latex
\begin{aligned}\mathbf a&=\mathbf D\mathbf c+\mathbf N\boldsymbol\beta+\mathbf e,\qquad\mathbf C=\operatorname{Cov}(\mathbf e),\\[4pt]\mathbf P&=\mathbf I-\mathbf Q_N\mathbf Q_N^{\mathsf T},\qquad\widehat{\mathbf c}=\mathbf H\mathbf a\end{aligned}
```


Additional evidence: Unknown target masses = 7; Reported outputs = 8 with PM10; Selected frequencies = 256 tones; Scaled identity tolerance = 10⁻⁵


Notation legend:

a: attenuation vector (dB), e: error (dB)
D: target response matrix
c, ĉ: true / estimated concentrations (µg/m³)
N β: nuisance attenuation contribution (dB)

C = Cov(e): observation covariance (dB²)
N: nuisance response matrix
β: nuisance coefficients
Q_N: orthonormal whitened nuisance basis

P: projector away from nuisance space
I: identity matrix, T: matrix transpose
H: linear concentration retrieval operator
Bold symbols denote vectors or matrices

Numerical gates check scaled H D ≈ I and nuisance rejection H N ≈ 0.

No algorithm can separate an arbitrary gain error that occupies the same spectral direction as the pollutant.




Sources: docs/50_species_methods_and_percentage_guide.md, scripts/joint_receiver_support.py


## Slide 19: Task 3.1 · Frequency selection improves five-gas inference



A deterministic coordinate-exchange screen selected sixteen blocks using the standard 45° design case.

The selection optimized the worst relative gas uncertainty while retaining PM and nuisance parameters. Exact tone spectra followed the coarse screen.


CH₃CN at 1 µg/m³ | Uniform bands | Selected bands
Simulated recall | 57.40% | 97.67%
Total acquisition time | 20 s | 20 s
Assumed residual standard deviation | 0.0001 dB | 0.0001 dB


Additional evidence: Deterministic starts = 3; Selected blocks = 16; Improved exact gas limits = 5 / 5

All five exact VOC information limits improve relative to the uniform design.

January weather and response draws did not choose bands. Global optimality and unknown-weather robustness remain unproved.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. The fresh uniform control is 57.40%. The historical 56.63% value belongs to an earlier independent simulation. The selected result is a conditional improvement at equal resources.


Sources: docs/51_joint_design_time_calibration_results.md, results/joint_receiver_revision/selection.json


## Slide 20: Task 3.2 · Payload moments estimate signal and noise



Used the existing constant-modulus QPSK payload instead of discarding most samples and retaining only 30 pilots per 10,000 symbols.

Applied the established M2M4 estimator with a finite-sample correction, then compared sample and reference powers.


Equation: M₂ = S + V       M₄ = S² + 4SV + 2V²
S = √(2M₂² − M₄)       A = −10 log₁₀(Ssample / Sreference)


S is received signal power. V is noise power. The moments separate signal and noise under the QPSK and Gaussian-noise model.


LaTeX:

```latex
\begin{aligned}M_2&=S+V,\qquad M_4=S^2+4SV+2V^2,\\[4pt]S&=\sqrt{2M_2^2-M_4},\qquad A=-10\log_{10}\!\left(\frac{S_{\mathrm{sample}}}{S_{\mathrm{reference}}}\right)\end{aligned}
```


Additional evidence: Pilot fraction per frame = 0.3%; Payload fraction per frame = 99.7%; Signal moments = Second and fourth; Modulation tested = QPSK


Notation legend:

M₂: second moment E[|y|²]
M₄: fourth moment E[|y|⁴]
y: received complex symbol
E: expectation, |y|: complex magnitude

S: received signal power
V: receiver noise power
M₂, S, V share power units
M₄ has squared power units

A: differential attenuation (dB)
S_sample: signal power in sample observation
S_reference: signal power in reference
log₁₀: base ten logarithm

More existing symbols contribute information without adding sensing transmissions.

Arbitrary QAM, nonlinear distortion or severe intercarrier interference invalidate these simple moments.

M2M4 is established prior work. The contribution is its application, resource accounting and conditional evaluation here. Invalid inversions count as failures. Large experiments use the joint asymptotic distribution of second/fourth sample moments and nonlinear inversion. Raw QPSK controls independently test bounded cases.


Sources: docs/50_species_methods_and_percentage_guide.md, docs/42_payload_recall.md, https://arxiv.org/abs/2506.15998, paper/current_study.tex


## Slide 21: Task 3.2 · Why payload reuse mattered

Earlier ideal broad reference, three target gases and zero persistent calibration residual


Historical control | Pilots | Payload M2M4 | Reference assumption
CH₃CN, 1 µg/m³, 10 s | 0.460% recall | 99.955% recall | Exactly known reference
CH₃CN, 1 µg/m³, 20 s total | 0.380% recall | 93.800% recall | 10 s independent reference + 10 s sample


Additional evidence: Pilot samples per frame = 30; Total symbols per frame = 10,000; Old physical architecture = Ideal simultaneous broad bands

Payload moments recover information that sparse pilot-only sensing discards.

The ideal broad architecture and zero residual assumption prevent direct transfer to deployed hardware.

Historical results in docs/42_payload_recall.md. This table compares methods within each original control. It is separate from the current five-gas hopping receiver and its eight-output false-alarm family. M2M4 itself is established prior work.


Sources: docs/42_payload_recall.md, docs/46_critical_calibration_assumption.md


## Slide 22: Task 3.2 · Detection gains are species dependent

20 s total, assumed 0.0001 dB residual, selected bands and standard atmosphere at 45°


Gas | Recall at 1 (%) | Misses at 1 (%) | c95 µg/m³ | Recall at c95 (%) | 95% CI at c95 (%) | RMSE at c95 (%)
Formaldehyde | 0.77 | 99.23 | 7.846 | 95.12 | 94.68–95.53 | 21.14
Methanol | 0.75 | 99.25 | 8.838 | 95.12 | 94.68–95.53 | 21.24
Acetonitrile | 97.67 | 2.33 | 0.927 | 95.12 | 94.68–95.53 | 21.49
Chloromethane | 3.58 | 96.42 | 3.918 | 94.72 | 94.26–95.15 | 21.64
Formic acid | 0.16 | 99.84 | 30.550 | 94.85 | 94.40–95.28 | 21.55


Additional evidence: Positive / null trials = 10,000 / 10,000; Family false alarms = 0.79%; Relative RMSE at 95% points = Approximately 21%

Acetonitrile reaches 97.67% recall at 1 µg/m³. Other gases require higher concentrations.

These are simulated detection frequencies, not measured field performance or concentration accuracy.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. Each positive and null class has 10,000 trials. Exact CH3CN interval 97.355–97.957%. Family false alarms 0.79%. At nominal 95% detection points relative concentration RMSE is about 21%, not 5%.


Sources: docs/51_joint_design_time_calibration_results.md, results/joint_receiver_revision/response_metrics.csv


## Slide 23: Task 4.1 · Lower bounds with nuisance parameters



Derived full QPSK and magnitude likelihood information with unknown signal power, noise power and finite reference uncertainty.

Profiled nuisance parameters before comparing the attainable concentration covariance with the estimator variance.


Equation: Jab = E[(∂ log p(y;θ)/∂θa)(∂ log p(y;θ)/∂θb)]
Jeff = Jcc − Jcη Jηη⁻¹ Jηc       Cov(ĉ) ⪰ Jeff⁻¹


c denotes target concentration and η all nuisance parameters. The Schur complement accounts for their uncertainty.


LaTeX:

```latex
\begin{aligned}J_{ab}&=\mathbb E\!\left[\frac{\partial\log p(y;\boldsymbol\theta)}{\partial\theta_a}\frac{\partial\log p(y;\boldsymbol\theta)}{\partial\theta_b}\right],\\[4pt]\mathbf J_{\mathrm{eff}}&=\mathbf J_{cc}-\mathbf J_{c\eta}\mathbf J_{\eta\eta}^{-1}\mathbf J_{\eta c},\qquad\operatorname{Cov}(\widehat{\mathbf c})\succeq\mathbf J_{\mathrm{eff}}^{-1}\end{aligned}
```


Additional evidence: Likelihoods = QPSK and magnitude; Unknown noise = Included; Finite reference = Included; Historical efficiency = 95.89–97.61%


Notation legend:

y: observed signal data
θ: complete unknown parameter vector
p(y;θ): likelihood of the observations
E: expectation under the assumed model

J_ab: Fisher information entry for θ_a, θ_b
c: target concentration vector (µg/m³)
η: nuisance parameter vector
J_cc, J_cη, J_ηη: Fisher matrix blocks

J_eff: information after nuisance profiling
ĉ: estimated concentration vector
Cov(ĉ): estimator covariance, units (µg/m³)²
−1: matrix inverse, ⪰: covariance lower bound

The bound identifies when replacing the estimator offers little remaining gain.

The bound is local and conditional on the likelihood, covariance and physical signatures.




Sources: docs/44_payload_information_derivation.md, docs/45_payload_bounds_results.md


## Slide 24: Task 4.1 · M2M4 is already close to the bound

Historical broad reference, three target gases, 20 s total and zero extra calibration residual


Equation: Efficiency = variance lower bound / estimator variance


Values near 100% leave little improvement available from estimator replacement in this control.


LaTeX:

```latex
\mathrm{Efficiency}=\frac{\text{variance lower bound}}{\text{estimator variance}}
```


Gas | CRLB / M2M4 variance | Historical 95% limit µg/m³
Formaldehyde | 95.89% | 4.456
Methanol | 97.61% | 10.307
Acetonitrile | 96.49% | 1.023


Additional evidence: Historical output family = 6; Acquisition split = 10 s + 10 s; Calibration benchmark = Zero extra residual


Notation legend:

Efficiency: lower bound / estimator variance
Displayed percentage = 100 × this ratio

Variance lower bound: conditional CRLB
CRLB: Cramér–Rao lower bound

Estimator variance: variance of M2M4 output
Both variances use the same concentration units²

The next substantial improvement came from frequency information and design.

These historical bounds use a different architecture and target family from the current five-gas receiver.

Standard atmosphere at 45°, charged 10 s reference plus 10 s sample, unknown noise and joint spectral nuisance. The prior six-output family differs from the current eight-output family. Do not use this table to rank current and old designs as equal conditions.


Sources: docs/45_payload_bounds_results.md


## Slide 25: Task 4.2 · Time and calibration jointly set uncertainty



Recomputed the link, absorption, emission and target fit when weather, elevation, bands or receiver noise change.

The latest common grid contains every VOC, PM2.5, coarse PM and PM10 in every operating condition.


Equation: C(t,σcal) = diag[Vsample(t/2) + Vreference(t/2)] + σcal²K
Kij = exp(−|νi − νj| / 10 GHz)


Thermal variance decreases with retained symbols. The additional calibration residual persists through the acquisition.


LaTeX:

```latex
\begin{aligned}\mathbf C(t,\sigma_{\mathrm{cal}})&=\operatorname{diag}\!\left[\mathbf V_{\mathrm{sample}}(t/2)+\mathbf V_{\mathrm{reference}}(t/2)\right]+\sigma_{\mathrm{cal}}^2\mathbf K,\\[4pt]K_{ij}&=\exp\!\left(-\frac{|\nu_i-\nu_j|}{10\,\mathrm{GHz}}\right)\end{aligned}
```


Additional evidence: Time grid = 2 / 20 / 100 s; Residual grid = 0 / 0.0001 / 0.001 dB; Noise-figure grid = 6 / 17 dB; Calibration draws = Once per acquisition


Notation legend:

C: attenuation covariance matrix (dB²)
t: total reference plus sample time (s)
t / 2: time assigned to each observation
V_sample, V_reference: variance vectors (dB²)

diag: diagonal matrix built from a vector
σ_cal: persistent residual standard deviation (dB)
K: dimensionless spectral correlation matrix
K_ij: correlation of frequency bins i and j

ν_i, ν_j: bin frequencies in matching units
10 GHz: assumed spectral correlation length
exp: exponential function
σ_cal² K: persistent covariance contribution

More time helps until persistent calibration error dominates.

The 10 GHz correlation length and each calibration standard deviation remain unmeasured assumptions.




Sources: docs/50_species_methods_and_percentage_guide.md, results/joint_receiver_revision/global_comparison_protocol.json


## Slide 26: Task 4.2 · Longer time cannot remove calibration error

Acetonitrile at 1 µg/m³, selected bands, standard atmosphere at 45°


Additional evidence: 20 s, 0 dB = 99.28% recall; 20 s, 0.0001 dB = 97.67% recall; 20 s, 0.001 dB = 4.36% recall; 100 s, 0.001 dB = 5.05% recall

At 0.001 dB, recall is only 4.36% at 20 s and 5.05% at 100 s.

Zero and nonzero residuals are sensitivity assumptions. No receiver stability measurement establishes them.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. Curves use separate finite Monte Carlo samples. The 100% observed values retain confidence intervals below perfect population recall. The covariance is persistent within each acquisition.


Sources: docs/51_joint_design_time_calibration_results.md, results/joint_receiver_revision/response_metrics.csv


## Slide 27: Task 4.2 · PM shares the full global comparison




Variable | Compared settings
Frequency plan | Uniform and selected sixteen-block schedules
Atmosphere | Standard and January sounding
Elevation | 30°, 45°, 60°, 90°
Reference + sample time | 2 s, 20 s, 100 s
Assumed calibration residual | 0, 0.0001, 0.001 dB
Receiver noise figure | 6 dB and 17 dB


Additional evidence: Common result rows = 2,304; Rejected settings = Standard, 30°, NF 17 dB; PM predicted recall = Approximately 0.125%

288 conditions × 8 outputs = 2,304 rows. Each output has 270 computed and 18 rejected conditions.

No valid 95% response limit for PM2.5 or PM10 anywhere in this grid.

Fixed 23 dBm transmit power, matched reference weather, 10 GHz residual correlation. All rejected cases are standard atmosphere, 30° elevation, 17 dB noise figure for both schedules and all times/calibrations. Their target separation fails the numerical gate. Failed rows remain present and do not receive fabricated zero recall.


Sources: results/joint_receiver_revision/global_comparison.csv, results/joint_receiver_revision/global_comparison_protocol.json


## Slide 28: Task 4.3 · Detection limits and percentage definitions



Fixed a 1% family false-alarm budget across eight outputs before observing outcomes.

Solved the concentration for nominal 95% power using positive-signal variance, then tested it with fresh simulated responses.


Equation: z = Φ⁻¹(1 − 0.01/8)       detect if ĉj > z snull
c95 = z snull + 1.64485 spositive(c95)


Positive absorption changes SNR and variance. The solution stays within at most 1 dB added absorption.


LaTeX:

```latex
\begin{aligned}z&=\Phi^{-1}\!\left(1-\frac{0.01}{8}\right),\qquad\widehat c_j>z\,s_{\mathrm{null}},\\[4pt]c_{95}&=z\,s_{\mathrm{null}}+1.64485\,s_{\mathrm{positive}}(c_{95})\end{aligned}
```


Additional evidence: One-sided target α = 0.01 / 8 = 0.00125; Null threshold z = Approximately 3.023; Positive power target = 95%; Absorption cap = 1 dB


Notation legend:

Φ⁻¹: inverse standard normal CDF
z: dimensionless null detection threshold
0.01: family false alarm probability budget
8: number of reported outputs

ĉ_j: estimate for target j (µg/m³)
s_null: standard deviation under the null
s_positive(c): standard deviation at mass c
Both standard deviations use µg/m³

c₉₅: concentration for 95% recall (µg/m³)
1.64485: Φ⁻¹(0.95), a normal quantile
>: target detection decision
The variance depends on positive concentration

Reports include low recalls, missed detections, exact binomial intervals and concentration RMSE.

95% detection power, a 95% confidence interval and 5% concentration error describe different quantities.

Recall = TP/(TP+FN). False alarms = FP/(FP+TN). Relative RMSE = sqrt(mean((estimate−truth)^2))/truth. Precision and F1 use artificial 50% prevalence. A missing in-domain solution remains unavailable. The PM10 output participates in the family although it derives from two masses.


Sources: docs/50_species_methods_and_percentage_guide.md, scripts/evaluate_joint_receiver.py


## Slide 29: Task 4.3 · Every 95% limit needs time and calibration

Nominal 95% response concentration in µg/m³, selected bands, standard atmosphere at 45°


Total s | Residual dB | H₂CO | CH₃OH | CH₃CN | CH₃Cl | HCOOH
2 | 0 | 25.778 | 27.695 | 2.917 | 12.206 | 102.781
2 | 0.0001 | 25.862 | 27.911 | 2.938 | 12.309 | 102.894
2 | 0.001 | 33.018 | 44.262 | 4.550 | 19.693 | 113.332
20 | 0 | 7.568 | 8.131 | 0.856 | 3.584 | 30.171
20 | 0.0001 | 7.846 | 8.838 | 0.927 | 3.918 | 30.550
20 | 0.001 | 21.913 | 35.377 | 3.557 | 15.567 | 56.267
100 | 0 | 3.361 | 3.612 | 0.380 | 1.592 | 13.400
100 | 0.0001 | 3.945 | 4.999 | 0.517 | 2.226 | 14.228
100 | 0.001 | 20.826 | 34.603 | 3.468 | 15.192 | 49.310


Additional evidence: CH₃CN, 20 s / 0.0001 dB = 0.927 µg/m³; CH₃CN, 100 s / 0.001 dB = 3.468 µg/m³; Valid PM limits in nine cases = 0



PM2.5, coarse PM and PM10 have no valid 95% response limit in these nine conditions.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. Values solve positive-response variance and precede Monte Carlo evaluation. Actual simulated recalls near 95% remain as measured fractions in the response CSV. All calibration levels are assumed.


Sources: docs/51_joint_design_time_calibration_results.md, results/joint_receiver_revision/response_metrics.csv


## Slide 30: Task 4.3 · Environmental interpretation remains open



Converted gas mass to surface-equivalent mole fraction using pressure, temperature and molar mass.

Observable: short slant-path enhancement relative to a reference. Ambient guidance has distinct location and averaging requirements.

PM reference masses are 15 and 45 µg/m³. These tests do not establish compliance.


Equation: ppm = cµg/m³ R T / (p Mg/mol)


The numeric conversion assumes the displayed mass and molar-mass units. PM has mass units and no gas ppm conversion.


LaTeX:

```latex
\chi_{\mathrm{ppm}}=\frac{c_{\mu\mathrm{g}/\mathrm m^3}\,R\,T}{p\,M_{\mathrm g/\mathrm{mol}}}
```


Additional evidence: H₂CO current limit ppm = 0.006179; CH₃CN current limit ppm = 0.000534; Limit conditions = 20 s / 0.0001 dB; Ambient PM test masses = 15 and 45 µg/m³


Notation legend:

χ_ppm: gas mole fraction in ppm
c: gas mass concentration in µg/m³
M: gas molar mass in g/mol

R: ideal gas constant, 8.314 J/(mol K)
T: local absolute temperature (K)
p: local atmospheric pressure (Pa)

1 ppm = 10⁻⁶ mol/mol
The stated mass units cancel the 10⁶ factor
This gas conversion does not apply to PM

The study reports conditional floors and an explicit negative / unverified standards assessment.

Unknown baseline abundance, vertical profiles, PM information and independent truth prevent a positive compliance claim.

The prior standards review discusses WHO 2021 ambient PM guidelines and separate indoor formaldehyde guidance. These are different domains and time averages. This presentation does not interpret short radio enhancements as regulatory measurements.


Sources: docs/50_species_methods_and_percentage_guide.md, docs/45_payload_bounds_results.md, docs/41_measurement_protocol.md


## Slide 31: Calibration is the critical engineering requirement



Zero calibration error means zero additional differential residual after modeled corrections. Thermal noise and reference uncertainty still remain.

At 20 s, the local CH₃CN requirement for 95% power at 1 µg/m³ is approximately 0.000146 dB residual standard deviation under the nominal covariance.


Equation: |bi| ≤ ε  ⇒  Bj = ε ‖Hj‖₁
Protected local requirement ≈ (z + 1.64485)sj + 2Bj


A persistent signed bias can move both the null threshold and the positive response in the adverse direction.


LaTeX:

```latex
\begin{aligned}|b_i|&\leq\varepsilon\quad\Longrightarrow\quad B_j=\varepsilon\,\lVert\mathbf H_j\rVert_1,\\[4pt]c_{95,\mathrm{protected}}&\simeq(z+1.64485)s_j+2B_j\end{aligned}
```


Additional evidence: Required local σ at 20 s = About 0.000146 dB; Nominal random σ = 0.0001 dB; Power change for 0.0001 dB = About 0.002303%; Field calibration records = None


Notation legend:

b_i: persistent bias in attenuation bin i (dB)
ε: upper bound on each |b_i| (dB)
i: spectral bin, j: retrieved target

H_j: row j of the concentration operator
‖H_j‖₁: sum of absolute row coefficients
B_j: resulting concentration bias bound (µg/m³)

s_j: concentration standard deviation (µg/m³)
z: null threshold, 1.64485: 95% normal quantile
c₉₅,protected: bias protected limit (µg/m³)
≃: local approximation with constant variance

Calibration requirements are now quantitative and retained with every result.

A small random standard deviation does not guarantee resistance to arbitrary drift or unknown hop gains.

The 0.000146 dB number is a local requirement, not a measured achieved accuracy. Independent hop-gain nuisance terms make the current separation unstable. Prior zero-calibration headline controls are retained separately in the permanent calibration note.


Sources: docs/46_critical_calibration_assumption.md, results/joint_receiver_revision/calibration_requirements.csv, docs/50_species_methods_and_percentage_guide.md


## Slide 32: Failures that constrain the claimed achievement




Failure or stress | Finding | Implication
PM mass and extra size split | Negligible useful information / unstable inverse | A successful optimizer cannot repair missing information
Unknown relative hop gains | Target separation fails | Requires calibrated relative spectral response
Weather mismatch | Frozen standard operator acquires bias | Matched-weather success is insufficient
Unamplified RF converter | Fails usable-SNR gate | Nominal power requires a complete RF chain
Modulation / receiver mismatch | Simple payload moments may become invalid | Receiver assumptions need dedicated validation


Additional evidence: Numerically rejected global cases = 18 / 288; Useful PM limits = 0 / 270 valid cases; Gaussian architecture rate loss = 14.64%



The intended general atmospheric VOC/PM instrument remains an open research outcome.

All listed failures remain in the current audit and retained stress outputs. The nominal 17 dB noise-figure grid also rejects standard atmosphere at 30° for both schedules. Successful runs do not conceal those cases.


Sources: docs/49_completion_audit_and_fixes.md, results/joint_receiver_revision/stress_sensitivity.csv


## Slide 33: Remaining problems and evidence needed




Open problem | Evidence required to close it
RF hardware and calibration | Measured power, noise, settling, spectral covariance and drift at selected tones
PM mass / composition | Paired optical properties, humidity, particle size and independent mass truth
Weather and concentration profiles | Independent profiles, column information and reference abundance
Full receiver dynamics | Continuous time-scaled channel with fractional timing, oscillator and pointing errors
Independent validation | Separate calibration and test campaigns with paired radio / concentration data
Deployment and environmental use | Applicable averaging domain, spectrum coordination and realistic operational coverage


Additional evidence: Nominal RF target = 23 dBm, NF 6 dB; Current calibration assumption = 0.0001 dB; Current physical truth = No paired radio/VOC/PM test





Complete remaining-work ledger: docs/49_completion_audit_and_fixes.md. Additional unresolved details include unequal dwell/global frequency optimization, spectroscopy uncertainty, real-time hardware latency, atmospheric horizontal variability and communication coding/adaptation baselines.


Sources: docs/49_completion_audit_and_fixes.md, docs/41_measurement_protocol.md


## Slide 34: Proposed next experiments




Priority | Experiment | Decision it enables
1 | Repeated blank / reference acquisitions at selected tones | Can the required differential stability be achieved?
2 | Controlled gas path with independent concentration truth | Does the predicted VOC recall survive real model error?
3 | PM cell with known mass, size and humidity | Does radio information separate mass from composition?
4 | Full receiver and reference schedule under motion | Can the sensing result survive operational timing?


Additional evidence: Calibration acceptance question = σ ≤ about 0.000146 dB at 20 s?; Frozen test target = 1 µg/m³ CH₃CN; Independent test measurements = Still required

Freeze calibration and model choices before evaluating an independent test campaign.

Additional Monte Carlo trials improve numerical precision but cannot replace missing measurements.

These are proposed next experiments. No campaign has been completed or funded by this presentation. Before hardware access, full warped-time simulation and an additional PM observable are the most useful computational follow-ups.


Sources: docs/49_completion_audit_and_fixes.md, docs/41_measurement_protocol.md


## Slide 35: What we can report to the supervisor



The original eleven modeling and simulation tasks now have implementations with traceable outputs.

Payload reuse and frequency selection improve conditional VOC detection. Acetonitrile reaches 97.67% recall at 1 µg/m³ with 20 s and assumed 0.0001 dB residual.

The analysis explains why PM remains weak and why more averaging cannot overcome persistent calibration error.

The next milestone is independent physical validation of the selected receiver and its concentration estimates.


Additional evidence: Task implementations = 11 / 11; Verified research checks = 25,172; Conditional CH₃CN recall = 97.67%; Validated field recall = Unavailable

The main achievement is a reproducible feasibility assessment and a stronger, explicitly conditional VOC design.

Useful joint PM retrieval, zero communication architecture cost and validated field performance remain unachieved.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. The current schedule loses 14.64% Gaussian rate against the best tested fixed block. Source snapshot 461a3ba retains 235 tests and 25,172 numerical checks. These verify implementation and consistency, not physical truth.


Sources: docs/49_completion_audit_and_fixes.md, docs/51_joint_design_time_calibration_results.md


## Slide 36: Appendix · Global VOC and PM outcomes

Envelopes over 270 valid operating conditions per output, with 18 additional rejected conditions


Output | Reference µg/m³ | Predicted recall range | Valid 95% limits / 270
H2CO | 1 | 0.128–89.043% | 270
CH3OH | 1 | 0.130–72.886% | 270
CH3CN | 1 | 0.282–100.000% | 270
CH3Cl | 1 | 0.139–100.000% | 270
HCOOH | 1 | 0.125–12.651% | 269
PM2.5 | 15 | 0.125–0.125% | 0
PMcoarse | 45 | 0.125–0.125% | 0
PM10 | 45 | 0.125–0.125% | 0


Additional evidence: Grid = 2 plans × 2 weather × 4 elevations; Other axes = 3 times × 3 residuals × 2 noise figures; Mass assumptions = 1 / 15 / 45 µg/m³ (see table)



Different reference concentrations and operating conditions prevent a direct same-condition species ranking.

These are conditional predictions using positive-response variance, not Monte Carlo frequencies. Ranges are operating-condition envelopes, not confidence intervals. Full 288-condition axes appear on Task 4.2 slides. Power fixed at 23 dBm and reference weather matched.


Sources: results/joint_receiver_revision/global_comparison.csv


## Slide 37: Appendix · Low PM recalls remain visible

Simulated recall, selected bands, standard atmosphere at 45°, same joint five-gas fit


Total s | Residual dB | PM2.5 at 15 µg/m³ | Coarse at 45 µg/m³ | PM10 at 45 µg/m³
2 | 0 | 0.14% | 0.14% | 0.12%
2 | 0.0001 | 0.10% | 0.10% | 0.06%
2 | 0.001 | 0.09% | 0.11% | 0.14%
20 | 0 | 0.11% | 0.15% | 0.16%
20 | 0.0001 | 0.15% | 0.07% | 0.14%
20 | 0.001 | 0.15% | 0.19% | 0.09%
100 | 0 | 0.15% | 0.12% | 0.10%
100 | 0.0001 | 0.08% | 0.13% | 0.07%
100 | 0.001 | 0.07% | 0.10% | 0.13%


Additional evidence: PM10 positive mixture = Fine 49/90, coarse 41/90; Null target threshold = 0.125% theoretical marginal rate; Monte Carlo class size = 10,000



These recalls are near the false-alarm scale. No cell establishes useful PM detection.

Selected bands, standard atmosphere, 45°, matched reference, 23 dBm and 6 dB noise figure. PM10 positive injection uses fine/coarse fractions 49/90 and 41/90. Each class has 10,000 trials. Binomial variation explains small nonmonotonic differences near the null rate. PM10 variance includes the cross covariance.


Sources: results/joint_receiver_revision/response_metrics.csv


## Slide 38: Appendix · Reproducible evidence map

Research snapshot 461a3ba, 27 September 2026


Research material | Repository location
Original task definition | I2R_proposal_THz_ISAC (1).pdf
Current results and global comparison | docs/51_joint_design_time_calibration_results.md
Species, equations and metric definitions | docs/50_species_methods_and_percentage_guide.md
Complete open-issue ledger | docs/49_completion_audit_and_fixes.md
Critical calibration record | docs/46_critical_calibration_assumption.md
Data, trials, hashes and validation | results/joint_receiver_revision/
Current manuscript | output/pdf/thz_isac_pollutant_sensing_ieee.pdf


Additional evidence: Retained metric rows = 480; Global rows = 2,304; Passing research tests = 235





Repository: https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring . The snapshot contains 235 passing tests and 25,172 numerical checks. These counts describe the computational research snapshot, not slide validation or independent physical evidence.


Sources: docs/49_completion_audit_and_fixes.md, docs/51_joint_design_time_calibration_results.md


## Slide 39: Appendix · Physical and methodological sources



HITRAN2024 and HAPI: line data, isotope handling and spectroscopic calculations.

ITU-R P.835 and P.676: reference atmosphere, oxygen/water absorption and atmospheric background.

NOAA IGRA: independent measured weather soundings.

Aliaga et al. (2024) and Yang et al. (2024): satellite differential absorption and gas/particle propagation context.

Xu, Fu and Kim (2025): using pilots and payloads for sensing. Established M2M4 literature supplies the signal/noise estimator.


Additional evidence: Original tasks = 11; Current source snapshot = 461a3ba; Additional organic catalog gaps = 4; Paired field validation = Open



Published models motivate and parameterize the study. They do not validate this receiver’s field performance.

Sources:
HITRAN2024: https://hitran.org/media/refs/HITRAN-2024.pdf
HAPI: https://doi.org/10.1016/j.jqsrt.2016.03.005
ITU-R P.835-7: https://www.itu.int/rec/R-REC-P.835
ITU-R P.676-13: https://www.itu.int/rec/R-REC-P.676
NOAA IGRA: https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive
Aliaga et al.: https://doi.org/10.1109/JSTARS.2024.3480816
Yang et al.: https://doi.org/10.1109/OJCOMS.2024.3386759
Xu et al.: https://arxiv.org/abs/2506.15998
M2M4: Gianmarco Romano, 2021, doi:10.3390/s21154950. See full references in current manuscript.


Sources: paper/current_study.tex