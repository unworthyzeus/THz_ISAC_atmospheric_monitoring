# THz sensing

The current September 8 deliverable is the [revised PDF](build/main.pdf), with its [claim and evidence ledger](../docs/revision_0908.md).

**RESULT.** Constructed an explicit efficient estimator and checked 10,000 Gaussian observations per declared configuration. At 300 coherent pilots, CO has normalized noise error 0.994 and an arbitrary persistent spectral-bias allowance of only 0.000740 dB. At 30,000 pilots the declared combined physical mismatch increases SO2 normalized RMSE from 0.582 to 3.918. [Evidence](../results/revision_0908/attainability.csv).

**CLAIM BOUNDARY.** The estimator attains its bound only in the declared unconstrained linear Gaussian model. The observation likelihood, receiver calibration, vertical profiles and simultaneous multiband acquisition remain unvalidated. No measured atmospheric radio attenuation was acquired. [Scope and next steps](../docs/revision_0908.md).

Reproduction commands, runtime manifests, validation and retained failures are linked in that ledger. Historical source attribution remains in the [source map](../docs/source_map.md); older experiments retain their own assumptions in the manuscript appendices.
