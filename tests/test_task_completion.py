"""Independent physical limits and failure cases for the completion study."""
import numpy as np
import pytest
from scipy.constants import Boltzmann,Planck
from scipy.stats import norm
from thz_isac.atmospheric_profiles import StandardAtmosphere,TabulatedAtmosphere,ExtendedMeasuredAtmosphere,parse_igra_soundings
from thz_isac.microwave_absorption import specific_attenuation,downwelling_brightness_k,coefficients
from thz_isac.aerosol_mie import SizeDistribution,mass_extinction,physical_diameter_from_aerodynamic,truncated_lognormal
from thz_isac.waveform_link import OFDMPlan,preserved_capacity,pointing_gain_fraction
from thz_isac.communication_capacity import waterfill_power
from thz_isac.robust_retrieval import decision_limits,ug_m3_to_ppm,identifiability,fit_complex_amplitude
from thz_isac.slant_path import satellite_slant_quadrature


def test_standard_surface_and_upper_reference():
    a=StandardAtmosphere();t,p,w,n=a.state(np.array([0.,86000.,100000.]))
    assert t[0]==288.15 and p[0]==101325
    assert t[1]==186.8673
    assert p[2]==pytest.approx(.0320124364,rel=1e-8)
    e=w*1e6*Boltzmann*t
    assert e[2]/p[2]==pytest.approx(2e-6)
    assert np.all(n>=1)


def test_standard_interfaces_continuous_and_geopotential():
    a=StandardAtmosphere();bounds=a.boundaries_m[1:-1]
    left=a.state(bounds-.01);right=a.state(bounds+.01)
    np.testing.assert_allclose(left[0],right[0],atol=.001,rtol=0)
    np.testing.assert_allclose(left[1],right[1],rtol=3e-4)
    # Geometric 11 km is not the 11 km geopotential tropopause.
    assert a.state(np.array([11000.]))[0][0]>216.65
    with pytest.raises(ValueError):a.state([100001])


def measured():
    return TabulatedAtmosphere(np.array([0.,1000.,20000.]),np.array([290.,280.,217.]),
        np.array([101000.,89000.,5500.]),np.array([1000.,700.,.015]))


def test_profile_interpolation_and_no_silent_extrapolation():
    a=measured();t,p,w,n=a.state([500.])
    assert t[0]==285.
    assert p[0]==pytest.approx(np.sqrt(101000*89000))
    with pytest.raises(ValueError):a.state([20001])
    with pytest.raises(ValueError):TabulatedAtmosphere([0,1,2],[290]*3,[1000,2000,500],[1]*3)


def test_profile_extension_preserves_measurements_and_joins():
    a=measured();ext=ExtendedMeasuredAtmosphere(a)
    for x,y in zip(a.state([0,10000,20000]),ext.state([0,10000,20000])):np.testing.assert_allclose(x,y)
    below=ext.state(np.array([20000-1e-3]));above=ext.state(np.array([20000+1e-3]))
    for x,y in zip(below,above):np.testing.assert_allclose(x,y,rtol=1e-5)
    z=np.linspace(0,100000,1001);t,p,w,n=ext.state(z)
    assert np.all(np.diff(p)<0) and np.isfinite(n).all()


@pytest.mark.parametrize('temperature,pressure,rho',[(288.15,101325,7.5),(250.,60000.,2.),(220.,5000.,.001)])
def test_p676_13_agrees_with_independent_unchanged_annex1(temperature,pressure,rho):
    from itur.models import itu676
    f=np.linspace(60,400,257);e=rho*temperature/216.7*100
    parts=specific_attenuation(f,temperature,pressure,e)
    # Version 13 Annex 1 coefficients/equations agree with version 12. The
    # newer approximate slant methods are not thereby validated or claimed.
    old=itu676.get_version()
    try:
        itu676.change_version(12)
        ref=itu676.gamma_exact(f,(pressure-e)/100,rho,temperature).value
    finally:itu676.change_version(old)
    np.testing.assert_allclose(parts['total'],ref,rtol=2e-12,atol=1e-12)
    np.testing.assert_allclose(parts['total'],sum(v for k,v in parts.items() if k!='total'))
    assert np.all(parts['total']>0)


