# Pipe Diameter and Minimum Wall Thickness

## Input normalization and calculation stages

User numeric input accepts either a decimal point or decimal comma, including
scientific notation. Thousands separators and mixed point/comma forms are not
accepted. Pipe Diameter/DN Selection and Wall Thickness are independent stages:
each uses only its own required inputs, while a recommended DN may populate the
wall-thickness outside diameter as a convenience.

Version 1 implements `D = sqrt(4 × Q / (V × π))`, with Q converted from
m³/h to m³/s. DN selection uses the first library inside diameter at least as
large as D, then recommends one larger library record when available.

Wall thickness uses `sigma_allow = Rp0.2 / safety_factor`,
`s0 = (da × pc) / ((20 × sigma_allow × v) + pc)`,
`b = 0.4 × (da / R) × s0`, and `s = s0 + c + b`. Bend allowance is zero when
disabled. All values retain full precision internally and display six decimals.

This module supports library and manual values. It does not claim
classification-society compliance and excludes PDF reporting, network, cloud,
and multi-user operation.

## Discharge head-loss audit

**Correction:** The canonical YSH equations are `h_local = 6400 × K_total ×
Q² / D⁴`, `h_pipe = 6.4e6 × f × L × Q² / D⁵`, `h_total = h_local + h_pipe`,
and `H_system = Hgeo + h_total`, with Q in m³/h, D in mm, L in m, and f as the
Darcy friction factor. SI Darcy-Weisbach is an audit comparison only. The
validated Excel case D=254 mm, Q=532 m³/h, L=343 m, f=0.0153374,
K_total=113.95 gives h_local=49.588697543072 m, h_pipe=9.013231371893 m,
h_total=58.601928914965 m, Hgeo=17 m, and H_system=75.601928914965 m.

The canonical result uses SI Darcy-Weisbach. The legacy straight-pipe
coefficient `6.4e6 × f × L × Q² / D⁵` is retained only for comparison. The
derived local-loss coefficient form has D⁴; the recorded D⁵ local-loss form is
unresolved and is not used for the main result.

## Unresolved engineering discrepancy

For `da=273.05 mm`, `pc=16 bar`, `Rp0.2=190 MPa`, safety factor `1.8`, weld
factor `1.0`, corrosion allowance `1.0 mm`, and bend disabled, the current
approved implementation calculates `s0=2.053865 mm` and total required
thickness `s=3.053865 mm`. A verified Excel workbook reports `3.35 mm`.
That Excel formula or its governing minimum/standard-wall selection rule has
not been supplied, so this is unresolved. The module must not be described as
validated, and `3.35 mm` is not treated as a raw formula result.
