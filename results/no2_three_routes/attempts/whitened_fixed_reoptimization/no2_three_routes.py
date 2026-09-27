"""Develop differential, structured-calibration and fine-grid NO2 designs."""
from pathlib import Path
from itertools import product
import argparse
import json
import sys
import traceback
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from run_rmse_metric_audit import build_context
from thz_isac.physical_spectroscopy import build_layered_zenith_attenuation_design,apply_plane_parallel_slant
from thz_isac.link_budget import LEOLinkBudgetConfig,compute_leo_link_budget
from thz_isac.no2_design import solve_target,integer_dwell,polynomial_calibration,risk_components
from thz_isac.attainable_estimation import efficient_linear_estimator

OUT=ROOT/'results/no2_three_routes'
SCALE=np.array([4000.,100.,40.,25.])
CONFIG=ROOT/'results/revision_0908/protocol.json'
AIR=ROOT/'data/processed/air_quality/beijing_air_quality_clean.csv.gz'
LINES=ROOT/'data/processed/hitran/hitran_60_400GHz_lines.csv'
ARCHIVE=ROOT/'results/closure_robust_atmosphere/inputs.npz'
CASES=[
 ('coarse_equal_box','coarse','equal',1,1e-4,1e-4),
 ('coarse_dwell_box','coarse','optimal',1,1e-4,1e-4),
 ('fine_equal_box','fine','equal',1,1e-4,1e-4),
 ('fine_dwell_box','fine','optimal',1,1e-4,1e-4),
 ('coarse_equal_polynomial','coarse','equal',1,1e-4,0.),
 ('coarse_equal_poly_residual','coarse','equal',1,1e-4,1e-5),
 ('fine_dwell_polynomial','fine','optimal',1,1e-4,0.),
 ('fine_dwell_poly_residual','fine','optimal',1,1e-4,1e-5),
 ('coarse_equal_diff_stable','coarse','equal',2,0.,0.),
 ('coarse_equal_diff_drift','coarse','equal',2,1e-5,1e-5),
 ('coarse_equal_diff_independent','coarse','equal',2,2e-4,2e-4),
 ('fine_dwell_diff_stable','fine','optimal',2,0.,0.),
 ('fine_dwell_diff_drift','fine','optimal',2,1e-5,1e-5),
 ('fine_dwell_diff_independent','fine','optimal',2,2e-4,2e-4),
 ('fine_dwell_diff_poly_residual','fine','optimal',2,1e-5,1e-6),
]
PROTOCOL=dict(
 question='Evaluate all three proposed NO2 routes, including unfavorable controls, at matched integrated acquisition resources.',
 source_boundary='HITRAN and the two-page I2R proposal are available. I2R contains research tasks, not repeated receiver calibration recordings. No measured drift is fitted or claimed.',
 frequency='Union of the existing 71 retained probes in 260-400 GHz and a 0.25 GHz grid. Recompute the 24-layer Voigt model directly; retain new probes with nominal SNR >=5 dB at -1 dBm. Preserve all original band probes.',
 design_envelope='54 recalculated discrepancies: the original 27 T/p/height states at two training-only concentration quantiles. Differential design uses twice this symmetric convex envelope, so it does not assume atmospheric cancellation.',
 calibration='Box or a declared subset: three Legendre modes on 260-400 GHz, each coefficient bounded by (total-residual)/3, plus residual L-infinity box. No empirical coverage guarantee.',
 temporal='Two separate spectra estimate changes. Identical persistent calibration cancels; remaining difference envelopes are 0, 1e-5, or 2e-4 dB. Independent 1e-4 errors in both readings require the last case. Absolute retrieval additionally requires a known baseline.',
 acquisition='One active tone, -1 dBm, 1 microsecond pilots, 1 millisecond assumed retuning, one or two sorted sweeps. Each sweep is charged m-1 switches. Setup, inter-epoch waiting and moving-LEO geometry tracking are excluded. Duration denotes charged acquisition, not elapsed interval.',
 dwell='Continuous c-optimal robust dwell, then integer pilots with at least one pilot at every retained tone and a new solve at the rounded variance. No support selection after evaluation.',
 durations_s=[10.,100.],cases=[list(c) for c in CASES],
 likelihood='Known nominal coherent diagonal thermal covariance and zero independent residual, inherited LEO link. A second replay substitutes modeled weather-dependent covariance and flags low SNR; it cannot validate the coherent approximation.',
 evaluation='Operators and allocations are frozen before evaluating 16 new modeled T/p/height states using real test-period concentrations and 24 same-station consecutive-hour pairs from that period. Real weather is used for the latter. No pair crosses the fixed train/validation/test boundary. Previously used public data are not a new independent population sample.',
 seed=909803,new_states=16,real_pairs=24,
 sensitivity='Replay fixed designs at -10 and -1 dBm and retuning 0, 0.1, 1, 10 ms. This is fixed-design sensitivity, not a new optimum.',
 reference_scale='Errors divided by 25 ug/m3; change error uses the same magnitude, not a health compliance or detection threshold.',
)


