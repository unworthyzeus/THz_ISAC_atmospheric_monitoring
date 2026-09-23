"""Report errors, precision/recall and plots for physical response controls.

Positive/absent classes have a declared 50% prevalence. These are conditional
simulation detection metrics, not precision on an environmental population.
"""
from pathlib import Path
from dataclasses import asdict
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import precision_recall_curve,average_precision_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from thz_isac.joint_voc_pm import make_joint_retrieval,fine_coarse_to_pm25_pm10
from thz_isac.communication_capacity import waterfill_power,check_capacity_contract
from thz_isac.link_budget import LEOLinkBudgetConfig,compute_leo_link_budget
from thz_isac.retrieval_metrics import detection_metrics,concentration_errors

TARGETS=('H2CO','CH3OH','CH3CN','PM2.5','PMcoarse','PM10')
LABELS=('Formaldehyde','Methanol','Acetonitrile','PM2.5','Coarse PM','PM10')


def main():
    out=ROOT/'results/task_1_3_metrics'
    source=ROOT/'results/task_1_3/refracted45_inputs.npz'
    source_manifest=ROOT/'results/task_1_3/manifest.json'
    if not source_manifest.exists(): raise SystemExit('Complete run_task_1_3.py validation before evaluating retrieval.')
    manifest=json.loads(source_manifest.read_text())
    assert digest(source)==manifest['outputs'][source.name]
    data=np.load(source); f=data['frequency_ghz']
    config=json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())['reference_link']
    link_config=LEOLinkBudgetConfig(**config); total=10**((link_config.tx_power_dbm-30)/10)
    bg=data['background_db']
    gain=compute_leo_link_budget(f,45,link_config,bg).snr_linear[0]/(total/len(f))
    power=waterfill_power(gain,total); snr=gain*power; mask=snr>=10**.5
    capacity=check_capacity_contract(gain,power,total,1e6,frame_symbols=10000,
             baseline_pilot_symbols=30,candidate_pilot_symbols=30)
    assert capacity.accepted
    pm_source=ROOT/'results/tables/single_channel_repair_predictions.csv'
    pm_row=pd.read_csv(pm_source,nrows=1).iloc[0]
    positive_truth=[1.,1.,1.,float(pm_row['true_PM2.5']),
                    float(pm_row['true_PM10']-pm_row['true_PM2.5']),float(pm_row['true_PM10'])]
    protocol=dict(source=str(source.relative_to(ROOT)),source_sha256=digest(source),
       geometry='Full task 1.3 refracted path at 45 degree geometric elevation',
       background='ITU P.676-12; pure HITRAN background remains a failed sensitivity control',
       frequency_bounds_ghz=[60,400],frames=[1,10,1000],elapsed_s=[.01,.1,10.],
       residual_std_db=[0,.001],positive_draws=5000,null_draws=5000,seed=20260923,
       target_positive_truth_ug_m3=positive_truth,positive_prevalence_pct=50,
       pm_source=dict(file=str(pm_source.relative_to(ROOT)),sha256=digest(pm_source),
                      station=pm_row['station'],datetime=pm_row['datetime']),
       detector='Signed GLS estimate / conditional standard error; fixed one-sided per-target null alpha=1%',
       z_threshold=float(norm.isf(.01)),threshold_tuned_on_test=False,
       scope='Complex-pilot response controls; no environmental VOC labels, no field precision/recall claim',
       error_percentage_denominator='Known positive control concentration; percentages undefined for zero truth',
       added_pilots=0,rate=asdict(capacity),sensing_tones=int(mask.sum()),
       comparison='Shared underlying noise across duration/residual scenarios; independent null and positive draws')
    run=Run(out,protocol,__file__)
    d=data['gas'][mask,:3]; pm=data['pm'][mask]
    nuisance=np.column_stack((np.ones(mask.sum()),bg[mask],data['gas'][mask,3:7]))
    truth=np.array(protocol['target_positive_truth_ug_m3']); base_truth=truth[:5]
    rng=np.random.default_rng(protocol['seed']); shape=(5000,mask.sum())
    nr=rng.normal(size=shape); ni=rng.normal(size=shape)
    pr=rng.normal(size=shape); pi=rng.normal(size=shape)
    persistent_null=rng.normal(size=shape); persistent_positive=rng.normal(size=shape)
    rows=[]; errors=[]; curve_rows=[]; samples={}; final_sd=None
    for frames in protocol['frames']:
        for residual in protocol['residual_std_db']:
            n=30*frames
            variance=2*(10/np.log(10))**2/(n*snr[mask])+residual**2
            joint=make_joint_retrieval(d,pm,nuisance,np.diag(variance),TARGETS[:3])
            sd=np.r_[np.sqrt(np.diag(joint.estimator.covariance)),np.sqrt(joint.reported_pm_covariance()[1,1])]
            signal=joint.design@base_truth
            noise_scale=np.sqrt(2*n*snr[mask])
            null_db=-20*np.log10(np.abs(1+(nr+1j*ni)/noise_scale))+residual*persistent_null
            positive_db=-20*np.log10(np.abs(10**(-signal/20)+(pr+1j*pi)/noise_scale))+residual*persistent_positive
            null=joint.estimate(null_db); positive=joint.estimate(positive_db)
            null=np.column_stack((null,fine_coarse_to_pm25_pm10(null)[:,1]))
            positive=np.column_stack((positive,fine_coarse_to_pm25_pm10(positive)[:,1]))
            key=f'frames{frames}_residual{residual:g}'
            samples[key+'_positive']=positive; samples[key+'_null']=null
            for j,name in enumerate(TARGETS):
                context=dict(frames=frames,elapsed_s=frames*.01,residual_std_db=residual,target=name,
                             standard_error_ug_m3=sd[j])
                scores=np.r_[null[:,j]/sd[j],positive[:,j]/sd[j]]
                y=np.r_[np.zeros(5000),np.ones(5000)]
                metrics=detection_metrics(positive[:,j]/sd[j],null[:,j]/sd[j],protocol['z_threshold'])
                for metric in ('precision','recall','false_positive'):
                    lo,hi=metrics.pop(metric+'_ci95_pct')
                    metrics[metric+'_ci95_lower_pct']=lo; metrics[metric+'_ci95_upper_pct']=hi
                metrics['average_precision_pct']=100*average_precision_score(y,scores)
                rows.append({**context,**metrics})
                for case,est,actual in [('positive',positive[:,j],truth[j]),('absent',null[:,j],0.)]:
                    e=concentration_errors(est,actual)
                    e['conditional_95pct_interval_coverage_pct']=float(100*np.mean(np.abs(est-actual)<=norm.ppf(.975)*sd[j]))
                    errors.append({**context,'control':case,**e})
                if frames==1000 and residual==0:
                    precision,recall,thresholds=precision_recall_curve(y,scores)
                    indices=np.unique(np.linspace(0,len(precision)-1,501,dtype=int))
                    curve_rows.extend(dict(target=name,recall_pct=100*recall[i],precision_pct=100*precision[i]) for i in indices)
            if frames==1000 and residual==0: final_sd=sd
    metric_table=pd.DataFrame(rows); error_table=pd.DataFrame(errors); curves=pd.DataFrame(curve_rows)
    metric_table.to_csv(out/'detection_metrics.csv',index=False)
    error_table.to_csv(out/'concentration_errors.csv',index=False)
    curves.to_csv(out/'precision_recall_curves.csv',index=False)
    np.savez_compressed(out/'control_estimates.npz',**samples)
    np.savez_compressed(out/'communication_allocation.npz',frequency_ghz=f,gain_per_watt=gain,power_w=power,sensing_mask=mask)
    make_plots(out,metric_table,error_table,curves,final_sd,protocol)
    selected=metric_table[(metric_table.frames==1000)&(metric_table.residual_std_db==0)]
    write_json(out/'summary.json',dict(capacity=asdict(capacity),metrics=selected.to_dict('records'),
           limitation='Balanced response controls at 1 ug/m3 per VOC; precision depends on this artificial prevalence. No field validation.'))
    run.finish(extra=dict(input_hashes={str(source.relative_to(ROOT)):digest(source),str(source_manifest.relative_to(ROOT)):digest(source_manifest)},
       code_hashes={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'src/thz_isac/retrieval_metrics.py',ROOT/'src/thz_isac/joint_voc_pm.py',ROOT/'src/thz_isac/communication_capacity.py']}))
    print(selected[['target','precision_pct','recall_pct','false_positive_rate_pct','average_precision_pct']].to_string(index=False))


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=180)
    fig.savefig(out/(name+'.svg'))
    plt.close(fig)


