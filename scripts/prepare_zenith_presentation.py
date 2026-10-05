"""Prepare a sourced teaching deck from the saved zenith experiment."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/zenith_single_compound'
BUILD = ROOT / 'tmp/zenith_deck'
OUT = ROOT / 'output/presentations'
BUILD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
SNAPSHOT = 'b94f3fe'
REPO = f'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/{SNAPSHOT}/'

def read_csv(name):
    with (DATA / name).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))

base = json.loads((DATA / 'baseline.json').read_text())
worked = json.loads((DATA / 'worked_example.json').read_text())
tones = read_csv('tone_by_tone.csv')
observations = read_csv('worked_observation.csv')
controls = read_csv('receiver_control.csv')
sensitivity = read_csv('sensitivity.csv')
spacing = read_csv('ofdm_spacing.csv')
mini = worked['miniature']
result = base['result']
S = {
    'tutorial': REPO + 'docs/55_zenith_single_compound_walkthrough.md',
    'revision': REPO + 'docs/54_supervisor_revision_2026_10_05.md',
    'hitran': 'https://hitran.org/lbl/',
    'p835': 'https://www.itu.int/rec/R-REC-P.835-7-202408-I/en',
    'p676': 'https://www.itu.int/rec/R-REC-P.676-13-202208-I',
    'sen': 'https://www.nature.com/articles/s41928-022-00897-6',
    'teralink': 'https://arxiv.org/html/2606.15410v1',
    'cooper': 'https://doi.org/10.1109/JMW.2025.3610360',
    'emerge': 'https://acp.copernicus.org/articles/23/1893/2023/index.html',
}
CONDITION = '20 s total • ideal tracking • assumed, unmeasured 0.001 dB differential calibration residual'
slides = []

def add(title, *, body=None, table=None, widths=None, latex=None, legend=None,
        chart=None, takeaway=None, caveat=None, notes='', refs=None, source='Saved zenith experiment · b94f3fe', kind='standard'):
    slides.append(dict(title=title, body=body or [], table=table, widths=widths,
                       latex=latex, legend=legend, chart=chart, takeaway=takeaway,
                       caveat=caveat, notes=notes, sources=refs or [S['tutorial']],
                       source=source, kind=kind))

add('Detecting acetonitrile\nat 90° elevation', kind='cover',
    body=['A complete example using a LEO downlink', 'Intuition, observations, matrices and the detection decision'],
    notes='This example concerns a prespecified increase in acetonitrile relative to a reference. All observations in the worked example are simulations driven by published physical models and acquired HITRAN parameters. The underlying research snapshot is b94f3fe, dated 5 October 2026. No measured orbital detection is claimed.')

add('The detection question', body=[
    'Has acetonitrile, CH₃CN, increased? Compare a baseline transmission (reference) with a later transmission (sample).',
    'The unknown q is the concentration increase at ground level under an assumed vertical profile, measured in µg/m³.',
    'LEO links are a useful example throughout the sensing chain. The same reasoning can be adapted to terrestrial and UAV links.'],
    takeaway='The output is a concentration enhancement and a statistical decision.',
    caveat='One path does not recover an arbitrary vertical profile or a 3D image.',
    notes='Explain the difference between detecting an enhancement and measuring an absolute background concentration. The reference is a finite, noisy acquisition. Other gases remain unchanged in this first example. A positive decision means consistency with the chosen CH3CN template under these assumptions, not proven chemical specificity in an unknown mixture.')

add('The intuition', body=[
    '1. Send known tones across a 10 GHz band and measure their received amplitudes.',
    '2. Compare a reference with a sample after correcting known link changes.',
    '3. Match the remaining frequency pattern to the molecular absorption template.',
    '4. Estimate its strength and compare it with a threshold fixed in advance.'],
    takeaway='The useful evidence is the spectral shape across tones, not one noisy dip.',
    notes='The molecular template is calculated from spectroscopy, not drawn by hand. Thermal averaging reduces random receiver uncertainty. Persistent calibration errors do not disappear simply by collecting more pilots. Unknown gain offset and gain slope are fitted so that they do not automatically count as gas.')

add('The 90° geometry', table=[['Quantity', 'Example', 'Meaning'],
    ['Ground elevation', '90°', 'Satellite directly overhead'],
    ['Satellite altitude', '550 km', 'Chosen LEO scenario'],
    ['Slant range', '550 km', 'Shortest path for this altitude'],
    ['Atmospheric integration', '0–100 km', 'Standard atmosphere'],
    ['Concentration profile', 'q exp(−z / 1500 m)', 'Assumed enhancement shape']], widths=[.31,.24,.45],
    takeaway='90° is the maximum ground elevation. A 30° value can be a minimum elevation mask.',
    caveat='This is a static zenith benchmark. A real satellite keeps moving during acquisition.',
    notes='Angles must be defined: ground elevation, satellite off nadir angle and Earth central angle differ. The example sets the ground elevation to 90 degrees. A 550 km orbit is a chosen geometry, not a retrieved orbit. The physical atmosphere occupies only part of the 550 km propagation path. Coverage values and moving geometry are retained in the research note.',
    refs=[S['tutorial'],S['revision'],S['p835']], source='Geometry: chosen scenario · Atmosphere: ITU P.835')

add('What the hardware sources demonstrate', table=[['Source', 'Reported quantity', 'Scope'],
    ['Sen et al., Nature Electronics', '200 mW, about 23 dBm', 'Measured terrestrial link, 210–240 GHz'],
    ['TeraLink, 2026 preprint', '25 dBm, 7 dB noise figure', 'Published LEO design, not flight validation'],
    ['Cooper et al., JMW', '>400 mW at 240 GHz', 'Continuous wave source component']], widths=[.32,.29,.39],
    takeaway='25 dBm is a design anchor for this example, not proof of a complete OFDM payload.',
    caveat='The sources do not demonstrate the full bandwidth, linear output, tracking and calibration together.',
    notes='Sen et al. is experimental terrestrial evidence. TeraLink is a proposed space link with qualification work ongoing. Cooper et al. reports a frequency multiplier source, not a complete wideband satellite modem. RF average power, peak radar power and electrical power are different quantities. Increasing the simulated power to 1 W or 10 W is only an engineering sensitivity, not a demonstrated payload capability.',
    refs=[S['sen'],S['teralink'],S['cooper'],S['revision']], source='Sen et al. · TeraLink preprint · Cooper et al. · Full links in notes')

add('The chosen link budget inputs', table=[['Input', 'Value', 'Status'],
    ['Total average RF power', '25 dBm = 316 mW', 'Published design anchor'],
    ['Transmit / receive diameter', '0.10 m / 1.0 m', 'Circular aperture model'],
    ['Aperture efficiency', '0.65 at both ends', 'Assumed'],
    ['Gain at 235 GHz', '45.96 / 65.96 dBi', 'Calculated from aperture'],
    ['Receiver noise figure', '7 dB at T₀ = 290 K', 'Published design anchor'],
    ['Implementation loss', '5 dB', 'Assumed budget']], widths=[.36,.31,.33],
    caveat='The linear average power available for OFDM after amplifier backoff remains unverified.',
    notes='G = η(πDf/c)². A 1 m ground reflector also appears in the TeraLink design analysis, with 60% efficiency there; this example uses an assumed 65%. The 10 cm equivalent circular transmit aperture is not an assertion that the published 9 × 9 cm horn array has this exact geometry. Calculated uniform aperture beamwidths are about 0.7455 degrees for transmit and 0.07455 degrees for receive. Both pointing and surface accuracy matter.',
    refs=[S['teralink'],S['revision'],REPO+'results/zenith_single_compound/antennas.csv'], source='Design anchors: TeraLink · Assumptions and aperture calculations: repository')

add('The OFDM frequency grid', table=[['Quantity', 'Value'],
    ['Occupied band and tone count K', '230–240 GHz, 1,024 tones'],
    ['Spacing Δf = B / K', '9.765625 MHz'],
    ['Useful symbol Tᵤ = 1 / Δf', '102.4 ns'],
    ['Assumed cyclic prefix T_CP', '10 ns'],
    ['Transmitted symbol Tₛ = Tᵤ + T_CP', '112.4 ns'],
    ['Pilots per 10,000 symbol frame', '30 full pilot symbols, 0.3%']], widths=[.53,.47],
    takeaway='All tones share the same 25 dBm total average transmit power.',
    notes='The tone centers are 230 GHz + (k+1/2)Δf for k from 0 to 1023. Thus the first center is 230.0048828125 GHz and the last is 239.9951171875 GHz. The cyclic prefix is a short copy of the end of the symbol placed at its beginning to accommodate channel delay spread; its duration here is assumed. A frame is a repeated schedule of 10,000 symbols. Residual frequency error is another design assumption. This is not a validated hardware waveform. Unknown data symbols are not used for sensing in this tutorial. The spacing appendix explains the comparison.',
    refs=[S['tutorial'],REPO+'results/zenith_single_compound/ofdm_spacing.csv'])

add('Twenty seconds include the reference', table=[['Acquisition', 'Scheduled time', 'Complete frames', 'Pilots per tone'],
    ['Reference', '10 s', '8,896', '266,880'],
    ['Sample', '10 s', '8,896', '266,880']], widths=[.27,.23,.23,.27],
    latex=r'M=\left\lfloor\frac{10\ \mathrm{s}}{10{,}000\times112.4\ \mathrm{ns}}\right\rfloor\!\times30=266{,}880',
    legend='M is the number of known pilot observations per tone, per acquisition.',
    takeaway='19.998208 s are occupied by complete frames. Both acquisitions contribute noise.',
    caveat='Waiting for comparable geometry, calibration and reference availability adds operational time.',
    notes='Each acquisition transmits 88,960,000 complete symbols. The two acquisitions leave 0.001792 s unused because only complete frames count. The reference is not exact and is not free. Ideal correction of delay, phase, Doppler and gain is assumed over these windows; a static 90 degree path cannot literally persist for twenty seconds in a LEO pass.')

add('The molecular template comes from spectroscopy', body=[
    'HITRAN supplies CH₃CN line positions, strengths and broadening parameters.',
    'A Voigt model and the atmospheric pressure and temperature give the cross section at each altitude.'],
    latex=r'c(z)=q e^{-z/H_g},\quad H_g=1500\ \mathrm{m}\qquad a_k=\frac{10}{\ln 10}\int_0^{100\ \mathrm{km}}\sigma_k(z)n_1(z)\,dz',
    legend='q: surface equivalent enhancement (µg/m³) · σₖ: effective absorption area per molecule\nn₁: molecular density for q = 1 µg/m³ · aₖ: dB per (µg/m³). Use consistent length units in the integral.',
    takeaway='The predicted extra attenuation at tone k is aₖq dB.',
    caveat='The vertical shape is assumed. The model does not measure concentration at each height.',
    notes='17,880 retained CH3CN transitions from local isotope ID 1 are used. Their acquired line centers span 2.77489–2003.4586 GHz, and the model includes the acquired line wings. Natural isotope abundance is already included in HITRAN line intensity. HAPI Voigt and TIPS2025 supply temperature dependence. At q = 1 µg/m³, n1(0) is approximately 1.467 × 10^16 molecules/m³ using molar mass 41.053 g/mol. HAPI cross sections in cm² require density in cm⁻³ and path in cm. The mass column is approximately 1500q µg/m². ITU oxygen/water attenuation is modeled separately without duplicating these contributions in HITRAN.',
    refs=[S['hitran'],S['p835'],S['tutorial'],REPO+'results/zenith_single_compound/physics_provenance.json'], source='Spectroscopy: acquired HITRAN catalog and HAPI · Atmosphere: ITU P.835')

add('The acetonitrile spectral pattern', chart=dict(
    x=[float(r['frequency_ghz']) for r in tones],
    series=[dict(name='Calculated CH₃CN sensitivity', values=[float(r['gas_db_per_ug_m3'])*1e3 for r in tones], color='#126B76')],
    xtitle='Frequency (GHz)',ytitle='Sensitivity [10⁻³ dB per (µg/m³)]', ymin=0, ymax=.85),
    takeaway='The estimator uses the full 1,024 tone template, including its curvature.',
    caveat='Calculated absorption from external line parameters, not a measured satellite spectrum.',
    notes='Every plotted value is taken from tone_by_tone.csv. A gain offset and linear gain slope can explain parts of this pattern. The estimator therefore uses the part that remains after projecting out those nuisance directions. The displayed curve is the model for the assumed exponential vertical profile.',
    refs=[S['hitran'],REPO+'results/zenith_single_compound/tone_by_tone.csv'], source='HITRAN driven calculation · tone_by_tone.csv')

first = tones[0]
add('One tone: the complete power accounting', table=[['Term at 230.004883 GHz', 'Value'],
    ['Transmit power per tone: 25 − 10 log₁₀(1024)', '−5.1030 dBm'],
    ['Transmit gain + receive gain', '45.7705 + 65.7705 dBi'],
    ['Free space loss', '194.4898 dB'],
    ['Oxygen / water attenuation', '4.5477 dB'],
    ['Implementation loss', '5.0000 dB'],
    ['Received reference power', '−97.5996 dBm']], widths=[.69,.31],
    takeaway='Received power = tone power + gains − propagation loss − implementation loss.',
    notes='These values describe the reference, with enhancement q = 0. A sample enhancement subtracts a_k q dB additionally. The total average RF power must be divided among all active tones. Gain is a power gain. The first tone is shown for auditable arithmetic, while the simulation recomputes all frequency dependent terms for every tone.',
    refs=[S['p676'],REPO+'results/zenith_single_compound/tone_by_tone.csv'], source='Calculated first tone · ITU P.676 background · tone_by_tone.csv')

add('Receiver noise determines the pilot uncertainty',
    latex=r'T_e=T_0\left(10^{NF/10}-1\right),\qquad N_k=k_B(T_{\mathrm{sky},k}+T_e)\Delta f,\qquad\rho_{r,k}=P_{r,k}/N_k',
    legend='NF: receiver added noise, expressed as a noise figure (7 dB) · T₀ = 290 K · Tₑ: equivalent noise temperature\nT_sky: sky brightness temperature (K) · k_B: Boltzmann constant · Nₖ: noise power (W) · ρ: signal to noise ratio',
    table=[['First tone', 'Calculated value'], ['Sky temperature', '177.831 K'], ['Noise power per tone', '−97.4270 dBm'], ['Reference SNR ρ₀ in dB', '−0.1726 dB']], widths=[.6,.4],
    caveat='Sky emission and receiver noise are counted once. Noise figure is not applied twice.',
    notes='The integrated atmosphere contributes attenuation and thermal emission. The receiver noise temperature convention uses the 290 K reference temperature, but atmospheric sky temperature is calculated independently. Antenna spillover and hardware thermal losses require more detailed measurements for a real terminal. The reference SNR across the full band is between −0.1874 and −0.1657 dB.', refs=[S['p676'],S['tutorial'],REPO+'results/zenith_single_compound/tone_by_tone.csv'])

add('The observation matrices',
    latex=r'\mathbf Y_r=\operatorname{diag}(\mathbf h_r)\mathbf X_r+\mathbf W_r,\qquad r\in\{0,1\}',
    table=[['Object', 'Dimensions', 'Meaning'],
    ['Xᵣ', '1,024 × 266,880', 'Known unit magnitude pilots'],
    ['hᵣ', '1,024 × 1', 'Amplitude and phase response of each tone'],
    ['diag(hᵣ)', '1,024 × 1,024', 'One complex gain per tone'],
    ['Yᵣ and Wᵣ', '1,024 × 266,880', 'Received samples and complex thermal noise']], widths=[.2,.25,.55],
    legend='r = 0: reference · r = 1: sample · k: tone · m: pilot · |hᵣ,ₖ|² = received power with unit pilots',
    caveat='Delay, phase and carrier frequency corrections are ideal in this observation model.',
    notes='Each W_r,k,m is independent circular complex Gaussian noise with expected squared magnitude N_k. With unit pilots, |h_r,k|² is received power. This equation defines the physical observation model. The implementation draws exact coherent Gaussian pilot means as sufficient statistics, avoiding storage of the huge Y matrices. It does not run a full 10 GHz waveform, IFFT, cyclic prefix, synchronization or payload decoder.')

add('Averaging produces one channel estimate per tone',
    latex=r'\widehat h_{r,k}=\frac{1}{M}\sum_{m=1}^M Y_{r,k,m}X_{r,k,m}^{*},\qquad\widehat h_{r,k}\sim\mathcal{CN}\!\left(h_{r,k},\frac{N_k}{M}\right)',
    legend='M = 266,880 pilots per tone in each acquisition · *: complex conjugate\nCN: circular complex Gaussian distribution, with stated complex variance',
    body=['The receiver removes the known pilot phase, then averages coherently.',
          'The raw matrices reduce to two complex vectors, each with 1,024 entries.'],
    takeaway='Thermal variance falls by M only when the phase correction permits coherent averaging.',
    caveat='Persistent spectral calibration error survives this averaging.',
    notes='The complex mean distribution is exact for the stated independent Gaussian pilot model. Its use avoids simulating 273 million complex samples per acquisition. The minimum coherent mean SNR exceeds 255,000 under the baseline, which supports the subsequent log amplitude delta approximation. This mathematical reduction does not demonstrate the stability or tracking of a physical receiver.')

add('The reference ratio becomes an attenuation vector',
    latex=r'y_k=-20\log_{10}\!\left(\frac{|\widehat h_{1,k}|}{|\widehat h_{0,k}|}\right),\qquad \mathbf y\in\mathbb R^{1024}',
    legend='yₖ: differential attenuation (dB) · ĥ₀: reference channel estimate · ĥ₁: sample channel estimate',
    body=['Extra molecular absorption reduces the sample amplitude, so the expected yₖ is positive.',
          'Known geometry and hardware corrections precede the comparison.'],
    takeaway='Under matched background, the molecular contribution is yₖ ≈ aₖq.',
    caveat='An amplitude equalizer that removes the molecular pattern would also remove the sensing evidence.',
    notes='The factor is 20 because the ratio uses field amplitude. Equivalently, the power ratio uses 10 log10. The modeled calibration residual enters this differential dB vector once per reference/sample pair. Weather mismatch can add a structured bias and is not automatically canceled.')

add('The design matrix separates gas from gain changes',
    latex=r'\begin{gathered}\mathbf y=\mathbf A\boldsymbol\theta+\boldsymbol\varepsilon,\qquad\mathbf A=\begin{bmatrix}\mathbf a&\mathbf 1&\mathbf u\end{bmatrix}\in\mathbb R^{1024\times3}\\\boldsymbol\theta=\begin{bmatrix}q&b_0&b_1\end{bmatrix}^{T},\qquad u_k=\frac{f_k-\bar f}{f_{\max}-f_{\min}}\end{gathered}',
    legend='a: molecular template [dB per (µg/m³)] · q: enhancement (µg/m³) · ε: remaining measurement error (dB)\nb₀: gain offset (dB) · b₁: gain slope coefficient (dB) · u: dimensionless, spanning −0.5 to +0.5',
    body=['Column 1 is the predicted molecular shape.',
          'Columns 2 and 3 allow an unknown common gain offset and linear spectral tilt.'],
    takeaway='A is built from known frequency samples. Only q, b₀ and b₁ are unknown.',
    notes='The nuisance matrix B = [1,u] has dimension 1024 × 2. Fitting nuisance terms costs information but avoids attributing simple gain changes to gas. A different changing gas or an arbitrary nonlinear calibration error can still imitate part of a. The appendix lists every entry for a five tone subset.')

add('The covariance includes both measurements',
    latex=r'\begin{gathered}\mathbf C(q)=\operatorname{diag}(v_k(q))+\sigma_{\mathrm{cal}}^2\mathbf R,\quad R_{ij}=e^{-|f_i-f_j|/(10\ \mathrm{GHz})}\\v_k(q)=\frac{(20/\ln10)^2}{2M}\left[\rho_{0,k}^{-1}+\rho_{1,k}(q)^{-1}\right]\end{gathered}',
    legend='C: 1,024 × 1,024 covariance in dB² · vₖ: thermal variance of the log ratio\nρ₀, ρ₁: linear per pilot SNR · σ_cal = 0.001 dB: assumed differential residual standard deviation',
    body=['Diagonal thermal noise contains reference and sample uncertainty.',
          'Calibration residual is the instrument error left after correction. Its spectral pattern persists across the pair.'],
    caveat='The 0.001 dB residual and its frequency correlation are assumptions, not receiver measurements.',
    notes='The log ratio variance is a high coherent mean SNR approximation. rho_1,k(q) = rho_0,k × 10^(−a_k q/10). C(q) is thus slightly concentration dependent. The calibration covariance already describes a differential residual, so it must not be doubled or divided by M again. The detector fixes its weights using C(0), while positive concentration power calculations evaluate C(q).')

add('Whitening and removal of nuisance directions',
    latex=r'\begin{gathered}\mathbf C(0)=\mathbf L\mathbf L^T,\quad\widetilde{\mathbf y}=\mathbf L^{-1}\mathbf y,\quad\widetilde{\mathbf a}=\mathbf L^{-1}\mathbf a,\quad\widetilde{\mathbf B}=\mathbf L^{-1}\mathbf B\\\mathbf r=(\mathbf I-\mathbf Q\mathbf Q^T)\widetilde{\mathbf a}\end{gathered}',
    legend='L: Cholesky factor of null (q = 0) covariance · B = [1,u] · Q: orthonormal basis for columns of L⁻¹B\nr: the whitened molecular pattern after removing gain offset and slope',
    body=['Whitening changes coordinates so that the null noise covariance is the identity.',
          'Projection keeps only the molecular pattern that gain offset and slope cannot explain.'],
    takeaway='If r were zero, the concentration would be unidentifiable under this nuisance model.',
    notes='The code uses Cholesky solves and an SVD basis, not explicit matrix inverses. L is 1024 × 1024, B and Q are 1024 × 2, and r is 1024 × 1. Whitening means the null noise covariance becomes identity. Projection onto the orthogonal complement of the nuisance span provides the generalized least squares concentration estimator.')

add('One row of weights estimates concentration',
    latex=r'\widehat q=\frac{\mathbf r^T\widetilde{\mathbf y}}{\mathbf r^T\mathbf r}=\mathbf H\mathbf y,\qquad\mathbf H=\frac{\mathbf r^T\mathbf L^{-1}}{\mathbf r^T\mathbf r},\qquad s_0^2=\mathbf H\mathbf C(0)\mathbf H^T',
    legend='H: 1 × 1,024 concentration weights [(µg/m³)/dB] · q̂: estimated enhancement (µg/m³)\ns₀: null standard deviation of q̂ (µg/m³)',
    table=[['Quantity', 'Baseline value'], ['Null standard deviation s₀', '12.7313 µg/m³'], ['Response to gas: H a', '1, within numerical precision'], ['Response to gain terms: H B', '0, within numerical precision']], widths=[.63,.37],
    caveat=CONDITION,
    notes='A positive or negative H entry is expected because the filter rejects nuisance directions. Ha differs from one by 5.55 × 10^−16 and the maximum magnitude of HB is 9.56 × 10^−13 in the saved arrays. These are algebraic checks, not experimental validation. The null standard deviation includes both finite acquisitions and the assumed persistent covariance.', refs=[S['tutorial'],REPO+'results/zenith_single_compound/verification.json'])

add('A fixed threshold turns the estimate into a decision',
    latex=r'H_0:q=0,\quad H_1:q>0,\qquad\widehat q>\underbrace{z_{0.99}s_0}_{\tau}=2.32635\times12.7313=29.6174\ \mathrm{\mu g/m^3}',
    legend='τ: decision threshold · z₀.₉₉: standard normal 99th percentile · false alarm target α = 1%\ns₁(q) = √[H C(q) Hᵀ]: standard deviation when the enhancement is q, using the fixed null weights H',
    body=['The 1% false alarm target applies to one prespecified compound and one decision.',
          'A 95% detection concentration is higher than the decision threshold.'],
    takeaway='Solving q − τ = 1.64485 s₁(q) gives q₉₅ = 50.5814 µg/m³.',
    caveat=CONDITION,
    notes='s1(q) = sqrt(H C(q) H^T), with H frozen at the null. Gaussian power is 1 − Φ((τ−q)/s1(q)). This yields 50.5813965969 µg/m³, while the constant variance shortcut yields 50.5584696236. The detection threshold is not itself a 95% sensitivity limit. Repeated searches across species, bands or time windows require a false alarm policy beyond this single test.')

add('One simulated observation crosses the threshold', chart=dict(
    x=[float(r['frequency_ghz']) for r in observations],
    series=[dict(name='Simulated attenuation',values=[float(r['observed_enhancement_db']) for r in observations],color='#B4BFC8'),
            dict(name='True molecular attenuation',values=[float(r['true_enhancement_db']) for r in observations],color='#126B76')],
    xtitle='Frequency (GHz)',ytitle='Differential attenuation (dB)',ymin=-.06,ymax=.1),
    takeaway=f"True q = {worked['true_concentration_ug_m3']:.4f} · estimated q = {worked['estimate_ug_m3']:.4f} > 29.6174 µg/m³ → detection",
    caveat=CONDITION,
    notes='The true q was fixed at the analytical 95% power concentration before drawing the observation. Random seed 20261005. The estimate differs from truth because this is one noisy draw. A successful example does not establish 95% empirical performance. The figure contains all 1024 tones and includes the saved persistent calibration residual. This is simulated evidence, not a measured spectrum.',
    refs=[REPO+'results/zenith_single_compound/worked_example.json',REPO+'results/zenith_single_compound/worked_observation.csv'])

add('Repeated simulations retain the failed low concentration case', table=[['True q (µg/m³)', 'Predicted response', 'Simulated response', '95% interval'],
    *[[f"{float(r['true_ug_m3']):.4f}".rstrip('0').rstrip('.'),f"{float(r['predicted_response_pct']):.2f}%",f"{float(r['empirical_response_pct']):.2f}%",f"{float(r['response_ci95_lower_pct']):.2f}–{float(r['response_ci95_upper_pct']):.2f}%"] for r in controls]], widths=[.25,.25,.25,.25],
    body=['10,000 independent reference/sample pairs for each concentration.'],
    takeaway='At 1 µg/m³, the 1.31% simulated response is close to the false alarm rate.',
    caveat=CONDITION,
    notes='At q = 0 the simulation gives 113 detections out of 10,000. At q = 1, 131/10,000. At q = 50.5814, 9475/10,000. Intervals are the saved 95% binomial intervals. Simulated complex pilot means test the analytical approximation within the same physical and error model. They do not validate an orbital receiver or measured calibration statistics.',
    refs=[REPO+'results/zenith_single_compound/receiver_control.csv'])

add('The result does not establish background monitoring', body=[
    'The example predicts a 95% enhancement limit of 50.58 µg/m³ under its stated model.',
    'An aircraft study reports a selected background of 145 parts per trillion by volume (pptv), about 0.252 µg/m³ at 288.15 K and 101,325 Pa.',
    'The model limit is about 29.1 parts per billion by volume (ppbv) at those conditions, roughly 200 times that mixing ratio.'],
    takeaway='The useful result is an explicit detection calculation with a clear sensitivity limitation.',
    caveat=CONDITION,
    notes='The EMeRGe article uses a winter IAGOS reference from selected aircraft data during 2012–2016. This is not a universal surface concentration. Conversion uses 1 ppbv = 1.73623578 µg/m³ at 288.15 K and 101325 Pa. The comparison is contextual: a selected atmospheric mixing ratio and a modeled differential amplitude with an assumed profile are different observables. Do not describe this benchmark as demonstrated ambient pollution detection.', refs=[S['emerge'],S['tutorial']], source='Ambient context: EMeRGe / IAGOS study · Conditional result: saved zenith experiment')

add('What is needed for a physical demonstration', body=[
    'Measure blank reference/sample stability and spectral covariance with the intended receiver.',
    'Verify the available linear RF power and bandwidth, then test tracking during a moving pass.',
    'Use independent concentration measurements and changing weather to assess false detections.',
    'For 3D reconstruction, add distinct rays and evaluate matrix rank and spatial resolution.'],
    takeaway='LEO links remain a useful example for the complete chain, including its practical limits.',
    caveat='This tutorial models direct transmission. Molecular scattering and multistatic imaging need a separate feasibility study.',
    notes='The present evidence supports a conditional computational example. Future work on molecular scattering must distinguish molecular absorption and emission from elastic scattering, and molecular effects from refractive index turbulence. Multiple receivers alone do not guarantee 3D identifiability. A tomography forward model would use ray lengths and spectral coefficients across voxels and needs adequate angular diversity. The supervisor revision includes a nonresonant scattering screen and a corrected PM extinction analysis.', refs=[S['tutorial'],S['revision']])

add('Appendix · Every entry of a five tone design matrix', table=[['Tone index k', 'aₖ [10⁻⁴ dB/(µg/m³)]', '1', 'uₖ'],
    *[[str(k),f'{row[0]*1e4:.6f}','1',f'{row[2]:.6f}'] for k,row in zip(mini['tone_indices_zero_based'],mini['A'])]], widths=[.22,.38,.12,.28],
    latex=r'\mathbf y_5=\mathbf A_5\begin{bmatrix}q&b_0&b_1\end{bmatrix}^{T}+\boldsymbol\varepsilon_5,\qquad\mathbf A_5\in\mathbb R^{5\times3}',
    legend='The table scales only the a column by 10⁴ for readability. Use its original units in the calculation.',
    caveat='This subset is only an arithmetic illustration. The main result uses all 1,024 tones.',
    notes='The selected zero based tone indices are 0, 255, 511, 767 and 1023. Values come directly from worked_example.json. The full precision arrays are saved there and in matrices.npz. Values displayed here are rounded, so manual reconstruction has rounding error.', refs=[REPO+'results/zenith_single_compound/worked_example.json'])

add('Appendix · The five tone covariance matrix', table=[['C₅ / 10⁻⁴ dB²', '0', '255', '511', '767', '1023'],
    *[[str(k),*[f'{v*1e4:.6f}' for v in row]] for k,row in zip(mini['tone_indices_zero_based'],mini['C'])]], widths=[.24,.152,.152,.152,.152,.152],
    body=['Diagonal entries contain thermal variance and calibration variance.', 'Off diagonal entries come from the assumed correlated calibration residual.'],
    takeaway='C₅ is the corresponding submatrix of the null covariance C(0).',
    caveat='Assumed, unmeasured 0.001 dB differential calibration residual · 20 s total acquisition',
    notes='For example C00 = 0.00029515286513673 dB². The displayed diagonal value is 2.951529 because the table is in units of 10^−4 dB². The first and last off diagonal entry is 3.68238873913915 × 10^−7 dB². The five tone estimator must be recomputed using A5 and C5; simply taking five entries of the full H is not the same estimator.', refs=[REPO+'results/zenith_single_compound/worked_example.json'])

add('Appendix · Multiplication gives the five tone estimate', table=[['Tone index', 'Observed yₖ (dB)', 'Recomputed H₅ weight'],
    *[[str(k),f'{y:.9f}',f'{h:.3f}'] for k,y,h in zip(mini['tone_indices_zero_based'],mini['y'],mini['H'][0])]], widths=[.25,.36,.39],
    latex=r'\widehat q_5=\mathbf H_5\mathbf y_5=171.7494,\quad s_{0,5}=165.1163,\quad\tau_5=384.124\ \mathrm{\mu g/m^3}',
    legend='H₅ weights have units (µg/m³)/dB. Both q̂₅ and s₀,₅ are in µg/m³.',
    takeaway='171.75 < 384.12: this five tone subset does not detect the same simulated sample.',
    caveat='20 s total · ideal tracking · assumed, unmeasured 0.001 dB calibration residual',
    notes='Compute H5 with the same whiten/project method using A5 and C5, then form the dot product with y5. The true enhancement is still 50.5814 µg/m³. Discarding almost all tones gives a much larger uncertainty and this failed decision. The 1024 tone estimate was 39.4247 µg/m³ with threshold 29.6174. The full arrays, not rounded slide values, produce the saved results.', refs=[REPO+'results/zenith_single_compound/worked_example.json'])

add('Appendix · The spacing comparison', table=[['Tones', 'Δf (MHz)', 'CP time (%)', 'ICI at 100 kHz (%)', 'q₉₅ (µg/m³)'],
    *[[r['tones'],f"{float(r['spacing_mhz']):.4f}",f"{float(r['cp_fraction_of_transmitted_time'])*100:.2f}",f"{float(r['cfo_100khz_ici_fraction'])*100:.5f}",f"{float(r['limit_95pct_ug_m3']):.2f}"] for r in spacing]], widths=[.13,.19,.21,.27,.20],
    body=['ICI means interference between tones. It is a separate screen, not included in the ideal q₉₅.'],
    takeaway='1,024 tones give the lowest ideal q₉₅ among these cases with ICI below an illustrative 0.1% cap.',
    caveat=CONDITION,
    notes='All four candidates keep 10 GHz total bandwidth and 25 dBm total RF power. The CP is always 10 ns. ICI is intercarrier interference from the stated residual carrier frequency offset, using a separate analytical screening calculation. The ideal q95 results do not incorporate ICI. Residual 100 kHz and the 0.1% cap are illustrative choices; phase noise and measured channel delay spread remain unknown. Therefore this is a limited trade study, not a global optimum or complete waveform validation.', refs=[REPO+'results/zenith_single_compound/ofdm_spacing.csv'])

power_rows=[r for r in sensitivity if r['comparison']=='Power and calibration, same apertures' and float(r['residual_db'])==.001]
add('Appendix · More RF power helps, conditionally', chart=dict(
    x=[float(r['power_dbm']) for r in power_rows],
    series=[dict(name='Predicted 95% detection concentration', values=[float(r['limit_95pct_ug_m3']) for r in power_rows],color='#126B76')],
    xtitle='Total average RF power (dBm)',ytitle='95% detection concentration (µg/m³)',ymin=0,ymax=140,xmin=15),
    takeaway='25 dBm: 50.58 µg/m³ · 30 dBm: 31.83 µg/m³ · 40 dBm: 18.06 µg/m³\nThe 1 W and 10 W cases are unproven hardware scenarios.',
    caveat=CONDITION,
    notes='All points use the same 10 cm transmit and 1 m receive apertures, 65% efficiencies, 7 dB NF, and 5 dB implementation loss. The 17 dBm point illustrates an 8 dB reduction relative to the 25 dBm design anchor; it is not a required OFDM backoff specification. 30 dBm is 1 W and 40 dBm is 10 W. These last cases are unproven hardware sensitivity scenarios, not demonstrated wideband orbital transmitters. Neither increased power nor averaging removes arbitrary systematic error.', refs=[REPO+'results/zenith_single_compound/sensitivity.csv',S['revision']])

add('Appendix · Calibration and background change the result', table=[['Change from the baseline', 'Predicted concentration scale'],
    ['Zero added calibration residual', 'q₉₅ = 47.40 µg/m³'],
    ['Assumed 0.001 dB residual', 'q₉₅ = 50.58 µg/m³'],
    ['Assumed 0.01 dB residual', 'q₉₅ = 157.79 µg/m³'],
    ['Fit an additional background amplitude', 'Local q₉₅ approximation = 83.63 µg/m³']], widths=[.57,.43],
    takeaway='The error model and nuisance space determine what spectral information remains.',
    caveat='20 s total · ideal tracking · every calibration level is assumed and unmeasured',
    notes='The first three rows use the positive concentration covariance in the saved power and calibration sweep. The last row is explicitly a local constant covariance approximation from background_nuisance.json, so it should not be presented as exactly the same finite q root calculation. A 1% water partial pressure change at fixed temperature and total pressure produces about +0.579 µg/m³ blank bias under the original nuisance model; a +1 K change at fixed total and water partial pressures produces −0.750 µg/m³. These are selected perturbations, not a distribution of real weather or an exhaustive robustness test.', refs=[REPO+'results/zenith_single_compound/sensitivity.csv',REPO+'results/zenith_single_compound/background_nuisance.json',REPO+'results/zenith_single_compound/weather_mismatch.csv'])

motion=read_csv('motion.csv')
add('Appendix · The satellite moves during a measurement', table=[['Time after zenith', 'Elevation', 'Range (km)', 'Doppler at 235 GHz'],
    *[[f"{float(r['seconds_from_zenith']):g} s",f"{float(r['elevation_deg']):.3f}°",f"{float(r['slant_range_km']):.3f}",f"{float(r['doppler_hz'])/1e3:.1f} kHz"] for r in motion]], widths=[.25,.22,.23,.30],
    body=['Doppler is the frequency shift caused by motion between the transmitter and receiver.'],
    takeaway='A coherent 10 s acquisition requires time dependent delay, phase, frequency and gain corrections.',
    caveat='The static sensitivity calculation assumes ideal tracking. It does not establish moving link performance.',
    notes='These are a circular 550 km overhead pass geometry screen using the repository motion model. Doppler signs follow the receding satellite after zenith convention. The calculation omits a full orbit and ground rotation model. At ±5 s around zenith, elevation is about 86.05 degrees. Even near zenith the phase evolves rapidly; an instantaneous zero radial speed does not imply a constant channel over the measurement.', refs=[REPO+'results/zenith_single_compound/motion.csv',S['revision']])

add('Sources · Hardware and atmospheric context', body=[
    'Sen et al. (2023), Nature Electronics. Terrestrial 210–240 GHz link. DOI: 10.1038/s41928-022-00897-6',
    'TeraLink (2026), preprint arXiv:2606.15410v1. Proposed LEO link parameters and qualification scope.',
    'Cooper et al. (2025), IEEE Journal of Microwaves. 240 GHz frequency multiplier source. DOI: 10.1109/JMW.2025.3610360',
    'EMeRGe study (2023), Atmospheric Chemistry and Physics 23, 1893. DOI: 10.5194/acp-23-1893-2023'],
    notes='The full clickable source URLs are listed below. Hardware sources support only their stated evidence scope. The EMeRGe/IAGOS background reference is contextual, not a universal ground concentration.',refs=[S['sen'],S['teralink'],S['cooper'],S['emerge']],source='Primary research sources · Clickable URLs in slide notes and companion notes')

add('Sources · Physics and reproducible calculations', body=[
    'HITRAN molecule 41, CH₃CN. Acquired line parameters and provenance are saved with the experiment.',
    'ITU P.835-7 (2024): reference standard atmosphere. ITU P.676-13 (2022): gaseous attenuation and emission model.',
    'Research snapshot b94f3fe: docs/54 and docs/55 contain the source audit and full derivation.',
    'results/zenith_single_compound contains every tone, A, C, H, observations, sensitivity tables and hashes.'],
    takeaway='Reproduction entry point: scripts/run_zenith_tutorial.py',
    notes='Exact links follow. matrices.npz stores the full A, C and H arrays. worked_example.json stores all entries for the five tone example. manifest.json records inputs, outputs and package versions. HAPI/HITRAN acquisition requirements and the full run command are in docs/55. Presentation preparation reads saved outputs and does not invent a new physical dataset.', refs=[S['hitran'],S['p835'],S['p676'],S['tutorial'],S['revision'],REPO+'results/zenith_single_compound/manifest.json'])

# Keep the five tone threshold tied to the saved uncertainty rather than hand rounding.
from scipy.stats import norm
threshold5=float(norm.ppf(.99)*mini['sd_ug_m3'])
slides[26]['latex']=slides[26]['latex'].replace('384.124',f'{threshold5:.4f}')
slides[26]['takeaway']=f'171.75 < {threshold5:.2f}: this five tone subset does not detect the same simulated sample.'

# Introduce the field before using its vocabulary. Mathematical detail follows.
add('A communication link as a sensing experiment', body=[
    'The transmitter sends a radio signal. The receiver measures how the propagation path has changed it.',
    'This project asks whether those changes also reveal the amount of a gas along the path.',
    'ISAC means integrated sensing and communications: using a communication signal to carry data and obtain information about the environment.'],
    takeaway='Here the transmitter is on a low Earth orbit (LEO) satellite and the receiver is on the ground.',
    caveat='This is a proposed sensing use of the link. Useful atmospheric detection still needs experimental validation.',
    notes='No prior project knowledge is assumed. Radio frequency, abbreviated RF, refers here to the electromagnetic signal sent by the transmitter. At 235 GHz the wavelength is about 1.28 mm, in the subterahertz range used by the project. The satellite is a concrete way to illustrate the entire inference chain. The question is whether the small additional gas signature survives spreading loss, ordinary atmospheric absorption, receiver noise and instrument drift. The example uses known pilot symbols for sensing and leaves the unknown data symbols unused.',refs=[S['tutorial'],S['revision']])

add('Why a molecule can change a radio signal', body=[
    'Acetonitrile, CH₃CN, is the one gas selected for this example.',
    'Its rotational transitions absorb energy at particular frequencies. Pressure and temperature broaden and modify the spectral features.',
    'A spectral template is the calculated attenuation at every measured frequency for one unit of concentration.'],
    takeaway='More gas increases the attenuation according to this template, within the assumed profile.',
    caveat='Other molecules can have overlapping signatures. The first example assumes their concentrations do not change.',
    notes='Absorption is a reduction of the power in the directly received signal. The receiver is not photographing molecules or collecting a reflected image. HITRAN is a spectroscopic database that supplies line frequencies, intensities and broadening data. The calculation combines those data with pressure and temperature along the path. A Voigt line shape convolves Doppler broadening and collision broadening. This slide introduces the physical mechanism; the later integral specifies the model mathematically.',refs=[S['hitran'],S['tutorial']],source='Molecular parameters: HITRAN · Physical model and scope: docs/55')

add('Many frequencies in one transmitted signal', table=[['Term', 'Physical meaning'],
    ['OFDM', 'Orthogonal frequency division multiplexing: many separately recoverable tones'],
    ['Tone / subcarrier', 'One regularly spaced frequency component of the waveform'],
    ['Pilot', 'A transmitted symbol whose amplitude and phase the receiver already knows'],
    ['Bandwidth', 'The total frequency span used at the same time'],
    ['Symbol', 'One time interval over which the tone coefficients are transmitted']],widths=[.26,.74],
    takeaway='Center frequency: 235 GHz. Bandwidth: 10 GHz. The example measures 1,024 tones.',
    notes='Frequency is oscillations per second. GHz means 10^9 Hz. The center frequency says where the band lies, while bandwidth says how wide it is. Orthogonal means the chosen tones have zero cross inner product over the useful symbol interval in the ideal synchronized model. Known pilots let the receiver infer amplitude and phase changes without knowing the gas concentration. A short cyclic prefix is included between useful intervals to accommodate channel delay spread. Doppler shifts from motion and phase noise disturb ideal separation. The receiver also carries data, but this teaching calculation uses only the known pilots.',refs=[S['tutorial']])

add('How to read the radio power units', table=[['Unit', 'Definition or interpretation', 'Example'],
    ['dB', '10 log₁₀ of a power ratio', '+10 dB means ×10 power'],
    ['dBm', '10 log₁₀(P / 1 mW)', '25 dBm ≈ 316 mW'],
    ['dBi', 'Antenna gain relative to an isotropic radiator', 'Directionality, not created energy'],
    ['Attenuation in dB', 'Positive loss subtracted in a link budget', '10 dB loss leaves 10% of the power']],widths=[.2,.46,.34],
    takeaway='Power ratios multiply in linear units and add in decibels. Amplitude ratios use 20 log₁₀.',
    notes='For the same impedance, power is proportional to the square of amplitude. This explains 20 log10 for field amplitude versus 10 log10 for power. Negative dBm means less than 1 mW, not negative power. Antenna gain describes concentrating radiation or collecting an incoming wave, not amplifier output. A link budget is simply the accounting from total transmit power to received power after all gains and losses. Dividing a fixed total power among K equal tones subtracts 10 log10(K) dB per tone. RF average power, electrical input power and radar pulse peak power are distinct.',refs=[S['tutorial'],S['revision']])

amplitude_ratio=10**(-float(observations[0]['true_enhancement_db'])/20)
add('What the receiver is trying to distinguish', table=[['At the first tone, before measurement errors', 'Model value'],
    ['Chosen enhancement q for the worked sample', f"{worked['true_concentration_ug_m3']:.4f} µg/m³"],
    ['Extra molecular attenuation', f"{float(observations[0]['true_enhancement_db']):.6f} dB"],
    ['Sample amplitude / reference amplitude', f'{amplitude_ratio:.6f}'],
    ['Reduction in amplitude', f'{(1-amplitude_ratio)*100:.4f}%']],widths=[.69,.31],
    takeaway='The measurement must distinguish a small molecular change from noise and instrument drift.',
    caveat='This is the predicted molecular effect for the assumed profile, before adding noise. It is not a measured change.',
    notes='Reference means the baseline transmission. Sample means the transmission after a specified concentration enhancement. Both acquisitions have finite thermal noise. The values here are derived from the saved first tone, not invented illustrative observations. The molecular amplitude ratio is 10^(−a_k q/20). The worked sample concentration is a deliberately chosen simulation input, not a claim about typical background air. The detector later combines all frequencies and accounts for uncertainty rather than interpreting this one tone alone.',refs=[REPO+'results/zenith_single_compound/worked_observation.csv',S['tutorial']])
intro=slides[33:]
del slides[33:]
slides.insert(1,intro[0])
slides[3:3]=intro[1:]

assert len(slides)==38
assert len(tones)==len(observations)==1024
assert len(power_rows)==6
for slide in slides:
    assert slide['notes'] and slide['sources']
    if slide['chart']:
        for series in slide['chart']['series']:
            assert len(series['values'])==len(slide['chart']['x'])
(BUILD/'slides.json').write_text(json.dumps(slides,indent=2,ensure_ascii=False),encoding='utf-8')
notes=['# Acetonitrile at 90°: presenter notes','',
       'Research snapshot b94f3fe. All physical detection results are conditional predictions or simulations, not measured field performance.',
       '', 'Audience: mathematically fluent readers with no project or radio engineering background. Slides 1–29 form the main explanation. Slides 30–38 provide arithmetic, sensitivity and sources.', '']
for i,slide in enumerate(slides,1):
    notes += [f"## {i}. {slide['title'].replace(chr(10),' ')}", '',slide['notes'],'']
    if slide['latex']: notes += ['Equation:', '', '$$\n'+slide['latex']+'\n$$','']
    if slide['legend']: notes += [slide['legend'],'']
    if slide['caveat']: notes += ['Condition: '+slide['caveat'],'']
    notes += ['Sources:', '', *[f'- <{url}>' for url in slide['sources']], '']
(OUT/'zenith_acetonitrile_presenter_notes.md').write_text('\n'.join(notes),encoding='utf-8')
print(f'Prepared {len(slides)} slides with saved data, source links and presenter notes')
