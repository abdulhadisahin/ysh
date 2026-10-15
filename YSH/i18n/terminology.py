"""Visible engineering vocabulary; no calculation, persistence, or UI dependencies.

Symbols identify physical quantities, while existing message keys remain aliases.
Q12 and Qpump are separate transfer quantities and are deliberately not redefined.
"""

from types import MappingProxyType

TERMS_TR = MappingProxyType(
    {
        "Q": "Hacimsel debi",
        "V": "Ortalama akış hızı",
        "D": "Gerekli teorik iç çap",
        "Di": "Boru iç çapı",
        "da": "Boru dış çapı",
        "s": "Et kalınlığı",
        "s0": "Temel et kalınlığı",
        "R": "Bükme yarıçapı",
        "b": "Bükme ilavesi",
        "c": "Korozyon artımı",
        "v": "Kaynak faktörü",
        "σallow": "Müsaade edilen gerilme",
        "ν": "Kinematik viskozite",
        "ρ": "Akışkan yoğunluğu",
        "k": "Mutlak pürüzlülük",
        "k/Di": "Bağıl pürüzlülük",
        "Re": "Reynolds sayısı",
        "f": "Darcy sürtünme faktörü",
        "K": "Lokal kayıp katsayısı",
        "hf": "Boru sürtünme kaybı",
        "hL": "Lokal yük kaybı",
        "hhat": "Toplam basma hattı yük kaybı",
        "Hgeo": "Statik basma yüksekliği",
        "Hs": "Toplam basma yüksekliği",
        "he": "Emme hattı yük kaybı",
        "HEgeo": "Statik emme yüksekliği",
        "PE": "Emme haznesi mutlak basıncı",
        "Pb": "Akışkanın buhar basıncı",
        "ENPYm": "Mevcut Net Pozitif Emme Yüksekliği",
        "NPSHr": "Gerekli Net Pozitif Emme Yüksekliği",
        "ΔENPY": "ENPY marjı"
    }
)

TERMS_EN = MappingProxyType(
    {
        "Q": "Volumetric flow rate",
        "V": "Mean flow velocity",
        "D": "Required theoretical inside diameter",
        "Di": "Pipe Inside Diameter",
        "da": "Pipe outside diameter",
        "s": "Wall thickness",
        "s0": "Base wall thickness",
        "R": "Bend radius",
        "b": "Bend allowance",
        "c": "Corrosion allowance",
        "v": "Weld factor",
        "σallow": "Allowable stress",
        "ν": "Kinematic Viscosity",
        "ρ": "Fluid density",
        "k": "Absolute roughness",
        "k/Di": "Relative roughness",
        "Re": "Reynolds number",
        "f": "Darcy friction factor",
        "K": "Local loss coefficient",
        "hf": "Pipe friction loss",
        "hL": "Local head loss",
        "hhat": "Total discharge line head loss",
        "Hgeo": "Static discharge head",
        "Hs": "Total discharge head",
        "he": "Suction line head loss",
        "HEgeo": "Static suction height",
        "PE": "Suction reservoir absolute pressure",
        "Pb": "Fluid vapour pressure",
        "ENPYm": "Available NPSH",
        "NPSHr": "Required NPSH",
        "ΔENPY": "NPSH margin"
    }
)

MESSAGE_SYMBOLS = MappingProxyType(
    {
        "field.flow_rate": "Q",
        "field.design_velocity": "V",
        "result.flow_velocity": "V",
        "result.calculated_diameter": "D",
        "field.pipe_inside_diameter": "Di",
        "field.inside_diameter": "Di",
        "library.inside_diameter": "Di",
        "field.pipe_outside_diameter": "da",
        "field.outside_diameter": "da",
        "library.outside_diameter": "da",
        "result.required_wall_thickness": "s",
        "field.wall_thickness": "s",
        "library.wall_thickness": "s",
        "result.base_wall_thickness": "s0",
        "field.bend_radius": "R",
        "result.bend_allowance": "b",
        "field.corrosion_allowance": "c",
        "constant.corrosion_allowance": "c",
        "field.weld_factor": "v",
        "constant.weld_factor": "v",
        "result.allowable_stress": "σallow",
        "field.kinematic_viscosity": "ν",
        "field.fluid_density": "ρ",
        "field.roughness": "k",
        "field.active_roughness": "k",
        "result.relative_roughness": "k/Di",
        "result.reynolds_number": "Re",
        "result.friction_factor": "f",
        "field.local_loss_k": "K",
        "result.pipe_friction_loss": "hf",
        "result.local_loss": "hL",
        "result.total_hydraulic_loss": "hhat",
        "field.geodetic_head": "Hgeo",
        "result.geodetic_head": "Hgeo",
        "result.system_manometric_head": "Hs",
        "result.pump_discharge_head": "Hs",
        "result.suction_head_loss": "he",
        "field.static_suction_height": "HEgeo",
        "field.suction_pressure": "PE",
        "field.vapour_pressure": "Pb",
        "result.available_npsh": "ENPYm",
        "warning.available_enpy": "ENPYm",
        "field.npsh_required": "NPSHr",
        "warning.required_npsh": "NPSHr",
        "result.npsh_margin": "ΔENPY"
    }
)

def terminology_messages(language: str) -> dict[str, str]:
    """Resolve existing and future report-facing keys from the same vocabulary."""
    terms = TERMS_TR if language == "tr" else TERMS_EN
    return {
        **{f"engineering.{symbol}": term for symbol, term in terms.items()},
        **{key: terms[symbol] for key, symbol in MESSAGE_SYMBOLS.items()},
    }
