# Audit of the 0.116% thermal convergence failure

Date: 2026-09-23. Scope: proposal tasks 1.3 and 2.1, evaluated frequencies **60-400 GHz**. This note records the original failure, the numerical correction, its consequences and the threshold history. The broader eight-task report is [38_full_model_completion.md](38_full_model_completion.md).

## Result and threshold decision

**The acceptance threshold did not change.** It was and remains a relative RMS difference of **0.001**, which is **0.1%**. The original brightness-temperature comparison was **0.115957786%** and failed. Refining the vertical thermal integration reduced the comparison to **0.003185544%**, which passes the same criterion. The discrepancy fell by a factor of **36.40**.

| Quantity | Original relative RMS (%) | Refined relative RMS (%) | Acceptance threshold (%) | Result |
| --- | ---: | ---: | ---: | --- |
| Trace-gas attenuation design | 0.003811015 | 0.003811015 | 0.1 | Passed; unchanged |
| PM attenuation design | 0.022464566 | 0.022464566 | 0.1 | Passed; unchanged |
| Microwave background attenuation | 0.001995302 | 0.001995302 | 0.1 | Passed; unchanged |
| Sky brightness temperature | **0.115957786** | **0.003185544** | **0.1** | **Failed, then passed after refinement** |

Original evidence: [initial_integration_convergence.csv](../results/task_completion/initial_integration_convergence.csv). Final evidence: [integration_convergence.csv](../results/task_completion/integration_convergence.csv). Independently replayed values and link effects: [thermal_convergence_audit.json](../results/task_completion/thermal_convergence_audit.json).

## What the 0.116% actually measures

The convergence statistic compares two numerical evaluations of the same model:

```text
r = ||T_sky(order 2) - T_sky(order 4)||_2 / ||T_sky(order 4)||_2
reported percentage = 100 * r
accept if r < 0.001
```

The vector contains the 512 evaluated channels: 256 broad reference probes between 60 and 400 GHz and 256 contiguous E-band tones near 73.5 GHz. The norm is over that particular channel vector, so the E-band block contributes 256 entries. It is not a uniformly weighted integral over the entire 60-400 GHz interval, a maximum error bound for each channel, or a convergence test for arbitrary frequency grids.

For the initial calculation, `r = 0.0011595778605235367`; multiplying by 100 produces **0.11595778605235367%**, rounded to **0.116%**. Confusing the fraction with the percentage would produce a factor-of-100 error. The result is a quadrature discrepancy, not measured atmospheric error, VOC concentration error, detection recall, or communication-capacity loss.

The 0.1% criterion is a declared numerical acceptance budget for this study, not an ITU-prescribed sensor-accuracy standard. Passing a two-order comparison is evidence of numerical stability on this model/grid; it does not establish absolute accuracy against the atmosphere or exclude a shared discretization bias.

## Cause and correction

The original altitude edges used 1 km spacing through 12 km, 4 km spacing from 12 to 40 km, and 10 km spacing from 40 to 100 km, augmented with atmospheric interfaces. Two and four Gauss points per interval produced 66 and 132 nodes. This was adequate for the saved attenuation integrals but missed the declared tolerance for thermal radiative transfer.

Thermal emission weights each layer's temperature-dependent source by its absorption and by transmission through all lower layers. A smooth total attenuation integral can converge while this temperature-weighted transfer calculation still needs finer vertical resolution. The refinement result supports insufficient thermal-grid resolution as the cause of this numerical failure; no physical parameter was fitted to force agreement.

[refine_task_completion_sky.py](../scripts/refine_task_completion_sky.py) performs the following correction:

1. Preserves the initial manifest, arrays and failed convergence table before replacing any thermal result.
2. Refines the thermal altitude intervals to **100 m from 0 to 20 km** and **500 m from 20 to 100 km**, retaining atmospheric interfaces.
3. Repeats the same spherical refracted path calculation, P.835-7 atmosphere, P.676-13 attenuation and Planck-equivalent LTE source calculation at orders two and four.
4. Saves a separate, replayable thermal grid, including temperatures, path weights and each layer's attenuation.
5. Replaces only `sky_temperature_k` in the existing physics arrays and applies the original **0.001** threshold.

