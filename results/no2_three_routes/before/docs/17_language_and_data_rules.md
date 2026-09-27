# Language And Data Rules

## Language Rule

All project facing text must be written in English.

This rule applies to documentation, paper drafts, figures, tables, code comments, commit messages, and script output intended for humans.

Spanish is allowed only when quoting an original source or preserving an external file name.

## Research Note Rule

Every substantial work block must leave a Markdown trace explaining:

1. What was done.
2. Why it was done.
3. What changed.
4. What result was obtained.
5. What remains open.
6. What should be improved next.

## Data Rule

The main scientific results must not rely on invented synthetic data.

Allowed:

1. HITRAN spectroscopic line data.
2. Real pollution concentration datasets.
3. Standard atmosphere models.
4. Published propagation, absorption, Rayleigh, Mie, or link budget models.
5. Synthetic CSI generated from external physical data and published models.

Not allowed as main evidence:

1. Hand made spectral lines.
2. Uniformly sampled pollutant labels without a real data source.
3. Results where the estimator knows the exact toy generator and is then presented as physically meaningful.

## Current Consequence

The earlier toy synthetic benchmark remains useful only as an engineering sanity check. It should not be used as the central result of the IEEE paper.

The next research stage must use external data, starting with HITRAN line data and a public air quality dataset.

