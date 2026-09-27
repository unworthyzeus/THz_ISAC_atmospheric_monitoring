"""Visible input provenance on the method slide of each original task."""

TASK_SOURCES = {
    6: ('1.1', [
        'NOAA IGRA: Beijing CHM00054511.',
        '2026 snapshot: 521 soundings.',
        '1 January profile in the current grid.',
        'Jan/Apr/Jul/Sep in earlier checks.',
        'Used for pressure, T and humidity.',
        'ITU P.835 supplies the standard case.',
        'VOC/PM vertical profiles are assumed.',
    ]),
    8: ('1.2', [
        'HITRAN2024, acquired via HAPI.',
        '319,001 lines, 25 isotope tables.',
        'Acquisition window: 0–3000 GHz.',
        'Five VOC targets + four interferents.',
        'Line strength, width, shift and energy',
        'feed the local absorption profiles.',
        'HAPI supplies masses and partition sums.',
    ]),
    10: ('1.3', [
        'HITRAN: the same nine-gas line pool.',
        'ITU P.676: oxygen/water background.',
        'ITU / January IGRA atmospheric states.',
        'Used in layerwise slant integration.',
        'Water paper, Fig. 8, 380.197 GHz:',
        'published slopes are a separate check.',
        'No measured atmospheric THz paths.',
    ]),
    12: ('1.4', [
        'Inputs: assumed aerosol properties.',
        'Fine 0.03–2.5 µm; coarse 2.5–10 µm.',
        'Density and refractive index shown above.',
        'Used for mass-normalized extinction.',
        'Calcite: 8 sample + 4 blank recordings.',
        'Separate transmission check only:',
        'no measured PM mass or size labels.',
    ]),
    14: ('2.1', [
        'ITU P.676: background and sky emission.',
        'Task 1: HITRAN / IGRA propagation.',
        '550 km, 23 dBm, 6 dB NF: scenarios.',
        'Used to compute SNR and time budgets.',
        'No measured RF chain dataset is used.',
        'Power, noise and settling are requirements.',
    ]),
    16: ('2.2', [
        'Physics: Task 1. Receiver: Task 2.1.',
        'Generated QPSK/OFDM observations.',
        '16 raw frames: one per chosen block.',
        'Used for timing and decoded-bit checks.',
        'Recall trials use simulated moments.',
        'No downloaded or measured CSI set.',
    ]),
    18: ('3.1', [
        'Five target + four interfering gases.',
        'HITRAN signatures and two PM modes.',
        'Standard atmosphere selects 16 bands.',
        'January IGRA checks weather transfer.',
        'Used to build the joint inverse model.',
        'No measured training labels are used.',
    ]),
    20: ('3.2', [
        'Generated QPSK moments, not field CSI.',
        '10,000 trials per null/positive class.',
        'Five VOC scenarios + PM mass controls.',
        'HITRAN/IGRA define the forward model.',
        'Used to estimate recall and mass error.',
        'Earlier three-gas controls stay separate.',
    ]),
    23: ('4.1', [
        'Analytical QPSK / magnitude likelihood.',
        'Unknown signal, noise and reference.',
        'Historical three-gas physical model.',
        'Used for Fisher bounds and efficiency.',
        'No independent measured dataset.',
        '20 s, zero extra residual: benchmark.',
    ]),
    25: ('4.2', [
        'HITRAN gas signatures and PM model.',
        'ITU standard + January IGRA profile.',
        '288 settings; 8 outputs; 2,304 rows.',
        'Time 2/20/100 s, residual 0–0.001 dB.',
        'Used for the common sensitivity grid.',
        'These are generated model outputs.',
    ]),
    28: ('4.3', [
        'Current positive/null response trials.',
        '480 retained percentage/error rows.',
        'Used for limits, recall and intervals.',
        'WHO 2021 PM levels: comparison only.',
        '15/45 µg/m³: declared PM controls.',
        'No field compliance dataset is available.',
    ]),
}


def attach_task_sources(slides):
    for index, (task, lines) in TASK_SOURCES.items():
        slide = slides[index - 1]
        assert slide['title'].startswith(f'Task {task} '), (index, task)
        slide['task_data'] = '\n'.join(lines)
        slide['sources'].append('docs/53_dataset_subsets_and_roles.md')
    # Current inputs belong on the method slide; historical catalog totals stay in the appendix discussion.
    slides[7]['detail'] = [
        ['Current target gases', '5'], ['Interfering gases', '4'],
        ['Current isotope tables', '25'], ['Current acquired lines', '319,001'],
    ]
