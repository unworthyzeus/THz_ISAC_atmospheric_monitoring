"""Complete the proposal's line-shape/slant-integration simulation task."""
from pathlib import Path
from dataclasses import asdict
import contextlib
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from thz_isac.slant_path import ReferenceAtmosphere,satellite_slant_quadrature
from thz_isac.stratified_absorption import local_absorption
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule,GHZ_PER_WAVENUMBER


def main():
    out=ROOT/'results/task_1_3'
    weather=json.loads((ROOT/'results/review/protocol.json').read_text())['surface_conditions']
    atmosphere=ReferenceAtmosphere(weather['temperature_k'],weather['pressure_pa'],weather['dew_point_c'])
    line_file=ROOT/'data/processed/voc_hitran_20260922_0_3000/lines_0_3000GHz.csv'
    acquisition=json.loads((ROOT/'results/voc_pm_capacity/acquisition_manifest_3000ghz.json').read_text())
    assert digest(line_file)==acquisition['processed_sha256']
    lines=pd.read_csv(line_file); f=np.linspace(60,400,256)
    protocol=dict(task='Proposal 1.3: line shape and elevation-dependent molecular path absorption',
        atmosphere=asdict(atmosphere),frequency_bounds_ghz=[60,400],frequency_count=len(f),
        top_altitude_m=20000,satellite_altitude_m=550000,earth_radius_m=6371000,
        geometry='Spherical refractive boundary-value ray connecting ground and satellite',
        layer_count=40,quadrature_order=2,convergence_orders=[1,2,4],
        self_broadening='Local H2O and O2 fractions; trace-gas derivative at zero abundance',
        missing_parameters='n_self falls back to n_air; delta_self=0 for standard HITRAN records',
        refractivity='ITU P.453 radio formula, nondispersive, spherical symmetry; vacuum above 20 km',
        profiles=['voigt','lorentz'],background_comparator='ITU P.676-12; not version 13',
        scope='Complete numerical task under declared stratification; independent field validation absent')
    run=Run(out,protocol,__file__)
    ray=satellite_slant_quadrature(atmosphere,45,layers=40,order=2)
    print('Building full local Voigt coefficients at 80 integration nodes.',flush=True)
    voigt=local_absorption(lines,f,ray.altitude_m,atmosphere)
    current=voigt.integrate(ray)
    np.savez_compressed(out/'refracted45_inputs.npz',**current)
    state=atmosphere.state(ray.altitude_m)
    pd.DataFrame(dict(altitude_m=ray.altitude_m,temperature_k=state[0],pressure_pa=state[1],
                     water_number_density_cm3=state[2],refractive_index=state[3],
                     radial_weight_m=ray.radial_weights_m,path_weight_m=ray.path_weights_m)).to_csv(out/'reference_path.csv',index=False)
    # Every geometry uses the same local coefficients; only the physical path changes.
    rows=[]; curves={}
    for elevation in (5,15,30,45,60,90):
        for geometry in ('plane_parallel','spherical','refracted'):
            path=satellite_slant_quadrature(atmosphere,elevation,layers=40,order=2,geometry=geometry)
            values=voigt.integrate(path)
            for j,name in enumerate(voigt.gas_names):
                rows.append(dict(elevation_deg=elevation,geometry=geometry,target=name,
                   apparent_elevation_deg=path.apparent_elevation_deg,atmospheric_path_m=path.atmospheric_path_m,
                   total_path_m=path.total_path_m,peak_db_per_ug_m3=float(values['gas'][:,j].max()),
                   rms_db_per_ug_m3=float(np.sqrt(np.mean(values['gas'][:,j]**2)))))
            curves[(elevation,geometry)]=values
    pd.DataFrame(rows).to_csv(out/'elevation_geometry.csv',index=False)
    print('Testing quadrature convergence on the entire 256-frequency grid.',flush=True)
    convergence=[]
    for order in (1,4):
        path=satellite_slant_quadrature(atmosphere,45,layers=40,order=order)
        local=local_absorption(lines,f,path.altitude_m,atmosphere)
        values=local.integrate(path)
        for field in ('gas','pm','hitran_background_db','background_db'):
            difference=np.abs(values[field]-current[field])
            convergence.append(dict(order=order,field=field,relative_rms_difference=float(np.linalg.norm(difference)/np.linalg.norm(values[field])),
                peak_normalized_difference=float(difference.max()/np.max(np.abs(values[field])))))
    pd.DataFrame(convergence).to_csv(out/'quadrature_convergence.csv',index=False)
    assert max(r['relative_rms_difference'] for r in convergence if r['order']==4)<.001
    print('Comparing Lorentz and Voigt through the identical refracted path.',flush=True)
    lorentz=local_absorption(lines,f,ray.altitude_m,atmosphere,line_shape='lorentz').integrate(ray)
    shape=[]
    for j,name in enumerate(voigt.gas_names):
        shape.append(dict(molecule=name,lorentz_vs_voigt_relative_rms=float(np.linalg.norm(lorentz['gas'][:,j]-current['gas'][:,j])/np.linalg.norm(current['gas'][:,j]))))
    pd.DataFrame(shape).to_csv(out/'line_shape_comparison.csv',index=False)
    print('Checking multiple pressure/temperature/self-broadening states against HAPI.',flush=True)
    import hapi
    validation=[]
    with (out/'hapi_reference.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        hapi.db_begin(str(ROOT/'data/raw/voc_hitran_20260922_0_3000'))
        for altitude in (0,6000,18000):
            t,p,water,_=atmosphere.state(np.array([altitude])); total=p/(1.380649e-23*t)/1e6
            for name,mid in [('H2CO',20),('CH3OH',39),('CH3CN',41),('CO',5),('O3',3),('SO2',9),('NO2',10),('H2O',1),('O2',7)]:
                q=float(water[0]/total[0]) if name=='H2O' else float(.20946*(1-water[0]/total[0])) if name=='O2' else 0.
                for profile in ('voigt','lorentz'):
                    local=molecular_cross_section_cm2_per_molecule(lines,f,name,temperature_k=float(t[0]),
                        pressure_pa=float(p[0]),self_mole_fraction=q,line_shape=profile)
                    routine=hapi.absorptionCoefficient_Voigt if profile=='voigt' else hapi.absorptionCoefficient_Lorentz
                    _,external=routine(Components=((mid,1),),SourceTables=name+'_main_0_3000GHz',
                         Environment={'T':float(t[0]),'p':float(p[0]/101325)},WavenumberGrid=f/GHZ_PER_WAVENUMBER,
                         WavenumberWing=101.,IntensityThreshold=0.,HITRAN_units=True,Diluent={'air':1-q,'self':q})
                    error=float(np.max(np.abs(local-external))/external.max())
                    validation.append(dict(altitude_m=altitude,molecule=name,profile=profile,self_fraction=q,
                                           peak_normalized_error=error,passed=error<1e-5))
    pd.DataFrame(validation).to_csv(out/'hapi_multistate_validation.csv',index=False)
    assert all(r['passed'] for r in validation), 'HAPI multistate comparison failed.'
    pd.DataFrame(dict(frequency_ghz=f,itu_refracted_db=current['background_db'],
                    hitran_refracted_db=current['hitran_background_db'],
                    hitran_lorentz_db=lorentz['hitran_background_db'])).to_csv(out/'background_models.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for j,label in enumerate(('Formaldehyde','Methanol','Acetonitrile')):
        axes[0].semilogy(f,current['gas'][:,j],label=label)
    axes[0].set(xlabel='Frequency (GHz)',ylabel='Slant loss per ug/m³ (dB)',title='VOC absorption: full refracted path')
    axes[0].legend(fontsize=8)
    frame=pd.DataFrame(rows)
    for geometry in ('plane_parallel','spherical','refracted'):
        subset=frame[(frame.geometry==geometry)&(frame.target=='H2CO')]
        axes[1].plot(subset.elevation_deg,subset.atmospheric_path_m/1000,'o-',label=geometry.replace('_',' '))
    axes[1].set(xlabel='Geometric elevation (degrees)',ylabel='Path through 0–20 km (km)',title='Elevation-dependent atmospheric path')
    axes[1].legend(fontsize=8)
    axes[2].semilogy(f,current['hitran_background_db'],label='HITRAN Voigt')
    axes[2].semilogy(f,current['background_db'],label='ITU P.676-12')
    axes[2].set(xlabel='Frequency (GHz)',ylabel='Background attenuation (dB)',title='Background discrepancy retained')
    axes[2].legend(fontsize=8)
    for ax in axes: ax.grid(alpha=.2)
    fig.savefig(out/'slant_spectra_geometry.png',dpi=180); plt.close(fig)
    summary=dict(status='numerical_task_implemented_and_verified',frequency_range_ghz=[60,400],
        apparent_elevation_for_geometric_45=ray.apparent_elevation_deg,
        atmospheric_path_km=ray.atmospheric_path_m/1000,
        max_hapi_peak_normalized_error=max(r['peak_normalized_error'] for r in validation),
        max_fine_quadrature_relative_difference=max(r['relative_rms_difference'] for r in convergence if r['order']==4),
        unresolved='HITRAN far-wing/continuum background differs from ITU; measured profiles, dispersion and field validation absent.')
    write_json(out/'summary.json',summary)
    run.finish(extra=dict(summary=summary,input_hashes={str(line_file.relative_to(ROOT)):digest(line_file)},
       code_hashes={str(path.relative_to(ROOT)):digest(path) for path in [ROOT/'src/thz_isac/slant_path.py',
                    ROOT/'src/thz_isac/stratified_absorption.py',ROOT/'src/thz_isac/physical_spectroscopy.py']}))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
