# Literature Map

## Project Core

| Topic | Source | Role |
| --- | --- | --- |
| Sub THz satellite communication and differential absorption radar | Aliaga et al., 2024 | Direct inspiration for atmospheric ISAC |
| THz attenuation in space air ground channels | Yang, Gao, and Han, 2024 | Propagation and attenuation modeling |
| THz ISAC for environmental sensing | Dong and Akan, 2026 | Example of opportunistic environmental sensing |
| LEO ISAC rain rate bounds | Dong et al., 2026 | Estimation bounds and detectability framing |
| Ka band space weather sensing | Wang et al., 2025 | Link internal sensing architecture |

## Required External Data Sources

| Source | Use |
| --- | --- |
| HITRAN | Molecular line positions, intensities, and broadening parameters |
| Public air quality dataset | Real PM and gas concentration scenarios |
| Standard atmosphere model | Pressure, temperature, and density profiles |
| ITU R recommendations | Link budget and atmospheric attenuation reference |

## Reading Priority

1. Aliaga et al. for the sub THz satellite sensing architecture.
2. Yang et al. for channel attenuation components.
3. HITRAN documentation for line by line data access.
4. Rain rate estimation bounds for the statistics section.
5. Public air quality dataset documentation for units and missing data handling.

## Caution

The literature spans THz, sub THz, Ku band, and Ka band. Each result must be checked for frequency dependence before being transferred into this project.

