"""Natural-mixture molar masses for mass concentration and ppm conversion.

Reference: CIAAW Abridged Standard Atomic Weights 2024,
https://ciaaw.org/abridged-atomic-weights.htm . Doppler widths separately use
each isotopologue's HITRAN mass. These two mass conventions must not be mixed.
"""
import numpy as np

NATURAL_MOLAR_MASS_G_MOL = {
    'H2CO': 30.026, 'CH3OH': 32.042, 'CH3CN': 41.053,
    'CH4': 16.043, 'CO': 28.010, 'O3': 47.997,
    'SO2': 64.058, 'NO2': 46.005, 'H2O': 18.015, 'O2': 31.998,
}


def natural_mass_design(design,gas_names,source_molar_masses):
    """Exact unit correction of linear absorption per ug/m3 from stored masses."""
    d=np.asarray(design,dtype=float);m=np.asarray(source_molar_masses,dtype=float)
    if d.ndim!=2 or d.shape[1]!=len(gas_names) or m.shape!=(len(gas_names),) or not np.isfinite(d).all() or not np.isfinite(m).all() or np.any(m<=0):
        raise ValueError('Invalid concentration design or source masses')
    target=np.array([NATURAL_MOLAR_MASS_G_MOL[name] for name in gas_names])
    return d*(m/target)
