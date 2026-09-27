"""Thermal quadrature refinement over every new physical case."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere, sounding_atmosphere, ExtendedMeasuredAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
OUT = ROOT/'results/payload_bounds'


def main():
    f = np.linspace(60, 400, 256)
    rows = []
    for label in ['standard', 'igra_01', 'igra_04', 'igra_07', 'igra_09']:
        ground, model = 0., StandardAtmosphere()
        if label != 'standard':
            measured = sounding_atmosphere(pd.read_csv(ROOT/f'results/task_completion/{label}_measured.csv'))
            ground, model = measured.ground_altitude_m, ExtendedMeasuredAtmosphere(measured)
        top = 100000-ground
        edges = np.unique(np.r_[np.arange(0, 20001, 100), np.arange(20500, top, 500), top])
        options = dict(top_altitude_m=top, earth_radius_m=6371000+ground, satellite_altitude_m=550000-ground,
                       layer_edges_m=edges, order=2)
        ray = satellite_slant_quadrature(model, 45, **options)
        t, p, w, _ = model.state(ray.altitude_m)
        gamma = np.concatenate([specific_attenuation(f, t[i:i+32], p[i:i+32], w[i:i+32]*1e6*Boltzmann*t[i:i+32])['total'] for i in range(0, len(t), 32)])
        for el in [5, 15, 30, 45, 60, 90]:
            ray = satellite_slant_quadrature(model, el, **options)
            layers = gamma*ray.path_weights_m[:, None]/1000
            result = dict(background_db=layers.sum(0), sky_temperature_k=downwelling_brightness_k(f, t, layers))
            reference = np.load(OUT/f'{label}_{el:02d}_physics.npz')
            for field, actual in result.items():
                error = float(np.linalg.norm(actual-reference[field])/np.linalg.norm(reference[field]))
                rows.append(dict(case=f'{label}_{el:02d}', field=field, relative_rms=error, threshold=.001, passed=error < .001))
    pd.DataFrame(rows).to_csv(OUT/'thermal_convergence.csv', index=False)
    passed = all(r['passed'] for r in rows)
    (OUT/'thermal_convergence.json').write_text(json.dumps(dict(status='passed' if passed else 'failed',
        controls=len(rows), maximum_relative_rms=max(r['relative_rms'] for r in rows),
        method='Order 2 versus order 4 on refined physical layers, all profiles and elevations'), indent=2)+'\n')
    if not passed:
        raise RuntimeError('Thermal quadrature gate failed')


if __name__ == '__main__':
    main()
