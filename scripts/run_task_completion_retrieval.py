"""Tasks 2.1/3.1/3.2/4.3: resources, nuisance, exact fits and detection limits."""
from pathlib import Path
from dataclasses import asdict
import sys,json,time,hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from thz_isac.waveform_link import OFDMPlan,physical_channel_gain,preserved_capacity,maximum_zenith_pass_s,ofdm_coherent_fraction,impaired_spectral_efficiency
from thz_isac.link_budget import LEOLinkBudgetConfig
from thz_isac.communication_capacity import waterfill_power,check_capacity_contract
from thz_isac.robust_retrieval import identifiability,decision_limits,ug_m3_to_ppm,fit_complex_amplitude,profile_complex_concentration
from thz_isac.joint_voc_pm import make_joint_retrieval,fine_coarse_to_pm25_pm10
from thz_isac.retrieval_metrics import detection_metrics,concentration_errors
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL,natural_mass_design
OUT=ROOT/'results/task_completion';TARGETS=('H2CO','CH3OH','CH3CN','PM2.5','PMcoarse','PM10')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def serial(info):return {k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in info.items()}


def main():
    start=time.perf_counter();manifest=json.loads((OUT/'physics_manifest.json').read_text())
    if manifest['status']!='passed':raise ValueError('Physics convergence gate failed')
    source=OUT/'physics_order4.npz'
    if sha(source)!=manifest['outputs'][source.name]:raise ValueError('Physics result hash mismatch')
    data=dict(np.load(source))
    gas_names=manifest['gas_names']
    data['gas']=natural_mass_design(data['gas'],gas_names,[MOLAR_MASS_G_MOL[n] for n in gas_names])
    config=LEOLinkBudgetConfig(**json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())['reference_link'])
    total=10**((config.tx_power_dbm-30)/10);plan=OFDMPlan((73.5,))
    pmsource=ROOT/'results/tables/single_channel_repair_predictions.csv'
    row=pd.read_csv(pmsource,nrows=1).iloc[0]
    truth=np.array([1.,1.,1.,row['true_PM2.5'],row['true_PM10']-row['true_PM2.5']])
    truth_report=np.r_[truth,truth[-2:].sum()]
    weather=pd.read_csv(OUT/'measured_weather_attenuation.csv')
    profiles=np.array([group.attenuation_db.to_numpy() for _,group in weather.groupby('datetime')])
    protocol=dict(analysis_window_ghz=[60,400],positive_controls=5000,absent_controls=5000,seed=20260924,
       presence_prevalence_pct=50,truth_ug_m3=truth_report.tolist(),pm_truth_source=str(pmsource.relative_to(ROOT)),
       pm_truth_sha256=sha(pmsource),pm_station=row['station'],pm_datetime=row['datetime'],
       durations_s=[.1,10.,1800.],residual_std_db=[0.,.001],residual_frequency_correlation_scale_ghz=10.,
       alpha_family=.01,targets_in_family=6,required_detection_power=.95,
       persistent_bias_bound_db=[0.,.0001,.001],
       scope='Physical instrument-response controls, no measured VOC labels or radio observations',
       nonlinear_scope='Exact Beer-Lambert complex-amplitude fit, declared bounds, same stored pilot samples',
       nonlinear_upper_bounds_ug_m3=[1000,1000,1000,1000,1000],
       no_extra_pilots=True,background='ITU P.676-13 Annex 1',
       optical_inputs='Uncalibrated Mie distributions: aerosol_controls.json',
       waveform=asdict(plan),noise='Sky emission plus receiver equivalent noise; residual covariance is a sensitivity scenario')
    protocol['mass_concentration_convention']=dict(source='CIAAW abridged standard atomic weights 2024',
        url='https://ciaaw.org/abridged-atomic-weights.htm',molar_mass_g_mol=NATURAL_MOLAR_MASS_G_MOL,
        operation='Stored linear spectra use historical main-isotope mass convention; multiply each gas column by old_mass/natural_mass before inference. Isotope-specific Doppler masses unchanged.')
    protocol['pass_geometry']=dict(ideal_overhead_pass_above_45deg_s=maximum_zenith_pass_s(45),
        ideal_overhead_pass_above_5deg_s=maximum_zenith_pass_s(5),
        duration_1800s='Stationary sensitivity control only; exceeds one ideal 550 km pass and requires a separately modeled revisit/constellation strategy')
    write('retrieval_protocol.json',protocol)
    metrics=[];errors=[];limits=[];resources=[];rankrows=[];biasrows=[];fitrows=[];samples={};curve=[];syncrows=[];likelihoodrows=[]
    for band,section in [('multiband_reference',slice(0,256)),('eband_73p5GHz',slice(256,512))]:
        f=data['frequency_ghz'][section];bg=data['background_db'][section];sky=data['sky_temperature_k'][section]
        channel=physical_channel_gain(f,bg,sky,config,45)
        gain=channel['gain_per_watt'];power=waterfill_power(gain,total);snr=gain*power
        if band.startswith('eband'):
            check=preserved_capacity(plan,gain,total,power)
        else:
            check=asdict(check_capacity_contract(gain,power,total,1e6,frame_symbols=10000,baseline_pilot_symbols=30,candidate_pilot_symbols=30))
            check.update(occupied_bandwidth_hz=256e6,simultaneous_rf_chains=None,
                         limitation='256 ideal separated probe channels; no hardware band plan or CP claimed')
        assert check['accepted']
        for cfo in [0.,1e3,1e4,1e5]:
            for phase in [0.,.03,.1]:
                fraction=ofdm_coherent_fraction(cfo,1e6,phase)
                efficiency=impaired_spectral_efficiency(snr,fraction)
                rate=1e6*(1-30/10000)*efficiency.sum()/(1+plan.cyclic_prefix_fraction if band.startswith('eband') else 1)
                syncrows.append(dict(band=band,residual_cfo_hz=cfo,phase_rms_rad=phase,coherent_power_fraction=fraction,
                    communication_rate_bps=rate,sensing_reuse_rate_bps=rate,incremental_sensing_loss_pct=0.,
                    allocation='Same ideal communication allocation held fixed for impairment sensitivity; not reoptimized for ICI'))
        for pointing in [0.,.01,.05]:
            ch=physical_channel_gain(f,bg,sky,config,45,pointing_error_deg=pointing)
            pp=waterfill_power(ch['gain_per_watt'],total)
            rate=plan.net_rate_bps(ch['gain_per_watt'],pp) if band.startswith('eband') else check_capacity_contract(ch['gain_per_watt'],pp,total,1e6,frame_symbols=10000,baseline_pilot_symbols=30,candidate_pilot_symbols=30).reference_bps
            resources.append(dict(band=band,pointing_error_deg=pointing,rate_bps=rate,
                min_sky_temperature_k=float(sky.min()),max_sky_temperature_k=float(sky.max()),
                max_orbital_doppler_hz=float(channel['maximum_orbital_doppler_hz'].max()),
                **{k:v for k,v in check.items() if k not in ['reference_bps','candidate_bps']}))
        mask=snr>=10**.5
        np.savez_compressed(OUT/f'{band}_channel.npz',frequency_ghz=f,gain_per_watt=gain,power_w=power,snr=snr,sensing_mask=mask,sky_temperature_k=sky)
        if mask.sum()<20:
            rankrows.append(dict(band=band,status='insufficient_usable_channels'));continue
        fg=f[mask];gas=data['gas'][section][mask];pm=data['pm'][section][mask];sn=snr[mask]
        design=np.column_stack((gas[:,:3],pm));x=(fg-fg.mean())/(fg.max()-fg.min())
        base=np.column_stack((np.ones(mask.sum()),bg[mask],gas[:,3:]))
        weather_delta=(profiles[:,section][:,mask]-bg[mask]).T
        u,s,_=np.linalg.svd(weather_delta,full_matrices=False)
        weather_basis=u[:,s>s[0]*1e-8]
        policies={'reference_calibration':base,
                  'weather_uncertainty':np.column_stack((base,weather_basis)),
                  'smooth_calibration':np.column_stack((base,weather_basis,fg/400,(fg/400)**4))}
        for policy,nuisance in policies.items():
            for elapsed in protocol['durations_s']:
                pilots=plan.coherent_pilots(elapsed) if band.startswith('eband') else int(elapsed/.01)*30
                for residual in protocol['residual_std_db']:
                    context=dict(band=band,nuisance_policy=policy,elapsed_s=elapsed,residual_std_db=residual,pilots=pilots,sensing_tones=int(mask.sum()),
                        within_ideal_pass_above_45deg=elapsed<=maximum_zenith_pass_s(45))
                    variance=2*(10/np.log(10))**2/(pilots*sn)
                    correlation=np.exp(-np.abs(fg[:,None]-fg[None,:])/10)
                    cov=np.diag(variance)+residual**2*correlation
                    diagnostic=identifiability(design,nuisance,cov)
                    rankrows.append({**context,**serial(diagnostic), 'status':'evaluated' if diagnostic['identifiable'] else 'unidentifiable'})
                    if not diagnostic['identifiable']:continue
                    try:joint=make_joint_retrieval(gas[:,:3],pm,nuisance,cov,TARGETS[:3])
                    except ValueError as exc:
                        rankrows[-1].update(status='unidentifiable',reason=str(exc));continue
                    h=joint.estimator.operator;report_h=np.vstack((h,h[-2]+h[-1]))
                    sd=np.sqrt(np.diag(report_h@cov@report_h.T))
                    for epsilon in protocol['persistent_bias_bound_db']:
                        bias_bound=epsilon*np.abs(report_h).sum(axis=1)
                        threshold=decision_limits(sd,false_positive_rate=.01,power=.95,family_size=6,bias_bound=bias_bound)
                        for j,target in enumerate(TARGETS):
                            ld=float(threshold['detection_limit'][j]);ppm=float(ug_m3_to_ppm(ld,NATURAL_MOLAR_MASS_G_MOL[target],288.15,101325)) if j<3 else None
                            limits.append({**context,'target':target,'bias_bound_db':epsilon,
                                'standard_error_ug_m3':sd[j],'critical_level_ug_m3':threshold['critical_level'][j],
                                'detection_limit_ug_m3':ld,'detection_limit_ppm':ppm,
                                'interpretation':'Conditional local Gaussian limit; exact response checks and physical-domain gates reported separately',
                                'family_alpha':.01,'family_size':6,'required_power':.95})
                    for date,delta in zip(sorted(weather.datetime.unique()),weather_delta.T):
                        bias=report_h@delta
                        for j,target in enumerate(TARGETS):biasrows.append({**context,'weather_datetime':date,'target':target,'linearized_bias_ug_m3':bias[j],
                             'scope':'Fixed design linearized background mismatch diagnostic; large biases leave local-model validity'})
                    # Paired RNG across policies/configurations. Positive/absent
                    # draws are independent. Detection threshold is not tuned.
                    rng=np.random.default_rng(protocol['seed']);shape=(5000,len(fg))
                    signal=design@truth
                    znull=(rng.normal(size=shape)+1j*rng.normal(size=shape))/np.sqrt(2*pilots*sn)
                    zpos=10**(-signal/20)+(rng.normal(size=shape)+1j*rng.normal(size=shape))/np.sqrt(2*pilots*sn)
                    if residual:
                        chol=np.linalg.cholesky(correlation+np.eye(len(fg))*1e-12)
                        null_res=residual*rng.normal(size=shape)@chol.T;pos_res=residual*rng.normal(size=shape)@chol.T
                    else:null_res=pos_res=0.
                    anull=-20*np.log10(np.abs(1+znull))+null_res
                    apos=-20*np.log10(np.abs(zpos))+pos_res
                    null=anull@report_h.T;pos=apos@report_h.T
                    key=f'{band}_{policy}_{elapsed:g}s_{residual:g}'
                    samples[key+'_positive']=pos;samples[key+'_absent']=null
                    zcrit=norm.isf(.01/6)
                    for j,target in enumerate(TARGETS):
                        m=detection_metrics(pos[:,j]/sd[j],null[:,j]/sd[j],zcrit)
                        for measure in ('precision','recall','false_positive'):
                            lo,hi=m.pop(measure+'_ci95_pct');m[measure+'_ci95_lower_pct']=lo;m[measure+'_ci95_upper_pct']=hi
                        m['average_precision_pct']=100*average_precision_score(np.r_[np.zeros(5000),np.ones(5000)],np.r_[null[:,j],pos[:,j]])
                        metrics.append({**context,'target':target,'standard_error_ug_m3':sd[j],**m})
                        for tag,values,actual in [('positive',pos[:,j],truth_report[j]),('absent',null[:,j],0.)]:
                            errors.append({**context,'target':target,'control':tag,**concentration_errors(values,actual)})
                    # Empirical detector operating point at the analytical 95%
                    # limit: independent exact complex response per gas, same
                    # covariance. This catches low-SNR linearization failures.
                    if policy=='reference_calibration' and elapsed==10 and residual==0:
                        limit=decision_limits(sd,false_positive_rate=.01,power=.95,family_size=6)['detection_limit']
                        for j in range(3):
                            injected=truth.copy();injected[:3]=0.;injected[j]=limit[j]
                            mean=10**(-(design@injected)/20)
                            draw=mean+(rng.normal(size=(5000,len(fg)))+1j*rng.normal(size=(5000,len(fg))))/np.sqrt(2*pilots*sn)
                            estimate=(-20*np.log10(np.abs(draw)))@report_h.T
                            observed_recall=float(100*np.mean(estimate[:,j]>zcrit*sd[j]))
                            curve.append(dict(band=band,target=TARGETS[j],injected_ug_m3=limit[j],predicted_power_pct=95.,
                               observed_recall_pct=observed_recall,local_prediction_passed=abs(observed_recall-95)<1.,
                               max_target_attenuation_db=float(np.max(design@injected))))
                        # Retain 20 actual pilot realizations and each nonlinear
                        # fit including active bounds; no test-selected tuning.
                        samples[band+'_complex_positive']=zpos[:20]
                        for i in range(20):
                            fit=fit_complex_amplitude(zpos[i],design,nuisance,np.sqrt(1/(pilots*sn)),
                                  concentration_scale=np.array([10.,30.,3.,50.,50.]),upper_concentration=np.full(5,1000.),initial=np.maximum(0,np.minimum(pos[i,:5],999)))
                            for j,target in enumerate(TARGETS[:5]):fitrows.append(dict(band=band,draw=i,target=target,truth_ug_m3=truth[j],
                                 nonlinear_estimate_ug_m3=fit.concentrations[j],signed_gls_ug_m3=pos[i,j],
                                 success=fit.success,active_bound=int(fit.active_bounds[j]),cost=fit.cost,evaluations=fit.evaluations))
                        for target_index in [0,3]:
                            prof=profile_complex_concentration(zpos[0],design,nuisance,np.sqrt(1/(pilots*sn)),
                                  target_index=target_index,grid=[0,1,3,10,30,100,300,1000],
                                  concentration_scale=[10,30,3,50,50],upper_concentration=[1000]*5)
                            for c,cost,dev,ok in zip(prof['concentration'],prof['cost'],prof['deviance_from_grid_minimum'],prof['success']):
                                likelihoodrows.append(dict(band=band,target=TARGETS[target_index],draw=0,concentration_ug_m3=c,
                                    cost=cost,deviance_from_grid_minimum=dev,success=bool(ok),
                                    minimum_at_grid_boundary=prof['minimum_at_grid_boundary']))
        print(band,'complete',flush=True)
    tables=dict(detection_metrics=metrics,concentration_errors=errors,detection_limits=limits,
                link_resources=resources,weather_mismatch_bias=biasrows,nonlinear_fits=fitrows,
                detection_limit_response_check=curve,synchronization_sensitivity=syncrows,profile_likelihood=likelihoodrows)
    for name,rows in tables.items():pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
    write('identifiability.json',rankrows)
    np.savez_compressed(OUT/'retrieval_samples.npz',**samples)
    # Comparison gates preserve different averaging times and physical domains.
    comparisons=[dict(target='PM2.5',guideline_ug_m3=15,averaging_s=86400,domain='ambient surface air',source='https://www.who.int/news-room/questions-and-answers/item/who-global-air-quality-guidelines'),
                 dict(target='PM10',guideline_ug_m3=45,averaging_s=86400,domain='ambient surface air',source='https://www.who.int/news-room/questions-and-answers/item/who-global-air-quality-guidelines'),
                 dict(target='H2CO',guideline_ug_m3=100,averaging_s=1800,domain='indoor air',source='https://www.who.int/publications/i/item/9789289002134')]
    for item in comparisons:
        item.update(compliance_demonstrated=False,reason='No paired calibrated measurements; slant column is not an independently measured surface/indoor concentration',
                    continuous_coverage_demonstrated=False)
    comparisons.extend(dict(target=s,guideline_ug_m3=None,compliance_demonstrated=False,reason='No applicable ambient guideline established in the cited WHO documents; occupational limits not substituted') for s in ['CH3OH','CH3CN'])
    write('environmental_comparison.json',comparisons)
    make_plots(pd.DataFrame(metrics),pd.DataFrame(limits),pd.DataFrame(resources),data,weather)
    write('retrieval_manifest.json',dict(status='completed',wall_seconds=time.perf_counter()-start,
          physics_manifest_sha256=sha(OUT/'physics_manifest.json'),positive_and_absent_controls=5000,
          metrics_rows=len(metrics),limit_rows=len(limits),nonlinear_fit_rows=len(fitrows),
          code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'src/thz_isac/robust_retrieval.py',ROOT/'src/thz_isac/waveform_link.py']},
          outputs={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='retrieval_manifest.json' and not p.name.endswith('.log')}))
    print('Retrieval study completed',flush=True)


