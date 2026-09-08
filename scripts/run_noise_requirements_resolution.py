"""Compute conditional noise requirements under both declared observation models."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from repair_support import Run, digest
from run_rmse_metric_audit import build_context


def diagonal_floors(design, nuisance, variance):
    sd = np.sqrt(variance)
    d = design/sd[:, None]; n = nuisance/sd[:, None]
    norms = np.linalg.norm(n, axis=0); n = n[:, norms > 0]/norms[norms > 0]
    u, singular, _ = np.linalg.svd(n, full_matrices=False)
    rank = int(np.sum(singular > singular[0]*1e-12))
    residual = d-u[:, :rank]@(u[:, :rank].T@d)
    return np.sqrt(np.diag(np.linalg.inv(residual.T@residual)))


def main():
    config = json.loads((ROOT / "results/tables/physical_feasibility_config.json").read_text())
    review = json.loads((ROOT / "results/review/protocol.json").read_text())
    config["surface_conditions_from_uci_medians"] = review["surface_conditions"]
    config["pm_model"]["uci_median_fine_fraction_of_pm10"] = review["pm_fine_fraction"]
    protocol = dict(config=config, pilot_counts=[30, 300, 3000, 30000], residual_std_db=[0., .001, .01, .1, .63],
        models=["power", "coherent"], snr_min_db=5,
        boundary="Use only probes above 5 dB to avoid low-SNR extrapolation of both high-SNR likelihoods. Each model is a conditional scenario, not a measured receiver. Pilot energy and observation time grow with pilot count. Reference concentration scales are magnitude comparisons only.")
    run = Run(ROOT / "results/resolution_noise_requirements", protocol, __file__)
    air = ROOT / "data/processed/air_quality/beijing_air_quality_clean.csv.gz"
    lines = ROOT / "data/processed/hitran/hitran_60_400GHz_lines.csv"
    context = build_context(pd.read_csv(air), pd.read_csv(lines), config)
    keep = context.snr_db >= 5
    scale = np.array([4000., 100., 40., 25.])
    design = context.gas_design[keep]*scale[None, :]
    nuisance = np.column_stack((np.ones(len(context.snr_db)), context.background_db, context.pm_design))[keep]
    snr = 10**(context.snr_db[keep]/10); c = (10/np.log(10))**2
    rows = []; requirements = []
    for model in protocol["models"]:
        for pilots in protocol["pilot_counts"]:
            thermal = c/pilots*(1+1/snr)**2 if model == "power" else 2*c/(pilots*snr)
            for sigma in protocol["residual_std_db"]:
                floors = diagonal_floors(design, nuisance, thermal+sigma*sigma)
                for gas, floor in zip(["CO", "O3", "SO2", "NO2"], floors):
                    rows.append(dict(model=model, pilots=pilots, residual_std_db=sigma,
                        gas=gas, floor_over_reference_scale=float(floor), probes=int(keep.sum())))
            zero = diagonal_floors(design, nuisance, thermal)
            for index, gas in enumerate(["CO", "O3", "SO2", "NO2"]):
                if zero[index] > 1:
                    maximum = np.nan
                else:
                    lo, hi = 0., .63
                    for _ in range(60):
                        mid = (lo+hi)/2
                        if diagonal_floors(design, nuisance, thermal+mid*mid)[index] <= 1:
                            lo = mid
                        else:
                            hi = mid
                    maximum = lo
                requirements.append(dict(model=model, pilots=pilots, gas=gas,
                    zero_residual_floor=float(zero[index]), achievable_without_residual=bool(zero[index] <= 1),
                    maximum_residual_std_db=maximum))
    pd.DataFrame(rows).to_csv(run.output / "floors.csv", index=False)
    requirements = pd.DataFrame(requirements)
    requirements.to_csv(run.output / "requirements.csv", index=False)
    print(requirements.to_string(index=False))
    run.finish(extra={"input_hashes": {str(p): digest(p) for p in [air, lines]}, "retained_probes": int(keep.sum())})


if __name__ == "__main__":
    main()
