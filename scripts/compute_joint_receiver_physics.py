"""Recompute the frozen selected bands and held-out January atmosphere."""
from concurrent.futures import ProcessPoolExecutor
import json
import numpy as np
from scipy.constants import Boltzmann
from joint_receiver_support import ROOT, OUT, GASES, MASSES, initialize, layer, write, sha
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.physical_spectroscopy import concentration_ug_m3_to_number_density_cm3, DB_PER_NEPER
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.aerosol_mie import physical_diameter_from_aerodynamic, truncated_lognormal, mass_extinction
from receiver_design_physics import atmosphere, ray_for, integrate_cached


def main():
    plan=HoppingPlan(**json.loads((OUT/'selection.json').read_text())['plan'])
    oldplan=HoppingPlan(**json.loads((ROOT/'results/receiver_design/hopping_plan.json').read_text())['plan'])
    f=plan.frequency_ghz
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in [OUT/'selection.json',
        ROOT/'data/raw/payload_bounds/lines.csv',ROOT/'results/receiver_design/voc_pm_extension/lines.csv',
        ROOT/'scripts/joint_receiver_support.py',ROOT/'scripts/compute_joint_receiver_physics.py']}
    optics=[]
    for density,median,sd,lo,hi,index in [(1500.,.5,1.7,.03,2.5,1.5+.01j),(1800.,4.,1.6,2.5,10.,1.53+.01j)]:
        bounds=physical_diameter_from_aerodynamic(np.array([lo,hi]),density)
        dist=truncated_lognormal(median,sd,*bounds,density,order=64)
        optics.append(mass_extinction(f,dist,index)['extinction'])
    optics=np.column_stack(optics)
    for label in ['standard','igra_01']:
        model,ground=atmosphere(label);order=4 if label=='standard' else 2
        ray=ray_for(model,ground,45.,order=order);t,p,_,_=model.state(ray.altitude_m)
        cachepath=OUT/f'{label}_layers.npz'
        fingerprint=json.dumps(inputs,sort_keys=True)
        if cachepath.exists():
            if str(np.load(cachepath)['fingerprint'])!=fingerprint: raise RuntimeError('Changed physical inputs')
        else:
            gas=np.zeros((len(t),256,9));old_extra=np.zeros((len(t),256,2))
            with ProcessPoolExecutor(max_workers=6,initializer=initialize,initargs=(np.r_[f,oldplan.frequency_ghz],)) as pool:
                for j,name in enumerate(GASES):
                    mass=MASSES[name] if name in MASSES else NATURAL_MOLAR_MASS_G_MOL[name]
                    density=concentration_ug_m3_to_number_density_cm3(1.,mass)*np.exp(-ray.altitude_m/1500)
                    width=512 if name in MASSES else 256
                    values=np.array(list(pool.map(layer,[(name,tt,pp,dd,width) for tt,pp,dd in zip(t,p,density)],chunksize=4)))
                    gas[:,:,j]=values[:,:256]
                    if width==512: old_extra[:,:,j-3]=values[:,256:]
                    print(label,name,'exact spectra complete',flush=True)
            tr=ray_for(model,ground,45.,thermal=True)
            tt,pp,ww,_=model.state(tr.altitude_m)
            gamma=np.concatenate([specific_attenuation(f,tt[i:i+32],pp[i:i+32],ww[i:i+32]*1e6*Boltzmann*tt[i:i+32])['total'] for i in range(0,len(tt),32)])
            np.savez_compressed(cachepath,frequency_ghz=f,gas_layers=gas,old_extra=old_extra,
                gamma=gamma,thermal_temperature=tt,optics=optics,order=order,fingerprint=fingerprint)
        cache=np.load(cachepath)
        oldcache=np.load(ROOT/f'results/receiver_design/{label}_layers.npz')
        for el in [30.,45.,60.,90.]:
            new=integrate_cached(cache,label,el)
            old=integrate_cached(oldcache,label,el)
            old={k:(v[:256] if np.ndim(v) else v) for k,v in old.items()}
            ray=ray_for(model,ground,el,order=order)
            extra=np.einsum('i,ifg->fg',ray.path_weights_m,cache['old_extra'])
            old['gas']=np.column_stack([old['gas'][:,:3],extra,old['gas'][:,3:]])
            for name,data in [('selected',new),('uniform',old)]:
                data.update(surface_temperature_k=model.state(np.array([0.]))[0][0],surface_pressure_pa=model.state(np.array([0.]))[1][0])
                np.savez_compressed(OUT/f'{name}_{label}_{int(el)}_physics.npz',**data)
        print(label,'four elevations saved',flush=True)
    write('physics_manifest.json',dict(status='completed',inputs=inputs,
        outputs={p.name:sha(p) for p in OUT.glob('*.npz') if 'physics' in p.name or 'layers' in p.name},
        scope='Exact new tones, same established quadrature; standard design and January held-out weather. No measured radio responses.'))


if __name__=='__main__': main()
