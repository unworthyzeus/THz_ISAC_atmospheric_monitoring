"""Append dataset provenance without changing original task or formula slide numbers."""
import json


def append_dataset_slides(add, slides, root):
    ledger = json.loads((root / 'results/presentation_source_audit/dataset_subsets.json').read_text(encoding='utf-8'))
    provenance = 'docs/53_dataset_subsets_and_roles.md'
    spec = ledger['spectroscopy']
    rows = [['Gas and role', 'HITRAN isotope IDs', 'Acquired lines, 0–3000 GHz', 'Centres in 220–330 GHz']]
    for i, r in enumerate(spec['records']):
        rows.append([r['molecule'] + (' · target' if i < 5 else ' · interferent'),
                     ', '.join(map(str, r['isotopologue_ids'])),
                     f"{r['acquired_lines']:,}", f"{r['centres_220_330_ghz']:,}"])
    add('Datasets · Exact HITRAN subset in the current receiver', table=rows,
        widths=[350,300,430,376], kind='dense',
        subtitle='HITRAN2024 via HAPI. The current nine gases use two retained input tables and isotope-specific profiles.',
        limit='All acquired line wings enter the calculation. H₂O/O₂ background uses ITU-R P.676; these are parameters, not measured radio data.',
        notes='Input file hashes were checked against the current physics manifest. The two pools contain 287,737 and 31,264 rows. The molecular cross section function uses no wing cutoff by default. Centre counts in 220–330 GHz are descriptive and do not define a filter. HITRAN supplies line positions, strengths, air broadening, lower state energy, temperature exponents and pressure shifts. HAPI provides isotope masses and TIPS partition sums. Earlier 34-table acquisition totals belong to a broader historical catalog.',
        sources=[provenance, 'results/presentation_source_audit/dataset_subsets.json', 'results/payload_bounds/spectroscopy_acquisition.json', 'results/receiver_design/voc_pm_extension/acquisition.json', 'scripts/joint_receiver_support.py', 'src/thz_isac/physical_spectroscopy.py', 'https://hitran.org'])
    slides[-1]['detail'] = [['Acquired line pool',f"{spec['acquired_line_count']:,}"],['Isotope tables',str(spec['isotope_table_count'])],['Centres in receiver window',f"{spec['centre_count_220_330_ghz']:,}"]]

    weather = ledger['weather']
    rows = [['Sounding, UTC', 'Measured levels', 'Measured top above station', 'Where it was used']]
    for r in weather['selected']:
        month = r['datetime'][5:7]
        rows.append([r['datetime'][:10]+' 00:00',str(r['measured_levels']),f"{r['measured_top_m']/1000:.2f} km",'Current global grid and earlier tests' if month == '01' else 'Earlier seasonal sensitivity tests'])
    add('Datasets · NOAA IGRA weather profiles actually used',table=rows,
        widths=[320,230,380,526],
        subtitle='Beijing station CHM00054511, 2026 year to date archive acquired on 23 September 2026.',
        result='Current global comparisons use the January sounding and the ITU standard atmosphere.',
        limit='Measured weather provides no VOC/PM concentration labels. Above the measured top, the atmosphere is extended by a model to 100 km.',
        notes='The retained parser output contains 103,322 levels across 521 soundings. The declared selection was the first complete sounding reaching at least 20 km in January, April, July and September, before spectroscopy evaluation. Temperature, pressure and water profiles drive propagation. A model continues above the measured profile. The current receiver uses January as a weather check; band selection uses the standard atmosphere. The archive is a frozen year to date snapshot, not a complete year or global weather sample.',
        sources=[provenance,'results/task_completion/weather_selection.json','results/task_completion/source_acquisition.json','scripts/receiver_design_physics.py',weather['source']])
    slides[-1]['detail']=[['Retained levels','103,322'],['Retained soundings','521'],['Selected profiles','4 earlier / 1 current']]

    add('Datasets · Independent water and aerosol checks',table=[
        ['Source','Exact part used','What was checked','Important boundary'],
        ['Water vapour paper (2023)\nScientific Reports, Figure 8','Figure 8 aggregate slopes at 380.197353 GHz: VNA 0.033 ± 0.009 and TDS 0.027 ± 0.009','Absorption slope in (dB/m)/(g/m³), compared with declared model states','Published aggregates only. No raw measurement series or VOC labels.'],
        ['Calcite THz-TDS\nDOI 10.57745/DLJEFW, v1.0','8 sample and 4 blank recordings, 1 m path. Four native bins near 300, 325, 350 and 375 GHz.','Native FFT transmission with before/after blanks. 64 transmission rows.','No mass concentration or size labels. Cannot calibrate PM mass extinction.'],
    ], widths=[345,475,320,316],
        subtitle='These are external physical checks. Neither dataset supplies the current five VOC and PM recall labels.',
        limit='Calcite reference RMS difference is 0.0472 dB. This is a separate laboratory diagnostic, not the current receiver’s calibration covariance.',
        notes='Calcite particles were resuspended in dry nitrogen. All 12 recordings were analyzed with native FFT resolution around 25 GHz and no synthetic frequency refinement. Two blanks per reference phase were combined geometrically. Published calcite data have no concentration or size distribution labels. Water slopes are copied from the retained Figure 8 audit; their reported plus/minus values are not reinterpreted as confidence intervals. VNA comparison lies within the reported range, while the mean TDS comparison does not.',
        sources=[provenance,'results/five_task_closure/published_water_validation.json','results/five_task_closure/calcite_validation.json','https://doi.org/10.1038/s41598-023-47586-8','https://doi.org/10.57745/DLJEFW'])
    slides[-1]['detail']=[['Calcite observations','8 samples + 4 blanks'],['Native frequency resolution','About 25 GHz'],['Paired PM mass truth','Unavailable']]

    add('Datasets · Earlier Beijing benchmark and its filters',table=[
        ['Stage','Exact retained subset or procedure'],
        ['UCI Beijing Multi Site Air Quality','DOI 10.24432/C5RK5G. 12 sites, 1 March 2013 to 28 February 2017.'],
        ['Raw measurements','420,768 station hours. Six pollutants: CO, O₃, SO₂, NO₂, PM2.5 and PM10.'],
        ['Complete case filter','383,585 rows with required pollutants, temperature, pressure, dew point, rain and wind speed.'],
        ['Particle consistency filter','Removed 17,642 rows where PM10 < PM2.5. Retained 365,943 physically ordered rows.'],
        ['Modeling sample','Sort by timestamp and station. Select 20,000 deterministic evenly spaced rows.'],
        ['Chronological evaluation','12,000 train / 4,000 validation / 4,000 test. Normalize by the training Q95 − Q05 span.'],
    ],widths=[355,1101],kind='dense',
        subtitle='Historical pollution inversion and ground sensor branches. These rows do not label the current five VOC recall experiments.',
        limit='Beijing concentrations are measured. The atmospheric THz spectra generated from them are simulated; later work reused the known test period.',
        notes='This slide describes the principal physically filtered Beijing benchmark contract documented in the historical data provenance audit. The original cleaner excludes source wind direction. Complete case filtering may bias station and episode representation. Ground sensor forecasting and artificial channel masking are separate tasks from THz inversion. The current five VOC experiment uses controlled concentration scenarios, not these six pollutant rows.',
        sources=[provenance,'docs/35_data_provenance_and_synthetic_evidence_audit.md','scripts/download_external_data.py','https://doi.org/10.24432/C5RK5G'])
    slides[-1]['detail']=[['Complete case retention','91.163%'],['Physically ordered rows','365,943'],['Scored modeling sample','20,000']]

    add('Datasets · Other historical controls and unused sources',table=[
        ['Source / branch','Part actually used','Role and evidence boundary'],
        ['ESA CCI CO and NO₂ columns','March–December 2013, ten paired monthly rows. Grid centre 39.5° N, 116.5° E.','IASI/MOPITT CO total columns and OMI NO₂ tropospheric columns. Retrievals used for modeled feasibility.'],
        ['Mendeley protein THz-TDS\nDOI 10.17632/dpw4svmdr8.1','Fig3.csv: 7 lysozyme levels. Fig4.csv: 6 ovalbumin levels. Five bins from 0.9 to 1.3 THz.','Laboratory concentration control. Means and SDs only, with one concentration level held out at a time.'],
        ['UCI Air Quality, Italy\nDOI 10.24432/C59K5F','6,941 complete rows after removing −200 missing values. Split 4,164 / 1,388 / 1,389.','Four analyzer targets, five metal oxide sensors and weather. Earlier field calibration task, not THz.'],
        ['NASA Aura MLS','Metadata resolved; no granules acquired or scored.','Investigated option only. It must not be counted as an evaluated measurement dataset.'],
    ],widths=[365,545,546],kind='dense',
        subtitle='These sources support separate controls and historical studies, not a measured atmospheric VOC/PM receiver demonstration.',
        limit='The Italian branch has a weaker reproduction record. WHO and ITU documents supply benchmarks or models, rather than observation datasets.',
        notes='ESA extraction used 20 files, two species across ten months, with quality and coordinate checks. Mendeley acquisition downloaded ten files but only Fig3.csv and Fig4.csv fed the reported concentration score; no pseudo replicates were generated. The Italian source contains 9,358 raw hourly rows from March 2004 to February 2005, in an unnamed city, but the detailed historical audit reports no dedicated committed downloader or scoring manifest for that branch. Source and branch limitations are preserved.',
        sources=[provenance,'docs/35_data_provenance_and_synthetic_evidence_audit.md','results/tables/real_column_feasibility_manifest.json','results/tables/measured_thz_control_manifest.json','https://doi.org/10.17632/dpw4svmdr8.1','https://doi.org/10.24432/C59K5F'])
    slides[-1]['detail']=[['ESA extract','10 months / 20 files'],['Protein files scored','2 of 10 downloaded'],['Current paired radio / truth set','None']]
