# Physical Model

Updated 5 October 2026. The [single compound walkthrough](55_zenith_single_compound_walkthrough.md) gives the current minimal reproducible example; the [supervisor revision](54_supervisor_revision_2026_10_05.md) explains source evidence, PM corrections and practical limitations.

## Observation

The intended observable is the amplitude of wideband CSI:

```text
y(f) = H_dB(f) + measurement noise
```

The forward model decomposes attenuation into:

```text
H_dB(f) = link offset - FSPL(f) - gas_loss(f) - pm_loss(f)
```

The early toy model used invented spectral lines. That model is no longer acceptable as the main scientific result.

## Molecular Absorption

The current calculation uses acquired HITRAN line parameters:

1. Line center.
2. Line intensity.
3. Air broadening coefficient.
4. Lower state energy, temperature exponents, pressure shifts and isotope partition functions for temperature scaling.

The research range is 60 to 400 GHz. It is not an instantaneous receiver bandwidth. The new tutorial evaluates an explicit 10 GHz band from 230 to 240 GHz.

## Particulate Matter

Use full spherical Mie extinction with independently specified size distribution, density and complex refractive index. Separate absorption and scattering. PM2.5 and PM10 are aerodynamic mass cuts; use disjoint fine and coarse modes and derive PM10 by summing them.

In the Rayleigh limit and at fixed material optical constants, scattering per unit particle mass scales as particle radius cubed times frequency to the fourth power. Absorption per unit mass instead has leading linear frequency dependence. Consequently, total PM extinction cannot generally be modeled as concentration times frequency to the fourth power. The repository's current assumed absorbing particles are dominated by absorption, and their smooth signatures are almost indistinguishable from gain changes and one another.

Convert aerodynamic to physical diameter with an explicit density/shape/slip model. Size distributions and optical constants remain assumptions unless independently measured. The [new PM diagnostic](../results/zenith_single_compound/pm_diagnosis.json) rejects useful joint PM mass sensing under the declared conditions. See the [Mie implementation documentation](https://miepython.readthedocs.io/en/latest/07_algorithm.html) and the linked supervisor derivation.

## Geometry

The current implementation integrates stratified spherical refracted rays. Ground elevation ranges from the horizon to a maximum of 90°; 30° may be a minimum visibility mask. At 90° the atmospheric path is vertical and satellite slant range equals its height above the station. The old plane parallel path proportional to 1/sin(elevation) is an approximation, not the current general model. Coverage area, satellite off nadir angle and beam footprint are separate quantities.

## Noise

The new tutorial generates complex Gaussian pilot mean observations for both reference and sample, then takes their log magnitude ratio. Its estimator uses the corresponding local covariance plus a persistent differential calibration covariance. Other modules retain payload and Gaussian attenuation controls with their own assumptions. Ideal phase/time correction and the assumed calibration covariance are not validated by generating receiver noise.

## Targets

The target variables are:

1. PM concentration.
2. Gas concentration for selected HITRAN species.