def test_p676_state_broadcast_and_dry_limit():
    r=specific_attenuation([60,183,325],np.array([250.,290.]),np.array([30000.,100000.]),0.)
    assert r['total'].shape==(2,3)
    np.testing.assert_equal(r['water_lines'],0)
    np.testing.assert_equal(r['wet_continuum'],0)
    assert coefficients()[0].shape==(44,7) and coefficients()[1].shape==(35,7)
    with pytest.raises(ValueError):specific_attenuation([200],290,1000,2000)


def test_radiative_transfer_isothermal_slab_and_vacuum():
    f=np.array([60.,200.,400.]);q=Planck*f*1e9/Boltzmann
    tau=np.array([.1,1.,20.]);a=tau*10/np.log(10)
    actual=downwelling_brightness_k(f,[280.,280.],np.vstack([a*.4,a*.6]))
    expected=q/np.expm1(q/280)*(-np.expm1(-tau))+q/np.expm1(q/2.725)*np.exp(-tau)
    np.testing.assert_allclose(actual,expected,rtol=1e-13)
    np.testing.assert_allclose(downwelling_brightness_k(f,[280.],np.zeros((1,3))),q/np.expm1(q/2.725))


def test_mie_small_sphere_independent_rayleigh_scattering():
    from scipy.constants import speed_of_light
    f=np.array([60.,200.,400.]);d=.1e-6;m=1.5+0j;rho=1500.
    result=mass_extinction(f,SizeDistribution([.1],[1],rho),m)
    x=np.pi*d*f*1e9/speed_of_light
    qsca=8/3*x**4*abs((m*m-1)/(m*m+2))**2
    expected=qsca*np.pi*d*d/4/(rho*np.pi*d**3/6)
    np.testing.assert_allclose(result['scattering'],expected,rtol=1e-6)
    np.testing.assert_allclose(result['absorption'],0,atol=1e-14)


def test_mie_weight_normalization_and_passivity():
    f=np.array([60.,400.]);a=mass_extinction(f,SizeDistribution([.5,4.],[1,2],1500),1.5+.01j)
    b=mass_extinction(f,SizeDistribution([.5,4.],[10,20],1500),1.5+.01j)
    np.testing.assert_allclose(a['extinction'],b['extinction'])
    assert np.all(a['extinction']>=a['scattering'])
    with pytest.raises(ValueError):mass_extinction(f,SizeDistribution([1],[1],1500),1.5-.01j)
    with pytest.raises(ValueError):mass_extinction(f,SizeDistribution([1],[1],1500),1.5+.01j,growth_factor=1.5)


def test_aerodynamic_cut_and_distribution_convergence():
    da=np.array([.03,2.5,10.])
    np.testing.assert_allclose(physical_diameter_from_aerodynamic(da,1000),da,rtol=1e-8)
    assert np.all(physical_diameter_from_aerodynamic(da,2000)<da)
    a=truncated_lognormal(.5,1.7,.02,2.,1500,32);b=truncated_lognormal(.5,1.7,.02,2.,1500,64)
    np.testing.assert_allclose(mass_extinction([100,300],a,1.5+.01j)['extinction'],mass_extinction([100,300],b,1.5+.01j)['extinction'],rtol=1e-7)


def test_ofdm_resources_and_no_free_pilots():
    p=OFDMPlan((73.5,),subcarriers_per_block=64)
    assert p.frequency_ghz[-1]-p.frequency_ghz[0]==pytest.approx(.063)
    assert p.symbol_duration_s==pytest.approx(1.0625e-6)
    gain=np.linspace(100,300,64);power=waterfill_power(gain,.2)
    check=preserved_capacity(p,gain,.2,power)
    assert check['accepted'] and check['relative_loss']==0
    assert not preserved_capacity(p,gain,.2,power,candidate_pilot_symbols=300)['accepted']
    assert p.coherent_pilots(.010625)==30
    np.testing.assert_equal(pointing_gain_fraction([60,400],.5,0),1)
    assert pointing_gain_fraction([60,400],.5,.01)[1]<pointing_gain_fraction([60,400],.5,.01)[0]


@pytest.mark.parametrize('args',[dict(centers_ghz=(60.,)),dict(centers_ghz=(73.,73.1),simultaneous_rf_chains=2),dict(centers_ghz=(73.,74.)),dict(centers_ghz=(73.,),pilot_symbols=10000)])
def test_invalid_waveform_plans(args):
    with pytest.raises(ValueError):OFDMPlan(**args)


