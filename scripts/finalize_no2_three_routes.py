"""Package verified NO2 artifacts and refresh the current local PDF alias."""
from pathlib import Path
import json
import shutil
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_support import Run,digest,write_json


def main():
    out=ROOT/'results/no2_three_routes'
    run=Run(out/'delivery',dict(scope='Local packaging after independent verification, full THz tests and visual review.'),__file__)
    validation=json.loads((out/'validation/validation_manifest.json').read_text())[0]
    assert validation['tests']['passed']==161 and validation['tests']['returncode']==0
    assert validation['build']['returncode']==0 and not validation['qa']['issues'] and not validation['qa']['overfull']
    assert validation['pdf_sha256']==digest(ROOT/'paper/build/main.pdf')
    checks=json.loads((out/'verification/checks.json').read_text())
    assert checks['design_rows']==30 and checks['exact_rational_floor_certificates']==2
    # Compare the newly evaluated coarse coefficients to their immutable source.
    new=np.load(out/'physical/inputs.npz');old=np.load(ROOT/'results/followup_bounded_bias/inputs.npz')
    old_f=np.load(ROOT/'results/closure_robust_atmosphere/inputs.npz')['frequency']
    mask=(old_f>=260)&(old_f<=400)
    relative=float(np.max(abs(new['design'][new['coarse_mask']]/old['design'][mask]-1)))
    assert relative<1e-7
    write_json(run.output/'physical_overlap_check.json',dict(maximum_relative_gas_design_difference=relative,
        interpretation='New direct spectral evaluations agree with the archived coarse gas coefficients; this is not a certificate for physical parameter uncertainty.'))
    alias=ROOT/'output/pdf/thz_isac_pollutant_sensing_ieee.pdf'
    previous_hash=digest(alias)
    assert previous_hash==digest(out/'before/thz_isac_pollutant_sensing_ieee.pdf')
    shutil.copy2(ROOT/'paper/build/main.pdf',alias)
    write_json(run.output/'pdf_alias.json',dict(path=str(alias),previous_sha256=previous_hash,current_sha256=digest(alias),
        previous_copy=str(out/'before/thz_isac_pollutant_sensing_ieee.pdf')))
    write_json(run.output/'visual_review.json',dict(pages=15,
        reviewed='All four contact sheets, covering all 15 pages, plus the standalone current figure. New core text, table and figure checked for legibility, clipping and layout. Disconnected spectral windows are not joined by interpolated lines.',
        automatic_issues=validation['qa']['issues'],overfull=validation['qa']['overfull'],
        pdf_sha256=digest(alias),boundary='Layout and numerical consistency review, not external scientific endorsement.'))
    before={str(p.relative_to(out/'before')):digest(p) for p in (out/'before').rglob('*') if p.is_file()}
    write_json(run.output/'before_manifest.json',before)
    files=[ROOT/'src/thz_isac/no2_design.py',ROOT/'tests/test_no2_design.py',ROOT/'paper/main.tex',
        ROOT/'paper/continuation_results.tex',ROOT/'paper/no2_three_routes.tex',ROOT/'docs/no2_three_routes.md',
        ROOT/'docs/source_map.md',ROOT/'docs/no2_intervention_options.md',ROOT/'README.md',ROOT/'paper/README.md',
        ROOT/'references/proposals/I2R_proposal_THz_ISAC.pdf',ROOT/'I2R_proposal_THz_ISAC (1).pdf',alias]
    files+=list((ROOT/'scripts').glob('*no2*routes*.py'))
    files+=[ROOT/'scripts/characterize_receiver_calibration.py',ROOT/'scripts/no2_resource_requirements.py']
    files+=list(out.glob('*/manifest.json'))
    write_json(run.output/'final_artifacts.json',{str(p):digest(p) for p in files if p.is_file()})
    run.finish(extra={'verification_sha256':digest(out/'verification/checks.json'),
        'pdf_sha256':digest(alias),'tests_passed':161,
        'source_record':'I2R proposal inspected in full locally, physical pp. 1-2. NIST DOI 10.1117/12.784620, official full PDF read through web tool; no receiver recordings acquired.'})
    print('Delivered verified PDF:',alias)


if __name__=='__main__':main()
