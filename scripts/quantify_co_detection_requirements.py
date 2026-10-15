"""Calculate CO signal scale and conditional loss resolution requirements.

No instrument resolution, random error, calibration stability or detection
probability is asserted. The loss thresholds are labeled what if inputs.
"""
from pathlib import Path
import csv
import argparse
import hashlib
import importlib.util
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import Boltzmann, speed_of_light
from scipy.optimize import minimize_scalar, brentq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cloud-length-m', type=float, choices=[20., 200.], default=200.)
CLOUD_M = parser.parse_args().cloud_length_m
OUT = ROOT / ('results/co_detection_requirements_2026_10_15' if CLOUD_M == 20 else 'results/co_detection_requirements_200m_2026_10_15')
OUT.mkdir(parents=True, exist_ok=True)


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


co = load_module('co_requirements_model', 'scripts/restart_co_observability.py')
itu = load_module('co_requirements_background', 'src/thz_isac/microwave_absorption.py')
source = ROOT / 'results/restart_2026_10_14/co_line_parameters.csv'
with source.open(encoding='utf-8') as handle:
    lines = [{key: value if key in ('upper_v', 'lower_v') else float(value)
              for key, value in row.items()} for row in csv.DictReader(handle)]
centers = sorted(row['nu_cm_1'] * co.GHZ_PER_CM for row in lines
                 if row['upper_v'] == row['lower_v'] == '0'
                 and 60 <= row['nu_cm_1'] * co.GHZ_PER_CM <= 1000)


def extra_loss_db(frequencies, concentration_ppm=1., cloud_length_m=CLOUD_M):
    cross_section_m2 = co.cross_section(np.asarray(frequencies, dtype=float), lines) * 1e-4
    number_density = co.P / (Boltzmann * co.T) * concentration_ppm * 1e-6
    return cross_section_m2 * number_density * cloud_length_m * 10 / np.log(10)


def atmospheric_loss_db(frequencies, water_pressure_pa=1000., temperature_k=296., total_pressure_pa=101325.):
    return np.asarray(itu.specific_attenuation(np.asarray(frequencies), temperature_k, total_pressure_pa,
                                              water_pressure_pa)['total']).reshape(-1) * .2


peaks = []
for center in centers:
    peak = minimize_scalar(lambda f: -float(extra_loss_db([f])[0]),
                           bounds=(center - 1., center + 1.), method='bounded',
                           options={'xatol': 1e-9})
    assert peak.success
    frequency = float(peak.x)
    signal = float(extra_loss_db([frequency])[0])
    atmosphere = float(atmospheric_loss_db([frequency])[0])
    humidity = float(atmospheric_loss_db([frequency], 1010.)[0]) - atmosphere
    peaks.append({
        'catalog_center_ghz': center,
        'modeled_peak_ghz': frequency,
        'co_db_per_ppm_for_cloud': signal,
        'atmospheric_loss_db_for_200m': atmosphere,
        'atmospheric_power_transmission': 10 ** (-atmosphere / 10),
        'co_power_drop_percent_per_1ppm': -100 * np.expm1(-signal * np.log(10) / 10),
        'co_amplitude_drop_percent_per_1ppm': -100 * np.expm1(-signal * np.log(10) / 20),
        'water_1000_to_1010pa_residual_db': humidity,
        'water_residual_equivalent_co_ppm_at_one_frequency': humidity / signal,
        'free_space_loss_db_for_200m_isotropic_antennas':
            float(20 * np.log10(4 * np.pi * frequency * 1e9 * 200 / speed_of_light)),
    })
strongest = max(peaks, key=lambda row: row['co_db_per_ppm_for_cloud'])
thresholds = [0.1, 0.01, 0.001, 0.0001]
conditional = [{'reliably_resolvable_extra_loss_db_assumed': threshold,
                'co_concentration_ppm_for_cloud': threshold / strongest['co_db_per_ppm_for_cloud']}
               for threshold in thresholds]
concentrations = [{'co_concentration_ppm': ppm,
                   'extra_co_loss_db_at_strongest_peak': ppm * strongest['co_db_per_ppm_for_cloud']}
                  for ppm in [0.01, 0.04, 0.05, 0.1, 0.15, 0.35, 0.5, 1., 1.5]]
