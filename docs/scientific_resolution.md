# Current scientific resolution: THz sensing

**RESULT.** Computed receiver requirements on 202 modeled probes above 5 dB under two likelihoods and four pilot counts. Coherent CO crosses its one-sigma reference at 300 pilots only below 0.00490 dB independent residual; high-resource SO2 is also conditional, while O3 and NO2 remain above their scales. [Run manifest and hashed outputs](../results/resolution_noise_requirements/manifest.json).

**INFERENCE / CLAIM BOUNDARY.** These are local bounds under uncalibrated receiver assumptions. More pilots cost energy and time. Synchronized measured atmospheric attenuation and truth remain missing. [Current manuscript resolution section](../paper/resolution_results.tex).

The protocol and retained results define the scope of the empirical claims. [Frozen protocol](../results/resolution_noise_requirements/protocol.json).

The current manuscript is [this PDF](../paper/build/main.pdf); the executable source is [resolution_results.tex](../paper/resolution_results.tex).

Reproduce from this project directory with Python 3.12 and the recorded dependencies. Set `PYTHONPATH` to `src` and the project directory, `PYTHONUTF8=1`, `OMP_NUM_THREADS=1` and `OPENBLAS_NUM_THREADS=1`. The experiment itself declares any additional workers or Torch threads. [Recorded runtime environment](../results/resolution_noise_requirements/manifest.json).

```text
py -3.12 scripts/run_noise_requirements_resolution.py
```

**SELF-DERIVED.** New mathematical arguments, where applicable, are written in the current resolution section and kept separate from source-paper statements. They inherit the stated assumptions and do not establish broader source theorems. [Derivations and boundaries](../paper/resolution_results.tex).

Current tests, compilation logs and PDF hashes are listed in the [portfolio validation record](../../../00_research_portfolio/results/resolution/validation_manifest.json). The [artifact verification](../../../00_research_portfolio/results/resolution/result_verification/manifest.json) recomputes selected claims from stored raw outputs.

Historical review and repair files preserve their original estimands and run versions; they are not the current delivery manifest. The [before snapshot](../../../00_research_portfolio/results/resolution/before_manifest.json) preserves the previous state.