| Quadrature | Initial nodes | Refined thermal nodes | Maximum absolute old-to-refined brightness change |
| --- | ---: | ---: | ---: |
| Order 2 | 66 | 734 | 1.232872285 K |
| Order 4 | 132 | 1,468 | 0.373323317 K |

These maximum old-to-refined changes are different statistics from the relative RMS comparison between orders. The independent verifier checks that **every other field in both physics arrays is exactly unchanged**, including gas, PM and background attenuation. The expensive molecular line integration was already converged and was not recomputed for this correction.

The coarse arrays still contain their original altitude/temperature grids. Their updated `sky_temperature_k` comes from the separate `thermal_order*.npz` grid, as explicitly recorded in the refinement manifest; users must not associate that brightness result with the coarse grid when replaying emission.

## Why this matters for noise, retrieval and capacity

For ground-up layer ordering, the implemented radiative-transfer relation is:

```text
J_nu(T) = (h * nu / k) / expm1(h * nu / (k * T))
T_sky = sum_i J_nu(T_i) * [1 - exp(-tau_i)] * exp(-sum_{j<i} tau_j)
        + J_nu(2.725 K) * exp(-sum_i tau_i)
tau_i = layer_attenuation_dB_i * ln(10) / 10
```

This is Planck-equivalent antenna temperature, not simply the atmospheric kinetic temperature. Its implementation is [microwave_absorption.py](../src/thz_isac/microwave_absorption.py). For this study's receiver, [waveform_link.py](../src/thz_isac/waveform_link.py) uses:

```text
T_receiver = 290 K * [10^(NF_dB / 10) - 1]
N = k * B * (T_sky + T_receiver)
SNR = received_signal_power / N
```

With `NF = 6 dB`, receiver noise dominates much of the sky-temperature change. Nevertheless, numerical error in `T_sky` propagates into noise, per-tone SNR, pilot uncertainty, detection limits and information-rate calculations. Fixing the failed integration removes an avoidable numerical contribution before interpreting those quantities. It does not validate the assumed receiver calibration or pollutant profiles.

The replay quantifies the actual thermal effect using the final power allocation **held fixed in both calculations**, order-four brightness before/after, and unchanged attenuation and radio parameters:

| Band | Rate with initial sky (Mbit/s) | Rate with refined sky (Mbit/s) | Relative rate change (%) | Largest absolute channel noise change (%) |
| --- | ---: | ---: | ---: | ---: |
| Broad multiband reference | 783.513813 | 783.511695 | -0.000270264 | 0.032656357 |
| 73.5 GHz contiguous E-band | 763.440183 | 763.440052 | -0.000017134 | 0.000043134 |

These small changes describe the effect of the numerical correction. They are **not** an incremental sensing penalty: the communication-only and pilot-reuse sensing calculations use the same refined noise, power and required pilots, and still have **0% modeled incremental sensing rate loss**. No result attributes the much larger PM estimation difficulty to this small thermal correction.

## Threshold history: distinguish numerical and detection thresholds

| Criterion | Earlier setting | Current setting | Decision and meaning |
| --- | --- | --- | --- |
| Thermal/gas/PM/background quadrature acceptance in this completion run | Relative RMS < 0.001 = 0.1% | Same | **Unchanged.** Refine the grid after failure; do not relax the tolerance. |
| Detector false-positive budget | The preceding metrics study used 1% per target | This completion study uses 1% family-wise across six reported targets | **Changed intentionally and made stricter:** Bonferroni gives 0.01/6, or approximately 0.1667%, per target. This change is unrelated to the thermal failure. |
| Required power at the reported detection limit | Not an explicit LOD criterion in the preceding precision/recall report | 95% | New explicit operating requirement; checked with exact response controls for the three broad-band reference VOC limits. |
| Minimum single-pilot sensing SNR | 5 dB | 5 dB | Retained selection rule; it is not a proof that other coherent designs below this cutoff cannot work. |
| Numerical rank tolerance in the new nuisance audit | New audit | `rtol = 1e-10` | Declared numerical screening, not an environmental detection threshold. A barely retained direction can still be unusable. |

