# THz sensing

The current September 23, 2026 deliverable is [Limits of Sub-THz VOC and Particulate Sensing with Communication-Pilot Reuse](output/pdf/thz_isac_pollutant_sensing_ieee.pdf). The [five-task results report](docs/40_five_task_closure.md) explains all completed work, maps every task in the original proposal, links evidence and gives reproduction commands.

**The public-data computational assessment is complete; a calibrated atmospheric VOC/PM sensor and environmental compliance are not demonstrated.** New work adds environmental domain/averaging checks, actual OFDM decoding, moving-pass and synchronization controls, PM information diagnosis, a published 380 GHz water comparison and measured public calcite transmission. The practical E-band reference preserves communication under read-only pilot reuse but fails useful joint sensing. Calcite blanks drift by up to 0.090 dB and lack mass/size labels, so these measurements do not calibrate PM concentration.

The [measurement protocol](docs/41_measurement_protocol.md), [empty observation schema](results/five_task_closure/paired_measurement_schema.csv), [verification](results/five_task_closure/verification.json), [current manifest](results/five_task_closure/closure_manifest.json) and [paper build instructions](paper/README.md) accompany the results. Tests and numerical replay do not establish physical truth. Older manifests describe their own snapshots; the current manifest records changed documentation and deliverables.

## Earlier stages and retained evidence

The September 23 completion study extends proposal tasks **1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 3.2 and 4.3** with actual Beijing weather soundings, P.835-7/P.676-13, additional isotopologues, full Mie size distributions, OFDM resources, nonlinear retrieval and explicit detection-limit probabilities. See the [implementation, evidence and remaining physical-validation requirements](docs/38_full_model_completion.md). All evaluated frequencies remain 60-400 GHz.

The [thermal convergence audit](docs/39_thermal_convergence_audit.md) explains the **0.116% failure**, the finer-grid correction to **0.00319%**, why noise and capacity depend on it, and the unchanged **0.1% numerical threshold**. It separately records the stricter family-wise detection threshold. Research decisions, results, retained failures and remaining work are documented in Markdown; machine-readable arrays and tables remain linked evidence.

The latest extension implements **proposal task 1.3 with spherical refracted paths, air/self broadening, Voigt/Lorentz comparisons and numerical convergence checks**, and adds precision/recall, percentage concentration errors and plots. See the [task 1.3 and detection report](docs/37_task_1_3_and_detection_metrics.md). All metrics remain conditional simulation controls in 60–400 GHz.

The September 22 exploratory extension adds **60–400 GHz VOC estimation, joint fine/coarse PM retrieval, and an explicit zero communication-rate-loss check**. It uses newly acquired HITRAN data and retains failed identifiability and propagation scenarios. VOC sensitivities remain conditional; joint PM retrieval is not demonstrated. See the [methods, results, limitations, and reproduction commands](docs/36_voc_joint_pm_capacity.md).

The historical September 8 deliverable is preserved as [its original PDF](paper/history/2026-09-08/main.pdf), with its [claim and evidence ledger](docs/revision_0908.md). The paragraphs below describe that earlier result.

**RESULT.** Constructed an explicit efficient estimator and checked 10,000 Gaussian observations per declared configuration. At 300 coherent pilots, CO has normalized noise error 0.994 and an arbitrary persistent spectral-bias allowance of only 0.000740 dB. At 30,000 pilots the declared combined physical mismatch increases SO2 normalized RMSE from 0.582 to 3.918. [Evidence](results/revision_0908/attainability.csv).

**CLAIM BOUNDARY.** The estimator attains its bound only in the declared unconstrained linear Gaussian model. The observation likelihood, receiver calibration, vertical profiles and simultaneous multiband acquisition remain unvalidated. No measured atmospheric radio attenuation was acquired. [Scope and next steps](docs/revision_0908.md).

Reproduction commands, runtime manifests, validation and retained failures are linked in that ledger. Historical source attribution remains in the [source map](docs/source_map.md); older experiments retain their own assumptions in the manuscript appendices.
