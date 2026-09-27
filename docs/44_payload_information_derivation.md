# Payload information and finite reference derivation

## Purpose and model

This extends original proposal Task 4.1 beyond an estimator specific variance. The received complex subcarrier sample is `y = sqrt(S) x + w`, where `x` is equiprobable unit modulus QPSK and `w ~ CN(0,V)`. Samples are independent. Signal power and complex noise variance are both unknown; define `u = log(S)`, `v = log(V)`, `s = S/V` and `k = 10/log(10)`. Attenuation is `A = -k log(S/Sref)` in dB. This is a local regular estimation model. A Cramér–Rao bound is not a universal classification limit or a guarantee on finite sample mean squared error of biased estimators.

The complete constellation likelihood and the magnitude likelihood have different information. The full constellation calculation assumes a constant or tracked phase within an estimation block. An unknown constant phase has zero cross information with power and noise by reflection and axis exchange symmetry. Arbitrary untracked symbol phases require the magnitude observation. M2M4 itself is invariant to such phases.

## Full QPSK likelihood

Each Cartesian coordinate is a symmetric BPSK mixture with amplitude `a = sqrt(S/2)` and real noise variance `V/2`:

`p(r) = exp(-(r²+a²)/V) cosh(2ar/V) / sqrt(pi V)`.

Its scores for `(u,v)` are

`g_u = -a²/V + (ar/V)tanh(2ar/V)`,

`g_v = -1/2 + (r²+a²)/V - (2ar/V)tanh(2ar/V)`.

The two independent axes give `J_QPSK = 2 E[g gᵀ]`. Evenness permits integration under one mixture component. The implementation uses Gauss–Hermite quadrature with 256 points and checks it against 512 points. Independent tests differentiate library mixture densities numerically and integrate adaptively, without reusing these scores.

## Magnitude likelihood

For `q = |y|²`,

`p(q) = exp(-(q+S)/V) I0(2 sqrt(qS)/V) / V`.

Write `t = 2 sqrt(qS)/V` and `R = I1(t)/I0(t)`. The scores are

`g_u = -S/V + tR/2`,

`g_v = -1 + (q+S)/V - tR`.

The implementation integrates radius rather than squared radius, uses exponentially scaled Bessel functions, and covers `[max(0,sqrt(s)-10), sqrt(s)+10]` in units `sqrt(V)`. The omitted tails are negligible at the evaluated SNRs. Quadrature refinement and differentiation of SciPy's independent Rice density verify the result.

## Profiling receiver noise and the reference

The efficient signal power information per sample is the Schur complement

`j = J_uu - J_uv²/J_vv`.

The local attenuation variance bound for `N` samples and an exactly known reference is `k²/(N j)`. Known transmitted symbols give the favorable oracle `2 k²/(N s)`. The M2M4 estimator has asymptotic variance

`k² (2/s + 1/s² + 4/s³ + 1/s⁴)/N`.

The evaluated information order is therefore

`known symbols bound <= full QPSK bound <= magnitude bound <= M2M4 variance`.

An independent finite reference has unknown baseline power and a separately unknown noise variance. Profiling the baseline adds the two local variance bounds:

`Var(Ahat) >= k² [1/(Ns js) + 1/(Nr jr)]`.

A direct inverse of the joint four parameter Fisher matrix, with coordinates `(A, log(Sref), log(Vs), log(Vr))`, independently verifies this expression. Equal SNRs and a fixed total sample budget give an optimal equal reference/sample split. At unequal SNR, optimal allocation is proportional to the square roots of the per sample variances. No acquisition time is free. A stable but unknown reference abundance permits enhancement retrieval; an absolute concentration still requires independent baseline truth.

## Joint concentrations and spectral nuisance

The local dB mean is `D theta + B beta`, with three VOCs and two PM modes in `theta`. Nuisance columns contain gain, atmospheric background amplitude, and four interfering gases. Per tone efficient likelihood information determines a diagonal equivalent covariance. Whiten the designs by that covariance, project out the whitened nuisance span, and invert target information using normalized SVD. This profiles noise, reference and spectral nuisance in succession. PM10 is the sum of both fitted PM modes and includes their covariance.

The comparison reports `CRLB variance / M2M4 variance` after this joint inversion, rather than treating M2M4's own variance as the fundamental bound. Correlated differential calibration residuals belong to a separate Gaussian sensitivity model; the likelihood CRLB curves are thermal only.

## Detection limits and validation

Six simultaneous outputs use the fixed threshold `zc = Phi^-1(1-0.01/6)`. The local normal 95% power limit is `(zc + Phi^-1(0.95)) sd0`. Signal attenuation changes the positive distribution's SNR. The response limit therefore solves

`c = zc sd0 + Phi^-1(0.95) sd_positive(c)`

before Monte Carlo validation. The sample and independent reference each contribute their actual M2M4 variance. The estimator and null threshold remain fixed. Limits outside a declared 1 dB peak absorption domain are left unavailable, rather than extrapolated silently. Formal PM limits are local diagnostics only and are not validated high concentration performance claims.

All 30 weather/elevation cases are screened by the fixed 5 dB and 20 usable tone gate. Every eligible case is checked at 20 seconds total acquisition, with 10,000 independent null draws and 10,000 draws for each VOC at its predicted limit. Rejected operating points remain explicit. These controls simulate the joint sample moment distribution followed by nonlinear inversion. The earlier raw symbol check validates that approximation; the new study does not represent all millions of payload samples explicitly. No threshold or frequency is fitted to these trials.

## Scientific scope, remaining work and next step

The implementation and numerical results are recorded in [the results note](45_payload_bounds_results.md), with hashed input and output records in `results/payload_bounds`. Public weather supplies pressure, temperature and humidity, not pollutant labels. Vertical pollutant profiles, aerosol composition, Gaussian receiver noise and calibration stability remain assumptions. Geometry is assessed both at fixed elevations and through integrated moving pass information with ideal normalization. Raw moving waveform synchronization and normalization remain Task 2.2 work.

The main follow-up is an implementable band and reference design. If M2M4 is already close to the full likelihood bound, replacing the estimator alone cannot plausibly recover the missing orders of magnitude in PM or weak methanol information. Independent measurements are needed to test the assumed noise and calibration model.

## Primary references

- [Brännström and Rasmussen, 2005, non data aided AWGN parameter estimation](https://arxiv.org/abs/cs/0509007): likelihood and Cramér–Rao framework for unknown BPSK data. QPSK factorization and finite reference extension above are derived explicitly for this study.
- [Gudbjartsson and Patz, 1995, Rician distribution](https://pmc.ncbi.nlm.nih.gov/articles/PMC2254141/): magnitude of a complex Gaussian observation. Its real component variance is `V/2` under this document's convention.
- [Romano, 2021, M2M4 asymptotic efficiency](https://doi.org/10.3390/s21154950): established moment estimator context. This repository's variance and likelihood comparison use the declared random QPSK model.
