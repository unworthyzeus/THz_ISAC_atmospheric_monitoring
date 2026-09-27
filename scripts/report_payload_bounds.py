"""Generate figures and research/manuscript numbers from retained evidence."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/payload_bounds'
NAMES = {'H2CO': 'Formaldehyde', 'CH3OH': 'Methanol', 'CH3CN': 'Acetonitrile'}


def main():
    manifest = json.loads((OUT/'experiment_manifest.json').read_text())
    if manifest['status'] != 'passed':
        raise ValueError('Experiment not passed')
    data = pd.read_csv(OUT/'sensitivity.csv')
    validation = pd.read_csv(OUT/'detection_validation.csv')
    status = pd.read_csv(OUT/'case_status.csv')
    critical = data[(data['case'] == 'standard_45')&(data.target == 'CH3CN')&
        (data.method == 'm2m4')&(data.total_s == 20)&(data.noise_multiplier == 1)].sort_values('differential_residual_std_db')
    if len(critical) != 3 or not np.allclose(critical.differential_residual_std_db, [0., .0001, .001], rtol=0, atol=1e-15):
        raise ValueError('Critical calibration comparison does not match the declared cases')
    caveat = OUT/'calibration_caveat'
    caveat.mkdir(exist_ok=True)
    critical.to_csv(caveat/'critical_calibration_rows.csv', index=False)
    (caveat/'provenance.json').write_text(json.dumps(dict(
        claim='Zero residual calibration is an ideal benchmark; receiver calibration accuracy is not experimentally established',
        concentration_ug_m3=1., target='CH3CN', profile='standard', elevation_deg=45,
        reference_s=10, sample_s=10, receiver_noise_multiplier=1, family_alpha=.01, family_size=6,
        metric='Predicted recall, not empirical field recall',
        residual='Standard deviation of zero mean differential dB error; exponential frequency correlation length 10 GHz; not an arbitrary deterministic bias bound',
        sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'sensitivity.csv', OUT/'protocol.json']}
    ), indent=2)+'\n')
    base = data[(data.total_s == 20)&(data.noise_multiplier == 1)&(data.differential_residual_std_db == 0)]
    standard = base[base['case'] == 'standard_45']
    rows = []
    for target, name in NAMES.items():
        subset = standard[standard.target == target].set_index('method')
        m = subset.loc['m2m4']
        v = validation[(validation['case'] == 'standard_45')&(validation.target == target)].iloc[0]
        rows.append(dict(target=target, name=name, payload_lod95_ug_m3=m.response_lod95_ug_m3,
            payload_lod95_ppm=m.response_lod95_ppm, pilot_lod95_ug_m3=subset.loc['pilots'].response_lod95_ug_m3,
            qpsk_efficiency_pct=100*(subset.loc['qpsk_crlb'].sd_ug_m3/m.sd_ug_m3)**2,
            magnitude_efficiency_pct=100*(subset.loc['magnitude_crlb'].sd_ug_m3/m.sd_ug_m3)**2,
            validated_power_pct=v.recall_pct, power_ci_lower=v.recall_ci95_lower_pct,
            power_ci_upper=v.recall_ci95_upper_pct, recall_at_1ug_pct=m.recall_at_1ug_pct))
    headline = pd.DataFrame(rows)
    headline.to_csv(OUT/'headline.csv', index=False)
    primary = base[(base.method == 'm2m4')&base.target.isin(NAMES)]
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.1), sharex=True)
    colors = ['#172f51', '#258a87', '#b8751d', '#8b5276', '#77812d']
    for ax, (target, name) in zip(axes, NAMES.items()):
        for (profile, group), color in zip(primary[primary.target == target].groupby('profile', sort=False), colors):
            full = group.set_index('elevation_deg').response_lod95_ug_m3.reindex([5, 15, 30, 45, 60, 90])
            ax.plot(full.index, full, 'o-', lw=1.5, ms=4, color=color, label=profile.replace('igra_', 'IGRA month '))
        ax.axhline(1, color='#8a8a8a', ls=':', lw=1)
        ax.set(title=name, xlabel='Elevation (degrees)', yscale='log', xticks=[5, 30, 60, 90])
        ax.grid(alpha=.18)
    axes[0].set_ylabel('95% power detection limit (µg/m³)')
    axes[2].legend(fontsize=8)
    fig.suptitle('20 s total: 10 s reference + 10 s sample; matched weather; zero calibration residual', fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT/'payload_operating_region.png', dpi=200)
    fig.savefig(OUT/'payload_operating_region.pdf')
    plt.close(fig)
    ac = data[(data.method == 'm2m4')&(data.target == 'CH3CN')&(data.profile == 'standard')&(data.noise_multiplier == 1)]
    fig, ax = plt.subplots(figsize=(7, 4))
    for total, ls in [(20, '-'), (100, '--')]:
        for residual, color in [(0, '#1b7773'), (.001, '#a24639')]:
            g = ac[(ac.total_s == total)&(ac.differential_residual_std_db == residual)]
            ax.plot(g.elevation_deg, g.recall_at_1ug_pct, marker='o', ls=ls, color=color,
                    label=f'{total} s total, {residual:g} dB residual')
    ax.set(xlabel='Elevation (degrees)', ylabel='Predicted recall at 1 µg/m³ (%)', ylim=(0, 101),
           title='Acetonitrile: time, geometry and differential calibration')
    ax.legend(fontsize=8); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(OUT/'payload_calibration_region.png', dpi=200); plt.close(fig)
    table = '\n'.join(f'| {r.name} | {r.payload_lod95_ug_m3:.3f} | {r.payload_lod95_ppm:.6f} | {r.validated_power_pct:.2f}% | {r.qpsk_efficiency_pct:.2f}% |' for r in headline.itertuples(index=False))
    eligible = status[(status.noise_multiplier == 1)&(status.status == 'eligible')]
    rejected = status[status.status != 'eligible']
    acet = primary[primary.target == 'CH3CN']
    moving = pd.read_csv(OUT/'moving_geometry.csv')
    moving = moving[(moving.bins == 40)&(moving.method == 'm2m4')&(moving.target == 'CH3CN')].copy()
    moving['local_lod95_ug_m3'] = moving.sd_ug_m3*(norm.isf(.01/6)+norm.ppf(.95))
    moving.to_csv(OUT/'moving_headline.csv', index=False)
    moving_table = '\n'.join(f'| {r.center_elevation_deg:.0f}° | {r.total_transmission_s:.0f} | {r.local_lod95_ug_m3:.3f} |' for r in moving.itertuples(index=False))
    rejected_text = ', '.join(f'{r.case} (noise ×{r.noise_multiplier:g}, {r.sensing_tones} usable tones)' for r in rejected.itertuples(index=False))
    md = f'''# Payload bounds, sensitivity and detection floors

> **Critical calibration assumption:** Favorable results assume zero residual calibration error after correction, an accuracy not established experimentally. With a charged 10 + 10 second reference/sample pair at 45° in the standard atmosphere, predicted acetonitrile recall at 1 µg/m³ falls from 93.84% to 25.17% at a modeled differential residual standard deviation of 0.001 dB. Receiver noise and finite reference uncertainty remain present. [Permanent note and exact evidence](46_critical_calibration_assumption.md).

## What was done and why

Original proposal Tasks 4.1–4.3 are extended to passive payload sensing. The study now distinguishes estimator variance from fundamental local information, charges finite reference acquisition, recomputes atmospheric and link physics across elevation and measured weather, and validates the predicted detection limits. The [derivation](44_payload_information_derivation.md) gives the likelihoods, nuisance treatment and scope.

The 21 recovered HITRAN isotope files match the previous raw data hashes exactly. Seven gas designs are recomputed over spherical refracted rays, using the standard atmosphere and four previously selected NOAA IGRA soundings. Background absorption, atmospheric emission, receiver SNR and communication water filling are recomputed per case. PM optics and assumed vertical profiles are retained. The 30 physical cases span 5°, 15°, 30°, 45°, 60° and 90°. Total durations are 2, 20 and 100 seconds, with equal sample and independent reference windows. Receiver noise multipliers are 1 and 2; differential calibration residuals are 0, 0.0001 and 0.001 dB.

## Main result

At standard atmosphere, 45°, 20 seconds total, nominal receiver noise and zero residual:

| Gas | 95% power limit (µg/m³) | Limit (ppm) | Simulated power at limit | Efficiency vs full QPSK CRLB |
|---|---:|---:|---:|---:|
{table}

The estimator is already close to the full constellation information bound. Replacing M2M4 with a more elaborate likelihood estimator offers a small improvement in this case; it cannot plausibly remove the large methanol or PM limitations. The comparison includes unknown noise, finite reference, all three VOCs, both PM modes, and six spectral nuisance coefficients.

The quoted ppm values use the local surface pressure and temperature and natural mixture molecular masses. They express the assumed exponential column profile as a surface equivalent concentration enhancement. They are not directly measured ground level concentrations or absolute concentrations without baseline truth.

## Operating region and validation

{len(eligible)} of 30 physical cases meet the fixed 5 dB / 20 usable tone gate at nominal receiver noise. Every eligible case has 10,000 independent null responses and 10,000 responses for each VOC at its predicted limit. Across {len(validation)} VOC controls, measured power ranges from {validation.recall_pct.min():.2f}% to {validation.recall_pct.max():.2f}%; per target false positive frequency ranges from {validation.false_positive_pct.min():.2f}% to {validation.false_positive_pct.max():.2f}%. All power checks pass their fixed Monte Carlo tolerance. Counts, exact binomial confidence intervals and retained response arrays are available for replay. The threshold is fixed for a 1% family error budget across six outputs. No test outcomes choose it.

The response limit is solved using concentration dependent sample variance before testing. This corrects the local Gaussian limit without changing the null threshold. Moment draws are asymptotic sample moment responses followed by nonlinear inversion, supported by the earlier independent raw QPSK experiment. They are not full multi-million-symbol waveform simulations.

At 20 seconds and zero residual, acetonitrile limits over the eligible weather/elevation grid span {acet.response_lod95_ug_m3.min():.3f}–{acet.response_lod95_ug_m3.max():.3f} µg/m³. Weather is supplied to the estimator in these cases. This is a matched weather sensitivity study, not robustness to unknown weather; the earlier weather mismatch failures remain valid.

![Operating region](../results/payload_bounds/payload_operating_region.png)

Rejected cases, including doubled noise: {rejected_text}. These are retained failures of the declared operating gate. Their absence from plotted curves does not mean zero detection limit.

![Calibration sensitivity](../results/payload_bounds/payload_calibration_region.png)

The residual is the standard deviation of the *differential* correlated dB error after reference subtraction. It is therefore added once. It is a zero mean random sensitivity scenario, not a bound against arbitrary systematic drift. Previous bounded bias controls remain relevant.

## Changing geometry

For an ideal 550 km overhead circular pass, local information is integrated along the time dependent ray and link, with independent nuisance coefficients per time block and shared concentration. A matched reference pass is charged the same transmission time. Both passes require the same atmosphere and accurate instantaneous gain normalization. Orbital waiting time is excluded. Doubling midpoint resolution from 20 to 40 blocks changes standard deviations by less than 0.05%.

| Center elevation | Total reference + sample time (s) | Acetonitrile local 95% limit (µg/m³) |
|---|---:|---:|
{moving_table}

These are conditional information/estimator variance calculations along a moving geometry. They do not implement Doppler tracking, synchronization, orbit uncertainty or a raw moving waveform receiver. Those requirements remain in Task 2.2.

## Environmental guideline assessment

The [WHO 2021 guidelines](https://www.who.int/publications/i/item/9789240034228/) concern PM2.5, PM10, O3, NO2, SO2 and CO. They do not supply a benchmark for methanol or acetonitrile. The [WHO formaldehyde guideline](https://www.who.int/teams/environment-climate-change-and-health/air-quality-and-health/health-impacts/types-of-pollutants) is 100 µg/m³ averaged over 30 minutes in its indoor air quality context. It is not an outdoor satellite path threshold. A modeled formaldehyde detection limit below that number does not establish applicable compliance.

The WHO PM2.5 and PM10 24 hour levels are 15 and 45 µg/m³. Their averaging period and ground level exposure domain differ from a seconds long slant column enhancement. PM mass information remains impractical and composition is uncalibrated. The WHO guidelines are health recommendations, not a universal legally binding certification rule. No positive compliance conclusion is supported.

## Verification and reproducibility

Run `scripts/acquire_payload_spectroscopy.py`, `scripts/run_payload_physics.py`, `scripts/run_payload_bounds.py`, `scripts/check_payload_moving_geometry.py`, `scripts/check_payload_thermal.py`, `scripts/verify_payload_bounds.py`, and `scripts/report_payload_bounds.py`. The experiment may run concurrently with physics production; it cannot pass until the final physics manifest and every consumed hash match. Input acquisition preserves the historical manifests. Layer caches carry input fingerprints and refuse silent reuse after inputs change.

The new unit tests check quadrature convergence, information ordering, independent density derivatives and the joint Fisher inverse for a finite reference. The numerical verification checks saved response counts, resource budgets, units, estimator constraints, efficiency and output hashes. Original spectroscopy acquisition gaps remain excluded; matching the recovered files does not fill missing catalog requests.

## Remaining work, risks and next steps

Tasks 4.1 and 4.3 now have the requested computational extension; Task 4.2 has fixed and moving geometry sensitivity under the explicitly stated calibration assumptions. Positive environmental compliance and field performance remain unverified. The main remaining engineering work is a realizable multiband resource design and moving receiver implementation, Tasks 2.1 and 2.2. The ideal 60–400 GHz simultaneous tone reference still lacks that architecture. The unfavorable contiguous E-band result remains unchanged.

The scientific priority is to obtain more useful spectral information while preserving communication resources, then test gain/reference stability on measured transmissions with independent concentration truth. PM and weak methanol performance remain open for Tasks 3.1 and 3.2. More Monte Carlo trials or a neural network alone cannot establish information absent from the signal model.
'''
    (ROOT/'docs/45_payload_bounds_results.md').write_text(md, encoding='utf-8')
    tex = ['\\begin{tabular}{lrrr}\\toprule', 'Gas & Limit (\\ugm) & Limit (ppm) & Efficiency\\\\\\midrule']
    for r in headline.itertuples(index=False):
        tex.append(f'{r.name} & {r.payload_lod95_ug_m3:.3f} & {r.payload_lod95_ppm:.6f} & {r.qpsk_efficiency_pct:.1f}\\%\\\\')
    tex += ['\\bottomrule\\end{tabular}']
    (ROOT/'paper/payload_bounds_rows.tex').write_text('\n'.join(tex)+'\n')
    numbers = dict(eligible_cases=len(eligible), validation_controls=len(validation),
        power_min_pct=float(validation.recall_pct.min()), power_max_pct=float(validation.recall_pct.max()),
        acetonitrile_lod_min=float(acet.response_lod95_ug_m3.min()), acetonitrile_lod_max=float(acet.response_lod95_ug_m3.max()))
    (OUT/'report_numbers.json').write_text(json.dumps(numbers, indent=2)+'\n')
    macros = {'PayloadEligible': str(len(eligible)), 'PayloadControls': str(len(validation)),
        'PayloadPowerMin': f'{validation.recall_pct.min():.2f}', 'PayloadPowerMax': f'{validation.recall_pct.max():.2f}',
        'PayloadLodMin': f'{acet.response_lod95_ug_m3.min():.3f}', 'PayloadLodMax': f'{acet.response_lod95_ug_m3.max():.3f}'}
    (ROOT/'paper/payload_bounds_numbers.tex').write_text(''.join('\\newcommand{\\'+key+'}{'+value+'}\n' for key, value in macros.items()))
    print(headline.to_string(index=False))
    print(json.dumps(numbers))


if __name__ == '__main__':
    main()
