> Historical stage. The current results and claim boundaries are in the [targeted follow-up](targeted_followup.md).

# Scientific closure, September 8, 2026

**RESULT.** Implemented atmospheric tangent nuisance projection and tested a frozen nonlinear 27-state mismatch grid. At 30,000 pilots and median concentrations, worst SO2 normalized RMSE falls from 4.487 to 1.136, while CO rises from 0.556 to 1.047 because of noise amplification. [Recorded endpoint](../results/closure_robust_atmosphere/summary.csv); [protocol and provenance](../results/closure_robust_atmosphere/manifest.json).

**INFERENCE / SCOPE.** Bias reduction is not uniform RMSE improvement. None of the gases meets normalized error one over the declared grid under the tangent method. Measured receiver calibration, synchronized attenuation truth and realistic receiver resources remain missing. [Current derivation and limitations](../paper/main.tex); [frozen protocol](../results/closure_robust_atmosphere/protocol.json).

The current [PDF](../paper/build/main.pdf) and [TeX source](../paper/main.tex) replace the earlier entry point. The incoming version is retained in the [portfolio snapshot](../../../00_research_portfolio/results/closure_0908/before_manifest.json).

**RESULT.** Tests, builds, page inspection and artifact hashes are recorded separately in the [validation manifest](../../../00_research_portfolio/results/closure_0908/validation_manifest.json) and [independent verification](../../../00_research_portfolio/results/closure_0908/verification/manifest.json). Earlier result directories are historical evidence and remain available.
