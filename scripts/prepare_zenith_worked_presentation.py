"""Explain the saved physical calculation for an audience with telecom knowledge."""
from pathlib import Path
import csv
import json
import math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/zenith_single_compound'
STEPS=ROOT/'results/zenith_worked_steps'
BUILD=ROOT/'tmp/zenith_worked_deck'
OUT=ROOT/'output/presentations'
BUILD.mkdir(parents=True,exist_ok=True)
def csv_rows(path):
    with path.open(encoding='utf-8') as handle:return list(csv.DictReader(handle))
v=json.loads((STEPS/'worked_steps.json').read_text())
baseline=json.loads((DATA/'baseline.json').read_text())
worked=json.loads((DATA/'worked_example.json').read_text())
tones=csv_rows(DATA/'tone_by_tone.csv')
observations=csv_rows(DATA/'worked_observation.csv')
altitude=csv_rows(STEPS/'altitude_contributions.csv')
controls=csv_rows(DATA/'receiver_control.csv')
node=v['first_quadrature_node']; line=v['largest_line']; mini=worked['miniature']
REPO='https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/'
S=dict(tutorial=REPO+'b94f3fe/docs/55_zenith_single_compound_walkthrough.md',
       revision=REPO+'b94f3fe/docs/54_supervisor_revision_2026_10_05.md',
       steps=REPO+'main/results/zenith_worked_steps/worked_steps.json',
       hitran='https://hitran.org/docs/definitions-and-units/',hapi='https://hitran.org/hapi/',
       p835='https://www.itu.int/rec/R-REC-P.835-7-202408-I/en',
       p676='https://www.itu.int/rec/R-REC-P.676-13-202208-I',
       teralink='https://arxiv.org/html/2606.15410v1',
       sen='https://www.nature.com/articles/s41928-022-00897-6',
       cooper='https://doi.org/10.1109/JMW.2025.3610360',
       ambient='https://acp.copernicus.org/articles/23/1893/2023/index.html')
CONDITION='20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual'
slides=[]
def add(title,*,body=None,table=None,widths=None,latex=None,legend=None,chart=None,
        takeaway=None,caveat=None,notes='',refs=None,source='Saved CH₃CN example · numerical steps and sources in notes',kind='standard'):
    slides.append(dict(title=title,body=body or [],table=table,widths=widths,latex=latex,
                       legend=legend,chart=chart,takeaway=takeaway,caveat=caveat,notes=notes,
                       sources=refs or [S['tutorial'],S['steps']],source=source,kind=kind))

add('How a gas concentration\nbecomes a receiver decision',kind='cover',
    body=['Acetonitrile at 90°: one complete numerical calculation', 'Actual HITRAN parameters, explicit arithmetic and a simulated receiver'],
    notes='Assume a general telecommunications background. The question is how the project turns a concentration profile into a frequency dependent channel change, then estimates that concentration from noisy measurements. This is the same saved example as the earlier table, now with every physical and statistical step exposed. The spectroscopy records are real database inputs. The concentration profile, hardware and errors are model inputs; the receiver observations are simulated.')

add('What the four numbers in the original table mean',table=[['Number', 'Its role in the calculation'],
    ['50.5814 µg/m³', 'Chosen true enhancement q for this simulated experiment'],
    ['0.012181 dB', 'Predicted extra attenuation of the first tone'],
    ['0.998599', 'Predicted sample/reference amplitude ratio for that tone'],
    ['0.1401%', 'The same amplitude change expressed as a reduction']],widths=[.29,.71],
    takeaway='The last three values follow from q and the molecular absorption model. None is a receiver estimate.',
    caveat='q was chosen from the model’s 95% detection limit, before generating the observation. It is not a measured concentration.',
    notes='q is a controlled input; the other three quantities are deterministic predictions from that input. First derive 0.012181 dB from the actual spectroscopy and an assumed profile. Then derive the amplitude ratio. Finally add the modeled observation errors and calculate an estimate, which is 39.4247 µg/m³ for the saved draw. The reason for selecting 50.5814 is explained after deriving the detector.')

add('q describes an enhancement with a fixed vertical shape',table=[['Altitude z', 'Sample minus reference concentration'],
    *[[f'{z:g} m',f'{q:.4f} µg/m³'] for z,q in zip(v['profile_z_m'],v['profile_q_ug_m3'])]],widths=[.38,.62],
    latex=r'\Delta c(z)=c_{\mathrm{sample}}(z)-c_{\mathrm{reference}}(z)=q\,e^{-z/(1500\ \mathrm m)}',
    legend='q is the unknown surface equivalent increase (µg/m³). The profile shape is assumed, not independently recovered.',
    takeaway=f"Vertical mass column: (1500 m)q = {1000*v['vertical_mass_column_mg_m2']:,.1f} µg/m² = {v['vertical_mass_column_mg_m2']:.4f} mg/m².",
    caveat='The reference is a baseline acquisition, not necessarily gas free air. Other species are assumed unchanged.',
    notes='The receiver senses an integrated path effect. It cannot independently estimate the concentration at every altitude from this one ray. Specifying an exponential shape reduces the unknown function to one scalar q. In the differential model q = 0 means no enhancement relative to the reference, not necessarily zero absolute CH3CN. The saved link budget treats baseline CH3CN attenuation as negligible. If the actual vertical shape is different, q remains a model dependent equivalent amplitude.')

