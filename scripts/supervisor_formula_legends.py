"""Slide-specific notation legends, indexed by final slide number."""

LEGENDS = {
    2: [
        'a: measured attenuation vector (dB)\nD: target spectral response matrix\nc: target concentrations (µg/m³)',
        'N: background / instrument response matrix\nβ: nuisance parameter vector\nD c and N β: attenuation contributions (dB)',
        'e: measurement error vector (dB)\nBold letters: vectors or matrices\nMatrix products sum spectral contributions',
    ],
    6: [
        's: gas species index\nz: altitude (m)\nn_s(z): molecular number density (m⁻³)\nc_s,0: surface mass concentration (kg/m³)',
        'N_A: Avogadro constant (mol⁻¹)\nM_s: gas molar mass (kg/mol)\nH_s: assumed concentration scale height (m)\nexp: exponential function',
        'P(z): atmospheric pressure (Pa)\nT(z): atmospheric temperature (K)\nρ_H₂O(z): water vapour mass density (kg/m³)\nConvert µg/m³ to kg/m³ before substitution',
    ],
    7: [
        'c(z): mass concentration at altitude z\nc₀: surface mass concentration\nc and c₀ use the same mass / volume units',
        'z: altitude (m)\nH: assumed concentration scale height (m)\nexp: exponential function',
        'ĉ₀: estimated surface mass concentration\nHat: estimated quantity\n⇒: implication under the assumed profile',
    ],
    8: [
        's: species index, ℓ: spectral line index\nν: spectral frequency, ν_ℓ: line centre\nz: altitude (m)\nσ_s: molecular absorption cross section (m²)',
        'S_ℓ(T): integrated line strength at T\nV_ℓ: normalized Voigt line profile\nS_ℓ × V_ℓ has cross section units\nUse matching spectral units for S_ℓ and V_ℓ',
        'T(z): atmospheric temperature (K)\nP(z): atmospheric pressure\nδ_ℓ: line shift per unit pressure\nδ_ℓ P(z): pressure shift in frequency units',
    ],
    10: [
        's: gas species, ν: frequency\nA_s and A: power attenuation (dB)\nn_s: molecular number density (m⁻³)\nσ_s: molecular cross section (m²)',
        'ds: differential path length along ray (m)\nP_in and P_out: input and output power (W)\nz: altitude (m)\nln: natural logarithm',
        'b: conserved spherical ray invariant (m)\nn(r): refractive index at radial distance r\nr: distance from Earth’s centre (m)\nζ: local zenith angle',
    ],
    11: [
        'T_sky: equivalent sky noise temperature (K)\nν: frequency (Hz)\nT_i: physical temperature of layer i (K)',
        'J_ν(T): Planck brightness temperature (K)\nτ_i: dimensionless optical depth of layer i\ni: emitting layer, j: intervening layer',
        'j < i: layers between layer i and receiver\nT_space: space background temperature (K)\nexp(−τ): power transmission through a layer',
    ],
    12: [
        'κ_ext, κ_abs, κ_sca: mass coefficients\nExtinction, absorption, scattering (m²/kg)\nC_ext(r): particle extinction cross section (m²)\np(r): particle number distribution in radius\nr: physical particle radius (m)',
        'ρ: particle material density (kg/m³)\nk = 2π/λ: electromagnetic wavenumber (m⁻¹)\nλ: wavelength in the surrounding medium (m)\nq = (m² − 1)/(m² + 2): contrast factor\nm: complex relative refractive index',
        'Im(q): imaginary part of q\n|q|²: squared complex magnitude\ndr: radius integration element (m)\n≃: Rayleigh approximation for small particles\nThe two final terms describe one radius r',
    ],
    13: [
        'PM₁₀: total fine plus coarse mass (µg/m³)\nc_fine: modeled PM2.5 mass (µg/m³)\nc_coarse: modeled 2.5–10 µm mass (µg/m³)',
        'Var: variance of a concentration estimate\nCov: covariance between the two estimates\nAll variance terms have units (µg/m³)²',
        'Fine and coarse bins are disjoint\nPM₁₀ = c_fine + c_coarse\nTheir covariance must enter the total error',
    ],
    14: [
        'ν: frequency (Hz), λ: wavelength (m)\nP_t, P_r: transmit and received power (W)\nG_t, G_r: antenna power gains (linear)\nL_impl: implementation loss (linear)\nR: propagation distance (m)',
        'A(ν): atmospheric attenuation (dB)\nSNR: signal to noise power ratio (linear)\nk: Boltzmann constant (J/K)\nB: receiver noise bandwidth (Hz)\nT_sky: sky noise temperature (K)',
        'T₀: receiver noise reference temperature (K)\nF: receiver noise factor (linear)\nF = 10^(noise figure in dB / 10)\nT₀(F − 1): receiver noise temperature (K)\nGains and losses must be converted from dB',
    ],
    15: [
        'R̄: average Gaussian information rate (bit/s)\nb: selected frequency block index\nk: tone index within block b',
        't_b: transmission time in block b (s)\nt_total: total acquisition time (s)\nt_b / t_total: block’s time fraction',
        'Δf: bandwidth per tone (Hz)\nSNR_k: tone signal to noise ratio (linear)\nlog₂: base two logarithm',
    ],
    16: [
        'k: tone index, n: time sample index\nx_k: transmitted tone symbol\ny_k: received tone symbol\nh_k: complex channel coefficient',
        'w_k: additive complex receiver noise\nV_k: noise variance in symbol power units\nCN(0,V_k): circular complex Gaussian noise\nIts real / imaginary variances are V_k / 2',
        'X_k: frequency domain OFDM symbols\nx[n]: transmitted time domain samples\nIFFT: inverse fast Fourier transform\nh_k scales amplitude and rotates phase',
    ],
    17: [
        'f_D: Doppler frequency shift (Hz)\nf_c: carrier frequency (Hz)',
        'v_r: signed radial relative velocity (m/s)\nc: speed of light (m/s)',
        '≃: first order narrowband approximation\nThe shift sign follows the velocity convention',
    ],
    18: [
        'a: attenuation vector (dB), e: error (dB)\nD: target response matrix\nc, ĉ: true / estimated concentrations (µg/m³)\nN β: nuisance attenuation contribution (dB)',
        'C = Cov(e): observation covariance (dB²)\nN: nuisance response matrix\nβ: nuisance coefficients\nQ_N: orthonormal whitened nuisance basis',
        'P: projector away from nuisance space\nI: identity matrix, T: matrix transpose\nH: linear concentration retrieval operator\nBold symbols denote vectors or matrices',
    ],
    20: [
        'M₂: second moment E[|y|²]\nM₄: fourth moment E[|y|⁴]\ny: received complex symbol\nE: expectation, |y|: complex magnitude',
        'S: received signal power\nV: receiver noise power\nM₂, S, V share power units\nM₄ has squared power units',
        'A: differential attenuation (dB)\nS_sample: signal power in sample observation\nS_reference: signal power in reference\nlog₁₀: base ten logarithm',
    ],
    23: [
        'y: observed signal data\nθ: complete unknown parameter vector\np(y;θ): likelihood of the observations\nE: expectation under the assumed model',
        'J_ab: Fisher information entry for θ_a, θ_b\nc: target concentration vector (µg/m³)\nη: nuisance parameter vector\nJ_cc, J_cη, J_ηη: Fisher matrix blocks',
        'J_eff: information after nuisance profiling\nĉ: estimated concentration vector\nCov(ĉ): estimator covariance, units (µg/m³)²\n−1: matrix inverse, ⪰: covariance lower bound',
    ],
    24: [
        'Efficiency: lower bound / estimator variance\nDisplayed percentage = 100 × this ratio',
        'Variance lower bound: conditional CRLB\nCRLB: Cramér–Rao lower bound',
        'Estimator variance: variance of M2M4 output\nBoth variances use the same concentration units²',
    ],
    25: [
        'C: attenuation covariance matrix (dB²)\nt: total reference plus sample time (s)\nt / 2: time assigned to each observation\nV_sample, V_reference: variance vectors (dB²)',
        'diag: diagonal matrix built from a vector\nσ_cal: persistent residual standard deviation (dB)\nK: dimensionless spectral correlation matrix\nK_ij: correlation of frequency bins i and j',
        'ν_i, ν_j: bin frequencies in matching units\n10 GHz: assumed spectral correlation length\nexp: exponential function\nσ_cal² K: persistent covariance contribution',
    ],
    28: [
        'Φ⁻¹: inverse standard normal CDF\nz: dimensionless null detection threshold\n0.01: family false alarm probability budget\n8: number of reported outputs',
        'ĉ_j: estimate for target j (µg/m³)\ns_null: standard deviation under the null\ns_positive(c): standard deviation at mass c\nBoth standard deviations use µg/m³',
        'c₉₅: concentration for 95% recall (µg/m³)\n1.64485: Φ⁻¹(0.95), a normal quantile\n>: target detection decision\nThe variance depends on positive concentration',
    ],
    30: [
        'χ_ppm: gas mole fraction in ppm\nc: gas mass concentration in µg/m³\nM: gas molar mass in g/mol',
        'R: ideal gas constant, 8.314 J/(mol K)\nT: local absolute temperature (K)\np: local atmospheric pressure (Pa)',
        '1 ppm = 10⁻⁶ mol/mol\nThe stated mass units cancel the 10⁶ factor\nThis gas conversion does not apply to PM',
    ],
    31: [
        'b_i: persistent bias in attenuation bin i (dB)\nε: upper bound on each |b_i| (dB)\ni: spectral bin, j: retrieved target',
        'H_j: row j of the concentration operator\n‖H_j‖₁: sum of absolute row coefficients\nB_j: resulting concentration bias bound (µg/m³)',
        's_j: concentration standard deviation (µg/m³)\nz: null threshold, 1.64485: 95% normal quantile\nc₉₅,protected: bias protected limit (µg/m³)\n≃: local approximation with constant variance',
    ],
}
