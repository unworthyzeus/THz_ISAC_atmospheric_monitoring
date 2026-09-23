"""Mass-normalized particle distributions using full spherical Mie scattering.

No optical constants or size distributions are fitted to retrieval labels.
Material inputs must be supplied; default atmospheric PM composition is not
known. Growth factors are supplied independently and mass is dry particle mass.
"""
from dataclasses import dataclass
import numpy as np
from scipy.constants import speed_of_light
from scipy.optimize import brentq
import miepython


@dataclass(frozen=True)
class SizeDistribution:
    diameter_um: np.ndarray
    number_weights: np.ndarray
    density_kg_m3: float

    def __post_init__(self):
        d=np.asarray(self.diameter_um,dtype=float);w=np.asarray(self.number_weights,dtype=float)
        if d.ndim!=1 or len(d)<1 or w.shape!=d.shape or not np.isfinite(d).all() or not np.isfinite(w).all() or np.any(d<=0) or np.any(w<0) or w.sum()<=0:
            raise ValueError('Positive diameters and nonnegative nonempty number weights required')
        if not np.isfinite(self.density_kg_m3) or self.density_kg_m3<=0:
            raise ValueError('Positive particle density required')
        object.__setattr__(self,'diameter_um',d.copy())
        object.__setattr__(self,'number_weights',w/w.sum())


def truncated_lognormal(median_diameter_um, geometric_sd, minimum_um, maximum_um,
                        density_kg_m3, order=96):
    """Integrate the number distribution in log diameter over declared bounds."""
    if not np.isfinite([median_diameter_um,geometric_sd,minimum_um,maximum_um]).all() or not 0<minimum_um<maximum_um or median_diameter_um<=0 or geometric_sd<=1 or int(order)!=order or order<2:
        raise ValueError('Invalid lognormal distribution or quadrature order')
    x,w=np.polynomial.legendre.leggauss(int(order)); lo,hi=np.log([minimum_um,maximum_um])
    logd=(lo+hi)/2+(hi-lo)/2*x
    density=np.exp(-.5*((logd-np.log(median_diameter_um))/np.log(geometric_sd))**2)
    return SizeDistribution(np.exp(logd),w*density,density_kg_m3)


def physical_diameter_from_aerodynamic(aerodynamic_um, density_kg_m3,
                                      dynamic_shape_factor=1., mean_free_path_um=.066):
    """Stokes/Cunningham conversion for explicitly supplied gas mean free path.

    The default mean free path is a reference-air value, not a measured profile.
    Shape enters aerodynamic classification; the electromagnetic solver still
    assumes spheres. Wet growth must not reclassify the dry PM size cut.
    """
    da=np.asarray(aerodynamic_um,dtype=float)
    if not np.isfinite(da).all() or np.any(da<=0) or not np.isfinite([density_kg_m3,dynamic_shape_factor,mean_free_path_um]).all() or min(density_kg_m3,dynamic_shape_factor,mean_free_path_um)<=0:
        raise ValueError('Positive aerodynamic parameters required')
    def slip(d):
        kn=2*mean_free_path_um/d
        return 1+kn*(1.257+.4*np.exp(-1.1/kn))
    def solve(a):
        goal=a*a*slip(a)
        return brentq(lambda d:d*d*slip(d)*density_kg_m3/(1000*dynamic_shape_factor)-goal,a*1e-4,a*1e4)
    return np.array([solve(a) for a in da.ravel()]).reshape(da.shape)


def mass_extinction(frequency_ghz, distribution, refractive_index, *, growth_factor=1., water_refractive_index=None):
    """Return extinction/scattering/absorption in m2 per kg of dry mass.

    Complex indices use n + i*k for passive materials. The underlying Mie
    library uses the conjugate convention. Optional wet particles use a
    homogeneous Looyenga effective permittivity; this mixing assumption and
    growth input require separate material validation.
    """
    f=np.asarray(frequency_ghz,dtype=float)
    m=np.broadcast_to(np.asarray(refractive_index,dtype=complex),f.shape).copy()
    if f.ndim!=1 or not len(f) or not np.isfinite(f).all() or np.any((f<60)|(f>400)) or not np.isfinite(m).all() or np.any(m.real<=0) or np.any(m.imag<0):
        raise ValueError('60-400 GHz and passive material optical constants required')
    if not np.isfinite(growth_factor) or growth_factor<1:
        raise ValueError('Growth factor must be at least one')
    if growth_factor>1:
        if water_refractive_index is None:
            raise ValueError('Wet growth requires frequency-dependent water optical constants')
        mw=np.broadcast_to(np.asarray(water_refractive_index,dtype=complex),f.shape)
        if not np.isfinite(mw).all() or np.any(mw.real<=0) or np.any(mw.imag<0):
            raise ValueError('Invalid water optical constants')
        dry_fraction=growth_factor**-3
        m=np.sqrt((dry_fraction*(m*m)**(1/3)+(1-dry_fraction)*(mw*mw)**(1/3))**3)
    d=distribution.diameter_um*1e-6
    dry_mass=np.pi/6*distribution.density_kg_m3*d**3
    area=np.pi/4*(d*growth_factor)**2
    norm=distribution.number_weights@dry_mass
    qe=[];qs=[]
    for frequency,index in zip(f,m):
        ext,sca,_,_=miepython.efficiencies(np.conjugate(index),d*growth_factor,speed_of_light/(frequency*1e9))
        qe.append(distribution.number_weights@(area*ext)/norm)
        qs.append(distribution.number_weights@(area*sca)/norm)
    ext=np.array(qe);sca=np.array(qs)
    if np.any(sca>ext+1e-10*np.maximum(1,ext)):
        raise FloatingPointError('Passive Mie solution has scattering above extinction')
    return dict(extinction=ext,scattering=sca,absorption=ext-sca,
                maximum_size_parameter=float(np.pi*d.max()*growth_factor*f.max()*1e9/speed_of_light))
