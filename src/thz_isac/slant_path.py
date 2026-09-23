"""Spherical, refracting satellite rays and altitude quadrature.

Integrates Bouguer's invariant b=n(r) r sin(zenith angle) in a horizontally
stratified atmosphere. A boundary-value solve connects the specified ground
receiver and satellite position, so geometric and apparent elevation differ.
The modeled atmosphere ends at top_altitude_m; the exterior is vacuum.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import brentq
from scipy.constants import Boltzmann
from .physical_spectroscopy import water_vapor_pressure_pa_from_dew_point


@dataclass(frozen=True)
class ReferenceAtmosphere:
    surface_temperature_k: float = 290.35
    surface_pressure_pa: float = 100800.
    surface_dew_point_c: float = 5.4
    water_scale_height_m: float = 2000.

    def state(self, altitude_m):
        """Continuous lapse/isothermal reference through 20 km.

        Returns T [K], total P [Pa], water number density [cm^-3], n [-].
        Refractivity follows the P.453 radio formula; dispersion is excluded.
        """
        z=np.asarray(altitude_m,dtype=float)
        if not np.isfinite(z).all() or np.any((z<0)|(z>20000)):
            raise ValueError('Reference atmosphere supports altitudes from 0 to 20 km.')
        t0=self.surface_temperature_k; p0=self.surface_pressure_pa
        if not np.isfinite([t0,p0,self.water_scale_height_m]).all() or min(t0,p0,self.water_scale_height_m)<=0:
            raise ValueError('Positive finite atmosphere parameters required.')
        lapse=.0065; tropopause=11000.; factor=9.80665*.0289644/8.314462618
        tt=t0-lapse*tropopause
        if tt<=0: raise ValueError('Nonphysical tropopause temperature.')
        t=t0-lapse*np.minimum(z,tropopause)
        p=p0*(t/t0)**(factor/lapse)
        p=np.where(z>tropopause,p0*(tt/t0)**(factor/lapse)*np.exp(-factor*(z-tropopause)/tt),p)
        e0=water_vapor_pressure_pa_from_dew_point(self.surface_dew_point_c)
        water=e0/(Boltzmann*t0)*np.exp(-z/self.water_scale_height_m)/1e6
        e=water*1e6*Boltzmann*t
        if np.any(e>=p): raise ValueError('Water partial pressure exceeds total pressure.')
        refractivity=77.6*((p-e)/100)/t+72*(e/100)/t+3.75e5*(e/100)/t**2
        return t,p,water,1+refractivity*1e-6


@dataclass(frozen=True)
class SlantQuadrature:
    altitude_m: np.ndarray
    radial_weights_m: np.ndarray
    path_weights_m: np.ndarray
    apparent_elevation_deg: float
    geometric_elevation_deg: float
    central_angle_rad: float
    impact_parameter_m: float
    atmospheric_path_m: float
    total_path_m: float
    geometry: str


def satellite_slant_quadrature(atmosphere, elevation_deg, *, top_altitude_m=20000.,
                              satellite_altitude_m=550000., earth_radius_m=6371000.,
                              layers=40, order=4, geometry='refracted', layer_edges_m=None):
    """Gauss-Legendre integration nodes for a ground-to-satellite ray.

    Geometry can be refracted, spherical (straight), or plane_parallel.
    A nonescaping/turning refracted ray raises rather than using a secant.
    """
    if not np.isfinite(elevation_deg) or not 0<elevation_deg<=90:
        raise ValueError('Geometric elevation must lie in (0, 90] degrees.')
    if not np.isfinite([top_altitude_m,satellite_altitude_m,earth_radius_m]).all() or not 0<top_altitude_m<satellite_altitude_m or earth_radius_m<=0:
        raise ValueError('Invalid radii or atmosphere/satellite altitudes.')
    if not isinstance(layers,int) or not isinstance(order,int) or layers<1 or order<1:
        raise ValueError('Positive integer layer and quadrature counts required.')
    if geometry not in {'refracted','spherical','plane_parallel'}:
        raise ValueError('Unknown path geometry.')
    edges=np.linspace(0,top_altitude_m,layers+1) if layer_edges_m is None else np.asarray(layer_edges_m,dtype=float)
    if edges.ndim!=1 or len(edges)<2 or not np.isfinite(edges).all() or edges[0]!=0 or edges[-1]!=top_altitude_m or np.any(np.diff(edges)<=0):
        raise ValueError('Layer edges must strictly increase from zero to the atmosphere top.')
    interfaces=np.asarray(getattr(atmosphere,'boundaries_m',[11000.]),dtype=float)
    edges=np.unique(np.r_[edges,interfaces[(interfaces>0)&(interfaces<top_altitude_m)]])
    x,w=np.polynomial.legendre.leggauss(order)
    half=np.diff(edges)/2
    z=((edges[:-1]+edges[1:])[:,None]/2+half[:,None]*x).ravel()
    dz=(half[:,None]*np.broadcast_to(w,(len(half),len(w)))).ravel()
    r=earth_radius_m+z; rt=earth_radius_m+top_altitude_m
    rs=earth_radius_m+satellite_altitude_m; el=np.deg2rad(elevation_deg)
    distance=-earth_radius_m*np.sin(el)+np.sqrt(rs**2-earth_radius_m**2*np.cos(el)**2)
    target_phi=np.arctan2(distance*np.cos(el),earth_radius_m+distance*np.sin(el))
    if geometry=='plane_parallel':
        ds=dz/np.sin(el)
        return SlantQuadrature(z,dz,ds,elevation_deg,elevation_deg,target_phi,
                               earth_radius_m*np.cos(el),float(ds.sum()),float(distance),geometry)
    n=atmosphere.state(z)[3] if geometry=='refracted' else np.ones_like(z)
    n0=float(atmosphere.state(np.array([0.]))[3][0]) if geometry=='refracted' else 1.
    nr=n*r
    def angular_distance(b):
        inner=nr*nr-b*b
        if np.any(inner<=0): raise ValueError('Ray turns within the modeled atmosphere.')
        return np.sum(dz*b/(r*np.sqrt(inner)))+np.arccos(b/rs)-np.arccos(b/rt)
    if geometry=='spherical':
        b=earth_radius_m*np.cos(el)
    elif elevation_deg==90:
        b=0.
    else:
        # Check escape over a dense grid, including layer interfaces, before
        # bracketing the boundary-value solution.
        check_z=np.unique(np.concatenate((edges,np.linspace(0,top_altitude_m,2001))))
        check_nr=atmosphere.state(check_z)[3]*(earth_radius_m+check_z)
        upper=min(n0*earth_radius_m,float(check_nr.min()),rt)*(1-1e-12)
        if angular_distance(upper)<target_phi:
            raise ValueError('No escaping ray reaches this satellite under the supplied refractivity.')
        b=brentq(lambda trial:angular_distance(trial)-target_phi,0,upper,xtol=1e-7,rtol=1e-14)
    ds=dz*nr/np.sqrt(nr*nr-b*b)
    vacuum=np.sqrt(rs*rs-b*b)-np.sqrt(rt*rt-b*b)
    apparent=np.rad2deg(np.arccos(np.clip(b/(n0*earth_radius_m),0,1)))
    return SlantQuadrature(z,dz,ds,float(apparent),elevation_deg,float(angular_distance(b)),
                           float(b),float(ds.sum()),float(ds.sum()+vacuum),geometry)
