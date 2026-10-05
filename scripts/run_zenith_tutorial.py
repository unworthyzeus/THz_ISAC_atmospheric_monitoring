"""Reproduce the supervisor's single compound, 90 degree, 10 GHz example.

Run from the repository root. Published spectroscopy and atmosphere models
generate the channel. Random controls are explicitly simulated observations.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ[key] = '1'

from dataclasses import asdict
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann, speed_of_light
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.zenith_tutorial import (
    WidebandPlan, coverage_geometry, overhead_motion, differential_covariance,
    single_compound_fit, detection_summary,
)
from thz_isac.atmospheric_profiles import StandardAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.physical_spectroscopy import (
    molecular_cross_section_cm2_per_molecule, concentration_ug_m3_to_number_density_cm3,
    DB_PER_NEPER,
)
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.link_budget import LEOLinkBudgetConfig, aperture_gain_dbi, free_space_path_loss_db
from thz_isac.waveform_link import physical_channel_gain, ofdm_coherent_fraction
from thz_isac.aerosol_mie import truncated_lognormal, physical_diameter_from_aerodynamic, mass_extinction
from thz_isac.attainable_estimation import efficient_linear_estimator

OUT = ROOT/'results/zenith_single_compound'
SIZES = (256, 512, 1024, 2048)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def gas_integral(lines, f, order):
    atmosphere = StandardAtmosphere()
    edges = np.array([0, .5, 1, 2, 3, 5, 8, 12, 20, 40, 70, 100])*1000
    ray = satellite_slant_quadrature(atmosphere, 90., top_altitude_m=100000,
                                    layer_edges_m=edges, order=order)
    t, p, _, _ = atmosphere.state(ray.altitude_m)
    density0 = concentration_ug_m3_to_number_density_cm3(1., NATURAL_MOLAR_MASS_G_MOL['CH3CN'])
    total = np.zeros(len(f))
    for i, (temperature, pressure, z, ds) in enumerate(zip(t, p, ray.altitude_m, ray.path_weights_m)):
        cross = molecular_cross_section_cm2_per_molecule(lines, f, 'CH3CN',
            temperature_k=temperature, pressure_pa=pressure)
        total += DB_PER_NEPER*cross*density0*np.exp(-z/1500)*100*ds
        if i % 12 == 0:
            print(f'Gas quadrature order {order}: layer {i+1}/{len(t)}', flush=True)
    return total


def physics():
    source = ROOT/'data/raw/payload_bounds/lines.csv'
    if not source.exists():
        raise FileNotFoundError('Acquire the existing payload spectroscopy first: scripts/acquire_payload_spectroscopy.py')
    dependencies = [source] + [ROOT/'src/thz_isac'/name for name in (
        'physical_spectroscopy.py', 'atmospheric_profiles.py', 'microwave_absorption.py',
        'slant_path.py', 'concentration_units.py', 'zenith_tutorial.py')]
    fingerprint = {p.relative_to(ROOT).as_posix(): sha(p) for p in dependencies}
    fingerprint['recipe'] = '235 GHz; 10 GHz; N=256,512,1024,2048; gas order 6; thermal dz100m order2; 1500m gas profile; v1'
    key = json.dumps(fingerprint, sort_keys=True)
    cache = OUT/'physics.npz'
    if cache.exists() and str(np.load(cache)['fingerprint']) == key:
        print('Reusing matching exact spectroscopy cache', flush=True)
        return dict(np.load(cache))
    lines = pd.read_csv(source)
    lines = lines.loc[lines.molecule == 'CH3CN'].copy()
    f = np.concatenate([WidebandPlan(tones=n).frequencies_ghz for n in SIZES])
    gas = gas_integral(lines, f, 6)
    # Independent denser altitude quadrature at 65 distributed frequencies.
    check = np.linspace(0, len(f)-1, 65, dtype=int)
    fine = gas_integral(lines, f[check], 10)
    err = float(np.max(abs(fine-gas[check])/fine))
    if err > .001:
        raise RuntimeError(f'Gas altitude convergence exceeds 0.1 percent: {err}')
    atmosphere = StandardAtmosphere()
    ray = satellite_slant_quadrature(atmosphere, 90., top_altitude_m=100000,
        layer_edges_m=np.arange(0, 100001, 100), order=2)
    t, p, water, _ = atmosphere.state(ray.altitude_m)
    e = water*1e6*Boltzmann*t
    background = np.zeros(len(f)); sky = np.zeros(len(f))
    for start in range(0, len(f), 128):
        part = f[start:start+128]
        layers = specific_attenuation(part, t, p, e)['total']*ray.path_weights_m[:, None]/1000
        background[start:start+128] = layers.sum(axis=0)
        sky[start:start+128] = downwelling_brightness_k(part, t, layers)
    write('physics_provenance.json', dict(inputs=fingerprint, molecule='CH3CN',
        line_count=len(lines), isotope_ids=sorted(lines.isotopologue_id.unique().tolist()),
        acquired_line_center_min_ghz=float(lines.frequency_ghz.min()),
        acquired_line_center_max_ghz=float(lines.frequency_ghz.max()),
        wing_cutoff='None within acquired line catalog', gas_scale_height_m=1500,
        gas_quadrature_max_relative_difference=err, gas_convergence_check_frequencies=len(check),
        data_role='External line parameters; generated channel; no measured CSI or concentration truth'))
    result = dict(frequency_ghz=f, gas_db_per_ug_m3=gas, background_db=background,
                  sky_temperature_k=sky, fingerprint=key)
    np.savez_compressed(cache, **result)
    return result


def subset(data, tones):
    start = sum(SIZES[:SIZES.index(tones)])
    return {key: data[key][start:start+tones] for key in
            ('frequency_ghz', 'gas_db_per_ug_m3', 'background_db', 'sky_temperature_k')}


def link(data, plan, power_dbm=25., tx_diameter=.10, rx_diameter=1., nf=7.):
    cfg = LEOLinkBudgetConfig(550., power_dbm, tx_diameter, rx_diameter,
        plan.spacing_hz, tx_aperture_efficiency=.65, rx_aperture_efficiency=.65,
        receiver_noise_figure_db=nf, implementation_loss_db=5., n_active_subcarriers=plan.tones)
    channel = physical_channel_gain(data['frequency_ghz'], data['background_db'], data['sky_temperature_k'], cfg, 90.)
    p_tone = 10**((power_dbm-30)/10)/plan.tones
    snr = channel['gain_per_watt']*p_tone
    return cfg, channel, snr


def infer(data, plan, *, total_s=20., residual_db=.001, power_dbm=25., tx_diameter=.10,
          rx_diameter=1., nf=7.):
    cfg, channel, snr = link(data, plan, power_dbm, tx_diameter, rx_diameter, nf)
    count = plan.counts(total_s)
    pilots = count['pilots_per_tone_per_acquisition']
    covariance = differential_covariance(data['frequency_ghz'], snr, pilots, residual_db)
    estimator = single_compound_fit(data['gas_db_per_ug_m3'], data['frequency_ghz'], covariance)
    d = data['gas_db_per_ug_m3']
    z0 = norm.isf(.01)*np.sqrt(estimator.covariance[0, 0])
    # Find 95% power using the fixed null estimator and positive signal noise.
    # The calibration covariance cancels in the additional positive variance.
    weights2 = estimator.operator[0]**2
    def positive_sd(q):
        extra = (20/np.log(10))**2/(2*pilots*snr)*np.expm1(np.log(10)*d*q/10)
        return float(np.sqrt(estimator.covariance[0, 0]+weights2@extra))
    local = float((norm.isf(.01)+norm.ppf(.95))*np.sqrt(estimator.covariance[0, 0]))
    upper = max(1., local*2)
    if d.max()*upper > 1:
        limit = None
    else:
        limit = float(brentq(lambda q: (q-z0)/positive_sd(q)-norm.ppf(.95), 0, upper))
    result = detection_summary(estimator, 1.)
    result['predicted_detection_pct'] = float(100*norm.sf((z0-1)/positive_sd(1)))
    result.update(total_s=total_s, residual_db=residual_db, power_dbm=power_dbm,
        tx_diameter_m=tx_diameter, rx_diameter_m=rx_diameter, noise_figure_db=nf,
        snr_min_db=float(10*np.log10(snr.min())), snr_max_db=float(10*np.log10(snr.max())),
        limit_95pct_ug_m3=limit, pilot_mean_snr_min=float(pilots*snr.min()), **count)
    return result, estimator, covariance, channel, cfg, snr


def geometry_outputs():
    rows = []
    for altitude in (400., 550., 800.):
        for elevation in (0., 10., 30., 60., 80., 90.):
            rows.append(dict(altitude_km=altitude, minimum_elevation_deg=elevation,
                **{k: float(v) for k, v in coverage_geometry(elevation, altitude).items()}))
    pd.DataFrame(rows).to_csv(OUT/'coverage.csv', index=False)
    t = np.array([0., .5, 5., 25.])
    pd.DataFrame(dict(seconds_from_zenith=t, **overhead_motion(t))).to_csv(OUT/'motion.csv', index=False)
    antenna = []
    for f in (100., 235., 300., 400.):
        for diameter in (.1, .3, .5, 1., 2.):
            beam = 1.02*speed_of_light/(f*1e9*diameter)
            antenna.append(dict(frequency_ghz=f, diameter_m=diameter, efficiency=.65,
                gain_dbi=float(aperture_gain_dbi(f, diameter, .65)),
                approximate_full_hpbw_deg=float(np.rad2deg(beam)),
                nadir_hpbw_diameter_km=float(2*550*np.tan(beam/2)),
                ruze_rms_surface_for_1db_um=float(speed_of_light/(f*1e9)*np.sqrt(np.log(10)/10)/(4*np.pi)*1e6)))
    pd.DataFrame(antenna).to_csv(OUT/'antennas.csv', index=False)
    # Off resonance molecular scattering screen. This is nitrogen, not a VOC
    # resonance prediction, and deliberately ignores all propagation loss.
    scattering = []
    for f in (100., 235., 400.):
        alpha_volume = 1.710e-30  # NIST CCCBDB N2 polarizability in m3.
        cross = 8*np.pi/3*(2*np.pi*f*1e9/speed_of_light)**4*alpha_volume**2
        density = .78084*101325/(Boltzmann*288.15)
        fraction = density*cross*1000
        area = .65*np.pi/4  # Effective area of an assumed 1 m ground dish.
        # Maximum Rayleigh phase function is 1.5/(4 pi). All transmitter
        # power crosses the gas; every scatterer is at least 1 km from Rx.
        received = 10**((25-30)/10)*fraction*1.5*area/(4*np.pi*1000**2)
        scattering.append(dict(frequency_ghz=f, n2_cross_section_m2=cross,
            n2_number_density_m3=density, scattered_fraction_1km=fraction,
            optimistic_collected_power_dbm=float(10*np.log10(received/1e-3))))
    pd.DataFrame(scattering).to_csv(OUT/'molecular_scattering_screen.csv', index=False)
    atmosphere = StandardAtmosphere()
    ray = satellite_slant_quadrature(atmosphere, 90., top_altitude_m=100000,
        layer_edges_m=np.arange(0,100001,100), order=2)
    t,p,w,_ = atmosphere.state(ray.altitude_m)
    f = np.array([100.,140.,235.,300.,325.,380.,400.])
    layers = specific_attenuation(f,t,p,w*1e6*Boltzmann*t)['total']*ray.path_weights_m[:,None]/1000
    pd.DataFrame(dict(frequency_ghz=f, zenith_gaseous_attenuation_db=layers.sum(axis=0),
        sky_temperature_k=downwelling_brightness_k(f,t,layers))).to_csv(OUT/'frequency_screen.csv', index=False)


def pm_outputs(data, covariance):
    modes = [(1500., .5, 1.7, .03, 2.5, 1.5+.01j), (1800., 4., 1.6, 2.5, 10., 1.53+.01j)]
    rows = []; columns = []
    for name, (density, median, sd, lo, hi, index) in zip(('fine', 'coarse'), modes):
        bounds = physical_diameter_from_aerodynamic(np.array([lo, hi]), density)
        dist = truncated_lognormal(median, sd, *bounds, density, order=64)
        optics = mass_extinction(data['frequency_ghz'], dist, index)
        columns.append(DB_PER_NEPER*1e-9*1000*optics['extinction'])
        for f in (100., 235., 400.):
            value = mass_extinction(np.array([f]), dist, index)
            rows.append(dict(mode=name, frequency_ghz=f, density_kg_m3=density,
                real_index=index.real, imaginary_index=index.imag,
                extinction_m2_kg=float(value['extinction'][0]), scattering_m2_kg=float(value['scattering'][0]),
                absorption_m2_kg=float(value['absorption'][0]),
                scattering_fraction=float(value['scattering'][0]/value['extinction'][0]),
                size_parameter_max=value['maximum_size_parameter'],
                attenuation_db_at_50ug_m3=float(DB_PER_NEPER*50e-9*1000*value['extinction'][0])))
    pd.DataFrame(rows).to_csv(OUT/'pm_extinction.csv', index=False)
    f = data['frequency_ghz']
    nuisance = np.column_stack([np.ones(len(f)), (f-f.mean())/np.ptp(f), data['gas_db_per_ug_m3']])
    d = np.column_stack(columns)
    chol = cholesky(covariance, lower=True)
    wn = solve_triangular(chol, nuisance, lower=True)
    basis = np.linalg.qr(wn)[0]
    wd = solve_triangular(chol, d, lower=True)
    projected = wd-basis@(basis.T@wd)
    cosine = float(projected[:, 0]@projected[:, 1]/np.linalg.norm(projected[:, 0])/np.linalg.norm(projected[:, 1]))
    try:
        fit = efficient_linear_estimator(d, nuisance, covariance)
        pm_sd = np.sqrt(np.diag(fit.covariance)).tolist()
        condition = fit.target_condition
        status = 'Numerically fitted local PM errors; not validated detection limits'
    except ValueError:
        pm_sd = None; condition = None; status = 'Unidentifiable after nuisance projection'
    write('pm_diagnosis.json', dict(status=status, residual_db=.001, total_s=20,
        projected_fine_coarse_cosine=cosine, local_sd_ug_m3=pm_sd, target_condition=condition,
        input_status='Assumed composition, density and size distributions; no PM concentration labels',
        interpretation='A larger transmitter does not establish composition, size or unique PM mass'))
    return columns


def weather_outputs(data, estimator, weather_fit):
    """Controlled background perturbations, not measured weather statistics."""
    atmosphere = StandardAtmosphere()
    ray = satellite_slant_quadrature(atmosphere, 90., top_altitude_m=100000,
        layer_edges_m=np.arange(0, 100001, 100), order=2)
    t, p, w, _ = atmosphere.state(ray.altitude_m)
    e = w*1e6*Boltzmann*t
    rows = []
    for label, temp_shift, water_scale in (('water_plus_1pct', 0., 1.01),
                                          ('water_minus_1pct', 0., .99),
                                          ('temperature_plus_1K', 1., 1.)):
        a = np.zeros(len(data['frequency_ghz']))
        for start in range(0, len(a), 128):
            f = data['frequency_ghz'][start:start+128]
            gamma = specific_attenuation(f, t+temp_shift, p, e*water_scale)['total']
            a[start:start+128] = ray.path_weights_m@gamma/1000
        mismatch = a-data['background_db']
        rows.append(dict(perturbation=label,
            maximum_absolute_attenuation_error_db=float(abs(mismatch).max()),
            apparent_ch3cn_ug_m3=float((estimator.operator@mismatch)[0]),
            apparent_ch3cn_with_background_nuisance_ug_m3=float((weather_fit.operator@mismatch)[0]),
            scope='Deterministic blank background bias only; no weather occurrence probability'))
    pd.DataFrame(rows).to_csv(OUT/'weather_mismatch.csv', index=False)
    # Convergence of absorption and thermal emission at 33 primary tones.
    ix = np.linspace(0, len(data['frequency_ghz'])-1, 33, dtype=int)
    f = data['frequency_ghz'][ix]
    fine_ray = satellite_slant_quadrature(atmosphere, 90., top_altitude_m=100000,
        layer_edges_m=np.arange(0,100001,50), order=2)
    t,p,w,_ = atmosphere.state(fine_ray.altitude_m)
    layers = specific_attenuation(f,t,p,w*1e6*Boltzmann*t)['total']*fine_ray.path_weights_m[:,None]/1000
    a = layers.sum(axis=0); sky = downwelling_brightness_k(f,t,layers)
    errors = dict(background_max_relative_difference=float(np.max(abs(a-data['background_db'][ix])/a)),
        sky_max_relative_difference=float(np.max(abs(sky-data['sky_temperature_k'][ix])/sky)),
        check_frequencies=len(ix), fine_layer_step_m=50, baseline_layer_step_m=100)
    if max(errors['background_max_relative_difference'], errors['sky_max_relative_difference']) > .001:
        raise RuntimeError('Atmospheric thermal convergence exceeds 0.1 percent')
    write('thermal_convergence.json', errors)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data_all = physics()
    geometry_outputs()
    plan = WidebandPlan()
    data = subset(data_all, plan.tones)
    base, estimator, covariance, channel, cfg, snr = infer(data, plan)
    f = data['frequency_ghz']; d = data['gas_db_per_ug_m3']
    write('baseline.json', dict(plan=asdict(plan), link=asdict(cfg), result=base,
        status='Conditional pilot receiver prediction; assumed 0.001 dB differential residual; not measured',
        hypothesis='Single prespecified CH3CN enhancement, known 1500 m exponential vertical shape',
        geometry='90 degree snapshot; finite moving windows require delay, phase, frequency and gain tracking'))
    table = pd.DataFrame(data)
    table['tx_gain_dbi'] = aperture_gain_dbi(f, cfg.tx_aperture_diameter_m, cfg.tx_aperture_efficiency)
    table['rx_gain_dbi'] = aperture_gain_dbi(f, cfg.rx_aperture_diameter_m, cfg.rx_aperture_efficiency)
    table['fspl_db'] = free_space_path_loss_db(550., f)
    table['tx_per_tone_dbm'] = cfg.tx_power_dbm-10*np.log10(plan.tones)
    table['noise_per_tone_dbm'] = 10*np.log10(channel['noise_w']/1e-3)
    table['received_per_tone_dbm'] = table.noise_per_tone_dbm+10*np.log10(snr)
    table['snr_db'] = 10*np.log10(snr)
    table['estimator_weight_ug_m3_per_db'] = estimator.operator[0]
    nuisance = np.column_stack([np.ones(len(f)), (f-f.mean())/np.ptp(f)])
    table['gain_offset_column'] = nuisance[:, 0]; table['gain_slope_column'] = nuisance[:, 1]
    table.to_csv(OUT/'tone_by_tone.csv', index=False)
    np.savez_compressed(OUT/'matrices.npz', frequency_ghz=f, A=np.column_stack([d,nuisance]),
        C=covariance, H=estimator.operator, concentration_variance=estimator.covariance)
    comparisons = []
    for power in (17., 23., 25., 26., 30., 40.):
        for residual in (0., .0001, .001, .01):
            result = infer(data, plan, power_dbm=power, residual_db=residual)[0]
            result['comparison'] = 'Power and calibration, same apertures'
            comparisons.append(result)
    for total in (2., 100.):
        for residual in (.0001, .001):
            result = infer(data, plan, total_s=total, residual_db=residual)[0]
            result['comparison'] = 'Observation time'; comparisons.append(result)
    for tx, rx, nf in ((.5, .3, 6.), (.1, .3, 7.), (.1, 1., 12.), (.5, 1., 7.)):
        result = infer(data, plan, tx_diameter=tx, rx_diameter=rx, nf=nf)[0]
        result['comparison'] = 'Aperture and receiver noise'; comparisons.append(result)
    pd.DataFrame(comparisons).to_csv(OUT/'sensitivity.csv', index=False)
    spacing_rows = []
    for n in SIZES:
        variant = WidebandPlan(tones=n)
        result = infer(subset(data_all, n), variant)[0]
        spacing_rows.append(dict(tones=n, spacing_mhz=variant.spacing_hz/1e6,
            useful_symbol_ns=1e9/variant.spacing_hz, cp_ns=variant.cp_s*1e9,
            cp_fraction_of_transmitted_time=variant.cp_s/variant.symbol_s,
            cfo_100khz_ici_fraction=1-ofdm_coherent_fraction(1e5, variant.spacing_hz),
            cfo_1mhz_ici_fraction=1-ofdm_coherent_fraction(1e6, variant.spacing_hz), **result))
    pd.DataFrame(spacing_rows).to_csv(OUT/'ofdm_spacing.csv', index=False)
    # A finite reference raw complex pilot mean is a sufficient statistic under
    # the explicitly known per-symbol phase and stationary channel assumption.
    rng = np.random.default_rng(20261005)
    q = float(base['limit_95pct_ug_m3']) if base['limit_95pct_ug_m3'] else 10.
    pilots = base['pilots_per_tone_per_acquisition']
    z = (rng.normal(size=(2, len(f)))+1j*rng.normal(size=(2, len(f))))/np.sqrt(2*pilots*snr)
    h0 = 1+z[0]; h1 = 10**(-d*q/20)+z[1]
    corr = np.exp(-abs(f[:,None]-f[None,:])/10.)
    calibration = .001*(cholesky(corr, lower=True)@rng.normal(size=len(f)))
    observed = -20*np.log10(abs(h1)/abs(h0))+calibration
    estimate = float((estimator.operator@observed)[0])
    pd.DataFrame(dict(frequency_ghz=f, true_enhancement_db=d*q,
        observed_enhancement_db=observed, calibration_residual_db=calibration)).to_csv(OUT/'worked_observation.csv', index=False)
    selected = np.array([0, 255, 511, 767, 1023])
    mini_c = covariance[np.ix_(selected, selected)]
    mini = single_compound_fit(d[selected], f[selected], mini_c, nuisance[selected])
    write('worked_example.json', dict(simulated=True, seed=20261005,
        true_concentration_ug_m3=q, selection='Analytical 95 percent power concentration before random observation',
        estimate_ug_m3=estimate, threshold_ug_m3=base['threshold_ug_m3'],
        detected=bool(estimate>base['threshold_ug_m3']),
        miniature=dict(tone_indices_zero_based=selected.tolist(),
            A=np.column_stack([d,nuisance])[selected].tolist(), C=mini_c.tolist(),
            y=observed[selected].tolist(), H=mini.operator.tolist(),
            estimate_ug_m3=float((mini.operator@observed[selected])[0]),
            sd_ug_m3=float(np.sqrt(mini.covariance[0,0])))))
    # Receiver control: independent complex means, one persistent AR(1)
    # differential calibration draw per trial, and a fixed prespecified test.
    trials = 10000; alpha = np.exp(-(f[1]-f[0])/10.)
    outputs = []
    for truth in (0., 1., q):
        estimates = []
        for _ in range(trials//100):
            innovation = rng.normal(size=(100, len(f)))
            residual = np.empty_like(innovation)
            residual[:, 0] = .001*innovation[:, 0]
            for k in range(1, len(f)):
                residual[:, k] = alpha*residual[:, k-1]+.001*np.sqrt(1-alpha**2)*innovation[:, k]
            r0 = 1+(rng.normal(size=(100,len(f)))+1j*rng.normal(size=(100,len(f))))/np.sqrt(2*pilots*snr)
            r1 = 10**(-d*truth/20)+(rng.normal(size=(100,len(f)))+1j*rng.normal(size=(100,len(f))))/np.sqrt(2*pilots*snr)
            y = -20*np.log10(abs(r1)/abs(r0))+residual
            estimates.extend((y@estimator.operator[0]).tolist())
        estimates = np.array(estimates)
        np.save(OUT/f'estimates_{truth:.6g}.npy', estimates)
        detected = int(np.sum(estimates>base['threshold_ug_m3']))
        from scipy.stats import binomtest
        interval = binomtest(detected, trials).proportion_ci()
        positive_c = differential_covariance(f, snr, pilots, .001, enhancement_db=d*truth)
        prediction = detection_summary(estimator, truth, positive_covariance=positive_c)
        outputs.append(dict(true_ug_m3=truth, trials=trials, detected=detected,
            empirical_response_pct=100*detected/trials, response_ci95_lower_pct=100*interval.low,
            response_ci95_upper_pct=100*interval.high, predicted_response_pct=prediction['predicted_detection_pct'],
            bias_ug_m3=float(estimates.mean()-truth), rmse_ug_m3=float(np.sqrt(np.mean((estimates-truth)**2))),
            residual_db=.001, total_s=20., scope='Simulated complex pilot means with ideal tracking'))
    pd.DataFrame(outputs).to_csv(OUT/'receiver_control.csv', index=False)
    pm_outputs(data, covariance)
    # Retain an unmatched background template as an explicit nuisance stress.
    weather_nuisance = np.column_stack([nuisance, data['background_db']])
    weather_fit = single_compound_fit(d, f, covariance, weather_nuisance)
    write('background_nuisance.json', detection_summary(weather_fit, 1.))
    weather_outputs(data, estimator, weather_fit)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    axes[0,0].plot(f, d*1000); axes[0,0].set(xlabel='Frequency (GHz)', ylabel='Enhancement (milli dB per µg/m³)', title='CH₃CN: published line parameters')
    axes[0,1].plot(f, table.snr_db); axes[0,1].set(xlabel='Frequency (GHz)', ylabel='SNR per tone (dB)', title='25 dBm total, 10 cm Tx, 1 m Rx')
    axes[1,0].plot(f, observed, lw=.6, alpha=.55, label='One simulated observation')
    axes[1,0].plot(f, d*q, color='black', label='Expected absorption')
    axes[1,0].set(xlabel='Frequency (GHz)', ylabel='Differential attenuation (dB)', title=f'20 s total, assumed residual 0.001 dB; q={q:.2f} µg/m³')
    axes[1,0].legend(fontsize=8)
    comparison = pd.DataFrame(comparisons)
    for residual in (0., .001, .01):
        sub = comparison[(comparison.comparison=='Power and calibration, same apertures') & (comparison.residual_db==residual)]
        axes[1,1].semilogy(sub.power_dbm, sub.limit_95pct_ug_m3, marker='o', label=f'Assumed residual {residual:g} dB')
    axes[1,1].set(xlabel='Average RF power over all tones (dBm)', ylabel='Conditional 95% limit (µg/m³)', title='More power and calibration tested separately')
    axes[1,1].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.savefig(OUT/'zenith_detection.png', dpi=180)
    plt.close(fig)
    checks = dict(unit_response_error=float(abs((estimator.operator@d)[0]-1)),
        nuisance_rejection_max=float(abs(estimator.operator@nuisance).max()),
        covariance_replay_error=float(abs((estimator.operator@covariance@estimator.operator.T)[0,0]-estimator.covariance[0,0])),
        retained_reference_and_sample=True, constant_total_power_across_spacing_sweep=True)
    write('verification.json', checks)
    source_files = [Path(__file__), ROOT/'tests/test_zenith_tutorial.py']
    source_files += sorted((ROOT/'src/thz_isac').glob('*.py'))
    source_files += sorted((ROOT/'src/thz_isac/data').glob('*.csv'))
    write('manifest.json', dict(date='2026-10-05', python=platform.python_version(), numpy=np.__version__,
        packages={name:importlib.metadata.version(name) for name in
                  ('numpy','scipy','pandas','matplotlib','hitran-api','miepython')},
        sources={p.relative_to(ROOT).as_posix():sha(p) for p in source_files},
        outputs={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json'},
        status='Conditional computational evidence, not measured field performance'))
    print(json.dumps(base, indent=2), flush=True)
    print('Saved the full tutorial evidence in results/zenith_single_compound', flush=True)


if __name__ == '__main__':
    main()
