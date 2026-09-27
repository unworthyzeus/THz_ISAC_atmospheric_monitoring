"""One common multivariable comparison for five VOCs, PM2.5 and PM10."""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
from joint_receiver_support import ROOT,OUT,TARGETS,Z,fit,write
from evaluate_joint_receiver import response_limit
from thz_isac.payload_sensing import attenuation_variance
from thz_isac.hopping_receiver import HoppingPlan


def main():
    plans=dict(selected=HoppingPlan(**json.loads((OUT/'selection.json').read_text())['plan']),
        uniform=HoppingPlan(**json.loads((ROOT/'results/receiver_design/hopping_plan.json').read_text())['plan']))
    rows=[]
    for label,plan in plans.items():
        for profile in ['standard','igra_01']:
            for elevation in [30.,45.,60.,90.]:
                data=dict(np.load(OUT/f'{label}_{profile}_{int(elevation)}_physics.npz'))
                for duration in [2.,20.,100.]:
                    for sigma in [0.,.0001,.001]:
                        for nf in [6.,17.]:
                            settings=dict(plan=label,profile=profile,elevation_deg=elevation,total_s=duration,
                                residual_std_db=sigma,noise_figure_db=nf,tx_power_dbm=23.,correlation_length_ghz=10.)
                            try:r=fit(data,plan,total_s=duration,sigma=sigma,elevation=elevation,noise_figure_db=nf)
                            except ValueError as exc:
                                for name in TARGETS:rows.append(dict(**settings,target=name,status='rejected',reason=str(exc)))
                                continue
                            for j,name in enumerate(TARGETS):
                                concentration=1. if j<5 else 15. if name=='PM2.5' else 45.
                                direction=r['design'][:,j] if j<7 else r['design'][:,5]*49/90+r['design'][:,6]*41/90
                                limit=response_limit(r,j,direction,sigma)
                                h=r['operator'][j]
                                variance=attenuation_variance(r['snr']*10**(-direction*concentration/10),r['count']['payload'],'m2m4')+attenuation_variance(r['snr'],r['count']['payload'],'m2m4')
                                positive_sd=np.sqrt((h*h)@variance+sigma*sigma*h@r['correlation']@h)
                                recall=100*norm.sf((Z*r['sd'][j]-concentration)/positive_sd)
                                rows.append(dict(**settings,target=name,status='computed',
                                    reference_concentration_ug_m3=concentration,predicted_recall_pct=recall,
                                    predicted_miss_rate_pct=100-recall,predicted_marginal_false_alarm_pct=.01/8*100,
                                    local_sd_ug_m3=r['sd'][j],positive_sd_ug_m3=positive_sd,predicted_relative_rmse_pct=100*positive_sd/concentration,
                                    formal_local_lod95_ug_m3=(Z+norm.ppf(.95))*r['sd'][j],
                                    response_lod95_ug_m3=limit,valid_response95=bool(np.isfinite(limit)),
                                    minimum_sensing_snr_db=10*np.log10(min(r['snr'])),sensing_tones=int(r['mask'].sum()),
                                    gaussian_rate_bps=r['gaussian_rate_bps'],transmission_s=r['count']['transmission_total_s'],
                                    pm10_fine_mass_fraction=49/90 if name=='PM10' else np.nan,
                                    evidence='Conditional prediction; Monte Carlo percentages are in response_metrics.csv'))
    table=pd.DataFrame(rows);table.to_csv(OUT/'global_comparison.csv',index=False)
    write('global_comparison_protocol.json',dict(condition_count=288,output_count=8,rows=len(table),
        axes=dict(plan=['uniform','selected'],profile=['standard','igra_01'],elevation_deg=[30,45,60,90],
                  total_s=[2,20,100],residual_std_db=[0,.0001,.001],noise_figure_db=[6,17]),
        fixed=dict(tx_power_dbm=23,correlation_length_ghz=10,matched_reference_weather=True),
        targets=TARGETS,pm_reference_ug_m3={'PM2.5':15,'PMcoarse':45,'PM10':45},
        scope='Cartesian comparison under fixed assumed material/profile/calibration models, not an exhaustive physical population. Failed settings remain rejected for all outputs; no zero uncertainty imputation.',
        pm10='Joint fine/coarse sum with cross covariance; positive PM10 response uses fine fraction 49/90.'))
    print(table.groupby(['target','status']).size().to_string())


if __name__=='__main__':main()
