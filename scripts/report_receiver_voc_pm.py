"""Report requested 20 second calibration case and expanded target limitations."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design/voc_pm_extension'


def main():
    verification = json.loads((OUT/'verification.json').read_text())
    if verification['status'] != 'passed':
        raise RuntimeError('Verify results first')
    s = pd.read_csv(OUT/'sensitivity.csv')
    r = pd.read_csv(OUT/'response_controls.csv')
    calibration = pd.read_csv(OUT.parent/'calibration_response_controls.csv')
    short = calibration[(calibration.total_s == 20) & (calibration.residual_std_db == .0001)].iloc[0]
    selected = s[(s.total_s == 20) & (s.residual_std_db == .0001)]
    expanded = selected[selected['mode'] == 'expanded'].set_index('target')
    original = selected[selected['mode'] == 'original'].set_index('target')
    joint = r[(r['mode'] == 'expanded') & (r.control == 'joint mixture')].set_index('target')
    limits = r[r.control == 'response limit'].set_index('target')
    rows = '\n'.join(f'| {name} | {expanded.loc[name].local_lod95_ug_m3:.3f} | {joint.loc[name].recall_pct:.2f}% |' for name in ['H2CO', 'CH3OH', 'CH3CN', 'CH3Cl', 'HCOOH'])
    pmrows = '\n'.join(f'| {name} | {joint.loc[name].concentration_ug_m3:.0f} | {joint.loc[name].recall_pct:.2f}% | {expanded.loc[name].local_lod95_ug_m3:.3e} |' for name in ['PM2.5', 'PMcoarse', 'PM10'])
    fig, ax = plt.subplots(figsize=(7.4, 4.2), layout='constrained')
    names = ['H2CO', 'CH3OH', 'CH3CN', 'CH3Cl', 'HCOOH']
    ax.bar(names, expanded.loc[names].local_lod95_ug_m3, color='#26756d')
    ax.set(yscale='log', ylabel='Local 95% power limit (µg/m³)', title='Five VOCs jointly fitted with fine/coarse PM\n20 s total; assumed residual standard deviation 0.0001 dB')
    for i, name in enumerate(names):
        v = expanded.loc[name].local_lod95_ug_m3
        ax.text(i, v*1.12, f'{v:.2f}', ha='center')
    ax.set_ylim(.8, 400)
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
    fig.savefig(OUT/'expanded_voc_limits.png', dpi=180)
    plt.close(fig)
    content = f'''# Twenty seconds, nonzero calibration, more VOCs and PM size fractions

September 27, 2026. This extends the [receiver study](47_receiver_design_and_calibration.md). **All results assume a differential calibration residual standard deviation of 0.0001 dB unless stated otherwise. This has not been measured or demonstrated.** The reference and sample each occupy 10 seconds, including the existing receiver resource accounting. Standard atmosphere, 45 degrees elevation, matched reference weather, 23 dBm transmitting power and a 6 dB noise figure remain conditional requirements.

## Requested calibration comparison

With the original three VOCs plus fine/coarse PM fitted, acetonitrile at 1 µg/m³ has **{short.recall_pct:.2f}% simulated recall**, exact 95% interval **{short.ci95_lower_pct:.2f}–{short.ci95_upper_pct:.2f}%**, from 10,000 positives. Family false alarms are {short.family_false_alarm_pct:.2f}%. The predicted local 95% power limit is {original.loc['CH3CN'].local_lod95_ug_m3:.3f} µg/m³. The independently simulated simultaneous three-VOC/PM mixture gives 90.08%, consistent with this single-VOC control. At 0.001 dB, the original single-VOC control gives only 2.72%. These are distinct simulations, not field recall.

## Additional VOCs and interference

Six additional organic gas candidates were requested from [HITRAN](https://www.hitran.org/docs/molec-meta/): CH3Cl, HCOOH, CH3Br, C2H4, CH3F and CH3I. This is a spectroscopy inventory, not a claim that every candidate belongs to every regulatory VOC definition. CH3Cl and HCOOH yielded usable line lists, each with two available isotopologues. The retained 0–3000 GHz window contains 12,824 CH3Cl lines and 18,440 HCOOH lines; 670 and 401 respectively lie in 220–330 GHz. All four other candidates returned retrieval errors and remain **unavailable**, not zero absorption or absent molecules. The [acquisition ledger](../results/receiver_design/voc_pm_extension/acquisition.json) retains every attempt and exact input hashes. No missing spectrum was replaced with an invented one.

Exact pressure/temperature dependent Voigt spectra were integrated over the same refracted standard-atmosphere path at the 256 frozen receiver frequencies. Isotopic natural abundance is already included in HITRAN intensities and is not applied twice. Missing minor-isotope coverage remains a model limitation. Natural molar mass converts total mass concentration, while each isotope's HAPI mass is used for Doppler broadening. No frequency was chosen using these test outcomes.

All five VOCs and two PM masses are now fitted together. CO, O3, SO2, NO2, atmospheric background amplitude, common gain offset and slope remain nuisance parameters. PM10 is the sum of the two inferred masses including covariance. The family threshold is tightened from six to eight reported quantities, retaining the 1% budget.

| VOC | Local 95% power limit (µg/m³) | Simulated recall at 1 µg/m³ in the joint mixture |
|---|---:|---:|
{rows}

The expanded mixture has {joint.loc['CH3CN'].family_false_alarm_pct:.2f}% family false alarms in 10,000 null responses. The acetonitrile decline to **{joint.loc['CH3CN'].recall_pct:.2f}%** reflects the expanded inverse problem and stricter family threshold. The earlier 90.20% result must not be generalized to five unknown VOCs. Adding target names does not add independent spectral information.

At the separately solved response limits, CH3Cl gives {limits.loc['CH3Cl'].recall_pct:.2f}% recall at {limits.loc['CH3Cl'].concentration_ug_m3:.3f} µg/m³; HCOOH gives {limits.loc['HCOOH'].recall_pct:.2f}% at {limits.loc['HCOOH'].concentration_ug_m3:.3f} µg/m³. Each has 10,000 nonlinear moment response draws, with positive-signal thermal variance and a persistent calibration residual drawn once per acquisition. These controlled limits are not useful detection at 1 µg/m³.

![Expanded gas detection limits](../results/receiver_design/voc_pm_extension/expanded_voc_limits.png)

The [HITRAN2024 paper, page 31](https://hitran.org/media/refs/HITRAN-2024.pdf) explains that absolute pure rotational formic-acid intensities have not been measured and that its line strengths are computed from experimentally determined dipole moments. Catalog inclusion therefore does not provide independent measured validation of our forward model. Spectroscopic/model uncertainty is not included in the receiver noise intervals.

## PM masses and additional size fractions

PM2.5 and PM10 are overlapping mass cuts, not distinct chemicals. The original fit uses disjoint fine and coarse fractions; PM10 is their sum. The new simultaneous mixture retains the previously selected public Beijing values, fine 49 and coarse 41 µg/m³, giving PM10 = 90 µg/m³. This provides real concentration labels for a modeled radio response, not paired measured radio observations.

| PM output | Mixture concentration (µg/m³) | Simulated recall | Formal local 95% power scale (µg/m³) |
|---|---:|---:|---:|
{pmrows}

These very low recalls are at the false-alarm scale. The enormous formal limits are diagnostics of insufficient information, not physically valid high-concentration predictions. Even an optimistic single-PM calculation with every gas, other PM mode and gain known gives limits of approximately 905 µg/m³ for fine PM and 1,111 µg/m³ for coarse PM at 20 s and 0.0001 dB. Allowing gain/background nuisance terms alone raises those scales to 1.35 × 10¹⁰ and 4.73 × 10⁸ µg/m³. Thus the failure is not solely competition with the new gases.

The finer size study uses disjoint aerodynamic cuts 0.03–1, 1–2.5 and 2.5–10 µm. It subdivides the existing fine lognormal distribution, applies the Stokes/Cunningham diameter conversion and recomputes full Mie extinction per unit mass. The first two cuts retain the same assumed composition as the prior fine mode; no new soot, salt or dust material constants are fabricated. PM1, PM2.5 and PM10 would be corresponding cumulative sums.

**The three-bin inverse calculation is rejected as numerically unstable.** At 20 s and 0.0001 dB the scaled target condition number is approximately 9.76 × 10⁷ and the scaled identity error is 0.508, far above the 10⁻⁵ acceptance gate. The failure also occurs at 20 s/0.001 dB and 100 s/0.0001 dB. Its arrays and errors are retained, but no unreliable size uncertainties are promoted to valid results. Positive mass clipping or renaming the three variables would not repair missing size information.

Material composition remains uncalibrated. The previously analyzed [measured calcite aerosol dataset](https://doi.org/10.57745/DLJEFW) contains useful transmission data, but the inspected records lack the paired mass and particle-size labels needed to calibrate these mass extinction coefficients. Optical/infrared constants cannot simply be substituted for 220–330 GHz properties. This extension therefore adds a size-identifiability test, not validated chemical discrimination among aerosol materials.

## What remains and next steps

The computation closes the requested 20 s calibration comparison, evaluates two additional VOCs jointly and explicitly tests an additional PM size split. It retains four spectroscopy acquisition gaps and the PM failures. It does not establish achievable calibration, absolute atmospheric concentration, field performance or useful PM sensing.

The next design step is to select frequencies against all five gases and gain nuisance terms using separate design conditions, then evaluate them on fresh weather and response draws while charging the same time, power and tuning resources. Missing gas candidates require line positions, intensities and atmospheric broadening from a supported source. PM composition requires measured sub-THz optical properties plus independently measured mass/size distributions. Calibration still requires independent sweeps under the intended receiver conditions.

Reproduce with `python scripts/acquire_receiver_vocs.py`, `python scripts/extend_receiver_voc_pm.py`, `python scripts/verify_receiver_voc_pm.py`, and `python scripts/report_receiver_voc_pm.py`. The acquisition is pinned by hashes rather than a promise that future online responses are identical. Original snapshots remain separate. This report uses {verification['checks']} replay checks and retains the [sensitivity table](../results/receiver_design/voc_pm_extension/sensitivity.csv), [Monte Carlo counts and intervals](../results/receiver_design/voc_pm_extension/response_controls.csv) and [rejected size diagnostics](../results/receiver_design/voc_pm_extension/diagnostics.json).
'''
    (ROOT/'docs/48_expanded_voc_pm_and_20s_calibration.md').write_text(content, encoding='utf-8')
    tex = r'''\subsection{Additional VOCs and PM size fractions}
The requested 20 s, 0.0001 dB case was extended using newly acquired HITRAN CH$_3$Cl and HCOOH lines, with two available isotopologues each. Four other organic candidates remain acquisition gaps. Jointly fitting five VOCs and two PM masses, with the same background/gain nuisance terms and a 1\% family budget over eight outputs, reduces simulated 1 \ugm\ acetonitrile recall to RECALL\% in 10,000 joint-mixture responses. Family false alarms are 0.68\%. Conditional 95\% response limits are CLIMIT \ugm\ for CH$_3$Cl and FLIMIT \ugm\ for HCOOH, validated at 95.11\% and 95.16\% simulated recall. Additional species therefore expose ambiguity in the frozen receiver schedule.

PM2.5/PM10 recall at 49/90 \ugm\ remains only 0.08\%, at the false-alarm scale. Even with all other quantities known, a one-parameter fine-PM limit is approximately 905 \ugm. Subdividing the fine mode into aerodynamic cuts below and above 1 $\mu$m produces a numerically unstable three-bin inverse problem: its scaled identity error is 0.508 and the result is rejected. Composition remains assumed; missing particle mass/size calibration cannot be replaced by additional simulated material labels. These results use the same assumed 0.0001 dB residual, matched reference weather and unverified RF requirements. They are not measured field performance.
'''
    tex = tex.replace('RECALL', f"{joint.loc['CH3CN'].recall_pct:.2f}").replace('CLIMIT', f"{limits.loc['CH3Cl'].concentration_ug_m3:.3f}").replace('FLIMIT', f"{limits.loc['HCOOH'].concentration_ug_m3:.3f}")
    (ROOT/'paper/receiver_voc_pm.tex').write_text(tex, encoding='utf-8')
    print('Saved expanded VOC/PM report, figure and manuscript section')


if __name__ == '__main__':
    main()
