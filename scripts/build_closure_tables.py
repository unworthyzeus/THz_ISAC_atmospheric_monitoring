"""Render manuscript numbers from saved evidence."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/five_task_closure"
PAPER = ROOT / "paper"


def main():
    def select(name):
        frame = pd.read_csv(ROOT / "results/task_completion" / name)
        frame = frame[(frame.band == "multiband_reference") & (frame.nuisance_policy == "reference_calibration")
                      & (frame.elapsed_s == 10) & (frame.residual_std_db == 0)]
        if "bias_bound_db" in frame:
            frame = frame[frame.bias_bound_db == 0]
        if "control" in frame:
            frame = frame[frame.control == "positive"]
        return frame.set_index("target")
    limits = select("detection_limits.csv")
    metrics = select("detection_metrics.csv")
    errors = select("concentration_errors.csv")
    lines = []
    for name, label in [("H2CO", "Formaldehyde"), ("CH3OH", "Methanol"), ("CH3CN", "Acetonitrile")]:
        row = limits.loc[name]
        lines.append(f"{label} & {row.detection_limit_ug_m3:.2f} & {row.detection_limit_ppm:.5f} & {metrics.loc[name,'recall_pct']:.2f} & {errors.loc[name,'rmse_ug_m3']:.2f} " + r"\\")
    (PAPER / "closure_voc_rows.tex").write_text(
        r"\begin{tabular}{lrrrr}\toprule" + "\n" +
        r"VOC & LOD (\ugm) & ppm & Recall (\%) & RMSE (\ugm)\\\midrule" + "\n" +
        "\n".join(lines) + "\n" + r"\bottomrule\end{tabular}" + "\n")
    waveform = json.loads((OUT / "ofdm_waveform_controls.json").read_text())
    lines = [f"{r['normalized_cfo']*1000:.0f} & {r['bit_errors']:,} & {100*r['uncoded_ber']:.4f} & Identical " + r"\\" for r in waveform]
    (PAPER / "closure_waveform_rows.tex").write_text(
        r"\begin{tabular}{rrrr}\toprule" + "\n" +
        r"CFO (kHz) & Bit errors & BER (\%) & Reuse decisions\\\midrule" + "\n" +
        "\n".join(lines) + "\n" + r"\bottomrule\end{tabular}" + "\n")


if __name__ == "__main__":
    main()
