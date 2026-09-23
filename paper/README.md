# THz sensing

The current September 23, 2026 manuscript is **Limits of Sub-THz VOC and Particulate Sensing with Communication-Pilot Reuse**. Read the [six-page PDF](../output/pdf/thz_isac_pollutant_sensing_ieee.pdf) and [five-task evidence report](../docs/40_five_task_closure.md). It covers expanded physics, conditional VOC limits, negative PM/E-band results, OFDM decoding, an ideal moving pass, published water measurements and public calcite transmission. It does not establish measured atmospheric VOC/PM retrieval or environmental compliance.

Build from the repository root with `python scripts/build_current_paper.py`. This generates tables from saved evidence, compiles LaTeX twice and copies the PDF to its stable output path. [main.tex](main.tex) is the entry point; content is in [current_study.tex](current_study.tex). Compilation does not replace visual page inspection.

## Historical September 8 result

The previous source/PDF are preserved under [history/2026-09-08](history/2026-09-08), with the original [revision ledger](../docs/revision_0908.md). The text below describes that earlier result.

**RESULT.** Constructed an explicit efficient estimator and checked 10,000 Gaussian observations per declared configuration. At 300 coherent pilots, CO has normalized noise error 0.994 and an arbitrary persistent spectral-bias allowance of only 0.000740 dB. At 30,000 pilots the declared combined physical mismatch increases SO2 normalized RMSE from 0.582 to 3.918. [Evidence](../results/revision_0908/attainability.csv).

**CLAIM BOUNDARY.** The estimator attains its bound only in the declared unconstrained linear Gaussian model. The observation likelihood, receiver calibration, vertical profiles and simultaneous multiband acquisition remain unvalidated. No measured atmospheric radio attenuation was acquired. [Scope and next steps](../docs/revision_0908.md).

Reproduction commands, runtime manifests, validation and retained failures are linked in that ledger. Historical source attribution remains in the [source map](../docs/source_map.md); older experiments retain their own assumptions in the manuscript appendices.