add('The fixed experiment used in all calculations',table=[['Parameter', 'Value'],
    ['Geometry', '550 km LEO satellite, 90° ground elevation'],
    ['Spectrum', '230–240 GHz, 1,024 tones; first tone 230.004883 GHz'],
    ['Total RF power and apertures', '25 dBm; 0.10 m transmit / 1.0 m receive; η = 0.65'],
    ['Noise and additional loss', '7 dB receiver noise figure; 5 dB implementation loss'],
    ['Atmosphere and gas profile', 'ITU P.835 / P.676; CH₃CN scale height 1,500 m'],
    ['Acquisition', '10 s reference + 10 s sample; 0.3% full pilot symbols']],widths=[.32,.68],
    caveat='The static benchmark assumes ideal tracking. No source demonstrates this entire orbital configuration.',
    notes='LEO links are a useful example throughout the complete sensing chain. The same inference framework can use terrestrial or UAV geometry. The 25 dBm and 7 dB values have a published LEO design precedent in TeraLink, rather than flight validation. Aperture efficiency, implementation loss, vertical profile and calibration covariance are assumptions. Zenith is the shortest geometric path at a fixed orbit height; it cannot persist for a finite acquisition without time dependent tracking corrections.',refs=[S['tutorial'],S['revision'],S['teralink'],S['p835'],S['p676']])

add('Step 1 · Mass concentration becomes molecular density',
    latex=r'\begin{gathered}n_1(0)=\frac{10^{-6}\ \mathrm{g/m^3}}{41.053\ \mathrm{g/mol}}\,(6.02214076\times10^{23})=1.46691856\times10^{16}\ \mathrm{m^{-3}}\\n(z;q)=q\,n_1(0)e^{-z/1500}\end{gathered}',
    legend='n₁: density for a numerical concentration of 1 µg/m³ · n(z;q): molecular density for the chosen q\n41.053 g/mol: natural mixture molar mass · q is inserted numerically in µg/m³',
    body=[f"At q = {v['true_q_ug_m3']:.4f}, the surface molecular density is {v['surface_density_at_q_m3']:.6e} molecules/m³.",
          'HITRAN uses cm² per molecule, so the calculation converts density to cm⁻³ and path length to cm.'],
    takeaway='This converts an environmental concentration into the number of absorbers seen by the wave.',
    notes='The code uses concentration_ug_m3_to_number_density_cm3, giving 1.466918558936 × 10^10 molecules/cm³ per 1 µg/m³. Multiplying by q and exp(−z/1500) gives the molecular density at every integration node. This is dimensional conversion, not a fitted parameter. Natural molar mass is used for mass concentration; isotopologue mass is used for Doppler broadening. HITRAN intensity already contains natural isotope abundance, so the abundance is not applied a second time.',refs=[S['steps'],S['hitran'],REPO+'b94f3fe/src/thz_isac/concentration_units.py'])

add('Step 2 · One actual HITRAN transition',table=[['Catalog parameter', 'Saved value', 'Physical role'],
    ['Line center', '239.1379167 GHz', 'Transition frequency'],
    ['S(296 K)', '2.616 × 10⁻²¹ cm/molecule', 'Integrated line strength'],
    ['Air width γ_air', '0.1594 cm⁻¹/atm', 'Collision broadening'],
    ['Lower state energy E″', '47.8643 cm⁻¹', 'Temperature dependence'],
    ['Width temperature exponent', '0.71', 'Temperature scaling of width']],widths=[.29,.32,.39],
    takeaway='This is one of 17,880 retained CH₃CN transitions. The calculation sums their contributions.',
    caveat='The measured tone is at 230.004883 GHz. A transition contributes away from its center through its broadened shape.',
    notes='This is the largest individual contributor at the first tone and first altitude quadrature node, selected after evaluating all retained lines. It is not asserted to be the only relevant transition or a line centered on the tone. The molecule ID is 41 and local isotopologue ID is 1. The raw line wavenumber is 7.97678228 cm⁻¹, pressure shift is zero, and the actual record is exported with the derived contribution. Catalog range and line shape assumptions remain physical uncertainties.',refs=[S['hitran'],REPO+'main/results/zenith_worked_steps/largest_line_contributions.csv'],source='Actual acquired HITRAN record · largest_line_contributions.csv')

add('Step 2 · A line shape gives absorption at our tone',table=[['At z = 16.8826 m', 'Value'],
    ['Atmospheric state', 'T = 288.0403 K; p = 101,122.35 Pa'],
    ['Temperature corrected strength S(T)', '2.845759 × 10⁻²¹ cm/molecule'],
    ['Voigt value V at 230.004883 GHz', '0.4334214 cm'],
    ['Sum over all retained lines: σ₀(z)', '2.642246 × 10⁻²⁰ cm²/molecule']],widths=[.53,.47],
    latex=r'\sigma_{\ell,0}=S_\ell(T)V_\ell(f_0;T,p)=(2.845759\times10^{-21})(0.4334214)=1.233413\times10^{-21}\ \mathrm{cm^2}',
    legend='σ_ℓ,₀: one transition’s absorption cross section at tone 0 · σ₀ = Σℓ σ_ℓ,₀\nV is normalized over wavenumber. The temperature correction is worked out in the appendix.',
    caveat='σ is calculated from line parameters and atmospheric state. It is not a measured satellite attenuation.',
    notes='The Voigt function is the convolution of Doppler and collision broadening. Here the Lorentz half width is 0.1621900503 cm⁻¹ and the Doppler standard deviation is 6.42862709 × 10^−6 cm⁻¹. Their values are used at the actual tone wavenumber. Multiplying the temperature corrected line strength by this function gives one cross section. The other transitions supply the remaining sum. The layer has no single universal cross section: pressure and temperature change it with altitude.',refs=[S['hitran'],S['hapi'],S['p835'],S['steps']])