def source_context():
    config=json.loads(CONFIG.read_text())['config']
    data=pd.read_csv(AIR);hitran=pd.read_csv(LINES)
    return config,data,hitran


def forward_factory(config,hitran,frequency):
    surface=config['surface_conditions_from_uci_medians'];atm=config['atmosphere']
    linkconf=dict(config['reference_link'],tx_power_dbm=-1.,n_active_subcarriers=1)
    def forward(dt=0.,dp=0.,height=1500.,dew=None):
        z=build_layered_zenith_attenuation_design(hitran,frequency,
            surface_temperature_k=surface['temperature_k']+dt,surface_pressure_pa=surface['pressure_pa']+dp,
            surface_dew_point_c=surface['dew_point_c'] if dew is None else dew,
            pollutant_scale_height_m=height,water_scale_height_m=atm['water_scale_height_m'],
            pm_scale_height_m=atm['pm_scale_height_m'],n_layers=atm['n_layers'],
            top_altitude_m=atm['top_altitude_m'],partition_sum_version=atm['partition_sum_version'])
        return tuple(apply_plane_parallel_slant(a,45) for a in [z.gas_db_per_ug_m3,z.pm_db_per_ug_m3,z.background_db])
    def thermal(background):
        snr=compute_leo_link_budget(frequency,45,LEOLinkBudgetConfig(**linkconf),background).snr_db[0]
        # Clipping only avoids floating overflow in extreme out-of-model weather.
        return 2*(10/np.log(10))**2/10**(np.clip(snr,-150,150)/10),snr
    return forward,thermal


def mean(arrays,theta):return arrays[0]@theta[:4]+arrays[1]@theta[4:]+arrays[2]


def physical():
    run=Run(OUT/'physical',PROTOCOL,__file__)
    config,data,hitran=source_context();ctx=build_context(data,hitran,config)
    original=np.load(ARCHIVE)['frequency'];coarse=original[(original>=260)&(original<=400)]
    f=np.unique(np.round(np.r_[np.arange(260,400.0001,.25),coarse],9))
    forward,thermal=forward_factory(config,hitran,f);nominal=forward();a,snr=thermal(nominal[2])
    old=np.any(np.isclose(f[:,None],coarse,rtol=0,atol=1e-8),axis=1)
    keep=(snr>=5)|old
    f=f[keep];a=a[keep];snr=snr[keep];old=old[keep]
    nominal=tuple(x[keep] for x in nominal)
    forward,thermal=forward_factory(config,hitran,f)
    training=ctx.parameter_targets[ctx.split.train]
    theta=np.quantile(training,[.5,.95],axis=0)
    biases=[];states=[]
    for k,(dt,dp,height) in enumerate(product([-5.,0.,5.],[-2000.,0.,2000.],[1200.,1500.,1800.])):
        actual=forward(dt,dp,height)
        for j,q in enumerate(theta):
            biases.append(mean(actual,q)-mean(nominal,q));states.append([dt,dp,height,j])
        if (k+1)%3==0: print('physical design states',k+1,'of 27',flush=True)
    d=nominal[0]*SCALE;n=np.column_stack([np.ones(len(f)),nominal[2],nominal[1]])
    np.savez_compressed(run.output/'inputs.npz',frequency=f,coarse_mask=old,design=d,nuisance=n,
        design_bias=np.column_stack(biases),thermal=a,snr_db=snr,
        gas=nominal[0],pm=nominal[1],background=nominal[2])
    write_json(run.output/'summary.json',dict(candidate_probes=len(f),coarse_probes=int(old.sum()),states=states,
        quantiles=theta.tolist(),train_end=str(ctx.split.train_end),validation_end=str(ctx.split.validation_end)))
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [CONFIG,AIR,LINES,ARCHIVE]},
        'physics_code_sha256':digest(ROOT/'src/thz_isac/physical_spectroscopy.py')})


