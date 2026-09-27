# Error Optimization Plan

## Original Goal

Reduce estimation error for `gas_ppm` and `pm_ug_m3`.

## Updated Constraint

The main optimization must not rely on invented synthetic data.

The previous model benchmark remains a sanity check. The actual error minimization must be repeated with:

1. HITRAN line parameters.
2. Real pollution concentration records.
3. A published PM attenuation model.

## Work Already Done

Added:

1. `src/thz_isac/features.py`
2. `src/thz_isac/physics_estimator.py`
3. `scripts/run_model_benchmark.py`

These tools are still useful because they can be reused once real data is integrated.

## Why The Toy Error Became Low

The template least squares estimator knows the exact toy templates used by the generator. This is expected to produce very low error.

That result proves the estimator implementation is correct, but it does not prove atmospheric sensing viability.

## Next Improvement

Replace the toy templates with HITRAN templates and rerun the benchmark.

## Remaining Work

1. Download external data.
2. Build real data feature generation.
3. Rerun model benchmark.
4. Write results note.
5. Write IEEE paper only after real data results exist.

