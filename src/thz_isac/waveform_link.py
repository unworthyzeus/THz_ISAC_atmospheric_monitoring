"""Explicit OFDM frequency blocks, resource cost and atmospheric receiver noise.

Band membership is engineering metadata, not a spectrum licence. The E-band
example lies inside the ITU-listed 71-76 GHz space-to-Earth allocation; a
particular deployment still requires coordination and equipment validation.
"""
from dataclasses import dataclass
import numpy as np
from scipy.constants import Boltzmann, speed_of_light
from scipy.special import j1
from .link_budget import aperture_gain_linear, leo_slant_range_km
from .communication_capacity import waterfill_power


def maximum_zenith_pass_s(minimum_elevation_deg, satellite_altitude_km=550., earth_radius_km=6371.):
    """Ideal circular, overhead pass above a minimum geometric elevation.

    Earth rotation and non-overhead geometry are omitted; this is a declared
    kinematic reference, not a scheduling guarantee for a real constellation.
    """
    if not np.isfinite([minimum_elevation_deg,satellite_altitude_km,earth_radius_km]).all() or not 0<=minimum_elevation_deg<90 or min(satellite_altitude_km,earth_radius_km)<=0:
        raise ValueError('Invalid pass geometry')
    r=earth_radius_km*1000;rs=r+satellite_altitude_km*1000;el=np.deg2rad(minimum_elevation_deg)
    angle=np.arccos(r/rs*np.cos(el))-el
    omega=np.sqrt(3.986004418e14/rs**3)
    return float(2*angle/omega)


def ofdm_coherent_fraction(residual_frequency_offset_hz,spacing_hz,phase_rms_rad=0.):
    """Large-FFT rectangular OFDM CFO leakage plus independent phase jitter.

    sinc loss is a sensitivity model; a measured phase-noise spectrum and
    oscillator/channel tracking remain necessary for a hardware prediction.
    """
    if not np.isfinite([residual_frequency_offset_hz,spacing_hz,phase_rms_rad]).all() or spacing_hz<=0 or phase_rms_rad<0:
        raise ValueError('Invalid residual synchronization parameters')
    return float(np.sinc(residual_frequency_offset_hz/spacing_hz)**2*np.exp(-phase_rms_rad**2))


def impaired_spectral_efficiency(snr,coherent_fraction):
    """Per-tone log2(1+SINR) with untracked power treated as interference."""
    s=np.asarray(snr,dtype=float)
    if not np.isfinite(s).all() or np.any(s<0) or not np.isfinite(coherent_fraction) or not 0<=coherent_fraction<=1:
        raise ValueError('Invalid impairment inputs')
    return np.log1p(coherent_fraction*s/(1+(1-coherent_fraction)*s))/np.log(2)


@dataclass(frozen=True)
class OFDMPlan:
    centers_ghz: tuple[float,...]
    subcarriers_per_block: int = 256
    spacing_hz: float = 1e6
    cyclic_prefix_fraction: float = 1/16
    frame_symbols: int = 10000
    pilot_symbols: int = 30
    simultaneous_rf_chains: int = 1

    def __post_init__(self):
        n=self.subcarriers_per_block
        if not self.centers_ghz or any(not np.isfinite(c) for c in self.centers_ghz):
            raise ValueError('Finite block centers required')
        if isinstance(n,bool) or int(n)!=n or n<2 or not np.isfinite(self.spacing_hz) or self.spacing_hz<=0:
            raise ValueError('Positive integer subcarrier count and spacing required')
        if not np.isfinite(self.cyclic_prefix_fraction) or not 0<=self.cyclic_prefix_fraction<1:
            raise ValueError('Invalid cyclic prefix')
        if any(isinstance(x,bool) or int(x)!=x for x in (self.frame_symbols,self.pilot_symbols,self.simultaneous_rf_chains)) or not 0<self.pilot_symbols<self.frame_symbols or self.simultaneous_rf_chains<len(self.centers_ghz):
            raise ValueError('Frame/pilot counts or simultaneous RF-chain count invalid')
        half=n*self.spacing_hz/2e9; c=np.sort(self.centers_ghz)
        if c[0]-half<60 or c[-1]+half>400 or np.any(np.diff(c)<2*half):
            raise ValueError('Blocks overlap or extend outside 60-400 GHz')

    @property
    def frequency_ghz(self):
        offset=(np.arange(self.subcarriers_per_block)-(self.subcarriers_per_block-1)/2)*self.spacing_hz/1e9
        return np.concatenate([c+offset for c in self.centers_ghz])

    @property
    def symbol_duration_s(self):
        return (1+self.cyclic_prefix_fraction)/self.spacing_hz

    def coherent_pilots(self, observation_s):
        if not np.isfinite(observation_s) or observation_s<=0:
            raise ValueError('Positive observation duration required')
        return int(observation_s/(self.symbol_duration_s*self.frame_symbols))*self.pilot_symbols

    def net_rate_bps(self,gain_per_watt,power_w,implementation_gap_db=0.):
        g=np.asarray(gain_per_watt);p=np.asarray(power_w)
        if g.shape!=self.frequency_ghz.shape or p.shape!=g.shape or not np.isfinite(g).all() or not np.isfinite(p).all() or np.any(g<0) or np.any(p<0) or not np.isfinite(implementation_gap_db) or implementation_gap_db<0:
            raise ValueError('Invalid OFDM rate inputs')
        return float(self.spacing_hz/(1+self.cyclic_prefix_fraction)*(1-self.pilot_symbols/self.frame_symbols)*
                     np.log2(1+g*p/10**(implementation_gap_db/10)).sum())


