"""Bounded oracle ablations to prioritize interventions for NO2."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from thz_isac.calibration_floor import persistent_bias_floor


def main():
    source=ROOT/'results/followup_bounded_bias/inputs.npz';a=np.load(source)
    physical=ROOT/'results/closure_robust_atmosphere/inputs.npz';frequency=np.load(physical)['frequency']
    d=a['design'];n=a['nuisance'];b=a['design_bias'];zero=np.zeros((len(d),1));empty=np.empty((len(d),0))
    cases=[('current',d,n,b,3),('atmospheric_discrepancy_known',d,n,zero,3),
        ('other_gas_concentrations_known',d[:,3:4],n,b,0),('linear_nuisance_coefficients_known',d,empty,b,3),
        ('atmosphere_and_other_gases_known',d[:,3:4],n,zero,0),
        ('all_non_NO2_quantities_known',d[:,3:4],empty,zero,0)]
    protocol=dict(epsilon_db=1e-4,inputs='All 202 existing probes and the 54-state design envelope; no new radio observations.',
        cases=[c[0] for c in cases],
        question='Which ideal additional knowledge could reduce the noise-free bias floor, before investing in a proposed instrument?',
        boundary='Oracle ablations are hypothetical and retain the original NO2 sensitivity. Exact atmosphere here removes the entire archived discrepancy, not merely a surface temperature measurement. All finite-resource comparisons still use the existing noise and acquisition models.')
    run=Run(ROOT/'results/no2_intervention_audit',protocol,__file__)
    rows=[];certificates=[];operators={}
    for name,design,nuisance,bias,target in cases:
        r=persistent_bias_floor(design,nuisance,bias,1e-4,target)
        for key in ['operator','lp_equalities','lp_rhs','lp_inequalities','lp_cost']:
            operators[name+'|'+key]=r.pop(key)
        certificates.append(dict(case=name,**r))
        rows.append(dict(case=name,lower_bound=r['lower_bound'],primal_bias=r['primal_bias'],identity_error=r['identity_error']))
    pd.DataFrame(rows).to_csv(run.output/'oracle_floors.csv',index=False)
    write_json(run.output/'certificates.json',certificates)
    np.savez_compressed(run.output/'operators.npz',**operators)
    # Monotone diagnostic bracket: primal feasibility is checked numerically;
    # dual lower bounds certify the represented LP on the excluded side.
    low,high=1e-5,1e-4;steps=[]
    for iteration in range(20):
        middle=(low+high)/2;r=persistent_bias_floor(d,n,b,middle,3)
        steps.append(dict(epsilon_db=middle,lower_bound=r['lower_bound'],primal_bias=r['primal_bias'],identity_error=r['identity_error']))
        if r['primal_bias']<1:low=middle
        elif r['lower_bound']>1:high=middle
        else:break
    pd.DataFrame(steps).to_csv(run.output/'calibration_crossing.csv',index=False)
    peak=int(np.argmax(abs(d[:,3])))
    write_json(run.output/'summary.json',dict(
        numerical_noise_free_unit_crossing_bracket_db=[low,high],
        bracket_boundary='The low endpoint uses a floating-point feasible primal; this is a numerical design requirement, not an empirically attainable receiver specification.',
        strongest_existing_NO2_probe_GHz=float(frequency[peak]),
        strongest_existing_NO2_sensitivity_db_per_reference=float(abs(d[peak,3])),
        calibration_only_oracle_formula=1e-4/float(abs(d[peak,3])),
        frequency_selection_boundary='Discarding existing observations cannot improve an optimal noise-free lower bound: any subset estimator is an admissible full-grid estimator with zero weights elsewhere. New frequencies or observation types change the model; dwell allocation affects noise.'))
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [source,physical]},
        'solver_code_sha256':digest(ROOT/'src/thz_isac/calibration_floor.py')})
    print(pd.DataFrame(rows).to_string(index=False),flush=True)
    print('Numerical noise-free calibration crossing:',low,high,flush=True)


if __name__=='__main__':main()
