# Remaining work against the original proposal

Date: September 27, 2026. This audit compares the two page [original proposal](../I2R_proposal_THz_ISAC%20(1).pdf), the [September 23 task mapping](40_five_task_closure.md), and the [new payload sensing results](42_payload_recall.md). Updated after the [payload bounds, sensitivity and limit study](45_payload_bounds_results.md); its computational extensions of Tasks 4.1–4.3 are now implemented.

**Receiver follow-up:** The [new implementation and findings](47_receiver_design_and_calibration.md) add a sequential frequency plan, exact spectra, raw moving coded OFDM controls, nonzero calibration Monte Carlo, inverse calibration requirements and a charged communication scheduling comparison. These address the computational design gaps below within a declared receiver model. RF power/noise capability, relative gain stability, wideband timing effects and independent physical validation remain open. PM remains a negative feasibility finding. No experimental calibration accuracy is claimed.

## What was checked and why

The proposal has 11 numbered tasks. Its modeling and simulation requirements must be distinguished from successful pollutant retrieval and the further evidence needed for a validated instrument. The new payload method also needs extensions of analyses previously completed for pilots. Historical task entries 1.5, 3.3 and 4.4 are optional additions rather than original requirements.

## Current result

| Original task | Existing evidence | Remaining work |
|---|---|---|
| 1.1 Atmospheric layers | Standard atmosphere and measured weather profiles implemented. | No missing core implementation. Pollutant vertical profiles remain assumed and limit interpretation. |
| 1.2 HITRAN extraction | Target VOC and interfering gas spectra acquired, inventoried and checked. | Retain three unavailable requests and spectroscopy uncertainty gaps; they are not zero absorption. No missing core extraction pipeline. |
| 1.3 Voigt/Lorentz slant integration | Spherical refracted paths, line shapes and convergence checks implemented. | No missing core implementation. Independent column measurements would strengthen validation. |
| 1.4 PM scattering baseline | Rayleigh and full Mie size distribution calculations implemented. | Target optical properties, composition and humidity response remain uncalibrated. This model exists even though useful mass retrieval fails. |
| 2.1 Link parameterization | Link budget and an explicit E-band OFDM configuration implemented. | Specify an implementable multiband configuration that retains the new sensing benefit: frequency blocks, RF chains or retuning, power, bandwidth and acquisition time. Existing E-band fails useful sensing. This closes the architecture gap between the abstract's goal and the ideal broad reference. |
| 2.2 CSI synthesis | Complex pilot and FFT/CP waveform simulations implemented. | Integrate payload retrieval over a changing satellite path, including gain normalization, synchronization and reference timing. The current favorable payload experiment assumes stationary reference magnitude. |
| 3.1 Spectral isolation | Gas/background/PM nuisance projection and identifiability diagnostics implemented. | Useful simultaneous gas and PM discrimination remains unresolved; PM signals are too weak and nearly collinear in the evaluated design. |
| 3.2 Parameter estimation | Statistical and nonlinear estimators evaluated; payload method substantially improves selected VOC controls. | Methanol at 1 µg/m³ and useful PM density retrieval remain weak. The finite reference experiment detects enhancement; absolute concentration requires baseline knowledge. A justified negative feasibility conclusion can satisfy an assessment, but it is not successful joint retrieval. |
| 4.1 Analytical lower bound | Full QPSK and magnitude likelihood Fisher bounds now profile unknown noise and finite reference power, with joint spectral nuisance and M2M4 efficiency comparisons. Independent density and joint Fisher inverse checks pass. | The computational extension is implemented. Scope remains local regular estimation under the declared likelihood; receiver model validation requires measurements. |
| 4.2 Sensitivity | Payload elevation, recomputed SNR, five atmospheric profiles, noise, duration and differential residual sweeps now charge both reference and sample. Moving pass information is integrated with convergence checks. | The computational sensitivity extension is implemented. Unknown weather, actual gain normalization and synchronization remain unresolved; moving waveform implementation belongs to Task 2.2. |
| 4.3 ppm/mass floors and standards | Payload limits now include surface equivalent ppm, nonlinear response validation at predicted limits, averaging/domain checks and a retained negative/unverified standards assessment. | The computational reporting extension is implemented. Absolute concentration needs baseline truth, PM remains impractical and positive environmental compliance remains unverified. |

The proposal's abstract also asks for sensing without communication capacity degradation. Existing controls preserve the same transmitted resources and uncoded QPSK decisions. A useful multiband sensing architecture still needs the same resource comparison, and QPSK throughput must not be equated with Gaussian input Shannon capacity. This is an overarching objective, not a twelfth numbered task.

## Scope and limitations

Task 2.2 explicitly requests simulated CSI. Real atmospheric radio data are therefore a further validation milestone, rather than an entirely missing simulation implementation. Likewise, Task 3.2 lists curve fitting, ratiometric inversion and machine learning as alternative approaches; a neural network is not mandatory.

Calibration recordings and independent gas/PM truth are needed to promote the favorable simulated recall to an experimental performance claim. They are especially material to Task 4.3's stated compliance ambition. The [measurement protocol](41_measurement_protocol.md) defines the required data. There is currently no basis for a positive compliance statement.

## Next steps

1. Use the completed payload bound and sensitivity/floor evaluation for design decisions. M2M4 is already close to the full QPSK bound at the reference state, limiting gains available from estimator replacement alone.
2. Use the evaluated sequential band/resource design and bounded moving receiver as the engineering baseline. Resolve its RF power/noise and relative gain requirements, fractional timing and wideband Doppler effects. Its passive sensing preserves decoded packets on the same hopping schedule, but retuning has a nonzero cost against a fixed band; zero architecture cost is not established.
3. Resolve the joint sensing outcome: either obtain useful PM information under a justified design, or retain an explicit limitation/negative result for Tasks 3.1 and 3.2. Separate any benefit supplied by auxiliary sensors from information in the radio observation.
4. Validate the selected configuration with independent calibration and concentration truth when suitable measurements become available.

The original audit only changed the completion interpretation. This update incorporates new scientific code, physical integrations, response experiments and numerical verification, documented in the new results note. Historical experiment snapshots remain intact.

The [20 s, 0.0001 dB extension](48_expanded_voc_pm_and_20s_calibration.md) adds two HITRAN VOCs to joint inference and evaluates PM1/fine/coarse size separation. Additional unknown gases reduce acetonitrile recall; the three-size inverse problem fails the numerical acceptance gate. These retained failures further qualify the frozen receiver design.
