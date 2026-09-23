"""Local absorption coefficients integrated on an actual stratified ray.

The trace-gas columns are derivatives at zero added trace concentration.
H2O/O2 background self fractions are computed at every altitude. Voigt and
Lorentz are selectable; continuum/mixing are represented only by the separate
ITU background comparator, never silently added to HITRAN line absorption.
"""
from dataclasses import dataclass
import numpy as np
from scipy.constants import Boltzmann
from .physical_spectroscopy import (molecular_cross_section_cm2_per_molecule,
    concentration_ug_m3_to_number_density_cm3, MOLAR_MASS_G_MOL, DB_PER_NEPER,
    rayleigh_mass_extinction_m2_per_kg, DEFAULT_FINE_PM_MODE, DEFAULT_COARSE_PM_MODE)


@dataclass(frozen=True)
class LocalAbsorption:
    frequency_ghz: np.ndarray
    altitude_m: np.ndarray
    gas_db_per_m_per_ug_m3: np.ndarray
    pm_db_per_m_per_ug_m3: np.ndarray
    hitran_background_db_per_m: np.ndarray
    itu_background_db_per_m: np.ndarray
    gas_names: tuple
    line_shape: str

    def integrate(self, ray):
        if not np.array_equal(self.altitude_m,ray.altitude_m):
            raise ValueError('Spectroscopy and path quadrature nodes must match exactly.')
        ds=ray.path_weights_m
        return dict(frequency_ghz=self.frequency_ghz,
                    gas=np.einsum('z,zfg->fg',ds,self.gas_db_per_m_per_ug_m3),
                    pm=np.einsum('z,zfg->fg',ds,self.pm_db_per_m_per_ug_m3),
                    background_db=ds@self.itu_background_db_per_m,
                    hitran_background_db=ds@self.hitran_background_db_per_m)


def local_absorption(lines,frequency_ghz,altitude_m,atmosphere,*,
                     gas_names=('H2CO','CH3OH','CH3CN','CO','O3','SO2','NO2','CH4'),
                     line_shape='voigt',gas_scale_height_m=1500.,pm_scale_height_m=1000.,
                     include_self_broadening=True):
    from itur.models import itu676
    f=np.asarray(frequency_ghz,dtype=float); z=np.asarray(altitude_m,dtype=float)
    if f.ndim!=1 or not len(f) or np.any((f<60)|(f>400)) or not np.isfinite(f).all():
        raise ValueError('The study evaluates frequencies only in 60–400 GHz.')
    if not np.isfinite([gas_scale_height_m,pm_scale_height_m]).all() or min(gas_scale_height_m,pm_scale_height_m)<=0:
        raise ValueError('Positive finite scale heights required.')
    t,p,water,_=atmosphere.state(z)
    total=p/(Boltzmann*t)/1e6
    oxygen=.20946*(total-water)
    gas=np.empty((len(z),len(f),len(gas_names)))
    bg=np.zeros((len(z),len(f)))
    itu=np.empty_like(bg)
    for j,name in enumerate(gas_names):
        density=concentration_ug_m3_to_number_density_cm3(1.,MOLAR_MASS_G_MOL[name])*np.exp(-z/gas_scale_height_m)
        for i in range(len(z)):
            x=molecular_cross_section_cm2_per_molecule(lines,f,name,
                    temperature_k=t[i],pressure_pa=p[i],line_shape=line_shape)
            gas[i,:,j]=DB_PER_NEPER*x*density[i]*100  # cm^-1 -> m^-1.
    for name,density in [('H2O',water),('O2',oxygen)]:
        for i in range(len(z)):
            x=molecular_cross_section_cm2_per_molecule(lines,f,name,
                    temperature_k=t[i],pressure_pa=p[i],line_shape=line_shape,
                    self_mole_fraction=float(density[i]/total[i]) if include_self_broadening else 0.)
            bg[i]+=DB_PER_NEPER*x*density[i]*100
    old=itu676.get_version()
    try:
        itu676.change_version(12)
        e=water*1e6*Boltzmann*t/100
        rho=water*1e6*18.01528/6.02214076e23  # molecules/m3 -> g/m3.
        # Match P.676's e=rho*T/216.7 convention when converting its input.
        itu_rho=e*216.7/t
        for i in range(len(z)):
            itu[i]=itu676.gamma_exact(f,(p[i]/100-e[i]),itu_rho[i],t[i]).value/1000
    finally:
        itu676.change_version(old)
    pm_columns=[]
    for mode in (DEFAULT_FINE_PM_MODE,DEFAULT_COARSE_PM_MODE):
        extinction=rayleigh_mass_extinction_m2_per_kg(f,particle_diameter_um=mode.diameter_um,
                  particle_density_kg_m3=mode.density_kg_m3,refractive_index=mode.refractive_index)
        pm_columns.append(DB_PER_NEPER*1e-9*np.exp(-z/pm_scale_height_m)[:,None]*extinction)
    return LocalAbsorption(f,z,gas,np.stack(pm_columns,axis=-1),bg,itu,tuple(gas_names),line_shape)
