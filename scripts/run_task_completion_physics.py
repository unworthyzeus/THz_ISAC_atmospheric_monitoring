"""Task 1 physics: primary-source profiles, isotope/wing audit and Mie controls.

Results are a reproducible model-completion study, not field VOC retrieval.
Weather data are actual IGRA soundings. Aerosol material/size sensitivity
controls are explicitly conditional and do not become the main evidence.
"""
from pathlib import Path
import sys,json,hashlib,time
from dataclasses import asdict
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from thz_isac.atmospheric_profiles import StandardAtmosphere,parse_igra_soundings,sounding_atmosphere,ExtendedMeasuredAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.microwave_absorption import specific_attenuation,downwelling_brightness_k
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule,concentration_ug_m3_to_number_density_cm3,MOLAR_MASS_G_MOL,DB_PER_NEPER,rayleigh_mass_extinction_m2_per_kg
from thz_isac.aerosol_mie import truncated_lognormal,mass_extinction,physical_diameter_from_aerodynamic
from thz_isac.waveform_link import OFDMPlan

OUT=ROOT/'results/task_completion'
GASES=('H2CO','CH3OH','CH3CN','CO','O3','SO2','NO2')
EDGES=np.unique(np.r_[np.arange(0,12001,1000),np.arange(16000,40001,4000),np.arange(50000,100001,10000)])


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def integrate(lines,f,atmosphere,ray,gas_scale_m=1500.,label=''):
    t,p,water,_=atmosphere.state(ray.altitude_m)
    e=water*1e6*Boltzmann*t
    parts=specific_attenuation(f,t,p,e)
    layers=parts['total']*ray.path_weights_m[:,None]/1000
    bg=layers.sum(axis=0);sky=downwelling_brightness_k(f,t,layers)
    gas=np.zeros((len(f),len(GASES)))
    # Exact numerical tail bound on assumed exponential profile is recorded.
    # Nodes beyond 60 km carry <exp(-40) of the surface density, but remain
    # included to avoid an unexplained truncation in the trace integral.
    for j,name in enumerate(GASES):
        number=concentration_ug_m3_to_number_density_cm3(1.,MOLAR_MASS_G_MOL[name])
        for i,z in enumerate(ray.altitude_m):
            cross=molecular_cross_section_cm2_per_molecule(lines,f,name,temperature_k=t[i],pressure_pa=p[i])
            gas[:,j]+=DB_PER_NEPER*cross*number*np.exp(-z/gas_scale_m)*100*ray.path_weights_m[i]
        print(label,name,'integrated',len(ray.altitude_m),'nodes',flush=True)
    return dict(frequency_ghz=f,gas=gas,background_db=bg,sky_temperature_k=sky,
                altitude_m=ray.altitude_m,path_weights_m=ray.path_weights_m,
                temperature_k=t,pressure_pa=p,water_number_cm3=water,
                **{k+'_db':ray.path_weights_m@v/1000 for k,v in parts.items() if k!='total'})