add('Step 3 · One altitude node contributes optical depth',table=[['First quadrature node', 'Numerical value'],
    ['Cross section σ₀', '2.6422462 × 10⁻²⁰ cm²/molecule'],
    ['Density n₁(z) for q = 1 µg/m³', '1.4505008 × 10¹⁰ molecules/cm³'],
    ['Integration weight w', '42.831123 m = 4,283.1123 cm']],widths=[.53,.47],
    latex=r'\delta\tau_{0,1}=\sigma_0n_1w=(2.6422462\times10^{-20})(1.4505008\times10^{10})(4283.1123)=1.6415372\times10^{-6}',
    legend='δτ₀,₁: dimensionless optical depth contribution at tone 0 for 1 µg/m³\nThe weight is a Gauss quadrature weight, not the thickness of a physical uniform slab.',
    takeaway='Repeat this product at each altitude node and add the contributions.',
    notes='At zenith, the geometric path element equals the vertical element. The model uses order six Gauss quadrature over altitude intervals and inserts atmospheric layer boundaries, giving 114 nodes. The first node is at 16.882621449 m. Its number density is n1(0) exp(−16.882621449/1500). Its contribution in dB per unit q is 4.342944819 × 1.641537197735 × 10^−6 = 7.129105468153 × 10^−6. Numerical integration weights must not be interpreted as a measurement of the local gas profile.',refs=[S['steps'],REPO+'main/results/zenith_worked_steps/quadrature_first_tone.csv'])

add('Step 3 · Adding the atmosphere gives the tone sensitivity',table=[['Altitude interval', 'Optical depth for q = 1 µg/m³', 'Attenuation sensitivity (dB per µg/m³)'],
    *[[f"{float(r['lower_m'])/1000:g}–{float(r['upper_m'])/1000:g} km",f"{float(r['optical_depth_per_unit_q']):.7e}",f"{float(r['attenuation_db_per_unit_q']):.7e}"] for r in altitude]],widths=[.21,.38,.41],
    takeaway='Sum: τ₀,₁ = 5.5450845 × 10⁻⁵ → a₀ = (10 / ln 10) τ₀,₁ = 0.00024081996 dB/(µg/m³)',
    caveat='The vertical profile and atmospheric state determine this coefficient. It is not a universal CH₃CN constant.',
    notes='Each displayed row sums the exact quadrature contributions in that altitude interval, not a midpoint approximation. The 0–100 km total is 5.545084465494345 × 10^−5 optical depth per unit q. Multiplication by 10/ln10 gives 2.40819958505 × 10^−4 dB/(µg/m³), matching the earlier saved tone table to floating point precision. The full list of 114 nodes retains the temperature, pressure, cross section, molecular density and weight.',refs=[S['steps'],REPO+'main/results/zenith_worked_steps/altitude_contributions.csv'])

add('Step 4 · The chosen concentration gives 0.012181 dB',
    latex=r'\begin{gathered}\Delta A_0=a_0q=(0.0002408199585)(50.5813966)=0.01218100983\ \mathrm{dB}\\\tau_0(q)=q\tau_{0,1}=(50.5813966)(5.545084465\times10^{-5})=0.002804781165\end{gathered}',
    legend='ΔA₀: extra CH₃CN attenuation at the first tone · τ₀: corresponding dimensionless optical depth',
    body=['The 4.5477 dB oxygen/water loss belongs to the baseline link budget.',
          'The 0.012181 dB value is the additional loss caused by this CH₃CN enhancement.'],
    takeaway='The concentration multiplies a sensitivity computed from real spectral parameters and an assumed path profile.',
    notes='This is the missing multiplication behind the second row in the screenshot. Line strengths and cross sections determine a0, while q sets the magnitude of the extra gas column. This linearity is in optical depth and dB attenuation under the fixed trace gas line shape. The complex channel amplitude itself changes exponentially. Background cancellation assumes the reference and sample atmosphere are matched after correction.')

add('Step 5 · Absorption predicts the amplitude change',
    latex=r'\begin{gathered}\frac{|h_{1,0}|}{|h_{0,0}|}=e^{-\tau_0/2}=10^{-\Delta A_0/20}=10^{-0.01218100983/20}=0.9985985923\\100\left(1-\frac{|h_{1,0}|}{|h_{0,0}|}\right)=0.1401407692\%\end{gathered}',
    legend='h₀,₀: reference channel at tone 0 · h₁,₀: sample channel at tone 0, before measurement error',
    body=['The ratio concerns channel magnitude after known geometric and instrument corrections.',
          'The power ratio is 0.99719915. The stated 0.1401% is an amplitude reduction.'],
    takeaway='These are the third and fourth rows of the screenshot, now derived from the gas column.',
    caveat='A predicted change of 0.1401% is not yet evidence that a receiver can resolve it.',
    notes='Beer attenuation gives a power factor exp(−τ), hence an amplitude factor exp(−τ/2). The result is deterministic for the chosen concentration and physical model. It contains no receiver noise yet. The total received sample power at this tone becomes −97.61177776 dBm compared with the reference −97.59959675 dBm. The baseline channel magnitude is normalized to one for the next receiver calculation.',refs=[S['steps'],S['tutorial'],S['hitran']])

