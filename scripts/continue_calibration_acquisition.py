"""Persistent calibration error and an explicitly sequential band-limited receiver."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts'), str(ROOT.parents[1]/'00_research_portfolio/scripts')]
from repair_support import Run, digest, write_json
from thz_isac.calibration_robustness import calibration_robust_estimator, envelope_risk, sequential_pilot_count
from thz_isac.bounded_bias import bounded_bias_estimator

GASES = ['CO', 'O3', 'SO2', 'NO2']
OUT = ROOT/'results/continuation_calibration'
SOURCE_URL = 'https://vadiodes.com/vna-extenders-vnax/'


def main():
    source = ROOT/'results/followup_bounded_bias/inputs.npz'
    physical = ROOT/'results/closure_robust_atmosphere/inputs.npz'
    a = np.load(source); f = np.load(physical)['frequency']
    # The archived physical spectrum uses GHz (closure_robust_atmosphere.py).
    ghz = f
    band = (ghz >= 260) & (ghz <= 400)
    assert 8 < band.sum() < len(f)
    per_tone_dbm = 23 - 10*np.log10(256)
    configurations = [dict(name='legacy_30k', mask=np.ones(len(f), bool), pilots=30000,
                           tone_power_dbm=per_tone_dbm, duration_s=.03, acquisition='ideal_simultaneous'),
                      dict(name='legacy_10m', mask=np.ones(len(f), bool), pilots=10000000,
                           tone_power_dbm=per_tone_dbm, duration_s=10., acquisition='ideal_simultaneous')]
    for power in [-1., -10.]:
        for seconds in [.03, 10., 100.]:
            configurations.append(dict(name=f'band_{power:g}dBm_{seconds:g}s', mask=band,
                pilots=sequential_pilot_count(seconds, int(band.sum())), tone_power_dbm=power,
                duration_s=seconds, acquisition='sequential_260_400_GHz'))
    protocol = dict(calibration_bounds_db=[0., 1e-5, 1e-4, 1e-3], residual_sd_db=[0., .001],
        primary='Compare the new box-aware estimator with the prior atmospheric-only estimator at identical resources and the same deterministic calibration envelope.',
        design='All 54 previously archived atmospheric discrepancies; no outcomes select the envelope or resource grid.',
        evaluation='Replay all 64 previously inspected physical states as a stress test. This is not a new independent validation set.',
        power_source=SOURCE_URL, power_locator='Vector Network Analyzer Extenders Summary of Specifications, WM-710 (WR2.8), 260-400 GHz: -1 dBm typical test-port power and +/-0.5 dB typical magnitude stability.',
        source_disagreement='The dated 2022.03.17 VDI summary lists -10 dBm for that band. Both power scenarios are retained; no production unit is characterized.',
        source_boundary='Magnitude stability is not inserted as independent residual noise or as a calibrated uncertainty bound. Published power is typical, not guaranteed.',
        likelihood='Original LEO propagation, apertures, noise figure and coherent per-tone law retained as assumptions. Thermal variance is scaled by the actual scenario tone power.',
        acquisition='One tone at a time, equal integer dwell, 1 microsecond per pilot. Zero retuning overhead is an optimistic lower-time scenario. Further acquisition sensitivities are retained separately.',
        configurations=[{k:(np.flatnonzero(v).tolist() if k=='mask' else v) for k,v in c.items()} for c in configurations])
    run=Run(OUT, protocol, __file__)
    write_json(OUT/'source_record.json', dict(url=SOURCE_URL,
        access='Official table read through the web tool on 2026-09-08. Direct requests download returned HTTP 403; that failed attempt is retained in continuation_calibration_run2.log. No original HTML snapshot is claimed.',
        extracted_fields=dict(band_GHz=[260,400],typical_power_dbm=-1.,typical_magnitude_stability_db=.5),
        dated_pdf='https://vadiodes.com/wp-content/uploads/2012/01/VDI-956_VNA-X_Typical_Performance_2022.03.17.pdf'))
    rows=[]; heldout=[]; failures=[]; resources=[]; saved={}
    for c in configurations:
        mask=c['mask']; d=a['design'][mask]; n=a['nuisance'][mask]
        bias=a['design_bias'][mask]; replay=a['heldout_bias'][mask]
        thermal=a['thermal'][mask]*10**((per_tone_dbm-c['tone_power_dbm'])/10)
        resources.append(dict(configuration=c['name'], acquisition=c['acquisition'], probes=int(mask.sum()),
            pilots_per_tone=c['pilots'], tone_power_dbm=c['tone_power_dbm'], duration_s=c['duration_s'],
            radiated_energy_j=(10**(23/10)/1000*c['duration_s'] if c['acquisition']=='ideal_simultaneous'
                else 10**(c['tone_power_dbm']/10)/1000*c['pilots']*int(mask.sum())*1e-6)))
        for residual in protocol['residual_sd_db']:
            variance=thermal/c['pilots']+residual**2
            try:
                previous=bounded_bias_estimator(d,n,variance,bias).estimator
            except Exception as error:
                failures.append(dict(configuration=c['name'], residual=residual, method='atmospheric_only', error=repr(error)))
                continue
            for epsilon in protocol['calibration_bounds_db']:
                for method in ['atmospheric_only','calibration_aware']:
                    try:
                        estimator=(previous if method=='atmospheric_only' else
                            calibration_robust_estimator(d,n,variance,bias,epsilon).estimator)
                        h=estimator.operator
                        risk,ab,cb=envelope_risk(h,variance,bias,epsilon)
                        noise=(h*h)@variance
                        replay_risk=np.sqrt(noise[:,None]+(abs(h@replay)+cb[:,None])**2)
                        key=f'{c["name"]}|{residual:g}|{epsilon:g}|{method}'
                        saved['h_'+key]=h; saved['v_'+key]=variance; saved['mask_'+key]=mask
                        for j,gas in enumerate(GASES):
                            rows.append(dict(configuration=c['name'], residual_db=residual, epsilon_db=epsilon,
                                method=method,gas=gas,design_rmse=risk[j],noise_sd=np.sqrt(noise[j]),
                                atmosphere_bias=ab[j],calibration_bias=cb[j],l1_sensitivity=abs(h[j]).sum(),
                                replay_worst_rmse=replay_risk[j].max(),replay_passes=int((replay_risk[j]<=1).sum()),
                                target_identity_error=float(np.max(abs(h@d-np.eye(4))))))
                            heldout.extend(dict(configuration=c['name'],residual_db=residual,epsilon_db=epsilon,
                                method=method,gas=gas,state=k,rmse=value) for k,value in enumerate(replay_risk[j]))
                    except Exception as error:
                        failures.append(dict(configuration=c['name'],residual=residual,epsilon=epsilon,method=method,error=repr(error)))
        pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False)
        print(c['name'], 'complete',len(rows),'rows;',len(failures),'failures',flush=True)
    pd.DataFrame(heldout).to_csv(OUT/'replay.csv',index=False)
    pd.DataFrame(resources).to_csv(OUT/'resources.csv',index=False)
    sensitivities=[]
    for seconds in [.03,10.,100.]:
        for retune in [0.,1e-4,1e-3,1e-2]:
            try: count=sequential_pilot_count(seconds,int(band.sum()),retune_s=retune);status='fits'
            except ValueError: count=0;status='no_complete_sweep'
            sensitivities.append(dict(duration_s=seconds,retune_s=retune,probes=int(band.sum()),pilots_per_tone=count,status=status))
    pd.DataFrame(sensitivities).to_csv(OUT/'retuning_sensitivity.csv',index=False)
    np.savez_compressed(OUT/'operators.npz',**saved)
    run.finish(failures,extra={'input_hashes':{str(p):digest(p) for p in [source,physical]},
        'development_attempts':['An initial preflight assumed Hz for a GHz frequency array. The explicit band-size assertion stopped the run before any solve; source-unit inspection corrected it. Initial log retained.',
            'Direct manufacturer HTML download returned HTTP 403. The public table was read using the web tool and extracted fields are retained with that access limitation.'],
        'estimator_code_sha256':digest(ROOT/'src/thz_isac/calibration_robustness.py')})
    if failures:raise RuntimeError('Solver failures retained; inspect before selecting any conclusion')


if __name__=='__main__':main()
