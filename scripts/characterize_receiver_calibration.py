"""Analyze supplied repeated reference sweeps; never manufacture receiver data."""
from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from repair_support import Run,digest,write_json
from thz_isac.no2_design import characterize_calibration


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--degree',type=int,default=2)
    args=parser.parse_args()
    run=Run(args.output,dict(input=str(args.input.resolve()),degree=args.degree,
        split='First 60 percent of timestamps train; next 20 percent validation; final 20 percent test.',
        interpretation='Empirical descriptive repeatability; training maxima are not population error guarantees.'),__file__)
    result=characterize_calibration(pd.read_csv(args.input),degree=args.degree)
    arrays={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
    np.savez_compressed(run.output/'calibration.npz',**arrays)
    pd.DataFrame(result['summary']).to_csv(run.output/'coverage.csv',index=False)
    write_json(run.output/'summary.json',{k:v for k,v in result.items() if k not in arrays})
    run.finish(extra={'input_sha256':digest(args.input),'analysis_code_sha256':digest(ROOT/'src/thz_isac/no2_design.py')})
    print(pd.DataFrame(result['summary']).to_string(index=False))


if __name__=='__main__':main()
