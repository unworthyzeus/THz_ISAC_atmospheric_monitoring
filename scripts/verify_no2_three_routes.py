"""Independent arithmetic replay of the saved NO2 design and stress artifacts."""
from pathlib import Path
from fractions import Fraction
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_support import Run,digest,write_json


def main():
    out=ROOT/'results/no2_three_routes'
    run=Run(out/'verification',dict(scope='Independent arithmetic, constraint, allocation and outcome replay; no solver optimality certificate.'),__file__)
    a=np.load(out/'physical/inputs.npz');hdata=np.load(out/'design/operators.npz')
    table=pd.read_csv(out/'design/summary.csv');resources=pd.read_csv(out/'design/resources.csv')
    discrepancies=[];identities=[];budget_errors=[];rounding=[]
    for row in table.itertuples():
        key=f'{row.case}|{row.duration_s:g}s';mask=hdata[key+'|mask'];h=hdata[key+'|h'];count=hdata[key+'|counts']
        frequency=a['frequency'][mask];v=row.sweeps*a['thermal'][mask]/count
        atmosphere=row.sweeps*np.max(abs(h@a['design_bias'][mask]))
        x=2*(frequency-260)/140-1
        modes=np.column_stack([np.ones(len(frequency)),x,(3*x*x-1)/2])*(row.total_calibration_db-row.residual_db)/3
        calibration=sum(abs(h@modes))+row.residual_db*sum(abs(h))
        noise=np.sqrt((h*h)@v);risk=np.hypot(noise,atmosphere+calibration)
        discrepancies.extend([abs(noise-row.noise_sd),abs(atmosphere-row.atmosphere_bias),
                              abs(calibration-row.calibration_bias),abs(risk-row.design_rmse)])
        expected=np.array([0,0,0,1.]);n=a['nuisance'][mask]
        identities.append(max(np.max(abs(h@a['design'][mask]-expected)),np.max(abs(h@n)/np.linalg.norm(n,axis=0))))
        r=resources[(resources['case']==row.case)&(resources.duration_s==row.duration_s)].iloc[0]
        assert np.all(count>=1) and np.all(count==count.astype(int))
        integration=count.sum()*row.sweeps*1e-6
        charged=integration+(len(h)-1)*row.sweeps*.001
        budget_errors.extend([abs(r.integration_s-integration),abs(r.charged_s-charged),
                              max(0,charged-row.duration_s),abs(r.radiated_energy_j-integration*10**(-.1)/1000)])
        if np.isfinite(row.continuous_rmse):rounding.append(row.design_rmse-row.continuous_rmse)
    # Fine grid includes every coarse frequency, so its change of candidate
    # observations is explicit; all comparisons keep the same power/time cap.
    assert int(a['coarse_mask'].sum())==71
    assert len(table)==30 and len(resources)==30
    state=np.load(out/'evaluation/stress_inputs.npz');errors=pd.read_csv(out/'evaluation/errors.csv')
    stress_errors=[]
    for (name,duration,suite,noise_model),group in errors.groupby(['case','duration_s','suite','noise_model']):
        row=table[(table['case']==name)&(table.duration_s==duration)].iloc[0]
        key=f'{name}|{duration:g}s';mask=hdata[key+'|mask'];h=hdata[key+'|h'];count=hdata[key+'|counts']
        if suite=='new_model_states':
            b=state['new_bias'][mask];thermal=state['new_thermal'][mask]
        else:
            b=state['pair_absolute_bias' if row.sweeps==1 else 'pair_difference_bias'][mask]
            thermal=state['pair_thermal_sample'][mask]
            if row.sweeps==2:thermal=thermal+state['pair_thermal_reference'][mask]
        noise=(h*h)@(row.sweeps*a['thermal'][mask]/count) if noise_model=='nominal' else (h*h/count)@thermal
        risk=np.sqrt(noise+(abs(h@b)+row.calibration_bias)**2)
        stress_errors.extend(abs(risk-group.sort_values('state').rmse.to_numpy()))
    pairs=pd.read_csv(out/'evaluation/pair_metadata.csv')
    reference=pd.to_datetime(pairs.reference_time);sample=pd.to_datetime(pairs.sample_time)
    assert (sample-reference==pd.Timedelta(hours=1)).all()
    assert (reference>pd.Timestamp('2016-06-03 04:00:00')).all()
    assert len(set(pairs.reference_row)&set(pairs.sample_row))==0
    stats=dict(design_rows=len(table),stress_rows=len(errors),pairs=len(pairs),
        max_design_absolute_error=float(max(discrepancies)),max_identity_error=float(max(identities)),
        max_budget_error=float(max(budget_errors)),max_stress_absolute_error=float(max(stress_errors)),
        minimum_rounded_minus_continuous=float(min(rounding)),maximum_rounded_minus_continuous=float(max(rounding)))
    assert stats['max_design_absolute_error']<1e-7
    assert stats['max_identity_error']<1e-7
    assert stats['max_budget_error']<1e-8
    assert stats['max_stress_absolute_error']<1e-6
    assert stats['minimum_rounded_minus_continuous']>-1e-6
    # Every rounded optimized design should improve the equal-dwell competitor
    # with the same candidate grid and box, within numerical tolerance.
    for grid in ['coarse','fine']:
        for duration in [10.,100.]:
            equal=table[(table['case']==grid+'_equal_box')&(table.duration_s==duration)].design_rmse.iloc[0]
            optimal=table[(table['case']==grid+'_dwell_box')&(table.duration_s==duration)].design_rmse.iloc[0]
            assert optimal<=equal+1e-6
    lp=np.load(out/'requirements/floor_lp.npz')
    certificates=json.loads((out/'requirements/floor_certificates.json').read_text())
    for certificate in certificates:
        grid=certificate['grid'];eq=lp[grid+'|lp_equalities'];ineq=lp[grid+'|lp_inequalities']
        lam=list(map(Fraction,certificate['equality_dual_fractions']))
        mu=list(map(Fraction,certificate['inequality_dual_fractions']))
        assert all(value<=0 for value in mu)
        for j,cost in enumerate(lp[grid+'|lp_cost']):
            lhs=sum((Fraction(float(v))*weight for v,weight in zip(eq[:,j],lam)),Fraction(0))
            lhs+=sum((Fraction(float(v))*weight for v,weight in zip(ineq[:,j],mu)),Fraction(0))
            assert lhs<=Fraction(float(cost))
        value=sum((Fraction(float(v))*weight for v,weight in zip(lp[grid+'|lp_rhs'],lam)),Fraction(0))
        assert value==Fraction(certificate['lower_fraction'])
        assert value>1
    stats['exact_rational_floor_certificates']=len(certificates)
    times=pd.read_csv(out/'requirements/fixed_design_time.csv')
    for row in times[times.status=='conditional_fixed_design_sufficient'].itertuples():
        key=f'{row.case}|100s';h=hdata[key+'|h'];mask=hdata[key+'|mask'];w=hdata[key+'|weights']
        specification=table[(table['case']==row.case)&(table.duration_s==100)].iloc[0]
        sweeps=specification.sweeps;m=len(h)
        budget=int(np.floor((row.sufficient_acquisition_s-sweeps*(m-1)*.001+1e-12)/(sweeps*1e-6)))
        ideal=(budget-m)*w/w.sum();count=np.floor(ideal).astype(int)+1
        count[np.argsort(-(ideal-np.floor(ideal)),kind='stable')[:budget-int(count.sum())]]+=1
        actual=np.sqrt((h*h)@(sweeps*a['thermal'][mask]/count)+row.bias**2)
        assert actual<=1+1e-12 and abs(actual-row.achieved_rmse)<1e-10
    write_json(run.output/'checks.json',stats)
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [out/'physical/inputs.npz',out/'design/operators.npz',
        out/'design/summary.csv',out/'design/resources.csv',out/'evaluation/stress_inputs.npz',out/'evaluation/errors.csv']}})
    print(stats)


if __name__=='__main__':main()
