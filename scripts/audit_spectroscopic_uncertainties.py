"""Retain HITRAN uncertainty and reference codes without inventing error bars."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/task_completion'


def main():
    acquisition=json.loads((OUT/'spectroscopy_acquisition.json').read_text())
    rows=[];summary=[];input_hashes={}
    for rec in acquisition['records']:
        if rec['status']!='acquired':continue
        name=rec['molecule'];iso=rec['isotopologue_id']
        path=ROOT/'data/raw/task_completion'/f'{name}_iso{iso}_0_3000GHz.data'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==rec['data_sha256']
        input_hashes[path.name]=digest;group=[]
        for index,line in enumerate(path.read_text().splitlines()):
            if not line.strip():continue
            if len(line)!=160:raise ValueError('Expected standard 160-character HITRAN record')
            frequency=float(line[3:15])*29.9792458
            if not 60<=frequency<=400:continue
            codes=line[127:133];references=line[133:145]
            item=dict(molecule=name,isotopologue_id=iso,raw_row=index+1,frequency_ghz=frequency,
                      intensity=float(line[15:25]),uncertainty_codes=codes,reference_codes=references)
            for j,parameter in enumerate(['position','intensity','air_width','self_width','temperature_exponent','pressure_shift']):
                item[parameter+'_code']=int(codes[j]) if codes[j].isdigit() else None
            rows.append(item);group.append(item)
        frame=pd.DataFrame(group)
        if len(frame):
            for parameter in ['position','intensity','air_width','self_width','temperature_exponent','pressure_shift']:
                counts=frame[parameter+'_code'].value_counts(dropna=False)
                for code,count in counts.items():summary.append(dict(molecule=name,isotopologue_id=iso,parameter=parameter,
                    uncertainty_code=int(code) if pd.notna(code) else 'missing',lines=int(count),fraction_pct=100*count/len(frame)))
    destination=ROOT/'data/processed/task_completion/in_band_line_uncertainties.csv'
    pd.DataFrame(rows).to_csv(destination,index=False)
    pd.DataFrame(summary).to_csv(OUT/'spectroscopic_uncertainty_inventory.csv',index=False)
    manifest=dict(source='https://hitran.org/docs/uncertainties/',in_band_lines=len(rows),input_hashes=input_hashes,
       processed_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
       convention='Six fixed-width ierr codes and six two-character iref codes retained as provided',
       uncertainty_interpretation='Relative codes 0/1/2 mean unavailable/default/estimate. They are not a zero-percent uncertainty or a probability distribution. Absolute codes apply to line position and pressure shift.',
       confidence_limit_scope='Retrieval covariance conditions on line parameters. Unreported spectroscopic uncertainty prevents an unconditional field detection limit.')
    (OUT/'spectroscopic_uncertainty_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Audited',len(rows),'in-band transitions')


if __name__=='__main__':main()
