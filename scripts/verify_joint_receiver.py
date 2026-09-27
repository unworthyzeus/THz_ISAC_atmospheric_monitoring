"""Numerical replay for every time/calibration percentage and retained failure."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm,binomtest
from joint_receiver_support import ROOT,OUT,TARGETS,Z,sha,fit,write
from thz_isac.hopping_receiver import HoppingPlan
from evaluate_joint_receiver import percentage_metrics,response_limit
from thz_isac.payload_sensing import attenuation_variance


def main():
    checks=[]
    def check(ok,label):
        checks.append(label)
        if not ok: raise AssertionError(label)
    manifest=json.loads((OUT/'physics_manifest.json').read_text())
    for p,digest in manifest['inputs'].items(): check(sha(ROOT/p)==digest,'input hash '+p)
    for p,digest in manifest['outputs'].items(): check(sha(OUT/p)==digest,'physics hash '+p)
    selection=json.loads((OUT/'selection.json').read_text())
    plan=HoppingPlan(**selection['plan'])
    check(len(plan.centers_ghz)==16,'same RF block count')
    metrics=pd.read_csv(OUT/'response_metrics.csv')
    sensitivity=pd.read_csv(OUT/'sensitivity.csv')
    core=sensitivity[(sensitivity.plan=='selected')&(sensitivity.profile=='standard')&(sensitivity.elevation_deg==45)]
    selected_limits=core[(core.total_s==20)&(core.residual_std_db==.0001)].set_index('target').loc[TARGETS[:5]].local_lod95_ug_m3
    old_limits=sensitivity[(sensitivity.plan=='uniform')&(sensitivity.profile=='standard')&(sensitivity.elevation_deg==45)&(sensitivity.total_s==20)&(sensitivity.residual_std_db==.0001)].set_index('target').loc[TARGETS[:5]].local_lod95_ug_m3
    check((selected_limits<old_limits).all(),'all five exact design limits improve')
    check(set(zip(core.total_s,core.residual_std_db))=={(t,s) for t in [2.,20.,100.] for s in [0.,.0001,.001]},'complete time calibration grid')
    cases=metrics.case.unique()
    check(len(cases)==12,'nine primary controls and three design comparisons')
    for key in cases:
        a=np.load(OUT/(key+'_responses.npz'));h,d,n,c,sd=[a[k] for k in ['operator','design','nuisance','covariance','sd']]
        scales=np.linalg.norm(d,axis=0)
        check(np.max(abs((h[:7]@d)*scales[:,None]/scales[None,:]-np.eye(7)))<1e-5,'scaled target identity '+key)
        check(np.linalg.norm(h@n)/(np.linalg.norm(h)*np.linalg.norm(n))<1e-12,'nuisance rejection '+key)
        check(np.allclose(sd**2,np.diag(h@c@h.T)),'covariance '+key)
        check(np.allclose(h[-1],h[-2]+h[-3]),'PM10 contrast '+key)
        check(np.isclose(a['z'],Z),'family threshold '+key)
        check(np.max(abs(a['null'].mean(0)/sd))*100<5,'null mean '+key)
        check(np.max(abs(a['null'].var(0)/sd**2-1))<.07,'null variance '+key)
        family=int(np.any(a['null']>Z*sd,axis=1).sum())
        check(binomtest(family,10000,.01,alternative='greater').pvalue>.01/12,'family null test '+key)
        for row in metrics[metrics.case==key].itertuples():
            j=TARGETS.index(row.target)
            positive=a['mixture'][:,j] if row.control=='joint mixture' else a[row.score_key]
            replay=percentage_metrics(positive,a['null'][:,j],Z*sd[j],row.concentration_ug_m3)
            for name,value in replay.items():
                check(np.isclose(value,getattr(row,name),rtol=1e-9,atol=1e-9,equal_nan=True),'percentage/error replay '+key+row.target+name)
            check(family==row.family_false_count,'family count '+key)
            check(np.isclose(row.recall_pct+row.miss_rate_pct,100),'recall complement')
            if row.control=='response95':
                check(abs(row.recall_pct-95)<100*(5*np.sqrt(.95*.05/10000)+.002),'95 percent response power '+key+row.target)
                check(row.maximum_absorption_db<=1,'response domain '+key+row.target)
    for target in TARGETS:
        sub=core[core.target==target]
        for sigma in [0.,.0001,.001]:
            values=sub[sub.residual_std_db==sigma].sort_values('total_s').local_lod95_ug_m3.to_numpy()
            check(np.all(np.diff(values)<=1e-5*np.max(values)),'more time cannot worsen local information '+target)
        for t in [2.,20.,100.]:
            values=sub[sub.total_s==t].sort_values('residual_std_db').local_lod95_ug_m3.to_numpy()
            check(np.all(np.diff(values)>=-1e-5*np.max(values)),'more random residual cannot improve information '+target)
    check(not metrics[(metrics.target.str.startswith('PM'))&(metrics.control=='response95')].shape[0],'no fictitious 95 percent PM success')
    check(core[core.target.str.startswith('PM')].response_lod95_ug_m3.isna().all(),'PM limits unavailable in trace domain')
    frames=pd.read_csv(OUT/'selected_raw_frames.csv')
    check(len(frames)==16 and frames.timing_correct.all(),'selected tone modem spot checks')
    check(frames.decoded_outputs_equal.all(),'passive sensing preserves selected modem packets')
    trade=json.loads((OUT/'communication_tradeoff.json').read_text())
    check(trade['gaussian_rate_loss_vs_best_tested_fixed_pct']>0,'architecture has a capacity tradeoff')
    for t in [2.,20.,100.]:
        count=plan.counts(t)
        check(count['transmission_total_s']+count['settling_total_s']<=t+1e-12,'charged time '+str(t))
    global_table=pd.read_csv(OUT/'global_comparison.csv')
    axes=['plan','profile','elevation_deg','total_s','residual_std_db','noise_figure_db']
    check(len(global_table)==2304,'complete common global output count')
    check(global_table[global_table.target.str.startswith('PM')].response_lod95_ug_m3.isna().all(),'no valid PM limit across the entire global grid')
    groups=global_table.groupby(axes)
    check(len(groups)==288,'complete common global condition count')
    expected_axes=[{'selected','uniform'},{'standard','igra_01'},{30.,45.,60.,90.},{2.,20.,100.},{0.,.0001,.001},{6.,17.}]
    for axis,expected in zip(axes,expected_axes):check(set(global_table[axis])==expected,'global axis '+axis)
    plans={'selected':plan,'uniform':HoppingPlan(**json.loads((ROOT/'results/receiver_design/hopping_plan.json').read_text())['plan'])}
    for key,group in groups:
        label,profile,elevation,duration,sigma,nf=key
        check(len(group)==8 and set(group.target)==set(TARGETS),'all outputs share each global condition')
        data=dict(np.load(OUT/f'{label}_{profile}_{int(elevation)}_physics.npz'))
        try:r=fit(data,plans[label],total_s=duration,sigma=sigma,elevation=elevation,noise_figure_db=nf)
        except ValueError as exc:
            check((group.status=='rejected').all() and (group.reason==str(exc)).all(),'retain every failed global condition')
            check(group.predicted_recall_pct.isna().all(),'rejected conditions have no fictitious recall')
            continue
        check((group.status=='computed').all(),'valid global condition status')
        covariance=r['operator']@r['covariance']@r['operator'].T
        check(np.isclose(r['sd'][7]**2,covariance[5,5]+covariance[6,6]+2*covariance[5,6]),'global PM10 includes cross covariance')
        for row in group.itertuples():
            j=TARGETS.index(row.target);c=1. if j<5 else 15. if j==5 else 45.
            direction=r['design'][:,j] if j<7 else r['design'][:,5]*49/90+r['design'][:,6]*41/90
            h=r['operator'][j]
            variance=attenuation_variance(r['snr']*10**(-direction*c/10),r['count']['payload'],'m2m4')+attenuation_variance(r['snr'],r['count']['payload'],'m2m4')
            sd=np.sqrt((h*h)@variance+sigma*sigma*h@r['correlation']@h)
            limit=response_limit(r,j,direction,sigma)
            check(row.reference_concentration_ug_m3==c,'global reference concentration')
            check(np.isclose(row.predicted_recall_pct,100*norm.sf((Z*r['sd'][j]-c)/sd)),'global positive variance recall')
            check(np.isclose(row.predicted_miss_rate_pct+row.predicted_recall_pct,100),'global missed detections')
            check(np.isclose(row.predicted_relative_rmse_pct,100*sd/c),'global relative error')
            check(np.isclose(row.response_lod95_ug_m3,limit,equal_nan=True),'global bounded 95 percent limit')
            check(row.valid_response95==bool(np.isfinite(limit)),'global limit availability')
    write('verification.json',dict(status='passed',checks=len(checks),response_cases=len(cases),
        global_comparison_rows=len(global_table),global_conditions=len(groups),
        metric_rows=len(metrics),sensitivity_rows=len(sensitivity),
        scope='Exact numerical replay, conditional simulation controls and failure gates; no empirical hardware or atmospheric validation.'))
    print(json.dumps(dict(status='passed',checks=len(checks),metric_rows=len(metrics))))


if __name__=='__main__':main()
