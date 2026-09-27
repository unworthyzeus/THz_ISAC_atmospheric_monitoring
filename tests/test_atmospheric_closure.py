from pathlib import Path
import numpy as np
import pandas as pd
from thz_isac.attainable_estimation import efficient_linear_estimator

def test_atmospheric_estimator_against_augmented_least_squares():
    root=Path(__file__).resolve().parents[1]/'results/closure_robust_atmosphere'
    inputs=np.load(root/'inputs.npz');d=inputs['design'];n=inputs['expanded_nuisance']
    variance=2*(10/np.log(10))**2/(30000*inputs['snr'])
    a=np.column_stack([d,n])/np.sqrt(variance)[:,None]
    scale=np.linalg.norm(a,axis=0);normalized=a/scale
    inverse=np.linalg.lstsq(normalized,np.eye(len(a)),rcond=1e-12)[0]/scale[:,None]
    operator=inverse[:4]/np.sqrt(variance)[None,:]
    implemented=efficient_linear_estimator(d,n,np.diag(variance))
    np.testing.assert_allclose(operator,implemented.operator,rtol=2e-8,atol=2e-9)
    grid=pd.read_csv(root/'grid.csv')
    for row in grid[(grid.pilots==30000)&(grid.method=='atmospheric_tangent')].itertuples():
        j=['CO','O3','SO2','NO2'].index(row.gas)
        bias=inputs[f'bias_{row.dt}_{row.dp}_{row.height}_{row.quantile}']
        expected=np.sqrt(np.sum(operator[j]**2*variance)+(operator[j]@bias)**2)
        assert np.isclose(expected,row.rmse_ratio,rtol=1e-8)
