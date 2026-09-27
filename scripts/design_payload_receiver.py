"""Select a contiguous modem using design physics, then evaluate exact spectra.

The coarse existing grid is used only for screening. No Monte Carlo outcomes
or seasonal evaluation cases select the band. RF power and noise are design
requirements, not claims about purchased hardware.
"""
from pathlib import Path
from dataclasses import replace, asdict
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from thz_isac.link_budget import LEOLinkBudgetConfig
from thz_isac.waveform_link import OFDMPlan, physical_channel_gain
from thz_isac.communication_capacity import waterfill_power
from thz_isac.payload_sensing import attenuation_variance, resource_counts
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.hopping_receiver import HoppingPlan

OUT = ROOT / 'results/receiver_design'
OLD = ROOT / 'results/payload_bounds'
Z = norm.isf(.01 / 6)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def config(spacing, power_dbm=23., noise_figure_db=6.):
    source = json.loads((ROOT / 'results/tables/physical_feasibility_config.json').read_text())
    return replace(LEOLinkBudgetConfig(**source['reference_link']),
                   subcarrier_bandwidth_hz=spacing, tx_power_dbm=power_dbm,
                   receiver_noise_figure_db=noise_figure_db)


def fit(data, plan, *, total_s=20., residual_db=.001, elevation=45.,
        power_dbm=23., noise_figure_db=6., slope=True, screen_only=False,
        independent_hop_gains=False):
    cfg = config(plan.spacing_hz, power_dbm, noise_figure_db)
    ground = float(data.get('ground_altitude_m', 0.)) / 1000
    cfg = replace(cfg, earth_radius_km=cfg.earth_radius_km + ground,
                  satellite_altitude_km=cfg.satellite_altitude_km - ground)
    link = physical_channel_gain(plan.frequency_ghz, data['background_db'], data['sky_temperature_k'], cfg, elevation)
    total_power = 10 ** ((power_dbm - 30) / 10)
    if isinstance(plan, HoppingPlan):
        power = np.concatenate([waterfill_power(g, total_power) for g in
            link['gain_per_watt'].reshape(-1, plan.subcarriers_per_block)])
    else:
        power = waterfill_power(link['gain_per_watt'], total_power)
    snr = link['gain_per_watt'] * power
    mask = snr >= 10 ** .5
    if mask.sum() < 20:
        raise ValueError('Fewer than 20 tones at 5 dB')
    f = plan.frequency_ghz[mask]
    d = np.column_stack([data['gas'][mask, :3], data['pm'][mask]])
    n = np.column_stack([np.ones(len(f)), data['background_db'][mask], data['gas'][mask, 3:]])
    if slope:
        n = np.column_stack([n, (f - f.mean()) / np.ptp(f)])
    if independent_hop_gains:
        indicators = np.repeat(np.eye(len(plan.centers_ghz)), plan.subcarriers_per_block, axis=0)[mask]
        n = np.column_stack([n, indicators])
    count = (plan.counts(total_s) if isinstance(plan, HoppingPlan) else
             resource_counts(total_s / 2, symbol_duration_s=plan.symbol_duration_s))
    thermal = 2 * attenuation_variance(snr[mask], count['payload'], 'm2m4')
    corr = np.exp(-abs(f[:, None] - f[None, :]) / 10.)
    covariance = np.diag(thermal) + residual_db ** 2 * corr
    if screen_only:
        # The coarse grid cannot resolve the rank of the exact narrow band
        # joint problem. This optimistic single species curvature criterion
        # only selects where to spend the exact spectroscopy computation.
        simple = np.column_stack([np.ones(len(f)), f - f.mean()])
        sd = np.array([np.sqrt(efficient_linear_estimator(d[:, j:j+1], simple,
            covariance).covariance[0, 0]) for j in range(3)])
        return dict(sd=sd, mask=mask, condition=1.)
    estimator = efficient_linear_estimator(d, n, covariance)
    h = np.vstack([estimator.operator, estimator.operator[-2:].sum(axis=0)])
    sd = np.sqrt(np.diag(h @ covariance @ h.T))
    return dict(sd=sd, operator=h, design=d, nuisance=n, covariance=covariance,
                thermal=thermal, correlation=corr, snr=snr, power=power, mask=mask,
                count=count, condition=estimator.target_condition,
                gaussian_input_rate_bps=(plan.net_rate_bps(link['gain_per_watt'], power, total_s)
                    if isinstance(plan, HoppingPlan) else plan.net_rate_bps(link['gain_per_watt'], power)))


