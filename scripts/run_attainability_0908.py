"""Estimator attainability, systematic calibration budgets and physical mismatch."""
from pathlib import Path
import copy
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest
from run_rmse_metric_audit import build_context
from thz_isac.attainable_estimation import efficient_linear_estimator,calibration_allowance,bias_and_rmse
from thz_isac.physical_spectroscopy import build_layered_zenith_attenuation_design,apply_plane_parallel_slant

def main():
    config=json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())
    review=json.loads((ROOT/'results/review/protocol.json').read_text())
    config['surface_conditions_from_uci_medians']=review['surface_conditions']
    config['pm_model']['uci_median_fine_fraction_of_pm10']=review['pm_fine_fraction']
    protocol=dict(config=config,models=['power','coherent'],pilots=[30,300,3000,30000],
        residual_std_db=[0.,.001,.01],correlations=[0.,.9],correlation_length_ghz=10.,
        model_scenarios=['matched','temperature_plus_5K','pressure_minus_2000Pa','height_1200m','combined'],
        concentration_quantiles=[.5,.95],noise_seed=908200,noise_draws=10000,
        boundary='Known fixed covariance conditional Gaussian model. GLS is unconstrained and attains its efficient covariance only for a correct mean model. Physical mismatch scenarios are sensitivity assumptions, not calibrated error bounds. The existing real-label split is reused. Calibration allowances concern arbitrary deterministic per-probe bias and are distinct from independent random residual standard deviations.')
    run=Run(ROOT/'results/revision_0908',protocol,__file__)
    air=ROOT/'data/processed/air_quality/beijing_air_quality_clean.csv.gz'
    lines=ROOT/'data/processed/hitran/hitran_60_400GHz_lines.csv'
    data=pd.read_csv(air); hitran=pd.read_csv(lines)
    ctx=build_context(data,hitran,config)
    keep=ctx.snr_db>=5
    scales=np.array([4000.,100.,40.,25.]); gases=['CO','O3','SO2','NO2']
    d=ctx.gas_design[keep]*scales
    nuisance=np.column_stack((np.ones(len(keep)),ctx.background_db,ctx.pm_design))[keep]
    frequency=np.linspace(60,400,len(keep))[keep]
    snr=10**(ctx.snr_db[keep]/10); c=(10/np.log(10))**2
    training=ctx.parameter_targets[ctx.split.train]
    mismatch={}
    atm=config['atmosphere']; surface=config['surface_conditions_from_uci_medians']
    for scenario in protocol['model_scenarios']:
        if scenario=='matched':
            mismatch[scenario]=(ctx.gas_design[keep],ctx.pm_design[keep],ctx.background_db[keep])
            continue
        settings=dict(surface_dew_point_c=surface['dew_point_c'],
            pollutant_scale_height_m=atm['pollutant_scale_height_m'],water_scale_height_m=atm['water_scale_height_m'],
            pm_scale_height_m=atm['pm_scale_height_m'],n_layers=atm['n_layers'],top_altitude_m=atm['top_altitude_m'],
            surface_temperature_k=surface['temperature_k'],surface_pressure_pa=surface['pressure_pa'],
            partition_sum_version=atm['partition_sum_version'])
        if scenario in ['temperature_plus_5K','combined']: settings['surface_temperature_k']+=5
        if scenario in ['pressure_minus_2000Pa','combined']: settings['surface_pressure_pa']-=2000
        if scenario in ['height_1200m','combined']: settings['pollutant_scale_height_m']=1200
        design=build_layered_zenith_attenuation_design(hitran,frequency,**settings)
        mismatch[scenario]=tuple(apply_plane_parallel_slant(a,45) for a in
            [design.gas_db_per_ug_m3,design.pm_db_per_ug_m3,design.background_db])
    print('Physical mismatch designs constructed',flush=True)
    rows=[]; sensitivity=[]; checks=[]; inputs={'design':d,'nuisance':nuisance,'frequency_ghz':frequency,'snr':snr}
    for scenario,arrays in mismatch.items():
        for name,a in zip(['gas','pm','background'],arrays): inputs[scenario+'_'+name]=a
    np.savez_compressed(run.output/'inputs.npz',**inputs)
    normal=np.random.default_rng(908200).normal(size=(10000,len(snr)))
    for model in protocol['models']:
        for pilots in protocol['pilots']:
            thermal=c/pilots*(1+1/snr)**2 if model=='power' else 2*c/(pilots*snr)
            for sigma in protocol['residual_std_db']:
                for rho in protocol['correlations']:
                    corr=(1-rho)*np.eye(len(snr))+rho*np.exp(-np.abs(frequency[:,None]-frequency)/10)
                    covariance=np.diag(thermal)+sigma*sigma*corr
                    est=efficient_linear_estimator(d,nuisance,covariance)
                    allowance=calibration_allowance(est,np.ones(4))
                    floors=np.sqrt(np.diag(est.covariance))
                    checks.append(dict(model=model,pilots=pilots,sigma=sigma,rho=rho,
                        target_identity_error=float(np.max(np.abs(est.operator@d-np.eye(4)))),
                        nuisance_scaled_error=float(np.max(np.abs(est.operator@(nuisance/np.maximum(np.linalg.norm(nuisance,axis=0),1e-300))))),
                        condition=est.target_condition))
                    errors=normal@np.linalg.cholesky(covariance).T@est.operator.T
                    empirical=np.sqrt(np.mean(errors*errors,axis=0))
                    # Fitting independent errors to correlated observations uses sandwich risk.
                    independent=efficient_linear_estimator(d,nuisance,np.diag(np.diag(covariance)))
                    wrong_sd=np.sqrt(np.diag(independent.operator@covariance@independent.operator.T))
                    for j,gas in enumerate(gases):
                        rows.append(dict(model=model,pilots=pilots,residual_std_db=sigma,rho=rho,gas=gas,
                            predicted_sd_ratio=floors[j],empirical_rmse_ratio=empirical[j],
                            deterministic_bias_allowance_db=allowance[j],
                            independent_fit_actual_sd_ratio=wrong_sd[j],
                            pilot_time_lower_bound_s=pilots/1e6,
                            pilot_energy_lower_bound_j=10**((23-30)/10)*pilots/1e6))
                    if model=='coherent' and rho==0 and sigma in [0.,.001]:
                        for quantile in protocol['concentration_quantiles']:
                            theta=np.quantile(training,quantile,axis=0)
                            base=ctx.gas_design[keep]@theta[:4]+ctx.pm_design[keep]@theta[4:]
                            for scenario,(gas_d,pm_d,bg) in mismatch.items():
                                delta=gas_d@theta[:4]+pm_d@theta[4:]+bg-ctx.background_db[keep]-base
                                bias,rmse=bias_and_rmse(est,delta)
                                for j,gas in enumerate(gases):
                                    sensitivity.append(dict(pilots=pilots,sigma=sigma,quantile=quantile,scenario=scenario,
                                        gas=gas,bias_ratio=bias[j],sd_ratio=floors[j],rmse_ratio=rmse[j]))
            print(model,pilots,'complete',flush=True)
    pd.DataFrame(rows).to_csv(run.output/'attainability.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(run.output/'physical_mismatch.csv',index=False)
    pd.DataFrame(checks).to_csv(run.output/'identities.csv',index=False)
    run.finish(extra=dict(retained_probes=int(keep.sum()),input_hashes={str(p):digest(p) for p in
        [air,lines,ROOT/'results/review/protocol.json']},
        estimator_code_sha256=digest(ROOT/'src/thz_isac/attainable_estimation.py')))

if __name__=='__main__': main()