add('Step 6 · Observation time fixes the averaging gain',table=[['Resource', 'Calculation'],
    ['Tone spacing and useful symbol', '10 GHz / 1,024 = 9.765625 MHz; Tᵤ = 102.4 ns'],
    ['Transmitted symbol', '102.4 ns + 10 ns assumed CP = 112.4 ns'],
    ['Frame', '10,000 symbols, with 30 full pilot symbols'],
    ['Frames in each 10 s acquisition', 'floor[10 / (10,000 × 112.4 ns)] = 8,896'],
    ['Pilots per tone in each acquisition', 'M = 8,896 × 30 = 266,880']],widths=[.39,.61],
    takeaway='Both the reference and sample are noisy: 10 s + 10 s, not a free or exact reference.',
    caveat='Ideal phase, frequency, delay and gain tracking is assumed throughout each moving acquisition.',
    notes='This slide specifies the actual resources without teaching OFDM. The two schedules occupy 19.998208 seconds of complete frames, leaving 0.001792 seconds unused. A full pilot symbol measures all 1024 tones simultaneously. Sensing does not use the unknown payload symbols here. The 90 degree geometry is a snapshot approximation, and waiting for comparable reference conditions is additional operational time.')

add('Step 7 · One tone remains uncertain after averaging',table=[['First tone', 'Numerical value'],
    ['Reference SNR per pilot, linear', f"ρ₀ = {v['rho0']:.9f}"],
    ['Complex mean variance, normalized channel', f"1 / (Mρ₀) = {v['normalized_complex_noise_variance']:.7e}"],
    ['Thermal variance of the reference/sample log ratio', f"v₀(0) = {v['thermal_null_variance_db2']:.7e} dB²"],
    ['Total null variance after calibration term', f"C₀₀ = {v['total_null_variance_db2']:.7e} dB²"]],widths=[.60,.40],
    latex=r'v_0(0)=\frac{(20/\ln10)^2}{2M}\left(\frac1{\rho_0}+\frac1{\rho_0}\right),\qquad\sqrt{C_{00}}=0.0171800\ \mathrm{dB}',
    legend='C₀₀ = v₀(0) + (0.001 dB)² · The log ratio variance uses a high coherent mean SNR approximation.',
    caveat=CONDITION,
    notes='The expected signal at this tone is 0.012181 dB, while the null standard deviation after both acquisitions is 0.017180 dB. Even with perfectly known gain this is not a reliable single tone detection. With an unknown gain offset, a single tone cannot distinguish attenuation from a gain change at all. The normalized real and imaginary noise components each have standard deviation 0.001396230873. Multiple frequencies are essential for both uncertainty reduction and separation from nuisance gain changes.')

add('Step 8 · The saved receiver draw does not equal its mean',table=[['Normalized complex pilot means, simulated', 'Value'],
    ['Reference ĥ₀,₀', '1.0009162403 + j 0.0004400251'],
    ['Sample ĥ₁,₀', '1.0007326946 − j 0.0009412581'],
    ['Magnitudes |ĥ₀,₀| and |ĥ₁,₀|', '1.0009163371 and 1.0007331373'],
    ['Persistent differential calibration draw e₀', '−0.0020537566 dB']],widths=[.53,.47],
    latex=r'y_0=-20\log_{10}\!\left(\frac{1.0007331373}{1.0009163371}\right)-0.0020537566=0.0015899416-0.0020537566=-0.0004638149\ \mathrm{dB}',
    legend='The mean sample amplitude is 0.9985985923, but the noisy pilot mean can be larger. Seed: 20261005.',
    takeaway='A positive gas enhancement can produce a negative observed attenuation at one noisy tone.',
    caveat='These are simulated complex observations with the stated noise and calibration model, not field measurements.',
    notes='Exactly replay the original random generator draw: z_r,k = (u+jv)/sqrt(2Mρ0,k), h0 = 1+z0 and h1 = 10^(−a q/20)+z1. The model then adds one correlated differential dB calibration draw per pair. Each displayed magnitude is calculated from both complex components. The final y0 equals the stored observation to numerical precision. This addresses the difference between the deterministic table and what a receiver could actually return.',refs=[S['steps'],REPO+'main/results/zenith_worked_steps/complex_receiver_steps.csv'])

add('Step 9 · The detector uses the complete observed spectrum',chart=dict(
    x=[float(r['frequency_ghz']) for r in observations],
    series=[dict(name='Simulated observation y',values=[float(r['observed_enhancement_db']) for r in observations],color='#B4BFC8'),
            dict(name='True extra absorption a q',values=[float(r['true_enhancement_db']) for r in observations],color='#126B76')],
    xtitle='Frequency (GHz)',ytitle='Differential attenuation (dB)',ymin=-.06,ymax=.1),
    takeaway='Input to estimation: y has 1,024 entries. The first is −0.0004638 dB, not the predicted +0.012181 dB.',
    caveat=CONDITION,
    notes='All 1024 plotted observations are retained from the original saved simulation. The true template is shown for explanation, but the estimator does not receive q. It receives y, the template a calculated for one unit of concentration, a covariance model, and nuisance directions. Frequencies share a persistent correlated calibration error, so simply treating every sample as independent would overstate the information.')

add('Step 10 · The design matrix encodes gas and gain changes',table=[['Tone index k', 'aₖ [10⁻⁴ dB/(µg/m³)]', 'Offset column', 'Slope uₖ'],
    *[[str(k),f'{row[0]*1e4:.6f}','1',f'{row[2]:.6f}'] for k,row in zip(mini['tone_indices_zero_based'],mini['A'])]],widths=[.18,.38,.21,.23],
    latex=r'\mathbf y=\mathbf A\boldsymbol\theta+\boldsymbol\varepsilon,\quad\mathbf A=[\mathbf a\ \mathbf1\ \mathbf u]\in\mathbb R^{1024\times3},\quad\boldsymbol\theta=[q\ b_0\ b_1]^T',
    legend='Five displayed rows are selected from all 1,024. uₖ = (fₖ − mean(f)) / (max(f) − min(f)).\nb₀: common gain change (dB) · b₁: spectral gain slope coefficient (dB) · ε: remaining observation error (dB)',
    takeaway='A contains known model responses. The unknowns are q and the two gain coefficients.',
    notes='The molecular column is generated by the same physical integration at every tone. The other columns permit a constant and linear spectral gain error. They stop these simple instrument changes from automatically being called gas. All three columns must be fitted jointly. The table scales only a by 10^4 for readability; calculations use unscaled a. Allowing more nuisance directions can reduce sensitivity further.')