def make_plots(metrics,limits,resources,data,weather):
    def save(fig,name):
        fig.savefig(OUT/(name+'.png'),dpi=180);fig.savefig(OUT/(name+'.svg'));plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    f=data['frequency_ghz'][:256]
    for name in ['oxygen_lines','dry_continuum','water_lines','wet_continuum']:
        axes[0].plot(f,data[name+'_db'][:256],label=name.replace('_',' '))
    axes[0].set_yscale('symlog',linthresh=.05)
    axes[0].axhline(0,color='grey',lw=.6)
    axes[0].text(.98,.98,'Signed line-mixing component shown;\ntotal attenuation stays positive',
                 transform=axes[0].transAxes,ha='right',va='top',fontsize=7)
    axes[0].set(xlabel='Frequency (GHz)',ylabel='Slant attenuation (dB)',title='P.676-13 components | P.835-7, 45 degrees');axes[0].legend(fontsize=8)
    for date,g in weather.groupby('datetime'):axes[1].semilogy(f,g.attenuation_db.to_numpy()[:256],label=date[:10])
    axes[1].semilogy(f,data['background_db'][:256],ls='--',color='black',label='P.835-7 reference')
    axes[1].set(xlabel='Frequency (GHz)',ylabel='Slant attenuation (dB)',title='Actual weather profiles with explicit upper extension');axes[1].legend(fontsize=8)
    save(fig,'background_and_weather')
    selected=limits[(limits.elapsed_s==10)&(limits.bias_bound_db==0)&(limits.residual_std_db==0)&(limits.target.isin(TARGETS[:3]))]
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for (band,policy),g in selected.groupby(['band','nuisance_policy']):
        ax.semilogy(g.target,g.detection_limit_ug_m3,'o-',label=band+' / '+policy)
    ax.set(ylabel='95%-power detection limit (ug/m³)',title='10 s | 1% family-wise false-alarm budget | conditional model')
    ax.legend(fontsize=7);ax.grid(alpha=.2);save(fig,'detection_limits_by_nuisance')
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
    for band,g in resources.groupby('band'):ax.plot(g.pointing_error_deg,g.rate_bps/1e6,'o-',label=band)
    ax.set(xlabel='Pointing offset at each antenna (degrees)',ylabel='Modeled net rate (Mbit/s)',title='Same total power | explicit sky noise and existing pilots');ax.legend();ax.grid(alpha=.2)
    save(fig,'waveform_capacity_and_pointing')
    selected=metrics[(metrics.band=='multiband_reference')&(metrics.nuisance_policy=='reference_calibration')&(metrics.residual_std_db==0)&(metrics.target.isin(TARGETS[:3]))]
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    for target,g in selected.groupby('target'):
        line,=ax.semilogx(g.elapsed_s,g.recall_pct,'o--',label=target)
        ax.errorbar(g.elapsed_s,g.recall_pct,yerr=np.vstack((g.recall_pct-g.recall_ci95_lower_pct,g.recall_ci95_upper_pct-g.recall_pct)),
                    color=line.get_color(),fmt='none',capsize=3)
    pass_limit=maximum_zenith_pass_s(45)
    ax.axvspan(pass_limit,2300,color='grey',alpha=.12)
    ax.axvline(pass_limit,color='grey',ls=':')
    ax.text(.97,.52,'Shaded: exceeds ideal pass above 45°\n1,800 s is a stationary control\nDashed lines only connect evaluated points',
            transform=ax.transAxes,ha='right',fontsize=8)
    ax.set(xlabel='Observation time (s)',ylabel='Recall (%)',title='1 ug/m³ VOC controls | 1% family-wise budget | 95% intervals',ylim=(0,100));ax.legend();ax.grid(alpha=.2)
    save(fig,'voc_detection_duration')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plots-only',action='store_true',help='Redraw saved results without rerunning the experiment')
    args=parser.parse_args()
    if args.plots_only:
        inputs=['detection_metrics.csv','detection_limits.csv','link_resources.csv','physics_order4.npz','measured_weather_attenuation.csv']
        make_plots(pd.read_csv(OUT/inputs[0]),pd.read_csv(OUT/inputs[1]),pd.read_csv(OUT/inputs[2]),
                   dict(np.load(OUT/inputs[3])),pd.read_csv(OUT/inputs[4]))
        write('plot_manifest.json',dict(scope='Presentation correction only; stored experimental samples unchanged',
              review='Show signed oxygen line-mixing term; label duration beyond ideal pass; add existing recall confidence intervals',
              source_sha256=sha(Path(__file__)),inputs={name:sha(OUT/name) for name in inputs},
              outputs={p.name:sha(p) for extension in ['png','svg'] for p in OUT.glob('*.'+extension)}))
    else:main()
