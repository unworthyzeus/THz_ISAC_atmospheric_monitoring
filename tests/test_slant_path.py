import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import quad
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from thz_isac.slant_path import ReferenceAtmosphere,satellite_slant_quadrature
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule
from test_physical_spectroscopy import _processed_hitran_fixture


def test_spherical_ray_matches_analytic_shell_chord():
    atmosphere=ReferenceAtmosphere(); radius=6371000.; height=20000.
    for elevation in (1,5,15,45,90):
        ray=satellite_slant_quadrature(atmosphere,elevation,layers=100,order=8,geometry='spherical')
        el=np.deg2rad(elevation)
        length=-radius*np.sin(el)+np.sqrt((radius+height)**2-radius**2*np.cos(el)**2)
        assert ray.atmospheric_path_m==pytest.approx(length,rel=1e-10)
        assert ray.apparent_elevation_deg==pytest.approx(elevation,abs=1e-10)


def test_refracted_endpoint_and_independent_adaptive_path_integral():
    atmosphere=ReferenceAtmosphere()
    for elevation in (5,15,45,90):
        ray=satellite_slant_quadrature(atmosphere,elevation,layers=40,order=4)
        b=ray.impact_parameter_m; radius=6371000.; rs=radius+550000.; rt=radius+20000.
        def path_integrand(z):
            nr=float(atmosphere.state(np.array([z]))[3][0])*(radius+z)
            return nr/np.sqrt(nr*nr-b*b)
        length=quad(path_integrand,0,20000,points=[11000],epsabs=1e-6,epsrel=1e-11)[0]
        assert ray.atmospheric_path_m==pytest.approx(length,rel=1e-9)
        def angle_integrand(z):
            r=radius+z; n=float(atmosphere.state(np.array([z]))[3][0])
            return b/(r*np.sqrt((n*r)**2-b*b))
        angle=quad(angle_integrand,0,20000,points=[11000],epsabs=1e-12)[0]+np.arccos(b/rs)-np.arccos(b/rt)
        el=np.deg2rad(elevation)
        distance=-radius*np.sin(el)+np.sqrt(rs*rs-radius*radius*np.cos(el)**2)
        expected=np.arctan2(distance*np.cos(el),radius+distance*np.sin(el))
        assert angle==pytest.approx(expected,abs=1e-11)
        assert ray.apparent_elevation_deg>=elevation-1e-10


def test_zenith_identity_and_vacuum_refraction_limit():
    atmosphere=ReferenceAtmosphere()
    ray=satellite_slant_quadrature(atmosphere,90)
    np.testing.assert_allclose(ray.path_weights_m,ray.radial_weights_m,rtol=1e-14)
    assert ray.total_path_m==pytest.approx(550000.)
    class Vacuum:
        def state(self,z):
            state=list(atmosphere.state(z)); state[3]=np.ones_like(z); return state
    refracted=satellite_slant_quadrature(Vacuum(),15,order=6)
    straight=satellite_slant_quadrature(Vacuum(),15,geometry='spherical',order=6)
    np.testing.assert_allclose(refracted.path_weights_m,straight.path_weights_m,rtol=1e-10)


def test_line_shapes_and_self_broadening_have_physical_effect():
    table=_processed_hitran_fixture(); f=np.linspace(70,80,1001)
    kwargs=dict(temperature_k=296.,pressure_pa=101325.)
    air=molecular_cross_section_cm2_per_molecule(table,f,'H2O',**kwargs)
    wet=molecular_cross_section_cm2_per_molecule(table,f,'H2O',self_mole_fraction=1.,**kwargs)
    lorentz=molecular_cross_section_cm2_per_molecule(table,f,'H2O',line_shape='lorentz',**kwargs)
    assert wet.max()<air.max()
    np.testing.assert_allclose(lorentz,air,rtol=1e-4)
    low=dict(temperature_k=220.,pressure_pa=.01)
    doppler=molecular_cross_section_cm2_per_molecule(table,np.array([75.]),'H2O',**low)
    narrow=molecular_cross_section_cm2_per_molecule(table,np.array([75.]),'H2O',line_shape='lorentz',**low)
    assert narrow[0]>10*doppler[0]


def test_both_line_shapes_follow_hitran_positive_pressure_shift_convention():
    # HITRAN defines nu_star = nu + delta * pressure. A conspicuous shift
    # catches the sign independently of any third-party reference routine.
    table=_processed_hitran_fixture()
    table.loc[table.molecule=='CO','air_pressure_shift']=.05
    row=table.loc[table.molecule=='CO'].iloc[0]
    center=float(row.wavenumber_cm_1)+.05
    frequency=np.array([center-.05,center,center+.05])*29.9792458
    for profile in ('voigt','lorentz'):
        spectrum=molecular_cross_section_cm2_per_molecule(table,frequency,'CO',
                 temperature_k=296.,pressure_pa=101325.,line_shape=profile)
        assert spectrum.argmax()==1
        if profile=='lorentz':
            assert spectrum[1]==pytest.approx(row.line_intensity/(np.pi*row.gamma_air),rel=1e-12)


@pytest.mark.parametrize('elevation',[-1,0,91,np.nan])
def test_invalid_ray_elevation(elevation):
    with pytest.raises(ValueError): satellite_slant_quadrature(ReferenceAtmosphere(),elevation)
