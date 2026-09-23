"""Independently verify task 1.3 and the detection/error reporting artifacts."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_support import digest,write_json


def main():
    count=0
    for name,script in [('task_1_3','run_task_1_3.py'),('task_1_3_metrics','evaluate_retrieval_metrics.py')]:
        folder=ROOT/'results'/name
        manifest=json.loads((folder/'manifest.json').read_text())
        assert manifest['code_sha256']==digest(ROOT/'scripts'/script)
        count+=1
        for file,expected in manifest['outputs'].items():
            assert digest(folder/file)==expected,file
            count+=1
        for group in ('input_hashes','code_hashes'):
            for file,expected in manifest.get(group,{}).items():
                assert digest(ROOT/file.replace('\\','/'))==expected,file
                count+=1
    physical=ROOT/'results/task_1_3'
    checkpoint=json.loads((physical/'integration_checkpoint.json').read_text())
    recorded_sources={digest(ROOT/'scripts/run_task_1_3.py')}
    initial_source=physical/'integration_source_initial.py'
    if initial_source.exists(): recorded_sources.add(digest(initial_source))
    assert checkpoint['integration_source_sha256'] in recorded_sources
    hapi=pd.read_csv(physical/'hapi_multistate_validation.csv')
    assert len(hapi)==54 and hapi.passed.all()
    assert hapi.loc[hapi.profile=='lorentz','reference'].str.contains('sign adapter').all()
    sign=json.loads((physical/'hapi_pressure_shift_sign.json').read_text())
    assert sign['expected_center_cm_1']==sign['adapted_center_on_probe_grid_cm_1']
    assert sign['expected_center_cm_1']!=sign['unmodified_hapi_lorentz_center_on_probe_grid_cm_1']
    convergence=pd.read_csv(physical/'quadrature_convergence.csv')
    assert (convergence.loc[convergence.order==4,'relative_rms_difference']<.001).all()
    folder=ROOT/'results/task_1_3_metrics'
    protocol=json.loads((folder/'protocol.json').read_text())
    table=pd.read_csv(folder/'detection_metrics.csv')
    errors=pd.read_csv(folder/'concentration_errors.csv')
    samples=np.load(folder/'control_estimates.npz')
    targets=['H2CO','CH3OH','CH3CN','PM2.5','PMcoarse','PM10']
    for row in table.itertuples(index=False):
        j=targets.index(row.target)
        prefix=f'frames{row.frames}_residual{row.residual_std_db:g}'
        positive=samples[prefix+'_positive'][:,j]; null=samples[prefix+'_null'][:,j]
        threshold=norm.isf(.01)*row.standard_error_ug_m3
        tp=int(np.count_nonzero(positive>=threshold)); fp=int(np.count_nonzero(null>=threshold))
        assert (row.tp,row.fp,row.fn,row.tn)==(tp,fp,5000-tp,5000-fp)
        np.testing.assert_allclose(row.recall_pct,100*tp/5000,rtol=1e-12)
        np.testing.assert_allclose(row.precision_pct,100*tp/(tp+fp),rtol=1e-12)
        for control,values,truth in [('positive',positive,protocol['target_positive_truth_ug_m3'][j]),('absent',null,0)]:
            e=errors[(errors.frames==row.frames)&(errors.residual_std_db==row.residual_std_db)&
                       (errors.target==row.target)&(errors.control==control)].iloc[0]
            delta=values-truth
            np.testing.assert_allclose(e.rmse_ug_m3,np.linalg.norm(delta)/np.sqrt(len(delta)),rtol=1e-12)
            np.testing.assert_allclose(e.mae_ug_m3,np.abs(delta).mean(),rtol=1e-12)
            if truth:
                np.testing.assert_allclose(e.rmse_pct_of_truth,100*e.rmse_ug_m3/truth,rtol=1e-12)
            else:
                assert np.isnan(e.mae_pct_of_truth) and np.isnan(e.rmse_pct_of_truth)
    allocation=np.load(folder/'communication_allocation.npz')
    f=allocation['frequency_ghz']; p=allocation['power_w']; gain=allocation['gain_per_watt']
    assert len(f)==256 and f.min()>=60 and f.max()<=400
    np.testing.assert_allclose(p.sum(),10**((23-30)/10),rtol=1e-12)
    rate=.997*1e6*np.log2(1+gain*p).sum()
    np.testing.assert_allclose(rate,protocol['rate']['reference_bps'],rtol=1e-12)
    assert protocol['rate']['accepted'] and protocol['rate']['relative_loss']==0
    result=dict(status='passed',hashes_checked=count,detection_rows_checked=len(table),
       error_rows_checked=len(errors),hapi_cases_checked=len(hapi),rate_bps=float(rate),
       frequency_bounds_verified=[60,400],percentage_denominators_verified=True,
       verifier_sha256=digest(Path(__file__)),scope='Numerical verification; no field accuracy claim')
    write_json(ROOT/'results/task_1_3_verification.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
