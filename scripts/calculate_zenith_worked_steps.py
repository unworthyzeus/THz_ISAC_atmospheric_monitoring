"""Expose each physical and statistical step behind the saved CH3CN example."""
import os
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.constants import Avogadro, Boltzmann, speed_of_light
from scipy.linalg import cholesky, cho_solve
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from thz_isac import physical_spectroscopy as spec
from thz_isac.atmospheric_profiles import StandardAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.zenith_tutorial import differential_covariance
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL

DATA=ROOT/'results/zenith_single_compound'
OUT=ROOT/'results/zenith_worked_steps'
OUT.mkdir(parents=True,exist_ok=True)
tones=pd.read_csv(DATA/'tone_by_tone.csv')
obs=pd.read_csv(DATA/'worked_observation.csv')
saved=json.loads((DATA/'worked_example.json').read_text())
base=json.loads((DATA/'baseline.json').read_text())
mat=np.load(DATA/'matrices.npz')
f=tones.frequency_ghz.to_numpy()
a=tones.gas_db_per_ug_m3.to_numpy()
q=saved['true_concentration_ug_m3']
lines=pd.read_csv(ROOT/'data/raw/payload_bounds/lines.csv')
lines=lines.loc[lines.molecule=='CH3CN'].copy()
atmosphere=StandardAtmosphere()
edges=np.array([0,.5,1,2,3,5,8,12,20,40,70,100])*1000
ray=satellite_slant_quadrature(atmosphere,90.,top_altitude_m=100000,layer_edges_m=edges,order=6)
t,p,_,_=atmosphere.state(ray.altitude_m)
density0=float(spec.concentration_ug_m3_to_number_density_cm3(1.,NATURAL_MOLAR_MASS_G_MOL['CH3CN']))
rows=[]
for z,ds,T,P in zip(ray.altitude_m,ray.path_weights_m,t,p):
    cross=float(spec.molecular_cross_section_cm2_per_molecule(lines,f[:1],'CH3CN',temperature_k=T,pressure_pa=P)[0])
    density=density0*np.exp(-z/1500)
    tau=cross*density*100*ds
    rows.append(dict(z_m=z,weight_m=ds,temperature_k=T,pressure_pa=P,
                     cross_section_cm2=cross,density_per_unit_q_cm3=density,
                     optical_depth_per_unit_q=tau,attenuation_db_per_unit_q=spec.DB_PER_NEPER*tau))
layers=pd.DataFrame(rows)
layers.to_csv(OUT/'quadrature_first_tone.csv',index=False)
coarse=np.array([0,500,1000,2000,3000,5000,100001])
groups=[]
for lo,hi in zip(coarse[:-1],coarse[1:]):
    group=layers.loc[(layers.z_m>=lo)&(layers.z_m<hi)]
    groups.append(dict(lower_m=lo,upper_m=min(hi,100000),nodes=len(group),
                       optical_depth_per_unit_q=float(group.optical_depth_per_unit_q.sum()),
                       attenuation_db_per_unit_q=float(group.attenuation_db_per_unit_q.sum())))
pd.DataFrame(groups).to_csv(OUT/'altitude_contributions.csv',index=False)
assert np.isclose(layers.attenuation_db_per_unit_q.sum(),a[0],rtol=1e-10,atol=0)

# Resolve individual line contributions at the first quadrature node.
T=float(t[0]); P=float(p[0]); nu=lines.wavenumber_cm_1.to_numpy()
Qref=float(spec.partitionSum(41,1,296.,version=2025))
QT=float(spec.partitionSum(41,1,T,version=2025))
c2=spec.SECOND_RADIATION_CONSTANT_CM_K
strength=lines.line_intensity.to_numpy()*(Qref/QT)*np.exp(-c2*lines.lower_state_energy.to_numpy()*(1/T-1/296.))*(-np.expm1(-c2*nu/T))/(-np.expm1(-c2*nu/296.))
centers=nu+lines.air_pressure_shift.to_numpy()*P/101325.
gamma=lines.gamma_air.to_numpy()*(P/101325.)*(296./T)**lines.temperature_exponent.to_numpy()
mass=spec.molecularMass(41,1)*1e-3/Avogadro
sigmaD=abs(centers)*np.sqrt(Boltzmann*T/(mass*speed_of_light**2))
profile=spec.voigt_profile_wavenumber(f[0]/spec.GHZ_PER_WAVENUMBER,centers,sigmaD,gamma)
contribution=strength*profile
assert np.isclose(contribution.sum(),layers.cross_section_cm2.iloc[0],rtol=1e-12,atol=0)
line_table=lines.assign(strength_at_node=strength,gamma_at_node_cm_1=gamma,
                        doppler_sigma_cm_1=sigmaD,profile_at_tone_cm=profile,
                        cross_section_contribution_cm2=contribution)
line_table.sort_values('cross_section_contribution_cm2',ascending=False).head(12).to_csv(OUT/'largest_line_contributions.csv',index=False)
selected=line_table.loc[line_table.cross_section_contribution_cm2.idxmax()].to_dict()

