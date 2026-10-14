"""Prepare numerical evidence and font metrics for the CO presentation.

This script creates no visual assets. The deck builder creates native charts
and text using these saved scientific values.
"""
from pathlib import Path
import csv
import importlib.util
import json
import numpy as np
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tmp/co_observability_deck"
BUILD.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "results/restart_2026_10_14"
arrays = np.load(SOURCE / "channel_matrices.npz")
f = arrays["frequency_ghz"]
lengths = arrays["length_m"]
loss_db = arrays["tau_co"] * 10 / np.log(10)

with (SOURCE / "co_line_examples.csv").open(encoding="utf-8") as handle:
    examples = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(handle)]
centers = np.array([row["center_ghz"] for row in examples])
indices = [int(np.argmin(abs(f - center))) for center in centers]
# Keep the source samples at all line centers and every second other point.
selection = np.unique(np.r_[np.arange(0, len(f), 2), indices, len(f) - 1])

spec = importlib.util.spec_from_file_location("co_model", ROOT / "scripts/restart_co_observability.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
with (SOURCE / "co_line_parameters.csv").open(encoding="utf-8") as handle:
    lines = [{key: value if key in ("upper_v", "lower_v") else float(value)
              for key, value in row.items()} for row in csv.DictReader(handle)]
first = min((row for row in lines if row["upper_v"] == "0" and row["lower_v"] == "0"), key=lambda row: row["nu_cm_1"])
profile_f = np.linspace(105, 125, 801)
profiles = [model.cross_section(profile_f, [first], pressure) /
            (first["S_296_cm_per_molecule"] * model.GHZ_PER_CM) for pressure in (1., .1)]

font = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 100)
characters = "".join(chr(i) for i in range(32, 127)) + "τσαΔδπθ∫Σ∞−×²₀₁₂₃ₘₙₖℓγν≈∈∉μ∆ϕηε∂"
font_widths = {char: font.getlength(char) for char in characters}

content = {
    "examples": examples,
    "spectrum": {"x": f[selection].tolist(), "y_mdb": (loss_db[selection, -1] * 1e3).tolist()},
    "profiles": {"x": profile_f.tolist(), "one_atm": profiles[0].tolist(), "point_one_atm": profiles[1].tolist()},
    "paths": {"x": lengths.tolist(), "series": [{"frequency_ghz": float(f[k]), "loss_micro_db": (loss_db[k] * 1e6).tolist()} for k in indices[:3]]},
    "first_line_fwhm_ghz": examples[0]["air_hwhm_ghz_at_296K_1atm"] * 2,
    "font_widths_at_100px": font_widths,
    "source_manifest": json.loads((SOURCE / "manifest.json").read_text()),
}
(BUILD / "evidence.json").write_text(json.dumps(content, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(f"Prepared {len(selection)} spectral samples, two line profiles and three path curves.")
