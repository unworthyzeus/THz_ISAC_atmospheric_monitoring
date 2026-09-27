# THz sensing

**Critical assumption:** Favorable results require zero residual calibration error after correction, which has not been demonstrated experimentally. See the [permanent calibration note and retained sensitivity results](../docs/46_critical_calibration_assumption.md).

The current September 27, 2026 manuscript is **Sub-THz Atmospheric Sensing with Pilot and Payload Reuse: Recall Gains and Calibration Limits**. Read the [PDF](../output/pdf/thz_isac_pollutant_sensing_ieee.pdf) and [payload recall report](../docs/42_payload_recall.md). The new section derives passive QPSK moment sensing and reports 99.955% conditional acetonitrile recall at 1 µg/m³ and 10 s, finite reference results and calibration failures. The [preceding evidence report](../docs/40_five_task_closure.md) retains the physical model, PM/E-band limitations and public measurement checks. Atmospheric VOC recall remains simulated.

The [payload information and sensitivity extension](../docs/45_payload_bounds_results.md) adds Tasks 4.1–4.3: unknown noise and finite reference bounds, weather/elevation sensitivity, moving geometry information, and detection limits with ppm conversion. M2M4 is close to the full likelihood bound in the 45° reference; calibration and realizable spectral resources remain the priorities.

Build from the repository root with `python scripts/build_current_paper.py`. This generates tables from saved evidence, requires successful payload verification, compiles LaTeX twice and copies the PDF to its stable output path. [main.tex](main.tex) is the entry point; content is in [current_study.tex](current_study.tex), [payload_recall.tex](payload_recall.tex) and [payload_bounds.tex](payload_bounds.tex). The latest build and deliverable records are in `results/payload_bounds/report`. Compilation does not replace visual page inspection.

## Historical September 8 result

The previous source/PDF are preserved under [history/2026-09-08](history/2026-09-08), with the original [revision ledger](../docs/revision_0908.md). The text below describes that earlier result.

**RESULT.** Constructed an explicit efficient estimator and checked 10,000 Gaussian observations per declared configuration. At 300 coherent pilots, CO has normalized noise error 0.994 and an arbitrary persistent spectral-bias allowance of only 0.000740 dB. At 30,000 pilots the declared combined physical mismatch increases SO2 normalized RMSE from 0.582 to 3.918. [Evidence](../results/revision_0908/attainability.csv).

**CLAIM BOUNDARY.** The estimator attains its bound only in the declared unconstrained linear Gaussian model. The observation likelihood, receiver calibration, vertical profiles and simultaneous multiband acquisition remain unvalidated. No measured atmospheric radio attenuation was acquired. [Scope and next steps](../docs/revision_0908.md).

Reproduction commands, runtime manifests, validation and retained failures are linked in that ledger. Historical source attribution remains in the [source map](../docs/source_map.md); older experiments retain their own assumptions in the manuscript appendices.