Thus, “the threshold may have changed” has two distinct answers: **the 0.1% integration threshold did not change; the statistical detection threshold did change its scope from per-target to family-wise control.** Historical detection percentages are therefore not directly comparable without matching the model, nuisance set, resources and false-positive definition. Original results remain in [37_task_1_3_and_detection_metrics.md](37_task_1_3_and_detection_metrics.md).

## Preserved evidence and replay

| Artifact | Purpose |
| --- | --- |
| [physics_initial_manifest.json](../results/task_completion/physics_initial_manifest.json) | Original run and its failed convergence status |
| [physics_initial_order2.npz](../results/task_completion/physics_initial_order2.npz), [physics_initial_order4.npz](../results/task_completion/physics_initial_order4.npz) | Original numerical arrays |
| [initial_integration_convergence.csv](../results/task_completion/initial_integration_convergence.csv) | Failed original threshold check |
| [thermal_order2.npz](../results/task_completion/thermal_order2.npz), [thermal_order4.npz](../results/task_completion/thermal_order4.npz) | Finer grids, temperatures, layer optical depths and brightness |
| [physics_order2.npz](../results/task_completion/physics_order2.npz), [physics_order4.npz](../results/task_completion/physics_order4.npz) | Retained physics with refined sky temperature |
| [physics_manifest.json](../results/task_completion/physics_manifest.json) | Refinement method, source hash and final convergence status |
| [thermal_convergence_audit.json](../results/task_completion/thermal_convergence_audit.json) | Independent threshold, transfer, array-preservation and link-impact checks |
| [completion_manifest.json](../results/task_completion/completion_manifest.json) | Hashes of completed artifacts, code, inputs and Markdown documentation |

The initial driver deliberately stopped with **“Refine integration before retrieval”** when the gate failed. The subsequent refinement passed before the retrieval calculation proceeded. The original failure was not removed or relabelled as successful.

[verify_task_completion.py](../scripts/verify_task_completion.py) independently recomputes the original discrepancy, checks identical 0.001 thresholds in the original/final tables, checks exact preservation of nonthermal arrays, and replays emission using a **top-to-bottom recursive transfer calculation**. The production routine uses a vectorized layer sum; agreement between the two formulations provides an additional implementation check. The full repository suite passes **191 tests**, including the independent isothermal-slab thermal limit; see [final_pytest.txt](../results/task_completion/final_pytest.txt).

```powershell
# From the repository root with the scientific environment active:
$env:PYTHONPATH="$PWD\src;$PWD\scripts;$PWD"
python scripts/verify_task_completion.py
```

To reproduce from acquired inputs, follow the full ordered commands in the [completion report](38_full_model_completion.md). After a fresh coarse physics run, run `refine_task_completion_sky.py` before retrieval. On the already refined snapshot, that script recognizes the recorded correction and leaves the retained artifacts unchanged.

## Remaining limitations and next steps

The thermal model assumes the declared clear-sky, horizontally homogeneous atmosphere and LTE emission. It does not add measured clouds/rain, antenna spillover, surface pickup, calibrated hardware response, or observed VOC/PM profiles. Quadrature convergence cannot close those physical gaps.

The next steps are to repeat convergence checks whenever the atmosphere, elevation, frequency grid or transfer physics changes, then validate brightness/noise against suitable calibrated observations. The eight-task report records the separate measurement and instrument requirements. Any future change to the acceptance criterion must be recorded with its reason and a separate before/after comparison; it must not rewrite this failed run's history.
