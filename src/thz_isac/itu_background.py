"""Independent ITU-R P.676-12 background sensitivity for the same layers.

Version 12 is explicit: ITU-Rpy 0.4.0 does not implement the current version
13. This is an independent propagation-model comparison, not certification.
"""
import numpy as np
from .physical_spectroscopy import water_vapor_pressure_pa_from_dew_point


def itu676_12_layered_background(frequency_ghz, atmosphere, *, surface_temperature_k,
                               surface_dew_point_c, water_scale_height_m=2000., elevation_deg=45.):
    from itur.models import itu676
    f = np.asarray(frequency_ghz, dtype=float)
    if f.ndim != 1 or not np.isfinite(f).all() or np.any((f<1)|(f>1000)):
        raise ValueError('ITU line-by-line frequencies must lie in [1, 1000] GHz.')
    if not np.isfinite(elevation_deg) or not 0 < elevation_deg <= 90:
        raise ValueError('Elevation must lie in (0, 90] degrees.')
    if not np.isfinite(water_scale_height_m) or water_scale_height_m<=0:
        raise ValueError('Water scale height must be positive.')
    if not np.isfinite(surface_temperature_k) or surface_temperature_k<=0:
        raise ValueError('Surface temperature must be positive.')
    e0 = water_vapor_pressure_pa_from_dew_point(surface_dew_point_c)
    rho0 = e0*18.01528/(8.314462618*surface_temperature_k)  # g/m3
    rho = rho0*np.exp(-atmosphere.altitude_m/water_scale_height_m)
    # Annex 1 uses dry-air partial pressure; e = rho*T/216.7 in hPa.
    e_hpa = rho*atmosphere.temperature_k/216.7
    dry_pressure_hpa = atmosphere.pressure_pa/100-e_hpa
    if np.any(dry_pressure_hpa<=0):
        raise ValueError('Water profile implies nonpositive dry-air pressure.')
    old_version = itu676.get_version()
    try:
        itu676.change_version(12)
        layers = np.array([itu676.gamma_exact(f,float(p),float(r),float(t)).value
                          for p,r,t in zip(dry_pressure_hpa,rho,atmosphere.temperature_k,strict=True)])
    finally:
        itu676.change_version(old_version)
    return np.sum(layers*(atmosphere.layer_thickness_m/1000)[:,None],axis=0)/np.sin(np.deg2rad(elevation_deg))
