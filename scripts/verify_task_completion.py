"""Independent replay of saved counts, error percentages, limits and resources."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.constants import Boltzmann, Planck
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/task_completion'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_thermal_refinement(convergence):
    """Replay transfer in reverse layer order and audit the original threshold."""
    initial=pd.read_csv(OUT/'initial_integration_convergence.csv')
    np.testing.assert_array_equal(initial.quantity,convergence.quantity)
    np.testing.assert_array_equal(initial.acceptance_threshold,convergence.acceptance_threshold)
    np.testing.assert_array_equal(convergence.acceptance_threshold,np.full(len(convergence),.001))
    assert not initial.loc[initial.quantity=='sky_temperature_k','passed'].item()
    records=[]
    for order in [2,4]:
        old=np.load(OUT/f'physics_initial_order{order}.npz')
        new=np.load(OUT/f'physics_order{order}.npz')
        thermal=np.load(OUT/f'thermal_order{order}.npz')
        # Every pre-existing field except brightness must be bitwise preserved.
        for key in old.files:
            if key!='sky_temperature_k':np.testing.assert_array_equal(old[key],new[key])
        q=Planck*thermal['frequency_ghz']*1e9/Boltzmann
        brightness=q/np.expm1(q/2.725)
        # Independent top-to-bottom transfer recurrence, rather than the
        # production routine's vectorized sum over lower-layer transmission.
        for temp,attenuation in zip(thermal['temperature_k'][::-1],thermal['layer_attenuation_db'][::-1]):
            tau=attenuation*np.log(10)/10
            brightness=brightness*np.exp(-tau)+q/np.expm1(q/temp)*(-np.expm1(-tau))
        np.testing.assert_allclose(brightness,thermal['sky_temperature_k'],rtol=1e-12,atol=1e-11)
        np.testing.assert_array_equal(thermal['sky_temperature_k'],new['sky_temperature_k'])
        records.append(dict(order=order,initial_nodes=len(old['altitude_m']),refined_nodes=len(thermal['altitude_m']),
                            maximum_brightness_change_k=float(np.max(np.abs(new['sky_temperature_k']-old['sky_temperature_k'])))))
    before=np.load(OUT/'physics_initial_order2.npz');after=np.load(OUT/'physics_initial_order4.npz')
    initial_error=np.linalg.norm(before['sky_temperature_k']-after['sky_temperature_k'])/np.linalg.norm(after['sky_temperature_k'])
    np.testing.assert_allclose(initial_error,initial.loc[initial.quantity=='sky_temperature_k','relative_rms'].item(),rtol=1e-12)
    final_error=convergence.loc[convergence.quantity=='sky_temperature_k','relative_rms'].item()
    config=json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())['reference_link']
    receiver=config['receiver_noise_temperature_k']*(10**(config['receiver_noise_figure_db']/10)-1)
    impacts=[]
    for band,section in [('multiband_reference',slice(0,256)),('eband_73p5GHz',slice(256,512))]:
        channel=np.load(OUT/f'{band}_channel.npz')
        old_temp=after['sky_temperature_k'][section]+receiver
        new_temp=new['sky_temperature_k'][section]+receiver
        np.testing.assert_array_equal(channel['sky_temperature_k'],new['sky_temperature_k'][section])
        new_gain=channel['gain_per_watt'];old_gain=new_gain*new_temp/old_temp
        weight=(1-30/10000)*1e6/(1+1/16 if band.startswith('eband') else 1)
        old_rate=weight*np.log2(1+old_gain*channel['power_w']).sum()
        new_rate=weight*np.log2(1+new_gain*channel['power_w']).sum()
        impacts.append(dict(band=band,initial_rate_bps=float(old_rate),refined_rate_bps=float(new_rate),
             rate_change_pct=float(100*(new_rate/old_rate-1)),
             maximum_absolute_noise_change_pct=float(100*np.max(np.abs(new_temp/old_temp-1))),
             comparison='Order 4 before/after; refined power allocation held fixed in both; thermal noise change only'))
    audit=dict(threshold_changed=False,acceptance_relative_rms=.001,acceptance_percent=.1,
        initial_relative_rms=float(initial_error),initial_percent=float(initial_error*100),
        refined_relative_rms=float(final_error),refined_percent=float(final_error*100),
        reduction_factor=float(initial_error/final_error),all_other_physics_arrays_unchanged=True,
        independent_transfer_replay_passed=True,grids=records,link_impact=impacts,
        interpretation='Numerical stability of the declared model; not atmospheric measurement error or field validation')
    (OUT/'thermal_convergence_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


def main():
    protocol=json.loads((OUT/'retrieval_protocol.json').read_text())
    pm_source=ROOT/protocol['pm_truth_source']
    assert sha(pm_source)==protocol['pm_truth_sha256']
    data=np.load(OUT/'retrieval_samples.npz');metrics=pd.read_csv(OUT/'detection_metrics.csv')
    errors=pd.read_csv(OUT/'concentration_errors.csv');limits=pd.read_csv(OUT/'detection_limits.csv')
    targets=['H2CO','CH3OH','CH3CN','PM2.5','PMcoarse','PM10'];z=norm.isf(.01/6)
    for _,row in metrics.iterrows():
        key=f'{row.band}_{row.nuisance_policy}_{row.elapsed_s:g}s_{row.residual_std_db:g}'
        j=targets.index(row.target);pos=data[key+'_positive'][:,j];absent=data[key+'_absent'][:,j]
        predicted=pos>z*row.standard_error_ug_m3;null=absent>z*row.standard_error_ug_m3
        tp=int(predicted.sum());fp=int(null.sum());fn=len(pos)-tp;tn=len(absent)-fp
        assert [tp,fp,fn,tn]==[row.tp,row.fp,row.fn,row.tn]
        assert np.isclose(row.recall_pct,100*tp/len(pos))
        assert np.isclose(row.false_positive_rate_pct,100*fp/len(absent))
        if tp+fp:assert np.isclose(row.precision_pct,100*tp/(tp+fp))
    for _,row in errors.iterrows():
        key=f'{row.band}_{row.nuisance_policy}_{row.elapsed_s:g}s_{row.residual_std_db:g}'
        j=targets.index(row.target);value=data[key+'_'+row.control][:,j]
        truth=protocol['truth_ug_m3'][j] if row.control=='positive' else 0.
        rmse=np.sqrt(np.mean((value-truth)**2));mae=np.mean(np.abs(value-truth))
        assert np.isclose(row.rmse_ug_m3,rmse) and np.isclose(row.mae_ug_m3,mae)
        if truth:assert np.isclose(row.rmse_pct_of_truth,100*rmse/truth)
        else:assert pd.isna(row.rmse_pct_of_truth)
    # Zero-bias limits have an independent closed form.
    clean=limits[limits.bias_bound_db==0]
    np.testing.assert_allclose(clean.detection_limit_ug_m3,(norm.isf(.01/6)+norm.ppf(.95))*clean.standard_error_ug_m3,rtol=1e-12)
    resources=pd.read_csv(OUT/'link_resources.csv')
    for band in ['multiband_reference','eband_73p5GHz']:
        a=np.load(OUT/f'{band}_channel.npz');f=a['frequency_ghz'];power=a['power_w'];gain=a['gain_per_watt']
        assert f.min()>=60 and f.max()<=400
        assert np.isclose(power.sum(),10**((23-30)/10))
        rate=(1-30/10000)*1e6*np.log2(1+gain*power).sum()/(1+1/16 if band.startswith('eband') else 1)
        expected=resources[(resources.band==band)&(resources.pointing_error_deg==0)].iloc[0]
        assert np.isclose(rate,expected.rate_bps,rtol=1e-12)
        assert abs(expected.relative_loss)<1e-12 and expected.accepted
    convergence=pd.read_csv(OUT/'integration_convergence.csv')
    assert convergence.passed.all()
    a=np.load(OUT/'physics_order2.npz');b=np.load(OUT/'physics_order4.npz')
    for _,row in convergence.iterrows():
        actual=np.linalg.norm(a[row.quantity]-b[row.quantity])/np.linalg.norm(b[row.quantity])
        assert np.isclose(actual,row.relative_rms,rtol=1e-10)
    thermal=verify_thermal_refinement(convergence)
    hapi=pd.read_csv(OUT/'rare_isotope_hapi_validation.csv');assert hapi.passed.all()
    measured=json.loads((OUT/'measured_voc_manifest.json').read_text());assert measured['status']=='passed'
    assert sha(OUT/'measured_weather_voc.npz')==measured['output_sha256']
    # Seal completed artifacts, including preserved historical manifests.
    # Runtime logs and this verifier's previous final seals are excluded.
    outputs={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and not p.name.endswith('.log') and p.name not in ['completion_manifest.json','verification.json']}
    sources=[*sorted((ROOT/'src/thz_isac').glob('*.py')),*sorted((ROOT/'src/thz_isac/data').glob('*')),
             ROOT/'scripts/acquire_task_completion_inputs.py',ROOT/'scripts/run_task_completion_physics.py',ROOT/'scripts/run_task_completion_retrieval.py',
             ROOT/'scripts/run_measured_profile_voc.py',ROOT/'scripts/validate_task_completion_spectroscopy.py',Path(__file__)]
    sources.extend([ROOT/'scripts/refine_task_completion_sky.py',ROOT/'scripts/audit_spectroscopic_uncertainties.py'])
    sources.extend(sorted((ROOT/'tests').glob('test_*.py')))
    code={str(p.relative_to(ROOT)):sha(p) for p in sources if p.is_file()}
    documentation={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'README.md',ROOT/'docs/38_full_model_completion.md',ROOT/'docs/39_thermal_convergence_audit.md'] if p.is_file()}
    inputs={}
    for name in ['source_acquisition.json','spectroscopy_acquisition.json']:
        acquisition=json.loads((OUT/name).read_text())
        if 'processed_file' in acquisition:
            p=ROOT/acquisition['processed_file'];assert sha(p)==acquisition['processed_sha256'];inputs[str(p.relative_to(ROOT))]=sha(p)
        for rec in acquisition['records']:
            if rec['status']=='acquired' and 'file' in rec:
                p=ROOT/rec['file'];assert sha(p)==rec['sha256'];inputs[str(p.relative_to(ROOT))]=sha(p)
    experiment_inputs={str(p.relative_to(ROOT)):sha(p) for p in [pm_source,ROOT/'results/tables/physical_feasibility_config.json']}
    manifest=dict(outputs=outputs,code=code,inputs=inputs,experiment_inputs=experiment_inputs,
                  documentation=documentation,scope='Numerical replay and provenance, no field-validation claim')
    (OUT/'completion_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=dict(status='passed',output_hashes=len(outputs),code_hashes=len(code),external_inputs=len(inputs),
                detection_rows=len(metrics),error_rows=len(errors),decision_limit_rows=len(limits),rare_isotope_reference_cases=len(hapi),
                measured_weather_convergence=measured['september_order1_vs2_relative_rms'],
                thermal_threshold_changed=thermal['threshold_changed'],thermal_transfer_replay_passed=True,
                documentation_hashes=len(documentation))
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
