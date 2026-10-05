"""Geometry and calibrated pilot inference for the single compound tutorial.

This is a conditional receiver model, not measured detection performance.
All RF powers refer to the total average output across active tones.
"""
from dataclasses import dataclass

import numpy as np
from scipy.constants import speed_of_light
from scipy.stats import norm

from .attainable_estimation import efficient_linear_estimator
from .link_budget import leo_slant_range_km


def coverage_geometry(elevation_deg, altitude_km=550.0, earth_radius_km=6371.0):
    """Spherical visible cap above a ground elevation mask, without refraction."""
    distance = leo_slant_range_km(elevation_deg, altitude_km, earth_radius_km)
    el = np.deg2rad(elevation_deg)
    psi = np.arccos(earth_radius_km / (earth_radius_km + altitude_km) * np.cos(el)) - el
    psi = np.maximum(psi, 0.0)
    return dict(slant_range_km=distance, central_angle_deg=np.rad2deg(psi),
                ground_arc_radius_km=earth_radius_km * psi,
                coverage_area_km2=2 * np.pi * earth_radius_km**2 * (1 - np.cos(psi)),
                satellite_off_nadir_deg=90 - np.asarray(elevation_deg) - np.rad2deg(psi))


def overhead_motion(time_s, altitude_km=550.0, frequency_ghz=235.0):
    """Circular overhead orbit over a nonrotating spherical Earth.

    Time zero is zenith. Returned Doppler is signed for a downlink.
    """
    r = 6371e3
    rs = r + altitude_km * 1000
    omega = np.sqrt(3.986004418e14 / rs**3)
    angle = omega * np.asarray(time_s, float)
    distance = np.sqrt((rs-r)**2 + 4*r*rs*np.sin(angle/2)**2)
    radial_speed = r * rs * omega * np.sin(angle) / distance
    elevation = np.rad2deg(np.arcsin(np.clip((rs*np.cos(angle)-r)/distance, -1, 1)))
    return dict(elevation_deg=elevation, slant_range_km=distance/1000,
                radial_speed_m_s=radial_speed,
                doppler_hz=-frequency_ghz*1e9*radial_speed/speed_of_light)


@dataclass(frozen=True)
class WidebandPlan:
    center_ghz: float = 235.0
    bandwidth_hz: float = 10e9
    tones: int = 1024
    cp_s: float = 10e-9
    frame_symbols: int = 10000
    pilot_symbols: int = 30

    def __post_init__(self):
        if not np.isfinite([self.center_ghz, self.bandwidth_hz, self.cp_s]).all():
            raise ValueError('Finite waveform parameters required')
        if self.bandwidth_hz <= 0 or self.cp_s < 0:
            raise ValueError('Positive bandwidth and nonnegative CP required')
        for value in (self.tones, self.frame_symbols, self.pilot_symbols):
            if isinstance(value, bool) or int(value) != value or value < 1:
                raise ValueError('Positive integer resource counts required')
        if self.tones < 2 or self.pilot_symbols >= self.frame_symbols:
            raise ValueError('At least two tones and nonempty payload required')
        if self.center_ghz-self.bandwidth_hz/2e9 < 60 or self.center_ghz+self.bandwidth_hz/2e9 > 400:
            raise ValueError('Occupied band must be inside 60 to 400 GHz')

    @property
    def spacing_hz(self):
        return self.bandwidth_hz / self.tones

    @property
    def symbol_s(self):
        return 1/self.spacing_hz + self.cp_s

    @property
    def frequencies_ghz(self):
        return self.center_ghz + (np.arange(self.tones)-(self.tones-1)/2)*self.spacing_hz/1e9

    def counts(self, total_s):
        if not np.isfinite(total_s) or total_s <= 0:
            raise ValueError('Positive reference plus sample duration required')
        frames = int(np.floor(total_s / 2 / (self.frame_symbols*self.symbol_s)))
        if frames < 1:
            raise ValueError('Insufficient time for one frame in each acquisition')
        return dict(frames_per_acquisition=frames,
                    pilots_per_tone_per_acquisition=frames*self.pilot_symbols,
                    symbols_per_acquisition=frames*self.frame_symbols,
                    charged_total_s=2*frames*self.frame_symbols*self.symbol_s,
                    rounding_s=total_s-2*frames*self.frame_symbols*self.symbol_s)


def differential_covariance(frequency_ghz, snr, pilots, residual_db=0.001,
                            correlation_ghz=10.0, enhancement_db=None):
    """Delta method for log magnitude of coherent pilot means.

    Phase, timing and geometric loss must already have been corrected.
    Reference and sample thermal errors are independent. Residual calibration
    is already differential and drawn once for the whole paired acquisition.
    Signal dependent sample noise is retained when enhancement_db is supplied.
    """
    f = np.asarray(frequency_ghz, float)
    s = np.asarray(snr, float)
    if f.ndim != 1 or f.shape != s.shape or not len(f) or not np.isfinite(f).all() or not np.isfinite(s).all() or np.any(s <= 0):
        raise ValueError('Finite frequencies and positive matching SNR required')
    if not np.isfinite([pilots, residual_db, correlation_ghz]).all() or pilots < 1 or int(pilots) != pilots or residual_db < 0 or correlation_ghz <= 0:
        raise ValueError('Invalid averaging or residual parameters')
    a = np.zeros_like(f) if enhancement_db is None else np.broadcast_to(enhancement_db, f.shape)
    if not np.isfinite(a).all() or np.any(a < 0):
        raise ValueError('Nonnegative enhancement attenuation required')
    sample_snr = s * 10**(-a/10)
    # Var[-20 log10 |h_hat|] = (20/ln 10)^2 /(2 N rho).
    thermal = (20/np.log(10))**2/(2*pilots)*(1/s + 1/sample_snr)
    corr = np.exp(-abs(f[:, None]-f[None, :])/correlation_ghz)
    return np.diag(thermal) + residual_db**2*corr


def single_compound_fit(signature, frequency_ghz, covariance, nuisance=None):
    """Fit a signed concentration after eliminating offset and gain slope."""
    f = np.asarray(frequency_ghz, float)
    d = np.asarray(signature, float).reshape(-1, 1)
    n = np.column_stack([np.ones(len(f)), (f-f.mean())/np.ptp(f)]) if nuisance is None else nuisance
    return efficient_linear_estimator(d, n, covariance)


def detection_summary(estimator, concentration, false_alarm=0.01, positive_covariance=None):
    """Single prespecified one sided test; no multiple target search credit."""
    if not np.isfinite(concentration) or concentration < 0 or not 0 < false_alarm < 0.5:
        raise ValueError('Nonnegative concentration and valid false alarm probability required')
    sd0 = float(np.sqrt(estimator.covariance[0, 0]))
    sd1 = sd0 if positive_covariance is None else float(np.sqrt((estimator.operator @ positive_covariance @ estimator.operator.T)[0, 0]))
    threshold = norm.isf(false_alarm)*sd0
    return dict(sd_ug_m3=sd0, threshold_ug_m3=threshold,
                predicted_detection_pct=float(100*norm.sf((threshold-concentration)/sd1)),
                local_95pct_limit_ug_m3=float((norm.isf(false_alarm)+norm.ppf(.95))*sd0))
