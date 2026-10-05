# From a gas column to a receiver decision

5 October 2026. The revised presentation assumes a general telecommunications background. It explains the project's molecular sensing calculation, without lessons on dB, OFDM or other standard radio concepts.

## What changed and why

The earlier table placed four numbers together without showing enough of their origin. The new presentation derives each one, then follows the actual simulated observation through the estimator and decision. It contains 25 main slides and seven appendix slides:

- [PowerPoint](../output/presentations/zenith_acetonitrile_worked_example_v2.pptx)
- [PDF with slide bookmarks](../output/presentations/zenith_acetonitrile_worked_example.pdf)
- [Complete text, tables, equations, presenter notes and source links](../output/presentations/zenith_acetonitrile_worked_notes.md)
- [LaTeX equation source](../output/presentations/zenith_acetonitrile_worked_equations.tex)
- [Replayed numerical values](../results/zenith_worked_steps/worked_steps.json)
- [Input and output hashes](../results/zenith_worked_steps/manifest.json)

This uses actual acquired HITRAN line parameters and published atmosphere models. The enhancement profile and hardware are specified model inputs. The receiver observation is simulated. It is a real, reproducible numerical calculation using physical data, not a measured atmospheric detection.

LEO links are a useful running example for the complete sensing chain, including geometry, propagation, antennas, acquisition and inference. The example does not establish that every proposed LEO sensing mode is feasible.

## Physical meaning before the arithmetic

The gas has molecular transitions with frequency dependent absorption. At each altitude, the number of molecules and their absorption cross section determine a small loss. The calculation integrates that loss through the atmosphere at each radio tone. More gas increases the depth of the absorption pattern.

The receiver compares a reference acquisition with a sample acquisition. Their channel magnitude ratio contains the additional absorption, receiver noise and residual calibration error. A change in receiver gain can imitate part of the gas pattern, so the estimator jointly fits concentration, gain offset and gain slope. The component of the spectral pattern that survives those nuisance terms supplies evidence for the gas enhancement.

This is absorption along one ray. It does not localize individual molecules or recover an arbitrary vertical profile. Fixing a profile shape reduces the unknown concentration function to one parameter.

## The four values, derived

### 1. Specify what q means

The assumed enhancement relative to the reference is

$$
\Delta c(z)=q\exp[-z/(1500\ \mathrm m)].
$$

The selected input is q = 50.5813965969 µg/m³, an equivalent surface enhancement. Its vertical mass column is (1500 m)q = 75,872.0949 µg/m² = 75.8720949 mg/m². The sample enhancement at 1500 m is 18.6078559 µg/m³. The choice of q comes from the model's conditional 95% response concentration, derived below; it is not an environmental observation.

### 2. Convert mass into molecular density

Using a natural mixture molar mass of 41.053 g/mol, one µg/m³ corresponds to

$$
n_1(0)=\frac{10^{-6}}{41.053}(6.02214076\times10^{23})
      =1.46691855894\times10^{16}\ \mathrm{m^{-3}}.
$$

At each altitude, multiply this by exp(−z/1500) and by the numerical q in µg/m³. The chosen surface density is 7.41987894048 × 10¹⁷ molecules/m³. Density and path length are converted to cm⁻³ and cm to match the catalog's cm²/molecule cross sections.

### 3. Evaluate the actual spectroscopy at an integration node

At the first tone, f₀ = 230.0048828125 GHz, the first quadrature node is at z = 16.882621449 m. Its standard atmospheric state is T = 288.040263252 K and p = 101122.351535 Pa.

One retained CH₃CN transition is centered at 239.137916665 GHz, with S(296 K) = 2.616 × 10⁻²¹ cm/molecule, air width 0.1594 cm⁻¹/atm and lower state energy 47.8643 cm⁻¹. After temperature correction, S(T) = 2.84575900683 × 10⁻²¹ cm/molecule. Evaluating its Voigt profile at the measured tone gives V = 0.433421406467 cm. Thus this line contributes

$$
\sigma_{\ell,0}=S(T)V
=1.23341287121\times10^{-21}\ \mathrm{cm^2/molecule}.
$$

