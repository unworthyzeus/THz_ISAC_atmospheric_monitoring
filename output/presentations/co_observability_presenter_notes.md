## 1. Observing CO in the channel

The study restarts with a single gas, CO, over 60 to 1000 GHz. We study the frequency and path length dependence of the channel, initially with no receiver noise. The immediate objective is to identify what information allows us to attribute part of the measured loss to CO. The cover uses a decorative abstract illustration of light bands. It carries no measured spectral information.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 2. The channel is a frequency × length matrix

H has frequency along its rows and atmospheric path length along its columns. The table shows indices, not invented channel values. Repeating observations at the same geometry does not create independent path length samples. Nested paths through the same stationary medium might come from known receiver positions or a controlled variable path setup. The total transmitter to receiver distance d may differ from the atmospheric distance l. They coincide in the homogeneous terrestrial numerical example. A future angular coordinate would give h(f,l,theta). We begin by studying magnitudes because the immediate question concerns absorption.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 3. Geometry and absorption contribute to one channel

We assume the instrument response is known, corrected or matched between acquisitions. With that convention, the magnitude is the product of geometric amplitude gain and the two exponential absorption factors. The omitted full complex channel also contains propagation phase and molecular dispersion. Each tau is a dimensionless integral of a power absorption coefficient alpha, in 1/m, over path length. Beer–Lambert gives power transmission exp(-tau). Since power is proportional to squared magnitude, the channel amplitude uses exp(-tau/2). For unit gain far field antennas, |h_fs|=c0/(4 pi f d). A positive free space path loss is the reciprocal power gain, not an amplitude multiplier. The table uses compact plain text names for the subscripts.

