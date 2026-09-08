"""Training-atmosphere covariance sensitivity, preserving marginal noise variance."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from repair_support import Run,digest
from run_rmse_metric_audit import build_context
from thz_isac.review_protocol import training_surface_conditions
from thz_isac.correlated_bounds import correlated_floors


def main():
    config=json.loads((ROOT/"results/tables/physical_feasibility_config.json").read_text())
    strict=json.loads((ROOT/"results/review/protocol.json").read_text())
    config["surface_conditions_from_uci_medians"]=strict["surface_conditions"]
    config["pm_model"]["uci_median_fine_fraction_of_pm10"]=strict["pm_fine_fraction"]
    protocol=dict(config=config,residual_correlations=[0,.5,.9],lengths_ghz=[1,10,100],
        boundary="Correlated residual scenarios at unchanged marginal variance, not instrument calibration or an independent validation period. Correlation can improve or degrade efficient information after nuisance elimination; independent noise is not a universal optimistic bound.")
    run=Run(ROOT/"results/repair_correlated",protocol,__file__)
    air=ROOT/"data/processed/air_quality/beijing_air_quality_clean.csv.gz"
    lines=ROOT/"data/processed/hitran/hitran_60_400GHz_lines.csv"
    context=build_context(pd.read_csv(air),pd.read_csv(lines),config)
    expected=training_surface_conditions(context.sample,context.split.train)
    assert expected==strict["surface_conditions"]
    n=len(context.noise_variance)
    frequencies=np.linspace(config["atmosphere"]["frequency_min_ghz"],config["atmosphere"]["frequency_max_ghz"],n)
    nuisance=np.column_stack((np.ones(n),context.background_db,context.pm_design))
    scale=np.array([4000,100,40,25])
    design=context.gas_design*scale[None,:]
    rows=[]
    for length in protocol["lengths_ghz"]:
        kernel=np.exp(-np.abs(frequencies[:,None]-frequencies[None,:])/length)
        for rho in protocol["residual_correlations"]:
            correlation=(1-rho)*np.eye(n)+rho*kernel
            floors,rank,condition=correlated_floors(design,nuisance,context.noise_variance,
                config["observation"]["residual_error_std_db"],correlation)
            for gas,floor in zip(["CO","O3","SO2","NO2"],floors):
                rows.append(dict(length_ghz=length,rho=rho,gas=gas,floor_over_reference_scale=float(floor),
                    nuisance_rank=rank,condition_number=condition))
    pd.DataFrame(rows).to_csv(run.output/"floors.csv",index=False)
    run.finish(extra=dict(input_hashes={str(p):digest(p) for p in [air,lines]}))


if __name__=="__main__":
    main()