add('Step 11 · The covariance encodes which errors average down',
    latex=r'\begin{gathered}\mathbf C(q)=\operatorname{diag}(v_k(q))+10^{-6}\mathbf R,\qquad R_{ij}=e^{-|f_i-f_j|/(10\ \mathrm{GHz})}\\v_k(q)=\frac{(20/\ln10)^2}{2M}\left[\rho_{0,k}^{-1}+\rho_{1,k}(q)^{-1}\right],\quad\rho_{1,k}(q)=\rho_{0,k}10^{-a_kq/10}\end{gathered}',
    legend='C is 1,024 × 1,024 in dB². Its thermal term includes reference and sample noise.\n10⁻⁶ dB² is the assumed differential calibration variance; it is not divided by M.',
    body=['For example: C₀₀ = 2.95152865 × 10⁻⁴ dB², while C₀,₁₀₂₃ = 3.68238874 × 10⁻⁷ dB².',
          'The estimator fixes its weights using C(0). Detection probability at q > 0 uses the corresponding C(q).'],
    caveat='The calibration covariance is an explicit unmeasured assumption, not an estimate obtained from these data.',
    notes='The residual describes the reference/sample difference, so it is added once, not once for each acquisition. The null covariance assumes the two per pilot SNR values are equal. Under a positive enhancement the sample is weaker, slightly increasing its variance. The actual log amplitude observations are not exactly Gaussian; the high coherent mean SNR supports the delta approximation and the saved Monte Carlo control checks it within the model.')

add('Step 12 · Weighted regression estimates the unknowns',
    latex=r'\widehat{\boldsymbol\theta}=\arg\min_{\boldsymbol\theta}(\mathbf y-\mathbf A\boldsymbol\theta)^T\mathbf C(0)^{-1}(\mathbf y-\mathbf A\boldsymbol\theta),\qquad\mathbf G\widehat{\boldsymbol\theta}=\mathbf g',
    legend='G = Aᵀ C(0)⁻¹ A, a 3 × 3 matrix · g = Aᵀ C(0)⁻¹ y, a 3 × 1 vector\nθ̂ = [q̂, b̂₀, b̂₁]ᵀ · C(0)⁻¹ accounts for unequal noise and cross frequency correlation',
    body=['The fit seeks the concentration whose spectral shape best explains y after allowing gain offset and slope.',
          'The next slide gives every entry of the resulting three dimensional system.'],
    takeaway='The receiver does not divide each observed tone by aₖ and average the answers.',
    notes='This is generalized least squares under the stated covariance. The saved production estimator uses Cholesky solves and SVD projection, avoiding explicit inverses. The worked replay computes G and g using Cholesky solves and solves the small system. Its q agrees with the original estimator H y. The normal equations are shown because they expose every coefficient in a compact numerical example, not because explicit matrix inversion is recommended.')

G=v['G']; g=v['g']
add('Step 12 · The full spectrum reduces to this numerical system',table=[['Equation row', 'Coefficient of q', 'Coefficient of b₀', 'Coefficient of b₁', 'Right side g'],
    *[[str(i+1),f'{G[i][0]:.9f}',f'{G[i][1]:.6f}',f'{G[i][2]:.6f}',f'{g[i]:.9f}'] for i in range(3)]],widths=[.14,.21,.22,.22,.21],
    latex=r'\begin{bmatrix}G_{qq}&\mathbf G_{qb}\\\mathbf G_{bq}&\mathbf G_{bb}\end{bmatrix}\begin{bmatrix}\widehat q\\\widehat{\mathbf b}\end{bmatrix}=\begin{bmatrix}g_q\\\mathbf g_b\end{bmatrix}',
    legend='The matrix columns correspond to different parameter units: q in µg/m³, b₀ and b₁ in dB.\nAll values use all 1,024 tones. Displayed coefficients are rounded; source arrays retain full precision.',
    takeaway='The small q coefficient alone is not the usable information: much of the gas pattern resembles gain changes.',
    notes='Use the displayed system to reproduce the estimate, allowing for rounded coefficients. The full precision G, g and theta are saved in normal_equations.npz and worked_steps.json. The effective information is Gqq − Gqb Gbb^−1 Gbq, which is much smaller than Gqq. A and C are both necessary to construct this system; y appears only in g.',refs=[S['steps'],REPO+'main/results/zenith_worked_steps/normal_equations.npz'])

