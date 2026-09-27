# ML Estimators

## Principle

Start with interpretable estimators. A strong result from a simple model is easier to defend than a black box result that may learn artifacts.

## Baseline Models

| Model | Purpose |
| --- | --- |
| Linear regression | Direct interpretability |
| Ridge | Stable linear baseline for correlated spectra |
| Lasso | Frequency selection |
| ElasticNet | Hybrid selection and stability |
| PLS | Spectroscopy friendly dimensionality reduction |
| KNN | Nonparametric local baseline |
| SVR | Smooth nonlinear baseline |
| Random Forest | Robust tabular nonlinear baseline |
| Extra Trees | Strong synthetic and tabular baseline |

## Physics Informed Estimator

The template least squares estimator is useful only when the template is externally valid.

With toy templates, it is an engineering check.

With HITRAN templates and a published PM model, it becomes a meaningful physics informed baseline.

## Metrics

1. MAE.
2. RMSE.
3. R2.
4. Bias.
5. Normalized RMSE by target range.
6. Detection floor error near low concentrations.

## Next Improvement

Once HITRAN and real pollutant records are integrated, the model benchmark should be rerun and the toy results should be excluded from the paper tables.

