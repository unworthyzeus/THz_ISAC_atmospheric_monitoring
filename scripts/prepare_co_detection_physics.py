"""Source based calculations for the CO detection and absorption physics deck."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import numpy as np
from PIL import ImageFont
from scipy.constants import Boltzmann, speed_of_light
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/restart_2026_10_14'
OUT = ROOT / 'results/co_detection_physics_2026_10_15'
OUT.mkdir(parents=True, exist_ok=True)

def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

co = module('co', 'scripts/restart_co_observability.py')
itu = module('itu', 'src/thz_isac/microwave_absorption.py')
with (SOURCE / 'co_line_examples.csv').open(encoding='utf-8') as handle:
    examples = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]
with (SOURCE / 'co_line_parameters.csv').open(encoding='utf-8') as handle:
    lines = [{k: v if k in ('upper_v', 'lower_v') else float(v) for k, v in row.items()}
             for row in csv.DictReader(handle)]
first = min((r for r in lines if r['upper_v'] == r['lower_v'] == '0'), key=lambda r: r['nu_cm_1'])
f0 = first['nu_cm_1'] * co.GHZ_PER_CM
gamma_ghz = first['gamma_air_cm_1_atm'] * co.GHZ_PER_CM
t2_ps = 1e3 / (2 * np.pi * gamma_ghz)
std_mhz = f0 * 1e3 * np.sqrt(Boltzmann * co.T / co.MASS_KG) / speed_of_light
doppler_fwhm_mhz = 2 * np.sqrt(2 * np.log(2)) * std_mhz
time = np.linspace(0, 400, 401)
offset_mhz = np.linspace(-.6, .6, 601)
gaussian = np.exp(-.5 * (offset_mhz / std_mhz)**2) / (std_mhz * np.sqrt(2 * np.pi))
local_f = np.linspace(105, 125, 1001)
profiles = [co.cross_section(local_f, [first], pressure) /
            (first['S_296_cm_per_molecule'] * co.GHZ_PER_CM) for pressure in [1., .1]]

arrays = np.load(SOURCE / 'channel_matrices.npz')
f = arrays['frequency_ghz']
length = arrays['length_m']
centers = np.array([r['center_ghz'] for r in examples])
indices = [int(np.argmin(abs(f - center))) for center in centers]
selection = np.unique(np.r_[np.arange(0, len(f), 2), indices, len(f) - 1])
loss = arrays['tau_co'] * 10 / np.log(10)

def background(water_pa):
    return itu.specific_attenuation(centers, 296., 101325., water_pa)['total'].reshape(-1) * .2

humidity_residual = background(1010.) - background(1000.)
for row, residual in zip(examples, humidity_residual):
    row['relative_amplitude_drop_ppm'] = (1 - row['co_amplitude_transmission']) * 1e6
    row['water_plus_10pa_residual_db'] = float(residual)
    row['water_mismatch_to_co_loss_ratio'] = float(residual / row['co_extra_db_for_1ppm_20m'])
with (OUT / 'signal_and_humidity_scales.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(examples[0]))
    writer.writeheader()
    writer.writerows(examples)

# Reconstruct the exact historical curve shown in the user's attachment.
# This is provenance for that picture, not new CO sensing evidence.
old_tones_path = ROOT / 'results/zenith_single_compound/tone_by_tone.csv'
old_case_path = ROOT / 'results/zenith_worked_steps/worked_steps.json'
with old_tones_path.open(encoding='utf-8') as handle:
    old_tones = list(csv.DictReader(handle))
old_case = json.loads(old_case_path.read_text())
old_x = [float(row['frequency_ghz']) for row in old_tones]
old_y = [float(row['gas_db_per_ug_m3']) * old_case['true_q_ug_m3'] for row in old_tones]

font = ImageFont.truetype('C:/Windows/Fonts/georgia.ttf', 100)
deck_source = (ROOT / 'scripts/build_co_detection_physics.mjs').read_text(encoding='utf-8')
characters = set(deck_source) | {chr(i) for i in range(32, 127)}
widths = {char: font.getlength(char) for char in characters if char not in '\r\n\t'}
evidence = {
    'examples': examples,
    'first_line': {'center_ghz': f0, 'gamma_ghz': gamma_ghz, 'lorentz_fwhm_ghz': 2 * gamma_ghz,
                   't2_ps': t2_ps, 'doppler_fwhm_mhz': doppler_fwhm_mhz,
                   'width_ratio_lorentz_to_doppler': 2 * gamma_ghz * 1000 / doppler_fwhm_mhz},
    'coherence': {'time_ps': time.tolist(), 'one_atm': np.exp(-time / t2_ps).tolist(),
                  'point_one_atm': np.exp(-time / (10 * t2_ps)).tolist()},
    'doppler': {'offset_mhz': offset_mhz.tolist(), 'density_per_mhz': gaussian.tolist()},
    'profiles': {'frequency_ghz': local_f.tolist(), 'one_atm': profiles[0].tolist(), 'point_one_atm': profiles[1].tolist()},
    'spectrum': {'frequency_ghz': f[selection].tolist(), 'loss_mdb': (loss[selection, -1] * 1000).tolist()},
    'paths': {'length_m': length.tolist(), 'series': [{'center_ghz': float(f[k]), 'loss_udb': (loss[k] * 1e6).tolist()} for k in indices[:3]]},
    'historical_curve': {'frequency_ghz': old_x, 'extra_loss_db': old_y, 'species': 'CH3CN',
                          'meaning': 'Historical modeled curve from the user attachment; no detector claims reused'},
    'font_widths_at_100px': widths,
}
(OUT / 'evidence.json').write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n', encoding='utf-8')

# Check the physical normalization and the frequency/time linewidth relation.
area = quad(lambda x: np.exp(-.5 * (x / std_mhz)**2) / (std_mhz * np.sqrt(2 * np.pi)), -np.inf, np.inf)[0]
assert abs(area - 1) < 1e-9
assert abs((1 / (2 * np.pi * t2_ps * 1e-12)) / (gamma_ghz * 1e9) - 1) < 1e-14
assert np.all(humidity_residual > 0)
assert np.allclose(background(1000.), [row['background_db_at_200m'] for row in examples], rtol=1e-10)
assert np.max(abs(-20 * np.log10([r['co_amplitude_transmission'] for r in examples]) -
                     [r['co_extra_db_for_1ppm_20m'] for r in examples])) < 1e-12
manifest = {
    'date': '2026-10-15',
    'purpose': 'Explain physical linewidths and quantify signal scale without asserting experimental detectability',
    'assumptions': {'temperature_k': 296, 'total_pressure_pa': 101325, 'water_reference_pa': 1000,
                    'water_perturbed_pa': 1010, 'atmospheric_path_m': 200, 'cloud_length_m': 20,
                    'co_enhancement_ppm': 1, 'receiver_noise': 'absent',
                    'humidity_case': 'Chosen deterministic sensitivity perturbation, not an uncertainty distribution'},
    'first_line': evidence['first_line'],
    'humidity_345ghz': examples[2],
    'checks': {'normalized_doppler_area': float(area), 'linewidth_coherence_relation': True,
                'baseline_matches_saved_calculation': True, 'amplitude_loss_consistency': True},
    'limitations': ['No measured channel or demonstrated hardware precision', 'HITRAN main isotopologue Voigt approximation',
                    'Effective T2 inferred from the same Lorentz width, not independently measured',
                    'Humidity sensitivity is not a complete uncertainty analysis or identifiability test',
                    'No joint atmosphere and gas retrieval or detection threshold is claimed',
                    'Historical CH3CN curve retained only to explain the attached image'],
    'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [SOURCE / 'co_line_parameters.csv', SOURCE / 'channel_matrices.npz',
                                ROOT / 'src/thz_isac/microwave_absorption.py', old_tones_path, old_case_path]},
}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps({'first_line': evidence['first_line'], 'humidity_345ghz': examples[2]}, indent=2))