add('Step 13 · Eliminating gain terms gives the concentration',
    latex=r'\begin{gathered}I_q=G_{qq}-\mathbf G_{qb}\mathbf G_{bb}^{-1}\mathbf G_{bq}=0.3013440205-0.2951744347=0.006169585805\\t_q=g_q-\mathbf G_{qb}\mathbf G_{bb}^{-1}\mathbf g_b=15.0662651908-14.8230312721=0.243233918673\\\widehat q=t_q/I_q=39.42467555\ \mathrm{\mu g/m^3}\end{gathered}',
    legend='I_q: information for q after removing the gain nuisance terms [(µg/m³)⁻²]\nt_q: remaining weighted evidence for q [(µg/m³)⁻¹]',
    body=['The same solve gives b̂₀ = 0.00413651 dB and b̂₁ = 0.01014643 dB.',
          'The true simulated q was 50.5814 µg/m³. The estimate is different because this observation contains error.'],
    caveat=CONDITION,
    notes='This is the scalar Schur complement of the two gain parameters. It is algebraically equivalent to the whiten and project construction in the source tutorial. The subtraction removes the component of the molecular column that can be explained by a constant and a spectral slope. Rounding the two terms too aggressively before subtraction can lose precision, so the script uses full precision throughout. The inferred b coefficients are fitted nuisance values; they are not independent instrument calibration measurements.')

add('Step 14 · The estimate exceeds a prespecified threshold',
    latex=r'\begin{gathered}s_0=I_q^{-1/2}=12.73127783\ \mathrm{\mu g/m^3}\\\tau=z_{0.99}s_0=(2.326347874)(12.73127783)=29.61738111\ \mathrm{\mu g/m^3}\\\widehat q=39.42467555>29.61738111\quad\Longrightarrow\quad\text{detection}\end{gathered}',
    legend='H₀: q = 0 · H₁: q > 0 · s₀: standard deviation under H₀\nτ: threshold for 1% false alarm probability for this one prespecified compound and decision',
    body=['The decision says the observed pattern is inconsistent with no enhancement under this model.',
          'It does not establish exact concentration, unique chemical identity in a changing mixture, or field performance.'],
    caveat=CONDITION,
    notes='The threshold is fixed from the null model before inspecting the observation. The unconstrained signed estimator is used for the test; truncating negative estimates to zero would change its null distribution. This one successful random draw does not itself show 95% detection probability. The threshold and a 95% power concentration are different quantities.')

add('Why the chosen q was 50.5814 µg/m³',
    latex=r'\begin{gathered}\Pr(\widehat q>\tau\mid q)=0.95\quad\Longleftrightarrow\quad q-\tau=z_{0.95}s_1(q)\\q_{95}=29.61738111+(1.644853627)(12.74521644)=50.58139660\ \mathrm{\mu g/m^3}\end{gathered}',
    legend='s₁(q) = √[H C(q) Hᵀ] · H is the first row of G⁻¹ Aᵀ C(0)⁻¹, so q̂ = H y.\nz₀.₉₅: standard normal 95th percentile · these weights are fixed under the null.',
    body=['This concentration was selected from the analytical sensitivity calculation before the random receiver draw.',
          'It is a controlled simulation input. It was neither measured in the atmosphere nor estimated from the sample.'],
    takeaway='The threshold is 29.6174 µg/m³. Achieving 95% predicted response requires a larger true enhancement.',
    caveat=CONDITION,
    notes='The equation is implicit because s1 depends slightly on q through sample SNR. The code solves it numerically; evaluating at its solution gives the arithmetic displayed here. The constant variance approximation would give 50.5585 µg/m³. This explains the otherwise arbitrary looking number in the screenshot. It does not imply this is an environmentally typical concentration.')

add('Repeated observations show success and failure rates',table=[['True q (µg/m³)', 'Predicted response', 'Simulated response', '95% interval'],
    *[[f"{float(r['true_ug_m3']):.4f}".rstrip('0').rstrip('.'),f"{float(r['predicted_response_pct']):.2f}%",f"{float(r['empirical_response_pct']):.2f}%",f"{float(r['response_ci95_lower_pct']):.2f}–{float(r['response_ci95_upper_pct']):.2f}%"] for r in controls]],widths=[.25,.25,.25,.25],
    body=['10,000 simulated reference/sample pairs at each concentration, using the same fixed threshold.'],
    takeaway='1 µg/m³ is not reliably detected: the simulated response is only 1.31%, near the false alarm rate.',
    caveat=CONDITION,
    notes='The counts are 113/10000 under q=0, 131/10000 at q=1 and 9475/10000 at q=50.5814. The exact binomial intervals describe Monte Carlo uncertainty, not uncertainty in hardware calibration, spectroscopy or real weather. The observations use complex pilot means, rather than directly drawing a Gaussian concentration estimate.',refs=[S['tutorial'],REPO+'b94f3fe/results/zenith_single_compound/receiver_control.csv'])

add('What is real, assumed and simulated in this example',table=[['Evidence category', 'What belongs to it'],
    ['External physical inputs', 'Actual HITRAN records; published ITU atmospheric models'],
    ['Design assumptions', '550 km geometry; hardware configuration; exponential gas enhancement'],
    ['Unmeasured error assumption', '0.001 dB differential residual and its spectral covariance'],
    ['Simulated observation', 'Complex pilot means, calibration draw and resulting y'],
    ['Not demonstrated', 'Measured atmospheric detection, ambient sensitivity or 3D reconstruction']],widths=[.31,.69],
    takeaway='The calculation is concrete and reproducible. It is not an orbital measurement.',
    caveat='A selected aircraft background reference is about 0.252 µg/m³, far below this conditional enhancement limit.',
    notes='The EMeRGe/IAGOS contextual reference is 145 pptv, equivalent to about 0.252 µg/m³ at 288.15 K and 101325 Pa. It is not a universal ground concentration or a concentration profile measurement for this example. Real detection requires independently measured concentration, blank stability and a tested moving receiver. Multiple ground receivers would require adequate ray diversity and an identifiable tomographic model. LEO is a useful example for the full chain, not evidence that every proposed sensing mode is feasible.',refs=[S['tutorial'],S['revision'],S['ambient']])