# Replay the same complex receiver draw, retaining every intermediate value.
snr=10**(tones.snr_db.to_numpy()/10)
M=base['result']['pilots_per_tone_per_acquisition']
rng=np.random.default_rng(saved['seed'])
z=(rng.normal(size=(2,len(f)))+1j*rng.normal(size=(2,len(f))))/np.sqrt(2*M*snr)
h0=1+z[0]
h1=10**(-a*q/20)+z[1]
R=np.exp(-abs(f[:,None]-f[None,:])/10.)
cal=.001*(cholesky(R,lower=True)@rng.normal(size=len(f)))
thermal_y=-20*np.log10(abs(h1)/abs(h0))
y=thermal_y+cal
assert np.max(abs(y-obs.observed_enhancement_db.to_numpy()))<1e-12
pd.DataFrame(dict(frequency_ghz=f,h0_real=h0.real,h0_imag=h0.imag,h1_real=h1.real,h1_imag=h1.imag,
                  magnitude0=abs(h0),magnitude1=abs(h1),thermal_log_ratio_db=thermal_y,
                  calibration_db=cal,observed_db=y)).to_csv(OUT/'complex_receiver_steps.csv',index=False)

# Generalized least squares and its scalar Schur complement are equivalent.
A=mat['A']; C=mat['C']; H=mat['H']
chol=cholesky(C,lower=True)
normal=A.T@cho_solve((chol,True),A)
rhs=A.T@cho_solve((chol,True),y)
theta=np.linalg.solve(normal,rhs)
bb=normal[1:,1:]; ab=normal[0,1:]
removed_information=float(ab@np.linalg.solve(bb,ab))
information=float(normal[0,0]-removed_information)
removed_score=float(ab@np.linalg.solve(bb,rhs[1:]))
score=float(rhs[0]-removed_score)
qhat=score/information
assert np.isclose(qhat,saved['estimate_ug_m3'],rtol=1e-10,atol=1e-9)
assert np.isclose(information**-.5,base['result']['sd_ug_m3'],rtol=1e-10,atol=1e-9)
np.savez_compressed(OUT/'normal_equations.npz',G=normal,g=rhs,theta=theta)
sd1=float(np.sqrt((H@differential_covariance(f,snr,M,.001,enhancement_db=a*q)@H.T).item()))
profile_z=np.array([0,500,1500,3000,5000])
report=dict(
    case='Same saved numerical example, actual HITRAN parameters and simulated receiver',
    frequency_ghz=float(f[0]),true_q_ug_m3=q,scale_height_m=1500.,
    molar_mass_g_mol=NATURAL_MOLAR_MASS_G_MOL['CH3CN'],avogadro=Avogadro,
    density_per_unit_q_m3=density0*1e6,surface_density_at_q_m3=density0*1e6*q,
    profile_z_m=profile_z.tolist(),profile_q_ug_m3=(q*np.exp(-profile_z/1500)).tolist(),
    vertical_mass_column_mg_m2=q*1500/1000,
    line_count=len(lines),first_quadrature_node=rows[0],largest_line=selected,
    node_partition_reference=Qref,node_partition_temperature=QT,
    second_radiation_constant_cm_k=c2,
    cross_section_sum_at_node_cm2=float(contribution.sum()),
    optical_depth_per_unit_q=float(layers.optical_depth_per_unit_q.sum()),
    a0_db_per_ug_m3=float(a[0]),optical_depth_at_q=float(layers.optical_depth_per_unit_q.sum()*q),
    attenuation_at_q_db=float(a[0]*q),amplitude_ratio=float(10**(-a[0]*q/20)),
    amplitude_reduction_pct=float(100*(1-10**(-a[0]*q/20))),power_ratio=float(10**(-a[0]*q/10)),
    sample_power_dbm=float(tones.received_per_tone_dbm.iloc[0]-a[0]*q),
    pilots=M,rho0=float(snr[0]),normalized_complex_noise_variance=float(1/(M*snr[0])),
    normalized_component_sd=float(1/np.sqrt(2*M*snr[0])),
    thermal_null_variance_db2=float(C[0,0]-1e-6),total_null_variance_db2=float(C[0,0]),
    first_tone_null_sd_db=float(np.sqrt(C[0,0])),
    h0_real=float(h0[0].real),h0_imag=float(h0[0].imag),h1_real=float(h1[0].real),h1_imag=float(h1[0].imag),
    h0_magnitude=float(abs(h0[0])),h1_magnitude=float(abs(h1[0])),
    first_tone_thermal_y_db=float(thermal_y[0]),first_tone_cal_db=float(cal[0]),first_tone_y_db=float(y[0]),
    G=normal.tolist(),g=rhs.tolist(),theta=theta.tolist(),
    removed_information=removed_information,information=information,removed_score=removed_score,score=score,
    qhat_ug_m3=qhat,sd0_ug_m3=information**-.5,sd1_ug_m3=sd1,
    threshold_ug_m3=base['result']['threshold_ug_m3'],q95_reconstruction=base['result']['threshold_ug_m3']+norm.ppf(.95)*sd1,
    claims='No measured concentration or orbital CSI; 0.001 dB residual remains assumed and unmeasured.')
(OUT/'worked_steps.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
paths=[ROOT/'data/raw/payload_bounds/lines.csv',
       *[DATA/name for name in ('matrices.npz','worked_example.json','worked_observation.csv',
                               'tone_by_tone.csv','baseline.json')],
       *[ROOT/'src/thz_isac'/name for name in ('physical_spectroscopy.py','atmospheric_profiles.py',
                                             'slant_path.py','zenith_tutorial.py','concentration_units.py')],
       Path(__file__)]
manifest=dict(inputs={str(x.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths},
              outputs={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(OUT.iterdir()) if x.name!='manifest.json'},
              calibration_residual_db=.001,seed=saved['seed'],role='Detailed numerical replay, not a new measured experiment')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f'Replayed {len(layers)} quadrature nodes, {len(lines)} lines and {len(f)} complex receiver tones')
print(f'a0 = {a[0]:.12g}; qhat = {qhat:.12g}; sd0 = {information**-.5:.12g}')
