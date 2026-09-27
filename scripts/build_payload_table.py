"""Generate the payload paper table directly from verified detection results."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
verification = json.loads((ROOT/"results/payload_recall/verification.json").read_text())
if verification["status"] != "passed":
    raise ValueError("Payload result verification must pass before reporting")
source = ROOT/"results/payload_recall/detection_metrics.csv"
manifest = json.loads((source.parent/"manifest.json").read_text())
if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["outputs"][source.name]:
    raise ValueError("Detection results changed after the recorded experiment")
metrics = pd.read_csv(source)
names = dict(H2CO="Formaldehyde", CH3OH="Methanol", CH3CN="Acetonitrile")
rows = []
for duration in [10, 100]:
    for target, label in names.items():
        selected = metrics[(metrics.elapsed_s == duration) & (metrics.target == target) & (metrics.residual_std_db == 0)].set_index("method")
        rows.append(f"{duration} s & {label} & {selected.loc['pilots', 'recall_pct']:.3f} & {selected.loc['payload_m2m4', 'recall_pct']:.3f} " + r"\\")
(ROOT/"paper/payload_recall_rows.tex").write_text(
    r"\begin{tabular}{llrr}\toprule"+"\n"+
    r"Time & Target & Pilots (\%) & M2M4 (\%)\\\midrule"+"\n"+
    "\n".join(rows)+"\n"+r"\bottomrule\end{tabular}"+"\n")