The line need not be centered on the radio tone: pressure and Doppler broadening distribute its strength over frequency. Summing all 17,880 retained transitions gives σ₀ = 2.64224620281 × 10⁻²⁰ cm²/molecule at this altitude. Temperature, pressure and the line catalog determine this value; it is not an adjustable receiver coefficient. The [HITRAN definitions](https://hitran.org/docs/definitions-and-units/) specify the parameters and units; [HAPI](https://hitran.org/hapi/) supplies the TIPS2025 partition functions used here.

### 4. Integrate the atmospheric column

For q = 1 µg/m³, this node has n₁ = 1.45050083649 × 10¹⁰ molecules/cm³ and quadrature weight w = 4283.11230948 cm. Its optical depth contribution is

$$
\delta\tau_{0,1}=\sigma_0 n_1w
=1.64153719774\times10^{-6}.
$$

The weight is a numerical integration weight, not the thickness of a measured uniform gas slab. Summing the 114 nodes from 0 to 100 km gives τ₀,₁ = 5.54508446549 × 10⁻⁵. The first tone sensitivity is

$$
a_0=\frac{10}{\ln10}\tau_{0,1}
=0.000240819958505\ \frac{\mathrm{dB}}{\mathrm{\mu g/m^3}}.
$$

The [complete node table](../results/zenith_worked_steps/quadrature_first_tone.csv) and [altitude sums](../results/zenith_worked_steps/altitude_contributions.csv) expose every term. The standard atmospheric state follows [ITU P.835-7](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en). Oxygen/water background propagation and emission follow [ITU P.676-13](https://www.itu.int/rec/R-REC-P.676-13-202208-I).

### 5. Obtain the other three numbers

Multiplying by the selected concentration:

$$
\Delta A_0=a_0q
=(0.000240819958505)(50.5813965969)
=0.0121810098296\ \mathrm{dB}.
$$

The corresponding noiseless channel magnitude ratio and reduction are

$$
\frac{|h_{1,0}|}{|h_{0,0}|}=10^{-\Delta A_0/20}
=0.998598592308,
\qquad
100\left(1-\frac{|h_{1,0}|}{|h_{0,0}|}\right)=0.140140769241\%.
$$

These are predictions from the specified gas column. The 4.5477 dB oxygen/water attenuation belongs to the baseline link budget; 0.012181 dB is the additional modeled CH₃CN loss.

## From predicted loss to a simulated observation

The setup uses 550 km altitude at zenith, 230–240 GHz, 1024 tones, 25 dBm total average RF power, 0.10 m transmit and 1.0 m receive apertures, aperture efficiency 0.65, 7 dB noise figure and 5 dB implementation loss. Published hardware sources retain their scope in the [supervisor response](54_supervisor_revision_2026_10_05.md): these values do not establish a flight qualified combined system.

There are 10 s reference and 10 s sample acquisitions. With 112.4 ns transmitted symbol duration and 30 full pilot symbols in each 10,000 symbol frame, M = floor[10/(10000 × 112.4 ns)] × 30 = 266880 pilots per tone in each acquisition.

At tone 0, reference SNR is 0.961035658354 in linear units. Normalizing the true reference channel to one gives complex mean noise variance 1/(Mρ₀) = 3.89892129965 × 10⁻⁶. With seed 20261005, the saved complex draws are

$$
\widehat h_{0,0}=1.000916240334+j0.000440025145,
\qquad
\widehat h_{1,0}=1.000732694637-j0.000941258069.
$$

Their magnitude log ratio is +0.001589941624 dB. Adding the simulated differential calibration draw −0.002053756571 dB gives y₀ = −0.000463814947 dB. Thus even a positive true enhancement can give a negative observed value at one tone. The [receiver replay table](../results/zenith_worked_steps/complex_receiver_steps.csv) retains both complex means and the resulting observation for all 1024 tones.

The persistent differential calibration standard deviation is **assumed to be 0.001 dB and is unmeasured**. Its covariance is 10⁻⁶ exp(−|fᵢ−fⱼ|/10 GHz) dB². It does not decrease with the number of pilots. Thermal covariance includes noise in both acquisitions.

## The numerical inverse and decision

The model is y = Aθ + ε, where A = [a, 1, u] has dimensions 1024 × 3 and θ = [q, b₀, b₁]ᵀ. The normalized frequency coordinate u ranges from −0.5 to +0.5. The estimator fixes its weights using the covariance C(0), producing G = AᵀC(0)⁻¹A and g = AᵀC(0)⁻¹y:

$$
G\simeq
\begin{bmatrix}
0.301344020469 &458.463513671&127.082722926\\
458.463513671&983654.579709&-223.779286587\\
127.082722926&-223.779286587&198502.414349
\end{bmatrix},
\quad
g\simeq
\begin{bmatrix}
15.0662651908\\22141.4010312\\7023.36095531
\end{bmatrix}.
$$

Each column corresponds to its parameter's units: q in µg/m³, b₀ and b₁ in dB. The [normal equation arrays](../results/zenith_worked_steps/normal_equations.npz) retain full precision.

Eliminating the two gain terms gives effective information Iq = 0.301344020469 − 0.295174434664 = 0.00616958580540 and score tq = 15.0662651908 − 14.8230312721 = 0.243233918673. Therefore q̂ = tq/Iq = 39.4246755529 µg/m³, with fitted offset 0.004136509296 dB and slope coefficient 0.010146433268 dB.

**Under the stated hardware, matched background, ideal tracking, 20 s total acquisition and assumed, unmeasured 0.001 dB residual**, the null standard deviation is s₀ = 1/√Iq = 12.7312778289 µg/m³. A one sided 1% false alarm threshold for this prespecified compound is 2.326347874 × s₀ = 29.6173811110 µg/m³. This simulated draw exceeds the threshold. It does not establish field performance or unique identification in a changing mixture.

The earlier q was selected by solving q − threshold = 1.644853627 s₁(q), where s₁ uses sample attenuation in its covariance. At the solution s₁ = 12.7452164389 µg/m³, giving q = 50.5813965969 µg/m³. Under the same unmeasured calibration assumption, this is the **predicted 95% response concentration**. The saved 10,000 simulated pairs yield **94.75%**, whereas q = 1 µg/m³ yields only **1.31%**, near the false alarm rate. A single successful simulated draw is not a sensitivity validation.

## Verification and reproduction

The replay checks the first tone integrated sensitivity against the saved spectrum, every observed tone against the saved random draw, and the Schur complement estimate and uncertainty against the original experiment. All checks pass. The presentation package passes structural, geometry, native chart workbook and native table checks; every rendered slide was visually reviewed.

From the repository root:

```powershell
py -3.12 scripts/calculate_zenith_worked_steps.py
$env:DECK_PROFILE = 'worked'
py -3.12 scripts/prepare_zenith_worked_presentation.py
py -3.12 scripts/render_zenith_equations.py
# Set a new output filename for each regenerated revision.
$env:DECK_NAME = 'zenith_acetonitrile_worked_example_v3.pptx'
node scripts/build_zenith_presentation.mjs
py -3.12 scripts/package_zenith_pdf.py
```

Use the bundled Node runtime and artifact-tool dependencies described in the [earlier build note](56_zenith_example_presentation.md). The replay requires the original locally acquired HITRAN file at data/raw/payload_bounds/lines.csv and the saved zenith experiment. Its manifest records these inputs, relevant source modules and output hashes. The existing Python environment supplies HAPI, NumPy, Pandas, SciPy and PyMuPDF; equations use the existing pdflatex installation.

PowerPoint text, tables and its spectrum chart remain editable. The chart includes a workbook containing the plotted values. Equations use vector assets with separate LaTeX source. The PDF contains rendered pages; the companion Markdown contains searchable text and tables.

## Remaining work, limitations and next steps

No new measurement is introduced. Catalog accuracy, line wings, atmospheric mismatch, the assumed concentration profile, instrument covariance and the tracking approximation limit physical conclusions. A static 90° path cannot persist throughout a real 20 s pass without corrections. The 0.001 dB differential residual has not been established experimentally.

The next experiment should measure paired blank stability and its spectral covariance with the intended instrument, then test independently measured concentrations. Profile recovery, changing mixtures and multiple ground receiver tomography require new identifiable models and evidence. The presentation makes the current calculation auditable; it does not resolve those scientific requirements.