absolute_examples = []
for reference in [0., .1]:
    for total in [.15, .35, .5, 1., 1.5]:
        enhancement = total - reference
        signal = enhancement * strongest['co_db_per_ppm_for_cloud']
        absolute_examples.append({'total_co_ppm': total, 'reference_co_ppm': reference,
                                  'enhancement_co_ppm': enhancement,
                                  'extra_loss_db_at_strongest_peak': signal})

# Derived engineering requirements for an explicit statistical operating point.
# This is not a fitted or measured error model. sigma is the error of the final
# differential dB observable, including reference error, with no systematic bias.
false_alarm = .01
detection_probability = .95
normal_margin = float(norm.ppf(1 - false_alarm) + norm.ppf(detection_probability))
statistical_requirements = [{'co_concentration_ppm': ppm,
                            'signal_db': ppm * strongest['co_db_per_ppm_for_cloud'],
                            'maximum_gaussian_residual_std_db': ppm * strongest['co_db_per_ppm_for_cloud'] / normal_margin}
                           for ppm in [0.01, 0.04, 0.05, 0.1, 0.15, 0.35, 0.5, 1., 1.5]]
statistical_limits = [{'assumed_gaussian_residual_std_db': sigma,
                       'co_ppm_for_95percent_detection_1percent_false_alarm':
                           normal_margin * sigma / strongest['co_db_per_ppm_for_cloud']}
                      for sigma in [.01, .001, .0001]]
assert np.isclose(norm.sf(norm.ppf(1 - false_alarm)), false_alarm)
assert np.isclose(norm.sf(norm.ppf(1 - false_alarm) - normal_margin), detection_probability)

parameters = [('water_partial_pressure_pa', 'water_pressure_pa', 1000., .1),
              ('temperature_k', 'temperature_k', 296., .001),
              ('total_pressure_pa', 'total_pressure_pa', 101325., 1.)]


def derivative(frequencies, key, base, step):
    return (atmospheric_loss_db(frequencies, **{key: base + step}) -
            atmospheric_loss_db(frequencies, **{key: base - step})) / (2 * step)


sensitivities = []
peak_frequency = strongest['modeled_peak_ghz']
for label, key, base, step in parameters:
    slope = float(derivative([peak_frequency], key, base, step)[0])
    refined = float(derivative([peak_frequency], key, base, step / 2)[0])
    assert np.isclose(slope, refined, rtol=1e-6)
    change = strongest['co_db_per_ppm_for_cloud'] / abs(slope)
    direction = float(np.sign(slope))
    equivalent = brentq(lambda delta: float(atmospheric_loss_db([peak_frequency], **{key: base + direction * delta})[0]) -
                        strongest['atmospheric_loss_db_for_200m'] - strongest['co_db_per_ppm_for_cloud'],
                        0., 2 * change, xtol=1e-10)
    check = float(atmospheric_loss_db([peak_frequency], **{key: base + direction * equivalent})[0]) - strongest['atmospheric_loss_db_for_200m']
    assert np.isclose(check, strongest['co_db_per_ppm_for_cloud'], rtol=1e-7)
    sensitivities.append({'parameter': label, 'background_loss_derivative_db_per_unit': slope,
                          'linearized_magnitude_equivalent_to_1ppm_co': change,
                          'one_at_a_time_signed_change_equivalent_to_1ppm_co': direction * equivalent})

# Local identifiability only: project the CO shape against a specified finite
# atmospheric model and smooth calibration error, with equal frequency weights.
# No noise covariance, probability or global inverse uniqueness follows from it.
frequency_grid = np.linspace(peak_frequency - 15., peak_frequency + 15., 301)
co_response = extra_loss_db(frequency_grid)
columns = [derivative(frequency_grid, key, base, step) for _, key, base, step in parameters]
columns += [np.ones(len(frequency_grid)), (frequency_grid - peak_frequency) / 15.]
basis = np.column_stack(columns)
scaled_basis = basis / np.linalg.norm(basis, axis=0)
u, singular_values, _ = np.linalg.svd(scaled_basis, full_matrices=False)
rank = int(np.sum(singular_values > singular_values[0] * 1e-10))
unexplained = co_response - u[:, :rank] @ (u[:, :rank].T @ co_response)
orthogonal_fraction = float(np.linalg.norm(unexplained) / np.linalg.norm(co_response))
augmented = np.column_stack((scaled_basis, co_response / np.linalg.norm(co_response)))
augmented_rank = int(np.linalg.matrix_rank(augmented, tol=1e-10))
assert rank == 5 and augmented_rank == 6
assert np.linalg.norm(scaled_basis.T @ unexplained) < 1e-12
local_identifiability = {
    'frequency_range_ghz': [float(frequency_grid[0]), float(frequency_grid[-1])],
    'frequency_step_ghz': .1, 'samples': len(frequency_grid),
    'nuisance_parameters': [label for label, _, _, _ in parameters] + ['constant_gain_db', 'linear_gain_db'],
    'metric': 'Equal frequency weights in differential dB; not an instrument covariance model',
    'nuisance_rank': rank, 'rank_with_co': augmented_rank,
    'co_response_norm_fraction_outside_nuisance_span': orthogonal_fraction,
    'nuisance_scaled_singular_values': singular_values.tolist(),
    'claim': 'CO adds a locally independent response for this explicit uniform atmosphere and smooth calibration model',
    'not_claimed': 'Global uniqueness, mixture separation, measured performance or a practical ppm limit',
}

