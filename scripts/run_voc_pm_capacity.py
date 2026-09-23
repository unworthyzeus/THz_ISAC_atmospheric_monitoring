"""First externally parameterized joint VOC/PM study with zero capacity loss.

Uses HITRAN spectra, recorded Beijing reference weather, and one recorded PM
pair. VOC unit injections are instrument-response checks, not field labels.
"""
from pathlib import Path
from dataclasses import asdict
import argparse
import contextlib
import importlib.metadata
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from repair_support import Run, digest, write_json
from thz_isac.physical_spectroscopy import (build_layered_zenith_attenuation_design,
    molecular_cross_section_cm2_per_molecule, apply_plane_parallel_slant,
    MOLAR_MASS_G_MOL, GHZ_PER_WAVENUMBER)
from thz_isac.link_budget import LEOLinkBudgetConfig, compute_leo_link_budget
from thz_isac.communication_capacity import waterfill_power, check_capacity_contract
from thz_isac.joint_voc_pm import make_joint_retrieval, fine_coarse_to_pm25_pm10

VOCS = ('H2CO','CH3OH','CH3CN')
OTHER = ('CO','O3','SO2','NO2','CH4')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--line-window-ghz', type=int, choices=[1000,3000], default=3000)
    parser.add_argument('--background', choices=['hitran','itu676-12'], default='itu676-12')
    args=parser.parse_args()
    window=args.line_window_ghz
    suffix='' if window==1000 else '_0_3000'
    ledger = ROOT/'results/voc_pm_capacity'
    out = ledger/f'{args.background}_{window}ghz'
    input_path = ROOT/f'data/processed/voc_hitran_20260922{suffix}/lines_0_{window}GHz.csv'
    if not input_path.exists():
        raise SystemExit('Run scripts/download_voc_spectroscopy.py first.')
    acquisition_name='acquisition_manifest.json' if window==1000 else 'acquisition_manifest_3000ghz.json'
    acquisition = json.loads((ledger/acquisition_name).read_text())
    if digest(input_path) != acquisition['processed_sha256']:
        raise ValueError('Input spectroscopy does not match acquisition manifest.')
    lines = pd.read_csv(input_path)
    surface = json.loads((ROOT/'results/review/protocol.json').read_text())['surface_conditions']
    config = json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())
    frame_symbols, pilots, symbol_time_s = 10000, 30, 1e-6
    protocol = dict(voc_targets=VOCS, pm_parameters=['PM2.5','PM10-PM2.5'],
        line_center_window_ghz=[0,window], frequency_window_ghz=[60,400], tones=256,
        background_model=args.background,
        surface=surface, atmosphere=config['atmosphere'], reference_link=config['reference_link'],
        frame_symbols=frame_symbols, baseline_pilots_per_frame=pilots,
        added_sensing_pilots=0, symbol_time_s=symbol_time_s, maximum_relative_capacity_loss=0.,
        frames_accumulated=[1,10,1000], residual_std_db=[0.,.001],
        noise_draws=5000, seed=20260922,
        observation='Coherent existing pilots. Exact complex pilot averages checked separately from Gaussian dB approximation.',
        pm_optics='Existing exploratory Rayleigh modes; uncalibrated optical parameters retained explicitly.',
        voc_abundance='No measured VOC labels. Zero and 1 ug/m3 injections are response controls, not environmental populations.',
        communication='Same reference atmosphere, bands, power and pilot overhead on both sides. Shannon upper bound with known channel. No coded-throughput or deployable multiband-hardware claim.',
        accumulation='Requires unchanged concentrations and channel over accumulated frames; residual floor does not average down.')
    run = Run(out,protocol,__file__)
    frequency = np.linspace(60,400,256)
    options = dict(surface_temperature_k=surface['temperature_k'],surface_pressure_pa=surface['pressure_pa'],
                   surface_dew_point_c=surface['dew_point_c'],target_gases=VOCS+OTHER)
    zenith = build_layered_zenith_attenuation_design(lines,frequency,**options)
    gas = apply_plane_parallel_slant(zenith.gas_db_per_ug_m3,45.)
    pm = apply_plane_parallel_slant(zenith.pm_db_per_ug_m3,45.)
    bg = apply_plane_parallel_slant(zenith.background_db,45.)
    hitran_background = bg.copy()
    if args.background=='itu676-12':
        from thz_isac.itu_background import itu676_12_layered_background
        bg=itu676_12_layered_background(frequency,zenith.atmosphere,
            surface_temperature_k=surface['temperature_k'],surface_dew_point_c=surface['dew_point_c'])
    pd.DataFrame(dict(frequency_ghz=frequency,hitran_background_db=hitran_background,
                     selected_background_db=bg)).to_csv(out/'background_spectrum.csv',index=False)
    print('Layered VOC, interferent and PM spectra constructed.',flush=True)
    link_cfg = LEOLinkBudgetConfig(**config['reference_link'])
    total_power = 10**((link_cfg.tx_power_dbm-30)/10)
    link = compute_leo_link_budget(frequency,45,link_cfg,bg)
    gain = link.snr_linear[0]/(total_power/len(frequency))
    power = waterfill_power(gain,total_power)
    common = dict(frame_symbols=frame_symbols,baseline_pilot_symbols=pilots,candidate_pilot_symbols=pilots)
    candidates = dict(reuse_existing_pilots=power,
                      equal_power=np.full(len(frequency),total_power/len(frequency)))
    # Diagnostic redistribution, not a claimed optimal sensing allocation.
    sensitivity = np.linalg.norm(gas[:,:3]/np.linalg.norm(gas[:,:3],axis=0),axis=1)
    candidates['voc_weighted_redistribution'] = total_power*sensitivity/sensitivity.sum()
    capacity_rows=[]
    for name,candidate in candidates.items():
        check = check_capacity_contract(gain,candidate,total_power,1e6,**common)
        capacity_rows.append(dict(policy=name,pilots_per_frame=pilots,total_power_w=float(candidate.sum()),**asdict(check)))
    extra=check_capacity_contract(gain,power,total_power,1e6,**{**common,'candidate_pilot_symbols':300})
    capacity_rows.append(dict(policy='270_extra_pilots',pilots_per_frame=300,total_power_w=total_power,**asdict(extra)))
    pd.DataFrame(capacity_rows).to_csv(out/'capacity_contract.csv',index=False)
    assert capacity_rows[0]['accepted']
    snr=gain*power
    keep=snr>=10**(.5)
    # Dropping low-SNR sensing observations does not reallocate communication power.
    voc, modes = gas[keep,:3], pm[keep]
    nuisance = np.column_stack((np.ones(keep.sum()),bg[keep],gas[keep,3:7]))
    np.savez_compressed(out/'physical_inputs.npz',frequency_ghz=frequency,gas=gas,pm=pm,
                        background_db=bg,hitran_background_db=hitran_background,
                        gain_per_watt=gain,power_w=power,sensing_mask=keep)

    # Surface spectroscopy implementation checks and line-window sensitivity.
    import hapi
    checks=[]
    with (out/'hapi_validation.txt').open('w',encoding='utf-8') as log, contextlib.redirect_stdout(log):
        hapi.db_begin(str(ROOT/f'data/raw/voc_hitran_20260922{suffix}'))
        for j,molecule in enumerate(VOCS+('CH4',)):
            x=molecular_cross_section_cm2_per_molecule(lines,frequency,molecule,
                temperature_k=surface['temperature_k'],pressure_pa=surface['pressure_pa'])
            _,reference=hapi.absorptionCoefficient_Voigt(Components=(({'H2CO':20,'CH3OH':39,'CH3CN':41,'CH4':6}[molecule],1),),
                SourceTables=molecule+f'_main_0_{window}GHz',Environment={'p':surface['pressure_pa']/101325.,'T':surface['temperature_k']},
                WavenumberGrid=frequency/GHZ_PER_WAVENUMBER,WavenumberWing=100.,IntensityThreshold=0.,
                HITRAN_units=True,Diluent={'air':1.})
            short=lines.loc[lines.frequency_ghz.between(60,400)]
            narrow=molecular_cross_section_cm2_per_molecule(short,frequency,molecule,
                temperature_k=surface['temperature_k'],pressure_pa=surface['pressure_pa'])
            truncated=molecular_cross_section_cm2_per_molecule(lines.loc[lines.frequency_ghz<=1000],frequency,molecule,
                temperature_k=surface['temperature_k'],pressure_pa=surface['pressure_pa'])
            error=float(np.max(np.abs(x-reference))/np.max(reference))
            checks.append(dict(molecule=molecule,hapi_max_error_over_peak=error,passed=error<1e-5,
                band_only_line_list_rms_difference_over_full_rms=float(np.linalg.norm(x-narrow)/np.linalg.norm(x)),
                thousand_ghz_line_list_rms_difference_over_full_rms=float(np.linalg.norm(x-truncated)/np.linalg.norm(x)),
                peak_cross_section_cm2=x.max()))
    pd.DataFrame(checks).to_csv(out/'spectroscopy_validation.csv',index=False)
    if not all(r['passed'] for r in checks):
        run.finish(failures=['VOC spectroscopy validation failed.'])
        raise RuntimeError('Inspect spectroscopy validation before using the study.')

    signal_rows=[]
    for j,name in enumerate(VOCS+OTHER):
        signal_rows.append(dict(molecule=name,peak_db_per_ug_m3=float(gas[:,j].max()),
             rms_db_per_ug_m3=float(np.sqrt(np.mean(gas[:,j]**2))),
             lines_in_band=int(((lines.molecule==name)&lines.frequency_ghz.between(60,400)).sum())))
    pd.DataFrame(signal_rows).to_csv(out/'spectral_sensitivity.csv',index=False)
    if keep.sum()<12:
        summary=dict(status='insufficient_sensing_tones',retained_sensing_probes=int(keep.sum()),
            maximum_per_tone_snr_db=float(10*np.log10(snr.max())),capacity=capacity_rows[0],
            reason='Too few tones pass the predeclared per-pilot 5 dB threshold for joint targets and nuisance. No precision or estimates claimed.',
            background_model=args.background)
        write_json(out/'summary.json',summary)
        run.finish(failures=[summary['reason']],extra=dict(summary=summary,input_sha256=digest(input_path)))
        print(json.dumps(summary,indent=2),flush=True)
        return
    rows=[]; controls=[]; failures=[]; bounded_controls=[]
    rng=np.random.default_rng(protocol['seed'])
    real=rng.normal(size=(protocol['noise_draws'],keep.sum()))
    imag=rng.normal(size=real.shape)
    source_row=pd.read_csv(ROOT/'results/tables/single_channel_repair_predictions.csv',nrows=1).iloc[0]
    truth=np.array([1.,1.,1.,source_row['true_PM2.5'],source_row['true_PM10']-source_row['true_PM2.5']])
    write_json(out/'response_control.json',dict(voc_unit_injection_ug_m3=1.,
        interpretation='Unit response control, not a measured VOC abundance or population benchmark.',
        pm_source='results/tables/single_channel_repair_predictions.csv first row',
        datetime=source_row['datetime'],station=source_row['station'],target_values=truth.tolist()))
    for frames in protocol['frames_accumulated']:
        for residual in protocol['residual_std_db']:
            n_pilots=pilots*frames
            thermal=2*(10/np.log(10))**2/(n_pilots*snr[keep])
            covariance=np.diag(thermal+residual**2)
            joint=make_joint_retrieval(voc,modes,nuisance,covariance,VOCS)
            sd=np.sqrt(np.diag(joint.estimator.covariance))
            gaussian=real*np.sqrt(np.diag(covariance))
            errors=joint.estimate(gaussian)
            empirical=np.sqrt(np.mean(errors**2,axis=0))
            pmcov=joint.reported_pm_covariance()
            pmerrors=fine_coarse_to_pm25_pm10(errors)
            for j,name in enumerate(joint.target_names):
                ppb=sd[j]*8.314462618*surface['temperature_k']/(surface['pressure_pa']*MOLAR_MASS_G_MOL[name])*1000 if name in VOCS else None
                rows.append(dict(frames=frames,elapsed_s=frames*frame_symbols*symbol_time_s,
                    total_existing_pilots=n_pilots,added_sensing_pilots=0,residual_std_db=residual,target=name,
                    predicted_sd_ug_m3=sd[j],empirical_noise_rmse_ug_m3=empirical[j],
                    predicted_sd_ppb=ppb,condition=joint.estimator.target_condition,
                    systematic_bias_allowance_for_1ug_m3_rmse_db=None if sd[j]>=1 else
                    float(np.sqrt(1-sd[j]**2)/np.abs(joint.estimator.operator[j]).sum())))
            rows.append(dict(frames=frames,elapsed_s=frames*frame_symbols*symbol_time_s,
                total_existing_pilots=n_pilots,added_sensing_pilots=0,residual_std_db=residual,target='PM10',
                predicted_sd_ug_m3=float(np.sqrt(pmcov[1,1])),empirical_noise_rmse_ug_m3=float(np.sqrt(np.mean(pmerrors[:,1]**2))),
                predicted_sd_ppb=None,condition=joint.estimator.target_condition,
                systematic_bias_allowance_for_1ug_m3_rmse_db=None))
            if residual==0:
                signal=joint.design@truth
                # Exact coherent complex pilot average relative to a perfect
                # known clear-sky reference. Noise power is fixed at reference.
                amplitude=10**(-signal/20)
                noise=(real+1j*imag)/np.sqrt(2*n_pilots*snr[keep])
                exact=-20*np.log10(np.abs(amplitude+noise))
                estimates=joint.estimate(exact)
                for j,name in enumerate(joint.target_names):
                    controls.append(dict(frames=frames,target=name,truth_ug_m3=truth[j],
                        mean_estimate_ug_m3=float(estimates[:,j].mean()),
                        rmse_ug_m3=float(np.sqrt(np.mean((estimates[:,j]-truth[j])**2))),
                        gaussian_predicted_sd_ug_m3=sd[j],negative_estimate_fraction=float(np.mean(estimates[:,j]<0))))
                # Constraints can regularize the enormous PM ambiguity but
                # cannot supply independent information. Record null behavior.
                for label,response,expected in [('unit_voc_and_recorded_pm',exact[:100],truth),
                                                  ('all_targets_absent',gaussian[:100],np.zeros(5))]:
                    bounded=np.vstack([joint.estimate_nonnegative(y) for y in response])
                    for j,name in enumerate(joint.target_names):
                        bounded_controls.append(dict(frames=frames,control=label,target=name,
                            truth_ug_m3=expected[j],mean_estimate_ug_m3=float(bounded[:,j].mean()),
                            rmse_ug_m3=float(np.sqrt(np.mean((bounded[:,j]-expected[j])**2))),
                            nonzero_fraction=float(np.mean(bounded[:,j]>1e-10)),draws=len(response)))
            # Unknown smooth f and f^4 calibration terms span the Rayleigh PM
            # signatures. The rank guard must reject this stronger nuisance case.
            smooth=np.column_stack((nuisance,frequency[keep]/400,(frequency[keep]/400)**4))
            try:
                make_joint_retrieval(voc,modes,smooth,covariance,VOCS)
                raise AssertionError('PM must be unidentifiable with arbitrary Rayleigh-shaped calibration.')
            except ValueError as exc:
                failures.append(dict(frames=frames,residual_std_db=residual,
                   case='unknown_linear_and_quartic_spectral_calibration',status='unidentifiable',reason=str(exc)))
    pd.DataFrame(rows).to_csv(out/'joint_precision.csv',index=False)
    pd.DataFrame(controls).to_csv(out/'complex_pilot_response_controls.csv',index=False)
    pd.DataFrame(bounded_controls).to_csv(out/'nonnegative_response_controls.csv',index=False)
    pd.DataFrame(failures).to_csv(out/'identifiability_failures.csv',index=False)

    # Source-inspired physical residual diagnostic, with explicit null controls.
    n=30; covariance=np.diag(2*(10/np.log(10))**2/(n*snr[keep]))
    joint=make_joint_retrieval(voc,modes,nuisance,covariance,VOCS)
    matched=joint.design@truth + real[0]*np.sqrt(np.diag(covariance))
    normalized=(frequency[keep]-frequency[keep].mean())/np.ptp(frequency[keep])
    bad=matched+5*np.sin(19*normalized)
    write_json(out/'spectral_fit_checks.json',dict(matched=joint.spectral_fit(matched),
        deliberately_mismatched_response=joint.spectral_fit(bad),
        boundary='A deliberately large shape-mismatch unit test; fit p-values are conditional on known Gaussian covariance and do not certify a VOC detection.'))
    summary=dict(retained_sensing_probes=int(keep.sum()),communication_active_probes=int(np.sum(power>0)),
        background_model=args.background,line_center_window_ghz=window,
        capacity=capacity_rows[0],pm_signature_correlation=float(np.corrcoef(modes.T)[0,1]),
        formaldehyde_methane_peak_sensitivity_ratio=float(gas[:,0].max()/gas[:,-1].max()),
        main_conclusion='Existing-pilot reuse preserves the declared communication rate exactly. Joint VOC/PM estimates have large conditional errors; smooth calibration uncertainty makes joint PM unidentifiable.',
        field_validation=False)
    write_json(out/'summary.json',summary)
    plot_results(out,pd.DataFrame(rows),pd.DataFrame(capacity_rows))
    run.finish(extra=dict(input_hashes={str(p.relative_to(ROOT)):digest(p) for p in
        [input_path,ROOT/'results/review/protocol.json',ROOT/'results/tables/physical_feasibility_config.json',
         ROOT/'results/tables/single_channel_repair_predictions.csv']},
        code_hashes={str(p.relative_to(ROOT)):digest(p) for p in
        [ROOT/'src/thz_isac/physical_spectroscopy.py',ROOT/'src/thz_isac/communication_capacity.py',ROOT/'src/thz_isac/joint_voc_pm.py',ROOT/'src/thz_isac/itu_background.py']},
        additional_software={name:importlib.metadata.version(name) for name in ['hitran-api','matplotlib','psutil','itur']},
        outputs={p.name:digest(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json' and p.suffix!='.log'},
        summary=summary))
    print(json.dumps(summary,indent=2),flush=True)


def plot_results(out,precision,capacity):
    fig,axes=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
    zero=precision[precision.residual_std_db==0]
    for target,group in zero.groupby('target',sort=False):
        axes[0].loglog(group.elapsed_s,group.predicted_sd_ug_m3,'o-',label=target)
    axes[0].set(xlabel='Observation duration (s)',ylabel='Conditional standard error (ug/m3)',
                title='Joint retrieval using existing pilots')
    axes[0].legend(fontsize=8,ncol=2); axes[0].grid(alpha=.25,which='both')
    labels=['Existing pilots','Equal power','VOC-weighted power','Extra pilots']
    axes[1].bar(labels,100*capacity.relative_loss,color=['#246c56','#b77428','#b77428','#b77428'])
    axes[1].set(ylabel='Rate loss against communication optimum (%)',title='Zero-loss requirement')
    axes[1].tick_params(axis='x',rotation=22)
    fig.suptitle('Externally parameterized simulation; uncalibrated PM and receiver model',fontsize=11)
    fig.savefig(out/'voc_pm_capacity.png',dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
