"""Curated normative references printed in Word reports (presentation only; no engineering effect).

Each entry names the document, the table/clause the application actually uses and how far it was
verified. Entries marked 'supplier' or 'secondary' were taken from a quotation of the standard,
not from the licensed text itself.
"""
from __future__ import annotations
from dataclasses import dataclass

ALL = ('fuel', 'seawater', 'fire')
TL = 'https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-e/chapter-107-naval-ship-technology-ship-operation-installations-and-auxiliary-systems-2022-JAN.pdf'


@dataclass(frozen=True)
class Reference:
    modules: tuple[str, ...]
    families: tuple[str, ...]
    document: str
    table: str
    use_tr: str
    use_en: str
    basis: str  # 'primary' | 'secondary'
    url: str = ''


REFERENCES = (
    Reference(('pipe_design',), ('seawater',), 'Türk Loydu Part 107 Ch.8 (Jan 2022)', 'Tables 8.6, 8.7',
        'Boru minimum et kalınlığı', 'Minimum pipe wall thickness', 'primary', TL),
    Reference(('pipe_design',), ('seawater',), 'Türk Loydu Part 107 Ch.8 (Jan 2022)', 'Table 8.8',
        'CuNi10Fe izin verilen gerilme (68 N/mm²)', 'CuNi10Fe allowable stress (68 N/mm²)', 'primary', TL),
    Reference(('pipe_design',), ('seawater',), 'EEMUA 144 / KME OSNA-10, Wieland offshore brochure', 'Standard wall series (16 / 20 bar)',
        'CuNi10Fe standart et kalınlığı serileri', 'CuNi10Fe standard wall series', 'secondary',
        'https://www.wieland.com/en/Media/Files/brochures/offshore.pdf'),
    Reference(('pipe_design',), ALL, 'ISO 4200:1991', 'Table 1 (series A/B/C/E/F/G)',
        'Paslanmaz çelik standart et kalınlıkları', 'Stainless steel standard wall thicknesses', 'primary'),
    Reference(('pipe_design',), ALL, 'EN 10220:2002 / DIN EN 10220:2003-03', 'Dimension tables',
        'Dikişsiz/kaynaklı boru boyutları', 'Seamless/welded tube dimensions', 'secondary'),
    Reference(('pipe_design',), ('fuel',), 'EN 10216-1:2013', 'Table 1, Table 5',
        'P235TR2 mekanik özellikleri', 'P235TR2 mechanical properties', 'secondary'),
    Reference(('discharge_head_loss', 'suction_npsh'), ALL, 'Hydraulic Institute Data Tool, Pipe Frictional Losses', 'Table 3.A.1 (2024-07-19)',
        'Mutlak pürüzlülük değerleri', 'Absolute roughness values', 'primary'),
    Reference(('discharge_head_loss', 'suction_npsh', 'transfer_pump'), ('fuel',), 'ISO 8217:2017 (DMA/DMZ/DMB)', 'Table 1 (distillates)',
        'Kinematik viskozite (40 °C) ve yoğunluk aralıkları; lisanslı metin okunmadı, tedarikçi tablosundan alındı',
        'Kinematic viscosity (40 °C) and density ranges; licensed text not read, taken from a supplier table', 'secondary'),
    Reference(('discharge_head_loss', 'suction_npsh', 'transfer_pump'), ('fuel',), 'MIL-DTL-16884R (F-76)', 'Table I',
        'F-76 yoğunluk (15 °C) ve viskozite (40 °C)', 'F-76 density (15 °C) and viscosity (40 °C)', 'primary',
        'https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=12122'),
    Reference(('discharge_head_loss', 'suction_npsh', 'transfer_pump'), ('fuel',), 'MIL-DTL-5624X (JP-5 / F-44)', 'Table I',
        'JP-5 yoğunluk ve viskozite', 'JP-5 density and viscosity', 'primary',
        'https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=5558'),
    Reference(('discharge_head_loss', 'suction_npsh'), ('seawater',), 'MIT Seawater Thermophysical Properties Library', 'Tables 3 and 21',
        'Deniz suyu yoğunluk/viskozite', 'Seawater density/viscosity', 'primary',
        'https://web.mit.edu/seawater/2017_MIT_Seawater_Property_Tables_r2b_2023c.pdf'),
    Reference(('suction_npsh',), ALL, 'ANSI/HI 9.6.1-2024', 'NPSH margin',
        'NPSH marjı (yalnızca kaynak tanımı; tablolar alınmadı)', 'NPSH margin (edition identified only; tables not obtained)', 'secondary'),
    Reference(('fire_foam_system', 'fire_hazen_williams'), ('fire',), 'Türk Loydu Chapter 11 - Fire Fighting Ships (2019)', 'Section 1 C.5.1, C.5.3.3',
        'Yangın söndürme gemisi gereksinimleri', 'Fire fighting ship requirements', 'primary',
        'https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-c/chapter-11-fire-fighting-ships-2019-JULY.pdf'),
)


def references_for(module: str, family: str | None) -> tuple[Reference, ...]:
    return tuple(r for r in REFERENCES if module in r.modules and (family is None or family in r.families))
