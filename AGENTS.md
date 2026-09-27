# Repository Instructions

Commit completed changes and push to `main` by default, unless the user explicitly requests otherwise.

All project facing text must be written in English.

This includes:

1. Markdown documentation.
2. Paper drafts.
3. Figure titles and axis labels.
4. Table captions.
5. Code comments.
6. Commit messages.
7. Script output intended for humans.

Spanish may appear only when quoting an original source that is in Spanish or when preserving an external file name.

When adding research notes, always create or update a Markdown file explaining:

1. What was done.
2. Why it was done.
3. What result was obtained.
4. What remains to be done.
5. Risks or limitations.
6. Next steps.

Synthetic data generated from invented parameters must not be used as the main scientific result. Synthetic CSI is acceptable only when it is generated from external physical parameters, published models, or public datasets such as HITRAN line data and real pollution concentration records.

## Critical calibration qualification

When summarizing favorable payload recall or detection limits, state the residual calibration assumption alongside the result. The ideal benchmark assumes zero residual calibration error after correction; this accuracy has not been demonstrated experimentally. Retain the distinction between predicted recall, simulated empirical recall and measured field performance. Read `docs/46_critical_calibration_assumption.md` for the saved comparison and exact conditions before reusing headline results.