def screen():
    data = np.load(OLD / 'standard_45_physics.npz')
    grid = data['frequency_ghz']
    rows = []
    # Widths match integer FFT/CP sample counts. One active RF chain.
    for spacing in [1e6, 2e6, 4e6, 8e6, 16e6, 32e6, 64e6, 100e6]:
        for lo, hi in [(110., 170.), (220., 330.)]:
            for center in np.arange(lo + 16., hi - 15., 4.):
                plan = OFDMPlan((float(center),), spacing_hz=spacing)
                if plan.frequency_ghz.min() <= lo or plan.frequency_ghz.max() >= hi:
                    continue
                f = plan.frequency_ghz
                interpolated = {key: np.column_stack([np.interp(f, grid, data[key][:, j])
                    for j in range(data[key].shape[1])]) if data[key].ndim == 2
                    else np.interp(f, grid, data[key])
                    for key in ['gas', 'pm', 'background_db', 'sky_temperature_k']}
                row = dict(center_ghz=center, spacing_hz=spacing, bandwidth_ghz=256 * spacing / 1e9,
                           band_lower_ghz=lo, band_upper_ghz=hi)
                try:
                    result = fit(interpolated, plan, screen_only=True)
                    floors = (Z + norm.ppf(.95)) * result['sd']
                    row.update(status='eligible', score=float(max(floors[:3])),
                               h2co_lod=floors[0], ch3oh_lod=floors[1], ch3cn_lod=floors[2],
                               condition=result['condition'], sensing_tones=int(result['mask'].sum()))
                except (ValueError, np.linalg.LinAlgError) as exc:
                    row.update(status=str(exc), score=np.inf)
                rows.append(row)
    table = pd.DataFrame(rows).sort_values('score')
    table.to_csv(OUT / 'candidate_screen.csv', index=False)
    winner = table.iloc[0]
    if not np.isfinite(winner.score):
        raise RuntimeError('No candidate identifiable')
    plan = OFDMPlan((float(winner.center_ghz),), spacing_hz=float(winner.spacing_hz))
    write('selection.json', dict(plan=asdict(plan), selection='Minimum worst single species oracle curvature limit across three VOCs; standard 45 degree design case only; 20 seconds, 0.001 dB residual, unknown gain offset and slope. Other species fixed ONLY during coarse screening, which cannot resolve joint rank. Final exact spectra and joint inference are mandatory and may reject the candidate. No global optimality claimed.',
        coarse_score_ug_m3=float(winner.score), candidate_count=len(table),
        design_input_sha256=sha(OLD / 'standard_45_physics.npz'),
        hardware_band_ghz=[float(winner.band_lower_ghz), float(winner.band_upper_ghz)],
        power_dbm=23., noise_figure_db=6., calibration_residual_std_db=.001,
        hardware_status='Frequency and bandwidth compatible with converter family; power, noise, calibration and flight qualification remain requirements. No hardware performance claimed.'))
    print(table.head(8).to_string(index=False), flush=True)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    screen()
    # Fixed broad coverage candidate, not selected on evaluation outcomes.
    hopping = HoppingPlan(tuple(np.linspace(228., 316., 16)))
    write('hopping_plan.json', dict(plan=asdict(hopping),
        rationale='Fixed uniform coverage within one WR3.4 converter family; 16 sequential 16 MHz blocks. No simultaneous RF chains and no uncharged extra power or dwell.',
        source='https://vadiodes.com/wp-content/uploads/2012/01/VDI-737_CC_Product_Manual.pdf',
        converter='WR3.4CCU-M12 and WR3.4CCD-M12; 220-330 GHz; maximum IF 40 GHz; typical intrinsic conversion loss 12 dB.',
        power_dbm=23., noise_figure_db=6., settling_s_status='Sensitivity assumption requiring measurement',
        rf_requirements='Filtered single sideband with 1 GHz IF, synthesizer LO=(RF-1 GHz)/12, one active chain. Image rejection, amplification, antenna calibration, retuning and noise require characterization.',
        transmitter_gap='At -11 dBm input P0.1dB and 12 dB intrinsic conversion loss, unamplified small-signal output is approximately -23 dBm before filters and waveform backoff. The 23 dBm reference requires at least 46 dB extra linear gain; no such flight hardware is demonstrated.',
        calibration='0.001 dB correlated differential residual is a sensitivity case, not measured stability. Independent gain offset per hop is tested separately.'))
