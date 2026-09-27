# THz atmospheric sensing: targeted follow-up, September 8, 2026

**SELF-DERIVED. What changed and why.** Hard atmospheric tangent cancellation sacrificed too much target information. The new constrained convex estimator minimizes noise variance plus the largest squared bias over 54 archived atmospheric discrepancies, while retaining target response and the original nuisance cancellation. The finite symmetric convex hull gives an exact worst conditional MSE objective; the numerical implementation is not an interval certificate of optimality. [Derivation](../paper/followup_results.tex), [implementation](../src/thz_isac/bounded_bias.py), [analytic and nuisance tests](../tests/test_bounded_bias.py).

**RESULT. New modeled states.** On 64 fresh atmospheric states, at 30,000 coherent pilots and zero independent random residual, the worst normalized RMSE is:

| Gas | Nominal GLS | Hard tangent | Bounded bias | Bounded states at or below one |
| --- | ---: | ---: | ---: | ---: |
| CO | 0.601 | 1.049 | 0.278 | 64/64 |
| O3 | 2.785 | 2.706 | 1.312 | 0/64 |
| SO2 | 3.294 | 1.182 | 0.738 | 64/64 |
| NO2 | 13.660 | 13.711 | 12.162 | 0/64 |

Every table entry comes from the [held-out summary](../results/followup_bounded_bias/heldout_summary.csv), with its full [state records](../results/followup_bounded_bias/heldout.csv) and [frozen protocol](../results/followup_bounded_bias/heldout_protocol.json). These are nonlinear modeled sensitivity cases using physical spectroscopy and real training-period concentrations, not measured radio retrievals. The perturbation distribution has no calibrated population coverage. [Run assumptions and provenance](../results/followup_bounded_bias/manifest.json).

**RESULT. Resource limits.** Matched thermal noise alone requires at least 46,850 pilots for O3 and 4,416,231 for NO2 under the retained unbiased model and nuisance constraints. The finite bounded-bias design envelope needs about 5.91 million for NO2 at zero random residual. At the separately fixed ten-million-pilot grid point, all four gases pass all 64 new states; ideal simultaneous probing would take ten seconds and 1.995 J at one microsecond per pilot and 23 dBm total transmitted power. NO2 still misses the design target at one billion pilots when independent residual noise is 0.001 dB. [Necessary resources](../results/followup_bounded_bias/necessary_resources.csv), [design thresholds](../results/followup_bounded_bias/requirements.csv), [held-out results](../results/followup_bounded_bias/heldout_summary.csv), [resource assumptions](../results/followup_bounded_bias/protocol.json).

**INFERENCE. Remaining work and next step.** This repairs the CO/SO2 noise penalty in the declared model; it does not establish a realizable four-gas receiver. Synchronized attenuation measurements, receiver calibration, acquisition overhead and coherence over the required interval remain unvalidated. The next experiment needs measured noise and systematic bias before any deployment claim. Persistent spectral-error allowances are separately retained and must not be confused with independent random residual noise. [Scope](../paper/followup_results.tex), [systematic allowances](../results/followup_bounded_bias/systematic_allowances.csv).

Reproduce from this project with `python scripts/followup_bounded_bias.py`; dependencies include CVXPY/CLARABEL. The original unsuccessful dense parameterization is disclosed in the paper, and the successful run retains operators, software, hardware, seed, runtime, memory and hashes. [Requirements](../requirements.txt), [run manifest](../results/followup_bounded_bias/manifest.json), [operators](../results/followup_bounded_bias/inputs.npz).

Current deliverable: [PDF](../paper/build/main.pdf). All project tests and the PDF build pass in the [portfolio validation](../../../00_research_portfolio/results/followup_0908/validation_manifest.json). Independent recomputation and decoding are recorded separately in the [verification checks](../../../00_research_portfolio/results/followup_0908/verification/checks.json). Earlier protocols and failures remain in the [historical ledger](scientific_closure.md).
