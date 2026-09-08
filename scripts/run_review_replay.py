"""Replay the spectral benchmark with training-only weather and block intervals.

This repairs prospective computation, not historical test reuse. All results
remain diagnostic on the previously inspected Beijing record.
"""
import copy
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from run_rmse_metric_audit import build_context, RIDGE_ALPHAS  # noqa: E402
from thz_isac.review_protocol import training_surface_conditions, calendar_block_interval  # noqa: E402


def main():
    out=ROOT/"results/review"
    out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    config=json.loads((ROOT/"results/tables/physical_feasibility_config.json").read_text())
    air=ROOT/"data/processed/air_quality/beijing_air_quality_clean.csv.gz"
    lines=ROOT/"data/processed/hitran/hitran_60_400GHz_lines.csv"
    data=pd.read_csv(air)
    hitran=pd.read_csv(lines)
    historical=build_context(data,hitran,config)
    revised=copy.deepcopy(config)
    revised["surface_conditions_from_uci_medians"]=training_surface_conditions(historical.sample,historical.split.train)
    train=historical.sample.iloc[historical.split.train]
    revised["pm_model"]["uci_median_fine_fraction_of_pm10"]=float((train.PM2_5_ug_m3/train.PM10_ug_m3).median())
    protocol=dict(surface_conditions=revised["surface_conditions_from_uci_medians"],
        pm_fine_fraction=revised["pm_model"]["uci_median_fine_fraction_of_pm10"],
        alphas=RIDGE_ALPHAS.tolist(),blocks_days=[7,30],bootstrap_seed=609050,
        scope="Diagnostic replay; same previously explored test period. No fresh independent confirmation is claimed.")
    (out/"protocol.json").write_text(json.dumps(protocol,indent=2))
    strict=build_context(data,hitran,revised)
    rows=[]
    for label,context in [("historical",historical),("training_only",strict)]:
        scaler=StandardScaler().fit(context.observations[context.split.train])
        x=scaler.transform(context.observations)
        y=context.targets
        validations=[]
        for alpha in RIDGE_ALPHAS:
            model=Ridge(alpha=alpha).fit(x[context.split.train],y[context.split.train])
            pred=model.predict(x[context.split.validation])
            score=np.mean(np.sqrt(np.mean((pred-y[context.split.validation])**2,axis=0))/context.denominators)
            validations.append(score)
        alpha=RIDGE_ALPHAS[np.argmin(validations)]
        model=Ridge(alpha=alpha).fit(x[context.split.train],y[context.split.train])
        pred=model.predict(x[context.split.test])
        truth=y[context.split.test]
        reference=np.broadcast_to(y[context.split.train].mean(0),truth.shape)
        def score(p):
            return float(np.mean(np.sqrt(np.mean((p-truth)**2,axis=0))/context.denominators))
        for days in [7,30]:
            interval=calendar_block_interval(truth,pred,reference,context.denominators,
                context.sample.iloc[context.split.test].datetime,block_days=days)
            rows.append(dict(scenario=label,alpha=float(alpha),ridge=score(pred),mean=score(reference),
                             difference=score(pred)-score(reference),**interval))
        np.savez_compressed(out/f"{label}_predictions.npz",truth=truth,prediction=pred,reference=reference,
            denominators=context.denominators,test_indices=context.split.test)
        print(rows[-1],flush=True)
    pd.DataFrame(rows).to_csv(out/"spectral_replay.csv",index=False)
    manifest=dict(protocol=protocol,wall_seconds=time.perf_counter()-start,
        python=platform.python_version(),numpy=np.__version__,cpu=platform.processor(),cpu_only=True,failures=[],
        inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [air,lines]},
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in [".csv",".npz"]})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
