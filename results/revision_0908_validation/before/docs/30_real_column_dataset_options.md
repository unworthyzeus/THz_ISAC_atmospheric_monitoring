# Real Atmospheric Column Dataset Options

## Purpose

This note records the search for real path integrated atmospheric gas datasets that can replace the current conversion from surface concentration to an assumed vertical profile. It documents what was checked, why each source matters, which access paths worked, which paths require credentials, which proposed matches are invalid, and what should be tested next.

The immediate scientific objective is a column based positive control for CO and NO2. Satellite columns are much closer to the quantity sensed along a long atmospheric path than a road or surface station concentration. They are still retrieval products, not direct truth, and there is no paired measured sub THz CSI in any source reviewed here.

## Scope Correction

The current repository uses the [UCI Beijing Multi Site Air Quality dataset](https://archive.ics.uci.edu/dataset/501/beijingmultisiteairqualitydata), not the older Italian UCI Air Quality dataset.

| UCI source | Official period | Official location description | Consequence |
| --- | --- | --- | --- |
| Beijing Multi Site Air Quality, DOI `10.24432/C5RK5G` | 2013 03 01 to 2017 02 28 | 12 named monitoring sites in Beijing | This is the period and city relevant to the current repository. |
| [Air Quality, DOI `10.24432/C59K5F`](https://archive.ics.uci.edu/dataset/360/air%2Bquality) | March 2004 to February 2005 | A polluted road level site within an Italian city | UCI does not identify the city or publish a coordinate on the official record. It cannot be assigned to Milan or Lombardy without another primary source. |

Therefore:

1. A Milan satellite cell must not be joined to the Italian UCI record as if it were colocated.
2. Sentinel 5P does not overlap either UCI period.
3. The best immediate column experiment should use Beijing from 2013 to 2017.
4. The 2004 to 2005 options below are preserved only for a separate historical experiment or if the Italian site can later be geolocated from a primary source.

## Executive Decision

The best credential free pair for the current Beijing experiment is:

1. ESA CCI merged IASI and MOPITT monthly total CO columns on a 1 degree grid.
2. ESA CCI OMI monthly tropospheric NO2 columns on a 1 degree grid.

Both cover the full 48 month UCI Beijing period. Both are measurement derived satellite products. The CO record provides daytime and nighttime columns, uncertainties, and source flags. The NO2 record provides realistic Level 3 uncertainty information and averaging kernels. Matching their 1 degree grids avoids an unnecessary spatial regridding step.

The smallest verified parser smoke test is one March 2013 CO file plus one coarse March 2013 NO2 file. Their combined transfer size is 5,815,347 bytes. The science run should then use the 1 degree NO2 files so that CO and NO2 share the same nominal grid.

| Source | Quantity | Coverage | Resolution | Access | Decision |
| --- | --- | --- | --- | --- | --- |
| ESA CCI merged IASI and MOPITT CO | Total CO column | 2008 01 to 2024 12 | 1 degree, monthly | Anonymous direct NetCDF | Use for Beijing CO. |
| ESA CCI OMI NO2 | Tropospheric NO2 column | 2004 10 to 2021 03 | 0.2, 0.5, 1, and 2 by 2.5 degree, monthly | Anonymous direct NetCDF | Use the 1 degree files for Beijing NO2. |
| TEMIS QA4ECV OMI NO2 | Tropospheric NO2 column | 2004 10 to 2021 03 | Monthly global grid | Anonymous compressed ASCII | Useful lightweight cross check. |
| TEMIS QA4ECV SCIAMACHY NO2 | Tropospheric NO2 column | 2002 08 to 2012 04 | Monthly global grid | Anonymous compressed ASCII | Historical NO2 option with full Italian UCI period overlap. |
| NASA MOPITT V10 | CO profile and total column | 2000 03 to 2025 02 | 1 degree, daily or monthly | Free Earthdata Login required | Historical CO option with full Italian UCI period overlap. |
| CAMS EAC4 | CO and NO2 at surface, model levels, and total column | 2003 to 2025 | 0.75 degree, 3 hourly | Free ADS registration, licence acceptance, and API token required | Best profile bridge, but it is a reanalysis rather than an independent retrieval. |
| Sentinel 5P TROPOMI | CO total column and NO2 vertical column | Routine operations from 2018 | Level 2 orbit products | Copernicus Data Space registration and token required | Modern independent case only. No UCI overlap. |

## Option 1: ESA CCI Merged CO for Beijing

### What it is

The [CEDA catalogue record](https://catalogue.ceda.ac.uk/uuid/6242532d87d442a3acf0171d35c02e56/) describes a monthly Level 3 CO climate data record made by merging IASI on Metop A, B, and C with MOPITT V9T on Terra. It covers January 2008 through December 2024 on a 1 degree grid.

The record contains:

1. Daytime and nighttime total CO columns in molecules per square centimetre.
2. Column uncertainty fields.
3. Source flags that distinguish IASI only, MOPITT only, and merged cells.
4. Surface altitude and coordinate fields.

The catalogue explicitly says that registered and nonregistered users can access the public data. The complete archive is 416 MB in 205 files, with an average file size of 2.0 MB.

### Exact anonymous access

Archive browser:

[CEDA merged CO version 1.0 archive](https://data.ceda.ac.uk/neodc/esacci/precursors/data/MERGED_CO/v1.0)

Example March 2013 file:

[ESACCI merged CO, March 2013](https://dap.ceda.ac.uk/neodc/esacci/precursors/data/MERGED_CO/v1.0/2013/ESACCI-PREC-L3S-CO-IASI_MOPITT_MERGED_LATMOS-180x360_1M-201303-fv1.0.nc)

Anonymous HTTP metadata check on 2026 07 15:

| Field | Result |
| --- | --- |
| HTTP status | `200 OK` |
| Content type | `application/octet-stream` |
| Content length | `2,139,175` bytes |
| Authentication | Not required |

The year and month in the directory and filename can be changed reproducibly. The 2013 through February 2017 files cover the complete current UCI period.

### Why it is useful

This record supplies real monthly CO column variation without converting a Beijing surface measurement through an assumed 1,500 m scale height. It is also small enough to pin locally with hashes and include in a reproducible acquisition manifest.

### Limitations

1. A 1 degree cell is much larger than an individual urban station footprint.
2. Monthly aggregation removes hourly and daily variation in UCI.
3. The merged retrieval has instrument dependent sampling and sensitivity.
4. It is a total column, while the present pollutant model truncates integration at 12 km.
5. Its uncertainty and source flag fields must be propagated rather than discarded.

## Option 2: OMI NO2 for Beijing

### Preferred 1 degree NetCDF record

The [ESA CCI OMI Level 3 page](https://www.temis.nl/airpollution/no2col/cci-no2-omi.php) provides monthly mean tropospheric NO2 column files from October 2004 through March 2021 at four resolutions. The record is produced by KNMI in the ESA CCI Precursors project and has DOI [10.21944/cci-no2-omi-l3](https://doi.org/10.21944/cci-no2-omi-l3).

The [QA4ECV product specification](https://temis.nl/qa4ecv/no2col/QA4ECV_NO2_PSD_v1.1.compressed.pdf) defines the main quantity as the vertically integrated number of NO2 molecules between the surface and the tropopause per unit area. NO2 column density is reported in molecules per square centimetre.

Example March 2013 files:

| Role | Resolution | Direct file | Verified size |
| --- | --- | --- | ---: |
| Parser smoke test | 2 by 2.5 degree | [March 2013 coarse OMI NO2](https://d1qb6yzwaaq4he.cloudfront.net/airpollution/no2col/cci-no2/omi/2013/ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-0091x0144_1M-201303-fv1.0.nc) | 3,676,172 bytes |
| Science grid | 1 degree | [March 2013 one degree OMI NO2](https://d1qb6yzwaaq4he.cloudfront.net/airpollution/no2col/cci-no2/omi/2013/ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-0180x0360_1M-201303-fv1.0.nc) | 17,275,824 bytes |

Anonymous HTTP metadata checks returned `200 OK` and `application/x-netcdf` for both files. No account or token was required.

The coarse file is only for confirming the parser, coordinate orientation, missing values, units, and variable names. It is too coarse for the main Beijing analysis. The 1 degree version should be used with the 1 degree CO record.

### Lightweight QA4ECV ASCII alternative

TEMIS also exposes the monthly QA4ECV product as compressed TOMS format and ESRI grid format files. The [March 2013 OMI query page](https://www.temis.nl/airpollution/no2col/no2regioomimonth_qa.php?Region=8&Year=2013&Month=03) resolves to:

[QA4ECV OMI NO2 compressed ASCII, March 2013](https://d1qb6yzwaaq4he.cloudfront.net/qa4ecv/omi/v1/2013/03/no2_201303.asc.gz)

Verified anonymous response:

| Field | Result |
| --- | --- |
| HTTP status | `200 OK` |
| Content length | `3,464,499` bytes |
| Authentication | Not required |

This format is useful as an independent parser cross check. The NetCDF CCI record remains preferable because it carries richer uncertainty and averaging information.

### Limitations

1. The record is a tropospheric vertical column, not a surface concentration.
2. Clouds and OMI sampling affect the monthly mean.
3. Satellite averaging kernels and the a priori profile influence the retrieved column.
4. The OMI overpass samples only part of the diurnal pollution cycle.
5. A 1 degree monthly value cannot validate station hour variation.

## Option 3: CAMS EAC4 as a Profile Bridge

The [CAMS global reanalysis EAC4 catalogue](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=overview) covers 2003 onward at 0.75 degree horizontal resolution and 3 hour temporal resolution. It provides surface, total column, pressure level, and model level fields.

Relevant variables include:

1. Carbon monoxide in mass mixing ratio.
2. Nitrogen dioxide in mass mixing ratio.
3. Total column carbon monoxide in kilograms per square metre.
4. Total column nitrogen dioxide in kilograms per square metre.
5. Temperature, pressure, humidity, and meteorological fields needed by the layered spectroscopy model.

### Access constraint

Download is not anonymous. The [ADS terms](https://ads.atmosphere.copernicus.eu/disclaimer-privacy) require prior registration. The [official API setup](https://ads.atmosphere.copernicus.eu/how-to-api) requires a personal access token and manual acceptance of the dataset licence before the API request will run.

The exact dataset short name is:

```text
cams-global-reanalysis-eac4
```

The official workflow is to select the variables, dates, times, levels, and area in the download form, then copy the generated API request. That is safer than preserving an invented request schema in this note because the current data store validates the selectable fields dynamically.

### Why it is useful

EAC4 is the only reviewed source that can supply column, surface, and vertical profile information for the same time and grid. It can therefore test the present fixed scale height assumption and provide realistic pressure, temperature, and humidity profiles.

### Why it is not independent truth

EAC4 is a model and data assimilation product. Its values depend on the atmospheric model, emissions, assimilated observations, and the changing observing system. It is appropriate as a profile bridge and sensitivity input, not as an independent field validation of the THz inversion.

## Historical 2004 to 2005 Options

These options address the older Italian UCI period. They do not establish that the site was in Milan.

### NO2 with SCIAMACHY

The [TEMIS NO2 archive](https://www.temis.nl/airpollution/no2.php) provides QA4ECV version 1.1 SCIAMACHY columns from August 2002 through April 2012. This fully covers March 2004 through February 2005.

Example March 2004 monthly file:

[SCIAMACHY QA4ECV NO2 compressed ASCII, March 2004](https://d1qb6yzwaaq4he.cloudfront.net/qa4ecv/scia/v1.1/2004/03/no2_200403.asc.gz)

Verified anonymous response:

| Field | Result |
| --- | --- |
| HTTP status | `200 OK` |
| Content length | `3,269,606` bytes |
| Authentication | Not required |

This is the smallest verified credential free observational NO2 route with full temporal overlap. Its spatial footprint and monthly aggregation are still much coarser than a roadside reference analyser.

### NO2 with OMI

OMI begins on 2004 10 01, so it overlaps only October 2004 through February 2005. It is useful as a partial cross sensor check against SCIAMACHY, not as a complete one year record.

The anonymous ESA CCI 1 degree October 2004 file is:

[OMI NO2 one degree NetCDF, October 2004](https://d1qb6yzwaaq4he.cloudfront.net/airpollution/no2col/cci-no2/omi/2004/ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-0180x0360_1M-200410-fv1.0.nc)

It returned `200 OK` with a verified content length of `17,281,776` bytes.

For higher temporal resolution, NASA provides [OMNO2d version 4](https://disc.gsfc.nasa.gov/datacollection/OMNO2d_004.html), a daily 0.25 degree global product with total and tropospheric columns. Numeric downloads and subsetting require a free Earthdata Login.

### CO with MOPITT V10

The [NASA MOP03JM V10 record](https://asdc.larc.nasa.gov/project/MOPITT/MOP03JM_10) provides monthly gridded joint near infrared and thermal infrared CO profiles and total columns from 2000 03 03 through 2025 02 01. It fully overlaps the Italian UCI period.

The official DOI is [10.5067/TERRA/MOPITT/MOP03JM_L3.010](https://doi.org/10.5067/TERRA/MOPITT/MOP03JM_L3.010).

NASA CMR metadata discovery is anonymous, but the data objects are protected. A March 2004 metadata query returned:

```text
https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C4191539031-LARC_CLOUD&temporal=2004-03-01T00:00:00Z,2004-04-01T00:00:00Z&page_size=5
```

```text
MOP03JM-200403-L3V98.0.3.he5
153.01515007019043 MB
https://data.asdc.earthdata.nasa.gov/asdc-prod-protected/MOPITT/MOP03JM.10/2004.03/MOP03JM-200403-L3V98.0.3.he5
```

The [Earthdata access documentation](https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget) confirms that scripted downloads require an Earthdata Login and application authorization. No current credential free MOPITT CO data route for 2004 was found.

### CAMS EAC4

EAC4 starts in 2003 and therefore covers the complete Italian period for both total column CO and total column NO2. It has better temporal resolution than the monthly satellite products, but it requires an ADS account and remains a reanalysis.

## Why Sentinel 5P Is Not a Matched Dataset

Sentinel 5P was launched on 2017 10 13. The [ESA first public Level 2 release](https://sentinels.copernicus.eu/-/first-set-of-sentinel-5p-products-released-on-the-sentinel-5p-pre-operations-data-hub) states that qualified offline Level 2 products were available from 2018 06 28. The public products include:

```text
L2__CO____
L2__NO2___
```

It therefore has zero overlap with:

1. UCI Beijing, 2013 03 through 2017 02.
2. UCI Italian Air Quality, 2004 03 through 2005 02.

The [Copernicus Data Space OData documentation](https://documentation.dataspace.copernicus.eu/APIs/OData.html) allows catalogue search but requires an authorization token to download products. The [Sentinel Hub Level 2 documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S5PL2.html) can return a spatial subset, but its Process API also requires OAuth authentication.

TROPOMI remains valuable for a separate modern demonstration over Milan or Beijing. Such a demonstration must use a geolocated modern ground or profile dataset and must be presented as a different experiment, not as validation against either UCI record.

## What Worked

1. The CEDA CO catalogue, archive listing, and March 2013 NetCDF object were accessible anonymously.
2. The ESA CCI OMI NO2 catalogue and both coarse and 1 degree March 2013 NetCDF objects were accessible anonymously.
3. The TEMIS QA4ECV OMI and SCIAMACHY monthly compressed ASCII objects were accessible anonymously.
4. NASA CMR returned MOPITT V10 collection and granule metadata without credentials.
5. CAMS EAC4 exposes both target total columns and the vertical profile variables needed to test the assumed scale height.
6. Official records establish exact temporal coverage and make the Sentinel mismatch unambiguous.

## What Failed or Remains Blocked

1. Direct MOPITT numeric download is protected by Earthdata Login.
2. CAMS EAC4 download requires ADS registration, licence acceptance, and a personal token.
3. Copernicus Data Space product download requires an authorization token.
4. The public NASA AVDC directory examined for OMI Level 3 exposed derived images, not a credential free numeric replacement for the protected current GES DISC product.
5. No official UCI record identifies the Italian city as Milan or supplies a site coordinate.
6. No reviewed source contains measured sub THz CSI paired with these columns.
7. No satellite gas product supplies a direct PM2.5 or PM10 mass column equivalent to the UCI surface targets. Aerosol optical products would require a separate aerosol inversion and should not be relabelled as PM mass.

## Scientific Use in the THz Pipeline

The new column data should not be inserted into the current model as if they were surface concentrations. That would retain the same mismatch under different units.

The forward model should instead:

1. Read a measured column in molecules per square centimetre.
2. Choose a declared vertical shape from CAMS, a bounded profile family, or the current exponential profile only as a sensitivity case.
3. Normalize the vertical shape so that its integral equals the measured column.
4. Evaluate pressure and temperature dependent HITRAN absorption by layer.
5. Report retrieval error in column units.
6. Compare the CRB and empirical error with the real observed column spread and retrieval uncertainty, not with a WHO surface concentration guideline.

For CO, the total atmospheric domain must be reconciled with the present 12 km model top. For NO2, the tropospheric definition should be retained. A common column domain must be declared before a joint CO and NO2 result is interpreted.

## Risks

1. Satellite columns are retrievals with averaging kernels and a priori dependence.
2. Cloud filtering creates nonrandom temporal sampling.
3. Monthly 1 degree fields cannot resolve road level or station hour variation.
4. CO total column and NO2 tropospheric column do not have identical vertical domains.
5. Real column variation can still be too small for the declared THz link.
6. A positive result generated from a real column label and simulated THz observation remains a simulated sensing result.
7. EAC4 can reduce profile uncertainty but cannot serve as independent validation if it also supplies the target column.

## Recommended Next Actions

1. Download the March 2013 CEDA CO file and coarse ESA CCI OMI NO2 file as a parser smoke test.
2. Record URL, DOI, byte size, SHA256, variables, units, fill values, coordinates, and licence in the acquisition manifest.
3. Replace the coarse NO2 file with the 1 degree version for the science run.
4. Acquire all monthly files from 2013 03 through 2017 02 for the Beijing column experiment.
5. Extract a documented Beijing grid cell or bounded regional mean. Do not silently copy the UCI station labels onto the satellite grid.
6. Implement the column normalized layered forward model and rerun Fisher bounds for CO and NO2.
7. Use the real monthly column distribution as a positive control and compare error with the observed interquartile range and satellite retrieval uncertainty.
8. If credentials are available, add EAC4 profiles for the same grid and dates to test vertical profile sensitivity.
9. Keep Sentinel 5P as a later modern external case. Do not use it to claim temporal validation of the current UCI experiment.

## Result

A practical real column experiment is available without credentials for the actual Beijing period. It can begin with less than 20 MB of data and expand to the complete 48 month record. This removes the largest current target mismatch, but it does not solve the sensing problem by itself. The next result must show whether physically calibrated THz attenuation can resolve the variation present in these real columns under the declared link and uncertainty model.