def case_inputs(a,case):
    name,grid,allocation,sweeps,total,residual=case
    mask=a['coarse_mask'] if grid=='coarse' else np.ones(len(a['frequency']),bool)
    f=a['frequency'][mask];d=a['design'][mask];n=a['nuisance'][mask]
    b=a['design_bias'][mask]*sweeps
    modes=polynomial_calibration(f,total,residual) if total>residual else np.empty((len(f),0))
    return mask,f,d,n,b,modes,residual


def design():
    run=Run(OUT/'design',PROTOCOL,__file__);a=np.load(OUT/'physical/inputs.npz')
    rows=[];resources=[];saved={};failures=[];sens=[]
    for duration,case in product(PROTOCOL['durations_s'],CASES):
        name,grid,allocation,sweeps,total,residual=case;key=f'{name}|{duration:g}s'
        try:
            mask,f,d,n,b,modes,residual=case_inputs(a,case);thermal=a['thermal'][mask]
            available=duration-sweeps*(len(f)-1)*.001
            if allocation=='optimal':
                continuous=solve_target(d,n,b,modes,residual,thermal_per_second=thermal*1e-6*sweeps**2,available_s=available)
                weights=continuous.continuous_dwell_s;lower=continuous.risk
            else: weights=np.ones(len(f));lower=None
            count,resource=integer_dwell(weights,duration,sweeps=sweeps,retune_s=.001)
            variance=sweeps*thermal/count
            result=solve_target(d,n,b,modes,residual,variance=variance)
            saved[key+'|h']=result.operator;saved[key+'|counts']=count;saved[key+'|mask']=mask
            saved[key+'|variance']=variance;saved[key+'|weights']=weights
            rows.append(dict(case=name,duration_s=duration,grid=grid,allocation=allocation,sweeps=sweeps,
                total_calibration_db=total,residual_db=residual,probes=len(f),design_rmse=result.risk,
                noise_sd=result.noise_sd,atmosphere_bias=result.atmospheric_bias,calibration_bias=result.calibration_bias,
                continuous_rmse=lower,identity_error=result.identity_error,status=result.status))
            resources.append(dict(case=name,duration_s=duration,**resource,power_dbm=-1.,
                radiated_energy_j=resource['integration_s']*10**(-1/10)/1000,
                minimum_pilots=int(count.min()),maximum_pilots=int(count.max())))
            for power,retune in product([-10.,-1.],[0.,1e-4,1e-3,1e-2]):
                c,r=integer_dwell(weights,duration,sweeps=sweeps,retune_s=retune)
                v=sweeps*thermal*10**((-1-power)/10)/c
                risk,ns,ab,cb=risk_components(result.operator,v,b,modes,residual)
                sens.append(dict(case=name,duration_s=duration,power_dbm=power,retune_s=retune,
                    rmse=risk,noise_sd=ns,atmosphere_bias=ab,calibration_bias=cb,
                    charged_s=r['charged_s'],energy_j=r['integration_s']*10**(power/10)/1000))
            print(key,'risk',round(result.risk,5),'noise',round(result.noise_sd,5),flush=True)
        except Exception as error:
            failures.append(dict(key=key,error=repr(error),traceback=traceback.format_exc()))
            print(key,'FAILED',repr(error),flush=True)
        pd.DataFrame(rows).to_csv(run.output/'summary.csv',index=False)
        write_json(run.output/'failures.json',failures)
        np.savez_compressed(run.output/'operators.npz',**saved)
    pd.DataFrame(resources).to_csv(run.output/'resources.csv',index=False)
    pd.DataFrame(sens).to_csv(run.output/'sensitivity.csv',index=False)
    # Full spectral differences preserve GLS information once the original
    # offset is already free. Keep their induced covariance, including signs.
    mask=a['coarse_mask'];d=a['design'][mask];n=a['nuisance'][mask];m=len(d)
    c=np.diff(np.eye(m),axis=0);v=a['thermal'][mask]
    absolute=efficient_linear_estimator(d,n,np.diag(v))
    delta_n=c@n;delta_n=delta_n[:,np.linalg.norm(delta_n,axis=0)>1e-20]
    difference=efficient_linear_estimator(c@d,delta_n,c@np.diag(v)@c.T)
    reconstructed=difference.operator@c
    write_json(run.output/'spectral_difference_control.json',dict(
        covariance_relative_error=float(np.max(abs(difference.covariance/absolute.covariance-1))),
        no2_variance_ratio=float(difference.covariance[3,3]/absolute.covariance[3,3]),
        operator_relative_error=float(np.linalg.norm(reconstructed-absolute.operator)/np.linalg.norm(absolute.operator)),
        interpretation='Invertible coordinates on the offset-free observation space do not create information. Dropping off-diagonal contrast covariance would be incorrect.'))
    run.finish(failures,extra={'input_sha256':digest(OUT/'physical/inputs.npz'),
        'estimator_sha256':digest(ROOT/'src/thz_isac/no2_design.py')})
    if failures:raise RuntimeError('Retained design failures must be resolved before interpretation')


