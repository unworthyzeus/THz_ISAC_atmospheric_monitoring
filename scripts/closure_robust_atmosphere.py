"""Estimate pollutant spectra while projecting atmospheric tangent directions."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest
from run_rmse_metric_audit import build_context
from thz_isac.attainable_estimation import efficient_linear_estimator,bias_and_rmse
from thz_isac.physical_spectroscopy import build_layered_zenith_attenuation_design,apply_plane_parallel_slant

def main():
    config=json.loads((ROOT/'results/revision_0908/protocol.json').read_text())['config']
    protocol=dict(config=config,derivative_steps=[1.,500.,100.],temperatures=[-5.,0.,5.],
        pressures=[-2000.,0.,2000.],heights=[1200.,1500.,1800.],pilots=[3000,30000],
        methods=['nominal','atmospheric_tangent'],concentration_quantiles=[.5,.95],
        boundary='Tangent directions are frozen at the training median atmosphere and concentration, using central finite differences. The independent nonlinear 27-point mismatch grid evaluates their residual bias. Covariance is fixed nominal coherent noise; this does not substitute for measured receiver calibration.')
    run=Run(ROOT/'results/closure_robust_atmosphere',protocol,__file__)
    air=ROOT/'data/processed/air_quality/beijing_air_quality_clean.csv.gz'
    lines=ROOT/'data/processed/hitran/hitran_60_400GHz_lines.csv'
    data=pd.read_csv(air);hitran=pd.read_csv(lines);ctx=build_context(data,hitran,config)
    keep=ctx.snr_db>=5;frequency=np.linspace(60,400,len(keep))[keep]
    training=ctx.parameter_targets[ctx.split.train];median=np.quantile(training,.5,axis=0)
    surface=config['surface_conditions_from_uci_medians'];atm=config['atmosphere']
    def forward(t,p,height):
        design=build_layered_zenith_attenuation_design(hitran,frequency,
            surface_temperature_k=surface['temperature_k']+t,surface_pressure_pa=surface['pressure_pa']+p,
            surface_dew_point_c=surface['dew_point_c'],pollutant_scale_height_m=height,
            water_scale_height_m=atm['water_scale_height_m'],pm_scale_height_m=atm['pm_scale_height_m'],
            n_layers=atm['n_layers'],top_altitude_m=atm['top_altitude_m'],partition_sum_version=atm['partition_sum_version'])
        return tuple(apply_plane_parallel_slant(a,45) for a in
            [design.gas_db_per_ug_m3,design.pm_db_per_ug_m3,design.background_db])
    def mean(arrays,theta):return arrays[0]@theta[:4]+arrays[1]@theta[4:]+arrays[2]
    nominal=forward(0,0,1500)
    tangents=[]
    for axis,step in enumerate(protocol['derivative_steps']):
        plus=np.array([0.,0.,1500.]);minus=plus.copy();plus[axis]+=step;minus[axis]-=step
        tangents.append((mean(forward(*plus),median)-mean(forward(*minus),median))/(2*step))
    tangent=np.column_stack(tangents)
    scales=np.array([4000.,100.,40.,25.]);d=nominal[0]*scales
    nuisance=np.column_stack([np.ones(len(frequency)),nominal[2],nominal[1]])
    expanded=np.column_stack([nuisance,tangent]);snr=10**(ctx.snr_db[keep]/10)
    inputs=dict(design=d,nuisance=nuisance,expanded_nuisance=expanded,frequency=frequency,
        median=median,q95=np.quantile(training,.95,axis=0),snr=snr)
    estimators={};identities=[];failures=[]
    for pilots in protocol['pilots']:
        covariance=np.diag(2*(10/np.log(10))**2/(pilots*snr))
        for method,n in [('nominal',nuisance),('atmospheric_tangent',expanded)]:
            try:
                est=efficient_linear_estimator(d,n,covariance);estimators[pilots,method]=est
                identities.append(dict(pilots=pilots,method=method,condition=est.target_condition,
                    target_error=float(np.max(abs(est.operator@d-np.eye(4)))),
                    nuisance_error=float(np.max(abs(est.operator@(n/np.maximum(np.linalg.norm(n,axis=0),1e-300)))))))
            except Exception as error:failures.append(dict(pilots=pilots,method=method,error=repr(error)))
    rows=[]
    for dt in protocol['temperatures']:
        for dp in protocol['pressures']:
            for height in protocol['heights']:
                actual=forward(dt,dp,height)
                for q in protocol['concentration_quantiles']:
                    theta=np.quantile(training,q,axis=0);delta=mean(actual,theta)-mean(nominal,theta)
                    inputs[f'bias_{dt}_{dp}_{height}_{q}']=delta
                    for (pilots,method),est in estimators.items():
                        bias,rmse=bias_and_rmse(est,delta)
                        for j,gas in enumerate(['CO','O3','SO2','NO2']):
                            rows.append(dict(dt=dt,dp=dp,height=height,quantile=q,pilots=pilots,method=method,gas=gas,
                                bias_ratio=bias[j],noise_sd_ratio=np.sqrt(est.covariance[j,j]),rmse_ratio=rmse[j]))
        print('temperature',dt,'complete',flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(run.output/'grid.csv',index=False)
    frame.groupby(['pilots','method','gas','quantile']).agg(worst_rmse=('rmse_ratio','max'),
        worst_abs_bias=('bias_ratio',lambda x:abs(x).max()),noise_sd=('noise_sd_ratio','first')).reset_index().to_csv(run.output/'summary.csv',index=False)
    pd.DataFrame(identities).to_csv(run.output/'identities.csv',index=False)
    np.savez_compressed(run.output/'inputs.npz',**inputs)
    run.finish(failures,extra={'input_hashes':{str(p):digest(p) for p in [air,lines]}})
    if failures:raise RuntimeError('Rank or estimation failures retained')

if __name__=='__main__':main()
