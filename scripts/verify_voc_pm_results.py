"""Replay saved study invariants without regenerating spectroscopy or noise.

Uses a full-model SVD as an independent check of the nuisance-projected
estimator's covariance. Also verifies source/output bytes and power accounting.
"""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_support import digest, write_json


def main():
    ledger=ROOT/'results/voc_pm_capacity'
    checked_hashes=0
    for window in (1000,3000):
        name='acquisition_manifest.json' if window==1000 else 'acquisition_manifest_3000ghz.json'
        acquired=json.loads((ledger/name).read_text())
        # Normalize persisted Windows paths for reproduction on other systems.
        processed=ROOT/acquired['processed_file'].replace('\\','/')
        assert digest(processed)==acquired['processed_sha256']
        checked_hashes+=1
        suffix='' if window==1000 else '_0_3000'
        raw=ROOT/f'data/raw/voc_hitran_20260922{suffix}'
        for record in acquired['records']:
            assert record['status']=='acquired'
            for extension in ('data','header'):
                path=raw/f"{record['molecule']}_main_0_{window}GHz.{extension}"
                assert digest(path)==record[extension+'_sha256']
                checked_hashes+=1
    reports=[]
    for name in ('hitran_1000ghz','hitran_3000ghz','itu676-12_3000ghz'):
        folder=ledger/name
        manifest=json.loads((folder/'manifest.json').read_text())
        assert digest(ROOT/'scripts/run_voc_pm_capacity.py')==manifest['code_sha256']
        checked_hashes+=1
        for filename,expected in manifest['outputs'].items():
            assert digest(folder/filename)==expected, filename
            checked_hashes+=1
        for group in ('input_hashes','code_hashes'):
            for filename,expected in manifest.get(group,{}).items():
                assert digest(ROOT/filename.replace('\\','/'))==expected, filename
                checked_hashes+=1
        data=np.load(folder/'physical_inputs.npz')
        f=data['frequency_ghz']; gain=data['gain_per_watt']; power=data['power_w']
        assert f.min()>=60 and f.max()<=400 and len(f)==256
        assert np.all(power>=0) and np.isclose(power.sum(),10**((23-30)/10),rtol=1e-12)
        rate=(1-30/10000)*1e6*np.log2(1+gain*power).sum()
        capacity=pd.read_csv(folder/'capacity_contract.csv')
        assert capacity.iloc[0].accepted and not capacity.iloc[1:].accepted.any()
        np.testing.assert_allclose(capacity.iloc[0].candidate_bps,rate,rtol=1e-12)
        assert capacity.iloc[0].relative_loss==0
        # KKT condition for equal-bandwidth waterfilling, independent of solver.
        active=power>0
        marginal=gain/(1+gain*power)
        np.testing.assert_allclose(marginal[active],marginal[active].mean(),rtol=1e-12)
        assert np.all(marginal[~active]<=marginal[active].mean()*(1+1e-12))
        checks=pd.read_csv(folder/'spectroscopy_validation.csv')
        assert checks.passed.all()
        report=dict(run=name,rate_bps=float(rate),sensing_tones=int(data['sensing_mask'].sum()),
                    all_frequencies_in_60_400_ghz=True,capacity_contract_passed=True)
        mask=data['sensing_mask']
        if not mask.any():
            summary=json.loads((folder/'summary.json').read_text())
            assert summary['status']=='insufficient_sensing_tones'
            assert not (folder/'joint_precision.csv').exists()
            report['retrieval_status']='explicitly_unavailable'
        else:
            d=np.column_stack((data['gas'][mask,:3],data['pm'][mask]))
            n=np.column_stack((np.ones(mask.sum()),data['background_db'][mask],data['gas'][mask,3:7]))
            full=np.column_stack((d,n))
            table=pd.read_csv(folder/'joint_precision.csv')
            discrepancies=[]
            for (frames,residual),group in table.groupby(['frames','residual_std_db']):
                variance=2*(10/np.log(10))**2/(30*frames*gain[mask]*power[mask])+residual**2
                white=full/np.sqrt(variance[:,None])
                scale=np.linalg.norm(white,axis=0)
                _,s,vt=np.linalg.svd(white/scale,full_matrices=False)
                inverse=vt.T/s
                cov=(inverse@inverse.T)/scale[:,None]/scale[None,:]
                sd=np.sqrt(np.diag(cov)[:5])
                expected=group.set_index('target').loc[['H2CO','CH3OH','CH3CN','PM2.5','PMcoarse'],'predicted_sd_ug_m3'].to_numpy()
                discrepancies.append(float(np.max(np.abs(sd/expected-1))))
                np.testing.assert_allclose(sd,expected,rtol=1e-6)
                pm10=np.sqrt(cov[3,3]+cov[4,4]+2*cov[3,4])
                np.testing.assert_allclose(pm10,group.set_index('target').loc['PM10','predicted_sd_ug_m3'],rtol=1e-6)
            empirical=table.empirical_noise_rmse_ug_m3/table.predicted_sd_ug_m3
            assert np.max(np.abs(empirical-1))<.04
            exact=pd.read_csv(folder/'complex_pilot_response_controls.csv')
            assert np.max(np.abs(exact.rmse_ug_m3/exact.gaussian_predicted_sd_ug_m3-1))<.04
            failures=pd.read_csv(folder/'identifiability_failures.csv')
            assert len(failures)==6 and (failures.status=='unidentifiable').all()
            assert (table.added_sensing_pilots==0).all()
            report.update(retrieval_status='conditional_only',
                          independent_full_model_svd_max_relative_sd_difference=max(discrepancies),
                          maximum_monte_carlo_relative_rmse_difference=float(np.max(np.abs(empirical-1))))
        reports.append(report)
    result=dict(status='passed',checked_hashes=checked_hashes,runs=reports,
                scope='Numerical and provenance verification; no physical receiver or field validation.',
                verifier_sha256=digest(Path(__file__)))
    write_json(ledger/'verification.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
