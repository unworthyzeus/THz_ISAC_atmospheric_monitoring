"""Frozen-design evaluation: low recalls, 95% limits and concentration errors."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, binomtest
from scipy.optimize import brentq
from scipy.constants import gas_constant
from joint_receiver_support import ROOT, OUT, TARGETS, MASSES, Z, fit, write
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.payload_sensing import draw_attenuation, attenuation_variance


def draw_scores(rng, signal, r, sigma, draws=10000):
    factor=sigma*np.linalg.cholesky(r['correlation']); scores=[]
    for start in range(0,draws,500):
        count=min(500,draws-start)
        sample,ok=draw_attenuation(rng,signal,r['snr'],r['count']['payload'],count,'m2m4')
        ref,rok=draw_attenuation(rng,np.zeros(len(signal)),r['snr'],r['count']['payload'],count,'m2m4')
        if not ok.all() or not rok.all(): raise RuntimeError('Invalid inversion is a failed experiment')
        scores.append((sample-ref+rng.normal(size=sample.shape)@factor.T)@r['operator'].T)
    return np.concatenate(scores)


def response_limit(r,j,direction,sigma):
    local=(Z+norm.ppf(.95))*r['sd'][j]
    upper=min(4*local,1/max(direction))
    def margin(c):
        v=attenuation_variance(r['snr']*10**(-direction*c/10),r['count']['payload'],'m2m4')+attenuation_variance(r['snr'],r['count']['payload'],'m2m4')
        h=r['operator'][j]
        sd=np.sqrt((h*h)@v+sigma*sigma*h@r['correlation']@h)
        return c-Z*r['sd'][j]-norm.ppf(.95)*sd
    return brentq(margin,0,upper) if margin(upper)>=0 else np.nan


def percentage_metrics(positive, null, threshold, truth):
    tp=int((positive>threshold).sum()); fp=int((null>threshold).sum())
    n=len(positive); n0=len(null); fn=n-tp; tn=n0-fp
    ci=binomtest(tp,n).proportion_ci(); fci=binomtest(fp,n0).proportion_ci()
    errors=positive-truth; rmse=float(np.sqrt(np.mean(errors**2)))
    return dict(trials=n,null_trials=n0,hits=tp,misses=fn,false_count=fp,recall_pct=100*tp/n,
        recall_ci95_lower_pct=ci.low*100,recall_ci95_upper_pct=ci.high*100,
        miss_rate_pct=100*fn/n,false_alarm_pct=100*fp/n0,false_alarm_ci95_lower_pct=fci.low*100,
        false_alarm_ci95_upper_pct=fci.high*100,specificity_pct=100*tn/n0,
        precision_at_50pct_prevalence_pct=100*tp/(tp+fp) if tp+fp else np.nan,
        f1_at_50pct_prevalence_pct=200*tp/(2*tp+fp+fn),balanced_accuracy_pct=50*(tp/n+tn/n0),
        concentration_bias_ug_m3=float(errors.mean()),concentration_rmse_ug_m3=rmse,
        relative_bias_pct=float(100*errors.mean()/truth),relative_rmse_pct=100*rmse/truth,
        negative_estimate_pct=float(100*np.mean(positive<0)))


def main():
    plans=dict(selected=HoppingPlan(**json.loads((OUT/'selection.json').read_text())['plan']),
        uniform=HoppingPlan(**json.loads((ROOT/'results/receiver_design/hopping_plan.json').read_text())['plan']))
    write('evaluation_protocol.json',dict(seed=2026093002,trials_per_class=10000,family_alpha=.01,family_size=8,
        calibration='Persistent zero mean random dB residual, exponential 10 GHz correlation, once per acquisition. Assumed, not measured.',
        resources='One RF chain, 16 sequential 16 MHz blocks, 23 dBm active power, 6 dB NF, reference and sample charged equally, 1 ms settling/hop, same frame/pilot counts.',
        selection='Standard 45 degree design only. Exact spectra, January weather, other elevations and these Monte Carlo samples do not select bands.',
        metrics='Single-target positive controls with all other targets unknown in joint fit; PM10 positive mixture fine/coarse 49/41. Separate all-gas/PM mixture retained. Precision and F1 assume 50% prevalence; not population estimates.',
        concentration_grid_ug_m3=[1,5,10],pm_grid_ug_m3=[15,45,49,90],
        total_reference_plus_sample_s=[2.,20.,100.],residual_std_db=[0.,.0001,.001],
        recall_limit='Positive-response variance solved before trials, at most 1 dB absorption. No valid in-domain solution is recorded as unavailable, never extrapolated to claim success.',
        fresh_scope='January weather was not used in band selection, but was present in older project studies. It is a held-out design condition, not a new population sample.',
        interpretation='Predicted, Monte Carlo simulated and measured results remain distinct. No measured field recall exists.'))
    rows=[]; sensitivities=[]; rates=[]; failures=[]; rng=np.random.default_rng(2026093002)
    for plan_name,plan in plans.items():
        for profile in ['standard','igra_01']:
            for elevation in [30.,45.,60.,90.]:
                data=dict(np.load(OUT/f'{plan_name}_{profile}_{int(elevation)}_physics.npz'))
                for duration,sigma in [(t,s) for t in [2.,20.,100.] for s in [0.,.0001,.001]]:
                    key=f'{plan_name}_{profile}_{int(elevation)}_{int(duration)}_{sigma:g}'
                    try: r=fit(data,plan,total_s=duration,sigma=sigma,elevation=elevation)
                    except ValueError as exc:
                        failures.append(dict(case=key,status='rejected',reason=str(exc))); continue
                    rates.append(dict(case=key,plan=plan_name,profile=profile,elevation_deg=elevation,total_s=duration,
                        residual_std_db=sigma,gaussian_rate_bps=r['gaussian_rate_bps'],sensing_tones=int(r['mask'].sum()),
                        transmission_s=r['count']['transmission_total_s'],settling_s=r['count']['settling_total_s']))
                    for j,name in enumerate(TARGETS):
                        floor=(Z+norm.ppf(.95))*r['sd'][j]
                        direction=r['design'][:,j] if j<7 else r['design'][:,5]*49/90+r['design'][:,6]*41/90
                        corrected=response_limit(r,j,direction,sigma)
                        mass=(MASSES.get(name,NATURAL_MOLAR_MASS_G_MOL.get(name,np.nan)))
                        ppm_per_ug=gas_constant*float(data['surface_temperature_k'])/(float(data['surface_pressure_pa'])*mass)
                        sensitivities.append(dict(case=key,plan=plan_name,profile=profile,elevation_deg=elevation,total_s=duration,
                            residual_std_db=sigma,target=name,sd_ug_m3=r['sd'][j],local_lod95_ug_m3=floor,
                            response_lod95_ug_m3=corrected,surface_equivalent_response_lod95_ppm=corrected*ppm_per_ug,
                            surface_equivalent_local_lod95_ppm=floor*ppm_per_ug,
                            predicted_recall_at_1_ug_pct=100*norm.sf(Z-1/r['sd'][j]),
                            predicted_recall_at_5_ug_pct=100*norm.sf(Z-5/r['sd'][j]),
                            predicted_recall_at_10_ug_pct=100*norm.sf(Z-10/r['sd'][j])))
                    if not (elevation==45 and ((plan_name=='selected' and profile=='standard') or (duration==20 and sigma==.0001))): continue
                    null=draw_scores(rng,np.zeros(len(r['snr'])),r,sigma)
                    family=int(np.any(null>Z*r['sd'],axis=1).sum())
                    saved={k:r[k] for k in ['design','nuisance','operator','sd','covariance','snr','mask','correlation']}
                    saved.update(null=null,z=Z,payload=r['count']['payload'],sigma=sigma,labels=TARGETS)
                    for j,name in enumerate(TARGETS):
                        direction=r['design'][:,j] if j<7 else r['design'][:,5]*49/90+r['design'][:,6]*41/90
                        floor=response_limit(r,j,direction,sigma)
                        concentrations=[('low',v) for v in ([1.,5.,10.] if j<5 else [15.,45.,49.,90.])]
                        if np.isfinite(floor): concentrations.append(('response95',float(floor)))
                        else: failures.append(dict(case=key,target=name,status='no 95% response limit in the <=1 dB domain',formal_local_lod95_ug_m3=float((Z+norm.ppf(.95))*r['sd'][j])))
                        mass=MASSES.get(name,NATURAL_MOLAR_MASS_G_MOL.get(name,np.nan))
                        ppm_per_ug=gas_constant*float(data['surface_temperature_k'])/(float(data['surface_pressure_pa'])*mass)
                        for control,concentration in concentrations:
                            score_key=f'{name}_{control}_{concentration:.12g}'
                            scores=draw_scores(rng,direction*concentration,r,sigma)[:,j]
                            saved[score_key]=scores
                            metrics=percentage_metrics(scores,null[:,j],Z*r['sd'][j],concentration)
                            rows.append(dict(case=key,plan=plan_name,profile=profile,target=name,control=control,score_key=score_key,
                                total_s=duration,residual_std_db=sigma,concentration_ug_m3=concentration,
                                surface_equivalent_ppm=concentration*ppm_per_ug,maximum_absorption_db=max(direction*concentration),
                                family_false_count=family,family_false_alarm_pct=family/100,**metrics))
                    truth=np.r_[np.ones(5),49.,41.]
                    mixture=draw_scores(rng,r['design']@truth,r,sigma)
                    saved.update(mixture=mixture,mixture_truth=truth)
                    for j,name in enumerate(TARGETS):
                        concentration=np.r_[truth,90.][j]
                        rows.append(dict(case=key,plan=plan_name,profile=profile,target=name,control='joint mixture',score_key='mixture',
                            total_s=duration,residual_std_db=sigma,concentration_ug_m3=concentration,
                            family_false_count=family,family_false_alarm_pct=family/100,
                            **percentage_metrics(mixture[:,j],null[:,j],Z*r['sd'][j],concentration)))
                    np.savez_compressed(OUT/(key+'_responses.npz'),**saved)
                    print(key,'responses complete; family false alarms',family/100,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'response_metrics.csv',index=False)
    pd.DataFrame(sensitivities).to_csv(OUT/'sensitivity.csv',index=False)
    pd.DataFrame(rates).to_csv(OUT/'resources_and_rates.csv',index=False)
    write('failures.json',failures)
    print(pd.DataFrame(rows).query("plan=='selected' and profile=='standard' and (control=='response95' or control=='joint mixture')")[["target","control","concentration_ug_m3","recall_pct","miss_rate_pct","relative_rmse_pct"]].to_string(index=False))


if __name__=='__main__': main()