def make_plots(out,metrics,errors,curves,sd,protocol):
    chosen=metrics[(metrics.frames==1000)&(metrics.residual_std_db==0)].set_index('target')
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for j,(name,label,ax) in enumerate(zip(TARGETS,LABELS,axes.ravel())):
        row=chosen.loc[name]
        matrix=100*np.array([[row.tn,row.fp],[row.fn,row.tp]])/5000
        ax.imshow(matrix,vmin=0,vmax=100,cmap='Blues')
        for index in np.ndindex(2,2): ax.text(index[1],index[0],f'{matrix[index]:.2f}%',ha='center',va='center',color='white' if matrix[index]>50 else 'black')
        ax.set(xticks=[0,1],xticklabels=['Absent','Present'],yticks=[0,1],yticklabels=['Absent','Present'],
               xlabel='Predicted',ylabel='True control',title=label)
    fig.suptitle('Detection controls at 10 s | 1% nominal false-alarm threshold | rows sum to 100%')
    save(fig,out,'confusion_matrices')
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    for name,label in zip(TARGETS,LABELS):
        group=curves[curves.target==name]
        ax.plot(group.recall_pct,group.precision_pct,label=f'{label} (AP {chosen.loc[name,"average_precision_pct"]:.1f}%)',lw=1.2)
    ax.axhline(50,color='gray',ls='--',label='50% positive prevalence')
    ax.set(xlabel='Recall (%)',ylabel='Precision (%)',xlim=(0,100),ylim=(0,100),title='Precision–recall | balanced response controls, 10 s')
    ax.legend(fontsize=8); ax.grid(alpha=.2); save(fig,out,'precision_recall')
    selected=errors[(errors.frames==1000)&(errors.residual_std_db==0)&(errors.control=='positive')].set_index('target').loc[list(TARGETS)]
    fig,axes=plt.subplots(1,2,figsize=(13,4.6),layout='constrained'); x=np.arange(6)
    for ax,a,b,ylabel in [(axes[0],'mae_ug_m3','rmse_ug_m3','Absolute error (ug/m³)'),
                            (axes[1],'mae_pct_of_truth','rmse_pct_of_truth','Error / known positive concentration (%)')]:
        ax.bar(x-.18,selected[a],.36,label='MAE'); ax.bar(x+.18,selected[b],.36,label='RMSE')
        ax.set_yscale('log'); ax.set_xticks(x,LABELS,rotation=22,ha='right'); ax.set_ylabel(ylabel); ax.legend(); ax.grid(axis='y',alpha=.2)
    fig.suptitle('10 s estimation errors | VOC truth 1 ug/m³ each; PM truth 49 / 41 / 90 ug/m³')
    save(fig,out,'absolute_and_percentage_errors')
    fig,axes=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
    for name,label in zip(TARGETS[:3],LABELS[:3]):
        group=metrics[(metrics.target==name)&(metrics.residual_std_db==0)]
        axes[0].semilogx(group.elapsed_s,group.precision_pct,'o-',label=label)
        axes[1].semilogx(group.elapsed_s,group.recall_pct,'o-',label=label)
        axes[0].fill_between(group.elapsed_s,group.precision_ci95_lower_pct,group.precision_ci95_upper_pct,alpha=.12)
        axes[1].fill_between(group.elapsed_s,group.recall_ci95_lower_pct,group.recall_ci95_upper_pct,alpha=.12)
    for ax,label in zip(axes,['Precision (%)','Recall (%)']):
        ax.set(xlabel='Observation time (s)',ylabel=label,title=label+' at the fixed detection threshold')
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('Balanced simulated controls: 1 ug/m³ per VOC | shaded 95% Wilson intervals')
    save(fig,out,'detection_vs_time')
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    c=np.geomspace(.01,1000,501); rows=[]
    for j,label in enumerate(LABELS[:3]):
        recall=norm.sf(protocol['z_threshold']-c/sd[j])*100
        ax.semilogx(c,recall,label=label)
        rows.extend(dict(target=TARGETS[j],concentration_ug_m3=a,predicted_recall_pct=b) for a,b in zip(c,recall))
    ax.axhline(90,color='gray',ls='--',lw=1)
    ax.set(xlabel='Injected concentration (ug/m³)',ylabel='Predicted recall (%)',ylim=(0,100),
           title='Gaussian sensitivity calculation | 10 s, 1% nominal false-alarm rate')
    ax.legend(); ax.grid(alpha=.2); save(fig,out,'conditional_detection_curves')
    pd.DataFrame(rows).to_csv(out/'conditional_detection_curves.csv',index=False)


if __name__=='__main__': main()
