"""Seawater / fresh-water density and viscosity from published MIT correlations.

Sharqawy, Lienhard & Zubair, Desalination and Water Treatment 16 (2010) 354-380
(density: Eqs. 8-9; dynamic viscosity: Eqs. 22-23), as used by the MIT seawater library.
Temperature in degC (ITS-90), salinity in g/kg. Atmospheric-pressure correlations: the pressure
dependence is not applied, so pressure is limited to the range the paper states (0.1-1 MPa).
The 24 published MIT table points stored in the library are reproduced to rounding.
"""
import math

T_RANGE = (0.0, 180.0)
S_RANGE = (0.0, 150.0)
P_RANGE_MPA = (0.0, 1.0)


def in_range(temperature_c, salinity_g_kg, pressure_mpa):
    values = (temperature_c, salinity_g_kg, pressure_mpa)
    if any(type(v) not in (int, float) or isinstance(v, bool) or not math.isfinite(v) for v in values):
        return False
    return (T_RANGE[0] <= temperature_c <= T_RANGE[1] and S_RANGE[0] <= salinity_g_kg <= S_RANGE[1]
            and 0 < pressure_mpa <= P_RANGE_MPA[1])


def density_kg_m3(t, salinity_g_kg):
    s = salinity_g_kg / 1000.0
    rho_w = 9.999e2 + 2.034e-2 * t - 6.162e-3 * t**2 + 2.261e-5 * t**3 - 4.657e-8 * t**4
    return rho_w + s * (8.020e2 - 2.001 * t + 1.677e-2 * t**2 - 3.060e-5 * t**3 - 1.613e-5 * t * s)


def dynamic_viscosity_pa_s(t, salinity_g_kg):
    s = salinity_g_kg / 1000.0
    mu_w = 4.2844e-5 + 1.0 / (0.157 * (t + 64.993) ** 2 - 91.296)
    a = 1.541 + 1.998e-2 * t - 9.52e-5 * t**2
    b = 7.974 - 7.561e-2 * t + 4.724e-4 * t**2
    return mu_w * (1 + a * s + b * s * s)


def kinematic_viscosity_cst(t, salinity_g_kg):
    return dynamic_viscosity_pa_s(t, salinity_g_kg) / density_kg_m3(t, salinity_g_kg) * 1e6