def test_rank_loss_is_not_a_successful_estimate():
    f=np.linspace(0,1,30);d=np.column_stack((np.sin(f*20),f,f**4));n=np.column_stack((np.ones(30),f,f**4))
    info=identifiability(d,n,np.eye(30))
    assert not info['identifiable']
    assert np.all(info['retained_information_fraction'][1:]<1e-20)


def test_complex_fit_recovers_exact_nonlinear_response():
    f=np.linspace(0,1,100);d=np.column_stack((np.exp(-((f-.3)/.06)**2),np.exp(-((f-.7)/.05)**2)))*.02
    n=np.ones((100,1));truth=np.array([150.,50.]);y=10**(-(d@truth+.12)/20)+0j
    fit=fit_complex_amplitude(y,d,n,.001,concentration_scale=[100,100],upper_concentration=[1000,1000],initial=[50,100])
    assert fit.success
    np.testing.assert_allclose(fit.concentrations,truth,atol=1e-6)
    assert fit.calibration[0]==pytest.approx(.12,abs=1e-8)


def test_decision_limits_control_bias_and_power():
    sd=3.;b=2.;result=decision_limits(sd,false_positive_rate=.01,power=.95,bias_bound=b,family_size=5)
    assert norm.sf((result['critical_level']-b)/sd)==pytest.approx(.002)
    assert norm.sf((result['critical_level']-(result['detection_limit']-b))/sd)==pytest.approx(.95)
    assert ug_m3_to_ppm(1000,30.,298.15,101325)==pytest.approx(.815513466,rel=1e-6)
    with pytest.raises(ValueError):decision_limits(0)


def test_custom_path_edges_converge_and_preserve_full_atmosphere():
    a=StandardAtmosphere();edges=np.r_[np.arange(0,20001,1000),40000,70000,100000]
    r=satellite_slant_quadrature(a,90,top_altitude_m=100000,layer_edges_m=edges,order=2)
    assert r.atmospheric_path_m==pytest.approx(100000)
    assert r.total_path_m==pytest.approx(550000)
    with pytest.raises(ValueError):satellite_slant_quadrature(a,45,top_altitude_m=100000,layer_edges_m=[0,10000])


def test_pass_duration_and_synchronization_limits():
    from thz_isac.waveform_link import maximum_zenith_pass_s,ofdm_coherent_fraction,impaired_spectral_efficiency
    assert 0<maximum_zenith_pass_s(45)<maximum_zenith_pass_s(5)<1800
    assert ofdm_coherent_fraction(0,1e6)==1
    s=np.array([0.,1.,100.])
    np.testing.assert_allclose(impaired_spectral_efficiency(s,1),np.log2(1+s))
    np.testing.assert_equal(impaired_spectral_efficiency(s,0),0)
    assert ofdm_coherent_fraction(1e5,1e6,.1)<1


def test_mass_and_number_concentration_conventions():
    from thz_isac.concentration_units import natural_mass_design,NATURAL_MOLAR_MASS_G_MOL
    from scipy.constants import Avogadro
    old=np.array([30.010565,32.026215]);names=['H2CO','CH3OH']
    cross=np.array([[1e-20,2e-20],[3e-20,4e-20]])
    design=cross*(Avogadro*1e-12/old)
    corrected=natural_mass_design(design,names,old)
    expected=cross*(Avogadro*1e-12/np.array([NATURAL_MOLAR_MASS_G_MOL[n] for n in names]))
    np.testing.assert_allclose(corrected,expected,rtol=1e-15)


def test_profile_refits_nuisance_and_recovers_interior_minimum():
    from thz_isac.robust_retrieval import profile_complex_concentration
    f=np.linspace(0,1,100)
    d=.02*np.column_stack((np.exp(-((f-.3)/.06)**2),np.exp(-((f-.7)/.05)**2)))
    n=np.ones((100,1));truth=np.array([150.,50.])
    y=10**(-(d@truth+.12)/20)+0j
    profile=profile_complex_concentration(y,d,n,.001,target_index=0,grid=[100.,150.,200.],
        concentration_scale=[100.,100.],upper_concentration=[1000.,1000.])
    assert profile['success'].all()
    assert not profile['minimum_at_grid_boundary']
    assert np.argmin(profile['cost'])==1 and profile['cost'][1]<1e-12
    assert np.all(profile['deviance_from_grid_minimum'][[0,2]]>100)
