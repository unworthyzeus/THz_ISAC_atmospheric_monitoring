# Supervisor revision: geometry, hardware, bandwidth and the first detection example

5 October 2026. The repository was clean and `git pull --ff-only` reported that `main` was already current at `7b72b62`. This revision adds a new, deliberately simple calculation; previous experiment snapshots retain their original assumptions.

**LEO links are a useful running example for all parts of this study:** propagation geometry, atmospheric spectroscopy, transmitter and receiver budgets, antenna dimensions, OFDM, Doppler, observation time, detection and the future use of several receivers. The inference framework also applies to terrestrial and UAV links after changing their geometry and hardware. The LEO example does not imply that every frequency, pollutant or proposed payload is feasible.

Start with the [intuitive and mathematical single compound walkthrough](55_zenith_single_compound_walkthrough.md). Its 90° snapshot uses 10 GHz instantaneous bandwidth and acetonitrile. With **20 s total reference plus sample and an assumed, unmeasured 0.001 dB differential calibration residual**, the predicted 95% detection concentration is **50.58 µg/m³**. The corresponding simulated response is **94.75%**, with a 95% binomial interval of 94.29–95.18%. Detection at 1 µg/m³ fails: its simulated response is 1.31%, close to the 1% nominal false alarm probability. This is conditional computational evidence, not a measured atmospheric sensor result.

## Response to each note

| Supervisor note | Revision and evidence | Remaining boundary |
| --- | --- | --- |
| Check the maximum angle, height and coverage | Ground elevation has maximum 90°; 30° is a possible minimum mask. Spherical coverage is evaluated at 400, 550 and 800 km. | An actual pass need not reach zenith. A visibility cap is different from an antenna footprint. |
| Revise PM, retain VOC | Separate particulate absorption, scattering, aerodynamic size and composition. Recompute full Mie diagnostics and reject useful PM mass retrieval in this example. | Optical properties and size distributions remain assumed. |
| More transmitter power | Compare 17, 23, 25, 26, 30 and 40 dBm with fixed total bandwidth and apertures. Hardware references distinguish RF output, peak power and electrical consumption. | A 1 W or 10 W linear space transmitter at 235 GHz has not been established by these sources. |
| Check antenna gain, receiver and dimensions | Derive gains from aperture dimensions; report beamwidth, footprint and surface precision. Compare receiver noise figures. | Efficiency, pointing, backoff and noise remain requirements for this receiver. |
| Check operation near 400 GHz | Retain the 60–400 GHz research range, start near 235 GHz, and calculate background attenuation at selected frequencies. | The 235 GHz hardware evidence cannot be transferred to 400 GHz. |
| Use roughly 10 GHz bandwidth | New contiguous 230–240 GHz example with 1024 tones and total power split across them. | This is a proposed waveform, not a demonstrated complete modem or an authorized spectrum plan. |
| Check OFDM spacing | Evaluate 256, 512, 1024 and 2048 tones at the same 10 GHz and power; show CP and residual frequency offset tradeoffs. | A global optimum requires measured phase noise, delay spread and acquisition performance. |
| Begin at 90°, one compound, intuitively then mathematically | Explicit channel matrix, pilot counts, reference subtraction, covariance, nuisance matrix, estimator, threshold and saved observations. | Known vertical shape and matched background; one selected molecule; ideal tracking. |
| Future molecular scattering and multistatic 3D sensing | Off resonance nitrogen scattering screen and a voxel/path formulation below. | No demonstrated molecular echo receiver or validated 3D reconstruction. |

## Elevation, orbit and coverage

Let $e$ denote ground elevation above the horizon, $R$ Earth radius, $h$ satellite height and $\psi$ the angle at Earth's centre from the station to the subsatellite point. A straight ray over a spherical Earth gives

$$
d(e)=\sqrt{(R+h)^2-R^2\cos^2 e}-R\sin e,
\quad \psi(e)=\cos^{-1}\!\left(\frac{R}{R+h}\cos e\right)-e.
$$