add('The original table, now with its calculation attached',table=[['Quantity', 'How the value is obtained', 'Result'],
    ['Chosen enhancement', 'Solve the 95% power equation, then set the simulation input', '50.5814 µg/m³'],
    ['Extra absorption at tone 0', '(0.0002408199585) × 50.5813966', '0.012181 dB'],
    ['Sample/reference amplitude', '10^(−0.01218100983 / 20)', '0.998599'],
    ['Amplitude reduction', '100 × (1 − 0.9985985923)', '0.1401%']],widths=[.29,.49,.22],
    takeaway='After adding the modeled errors and fitting all tones: q̂ = 39.4247 µg/m³ > threshold 29.6174 → detection.',
    caveat=CONDITION,
    notes='This closes the requested explanation of the screenshot. The deterministic chain and statistical inverse are different operations. The forward model computes a pattern from a chosen concentration; the receiver fit estimates concentration from noisy observations without knowing the chosen value. That distinction is necessary to avoid confusing the simulated truth, predicted attenuation and retrieved concentration.')

T=node['temperature_k']; c2=v['second_radiation_constant_cm_k']
qfactor=v['node_partition_reference']/v['node_partition_temperature']
bf=math.exp(-c2*line['lower_state_energy']*(1/T-1/296))
sf=(-math.expm1(-c2*line['wavenumber_cm_1']/T))/(-math.expm1(-c2*line['wavenumber_cm_1']/296))
add('Appendix · Temperature correction for the actual line',
    latex=r'S(T)=S(296)\frac{Q(296)}{Q(T)}\exp\!\left[-c_2E^{\prime\prime}\left(\frac1T-\frac1{296}\right)\right]\frac{1-e^{-c_2\widetilde\nu/T}}{1-e^{-c_2\widetilde\nu/296}}',
    legend='Q(T): molecular partition sum · E″ = 47.8643 cm⁻¹ · ν̃ = 7.97678228 cm⁻¹\nc₂: second radiation constant (cm K) · T = 288.040263 K',
    body=[f'Q(296) / Q(T) = 88658.97016 / 83172.06723 = {qfactor:.9f}.',
          f'S(T) = 2.616 × 10⁻²¹ × {qfactor:.9f} × {bf:.9f} × {sf:.9f} = 2.845759 × 10⁻²¹ cm/molecule.'],
    takeaway='The line strength changes with state populations and stimulated emission before the profile is applied.',
    notes='The partition sums come from HAPI TIPS2025. The Boltzmann factor uses the lower state energy, and the last factor corrects stimulated emission. Width is also adjusted: γ = 0.1594 × (101122.3515/101325) × (296/288.040263)^0.71 = 0.1621900503 cm⁻¹. The saved source uses the second radiation constant defined in physical_spectroscopy.py. All factors are calculated at the first actual quadrature node, not at a rounded atmospheric state.',refs=[S['hitran'],S['hapi'],S['steps']])

add('Appendix · Power and noise at the first tone',table=[['Link budget term', 'Value'],
    ['Transmit power per tone', '25 − 10 log₁₀(1024) = −5.1030 dBm'],
    ['Transmit + receive gains', '45.7705 + 65.7705 dBi'],
    ['Free space + background + implementation loss', '194.4898 + 4.5477 + 5.0000 dB'],
    ['Reference / sample received power', '−97.5996 / −97.6118 dBm'],
    ['Noise power in one tone', '−97.4270 dBm'],
    ['Reference per pilot SNR', '−0.172605 dB = 0.96103566 linear']],widths=[.55,.45],
    caveat='The extra 0.012181 dB CH₃CN loss belongs only to the sample in this enhancement model.',
    notes='Received power equals per tone power plus both antenna gains minus free space, background and implementation loss. Noise uses kB(Tsky+Te)Δf, with Tsky = 177.831 K and Te = 290(10^(7/10)−1). The noise figure is not counted twice. More exact values are saved in tone_by_tone.csv. The 25 dBm is the total average RF power across all tones, not per tone or electrical input power.',refs=[S['tutorial'],S['p676'],REPO+'b94f3fe/results/zenith_single_compound/tone_by_tone.csv'])

add('Appendix · Five actual rows of the covariance',table=[['C / 10⁻⁴ dB²', '0', '255', '511', '767', '1023'],
    *[[str(k),*[f'{x*1e4:.6f}' for x in row]] for k,row in zip(mini['tone_indices_zero_based'],mini['C'])]],widths=[.24,.152,.152,.152,.152,.152],
    body=['This is a submatrix of the full null covariance, not a new error model.'],
    takeaway='The off diagonal elements carry the assumed correlation between spectral errors.',
    caveat=CONDITION,
    notes='Each row and column is indexed by the original tone number. Multiply each displayed entry by 10^−4 dB² to obtain the covariance value. The diagonal includes both thermal and persistent calibration variance. Selecting only these tones requires recalculating the estimator using the corresponding A rows and this submatrix. Taking five entries from the full H would not produce the five tone estimator.')

