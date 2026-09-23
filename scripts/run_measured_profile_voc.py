"""Recompute VOC line shapes on selected real weather, retaining assumed abundance profiles."""
from pathlib import Path
import sys,json,time,hashlib
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from thz_isac.atmospheric_profiles import sounding_atmosphere,ExtendedMeasuredAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule,concentration_ug_m3_to_number_density_cm3,MOLAR_MASS_G_MOL,DB_PER_NEPER
OUT=ROOT/'results/task_completion'


def main():
    start=time.perf_counter();source=ROOT/'data/processed/task_completion/all_isotopes_0_3000GHz.csv'
    lines=pd.read_csv(source);lines=lines[lines.molecule.isin(['H2CO','CH3OH','CH3CN'])]
    f=np.linspace(60,400,256);summary=[];saved={};hashes={}
    for month in [1,4,7,9]:
        path=OUT/f'igra_{month:02d}_measured.csv';frame=pd.read_csv(path);measured=sounding_atmosphere(frame)
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        atmosphere=ExtendedMeasuredAtmosphere(measured)
        for order in ([1,2] if month==9 else [2]):
            ray=satellite_slant_quadrature(atmosphere,45,top_altitude_m=100000-measured.ground_altitude_m,layers=50,order=order,
                    earth_radius_m=6371000+measured.ground_altitude_m,satellite_altitude_m=550000-measured.ground_altitude_m)
            t,p,_,_=atmosphere.state(ray.altitude_m)
            gas=np.zeros((len(f),3))
            for j,name in enumerate(['H2CO','CH3OH','CH3CN']):
                density=concentration_ug_m3_to_number_density_cm3(1.,MOLAR_MASS_G_MOL[name])*np.exp(-ray.altitude_m/1500)
                for i,z in enumerate(ray.altitude_m):
                    cross=molecular_cross_section_cm2_per_molecule(lines,f,name,temperature_k=t[i],pressure_pa=p[i])
                    gas[:,j]+=DB_PER_NEPER*cross*density[i]*100*ray.path_weights_m[i]
                print(month,order,name,flush=True)
            saved[f'month{month:02d}_order{order}']=gas
            for j,name in enumerate(['H2CO','CH3OH','CH3CN']):
                summary.append(dict(month=month,order=order,target=name,datetime=frame.datetime.iloc[0],
                    integration_nodes=len(ray.altitude_m),peak_db_per_ug_m3=float(gas[:,j].max())))
    saved['frequency_ghz']=f
    np.savez_compressed(OUT/'measured_weather_voc.npz',**saved)
    pd.DataFrame(summary).to_csv(OUT/'measured_weather_voc_summary.csv',index=False)
    error=np.linalg.norm(saved['month09_order1']-saved['month09_order2'])/np.linalg.norm(saved['month09_order2'])
    manifest=dict(status='passed' if error<.001 else 'convergence_failed',september_order1_vs2_relative_rms=float(error),
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),weather_input_hashes=hashes,
                  wall_seconds=time.perf_counter()-start,profile='Measured weather plus explicit P.835 upper continuation; VOC mass profile exp(-z/1500m) still assumed',
                  output_sha256=hashlib.sha256((OUT/'measured_weather_voc.npz').read_bytes()).hexdigest())
    (OUT/'measured_voc_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if error>=.001:raise SystemExit('Measured profile convergence failed')
    print('Measured VOC weather study completed',flush=True)


if __name__=='__main__':main()