# Check against the saved source calculation, independent of the optimized peaks.
with (ROOT / 'results/restart_2026_10_14/co_line_examples.csv').open(encoding='utf-8') as handle:
    previous = list(csv.DictReader(handle))
assert np.allclose(extra_loss_db(centers),
                   [float(row['co_extra_db_for_1ppm_20m']) * CLOUD_M / 20 for row in previous], rtol=1e-8, atol=1e-15)
assert np.allclose(atmospheric_loss_db(centers),
                   [float(row['background_db_at_200m']) for row in previous], rtol=1e-12)
f = strongest['modeled_peak_ghz']
for row in conditional:
    assert np.isclose(extra_loss_db([f], row['co_concentration_ppm_for_cloud'])[0],
                      row['reliably_resolvable_extra_loss_db_assumed'], rtol=1e-12)
assert np.isclose(extra_loss_db([f], 1., 200.)[0], 200 / CLOUD_M * extra_loss_db([f])[0])

for name, records in [('peak_comparison.csv', peaks),
                      ('conditional_ppm_thresholds.csv', conditional),
                      ('concentration_signal_scale.csv', concentrations),
                      ('absolute_and_reference_concentrations.csv', absolute_examples),
                      ('statistical_precision_requirements.csv', statistical_requirements),
                      ('conditional_statistical_limits.csv', statistical_limits),
                      ('single_frequency_atmospheric_sensitivity.csv', sensitivities)]:
    with (OUT / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

# Make the assumed finite cloud explicit beside a uniform CO path. Both use
# the same externally sourced spectroscopy; only the stated geometry changes.
lengths = np.linspace(0., 200., 401)
finite_cloud_length = np.clip(lengths - 20., 0., 20.)
signal_per_metre = strongest['co_db_per_ppm_for_cloud'] / CLOUD_M
finite_cloud_loss = signal_per_metre * finite_cloud_length
uniform_co_loss = signal_per_metre * lengths
nonzero_length = lengths[lengths >= 1.]
atmospheric_path_loss = strongest['atmospheric_loss_db_for_200m'] * nonzero_length / 200
free_space_loss = 20 * np.log10(4 * np.pi * peak_frequency * 1e9 * nonzero_length / speed_of_light)
plt.rcParams.update({'font.family': 'Georgia', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': '#F4F0E8', 'axes.facecolor': '#F4F0E8',
                     'text.color': '#242421', 'axes.labelcolor': '#242421'})
fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4))
fig.subplots_adjust(left=.07, right=.97, bottom=.26, top=.79, wspace=.25)
fig.suptitle('The plateau comes from the assumed cloud boundary', x=.07, ha='left',
             y=.97, fontsize=21)
ax = axes[0]
ax.axvspan(20, 40, color='#D89474', alpha=.2)
ax.plot(lengths, finite_cloud_loss * 1000, color='#B4472B', lw=2.5,
        label='Added CO only between 20 and 40 m')
ax.plot(lengths, uniform_co_loss * 1000, color='#69725D', lw=2.2,
        label='Added CO throughout the whole path')
ax.axvline(40, color='#B4472B', lw=.8, ls=':')
ax.set(xlim=(0, 200), ylim=(0, 11), xlabel='Total path length (m)',
       ylabel='Extra CO loss (mdB)', title='The extra chemical contribution')
ax.set_xticks([0, 20, 40, 80, 120, 160, 200])
ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.grid(alpha=.18)
ax = axes[1]
ax.plot(nonzero_length, atmospheric_path_loss, color='#B4472B', lw=2.3,
        label='Background atmospheric absorption')