def row_theta(row):
    return np.array([row.CO_ug_m3,row.O3_ug_m3,row.SO2_ug_m3,row.NO2_ug_m3,row.PM2_5_ug_m3,row.PM10_ug_m3-row.PM2_5_ug_m3])


def evaluation():
    completed=json.loads((OUT/'design/manifest.json').read_text())
    if completed['failures'] or len(pd.read_csv(OUT/'design/summary.csv'))!=len(CASES)*2:
        raise RuntimeError('Every design must pass before evaluation')
    run=Run(OUT/'evaluation',PROTOCOL,__file__)
    config,data,hitran=source_context();a=np.load(OUT/'physical/inputs.npz');f=a['frequency']
    hdata=np.load(OUT/'design/operators.npz');design_hash=digest(OUT/'design/operators.npz')
    forward,thermal=forward_factory(config,hitran,f);nominal=(a['gas'],a['pm'],a['background'])
    cut=pd.Timestamp(config['estimator_benchmark']['validation_end'])
    data['datetime']=pd.to_datetime(data['datetime'])
    test=data.loc[(data.datetime>cut)&(data.PM10_ug_m3>=data.PM2_5_ug_m3)].sort_values(['station','datetime'])
    rng=np.random.default_rng(PROTOCOL['seed'])
    states=rng.uniform([-5.,-2000.,1200.],[5.,2000.,1800.],size=(PROTOCOL['new_states'],3))
    selected=rng.integers(0,len(test),size=len(states))
    write_json(run.output/'frozen_evaluation.json',dict(design_sha256=design_hash,states=states.tolist(),
        selected_original_rows=test.iloc[selected].index.tolist(),selection='Frozen before any new forward evaluation'))
    absolute=[];vactual=[];records=[]
    for k,(state,index) in enumerate(zip(states,selected)):
        row=test.iloc[index];actual=forward(*state);theta=row_theta(row)
        absolute.append(mean(actual,theta)-mean(nominal,theta));vactual.append(thermal(actual[2])[0])
        records.append(dict(state=k,original_row=int(row.name),time=str(row.datetime),station=row.station,
            dt_k=state[0],dp_pa=state[1],height_m=state[2],NO2_ug_m3=row.NO2_ug_m3))
        if (k+1)%4==0:print('new modeled states',k+1,flush=True)
    # Pair selection uses station and timestamps only, with both endpoints in test.
    candidates=[]
    for station,group in test.groupby('station',sort=True):
        indices=group.index.to_numpy();time=group.datetime.to_numpy()
        valid=np.flatnonzero(np.diff(time)==np.timedelta64(1,'h'))
        candidates.extend((station,int(indices[i]),int(indices[i+1])) for i in valid)
    chosen=np.linspace(0,len(candidates)-1,PROTOCOL['real_pairs'],dtype=int)
    pairs=[candidates[i] for i in chosen]
    write_json(run.output/'frozen_pairs.json',dict(candidate_pairs=len(candidates),pairs=pairs,
        spacing='Consecutive recorded hours; acquisition budgets exclude the waiting interval.',
        geometry='The model repeats the same 45-degree slant geometry; the records are not synchronized satellite overpasses.'))
    pair_abs=[];pair_diff=[];pair_v0=[];pair_v1=[];pair_snr=[];pair_meta=[]
    surface=config['surface_conditions_from_uci_medians']
    for k,(station,i0,i1) in enumerate(pairs):
        errors=[];variances=[];snrs=[]
        for index in [i0,i1]:
            row=data.loc[index];theta=row_theta(row)
            dt=row.temperature_c+273.15-surface['temperature_k'];dp=row.pressure_hpa*100-surface['pressure_pa']
            actual=forward(dt,dp,1500.,row.dew_point_c)
            errors.append(mean(actual,theta)-mean(nominal,theta));v,snr=thermal(actual[2]);variances.append(v);snrs.append(snr)
        pair_abs.append(errors[1]);pair_diff.append(errors[1]-errors[0])
        pair_v0.append(variances[0]);pair_v1.append(variances[1]);pair_snr.append(np.minimum(snrs[0],snrs[1]))
        r0,r1=data.loc[i0],data.loc[i1]
        pair_meta.append(dict(pair=k,station=station,reference_row=i0,sample_row=i1,
            reference_time=str(r0.datetime),sample_time=str(r1.datetime),
            reference_NO2_ug_m3=r0.NO2_ug_m3,sample_NO2_ug_m3=r1.NO2_ug_m3,
            delta_NO2_ug_m3=r1.NO2_ug_m3-r0.NO2_ug_m3,
            reference_temperature_c=r0.temperature_c,sample_temperature_c=r1.temperature_c,
            reference_pressure_hpa=r0.pressure_hpa,sample_pressure_hpa=r1.pressure_hpa,
            reference_dew_point_c=r0.dew_point_c,sample_dew_point_c=r1.dew_point_c))
        if (k+1)%4==0:print('real weather/concentration pairs',k+1,'of',len(pairs),flush=True)
    saved=dict(new_bias=np.column_stack(absolute),new_thermal=np.column_stack(vactual),
        pair_absolute_bias=np.column_stack(pair_abs),pair_difference_bias=np.column_stack(pair_diff),
        pair_thermal_reference=np.column_stack(pair_v0),pair_thermal_sample=np.column_stack(pair_v1),
        pair_min_snr=np.column_stack(pair_snr))
    np.savez_compressed(run.output/'stress_inputs.npz',**saved)
    pd.DataFrame(records).to_csv(run.output/'new_state_metadata.csv',index=False)
    pd.DataFrame(pair_meta).to_csv(run.output/'pair_metadata.csv',index=False)
    rows=[];detail=[]
    for duration,case in product(PROTOCOL['durations_s'],CASES):
        name,grid,allocation,sweeps,total,residual=case;key=f'{name}|{duration:g}s'
        mask,f,d,n,b,modes,residual=case_inputs(a,case);h=hdata[key+'|h'];count=hdata[key+'|counts']
        cb=np.sum(abs(h@modes))+residual*sum(abs(h))
        # New single states evaluate absolute retrieval only; there is no
        # invented reference paired with those independent modeled states.
        suites=['real_hour_pairs']+(['new_model_states'] if sweeps==1 else [])
        for suite in suites:
            bias=(saved['new_bias'] if suite=='new_model_states' else saved[
                'pair_absolute_bias' if sweeps==1 else 'pair_difference_bias'])[mask]
            nominal_noise=float((h*h)@hdata[key+'|variance'])
            changed_thermal=(saved['new_thermal'] if suite=='new_model_states' else
                saved['pair_thermal_sample']+(saved['pair_thermal_reference'] if sweeps==2 else 0))[mask]
            state_noise=(h*h/count)@changed_thermal
            for noise_model,noise in [('nominal',nominal_noise),('weather_dependent',state_noise)]:
                risk=np.sqrt(noise+(abs(h@bias)+cb)**2)
                rows.append(dict(case=name,duration_s=duration,suite=suite,noise_model=noise_model,
                    worst_rmse=float(np.max(risk)),median_rmse=float(np.median(risk)),
                    passing_states=int(sum(risk<=1)),states=len(risk),
                    worst_atmosphere_bias=float(np.max(abs(h@bias))),calibration_bias=float(cb),
                    states_with_any_probe_below_5db=(int(np.sum(np.any(saved['pair_min_snr'][mask]<5,axis=0))) if suite=='real_hour_pairs' else None)))
                detail.extend(dict(case=name,duration_s=duration,suite=suite,noise_model=noise_model,
                    state=k,rmse=float(value),mean_bias=float((h@bias)[k])) for k,value in enumerate(risk))
    pd.DataFrame(rows).to_csv(run.output/'summary.csv',index=False)
    pd.DataFrame(detail).to_csv(run.output/'errors.csv',index=False)
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [AIR,LINES,CONFIG,OUT/'physical/inputs.npz',OUT/'design/operators.npz']},
        'frozen_design_sha256':design_hash})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['physical','design','evaluation'])
    args=parser.parse_args();globals()[args.stage]()


if __name__=='__main__':main()
