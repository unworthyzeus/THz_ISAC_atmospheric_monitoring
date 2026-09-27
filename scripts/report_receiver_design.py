"""Generate the engineering report from retained numerical evidence."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design'


def main():
    verify = json.loads((OUT/'verification.json').read_text())
    if verify['status'] != 'passed':
        raise RuntimeError('Verify the evidence before reporting it')
    moving = json.loads((OUT/'moving_waveform_summary.json').read_text())
    power = pd.read_csv(OUT/'nonzero_calibration_validation.csv')
    response = pd.read_csv(OUT/'calibration_response_controls.csv')
    budgets = pd.read_csv(OUT/'calibration_acceptance_budget.csv')
    sensitivity = pd.read_csv(OUT/'sensitivity.csv')
    engineering = json.loads((OUT/'engineering_controls.json').read_text())
    hop_gain = next(r for r in engineering if r['case'] == 'hopping_independent_unknown_gains')
    weather = pd.read_csv(OUT/'unknown_weather_failure.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout='constrained')
    labels = [f'{r.total_s:.0f} s\n{r.residual_std_db:g} dB' for r in response.itertuples()]
    axes[0].bar(labels, response.recall_pct, color=['#a64d42', '#bd7058', '#26756d', '#489f95'])
    axes[0].set(ylabel='Simulated recall at 1 µg/m³ (%)', ylim=(0, 105), title='Acetonitrile: calibration controls the result')
    axes[0].axhline(95, color='black', linestyle=':', linewidth=1)
    for i, row in response.iterrows():
        axes[0].text(i, row.recall_pct+2, f'{row.recall_pct:.2f}%', ha='center', fontsize=9)
    ref = sensitivity[(sensitivity.profile == 'standard') & (sensitivity.elevation_deg == 45) &
                      (sensitivity.total_s == 20) & (sensitivity.residual_std_db == .001)]
    x = np.arange(3)
    normal = [ref[ref.target == name].local_lod95_ug_m3.iloc[0] for name in ['H2CO', 'CH3OH', 'CH3CN']]
    axes[1].bar(x-.18, normal, width=.36, label='Correlated residual model')
    axes[1].bar(x+.18, hop_gain['local_lod95_ug_m3'][:3], width=.36, label='Unknown gain at each hop')
    axes[1].set(xticks=x, xticklabels=['H₂CO', 'CH₃OH', 'CH₃CN'], yscale='log',
                ylabel='Local 95% power limit (µg/m³)', title='20 s, residual standard deviation 0.001 dB')
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.savefig(OUT/'receiver_calibration_results.png', dpi=180)
    fig.savefig(OUT/'receiver_calibration_results.pdf')
    plt.close(fig)
    gas_table = '\n'.join(f'| {r.target} | {r.response_lod95_ug_m3:.3f} | {r.recall_pct:.2f}% | {r.ci_lower_pct:.2f}–{r.ci_upper_pct:.2f}% |' for r in power.itertuples())
    recall_table = '\n'.join(f'| {r.total_s:.0f} | {r.residual_std_db:g} | {r.recall_pct:.2f}% | {r.family_false_alarm_pct:.2f}% |' for r in response.itertuples())
    b = budgets[(budgets.target == 'CH3CN') & (budgets.concentration_ug_m3 == 1)]
    required = {int(r.total_s): r.required_max_correlated_residual_std_db for r in b.itertuples()}
    content = f'''# Receiver design, moving payload and calibration requirements

September 27, 2026. This is a follow-up to the [proposal audit](43_original_proposal_remaining_tasks.md) and the [critical calibration note](46_critical_calibration_assumption.md).

**The new favorable control uses a nonzero assumed calibration residual, not a measured calibration accuracy.** In the standard atmosphere at 45 degrees, with matched reference weather, 23 dBm radiated power and a 6 dB receiver noise figure, acetonitrile recall at 1 µg/m³ is {response.iloc[2].recall_pct:.2f}% in 10,000 simulated responses with 100 seconds total and residual standard deviation 0.0001 dB. At 0.001 dB it is only {response.iloc[1].recall_pct:.2f}%. Neither is field performance. The original zero residual benchmark remains an idealization.

## What was done and why

The missing link between separated ideal tones and an actual modem was made explicit. A contiguous candidate was screened, its exact spectrum was recomputed, and its failed joint identifiability was retained. A second candidate uses one active RF chain sequentially across 16 blocks within the 220–330 GHz WR3.4 family. Each block has 16 QPSK tones, 1 MHz spacing and a one sample cyclic prefix. Centers run from 228 to 316 GHz. A frame has 10,000 symbols and 30 existing pilots. This is 16 MHz instantaneous bandwidth, an 88 GHz tuning span and a 1.0625 µs symbol duration.

The reference and sample each use 10 seconds in the 20 second control. Charging 1 ms settling per hop and complete frames leaves 19.72 seconds of transmission and 0.032 seconds of settling. The remainder is frame rounding. Total radiated power is 23 dBm while transmitting, not 23 dBm per simultaneous block. Both transmissions carry ordinary coded communication data. Waiting between matched orbital passes remains outside this transmission-time budget.

HITRAN Voigt lines, Mie optics, refracted paths and atmospheric emission were recomputed at the exact new frequencies. Standard atmosphere and the four existing public seasonal weather soundings are evaluated at 30, 45, 60 and 90 degrees. The old coarse grid is used only for candidate screening. It cannot establish rank inside a narrow band. Candidate selection used the standard design case, not Monte Carlo outcomes or seasonal cases. The uniform hopping grid is an engineering candidate, not a globally optimal band allocation.

## Hardware feasibility is now an explicit gate

The [VDI compact converter manual](https://vadiodes.com/wp-content/uploads/2012/01/VDI-737_CC_Product_Manual.pdf), revision August 27, 2024, lists the WR3.4 converter family over 220–330 GHz, 12 dB typical intrinsic mixer conversion loss and a 40 GHz maximum IF for its M12 variant. These support a frequency-conversion architecture, not the assumed satellite power or noise performance.

A 1 GHz IF requires LO = (RF − 1 GHz)/12 and image filtering. The manual's approximately −11 dBm input at 0.1 dB compression implies roughly −23 dBm output before filters or waveform backoff when subtracting 12 dB conversion loss. Reaching the 23 dBm reference therefore requires at least 46 dB additional linear gain, plus filtering and crest-factor margin. Conversion loss is not a measured complete receiver noise figure. The 6 dB reference and 17 dB stress are requirements/sensitivities; the unamplified −23 dBm, 17 dB case fails the sensing SNR gate.

This is a concrete acquisition design with a quantified hardware gap, not a claim that an off-the-shelf flight modem meets it. Retuning time, phase noise, image rejection, antennas, spectrum coordination and receiver calibration remain to be characterized.

## Results with nonzero calibration residual

The primary 20 second case fits all three VOCs, both PM modes, background/interfering gases, unknown common gain offset and gain slope. Calibration is a zero mean differential dB residual with standard deviation 0.001 dB and exponential 10 GHz frequency correlation. It is drawn once per acquisition, not averaged away once per symbol. Reference thermal uncertainty is charged independently. The family false alarm budget remains 1% across six outputs.

| Target | 95% response limit (µg/m³) | Simulated recall at that limit | Exact 95% recall interval |
|---|---:|---:|---:|
{gas_table}

The family false alarm frequency in that control is {power.iloc[0].family_false_count/100:.2f}%. These are 10,000 response draws per class, using nonlinear moment inversion and a declared large-sample moment approximation. Raw waveform controls are separate.

| Total reference + sample time (s) | Residual standard deviation (dB) | Acetonitrile recall at 1 µg/m³ | Family false alarm frequency |
|---|---:|---:|---:|
{recall_table}

The requested 20 s, 0.0001 dB control gives {response.iloc[3].recall_pct:.2f}% recall (exact 95% interval {response.iloc[3].ci95_lower_pct:.2f}–{response.iloc[3].ci95_upper_pct:.2f}%). Thus it improves substantially over 0.001 dB but still falls below 95% power at 1 µg/m³.

For the selected design, local 95% power at 1 µg/m³ requires residual standard deviation at most approximately {required[20]:.6f} dB at 20 seconds or {required[100]:.6f} dB at 100 seconds under that correlation model. These are separate random-error requirements. The saved [calibration budget](../results/receiver_design/calibration_acceptance_budget.csv) also treats arbitrary persistent per-tone bias with a protected null threshold. Its separate bias budget cannot be combined with the random budget without recomputation.

![Calibration and gain uncertainty](../results/receiver_design/receiver_calibration_results.png)

Unknown independent gain offsets at every hop increase the acetonitrile local limit to {hop_gain['local_lod95_ug_m3'][2]:.1f} µg/m³. This exposes the need to calibrate relative gains between frequency settings. Simply fitting more nuisance terms does not fix calibration: it also removes absorption information. More averaging cannot remove a persistent indistinguishable spectral error.

## Moving coded receiver

The implementation generates raw IFFT/CP QPSK, AWGN and orbital carrier Doppler. It acquires integer timing within a nine-sample window, estimates residual CFO from CP correlations and tracks phase with existing pilots. Sensing uses geometry-normalized FFT magnitudes before the communication channel amplitude equalizer. Dividing sensing data by a channel amplitude estimated from those same pilots would remove the absorption being measured.

Each hop is sampled by three 10.625 ms bursts over a changing 10 second geometry, repeated for an independent matched reference. Only actually generated symbols enter the sensing covariance. The two controls generate {moving['raw_complex_samples']:,} complex samples and decode {moving['packets']:,} packets protected by Hamming (7,4) and CRC16. All {moving['correct_packets']:,} packets are correct in this run; zero observed errors do not establish a universal error rate. Carrier Doppler reaches {moving['maximum_absolute_doppler_hz']/1e6:.3f} MHz. The maximum residual CFO RMS is {moving['maximum_residual_cfo_rms_hz']:.1f} Hz with a 100 kHz initial prediction error. A retained 700 kHz error exceeds the CP acquisition range and decodes zero correct packets.

The blank and acetonitrile controls retain their signed concentration estimates and uncertainty, including unsuccessful PM estimates. They are two raw trajectories, not a recall estimate. The separate response experiments above estimate recall. Narrowband Doppler is assumed within each 16 MHz hop. Fractional timing, sample clock drift/wideband time dilation, arbitrary phase noise, multipath and unmatched reference weather remain outside this receiver model.

Decoded output is identical with passive sensing enabled. However, hopping and frame rounding cost {moving['scheduling_loss_vs_fixed_band_pct']:.3f}% of scheduled payload relative to an otherwise identical fixed-band modem. The buffered receiver needs 10.625 ms of samples per frame; CPU execution, real-time hardware latency and an optimal communication-only scheduler are not validated. Zero incremental loss on an already hopping link must not be promoted to zero architecture cost or equality with Gaussian-input Shannon capacity.

## Joint PM, weather and absolute concentration

PM retrieval remains unusable. The new gain slope control makes its weak smooth signature even less distinguishable from instrument response. These enormous local errors diagnose missing information; they are not physically valid PM concentration ranges. Independent PM constraints would supply information from another instrument and must be attributed accordingly.

Seasonal sensitivity is evaluated with matching weather. The frozen standard operator is also applied to seasonal background differences in [the mismatch control](../results/receiver_design/unknown_weather_failure.csv). Those apparent gas biases remain a failure mode, not calibrated uncertainty. That diagnostic isolates background mismatch and does not pretend to be a complete unmatched receiver likelihood.

The observable is an enhancement relative to a reference. Neither a better modem nor successful symbol decoding identifies an unknown reference abundance or validates the assumed vertical profiles. Absolute concentrations need independent baseline/column truth. Environmental compliance remains unsupported.

## Completion status and next steps

| Gap | What this work closes | What still needs external evidence or further engineering |
|---|---|---|
| Band/resource design | Exact frequency schedule, bandwidth, power, CP, pilots, reference and settling accounting; rejected designs retained. | Required RF power/noise and gain stability are not demonstrated. |
| Moving payload receiver | Bounded raw waveform acquisition, Doppler correction, pilot tracking and payload sensing. | Wideband timing effects, oscillator/pointing errors, unmatched reference and real-time implementation. |
| Calibration | Nonzero residual Monte Carlo, inverse acceptance budgets, persistent bias protection, acquisition template. | Independent measured calibration and subsequent validation campaigns. |
| Communication preservation | Actual coded packet comparison and a nonzero scheduling cost. | Hardware latency/availability and comparison with an optimized production communication system. |
| Joint gas/PM inference | Quantified limits and gain/weather failure boundaries. | Useful PM discrimination remains unresolved; negative feasibility is the supported outcome here. |
| Physical validation | Traceable collection requirements and numerical replay. | Actual paired radio and independent concentration measurements. |

The next empirical step is the [empty calibration measurement template](../results/receiver_design/calibration_measurement_template.csv), using the [exact frequencies](../results/receiver_design/required_calibration_frequencies.csv) and the [measurement gate](../results/receiver_design/calibration_measurement_gate.json). The existing calibration analysis command accepts real supplied sweeps. No observation was fabricated to fill this gap.

An [additional public data screen](../results/receiver_design/public_data_screen.json) found propagation datasets and a spectroscopy lead, but acquired no paired calibration/concentration validation data. The [Niigata laboratory dataset description](https://radio.eng.niigata-u.ac.jp/datasets/sub-thz/) includes a calibration procedure and directional channels; that description alone does not establish the residual accuracy needed here. Registration was not submitted. Access failures and unreviewed leads are retained in the screening record.

## Reproduction and limitations

Run `python scripts/design_payload_receiver.py`, `python scripts/receiver_design_physics.py`, `python scripts/evaluate_receiver_design.py`, `python scripts/receiver_calibration_budget.py`, `python scripts/run_moving_payload_receiver.py`, `python scripts/verify_receiver_design.py`, then `python scripts/report_receiver_design.py`, with the existing project dependencies and spectroscopy acquisition. Single BLAS threads avoid nested oversubscription during the six-process physical integrations.

The physical model retains previously evaluated quadrature and uncalibrated PM/vertical-profile assumptions. Its new narrow-band inverse problem has not received an independent experimental or alternative-spectroscopy validation. The verification replays {verify['checks']} checks; it verifies arithmetic, resource accounting, source hashes and retained outcomes, not physical truth. Original result snapshots remain separate. The new deliverable manifest records the files for this extension.
'''
    (ROOT/'docs/47_receiver_design_and_calibration.md').write_text(content, encoding='utf-8')
    tex = r'''\section{Sequential receiver and calibration feasibility}
A concrete extension replaces simultaneous separated probes with one active RF chain retuned over 16 blocks from 228 to 316 GHz, each with 16 tones at 1 MHz spacing. A one-sample CP, 30 pilots per 10,000 symbols, both reference and sample, 1 ms settling per hop and whole-frame rounding are charged. The 20 s reference/sample budget contains 19.72 s of transmissions. The WR3.4 converter family supports this frequency conversion range \cite{vdicc}, but the assumed 23 dBm radiated power and 6 dB receiver noise figure remain unverified requirements. Typical intrinsic conversion loss and the quoted small-signal input imply about $-23$ dBm unamplified output before filtering/backoff, leaving at least 46 dB of additional linear gain. This is not demonstrated flight hardware.

Exact Voigt/Mie spectra, refracted paths and emission are recomputed at the selected frequencies. A screened contiguous candidate is rejected after exact joint rank evaluation. With a 0.001 dB correlated differential residual, common gain offset/slope, joint VOC/PM inference and 20 s total, the hopping candidate's response limits are LIMITS \ugm\ for formaldehyde, methanol and acetonitrile. Independent response draws give approximately 95\% power at each limit and FAMILY\% family false alarms. Unknown independent gains at each hop increase acetonitrile's local limit to HOPGAIN \ugm. Thus retuning requires relative gain calibration, not just a frequency plan.

At 1 \ugm\ acetonitrile, 100 s total gives BAD\% simulated recall with 0.001 dB residual and GOOD\% with 0.0001 dB residual (10,000 positives per case). At 20 s and 0.0001 dB, recall is SHORT\% (95\% interval SHORTLO--SHORTHI\%). The 100 s result is a favorable \emph{assumed nonzero calibration} control, not measured stability. More averaging does not overcome the persistent residual. The local requirement for 95\% power at 100 s is approximately BUDGET dB under the specified correlation model. Arbitrary systematic drift requires a separate protected-threshold budget.

Raw moving controls now include IFFT/CP generation, integer timing acquisition, CP frequency correction, existing-pilot phase tracking, Hamming (7,4) coding and CRC16. The tested initial Doppler prediction error is 100 kHz; a 700 kHz control fails acquisition and is retained. Three bursts per hop sample changing geometry; only generated symbols enter the sensing variance. Across two reference/sample controls, PACKETS packets decode correctly, and passive sensing preserves decoded output. These two trajectories do not estimate recall. Hopping/frame scheduling nevertheless costs LOSS\% relative to a fixed-band modem with the same code and bandwidth. Processing buffers a 10.625 ms frame. Narrowband Doppler per hop and matched reference weather remain assumed; wideband time dilation, fractional timing, oscillator noise and real-time hardware latency remain unvalidated. PM, absolute baseline truth and field compliance are unresolved.
'''
    replacements = dict(LIMITS=', '.join(f'{v:.3f}' for v in power.response_lod95_ug_m3),
        FAMILY=f'{power.iloc[0].family_false_count/100:.2f}', HOPGAIN=f"{hop_gain['local_lod95_ug_m3'][2]:.1f}",
        SHORT=f'{response.iloc[3].recall_pct:.2f}', SHORTLO=f'{response.iloc[3].ci95_lower_pct:.2f}', SHORTHI=f'{response.iloc[3].ci95_upper_pct:.2f}', BAD=f'{response.iloc[1].recall_pct:.2f}', GOOD=f'{response.iloc[2].recall_pct:.2f}',
        BUDGET=f'{required[100]:.6f}', PACKETS=f"{moving['correct_packets']:,}",
        LOSS=f"{moving['scheduling_loss_vs_fixed_band_pct']:.3f}")
    for key, value in sorted(replacements.items(), key=lambda item: -len(item[0])):
        tex = tex.replace(key, value)
    (ROOT/'paper/receiver_design.tex').write_text(tex, encoding='utf-8')
    print('Saved report, paper section and figures')


if __name__ == '__main__':
    main()
