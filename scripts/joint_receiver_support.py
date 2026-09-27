"""Shared physics and inference for a separate five-gas receiver revision."""
from pathlib import Path
from dataclasses import replace
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.waveform_link import physical_channel_gain
from thz_isac.communication_capacity import waterfill_power
from thz_isac.payload_sensing import attenuation_variance
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL, DB_PER_NEPER, molecular_cross_section_cm2_per_molecule
from design_payload_receiver import config
OUT = ROOT/'results/joint_receiver_revision'
GASES = ['H2CO', 'CH3OH', 'CH3CN', 'CH3Cl', 'HCOOH', 'CO', 'O3', 'SO2', 'NO2']
TARGETS = GASES[:5]+['PM2.5', 'PMcoarse', 'PM10']
MASSES = {'CH3Cl': 50.485, 'HCOOH': 46.025}
Z = norm.isf(.01/8)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(name, obj):
    OUT.mkdir(exist_ok=True)
    (OUT/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def initialize(frequency):
    global LINES, FREQUENCY
    frames = [pd.read_csv(ROOT/'data/raw/payload_bounds/lines.csv'),
              pd.read_csv(ROOT/'results/receiver_design/voc_pm_extension/lines.csv')]
    LINES = {name: group for name, group in pd.concat(frames).groupby('molecule')}
    FREQUENCY = frequency
    MOLAR_MASS_G_MOL.update(MASSES)


def layer(task):
    name, t, p, density = task[:4]
    frequency = FREQUENCY if len(task)==4 else FREQUENCY[:task[4]]
    return DB_PER_NEPER*100*density*molecular_cross_section_cm2_per_molecule(
        LINES[name], frequency, name, temperature_k=t, pressure_pa=p)


def fit(data, plan, *, total_s=20., sigma=.0001, elevation=45., correlation_ghz=10.,
        power_dbm=23., noise_figure_db=6., slope=True, hop_offsets=False):
    cfg = config(plan.spacing_hz, power_dbm, noise_figure_db)
    ground = float(data.get('ground_altitude_m', 0.))/1000
    cfg = replace(cfg, earth_radius_km=cfg.earth_radius_km+ground, satellite_altitude_km=cfg.satellite_altitude_km-ground)
    gains = physical_channel_gain(plan.frequency_ghz, data['background_db'], data['sky_temperature_k'], cfg, elevation)['gain_per_watt']
    power = np.concatenate([waterfill_power(g, 10**((power_dbm-30)/10)) for g in gains.reshape(-1,16)])
    snr = gains*power
    mask = snr >= 10**.5
    if mask.sum() < 20:
        raise ValueError('Fewer than 20 tones meet the sensing gate')
    f = plan.frequency_ghz[mask]
    d = np.column_stack([data['gas'][:, :5], data['pm']])[mask]
    n = np.column_stack([np.ones(len(f)), data['background_db'][mask], data['gas'][mask, 5:]])
    if slope:
        n = np.column_stack([n, (f-f.mean())/np.ptp(f)])
    if hop_offsets:
        n = np.column_stack([n, np.repeat(np.eye(16),16,axis=0)[mask]])
    count = plan.counts(total_s)
    thermal = 2*attenuation_variance(snr[mask], count['payload'], 'm2m4')
    correlation = np.exp(-abs(f[:,None]-f[None,:])/correlation_ghz)
    covariance = np.diag(thermal)+sigma**2*correlation
    e = efficient_linear_estimator(d,n,covariance)
    scale = np.linalg.norm(d,axis=0)
    error = np.max(abs((e.operator@d)*scale[:,None]/scale[None,:]-np.eye(d.shape[1])))
    if error > 1e-5:
        raise ValueError('Numerically unstable target separation')
    h = np.vstack([e.operator,e.operator[-2:].sum(axis=0)])
    return dict(design=d,nuisance=n,operator=h,sd=np.sqrt(np.diag(h@covariance@h.T)),
        covariance=covariance,correlation=correlation,thermal=thermal,snr=snr[mask],mask=mask,
        count=count,power=power,condition=e.target_condition,identity_error=error,
        gaussian_rate_bps=plan.net_rate_bps(gains,power,total_s))