The ground arc radius is $R\psi$; the visible cap above a minimum elevation is $2\pi R^2(1-\cos\psi)$. Satellite off nadir angle is $90^\circ-e-\psi$. These are three different angles.

For $R=6371$ km and $h=550$ km:

| Minimum ground elevation | Slant range at edge | Ground arc radius | Visible cap area |
| ---: | ---: | ---: | ---: |
| 0° | 2703.81 km | 2557.05 km | 20.267 million km² |
| 10° | 1815.08 km | 1664.32 km | 8.653 million km² |
| 30° | 992.78 km | 793.50 km | 1.976 million km² |
| 60° | 626.89 km | 288.63 km | 0.262 million km² |
| 90° | 550.00 km | 0 km | 0 km² |

At exactly 90° the ray is vertical and the distance is shortest. A 90° elevation mask has zero area, although a nadir pointing antenna has a finite beam footprint. The cap describes which ground positions can see the satellite over its steering range; it is not simultaneous coverage by a narrow beam. Refraction is omitted in this coverage table. The existing refracted atmosphere integration is retained for spectroscopy and reduces to a vertical path at zenith.

The [motion calculation](../results/zenith_single_compound/motion.csv) makes the snapshot approximation explicit. A circular overhead pass over a nonrotating Earth reaches 86.05° and 551.20 km at 5 seconds from zenith, with 377 kHz carrier Doppler magnitude at 235 GHz. Thus a ten second observation centred on zenith is not ten seconds at exactly 90°. The tutorial is the requested fixed geometry benchmark; finite windows require tracking and geometry normalization. A 100 s total sensitivity represents two 50 s snapshots; actual endpoints at ±25 s are only 70.89°, so those numbers are not a validated moving pass result.

## Hardware references and selected assumptions

Sources were checked on 5 October 2026. Values refer to their stated frequency and operating mode.

