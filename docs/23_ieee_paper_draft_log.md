# IEEE Paper Draft Log

## What Was Done

An IEEE style paper draft was created at:

```text
paper/main.tex
```

## Why It Was Done

The project now has external data driven benchmark results. The paper is intended to summarize:

1. The research question.
2. The HITRAN and UCI data sources.
3. The forward model.
4. The estimator benchmark.
5. The best observed error.
6. The limitations that remain before claiming physical validation.

## Important Framing

The abstract and limitations explicitly state that CSI is simulated. This is necessary because only the spectroscopy and pollutant concentration records are external data.

## Main Result Included

The paper reports:

| Feature set | Model | Mean normalized RMSE | Mean R2 |
| --- | --- | ---: | ---: |
| Template projection | Ridge alpha 17.8 | 0.0779 | 0.9452 |

## What Remains

1. Replace the simplified forward model with calibrated HAPI absorption coefficients.
2. Improve the PM scattering model before making stronger physical claims.
3. Expand the paper after adding SNR, bandwidth, elevation, and atmospheric layer sweeps.
4. Add estimation bounds after the forward model is calibrated.

## Build Result

The paper was compiled with bundled Tectonic because the default MiKTeX latexmk route required Perl on this machine.

```powershell
python C:\Users\guill\.codex\plugins\cache\openai-bundled\latex\0.2.4\scripts\compile_latex.py C:\Research\THz_ISAC_atmospheric_monitoring\paper\main.tex --compiler tectonic --output-directory C:\Research\THz_ISAC_atmospheric_monitoring\paper\build --json
```

Output:

```text
paper/build/main.pdf
```

The final Tectonic pass produced a two page PDF. The first pass emitted expected temporary undefined citation and reference warnings before rerun. The final pass retained only Tectonic font substitution warnings from IEEEtran, which do not block PDF generation.

## Visual Inspection

The PDF was rendered to page images with Poppler and inspected. The table, figures, equations, and references are visible, with no clipped figures or overflowing equations observed.
