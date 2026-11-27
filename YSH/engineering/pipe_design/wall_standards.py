"""Explicit, scope-limited wall rules. Minimums are never nominal stock sizes."""
from dataclasses import dataclass
import re
from uuid import UUID

from engineering.pipe_design.validation import _positive
from engineering.validation import ValidationError, ValidationIssue

TL_DOCUMENT = 'Türk Loydu Kısım 107, Bölüm 8 (Ocak 2022)'
TL_URL = 'https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-e/chapter-107-naval-ship-technology-ship-operation-installations-and-auxiliary-systems-2022-JAN.pdf'
ISO_URL = 'https://cdn.standards.iteh.ai/samples/9985/a31e6a223a8f4108810f38151c202552/ISO-4200-1991.pdf'


@dataclass(frozen=True)
class ScopedWallMaterial:
    """Wall-only reference identity; no invented yield strength or roughness."""
    name: str
    designation: str
    standard: str
    source: str
    id: UUID
    yield_strength_mpa: float | None = None


def cuni_wall_material():
    from uuid import NAMESPACE_URL, uuid5
    return ScopedWallMaterial('CuNiFe10 / CuNi10Fe', 'CuNi10Fe',
        TL_DOCUMENT+' / Tablo 8.8', TL_URL,
        uuid5(NAMESPACE_URL,'d243:wall-reference:tl107:2022:CuNi10Fe'))


def material_code(designation):
    return re.sub(r'[^A-Z0-9]', '', designation.upper())


def is_cuni10(designation):
    return material_code(designation) in {'CUNIFE10', 'CUNI10FE'}


def auxiliary_cuni_stress(designation, family, temperature_c):
    """68 is already allowable stress, not a strength to divide by B.

    The user confirms that this application's seawater family is auxiliary
    seawater. TL Table 8.8 (annealed CuNi10Fe) records 68 at 50 and 75 °C.
    Missing/lower temperatures retain the user's criterion, explicitly NOT a
    verified TL temperature selection. Higher temperatures need another rule.
    """
    if family != 'seawater' or not is_cuni10(designation):
        return None
    if temperature_c is not None:
        import math
        if isinstance(temperature_c, bool) or not math.isfinite(temperature_c):
            raise ValidationError(ValidationIssue('valid_number', 'pipe.design_temperature'))
        if temperature_c > 75:
            raise ValidationError(ValidationIssue('pipe.cuni_temperature_scope'))
    verified = temperature_c in (50, 75)
    return {'value_mpa': 68.0, 'mode': 'DIRECT_ALLOWABLE',
            'source': TL_DOCUMENT if verified else 'DPO Standardı',
            'table': '8.8', 'publication_date': '2022-01' if verified else None,
            'verification_date': '2026-11-25' if verified else None,
            'url': TL_URL, 'tl_temperature_verified': verified,
            'temperature_c': temperature_c,
            'scope': 'Annealed CuNi10Fe; Table 8.8: 50 °C / 75 °C; auxiliary seawater only'}


def minimum_wall(designation, outside_mm):
    """Exact recorded diameter intervals; no interpolation across missing rows."""
    _positive(outside_mm, 'field.pipe_outside_diameter')
    if is_cuni10(designation):
        rows = ((8,10,.8),(12,20,1.),(25,44.5,1.2),(50,76.1,1.5),
                (88.9,108,2.),(133,159,2.5),(193.7,267,3.),
                (273,457.2,3.5),(470,470,3.5),(508,508,4.))
        value = next((v for lo,hi,v in rows if lo <= outside_mm <= hi), None)
        return value, '8.7'
    if material_code(designation) in {'316L','AISI316L','14404','304L','AISI304L','14307'}:
        rows = ((17.2,1.),(48.3,1.6),(88.9,2.),(168.3,2.3),(219.1,2.6),
                (273,2.9),(406,3.6),(float('inf'),4.))
        return next(v for hi,v in rows if outside_mm <= hi), '8.6'
    return None, None  # Steel needs the installation group in Tables 8.4/8.5.


@dataclass(frozen=True)
class NominalWall:
    """A verified material/OD/service-specific nominal table entry."""
    material: str
    outside_mm: float
    family: str
    thickness_mm: float
    standard: str
    table: str
    publication_date: str = '1991-02'
    url: str = ISO_URL
    status_note: str = ''


