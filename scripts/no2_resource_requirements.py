"""Constructive fixed-design time requirements and exact fine-grid box floors."""
from pathlib import Path
from fractions import Fraction
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from thz_isac.no2_design import integer_dwell
from thz_isac.calibration_floor import persistent_bias_floor


def main():
    out=ROOT/'results/no2_three_routes';run=Run(out/'requirements',dict(
        scope='Sufficient time for each frozen 100-second design, not the optimum across redesigned estimators or proof of physical stationarity.',
        target_rmse=1.,maximum_time_s=86400.,power_dbm=-1.,retune_s=.001,
        floors='Exact rational dual lower bounds only for the represented normalized coarse/fine atmospheric-hull plus 1e-4 dB box LP.'),__file__)
    a=np.load(out/'physical/inputs.npz');operators=np.load(out/'design/operators.npz')
    table=pd.read_csv(out/'design/summary.csv');rows=[];traces=[]
    for row in table[table_duration_mask(table)].itertuples():
        key=f'{row.case}|100s';mask=operators[key+'|mask'];h=operators[key+'|h'];w=operators[key+'|weights']
        thermal=a['thermal'][mask];bias=row.atmosphere_bias+row.calibration_bias
        def at(duration):
            count,r=integer_dwell(w,duration,sweeps=row.sweeps,retune_s=.001)
            return float(np.sqrt((h*h)@(row.sweeps*thermal/count)+bias*bias)),r
        if bias>=1:
            rows.append(dict(case=row.case,status='fixed_operator_bias_at_least_one',bias=bias,
                sufficient_acquisition_s=None,energy_j=None,achieved_rmse=None));continue
        lo,hi=100.,86400.
        if at(hi)[0]>1:
            rows.append(dict(case=row.case,status='not_reached_by_one_day',bias=bias,
                sufficient_acquisition_s=None,energy_j=None,achieved_rmse=None));continue
        for k in range(45):
            mid=(lo+hi)/2;risk,_=at(mid)
            traces.append(dict(case=row.case,iteration=k,duration_s=mid,rmse=risk))
            if risk<=1:hi=mid
            else:lo=mid
        # Round the sufficient budget upward to a millisecond, then check its
        # actual integer allocation. This is constructive, not a time lower bound.
        hi=np.ceil(hi*1000)/1000
        risk,resource=at(hi)
        while risk>1:hi+=.001;risk,resource=at(hi)
        rows.append(dict(case=row.case,status='conditional_fixed_design_sufficient',bias=bias,
            sufficient_acquisition_s=hi,energy_j=resource['integration_s']*10**(-.1)/1000,achieved_rmse=risk))
    pd.DataFrame(rows).to_csv(run.output/'fixed_design_time.csv',index=False)
    pd.DataFrame(traces).to_csv(run.output/'time_trace.csv',index=False)
    certificates=[];arrays={};floors=[]
    for grid,mask in [('coarse',a['coarse_mask']),('fine',np.ones(len(a['frequency']),bool))]:
        result=persistent_bias_floor(a['design'][mask],a['nuisance'][mask],a['design_bias'][mask],1e-4,3)
        for k in ['operator','lp_equalities','lp_rhs','lp_inequalities','lp_cost']:arrays[grid+'|'+k]=result.pop(k)
        certificates.append(dict(grid=grid,**result))
        floors.append(dict(grid=grid,probes=int(mask.sum()),lower_bound=result['lower_bound'],
            primal_bias=result['primal_bias'],identity_error=result['identity_error']))
    write_json(run.output/'floor_certificates.json',certificates)
    np.savez_compressed(run.output/'floor_lp.npz',**arrays)
    pd.DataFrame(floors).to_csv(run.output/'floor_summary.csv',index=False)
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [out/'physical/inputs.npz',out/'design/operators.npz',out/'design/summary.csv']},
        'lp_solver_sha256':digest(ROOT/'src/thz_isac/calibration_floor.py')})
    print(pd.DataFrame(rows).to_string(index=False));print(pd.DataFrame(floors).to_string(index=False))


def table_duration_mask(table):return table.duration_s==100.


if __name__=='__main__':main()
