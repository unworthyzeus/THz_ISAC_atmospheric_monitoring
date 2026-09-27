"""Frozen bias-envelope design, unseen nonlinear states and receiver requirements."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from repair_support import Run, digest, write_json
from run_rmse_metric_audit import build_context
from thz_isac.attainable_estimation import efficient_linear_estimator, bias_and_rmse
from thz_isac.bounded_bias import bounded_bias_estimator
from thz_isac.physical_spectroscopy import build_layered_zenith_attenuation_design, apply_plane_parallel_slant

GASES = ['CO', 'O3', 'SO2', 'NO2']


def main():
    protocol = dict(design='All 54 archived nonlinear bias vectors, from 27 atmospheric states and two training concentration quantiles; previously inspected design evidence.',
        primary_pilots=30000, pilot_grid=[30000, 300000, 3000000, 10000000],
        residual_grid_db=[0., .001, .01], methods=['nominal', 'atmospheric_tangent', 'bounded_bias'],
        heldout_seed=909510, heldout_states=64,
        heldout='Independent uniform draws over T offset [-5,5] K, pressure offset [-2000,2000] Pa and gas height [1200,1800] m. Concentrations are complete real training records selected without outcome filtering.',
        selection='No heldout outcome selects the bias envelope, method, pilots or covariance. Holdout is modeled sensitivity, not measured radio validation.',
        target='Per-gas RMSE normalized by [4000,100,40,25] ug/m3 at most one.',
        resource='1 microsecond per pilot; 23 dBm total transmitted power; ideal simultaneous probes. Retuning/coherence overhead excluded.',
        assumptions='Known diagonal coherent covariance; residual is independent random noise. No measured systematic-error calibration or physical uncertainty coverage is claimed.',
        numerical='Whitened null-space QP/SOCP with CLARABEL. Bias-response relative rank cutoff 1e-10. Achieved risks and identities are independently recomputed; no formal interval optimality certificate.')
    run = Run(ROOT / 'results/followup_bounded_bias', protocol, __file__)
    previous = ROOT / 'results/closure_robust_atmosphere/inputs.npz'
    archive = np.load(previous)
    d = archive['design']; n = archive['nuisance']; expanded = archive['expanded_nuisance']
    b = np.column_stack([archive[k] for k in archive.files if k.startswith('bias_')])
    thermal = 2 * (10 / np.log(10)) ** 2 / archive['snr']
    estimates = {}; rows = []; identities = []; failures = []
    for pilots in protocol['pilot_grid']:
        for residual in protocol['residual_grid_db']:
            variance = thermal / pilots + residual ** 2
            for method in protocol['methods']:
                try:
                    if method == 'bounded_bias':
                        solved = bounded_bias_estimator(d, n, variance, b)
                        est = solved.estimator
                    else:
                        est = efficient_linear_estimator(d, expanded if method == 'atmospheric_tangent' else n, np.diag(variance))
                    estimates[pilots, residual, method] = est
                    risk = np.sqrt(np.diag(est.covariance) + np.max(abs(est.operator @ b), axis=1) ** 2)
                    for j, gas in enumerate(GASES):
                        rows.append(dict(pilots=pilots, residual_db=residual, method=method, gas=gas,
                            design_worst_rmse=risk[j], noise_sd=np.sqrt(est.covariance[j,j]),
                            worst_abs_bias=np.max(abs(est.operator[j] @ b)), meets_target=bool(risk[j] <= 1)))
                    identities.append(dict(pilots=pilots, residual_db=residual, method=method,
                        target_error=float(np.max(abs(est.operator @ d - np.eye(4))))))
                except Exception as error:
                    failures.append(dict(pilots=pilots, residual_db=residual, method=method, error=repr(error)))
        print('design pilots', pilots, 'complete', flush=True)
    pd.DataFrame(rows).to_csv(run.output / 'design.csv', index=False)
    # Per-gas matched lower bounds: even exact atmospheric knowledge cannot improve
    # upon these unbiased linear Gaussian thermal-only floors at fixed resources.
    floor = efficient_linear_estimator(d, n, np.diag(thermal)).covariance.diagonal()
    pd.DataFrame(dict(gas=GASES, necessary_thermal_pilots=floor,
        duration_s=floor*1e-6, energy_j=floor*1e-6*10**(23/10)/1000)).to_csv(run.output/'necessary_resources.csv',index=False)
    requirements = []
    for residual in protocol['residual_grid_db']:
        for j, gas in enumerate(GASES):
            lo, hi = 30., 1e9
            upper = bounded_bias_estimator(d,n,thermal/hi+residual**2,b)
            if upper.design_rmse[j] > 1:
                requirements.append(dict(gas=gas,residual_db=residual,status='not_reached_by_1e9_pilots',pilots=np.nan,duration_s=np.nan,energy_j=np.nan))
                continue
            for _ in range(25):
                mid = np.sqrt(lo*hi)
                risk = bounded_bias_estimator(d,n,thermal/mid+residual**2,b).design_rmse[j]
                if risk <= 1: hi = mid
                else: lo = mid
            count = int(np.ceil(hi))
            requirements.append(dict(gas=gas,residual_db=residual,status='finite_design_envelope',pilots=count,duration_s=count*1e-6,energy_j=count*1e-6*10**(23/10)/1000))
        print('requirements residual',residual,'complete',flush=True)
    pd.DataFrame(requirements).to_csv(run.output/'requirements.csv',index=False)
    config = json.loads((ROOT/'results/revision_0908/protocol.json').read_text())['config']
    air = ROOT/'data/processed/air_quality/beijing_air_quality_clean.csv.gz'
    lines = ROOT/'data/processed/hitran/hitran_60_400GHz_lines.csv'
    data = pd.read_csv(air); hitran = pd.read_csv(lines); ctx = build_context(data, hitran, config)
    training = ctx.parameter_targets[ctx.split.train]
    surface = config['surface_conditions_from_uci_medians']; atm = config['atmosphere']
    frequency = archive['frequency']
    def forward(dt,dp,height):
        design = build_layered_zenith_attenuation_design(hitran,frequency,
            surface_temperature_k=surface['temperature_k']+dt,surface_pressure_pa=surface['pressure_pa']+dp,
            surface_dew_point_c=surface['dew_point_c'],pollutant_scale_height_m=height,
            water_scale_height_m=atm['water_scale_height_m'],pm_scale_height_m=atm['pm_scale_height_m'],
            n_layers=atm['n_layers'],top_altitude_m=atm['top_altitude_m'],partition_sum_version=atm['partition_sum_version'])
        return tuple(apply_plane_parallel_slant(a,45) for a in [design.gas_db_per_ug_m3,design.pm_db_per_ug_m3,design.background_db])
    def mean(arrays,theta): return arrays[0]@theta[:4]+arrays[1]@theta[4:]+arrays[2]
    nominal = forward(0.,0.,1500.)
    rng = np.random.default_rng(protocol['heldout_seed'])
    states = rng.uniform([-5.,-2000.,1200.],[5.,2000.,1800.],size=(protocol['heldout_states'],3))
    indices = rng.integers(0,len(training),size=len(states))
    write_json(run.output/'heldout_protocol.json',dict(states=states.tolist(),training_indices=indices.tolist()))
    heldout=[]; biases=[]
    for k, ((dt,dp,height), index) in enumerate(zip(states,indices)):
        theta=training[index]; delta=mean(forward(dt,dp,height),theta)-mean(nominal,theta); biases.append(delta)
        for (pilots,residual,method),est in estimates.items():
            bias,rmse=bias_and_rmse(est,delta)
            for j,gas in enumerate(GASES):
                heldout.append(dict(state=k,training_index=int(index),dt=dt,dp=dp,height=height,
                    pilots=pilots,residual_db=residual,method=method,gas=gas,bias=bias[j],rmse=rmse[j],meets_target=bool(rmse[j]<=1)))
        if (k+1)%8==0: print('heldout',k+1,'complete',flush=True)
    frame=pd.DataFrame(heldout);frame.to_csv(run.output/'heldout.csv',index=False)
    frame.groupby(['pilots','residual_db','method','gas']).agg(worst_rmse=('rmse','max'),mean_rmse=('rmse','mean'),passing_states=('meets_target','sum'),n=('state','size')).reset_index().to_csv(run.output/'heldout_summary.csv',index=False)
    arrays=dict(design=d,nuisance=n,expanded_nuisance=expanded,design_bias=b,heldout_bias=np.column_stack(biases),thermal=thermal)
    for key,est in estimates.items(): arrays['operator_'+str(key)]=est.operator
    np.savez_compressed(run.output/'inputs.npz',**arrays)
    pd.DataFrame(identities).to_csv(run.output/'identities.csv',index=False)
    run.finish(failures,extra={'input_hashes':{str(p):digest(p) for p in [previous,air,lines]},
        'development_attempts':['An exploratory dense parameterization failed in CLARABEL before holdout generation. Orthogonal variance decomposition and bias-response rank reduction resolved the numerical failure.'],
        'estimator_code_sha256':digest(ROOT/'src/thz_isac/bounded_bias.py')})
    if failures: raise RuntimeError('Failed estimator configurations retained')


if __name__=='__main__': main()