def main():
    OUT.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    source=ROOT/'data/processed/task_completion/all_isotopes_0_3000GHz.csv'
    lines=pd.read_csv(source)
    acquisition=json.loads((OUT/'spectroscopy_acquisition.json').read_text())
    if sha(source)!=acquisition['processed_sha256']:raise ValueError('Spectroscopic input hash mismatch')
    standard=StandardAtmosphere()
    eband=OFDMPlan((73.5,))
    f=np.r_[np.linspace(60,400,256),eband.frequency_ghz]
    # Primary-source line inventory and surface-state sensitivity controls.
    rows=[];inventory=[]
    for (name,iso),group in lines.groupby(['molecule','isotopologue_id']):
        inventory.append(dict(molecule=name,isotopologue_id=int(iso),lines=len(group),
           in_band_lines=int(group.frequency_ghz.between(60,400).sum()),
           zero_air_width=int((group.gamma_air==0).sum()),negative_air_width=int((group.gamma_air<0).sum())))
    pd.DataFrame(inventory).to_csv(OUT/'line_inventory.csv',index=False)
    for name in GASES:
        ref=molecular_cross_section_cm2_per_molecule(lines,f,name,temperature_k=288.15,pressure_pa=101325.)
        for selection,table,cutoff in [('main_isotope',lines[lines.isotopologue_id==1],None),
                                     ('all_iso_50GHz_wings',lines,50.),('all_iso_300GHz_wings',lines,300.)]:
            test=molecular_cross_section_cm2_per_molecule(table,f,name,temperature_k=288.15,pressure_pa=101325.,wing_cutoff_ghz=cutoff)
            rows.append(dict(molecule=name,control=selection,relative_rms=float(np.linalg.norm(test-ref)/np.linalg.norm(ref)),
                             maximum_absolute_cm2=float(np.max(np.abs(test-ref)))))
    pd.DataFrame(rows).to_csv(OUT/'isotope_and_wing_sensitivity.csv',index=False)
    # Distribution controls use the earlier declared material properties, now
    # over a size distribution. They are not a measured Beijing aerosol model.
    pm=[];pmrows=[]
    for name,density,median,sd,lo,hi,index in [('fine',1500.,.5,1.7,.03,2.5,1.5+.01j),('coarse',1800.,4.,1.6,2.5,10.,1.53+.01j)]:
        bounds=physical_diameter_from_aerodynamic(np.array([lo,hi]),density)
        dist=truncated_lognormal(median,sd,*bounds,density,order=64)
        result=mass_extinction(f,dist,index)
        fine=mass_extinction(f,truncated_lognormal(median,sd,*bounds,density,order=128),index)
        rayleigh=sum(w*rayleigh_mass_extinction_m2_per_kg(f,particle_diameter_um=d,particle_density_kg_m3=density,refractive_index=index)*d**3 for d,w in zip(dist.diameter_um,dist.number_weights))/(dist.number_weights@dist.diameter_um**3)
        pm.append(result['extinction'])
        pmrows.append(dict(mode=name,density_kg_m3=density,number_median_um=median,geometric_sd=sd,
           aerodynamic_cut_um=[lo,hi],physical_bounds_um=bounds.tolist(),refractive_index=[index.real,index.imag],
           maximum_size_parameter=result['maximum_size_parameter'],
           quadrature_relative_rms=float(np.linalg.norm(fine['extinction']-result['extinction'])/np.linalg.norm(fine['extinction'])),
           rayleigh_relative_rms=float(np.linalg.norm(rayleigh-result['extinction'])/np.linalg.norm(result['extinction']))))
        pd.DataFrame(dict(frequency_ghz=f,mie_extinction=result['extinction'],rayleigh_extinction=rayleigh,
                         mie_absorption=result['absorption'],mie_scattering=result['scattering'])).to_csv(OUT/f'{name}_particle_optics.csv',index=False)
    write('aerosol_controls.json',dict(scope='Uncalibrated material/size controls; dry PM mass and aerodynamic cuts explicit',modes=pmrows))
    # Save actual seasonal soundings before a spectrum/label is inspected.
    raw=ROOT/'data/raw/task_completion/beijing-2026.txt'
    soundings=parse_igra_soundings(raw.read_text())
    profiles=[];weather=[];rejections=[];chosen=[]
    for month in [1,4,7,9]:
        selected=None
        for date,group in soundings[soundings.datetime.str[5:7]==f'{month:02d}'].groupby('datetime'):
            try:
                measured=sounding_atmosphere(group)
                if measured.altitude_m[-1]<20000:raise ValueError('Less than 20 km complete weather coverage')
                selected=(date,group,measured);break
            except ValueError as exc:rejections.append(dict(datetime=date,reason=str(exc)))
        if selected is None:raise RuntimeError(f'No valid sounding in month {month}')
        date,group,measured=selected;chosen.append(date)
        group.to_csv(OUT/f'igra_{month:02d}_measured.csv',index=False)
        model=ExtendedMeasuredAtmosphere(measured)
        ray=satellite_slant_quadrature(model,45,top_altitude_m=100000-measured.ground_altitude_m,layers=60,order=2,
                 earth_radius_m=6371000+measured.ground_altitude_m,satellite_altitude_m=550000-measured.ground_altitude_m)
        t,p,w,n=model.state(ray.altitude_m);gamma=specific_attenuation(f,t,p,w*1e6*Boltzmann*t)['total']
        attenuation=ray.path_weights_m@gamma/1000
        weather.extend(dict(datetime=date,frequency_ghz=float(a),attenuation_db=float(b)) for a,b in zip(f,attenuation))
        profiles.append(dict(datetime=date,measured_levels=len(group),measured_top_m=float(measured.altitude_m[-1]),ground_altitude_m=measured.ground_altitude_m,
                             extended_to_m=100000,apparent_elevation_deg=ray.apparent_elevation_deg))
    pd.DataFrame(weather).to_csv(OUT/'measured_weather_attenuation.csv',index=False)
    write('weather_selection.json',dict(raw_sha256=sha(raw),retained_rows=len(soundings),soundings=int(soundings.datetime.nunique()),
          selection='First complete >=20 km sounding in January/April/July/September 2026, before spectroscopy evaluation',
          selected=profiles,rejected=rejections,limitation='Weather soundings are not VOC/PM labels or paired radio observations'))
    # Multi-layer primary model: full 100 km standard; measured-weather ensemble
    # remains an independent forward/background mismatch test.
    outputs=[];convergence=[]
    for order in [2,4]:
        ray=satellite_slant_quadrature(standard,45,top_altitude_m=100000,order=order,layer_edges_m=EDGES)
        data=integrate(lines,f,standard,ray,label=f'order{order}')
        data['pm']=np.column_stack(pm)*DB_PER_NEPER*1e-9*np.dot(ray.path_weights_m,np.exp(-ray.altitude_m/1000))
        np.savez_compressed(OUT/f'physics_order{order}.npz',**data)
        outputs.append(data)
    for field in ['gas','pm','background_db','sky_temperature_k']:
        error=float(np.linalg.norm(outputs[0][field]-outputs[1][field])/np.linalg.norm(outputs[1][field]))
        convergence.append(dict(quantity=field,relative_rms=error,acceptance_threshold=.001,passed=error<.001))
    pd.DataFrame(convergence).to_csv(OUT/'integration_convergence.csv',index=False)
    # Quantify the formerly omitted upper atmosphere on the same refined grid.
    d=outputs[1];z=d['altitude_m'];t,p,w,_=standard.state(z)
    gamma=specific_attenuation(f,t,p,w*1e6*Boltzmann*t)['total']
    lower=(z<=20000);upper=d['path_weights_m'][~lower]@gamma[~lower]/1000
    pd.DataFrame(dict(frequency_ghz=f,total_100km_db=d['background_db'],above_20km_db=upper)).to_csv(OUT/'upper_atmosphere.csv',index=False)
    write('physics_manifest.json',dict(status='passed' if all(r['passed'] for r in convergence) else 'convergence_failed',
          source_sha256=sha(source),analysis_window_ghz=[60,400],gas_names=GASES,
          gas_profile='Surface mass concentration times exp(-z/1500m); composition profile remains assumed',
          pm_profile='Dry mass concentration times exp(-z/1000m); assumed',
          background='ITU-R P.676-13 Annex 1, no HITRAN H2O/O2 double counting',
          standard_atmosphere='ITU-R P.835-7 Annex 1 to 100 km',
          waveform=asdict(eband),weather_selected=chosen,wall_seconds=time.perf_counter()-start,
          inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,raw]},
          code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),*sorted((ROOT/'src/thz_isac').glob('*.py'))]},
          outputs={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['physics_manifest.json']}))
    if not all(r['passed'] for r in convergence):raise SystemExit('Refine integration before retrieval')
    print('Physics study completed',time.perf_counter()-start,flush=True)


if __name__=='__main__':main()