add('Appendix · A five tone dot product can be checked by hand',table=[['Tone k', 'Observed yₖ (dB)', 'Five tone weight H₅,ₖ', 'Product H₅,ₖ yₖ'],
    *[[str(k),f'{y:.9f}',f'{h:.3f}',f'{h*y:.6f}'] for k,y,h in zip(mini['tone_indices_zero_based'],mini['y'],mini['H'][0])]],widths=[.15,.28,.28,.29],
    takeaway=f"Sum = {mini['estimate_ug_m3']:.4f} µg/m³; standard deviation = 165.1163; threshold = 384.1179 → no detection.",
    caveat='This discards 1,019 tones. The main detector uses all 1,024, with the same assumed 0.001 dB residual and 20 s total.',
    notes='These are the same five observations extracted from the full simulated spectrum. The weights are recomputed for only these five tones while allowing the same gain offset and slope. The entries and their products show a literal matrix multiplication. Its large uncertainty means the estimate 171.7494 is not persuasive evidence, even though it is larger than the full spectrum estimate. Source values retain full precision; the displayed products use full precision before rounding.')

add('Appendix · Hardware evidence keeps its original scope',table=[['Source', 'Useful evidence', 'What it does not establish'],
    ['Sen et al., Nature Electronics', '200 mW at 210–240 GHz, terrestrial link', 'Orbital operation'],
    ['TeraLink, 2026 preprint', '25 dBm, 7 dB NF, proposed LEO system', 'Flight validation of this example'],
    ['Cooper et al., JMW', '>400 mW CW at 240 GHz', 'A complete 10 GHz OFDM modem']],widths=[.28,.36,.36],
    takeaway='The selected parameters have physical references, but combined bandwidth, calibration and tracking remain unverified.',
    caveat='1 W and 10 W transmit cases elsewhere in the repository are sensitivity scenarios, not qualified payload specifications.',
    notes='Transmit power values must refer to the same quantity when comparing hardware: average linear OFDM output differs from peak pulse power and electrical supply power. The published design and laboratory references are meaningful anchors but cannot prove the whole assumed measurement chain. The research note retains antenna dimensions, pointing, surface tolerance, motion and power comparisons.',refs=[S['sen'],S['teralink'],S['cooper'],S['revision']],source='Primary hardware references · exact URLs in notes')

add('Sources · Spectroscopy and atmospheric state',body=[
    'HITRAN: actual CH₃CN line records, units, temperature correction and absorption model. hitran.org/docs/definitions-and-units/',
    'HAPI and TIPS2025: partition functions used in the spectral calculation. Kochanov et al., JQSRT 177 (2016), DOI 10.1016/j.jqsrt.2016.03.005.',
    'ITU P.835-7 (2024): standard atmospheric state. ITU P.676-13 (2022): oxygen/water propagation and emission.',
    'EMeRGe / IAGOS context: ACP 23, 1893 (2023), DOI 10.5194/acp-23-1893-2023.'],
    notes='These are primary method and context references. The HITRAN table is an external physical input; the code adds the declared geometry, concentration profile and receiver error assumptions. See the linked source audit for each claim boundary. HAPI version in the retained experiment is 1.3.0.0.',refs=[S['hitran'],S['hapi'],S['p835'],S['p676'],S['ambient']],source='Primary sources · clickable URLs in notes')

add('Sources · Every numerical step is saved',body=[
    'worked_steps.json contains the values substituted in the equations.',
    'quadrature_first_tone.csv and altitude_contributions.csv expose the complete atmospheric integral.',
    'complex_receiver_steps.csv records both complex pilot means and the final observation at every tone.',
    'normal_equations.npz stores G, g and θ̂; the original matrices.npz contains the full A, C and H.'],
    takeaway='Reproduce with scripts/calculate_zenith_worked_steps.py. The saved source hashes are in manifest.json.',
    notes='The numerical replay starts from the original experiment snapshot b94f3fe and does not alter the main scientific result. The data directory is results/zenith_worked_steps. The physical forward sum and the complex random draw are independently replayed, then compared against the saved outputs. The first tone sensitivity, whole spectrum estimate and uncertainty agree. Equations and slide source values are drawn from these files.',refs=[S['steps'],REPO+'main/results/zenith_worked_steps/manifest.json',REPO+'main/scripts/calculate_zenith_worked_steps.py',S['tutorial']])

assert len(slides)==32
assert all(s['notes'] and s['sources'] for s in slides)
assert math.isclose(v['a0_db_per_ug_m3']*v['true_q_ug_m3'],v['attenuation_at_q_db'],rel_tol=1e-12)
assert math.isclose(v['q95_reconstruction'],v['true_q_ug_m3'],rel_tol=1e-12)
(BUILD/'slides.json').write_text(json.dumps(slides,indent=2,ensure_ascii=False),encoding='utf-8')
notes=['# CH₃CN at 90°: worked calculation for a telecom audience','',
       'Slides 1–25 explain the experiment and derive the numerical receiver decision. Slides 26–32 provide calculation details and references.',
       '', 'The spectroscopic records are external physical data. The concentration profile and receiver observations are modeled; no orbital measurement is claimed.', '']
for i,s in enumerate(slides,1):
    notes += [f"## {i}. {s['title'].replace(chr(10),' ')}",'',s['notes'],'']
    if s['body']:notes += [*s['body'],'']
    if s['table']:
        notes += ['| '+' | '.join(s['table'][0])+' |',
                  '| '+' | '.join('---' for _ in s['table'][0])+' |',
                  *['| '+' | '.join(row)+' |' for row in s['table'][1:]],'']
    if s['latex']:notes += ['$$\n'+s['latex']+'\n$$','',s['legend'] or '','']
    if s['takeaway']:notes += [s['takeaway'],'']
    if s['caveat']:notes += ['Conditions: '+s['caveat'],'']
    notes += ['Sources:','',*[f'- <{url}>' for url in s['sources']],'']
(OUT/'zenith_acetonitrile_worked_notes.md').write_text('\n'.join(notes),encoding='utf-8')
print(f'Prepared {len(slides)} slides for a telecom audience with explicit numerical substitutions')
