"""Select bands using only the standard design atmosphere and coarse physics."""
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor
import json
import numpy as np
import pandas as pd
from joint_receiver_support import ROOT, OUT, GASES, MASSES, initialize, layer, write, sha
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.payload_sensing import attenuation_variance
from thz_isac.waveform_link import physical_channel_gain
from thz_isac.physical_spectroscopy import concentration_ug_m3_to_number_density_cm3
from design_payload_receiver import config
from receiver_design_physics import atmosphere, ray_for


def main():
    OUT.mkdir(exist_ok=True)
    a=np.load(ROOT/'results/payload_bounds/standard_45_physics.npz')
    mask=(a['frequency_ghz']>220.01)&(a['frequency_ghz']<329.99)
    f=a['frequency_ghz'][mask]
    cache=OUT/'screen_extra_gases.npz'
    if not cache.exists():
        model,ground=atmosphere('standard'); ray=ray_for(model,ground,45.,order=4)
        t,p,_,_=model.state(ray.altitude_m); extra=[]
        with ProcessPoolExecutor(max_workers=6,initializer=initialize,initargs=(f,)) as pool:
            for name in ['CH3Cl','HCOOH']:
                density=concentration_ug_m3_to_number_density_cm3(1.,MASSES[name])*np.exp(-ray.altitude_m/1500)
                values=np.array(list(pool.map(layer,[(name,tt,pp,dd) for tt,pp,dd in zip(t,p,density)],chunksize=4)))
                extra.append(ray.path_weights_m@values)
        np.savez_compressed(cache,frequency_ghz=f,gas=np.column_stack(extra))
    extra=np.load(cache)['gas']
    d=np.column_stack([a['gas'][mask,:3],extra,a['pm'][mask]])
    n=np.column_stack([np.ones(len(f)),a['background_db'][mask],a['gas'][mask,3:],(f-f.mean())/np.ptp(f)])
    cfg=config(1e6)
    gain=physical_channel_gain(f,a['background_db'][mask],a['sky_temperature_k'][mask],cfg,45.)['gain_per_watt']
    snr=gain*10**((23-30)/10)/16
    available=np.flatnonzero(snr>=10**.5)
    plan=HoppingPlan(tuple(np.linspace(228,316,16)))
    thermal=2*attenuation_variance(snr,plan.counts(20.)['payload'],'m2m4')/16
    c=np.diag(thermal)+.0001**2*np.exp(-abs(f[:,None]-f[None,:])/10)
    start=np.array([available[np.argmin(abs(f[available]-v))] for v in plan.centers_ghz])
    def uncertainty(indices):
        return np.sqrt(np.diag(efficient_linear_estimator(d[indices],n[indices],c[np.ix_(indices,indices)]).covariance))[:5]
    baseline=uncertainty(start)
    def objective(indices):
        try:
            ratio=uncertainty(indices)/baseline
            return float(np.max(ratio)+.05*np.log(ratio).sum())
        except (ValueError,np.linalg.LinAlgError):
            return 1e12
    rng=np.random.default_rng(2026093001)
    history=[]; winners=[]
    for restart in range(3):
        indices=start.copy() if restart==0 else np.sort(rng.choice(available,16,replace=False))
        score=objective(indices)
        for iteration in range(8):
            changed=False
            for slot in rng.permutation(16):
                best=score; best_index=indices[slot]
                for candidate in available:
                    if candidate in indices: continue
                    trial=indices.copy();trial[slot]=candidate; value=objective(trial)
                    if value<best-1e-9: best,best_index=value,candidate
                if best_index!=indices[slot]: indices[slot]=best_index;score=best;changed=True
            history.append(dict(restart=restart,iteration=iteration,objective=score,centers_ghz=sorted(f[indices].tolist())))
            print('screen',restart,iteration,'objective',score,flush=True)
            if not changed: break
        winners.append((score,indices.copy()))
    score,indices=min(winners,key=lambda v:v[0]); indices=np.sort(indices)
    selected=HoppingPlan(tuple(f[indices]))
    write('selection.json',dict(plan=asdict(selected),seed=2026093001,objective=score,
        criterion='Minimize maximum five-gas standard-deviation ratio relative to rounded uniform design, plus 0.05 times sum log ratios. Joint PM remains in the inverse problem.',
        screen='One center sample per block; thermal noise divided by 16; exact final 16-tone block integration required. Standard 45 degree atmosphere only; no weather or Monte Carlo evaluation used.',
        coarse_baseline_sd=baseline.tolist(),coarse_selected_sd=uncertainty(indices).tolist(),
        candidate_count=len(available),restarts=3,history=history,
        evaluation='Freeze before evaluating exact frequencies, January weather and fresh response draws. Retain any failed improvement.',
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'results/payload_bounds/standard_45_physics.npz',ROOT/'results/receiver_design/voc_pm_extension/lines.csv',cache]}))
    np.savez_compressed(OUT/'screen.npz',frequency_ghz=f,design=d,nuisance=n,covariance=c,selected_indices=indices,baseline_indices=start)
    print(json.dumps(dict(centers=selected.centers_ghz,baseline_sd=baseline.tolist(),selected_sd=uncertainty(indices).tolist())))


if __name__=='__main__': main()