- [beer](https://hitran.org/docs/cross-sections-definitions/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 4. A matched reference isolates the chemical loss

Define h0 with the same geometry, instrument response and background atmospheric optical depth, but without the additional target gas column. Dividing h by h0 cancels the shared multiplicative factors. The magnitude ratio is exp(-tau_c/2), so -2 times its natural logarithm gives the chemical optical depth. In decibels, extra loss is -20 log10(|h|/|h0|)=(10/ln10) tau_c. If h0 contains ambient CO, the retrieved quantity is the CO enhancement relative to that reference. An absolute column requires knowledge of the reference CO. A model can supply h0 only to the accuracy of its atmospheric and instrument assumptions.

- [beer](https://hitran.org/docs/cross-sections-definitions/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 5. An unknown atmosphere leaves the split ambiguous

After known geometry and calibration are removed, the observation gives the sum of optical depths. Any admissible q transferred from one component to the other leaves the measurement unchanged. The altered components must remain within their allowed physical models and nonnegativity constraints. This is a mathematical construction, not a claim that any chosen q belongs to a realistic humidity model. It proves nonuniqueness when the background is unrestricted. More frequencies and zero receiver noise do not eliminate an unrestricted functional ambiguity. A parameterized atmosphere can permit separation when changes in CO generate a response outside the span of atmospheric parameter changes.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 6. A discrete transition has a continuous profile

The unshifted center of this CO transition is about 115.271 GHz. An ideal infinitely sharp resonance would be a delta peak at its center, not a rectangular absorption band. A finite coherence time yields a Lorentzian response. Thermal velocities give a Gaussian Doppler distribution. A Voigt profile combines those contributions. Natural linewidth also exists but is not the main atmospheric width here. These mechanisms are physical and remain when receiver noise is set to zero. The plot compares area normalized profiles at 1 and 0.1 atm using the same HITRAN transition at 296 K. It isolates line broadening, rather than comparing equal ppm samples. At 1 atm the tabulated air half width is 2.40733 GHz, giving a Lorentz full width of 4.81467 GHz. Pressure shifts also move the center slightly. More sophisticated profiles and line mixing may matter for precision work. Smooth line wings and overlap must not be confused with separate continuum absorption.

- [hitran](https://hitran.org/docs/definitions-and-units/)
- [nist](https://physics.nist.gov/Pubs/AtSpec/node20.html)
- [continuum](https://hitran.org/mtckd/)

## 7. CO has eight main rotational lines in this band

The eight labels are the main isotopologue ground vibrational state rotational line centers in the 60 to 1000 GHz interval. JPL independently supports their positions. Other isotopologues and excited states add features. The actual spectrum includes all 146 retained HITRAN main isotopologue transitions with centers from 0 to 3000 GHz. The chart displays the stored physical spectrum, with every second sample plus the exact line center samples retained. A millidecibel is 0.001 dB. Relative peak heights follow the line strengths and widths for this temperature and pressure. They do not identify the most useful instrument band because background atmospheric loss and measurement precision also matter. This calculation uses a chosen gas column, exact background and calibration, and no receiver noise. It gives no practical detection threshold.

- [jpl](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat)
- [hitran](https://hitran.org/docs/definitions-and-units/)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)

## 8. Chemical loss grows only while crossing the cloud

For constant local temperature and pressure, tau_c(f,l)=sigma_c(f) times the accumulated column N_c(l). Here N_c is zero before 20 m, increases inside the cloud, and stops changing beyond 40 m. More distance after the cloud still increases geometric and background atmospheric loss. Receivers all beyond the cloud see the same chemical column in this ideal setup. A microdecibel is 0.000001 dB. For truly nested paths in a stationary medium, differentiating optical depth with respect to l gives the local absorption coefficient. That derivative does not apply to arbitrary different paths or a changing cloud. Concentration and cloud thickness are not individually determined from a single integrated column.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)

## 9. A chosen CO column gives a very small channel change

All displayed values come from the saved CO example. The scenario values are chosen inputs, not field measurements. Temperature is 296 K, pressure is 101325 Pa and water partial pressure is 1000 Pa. The chemical cloud contains 1 ppm excess CO from 20 to 40 m along a horizontal path. At the unshifted 115.271 GHz center, extra loss is 2.889726e-6 dB and the amplitude ratio is 0.999999667308. At 230.538 GHz the corresponding loss is 2.334813e-5 dB. At 345.796 GHz it is 7.966024e-5 dB. The known reference permits numerical recovery of the chosen column. Generation and inversion use the same forward assumptions, so this is an algebraic consistency result rather than an independent physical validation. The main isotopologue, air broadened Voigt approximation omits minor isotopologues, explicit water perturber effects and non-Voigt corrections. No practical sensitivity or detection limit follows from these numbers.

- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
- [hitran](https://hitran.org/docs/definitions-and-units/)
- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 10. The separation requires more than an absorption law

Knowledge of a well studied atmospheric law is not the same as knowledge of the atmosphere at acquisition time. The background needs temperature, pressure and humidity along the relevant ray. P.676 Annex 1 covers oxygen and water based gas attenuation up to 1000 GHz, with specified continuum terms, while omitting some minor species. Avoid double counting oxygen, water and continuum absorption by adding overlapping models. Geometry and instrument response also affect measured h. If the target already exists in the reference, the observable is a change from its reference column. To turn a column into a uniform concentration, cloud length must be known. These issues remain even if additive receiver noise is zero.

- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)
- [hitran](https://hitran.org/docs/definitions-and-units/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 11. Chemical identifiability and practical detectability

The overall objective is a defensible classification of which chemicals the system can distinguish in the specified band. For a local parameterized model, delta r = J_m delta theta_m + s_c delta N_c. CO is locally distinguishable when its response s_c lies outside the span of uncertain atmospheric responses J_m. With multiple gases, their columns must remain independent after accounting for nuisance responses. This local rank condition does not establish global uniqueness for a nonlinear model. Under exact arithmetic, exact forward knowledge and no receiver noise, arbitrarily small nonzero distinct responses are observable in principle. A finite operational concentration limit needs measurement precision, calibration, environmental uncertainty and a decision criterion. Nonzero extrapolated line wings alone do not certify practical detectability, and absence of an entry in one catalog does not prove a species has no response.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 12. The next experiment needs a defined reference

The immediate meeting decision is how the experiment obtains the background reference. A controlled reference acquisition can isolate an enhancement if the atmosphere, geometry and hardware remain matched. A modeled reference needs explicitly constrained atmospheric and calibration parameters. The next CO calculation should vary those uncertain quantities and examine whether the CO response remains distinct. After this single gas case, apply the same reasoning to other named gases individually, then mixtures. Angular dependence follows once path geometry is settled. This presentation does not carry forward the old proposal tasks or detector performance claims.

- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)

## 13. Appendix: the molecular model

The rigid rotor gives an instructive approximation for CO rotational levels. B is in Hz and h_P is Planck constant. Allowed absorption changes J to J+1, so frequency is near 2B(J+1), with centrifugal distortion corrections required for accurate line positions. The cross section is the sum of integrated strengths times normalized profiles. In this formula S and V use a common frequency convention. HITRAN itself uses wavenumber, with f in GHz = 29.9792458 times wavenumber in cm^-1. A change of integration variable requires consistent strength and profile normalization. Number density times cross section gives a local absorption coefficient. Its integral gives optical depth. Power follows exp(-tau); amplitude follows exp(-tau/2). For uniform temperature and pressure, the cross section can be taken outside the path integral and the unknown becomes the molecular column. The first example fixes temperature at HITRAN reference 296 K. Other temperatures require line intensity population and partition function corrections.

- [rotor](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules)
- [hitran](https://hitran.org/docs/definitions-and-units/)
- [beer](https://hitran.org/docs/cross-sections-definitions/)

## 14. Sources and reproducible calculation

The linked project note records the complete derivation, scientific assumptions and executable CO example. The numerical sources were downloaded and checked on October 14, 2026. The simulation uses real spectroscopic parameters with a chosen environmental scenario. References in individual notes identify which sources support each slide. Additional reading covers water vapor continuum, collision induced absorption and the rigid rotor correction terms.

- [hitran](https://hitran.org/docs/definitions-and-units/)
- [hapi](https://hitran.org/hapi/)
- [jpl](https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat)
- [itu](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf)
- [nist](https://physics.nist.gov/Pubs/AtSpec/node20.html)
- [rotor](https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules)
- [continuum](https://hitran.org/mtckd/)
- [cia](https://hitran.org/cia/)
- [local](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md)
- [numbers](https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv)