| Evidence | Reported values | What it establishes |
| --- | --- | --- |
| [Sen et al., Nature Electronics](https://www.nature.com/articles/s41928-022-00897-6) | 200 mW, about 23 dBm, at 210–240 GHz in a terrestrial communication demonstration | 23 dBm is substantial at these frequencies; it is not a generic low power satellite setting. |
| [TeraLink design, 2026 preprint](https://arxiv.org/html/2606.15410v1) | Proposed 25 dBm RF output, 7 dB receiver noise figure and 45 dBi spacecraft antenna; 9 cm × 9 cm horn array design | A relevant LEO design anchor. Space qualification and antenna development are still described as ongoing. It does not demonstrate this 10 GHz OFDM receiver. |
| [Cooper et al., IEEE Journal of Microwaves, DOI 10.1109/JMW.2025.3610360](https://www.researchgate.net/publication/396148562_A_Power-Combined_240_GHz_Frequency-Multiplier_Source_for_Cloud_Radar_Applications) | More than 400 mW CW near 240 GHz; source response spans 235–255 GHz | Measured component evidence near 26 dBm. CW output does not establish equal average linear OFDM power across the whole band. |
| [ESA EarthCARE cloud radar](https://www.esa.int/Applications/Observing_the_Earth/FutureEO/EarthCARE/EarthCARE_s_cloud_profiling_radar) | 94 GHz, 2.5 m antenna, more than 1.5 kW pulse power, 3.3 µs pulses, about 300 W electrical consumption | Real high power satellite radar hardware, at a different frequency and with a different duty cycle and waveform. |
| [Millán et al., 380 GHz DAR simulations](https://amt.copernicus.org/articles/18/4483/2025/index.html) | Assumed 100 W peak transmitter and 2 m antenna | A published future instrument scenario, not measured 100 W hardware at 380 GHz. |

The new baseline is **25 dBm total average RF output**, a **10 cm circular equivalent satellite aperture**, a **1 m ground aperture**, **65% aperture efficiencies**, **7 dB receiver noise figure**, and **5 dB combined implementation loss**. TeraLink's link analysis also assumes a 1 m ground dish, with 60% efficiency; the selected 65% and total implementation loss remain engineering assumptions here. The circular aperture model is not a reconstruction of its horn array.

For equal power allocation, 25 dBm is 316 mW across all 1024 tones, or −5.103 dBm per tone. It is neither 25 dBm per tone nor EIRP. The sweep includes 17 dBm as an illustrative 8 dB output backoff from 25 dBm; the required backoff must be measured for the selected waveform. The 30 and 40 dBm rows are engineering sensitivities, not assertions of available hardware. The source multiplier efficiency must not be substituted for complete payload electrical efficiency. A complete electrical, thermal, duty cycle and linearity budget remains open.

At 20 s and **assumed 0.001 dB residual**, changing only RF power gives:

| Total average RF power | Watts | Conditional 95% concentration |
| ---: | ---: | ---: |
| 17 dBm | 0.050 | 120.47 µg/m³ |
| 23 dBm | 0.200 | 62.25 µg/m³ |
| 25 dBm | 0.316 | 50.58 µg/m³ |
| 26 dBm | 0.398 | 45.77 µg/m³ |
| 30 dBm | 1 | 31.83 µg/m³ |
| 40 dBm | 10 | 18.06 µg/m³ |

Power helps the thermal error; it does not remove an unknown absorption shaped gain error. The [full sensitivity table](../results/zenith_single_compound/sensitivity.csv) also includes assumed residuals 0, 0.0001 and 0.01 dB, durations 2, 20 and 100 s, and aperture/noise changes. These pilot based single band results are not directly comparable with historical results that use payload observations and many selected bands.

## Apertures and operation near 400 GHz

For a circular aperture,

$$
G=\eta(\pi D/\lambda)^2,\qquad
\theta_{\rm HPBW}\simeq1.02\lambda/D.
$$

The beamwidth approximation uses a uniformly illuminated circular aperture and is only an engineering estimate for a real tapered antenna; see the [JPL antenna analysis](https://tda.jpl.nasa.gov/progress_report/42-158/158D.pdf). At 235 GHz, the 10 cm and 1 m apertures give 45.96 and 65.96 dBi. Their approximate full beamwidths are 0.746° and 0.0746°. The satellite beam's nadir half power footprint diameter is about 7.16 km at 550 km altitude. The ground receiver's narrower angular acceptance places a tighter requirement on tracking; its aperture does not define the illuminated ground area.

At 400 GHz, a 1 m aperture would ideally give 70.58 dBi and 0.0438° beamwidth. The Ruze surface error expression $L_{\rm surf}=\exp[-(4\pi\sigma/\lambda)^2]$, derived in the [NRAO antenna reference](https://www.cv.nrao.edu/~sransom/web/Ch3.html), gives approximately 28.6 µm RMS for 1 dB surface loss, versus 48.7 µm at 235 GHz. Maintaining the assumed 65% efficiency therefore needs mechanical and surface validation. The surface calculation is a requirement diagnostic; it is not a second loss silently applied in the link budget.

The published [ITU P.835 reference atmosphere](https://www.itu.int/rec/R-REC-P.835-7-202408-I/en) and [P.676 gaseous model](https://www.itu.int/rec/R-REC-P.676-13-202208-I) give the following **calculated vertical gaseous losses** for this sea level standard atmosphere: 4.72 dB at 235 GHz, 9.02 dB at 300 GHz, 97.91 dB at 325 GHz, 848.69 dB at 380 GHz and 33.74 dB at 400 GHz. These point frequencies include severe water absorption regions; they are not a universal loss for each surrounding band. Rain, clouds and weather mismatch would need separate treatment. Increasing carrier frequency does not guarantee better sensing or communication.

## Bandwidth and OFDM spacing

The previous modem used **1 MHz tone spacing**, sixteen tones per hop, **16 MHz instantaneous bandwidth**, and many sequential frequency settings. It did not have 1 MHz total bandwidth. The earlier 60–400 GHz research range was a search range, not a 340 GHz instantaneous receiver.

The new teaching case occupies 10 GHz at once, with 1024 active tones and $\Delta f=9.765625$ MHz. Useful symbol time is 102.4 ns; an assumed 10 ns CP makes the transmitted symbol 112.4 ns. CP protects against delay spread and timing error after acquisition; it does not need to cover the 1.835 ms absolute satellite propagation delay. Wideband Doppler requires time resampling as well as centre frequency correction. At the ±5 s endpoints, removing only centre Doppler leaves about 8.0 kHz shift at a 5 GHz band edge.

All spacing candidates use identical bandwidth, average RF power, 10 ns CP, pilot fraction and acquisition duration:

| Tones | Spacing | CP share of time | Leakage at assumed 100 kHz residual CFO | Conditional 95% limit, 20 s, 0.001 dB residual |
| ---: | ---: | ---: | ---: | ---: |
| 256 | 39.063 MHz | 28.09% | 0.00216% | 56.21 µg/m³ |
| 512 | 19.531 MHz | 16.34% | 0.00862% | 52.52 µg/m³ |
| 1024 | 9.766 MHz | 8.90% | 0.03449% | 50.58 µg/m³ |
| 2048 | 4.883 MHz | 4.66% | 0.13791% | 49.58 µg/m³ |

Leakage here is $1-\operatorname{sinc}^2(\delta f/\Delta f)$. A practical candidate is 1024 tones: among these four it has the smallest conditional detection limit while meeting an illustrative 0.1% leakage ceiling at a 100 kHz residual. This is an explicit engineering selection criterion, not a global optimum or a measured synchronization requirement. The 2048 tone candidate gains little in ideal sensitivity and is more sensitive to residual CFO. At 1 MHz residual, the 1024 tone leakage is 3.40%, which requires better correction.

The detection table assumes ideal phase/time correction and does not include that CFO leakage in its covariance. Passing the waveform screen does not demonstrate 0.001 dB calibration or validate the detection prediction. CP length, pilot placement, oscillator phase noise, sample clock error and residual spectral distortion require a receiver test. A 10 GHz complex waveform also needs roughly 10 Gsample/s complex sampling before implementation margins; at 16 bits each for I and Q, the uncompressed stream is 40 GB/s. A streaming accumulator can avoid storing all IQ, but the analog and digital bandwidth still has to exist.

More bandwidth permits multiple molecular signatures to be observed simultaneously when the band contains sufficiently distinct lines. It also spreads fixed transmitter power over more frequencies and collects more noise. This single molecule example does not prove joint chemical identifiability. Later extension must build the full multi species Jacobian, include interferents, check its singular values and adjust the false alarm threshold for the number of outputs.

## Revised PM interpretation

PM2.5 and PM10 describe aerodynamic mass cuts; they are not chemical species. Use disjoint fine and coarse modes, with PM10 equal to their sum. A dry spherical diameter must be converted from aerodynamic diameter using density and a declared slip/shape model. The current Mie calculation already supports that conversion and separately returns absorption and scattering.

For a Rayleigh sphere, with radius $a$, wave number $k=2\pi/\lambda$ and $K=(m^2-1)/(m^2+2)$,

$$
C_{\rm abs}\simeq4\pi k a^3\operatorname{Im}K,
\qquad C_{\rm sca}=\frac{8\pi}{3}k^4a^6|K|^2.
$$

Dividing by particle mass $4\pi\rho a^3/3$, absorption per mass has leading dependence $f/\rho$, while scattering per mass scales as $a^3 f^4/\rho$, for fixed refractive index. **A general PM extinction law proportional to concentration times $f^4$ is incorrect when material absorption matters.** The old physical overview has been corrected accordingly. Full Mie calculations supply the numerical results, and frequency dependent complex optical constants remain required for a real material.

The numerical solver is miepython 3.0.2; its [algorithm documentation](https://miepython.readthedocs.io/en/latest/07_algorithm.html) describes the Mie and small sphere calculations and their references. The saved output separates extinction, absorption and scattering rather than assigning total extinction to scattering.

With the repository's explicitly assumed refractive indices, densities and lognormal distributions, scattering contributes only 0.0000332% of fine mode extinction and 0.00355% of coarse mode extinction at 235 GHz. At 50 µg/m³ and a 1 km exponential scale height, total vertical extinction is approximately 0.0000107 and 0.00000869 dB respectively. These are assumption sensitivity calculations, not measured properties of ambient PM. The maximum size parameters at 400 GHz remain below 0.032 in both dry distributions.

The [new PM diagnostic](../results/zenith_single_compound/pm_diagnosis.json) gives a fine/coarse signature cosine of 0.99999949 after eliminating gas, gain offset and gain slope. Formal local mass errors become enormous and lie far outside a physically meaningful retrieval range. Useful PM concentration is rejected for this experiment. Higher power cannot supply missing composition or size information, and a smooth signature is easily confused with gain. Next: measured complex optical constants and independent particle mass/size labels, followed by a new identifiability calculation; consider optical aerosol sensing as complementary evidence.

## Future molecular scattering and multistatic imaging

Molecules can scatter electromagnetic radiation. That fact does not establish a usable sub THz echo or a chemical image. The current observable is attenuation of a direct transmitter to receiver path. Molecular absorption, thermal emission, nonresonant elastic scattering, hydrometeor echoes and turbulence induced refractivity scattering are different mechanisms.

A useful order of magnitude screen is nitrogen far from a molecular resonance. Using the [NIST CCCBDB polarizability](https://cccbdb.nist.gov/exp2x.asp?casno=7727379&charge=0), $\alpha_v=1.710\times10^{-30}$ m³, an isotropic dipole approximation gives

$$
\sigma_s=\frac{8\pi}{3}(2\pi/\lambda)^4\alpha_v^2.
$$

At 235 GHz this is about $1.44\times10^{-44}$ m² per molecule. For an intentionally optimistic 1 km sea level nitrogen column, all 25 dBm transmitter power traversing it, a 1 m receiver at least 1 km from every scatterer and no absorption, the maximum Rayleigh phase function gives collected power of about **−202.6 dBm**. The [calculation and other frequencies](../results/zenith_single_compound/molecular_scattering_screen.csv) are a screening estimate. They ignore polarization anisotropy, gas dynamics and receiver bandwidth. This is not a resonant VOC cross section, nor a proof that all molecular radar schemes are impossible. A proposed resonant scheme needs species specific differential scattering cross sections, linewidths and a complete bistatic sensitivity calculation. Ordinary clear air radar may detect refractivity structures rather than individual molecule chemistry; the [NERC radar explanation](https://mst.nerc.ac.uk/clear_air_returns.html) describes that distinction.

For a bistatic scattering voxel, the required forward model has the structure

$$
dP_r=\frac{P_tG_t}{4\pi R_t^2}\,
\beta(f,\theta,\mathbf r)\,dV\,
\frac{A_{e,r}}{R_r^2}\,
T_tT_r,
$$

where $\beta$ is differential volume scattering in m⁻¹ sr⁻¹, $T_t,T_r$ are power transmissions on both legs, and $A_{e,r}$ is receiver effective area. Receiver noise, illumination, bistatic angle, range gating, coherent integration and clutter must all be added. The familiar $c/(2B)$ monostatic range formula must not be presented as direct path chemical depth resolution. In bistatic sensing, delay constrains $R_t+R_r$; spatial resolution also depends on geometry.

Several receivers can instead support **transmission tomography without molecular echoes**. For path $i$, frequency $k$, voxel $v$, path length $L_{iv}$ in metres and local attenuation per concentration $a_{kv}$,

$$
y_{ik}=\sum_v L_{iv}a_{kv}q_v+(B\beta)_{ik}+\epsilon_{ik},
\quad A_{(i,k),v}=L_{iv}a_{kv}.
$$

For multiple species add an index $s$, with $A_{(i,k),(v,s)}=L_{iv}a_{kvs}$. Nonparallel rays at several times or satellite positions are needed to resolve spatial ambiguity. At one overhead view many receiver rays are nearly parallel; adding receivers alone does not guarantee height resolution. Pressure dependent spectra can contain some vertical information, but that does not guarantee a unique three dimensional field. Check the singular values of the whitened matrix after calibration nuisance projection, resolution kernels and held out predictions before displaying an image. Regularization introduces prior information and must be identified as such. The field must also be sufficiently stable over the acquisition interval.

This is the future work formulation requested by the supervisor. No 3D image or molecular echo detection is claimed in this revision.

## What was done, result, limitations and next steps

### Reality checks against ambient concentrations and background error

The [EMeRGe study](https://acp.copernicus.org/articles/23/1893/2023/index.html) derived a 145 pptv acetonitrile winter background from selected IAGOS-CARIBIC measurements; this is an atmospheric mixing ratio, not a universal surface mass concentration. Using the ideal gas conversion at our reference surface state, 288.15 K and 101325 Pa, this mixing ratio corresponds to about 0.252 µg/m³. Our conditional 50.58 µg/m³ enhancement limit corresponds to about 29.1 ppbv at that state, approximately 200 times the cited background mixing ratio. The vertical profiles and enhancement/baseline observables are different, so this is a scale comparison rather than a direct field validation. **The favorable high concentration illustration does not demonstrate sensitivity to typical background acetonitrile.**

Controlled changes to a blank background produce additional apparent gas. In the [weather mismatch calculation](../results/zenith_single_compound/weather_mismatch.csv), raising water partial pressure by 1% at fixed temperature/total pressure creates up to 0.0533 dB background error and an apparent +0.579 µg/m³ of acetonitrile with the frozen two nuisance detector. A uniform +1 K temperature perturbation at fixed total/water pressure gives −0.750 µg/m³. These are specified model perturbations, not measured weather uncertainty distributions. Adding one fitted background amplitude removes most of these particular biases, while increasing the local 95% concentration scale to 83.63 µg/m³; it cannot correct arbitrary profile changes.

The [existing public calcite cell measurement audit](53_dataset_subsets_and_roles.md#external-physical-checks) reports before/after blank RMS differences of 0.047225 dB in that separate apparatus. That is evidence that real measurements can drift appreciably; it is not a calibration measurement for this satellite receiver and must not be substituted into its covariance without matching instrument and timing. The proposed 0.001 dB residual remains unverified.

The new background/sky integration also passes a 100 m versus 50 m layer comparison at 33 frequencies: maximum relative differences are about $3.02\times10^{-9}$ for loss and $7.57\times10^{-7}$ for sky temperature. These numerical checks do not validate the atmospheric state, cloud/rain omission or receiver model.

### Evidence and next steps

The change replaces an opaque aggregate study with a source based, reproducible single compound benchmark and an explicit response to every note. It adds code, physical inputs and hashes, exact matrices, complex pilot mean simulations, power/time/calibration/spacing comparisons, PM diagnostics, geometry tables and a figure. The old model overview and project summary now point to the current interpretation.

The strongest supported result is a transparent calculation, including failed low concentration sensing. The main limit is 50.58 µg/m³ under the stated 20 s and 0.001 dB assumed residual, with a 94.75% simulated response at that concentration. A favorable response cannot be described without those assumptions. Measurements of calibration, RF linearity, antenna efficiency, noise, weather mismatch and concentration truth remain absent. The uniform 230–240 GHz band was chosen as a simple hardware anchored example containing an acetonitrile feature; it was not optimized for concentration detection or for several gases.

Next steps are to review the walkthrough with the supervisor, choose a real receiver and frequency plan, measure a paired reference/sample stability record, then repeat the inference with those errors. Expand to other compounds and moving geometry after the simple case is understood. Pursue tomography and scattering as separately budgeted future experiments. The current manuscript and supervisor slide decks describe older experiments and have not been regenerated as if these different assumptions were equivalent.

Reproduce with `py -3.12 scripts/run_zenith_tutorial.py` and verify with `py -3.12 -m pytest tests/test_zenith_tutorial.py -q`. Dependencies are the repository's existing requirements, including `requirements-voc-pm.txt`. The script requires the previously acquired HITRAN catalog; if absent, use `scripts/acquire_payload_spectroscopy.py` and the existing acquisition instructions. The [manifest](../results/zenith_single_compound/manifest.json) records code and output hashes. Spectroscopy uses 17,880 CH3CN transitions from the retained catalog, with HAPI partition functions and natural mixture concentration units; the channel and all receiver observations are simulated.
