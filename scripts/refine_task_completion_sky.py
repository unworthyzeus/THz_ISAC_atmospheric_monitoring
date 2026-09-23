"""Refine thermal radiative transfer without recomputing converged line spectra.

The first 2-vs-4 point sky-temperature check failed its 0.1% threshold. Preserve
that attempt, then refine the low atmosphere where the source function changes.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.microwave_absorption import specific_attenuation,downwelling_brightness_k
OUT=ROOT/'results/task_completion'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    manifest_path=OUT/'physics_manifest.json';manifest=json.loads(manifest_path.read_text())
    if manifest.get('sky_refinement'):
        print('Thermal refinement already applied; retained artifacts unchanged');return
    original=OUT/'physics_initial_manifest.json'
    if not original.exists():original.write_bytes(manifest_path.read_bytes())
    convergence=pd.read_csv(OUT/'integration_convergence.csv')
    convergence.to_csv(OUT/'initial_integration_convergence.csv',index=False)
    atmosphere=StandardAtmosphere();edges=np.unique(np.r_[np.arange(0,20001,100),np.arange(20500,100001,500)])
    results=[]
    for order in [2,4]:
        path=OUT/f'physics_order{order}.npz';data=dict(np.load(path));f=data['frequency_ghz']
        if sha(path)!=manifest['outputs'][path.name]:raise ValueError('Original integration artifact changed')
        backup=OUT/f'physics_initial_order{order}.npz'
        if not backup.exists():backup.write_bytes(path.read_bytes())
        ray=satellite_slant_quadrature(atmosphere,45,top_altitude_m=100000,layer_edges_m=edges,order=order)
        t,p,w,_=atmosphere.state(ray.altitude_m);e=w*1e6*Boltzmann*t
        gamma=np.empty((len(t),len(f)))
        for start in range(0,len(t),32):
            end=start+32;gamma[start:end]=specific_attenuation(f,t[start:end],p[start:end],e[start:end])['total']
        layers=gamma*ray.path_weights_m[:,None]/1000
        sky=downwelling_brightness_k(f,t,layers);results.append(sky)
        data['sky_temperature_k']=sky
        # Preserve a fully replayable radiative-transfer grid separate from
        # the already converged, much more expensive molecular line grid.
        np.savez_compressed(OUT/f'thermal_order{order}.npz',frequency_ghz=f,altitude_m=ray.altitude_m,
                            temperature_k=t,path_weights_m=ray.path_weights_m,layer_attenuation_db=layers,sky_temperature_k=sky)
        np.savez_compressed(path,**data)
        manifest['outputs'][path.name]=sha(path)
    difference=float(np.linalg.norm(results[0]-results[1])/np.linalg.norm(results[1]))
    convergence.loc[convergence.quantity=='sky_temperature_k','relative_rms']=difference
    convergence.loc[convergence.quantity=='sky_temperature_k','passed']=difference<.001
    convergence.to_csv(OUT/'integration_convergence.csv',index=False)
    manifest['outputs']['integration_convergence.csv']=sha(OUT/'integration_convergence.csv')
    manifest['status']='passed' if convergence.passed.all() else 'convergence_failed'
    manifest['sky_refinement']=dict(relative_rms=difference,low_atmosphere_spacing_m=100,above20km_spacing_m=500,
          source_file=str(Path(__file__).relative_to(ROOT)),source_sha256=sha(Path(__file__)),
          initial_manifest_sha256=sha(original),scope='Only thermal source-function quadrature refined; converged gas/PM/background arrays retained')
    # Runtime logs and unrelated concurrently produced artifacts are not part
    # of this stage's owned output set.
    manifest['outputs']={k:v for k,v in manifest['outputs'].items() if not k.endswith('.log')}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    if not convergence.passed.all():raise SystemExit('Thermal refinement still fails')
    print('Thermal refinement passed:',difference)


if __name__=='__main__':main()
