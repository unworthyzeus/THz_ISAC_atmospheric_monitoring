"""Recompute spectral and link inputs over real weather and refracted rays."""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere, sounding_atmosphere, ExtendedMeasuredAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule, concentration_ug_m3_to_number_density_cm3, DB_PER_NEPER
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL, natural_mass_design
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL

OUT = ROOT/'results/payload_bounds'
OLD = ROOT/'results/task_completion'
GASES = ['H2CO', 'CH3OH', 'CH3CN', 'CO', 'O3', 'SO2', 'NO2']
ELEVATIONS = [5, 15, 30, 45, 60, 90]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    source = ROOT/'data/raw/payload_bounds/lines.csv'
    lines = pd.read_csv(source)
    acquisition = json.loads((OUT/'spectroscopy_acquisition.json').read_text())
    if not all(r['matches_previous'] for r in acquisition['records']):
        raise ValueError('Reacquired catalog differs from frozen source')
    f = np.linspace(60, 400, 256)
    optics = np.column_stack([pd.read_csv(OLD/f'{n}_particle_optics.csv').mie_extinction.to_numpy()[:256] for n in ['fine', 'coarse']])
    cache_inputs = dict(lines=sha(source), script=sha(Path(__file__)))
    summary, comparisons, outputs = [], [], {}
    for label in ['standard', 'igra_01', 'igra_04', 'igra_07', 'igra_09']:
        ground = 0.
        model = StandardAtmosphere()
        if label != 'standard':
            path = OLD/(label+'_measured.csv')
            measured = sounding_atmosphere(pd.read_csv(path))
            model = ExtendedMeasuredAtmosphere(measured)
            ground = measured.ground_altitude_m
            cache_inputs[label] = sha(path)
        top = 100000-ground
        edges = np.unique(np.r_[np.arange(0, 12001, 1000), np.arange(16000, 40001, 4000), np.arange(50000, top, 10000), top])
        order = 4 if label == 'standard' else 2
        options = dict(top_altitude_m=top, satellite_altitude_m=550000-ground,
                       earth_radius_m=6371000+ground, layer_edges_m=edges, order=order)
        ray = satellite_slant_quadrature(model, 45, **options)
        cache = OUT/(label+'_layers.npz')
        fingerprint = json.dumps(cache_inputs, sort_keys=True)
        if cache.exists():
            local = np.load(cache)
            if str(local['fingerprint']) != fingerprint:
                raise ValueError('Layer cache input changed; preserve old output and explicitly rebuild')
            gas = local['gas_db_per_m_ug_m3']
        else:
            t, p, _, _ = model.state(ray.altitude_m)
            gas = np.zeros((len(t), len(f), len(GASES)))
            for j, name in enumerate(GASES):
                density = concentration_ug_m3_to_number_density_cm3(1., NATURAL_MOLAR_MASS_G_MOL[name])*np.exp(-ray.altitude_m/1500)
                subset = lines[lines.molecule == name]
                for i in range(len(t)):
                    cross = molecular_cross_section_cm2_per_molecule(subset, f, name, temperature_k=t[i], pressure_pa=p[i])
                    gas[i, :, j] = DB_PER_NEPER*cross*density[i]*100
                print(label, name, len(t), 'layers computed', flush=True)
            np.savez_compressed(cache, fingerprint=fingerprint, altitude_m=ray.altitude_m, gas_db_per_m_ug_m3=gas)
        # Refined thermal transfer is independent of expensive molecular lines.
        thermal_edges = np.unique(np.r_[np.arange(0, 20001, 100), np.arange(20500, top, 500), top])
        thermal_options = dict(options, layer_edges_m=thermal_edges, order=4)
        thermal_ray = satellite_slant_quadrature(model, 45, **thermal_options)
        tt, pp, ww, _ = model.state(thermal_ray.altitude_m)
        gamma = np.concatenate([specific_attenuation(f, tt[i:i+32], pp[i:i+32], ww[i:i+32]*1e6*Boltzmann*tt[i:i+32])['total'] for i in range(0, len(tt), 32)])
        surface_t, surface_p, _, _ = model.state(np.array([0.]))
        for el in ELEVATIONS:
            ray = satellite_slant_quadrature(model, el, **options)
            thermal_ray = satellite_slant_quadrature(model, el, **thermal_options)
            layers = gamma*thermal_ray.path_weights_m[:, None]/1000
            integrated = np.einsum('i,ifg->fg', ray.path_weights_m, gas)
            pm = optics*DB_PER_NEPER*1e-9*(ray.path_weights_m@np.exp(-ray.altitude_m/1000))
            background = layers.sum(0)
            sky = downwelling_brightness_k(f, tt, layers)
            key = f'{label}_{el:02d}'
            path = OUT/(key+'_physics.npz')
            np.savez_compressed(path, frequency_ghz=f, gas=integrated, pm=pm,
                background_db=background, sky_temperature_k=sky, surface_temperature_k=surface_t[0],
                surface_pressure_pa=surface_p[0], ground_altitude_m=ground)
            outputs[path.name] = sha(path)
            summary.append(dict(case=key, profile=label, elevation_deg=el, gas_nodes=len(ray.altitude_m),
                thermal_nodes=len(tt), ground_altitude_m=ground, apparent_elevation_deg=ray.apparent_elevation_deg,
                atmospheric_path_m=ray.atmospheric_path_m, surface_temperature_k=surface_t[0], surface_pressure_pa=surface_p[0]))
            if el == 45:
                old = (np.load(OLD/'physics_order4.npz')['gas'][:256] if label == 'standard'
                       else np.load(OLD/'measured_weather_voc.npz')[f'month{label[-2:]}_order2'])
                names = GASES if label == 'standard' else GASES[:3]
                corrected = natural_mass_design(old, names, [MOLAR_MASS_G_MOL[n] for n in names])
                for j, name in enumerate(names):
                    error = np.linalg.norm(integrated[:, j]-corrected[:, j])/np.linalg.norm(corrected[:, j])
                    comparisons.append(dict(profile=label, target=name, relative_rms=error, passed=bool(error < .001)))
        print(label, 'six elevations saved', flush=True)
    pd.DataFrame(summary).to_csv(OUT/'physical_cases.csv', index=False)
    pd.DataFrame(comparisons).to_csv(OUT/'physics_reproduction.csv', index=False)
    passed = all(r['passed'] for r in comparisons)
    (OUT/'physics_manifest.json').write_text(json.dumps(dict(status='passed' if passed else 'failed',
        inputs=cache_inputs, outputs=outputs, wall_seconds=time.perf_counter()-start,
        scope='Recomputed refracted paths, Voigt spectra, P.676 background and thermal transfer; matched known weather, assumed concentration scale heights; static elevation cases'), indent=2)+'\n')
    if not passed:
        raise RuntimeError('Historical spectrum reproduction failed')


if __name__ == '__main__':
    main()