def pointing_gain_fraction(frequency_ghz, aperture_diameter_m, error_deg):
    """Uniform circular-aperture Airy power pattern for angular offset."""
    if aperture_diameter_m<=0 or not np.isfinite(error_deg) or error_deg<0:
        raise ValueError('Invalid pointing parameters')
    x=np.pi*aperture_diameter_m*np.asarray(frequency_ghz)*1e9/speed_of_light*np.sin(np.deg2rad(error_deg))
    ratio=np.ones_like(x);np.divide(2*j1(x),x,out=ratio,where=x!=0)
    return ratio**2


def physical_channel_gain(frequency_ghz, attenuation_db, sky_temperature_k, config,
                          elevation_deg, *, pointing_error_deg=0., polarization_error_deg=0.,
                          extra_loss_db=0.):
    """SNR per watt including sky emission and receiver equivalent temperature."""
    f=np.asarray(frequency_ghz,dtype=float);a=np.asarray(attenuation_db,dtype=float);sky=np.asarray(sky_temperature_k,dtype=float)
    if f.shape!=a.shape or sky.shape!=f.shape or not all(np.isfinite(x).all() for x in (f,a,sky)) or np.any(f<=0) or np.any(a<0) or np.any(sky<0) or not np.isfinite([extra_loss_db,polarization_error_deg]).all() or extra_loss_db<0 or not 0<=polarization_error_deg<90:
        raise ValueError('Invalid channel arrays/losses')
    distance=float(leo_slant_range_km(elevation_deg,config.satellite_altitude_km,config.earth_radius_km))*1000
    gt=aperture_gain_linear(f,config.tx_aperture_diameter_m,config.tx_aperture_efficiency)
    gr=aperture_gain_linear(f,config.rx_aperture_diameter_m,config.rx_aperture_efficiency)
    pointing=pointing_gain_fraction(f,config.tx_aperture_diameter_m,pointing_error_deg)*pointing_gain_fraction(f,config.rx_aperture_diameter_m,pointing_error_deg)
    path=(speed_of_light/(4*np.pi*distance*f*1e9))**2
    receiver=config.receiver_noise_temperature_k*(10**(config.receiver_noise_figure_db/10)-1)
    # Antenna sky temperature plus receiver equivalent input noise. No second
    # multiplication by noise factor: that would count receiver noise twice.
    noise=Boltzmann*(sky+receiver)*config.subcarrier_bandwidth_hz
    gain=gt*gr*path*pointing*np.cos(np.deg2rad(polarization_error_deg))**2*10**(-(a+config.implementation_loss_db+extra_loss_db)/10)/noise
    return dict(gain_per_watt=gain,noise_w=noise,sky_temperature_k=sky,
                maximum_orbital_doppler_hz=f*1e9*7600/speed_of_light)


def preserved_capacity(plan,gain,total_power_w,candidate_power_w,*,candidate_pilot_symbols=None):
    baseline=waterfill_power(gain,total_power_w)
    reference=plan.net_rate_bps(gain,baseline)
    candidate=plan.net_rate_bps(gain,candidate_power_w)
    pilots=plan.pilot_symbols if candidate_pilot_symbols is None else candidate_pilot_symbols
    if not isinstance(pilots,int) or not plan.pilot_symbols<=pilots<plan.frame_symbols:
        raise ValueError('Candidate cannot remove required communication pilots')
    candidate*= (1-pilots/plan.frame_symbols)/(1-plan.pilot_symbols/plan.frame_symbols)
    loss=(reference-candidate)/reference if reference>0 else 0.
    return dict(reference_bps=reference,candidate_bps=candidate,relative_loss=loss,
                accepted=bool(np.sum(candidate_power_w)<=total_power_w*(1+1e-10) and loss<=1e-10),
                occupied_bandwidth_hz=len(gain)*plan.spacing_hz,
                simultaneous_rf_chains=plan.simultaneous_rf_chains,
                cyclic_prefix_fraction=plan.cyclic_prefix_fraction)
