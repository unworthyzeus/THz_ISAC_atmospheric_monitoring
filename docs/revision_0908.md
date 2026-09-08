# Scientific revision: THz sensing, September 8, 2026

**RESULT.** Constructed an explicit efficient estimator and checked 10,000 Gaussian observations per declared configuration. At 300 coherent pilots, CO has normalized noise error 0.994 and an arbitrary persistent spectral-bias allowance of only 0.000740 dB. At 30,000 pilots the declared combined physical mismatch increases SO2 normalized RMSE from 0.582 to 3.918. [Primary evidence](../results/revision_0908/attainability.csv); [supporting artifact](../results/revision_0908/physical_mismatch.csv).

**WHY AND CHANGE.** A local information lower bound was not an attained error, and independent random residual variance was being interpreted too easily as a calibration requirement. The primary paper now derives the nuisance-eliminating estimator, fixed-covariance attainability, exact bias and variance, a targetwise worst-case systematic-error allowance, and explicit pilot time and energy. Physical mean mismatch and correlation sensitivity are separate experiments. Earlier studies appear as supporting appendices. [Current manuscript source](../paper/main.tex).

**INFERENCE / CLAIM BOUNDARY.** The estimator attains its bound only in the declared unconstrained linear Gaussian model. The observation likelihood, receiver calibration, vertical profiles and simultaneous multiband acquisition remain unvalidated. No measured atmospheric radio attenuation was acquired. [Declared manuscript assumptions](../paper/main.tex).

**INDEPENDENT CHECK.** A separate full weighted-design pseudoinverse reproduces the estimator covariance with maximum relative discrepancy 1.01e-12. Four analytical estimator regression tests cover confounding, nuisance projection, covariance and attained bias. [Independent check](../results/revision_0908_validation/verification.json); [tests](../tests/test_attainable_estimation.py).

**REMAINING WORK AND NEXT STEP.** Acquire synchronized attenuation and concentration or column truth, with a separate calibration period and a realizable frequency/power/timing allocation. Specify concentration averaging times and acceptance errors before evaluating that new period. [Current claim boundaries](../paper/main.tex).

The primary deliverable is [the current PDF](../paper/build/main.pdf). Prior results retain their original protocols in the appendices and archived ledgers; they do not supersede this revision. [Incoming snapshot](../results/revision_0908_validation/before_manifest.json).

Execution metadata, versions, seeds where applicable, runtime, sampled memory and hashes are recorded in the [run manifest](../results/revision_0908/manifest.json). [Declared protocol](../paper/main.tex).

Reproduce numerical work with Python 3.12 and the recorded dependencies. From the project directory set `PYTHONPATH` to its `src` and root directories, `PYTHONUTF8=1`, `OMP_NUM_THREADS=1` and `OPENBLAS_NUM_THREADS=1`. Commands explicitly marked otherwise run from `C:/Research`.

```text
py -3.12 scripts/run_attainability_0908.py
```

Current test and build results are in the [validation record](../results/revision_0908_validation/validation.json). Independent THz estimator algebra is checked in the [verification manifest](../results/revision_0908_validation/verification.json). Failed and incomplete attempts remain in the [attempt ledger](../results/revision_0908_validation/attempts.json).
