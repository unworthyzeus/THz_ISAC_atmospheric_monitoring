# Scientific repair: THz conditional feasibility

## What changed and why

Independent noise was described too broadly as optimistic, and unrelated ground-data tasks obscured the physical sensing claim. The added computation and its frozen choices are recorded in the [implementation](../scripts/run_correlated_repair.py) and [protocol](../results/repair_correlated/protocol.json).

## Current result

RESULT: The training-atmosphere covariance study keeps marginal noise variance fixed and shows that correlation can raise or lower efficient estimation bounds. The CO bound ranges from 19.39 to 23.59 times its stated reference concentration scale. Ground-sensor repair scores no longer serve as atmospheric sensing evidence. See the [result artifact](../results/repair_correlated/floors.csv), [execution manifest](../results/repair_correlated/manifest.json) and [updated manuscript](../paper/build/main.pdf).

## Remaining limits and next decision

INFERENCE: No measured atmospheric THz observations or independent new validation period were acquired. Receiver covariance, vertical profiles and the likelihood remain modeled. The result is conditional feasibility analysis, not field validation or universal impossibility. These boundaries are stated in the [manuscript source](../paper/repair_results.tex) and supported by the scope of the [result artifact](../results/repair_correlated/floors.csv).

## Reproduction

Run from this project directory with Python 3.12 and the sibling `00_research_portfolio/scripts` directory present. The exact versions and input/output hashes are in the [execution manifest](../results/repair_correlated/manifest.json). This experiment uses the CPU. Parent-process RSS is sampled every 0.1 seconds; it is not an exact process peak, and the online EM worker memory is unavailable.

```powershell
$env:PYTHONPATH = 'src;.'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
py -3.12 scripts/run_correlated_repair.py
```

The [portfolio validation record](../../../00_research_portfolio/results/repairs/validation_manifest.json) records final tests and compilation. Prior experiment tables remain unchanged; the [prior version snapshot](../../../00_research_portfolio/results/repairs/before/THz_ISAC_atmospheric_monitoring) preserves the replaced overview and manuscript.
