"""Independent rare-isotope Voigt comparisons and unavailable-data audit."""
from pathlib import Path
import sys,json,contextlib,hashlib
import numpy as np
import pandas as pd
import hapi
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule


def main():
    out=ROOT/'results/task_completion';raw=ROOT/'data/raw/task_completion'
    lines=pd.read_csv(ROOT/'data/processed/task_completion/all_isotopes_0_3000GHz.csv')
    f=np.linspace(60,400,97);results=[]
    with (out/'rare_isotope_hapi.log').open('w') as log,contextlib.redirect_stdout(log):
        hapi.db_begin(str(raw))
        for name,mid,iso in [('H2CO',20,2),('H2CO',20,3),('CO',5,2),('CO',5,6),('H2O',1,2),('SO2',9,2)]:
            selected=lines[(lines.molecule==name)&(lines.isotopologue_id==iso)]
            for t,p in [(296.,101325.),(220.,5000.)]:
                ours=molecular_cross_section_cm2_per_molecule(selected,f,name,temperature_k=t,pressure_pa=p)
                _,ref=hapi.absorptionCoefficient_Voigt(Components=((mid,iso),),SourceTables=f'{name}_iso{iso}_0_3000GHz',
                     Environment={'T':t,'p':p/101325},WavenumberGrid=f/29.9792458,
                     WavenumberWing=101.,IntensityThreshold=0.,HITRAN_units=True,Diluent={'air':1.})
                error=float(np.max(np.abs(ours-ref))/ref.max())
                results.append(dict(molecule=name,isotopologue_id=iso,temperature_k=t,pressure_pa=p,
                    peak_normalized_error=error,passed=error<1e-5))
    pd.DataFrame(results).to_csv(out/'rare_isotope_hapi_validation.csv',index=False)
    if not all(r['passed'] for r in results):raise SystemExit('Rare-isotope reference comparison failed')
    print(len(results),'rare-isotope HAPI checks passed; maximum error',max(r['peak_normalized_error'] for r in results))


if __name__=='__main__':main()