EEMUA_URL = 'https://www.kme.com/fileadmin/DOWNLOADCENTER/SPECIAL%20DIVISION/2%20Marine%20Applications/2%20Offshore/OSNA10_Offshore_2017.pdf'
# EEMUA 234/1 (2016) seamless 90-10 Cu-Ni pipe, 16 bar series:
# outside diameter -> specified wall [mm]. Transcribed from the KME OSNA-10
# offshore catalogue (2017), which cites EEMUA 234 chapter 1; the same values
# appear in an EEMUA 144 supplier listing. The standard itself was not read.
# Catalogue note 4: for 159 mm and larger the wall may be up to 12.5 % below
# the specified value; this is NOT applied here (no thickness tolerance).
# Cross-checked against a second manufacturer table (Wieland Eucaro offshore
# brochure, 06/2015, citing EEMUA 144 Section 1/2): the 16 bar column agrees for
# every size. Sizes above 419 mm and the whole 20 bar column come from that
# brochure only (its larger rows match the KME values seen in a search excerpt).
# EEMUA 144 sizes have no 168.3 mm pipe: use 159 or 219.1.
EEMUA_144_16BAR_CUNI10 = {16.:2., 25.:2., 30.:2.5, 38.:2.5, 44.5:2.5, 57.:2.5,
    76.1:2.5, 88.9:2.5, 108.:3., 159.:3., 219.1:4., 267.:4.5, 323.9:5.5,
    368.:6.5, 419.:7., 457.2:8., 508.:8.5, 610.:10.5, 711.:12., 813.:13.5, 914.:15.5}
EEMUA_144_20BAR_CUNI10 = {16.:2., 25.:2., 30.:2.5, 38.:2.5, 44.5:2.5, 57.:2.5,
    76.1:2.5, 88.9:2.5, 108.:3., 159.:3.5, 219.1:4.5, 267.:5.5, 323.9:7.,
    368.:8., 419.:9., 457.2:9.5, 508.:11., 610.:13., 711.:15., 813.:17., 914.:19.}
WIELAND_URL = 'https://www.wieland.com/en/Media/Files/brochures/offshore.pdf'


def cuni_series(design_pressure_bar=None, design_temperature_c=None):
    """16 bar series (to 75 C) up to 16 bar; 20 bar series (to 38 C only) up to 20 bar; else none."""
    if design_pressure_bar is None or design_pressure_bar <= 16:
        return 16
    if design_pressure_bar <= 20 and (design_temperature_c is None or design_temperature_c <= 38):
        return 20
    return None


def recommend_wall(required_mm, designation, outside_mm, family, records=()):
    _positive(required_mm, 'result.required_wall_thickness')
    minimum, table = minimum_wall(designation, outside_mm)
    eligible = [r for r in records if material_code(r.material)==material_code(designation)
                and r.outside_mm==outside_mm and r.family==family
                and r.thickness_mm > required_mm
                and (minimum is None or r.thickness_mm >= minimum)]
    selected = min(eligible, key=lambda r:r.thickness_mm) if eligible and minimum is not None else None
    return {'minimum_wall_mm': minimum, 'minimum_standard': TL_DOCUMENT if table else None,
            'minimum_table': table, 'nominal_wall_mm': selected.thickness_mm if selected else None,
            'nominal_standard': selected.standard if selected else None,
            'nominal_table': selected.table if selected else None,
            'minimum_publication_date': '2022-01' if table else None,
            'nominal_publication_date': selected.publication_date if selected else None,
            'nominal_note': selected.status_note if selected else None,
            'verification_date': '2026-11-25',
            'minimum_url': TL_URL if table else None,
            'nominal_url': selected.url if selected else None,
            'status': 'MATCH' if selected else 'SOURCE_REQUIRED'}


def verified_nominal_walls(designation, outside_mm, family, design_pressure_bar=None, design_temperature_c=None):
    """ISO 4200:1991 Table 1, stainless ranges A/B/C/E/F/G only.

    Explicitly scoped subset of series-1 ODs. Never use this steel table for
    CuNi. Missing dimensions are unresolved, not rounded to another OD.
    Publication: February 1991; verification: 2026-11-25.
    """
    if is_cuni10(designation):
        # Auxiliary seawater only, matching the CuNi allowable-stress scope.
        series = cuni_series(design_pressure_bar, design_temperature_c) if family == 'seawater' else None
        table = {16: EEMUA_144_16BAR_CUNI10, 20: EEMUA_144_20BAR_CUNI10}.get(series, {})
        wall = table.get(float(outside_mm))
        if wall is None:
            return ()
        return (NominalWall(designation, outside_mm, family, wall,
                f'EEMUA 234/1 (2016), {series} bar, via KME / Wieland catalogues', f'{series} bar',
                publication_date='2016', url=EEMUA_URL if series == 16 else WIELAND_URL,
                status_note='pipe.nominal_secondary_source'),)
    if family not in {'fuel','fire','seawater'} or material_code(designation) not in {'316L','AISI316L','14404','304L','AISI304L','14307'}:
        return ()
    rows = {48.3:(1.6,2.,2.6,3.6,5.),60.3:(1.6,2.,2.3,2.9,4.,5.6),
            76.1:(1.6,2.3,2.6,2.9,5.,7.1),88.9:(2.,2.3,2.9,3.2,5.6,8.),
            114.3:(2.,2.6,2.9,3.6,6.3,8.8),139.7:(2.,2.6,3.2,4.,6.3,10.),
            168.3:(2.,2.6,3.2,4.5,7.1,11.),219.1:(2.,2.6,3.6,6.3,8.,12.5),
            273.:(2.,3.6,4.,6.3,10.,14.2)}
    return tuple(NominalWall(designation,outside_mm,family,t,'ISO 4200:1991','1')
                 for t in rows.get(outside_mm, ()))
