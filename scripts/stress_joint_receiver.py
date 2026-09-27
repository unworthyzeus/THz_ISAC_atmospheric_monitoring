"""Retain calibration, weather, hardware and communication tradeoffs."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
from joint_receiver_support import ROOT,OUT,TARGETS,Z,fit,write
from thz_isac.hopping_receiver import HoppingPlan,moving_ofdm_frame,orbital_state
from thz_isac.payload_sensing import resource_counts


def main():
    plan=HoppingPlan(**json.loads((OUT/'selection.json').read_text())['plan'])
    data=dict(np.load(OUT/'selected_standard_45_physics.npz'))
    baseline=fit(data,plan)
    rows=[]
    scenarios=[('correlation_1GHz',dict(correlation_ghz=1.)),('correlation_100GHz',dict(correlation_ghz=100.)),
        ('independent_hop_gains',dict(hop_offsets=True)),('noise_figure_17dB',dict(noise_figure_db=17.)),
        ('unamplified_converter',dict(noise_figure_db=17.,power_dbm=-23.))]
    for label,kw in scenarios:
        try:
            r=fit(data,plan,**kw)
            for j,name in enumerate(TARGETS):
                rows.append(dict(scenario=label,target=name,status='computed',local_lod95_ug_m3=(Z+norm.ppf(.95))*r['sd'][j],
                    predicted_recall_at_1_ug_pct=100*norm.sf(Z-1/r['sd'][j]),sigma_db=.0001,total_s=20.))
        except ValueError as exc: rows.append(dict(scenario=label,status='rejected',reason=str(exc)))
    pd.DataFrame(rows).to_csv(OUT/'stress_sensitivity.csv',index=False)
    budgets=[]
    for duration in [2.,20.,100.]:
        r=fit(data,plan,total_s=duration)
        for j,name in enumerate(TARGETS):
            for concentration in ([1.,5.,10.] if j<5 else [15.,45.,90.]):
                def margin(s): return concentration-(Z+norm.ppf(.95))*fit(data,plan,total_s=duration,sigma=s)['sd'][j]
                sigma=brentq(margin,0,.1,xtol=1e-12) if margin(0)>0 else np.nan
                # Simultaneous assumed random covariance plus bounded signed
                # per-tone bias. The threshold protects both null and positive.
                epsilon=max(0.,concentration-(Z+norm.ppf(.95))*r['sd'][j])/(2*np.abs(r['operator'][j]).sum())
                budgets.append(dict(target=name,total_s=duration,concentration_ug_m3=concentration,
                    max_random_std_db_for_local_95pct=sigma,
                    max_arbitrary_bias_db_given_random_std_0p0001=epsilon if epsilon>0 else np.nan,
                    interpretation='Conditional local requirements, not measured capability; missing means insufficient information even before that additional error.'))
    pd.DataFrame(budgets).to_csv(OUT/'calibration_requirements.csv',index=False)
    # Frozen standard receiver applied to independent January background.
    other=dict(np.load(OUT/'selected_igra_01_45_physics.npz'))
    error=(other['background_db']-data['background_db'])[baseline['mask']]
    bias=baseline['operator']@error
    pd.DataFrame(dict(target=TARGETS,apparent_concentration_ug_m3=bias,
        standardized_bias=bias/baseline['sd'],scope='Background mismatch diagnostic only; not an unmatched-weather likelihood')).to_csv(OUT/'weather_mismatch.csv',index=False)
    # Compare with the best fixed block within the union of tested schedules.
    choices=[]
    for label,pp in [('selected',plan),('uniform',HoppingPlan(**json.loads((ROOT/'results/receiver_design/hopping_plan.json').read_text())['plan']))]:
        a=dict(np.load(OUT/f'{label}_standard_45_physics.npz'));r=fit(a,pp)
        # All tones must be retained to map the 16 blocks in this reference.
        if not r['mask'].all(): raise RuntimeError('Fixed-block comparison needs full SNR vector')
        perblock=np.log2(1+r['snr']).reshape(16,16).sum(axis=1)
        fixed=resource_counts(20.,symbol_duration_s=pp.symbol_duration_s)['payload']/20*perblock
        for center,rate in zip(pp.centers_ghz,fixed): choices.append(dict(plan=label,center_ghz=center,gaussian_fixed_rate_bps=rate))
    best=max(choices,key=lambda x:x['gaussian_fixed_rate_bps'])
    write('communication_tradeoff.json',dict(candidate_gaussian_rate_bps=baseline['gaussian_rate_bps'],
        best_fixed_block_among_tested=best,
        gaussian_rate_loss_vs_best_tested_fixed_pct=100*(1-baseline['gaussian_rate_bps']/best['gaussian_fixed_rate_bps']),
        candidate_transmission_s=baseline['count']['transmission_total_s'],
        interpretation='Same 16 MHz instantaneous bandwidth, power and pilot/CP overhead. Best among tested blocks, not global band optimization. Gaussian-input rate is not QPSK throughput. Both reference and sample carry payload.',
        all_fixed_blocks=choices))
    # Fresh raw moving modem spot checks at every selected center. They do not
    # validate a full acquisition trajectory or estimate concentration recall.
    center_time=brentq(lambda t:orbital_state(t)['elevation_deg']-45,-120,-1)
    frames=[]
    for j,center in enumerate(plan.centers_ghz):
        snr=baseline['snr'][16*j:16*(j+1)]
        r=moving_ofdm_frame(snr,center_ghz=center,time_from_zenith_s=center_time,seed=2026093003+j)
        frames.append(dict(hop=j,center_ghz=center,timing_correct=r['timing_correct'],
            decoded_outputs_equal=r['decoded_outputs_equal'],post_correction_cfo_rms_hz=r['post_correction_cfo_rms_hz'],**r['baseline']))
    pd.DataFrame(frames).to_csv(OUT/'selected_raw_frames.csv',index=False)
    write('scope_boundaries.json',dict(raw_frames=16,raw_frame_scope='Matched narrowband Doppler/CP and integer timing only. New frequency spot checks; full warped-time acquisition remains open.',
        measured_calibration=False,measured_concentration_validation=False,measured_aerosol_composition=False,
        unresolved=['RF power/noise/retuning/image rejection', 'Fractional timing, clock drift, time dilation, oscillator noise, pointing and multipath',
            'Actual baseline abundance and pollutant vertical profiles', 'Full atmospheric weather transfer and nonstationarity',
            'Measured spectral covariance, drift and independent field test', 'PM information and composition', 'Applicable environmental averaging/domain']))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__': main()
