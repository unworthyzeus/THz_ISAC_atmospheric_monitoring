"""P.676-13 Annex 1 equations (1)-(9), with decomposed continuum terms.

Coefficient tables are extracted from the archived ITU primary source.
This background REPLACES H2O/O2 HITRAN absorption; it is never added to it.
Trace-species HITRAN spectra may be added separately.
"""
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.constants import Boltzmann, Planck


@lru_cache(maxsize=1)
def coefficients():
    root=Path(__file__).parent/'data'
    return tuple(np.loadtxt(root/f'itu676_13_{s}.csv',delimiter=',',skiprows=1)
                 for s in ('oxygen','water'))


def specific_attenuation(frequency_ghz, temperature_k, total_pressure_pa, water_pressure_pa):
    """Return separated absorption in dB/km on broadcast state x frequency axes."""
    f=np.asarray(frequency_ghz,dtype=float)
    t,p,e=np.broadcast_arrays(temperature_k,total_pressure_pa,water_pressure_pa)
    if f.ndim!=1 or not len(f) or not np.isfinite(f).all() or np.any((f<1)|(f>1000)):
        raise ValueError('Frequency vector must lie in 1-1000 GHz')
    if not all(np.isfinite(a).all() for a in (t,p,e)) or np.any(t<=0) or np.any(p<=0) or np.any((e<0)|(e>=p)):
        raise ValueError('Invalid atmospheric state')
    theta=300/t[...,None,None]; dry=(p-e)[...,None,None]/100; wet=e[...,None,None]/100
    ff=f[None,:]; oxygen,water=coefficients()
    fo,a1,a2,a3,a4,a5,a6=(oxygen[:,i,None] for i in range(7))
    width=a3*1e-4*(dry*theta**(.8-a4)+1.1*wet*theta)
    width=np.sqrt(width**2+2.25e-6)
    mixing=(a5+a6*theta)*1e-4*(dry+wet)*theta**.8
    shape=ff/fo*((width-mixing*(fo-ff))/((fo-ff)**2+width**2)+
                 (width-mixing*(fo+ff))/((fo+ff)**2+width**2))
    strength=a1*1e-7*dry*theta**3*np.exp(a2*(1-theta))
    oxygen_lines=.1820*f*np.sum(strength*shape,axis=-2)
    d=5.6e-4*(dry+wet)*theta**.8
    continuum=ff*dry*theta**2*(6.14e-5/(d*(1+(ff/d)**2))+
                      1.4e-12*dry*theta**1.5/(1+1.9e-5*ff**1.5))
    dry_continuum=.1820*f*continuum[...,0,:]
    fw,b1,b2,b3,b4,b5,b6=(water[:,i,None] for i in range(7))
    width=b3*1e-4*(dry*theta**b4+b5*wet*theta**b6)
    width=.535*width+np.sqrt(.217*width**2+2.1316e-12*fw**2/theta)
    shape=ff/fw*(width/((fw-ff)**2+width**2)+width/((fw+ff)**2+width**2))
    strength=b1*.1*wet*theta**3.5*np.exp(b2*(1-theta))
    individual=.1820*f*strength*shape
    water_lines=np.sum(individual[...,:-1,:],axis=-2)
    wet_continuum=individual[...,-1,:]
    return dict(oxygen_lines=oxygen_lines,dry_continuum=dry_continuum,
                water_lines=water_lines,wet_continuum=wet_continuum,
                total=oxygen_lines+dry_continuum+water_lines+wet_continuum)


def downwelling_brightness_k(frequency_ghz, temperature_k, layer_attenuation_db, space_temperature_k=2.725):
    """Layer LTE radiative transfer in Planck-equivalent antenna temperature.

    Layers are ordered from ground upward. Gas emission and absorption are
    linked by Kirchhoff's law; receiver noise must be added separately.
    """
    f=np.asarray(frequency_ghz,dtype=float)
    t=np.asarray(temperature_k,dtype=float)
    a=np.asarray(layer_attenuation_db,dtype=float)
    if t.ndim!=1 or a.shape!=(len(t),len(f)) or not all(np.isfinite(x).all() for x in (f,t,a)) or np.any(a<0) or np.any(t<=0) or np.any(f<=0) or space_temperature_k<=0:
        raise ValueError('Invalid radiative-transfer arrays')
    q=Planck*f*1e9/Boltzmann
    tau=a*np.log(10)/10
    lower=np.vstack((np.zeros(len(f)),np.cumsum(tau,axis=0)[:-1]))
    source=q/np.expm1(q/t[:,None])
    return np.sum(source*(-np.expm1(-tau))*np.exp(-lower),axis=0)+q/np.expm1(q/space_temperature_k)*np.exp(-tau.sum(axis=0))