ax.plot(nonzero_length, free_space_loss, color='#242421', lw=2.3,
        label='Geometric loss, isotropic antenna reference')
ax.set(xlim=(0, 200), ylim=(0, 150), xlabel='Total path length (m)',
       ylabel='Loss (dB)', title='Other losses continue after the cloud')
ax.set_xticks([0, 40, 80, 120, 160, 200])
ax.legend(frameon=False, fontsize=9, loc='center right')
ax.grid(alpha=.18)
fig.text(.07, .05, 'Chosen examples: 1 ppm added CO, 921.812 GHz, 296 K, 1 atm; water partial pressure 1000 Pa.\nThe finite cloud ends at 40 m. There is no physical rule that absorption stops after 20 m.\nLeft axis: millidecibels. Right axis: decibels. HITRAN CO + ITU P.676 atmosphere; model predictions.', fontsize=10, linespacing=1.5)
fig.savefig(OUT / 'co_path_extent_comparison.png', dpi=170)
plt.close(fig)
inputs = [source, ROOT / 'scripts/restart_co_observability.py',
          ROOT / 'src/thz_isac/microwave_absorption.py',
          ROOT / 'src/thz_isac/data/itu676_13_oxygen.csv',
          ROOT / 'src/thz_isac/data/itu676_13_water.csv', Path(__file__)]
summary = {
    'date': '2026-10-15',
    'purpose': 'Specify CO signal scale and conditional concentration requirements, not instrument performance',
    'assumptions': {'temperature_k': co.T, 'total_pressure_pa': co.P,
                    'water_partial_pressure_pa': 1000, 'cloud_length_m': CLOUD_M,
                    'total_atmospheric_path_m': 200, 'concentration': 'CO enhancement above matched reference',
                    'receiver_noise_in_forward_model': 'absent',
                    'line_model': 'Saved HITRAN main isotopologue, trace gas air broadened Voigt at 296 K',
                    'conditional_thresholds': 'Chosen reliable differential loss resolutions, not standard deviations or measured specifications'},
    'strongest_in_band_co_peak': strongest,
    'conditional_concentration_requirements': conditional,
    'concentration_signal_scale': concentrations,
    'absolute_concentration_examples': absolute_examples,
    'chosen_total_concentration_upper_ppm': 1.5,
    'formula': f"C_min_ppm = delta_A_reliable_db / {strongest['co_db_per_ppm_for_cloud']} * ({CLOUD_M:g} m / cloud_length_m)",
    'statistical_convention': {'false_alarm_probability_per_test': false_alarm,
                               'detection_probability': detection_probability,
                               'signal_to_std_requirement': normal_margin,
                               'assumptions': 'One preselected frequency, known positive signal, zero mean Gaussian residual with known sigma, no systematic bias; no search over gases or frequencies',
                               'sigma_definition': 'Standard deviation of the final differential dB residual, including reference error'},
    'statistical_precision_requirements': statistical_requirements,
    'conditional_statistical_limits': statistical_limits,
    'single_frequency_atmospheric_sensitivity': sensitivities,
    'local_spectral_identifiability': local_identifiability,
    'scenario_note': 'Concentrations in the output are enhancements above a reference, not observed background ranges',
    'checks': {'catalog_signal_matches_saved_calculation': True,
               'catalog_atmosphere_matches_saved_calculation': True,
               'conditional_thresholds_reproduce_assumed_loss': True,
               'cloud_length_scaling': True,
               'finite_difference_step_stability': True,
               'nonlinear_check_of_single_parameter_equivalent_change': True,
               'co_local_rank_increment': True},
    'limitations': ['No measured reliable loss resolution or calibration residual',
                    'No implemented or experimentally validated detector; Gaussian operating point is a chosen requirement',
                    'Atmospheric mismatch is a deterministic example, not an uncertainty distribution',
                    'One frequency cannot establish species identity with unrestricted interference',
                    'Maximum chemical peak does not identify the best instrument operating frequency'],
    'source_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in inputs},
}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps({'strongest_peak': strongest, 'statistical_requirements': statistical_requirements,
                  'statistical_limits': statistical_limits, 'atmospheric_sensitivities': sensitivities,
                  'local_spectral_identifiability': local_identifiability, 'checks': summary['checks']}, indent=2))
