"""Conditional information along an overhead circular pass, with charged reference.

Matched reference and sample are separate passes at the same geometric states.
This evaluates time dependent information, not synchronization or RF tracking.
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.physical_spectroscopy import DB_PER_NEPER
from thz_isac.link_budget import LEOLinkBudgetConfig
from thz_isac.waveform_link import physical_channel_gain
from thz_isac.communication_capacity import waterfill_power
from thz_isac.payload_sensing import attenuation_variance, resource_counts
from thz_isac.payload_information import attenuation_crlb

OUT = ROOT/'results/payload_bounds'


def projected_covariance(blocks):
    # Each block has its own unknown spectral nuisance coefficients. Shared
    # pollutant concentrations are fitted across the complete path by SVD.
    stacked = []
    for d, n, v in blocks:
        x, w = d/np.sqrt(v[:, None]), n/np.sqrt(v[:, None])
        w /= np.linalg.norm(w, axis=0)
        u, s, _ = np.linalg.svd(w, full_matrices=False)
        q = u[:, s > s[0]*1e-12]
        stacked.append(x-q@(q.T@x))
    x = np.concatenate(stacked)
    scale = np.linalg.norm(x, axis=0)
    _, s, vh = np.linalg.svd(x/scale, full_matrices=False)
    if s[-1] < s[0]*1e-12:
        raise ValueError('Unidentifiable moving geometry')
    a = (vh.T/s)/scale[:, None]
    return a@a.T


def main():
    model = StandardAtmosphere()
    f = np.linspace(60, 400, 256)
    gas = np.load(OUT/'standard_layers.npz')['gas_db_per_m_ug_m3']
    optics = np.column_stack([pd.read_csv(ROOT/f'results/task_completion/{n}_particle_optics.csv').mie_extinction.to_numpy()[:256] for n in ['fine', 'coarse']])
    edges = np.unique(np.r_[np.arange(0, 12001, 1000), np.arange(16000, 40001, 4000), np.arange(50000, 100001, 10000)])
    thermal_edges = np.unique(np.r_[np.arange(0, 20001, 100), np.arange(20500, 100001, 500)])
    thermal = satellite_slant_quadrature(model, 45, top_altitude_m=100000, layer_edges_m=thermal_edges, order=4)
    tt, pp, ww, _ = model.state(thermal.altitude_m)
    gamma = np.concatenate([specific_attenuation(f, tt[i:i+32], pp[i:i+32], ww[i:i+32]*1e6*Boltzmann*tt[i:i+32])['total'] for i in range(0, len(tt), 32)])
    config = LEOLinkBudgetConfig(**json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())['reference_link'])
    re, rs = 6371000., 6921000.
    angular_speed = np.sqrt(3.986004418e14/rs**3)
    results, trace = [], []
    for center in [45., 90.]:
        el = np.deg2rad(center)
        distance = -re*np.sin(el)+np.sqrt(rs**2-re**2*np.cos(el)**2)
        phi0 = np.arctan2(distance*np.cos(el), re+distance*np.sin(el))
        for total in [20., 100.]:
            duration = total/2
            for bins in [20, 40]:
                blocks = {m: [] for m in ['m2m4', 'qpsk_crlb', 'magnitude_crlb']}
                counts = resource_counts(duration/bins)
                actual_duration = bins*counts['charged_duration_s']
                # The 40-bin 10-second case uses 0.25 s, all a whole frame.
                if abs(actual_duration-duration) > 1e-9:
                    raise ValueError('Trajectory bins must contain complete frames')
                for k in range(bins):
                    t = -duration/2+(k+.5)*duration/bins
                    phi = phi0+angular_speed*t
                    elevation = np.rad2deg(np.arctan2(rs*np.cos(phi)-re, rs*abs(np.sin(phi))))
                    ray = satellite_slant_quadrature(model, elevation, top_altitude_m=100000, layer_edges_m=edges, order=4)
                    tr = satellite_slant_quadrature(model, elevation, top_altitude_m=100000, layer_edges_m=thermal_edges, order=4)
                    layers = gamma*tr.path_weights_m[:, None]/1000
                    bg = layers.sum(0)
                    sky = downwelling_brightness_k(f, tt, layers)
                    design_gas = np.einsum('i,ifg->fg', ray.path_weights_m, gas)
                    pm = optics*DB_PER_NEPER*1e-9*(ray.path_weights_m@np.exp(-ray.altitude_m/1000))
                    gain = physical_channel_gain(f, bg, sky, config, elevation)['gain_per_watt']
                    power = waterfill_power(gain, 10**((23-30)/10))
                    snr = gain*power
                    keep = snr >= 10**.5
                    s = snr[keep]
                    d = np.column_stack([design_gas[keep, :3], pm[keep]])
                    n = np.column_stack([np.ones(keep.sum()), bg[keep], design_gas[keep, 3:]])
                    for method in blocks:
                        variance = 2*(attenuation_variance(s, counts['payload'], 'm2m4') if method == 'm2m4'
                            else attenuation_crlb(s, counts['payload'], 'qpsk' if method == 'qpsk_crlb' else 'magnitude'))
                        blocks[method].append((d, n, variance))
                    trace.append(dict(center_elevation_deg=center, total_transmission_s=total, bins=bins,
                        time_from_center_s=t, elevation_deg=elevation, sensing_tones=int(keep.sum()),
                        payload_per_block=counts['payload'], radiated_power_w=float(power.sum())))
                for method, data in blocks.items():
                    cov = projected_covariance(data)
                    for j, name in enumerate(['H2CO', 'CH3OH', 'CH3CN', 'PM2.5', 'PMcoarse']):
                        results.append(dict(center_elevation_deg=center, total_transmission_s=total,
                            bins=bins, method=method, target=name, sd_ug_m3=float(np.sqrt(cov[j, j]))))
                print(center, total, bins, 'moving geometry evaluated', flush=True)
    table = pd.DataFrame(results)
    pd.DataFrame(trace).to_csv(OUT/'moving_geometry_trace.csv', index=False)
    table.to_csv(OUT/'moving_geometry.csv', index=False)
    pivot = table.pivot(index=['center_elevation_deg', 'total_transmission_s', 'method', 'target'], columns='bins', values='sd_ug_m3')
    error = float(np.max(abs(pivot[20]/pivot[40]-1)))
    (OUT/'moving_geometry_manifest.json').write_text(json.dumps(dict(
        status='passed' if error < .01 else 'convergence_failed', maximum_sd_relative_change_20_vs40=error,
        convergence_threshold=.01, orbit='Circular 550 km overhead pass, stationary Earth, mu=3.986004418e14 m3/s2',
        reference='Separate matched reference pass, same atmosphere and normalized instantaneous gain. Reference transmission time and energy charged; orbital waiting time excluded.',
        scope='Time dependent local information with blockwise nuisance projection; continuum approximated by converged midpoint blocks. Not raw moving waveform or a demonstration of realizable gain tracking.',
        limitations='Constant pollutant column profile and weather; no unknown normalization errors, Earth rotation, orbit uncertainty, Doppler or synchronization implementation.'), indent=2)+'\n')
    if error >= .01:
        raise RuntimeError('Moving geometry quadrature did not converge')


if __name__ == '__main__':
    main()
