"""Noise-free persistent-error lower bounds independent of pilot resources."""
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
    physical=ROOT/'results/closure_robust_atmosphere/inputs.npz';f=np.load(physical)['frequency']
    protocol=dict(epsilon_db=[1e-5,1e-4,1e-3],bands=['full_202','260_400_GHz'],
        objective='Noise-free worst absolute bias over the same finite atmospheric hull plus arbitrary per-probe persistent calibration error.',
        interpretation='A lower bound above one precludes the stated normalized RMSE target for every unbiased linear estimator satisfying the nuisance equalities, regardless of pilot count or thermal power.',
        certificate='Exact rational dual feasibility for normalized stored binary coefficients. It does not certify physical spectroscopy, an empirical calibration envelope or nonlinear/prior-assisted estimators.')
    run=Run(ROOT/'results/continuation_calibration_floor',protocol,__file__)
    rows=[];certificates=[];operators={};failures=[]
    for band,mask in [('full_202',np.ones(len(f),bool)),('260_400_GHz',(f>=260)&(f<=400))]:
        for epsilon in protocol['epsilon_db']:
            for j,gas in enumerate(['CO','O3','SO2','NO2']):
                try:
                    result=persistent_bias_floor(a['design'][mask],a['nuisance'][mask],a['design_bias'][mask],epsilon,j)
                    operators[f'{band}|{epsilon}|{gas}']=result.pop('operator')
                    for name in ['lp_equalities','lp_rhs','lp_inequalities','lp_cost']:
                        operators[f'{name}|{band}|{epsilon}|{gas}']=result.pop(name)
                    row=dict(band=band,epsilon_db=epsilon,gas=gas,**result)
                    certificates.append(row)
                    rows.append({k:v for k,v in row.items() if not k.endswith('fraction') and not isinstance(v,list)})
                except Exception as error:failures.append(dict(band=band,epsilon_db=epsilon,gas=gas,error=repr(error)))
            print(band,epsilon,'complete',flush=True)
    pd.DataFrame(rows).to_csv(run.output/'floors.csv',index=False)
    write_json(run.output/'certificates.json',certificates)
    np.savez_compressed(run.output/'operators.npz',**operators)
    run.finish(failures,extra={'input_hashes':{str(p):digest(p) for p in [source,physical]},
        'certificate_code_sha256':digest(ROOT/'src/thz_isac/calibration_floor.py')})
    if failures:raise RuntimeError('Failed floor solves retained')


if __name__=='__main__':main()
