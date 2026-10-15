# Chemical absorption in h(f, l): restart

The active research scope was reset on **October 14, 2026**. Start with **CO**, frequencies from **60 to 1000 GHz**, multiple atmospheric path lengths, and **no receiver noise**.

The immediate question for the supervisor meeting is: **How can we observe chemical attenuation a_c in the channel h(f, l), and what information separates it from the background atmosphere?**

Read the [new foundations and meeting brief](docs/59_restart_observability_2026_10_14.md). It derives the reference ratio, explains why absorption lines are continuous, distinguishes path length from cloud thickness, and states the conditions for unique separation.

The meeting presentation is available as an [editable PowerPoint](output/presentations/co_observability_editorial_v2.pptx) and a [reading PDF](output/presentations/co_observability_editorial_v2.pdf). Its 14 slides use a new ivory, charcoal and copper design. The [presenter notes](output/presentations/co_observability_presenter_notes.md) contain the assumptions, derivations and source links. See the [presentation record](docs/60_co_observability_presentation.md) for the content scope and reproduction steps.

A [concise English speaking script](output/pdf/co_observability_speaking_script.pdf) gives a few spoken sentences for each slide, including the reference equation and its meaning.

With a matched atmospheric reference, chemical optical depth follows from `tau_c = -2 ln(|h| / |h_0|)`. Without a reference or constraints on the atmosphere, its factor and the chemical factor cannot be uniquely separated. Zero receiver noise does not remove this ambiguity.

The [first CO example](scripts/restart_co_observability.py) uses fresh HITRAN line parameters, JPL line centers and an ITU P.676 background. It provides:

- A [frequency and length figure](results/restart_2026_10_14/co_observability.png), with an [exportable PDF](results/restart_2026_10_14/co_observability.pdf).
- A [path length figure](results/restart_2026_10_14/co_path_length.png) showing that chemical loss stops increasing after the entire cloud is crossed.
- The [channel matrices](results/restart_2026_10_14/channel_matrices.npz), [line examples](results/restart_2026_10_14/co_line_examples.csv) and [source hashes and verification](results/restart_2026_10_14/manifest.json).

Run `python scripts/restart_co_observability.py` from this directory. Required packages are NumPy, SciPy and Matplotlib; HAPI is needed to download the source if the saved line file is missing.

These are conditional model calculations with exact atmosphere and calibration. They verify the inversion and explain the physics; they establish neither measured performance nor a practical detection limit.

Next, specify how the reference would be obtained and which atmospheric quantities are known, then test CO with uncertain atmospheric parameters. Other gases follow individually, then mixtures. Angular dependence is a later extension.

The previous task lists and results are superseded as the active plan. The [historical README](HISTORY_before_restart_2026_10_14.md) preserves their original context and links. They are not completion criteria or evidence of performance for this new study.
