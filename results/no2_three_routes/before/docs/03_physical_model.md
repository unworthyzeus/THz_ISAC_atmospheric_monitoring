# Physical Model

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

The real data version should use HITRAN line parameters:

1. Line center.
2. Line intensity.
3. Air broadening coefficient.
4. Lower state energy if temperature scaling is included.

The model should evaluate line shapes across 60 to 400 GHz.

## Particulate Matter

PM attenuation should use a published Rayleigh or Mie scattering model.

The initial assumption can be:

```text
PM loss proportional to concentration * frequency^4
```

This is only reasonable when particle diameter is much smaller than wavelength. Larger particles require Mie scattering or a published empirical model.

## Geometry

The current slant path approximation is:

```text
path = troposphere_height / sin(elevation)
```

This is useful for first experiments, but a stratified integration should replace it later.

## Noise

The software currently adds Gaussian noise in dB. A more realistic version should generate complex CSI and then derive amplitude.

## Targets

The target variables are:

1. PM concentration.
2. Gas concentration for selected HITRAN species.

