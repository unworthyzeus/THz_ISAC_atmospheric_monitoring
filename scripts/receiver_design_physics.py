"""Exact HITRAN/Mie/thermal spectra for the frozen receiver candidates."""
from pathlib import Path
import sys
import json
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere, sounding_atmosphere, ExtendedMeasuredAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.physical_spectroscopy import concentration_ug_m3_to_number_density_cm3, DB_PER_NEPER
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.aerosol_mie import truncated_lognormal, mass_extinction, physical_diameter_from_aerodynamic
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.waveform_link import OFDMPlan
from design_payload_receiver import OUT, OLD, sha, write

GASES = ['H2CO', 'CH3OH', 'CH3CN', 'CO', 'O3', 'SO2', 'NO2']


def atmosphere(label):
    if label == 'standard':
        return StandardAtmosphere(), 0.
    measured = sounding_atmosphere(pd.read_csv(ROOT/f'results/task_completion/{label}_measured.csv'))
    return ExtendedMeasuredAtmosphere(measured), measured.ground_altitude_m


def edges(ground, thermal=False):
    top = 100000-ground
    return (np.unique(np.r_[np.arange(0, 20001, 100), np.arange(20500, top, 500), top]) if thermal
        else np.unique(np.r_[np.arange(0, 12001, 1000), np.arange(16000, 40001, 4000), np.arange(50000, top, 10000), top]))


def ray_for(model, ground, el, *, thermal=False, order=4):
    return satellite_slant_quadrature(model, el, top_altitude_m=100000-ground,
        satellite_altitude_m=550000-ground, earth_radius_m=6371000+ground,
        layer_edges_m=edges(ground, thermal), order=order)


def integrate_cached(cache, label, el):
    model, ground = atmosphere(label)
    ray = ray_for(model, ground, el, order=int(cache['order']))
    tr = ray_for(model, ground, el, thermal=True)
    layers = cache['gamma']*tr.path_weights_m[:, None]/1000
    return dict(frequency_ghz=cache['frequency_ghz'],
        gas=np.einsum('i,ifg->fg', ray.path_weights_m, cache['gas_layers']),
        pm=cache['optics']*DB_PER_NEPER*1e-9*(ray.path_weights_m@np.exp(-ray.altitude_m/1000)),
        background_db=layers.sum(axis=0),
        sky_temperature_k=downwelling_brightness_k(cache['frequency_ghz'], cache['thermal_temperature'], layers),
        ground_altitude_m=ground)


def main():
    start = time.perf_counter()
    hop = HoppingPlan(**json.loads((OUT/'hopping_plan.json').read_text())['plan'])
    contiguous = OFDMPlan(**json.loads((OUT/'selection.json').read_text())['plan'])
    f = np.r_[hop.frequency_ghz, contiguous.frequency_ghz]
    source = ROOT/'data/raw/payload_bounds/lines.csv'
    inputs = {p.relative_to(ROOT).as_posix(): sha(p) for p in
        [source, OUT/'hopping_plan.json', OUT/'selection.json', Path(__file__), ROOT/'scripts/payload_physics_workers.py']}
    inputs.update({p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/'src/thz_isac').glob('*.py')) if p.name != 'hopping_receiver.py'})
    optics = []
    for density, median, sd, lo, hi, index in [(1500., .5, 1.7, .03, 2.5, 1.5+.01j), (1800., 4., 1.6, 2.5, 10., 1.53+.01j)]:
        bounds = physical_diameter_from_aerodynamic(np.array([lo, hi]), density)
        dist = truncated_lognormal(median, sd, *bounds, density, order=64)
        optics.append(mass_extinction(f, dist, index)['extinction'])
    optics = np.column_stack(optics)
    outputs = {}
    for label in ['standard', 'igra_01', 'igra_04', 'igra_07', 'igra_09']:
        model, ground = atmosphere(label)
        if label != 'standard':
            path = ROOT/f'results/task_completion/{label}_measured.csv'
            inputs[path.relative_to(ROOT).as_posix()] = sha(path)
        order = 4 if label == 'standard' else 2
        ray = ray_for(model, ground, 45., order=order)
        path = OUT/f'{label}_layers.npz'
        fingerprint = json.dumps(inputs, sort_keys=True)
        if path.exists():
            if str(np.load(path)['fingerprint']) != fingerprint:
                raise RuntimeError('Changed physical inputs: retain existing snapshot and choose a new output directory')
        else:
            t, p, _, _ = model.state(ray.altitude_m)
            gas = np.zeros((len(t), len(f), len(GASES)))
            from payload_physics_workers import initialize, evaluate
            with ProcessPoolExecutor(max_workers=6, initializer=initialize, initargs=(str(source), f)) as pool:
                for j, name in enumerate(GASES):
                    density = concentration_ug_m3_to_number_density_cm3(1., NATURAL_MOLAR_MASS_G_MOL[name])*np.exp(-ray.altitude_m/1500)
                    for i, value in pool.map(evaluate, [(name, i, t[i], p[i], density[i]) for i in range(len(t))], chunksize=4):
                        gas[i, :, j] = value
                    print(label, name, 'exact spectra integrated', flush=True)
            tr = ray_for(model, ground, 45., thermal=True)
            tt, pp, ww, _ = model.state(tr.altitude_m)
            gamma = np.concatenate([specific_attenuation(f, tt[i:i+32], pp[i:i+32], ww[i:i+32]*1e6*Boltzmann*tt[i:i+32])['total'] for i in range(0, len(tt), 32)])
            np.savez_compressed(path, frequency_ghz=f, fingerprint=fingerprint, gas_layers=gas,
                gamma=gamma, thermal_temperature=tt, optics=optics, order=order)
        cache = np.load(path)
        outputs[path.name] = sha(path)
        for elevation in [30., 45., 60., 90.]:
            output = OUT/f'{label}_{int(elevation)}_physics.npz'
            np.savez_compressed(output, **integrate_cached(cache, label, elevation))
            outputs[output.name] = sha(output)
        print(label, 'saved', flush=True)
    write('physics_manifest.json', dict(status='completed', inputs=inputs, outputs=outputs,
        wall_seconds=time.perf_counter()-start,
        scope='Exact frequencies, existing HITRAN Voigt/Mie physics and public weather. No radio measurements. First 256 frequencies hopping, last 256 contiguous. Same previously validated layer quadrature.'))


if __name__ == '__main__':
    main()
