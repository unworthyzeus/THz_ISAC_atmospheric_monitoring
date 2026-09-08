# Work Plan

## Stage 1

1. Keep the toy simulator as a software sanity check.
2. Download real HITRAN line data for gases in the 60 to 400 GHz range.
3. Download a public air quality dataset with PM and gas concentration records.
4. Build a forward model that converts real pollutant records into simulated CSI amplitudes.

## Stage 2

1. Add a stratified atmosphere model.
2. Add satellite elevation and slant path geometry.
3. Use HITRAN line positions and intensities instead of toy spectral lines.
4. Add PM attenuation using a published Rayleigh or Mie model.

## Stage 3

1. Train interpretable estimators.
2. Train stronger ML baselines.
3. Compare errors on a held out test split.
4. Report best model results only for the external data driven pipeline.

## Stage 4

1. Add sensitivity sweeps for SNR, bandwidth, and elevation.
2. Estimate detection floors.
3. Write an IEEE style paper draft.
4. Compile the paper and store the PDF in `paper/build/`.

## Immediate Deliverables

1. `data/raw/` with external source files or documented download scripts.
2. `results/tables/real_data_model_benchmark.csv`.
3. `results/figures/real_data_best_scatter.png`.
4. `docs/18_external_data_acquisition.md`.
5. `paper/main.tex`.

