"""Reviewed source facts, separate from engineering rules and mutable user data.

Dates retain their published precision. Copyright, adoption, revision and entry
into force are distinct events. Bibliographic verification never authorizes a value.
"""
from dataclasses import asdict, dataclass
import hashlib
import json

AUDIT_DATE = '2026-11-24'


@dataclass(frozen=True)
class SourceEvidence:
    key: str
    owner: str
    document_number: str
    edition: str
    publication_date: str | None
    publication_precision: str | None
    clause: str
    applicability: str
    scope: str
    url: str
    revision_date: str | None = None
    effective_date: str | None = None
    copyright_year: str | None = None
    adoption_date: str | None = None
    amendments: str | None = None
    verification_date: str = AUDIT_DATE

    def payload(self):
        return asdict(self)


SOURCES = (
    SourceEvidence('MIT_WATER_TABLES_2023','MIT / Nayar, Sharqawy, Lienhard','Seawater Thermophysical Properties Library - Tables','Library 3.1.3 (2016-12-21); tables updated 2023-12-09',None,None,
        'Tables 3 and 21, printed pp.3 and 21 (PDF pp.6 and 24)',
        'Published correlation tables, not measured batch properties. Stored subset: T=10/20/40°C, S=0 or 30/35/40 g/kg, P=0.101325 MPa. No interpolation. S=0 is pure-water approximation.',
        'LIMITED_VALUE_SCOPE','https://web.mit.edu/seawater/2017_MIT_Seawater_Property_Tables_r2b_2023c.pdf',revision_date='2023-12-09'),
    SourceEvidence('EN10216_1_2013','CEN / DIN','EN 10216-1:2013','2013; DIN adoption 2014-03','2013-12','month',
        '8.3.1 Table 5; 7.2 Table 1; printed p.10 (preview PDF p.69)',
        'P235TR2 / 1.0255 seamless non-alloy TR2 tubes; room-temperature properties, specified delivery condition. T>60 mm by agreement. Not allowable stress or roughness. TS national adoption/date not verified.',
        'LIMITED_VALUE_SCOPE','https://api.pageplace.de/preview/DT0400.9783410304173_A41769316/preview-9783410304173_A41769316.pdf'),
    SourceEvidence('F76_R','US Department of Defense','MIL-DTL-16884R','R','2025-01-03','day',
        'Table I, p.7','F-76: density at 15°C; viscosity at 40°C. Midpoints are D243-derived, not source nominals.',
        'NUMERIC_RANGE','https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=12122'),
    SourceEvidence('F44_X','US Department of Defense','MIL-DTL-5624X','X','2024-02-12','day',
        'Table I, p.10','JP-5/F-44: density at 15°C; viscosity maximum at -20°C. No viscosity default verified.',
        'NUMERIC_RANGE','https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=5558'),
    SourceEvidence('ISO8217_2024','ISO','ISO 8217:2024','7','2024-05-30','day',
        'Publisher life-cycle stage 60.60','Document identity/date only; normative grade/property tables not obtained.',
        'BIBLIOGRAPHY_ONLY','https://www.iso.org/standard/80579.html'),
    SourceEvidence('TL_FFS_2019','Türk Loydu','Chapter 11 - Fire Fighting Ships','July 2019','2019-07','month',
        'Section 1 C.5.1; C.5.3.3, p.1-11','TL_FFS only. Retrieved PDF includes RCS 03/2021 and 02/2022; not a universal vessel rule.',
        'LIMITED_VALUE_SCOPE','https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-c/chapter-11-fire-fighting-ships-2019-JULY.pdf',
        effective_date='2019-07-01', amendments='RCS 03/2021; RCS 02/2022 (retrieved consolidated PDF)'),
    SourceEvidence('TL_LT500_2019','Türk Loydu','Chapter 35 - Tentative Rules for Ships less than 500 GT','July 2019','2019-07','month',
        'Section 4 A.1.2.5, p.4-2','Galvanised steel/copper seawater piping in this explicit scope. Original edition of generic D243 profile is unspecified.',
        'CORROBORATION_ONLY','https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-c/chapter-35-Tentative-Rules-For-Ships-Less-Than-500-GRT-%28JULY-2019%29.pdf',
        effective_date='2019-07-01'),
    SourceEvidence('EVERLLENCE_L3240CD_NR','Everllence','L32/40CD GenSet NR Project Guide - Marine','10.2026/4.0','2026-10','month',
        '6.2.1, Table 85, pp.163-164/311','Engine-specific non-binding recommendations. Do not assign this variant/edition to generic profiles. Air ranges are delivery-side only.',
        'CORROBORATION_ONLY','https://www.everllence.com/applications/projectguides/4stroke/Genset/PG_G-II_L3240CD%20NR.pdf',
        revision_date='2026-10-13',copyright_year='2025'),
    SourceEvidence('EN10220_2002','CEN','EN 10220:2002','2002','2002-12','month',
        'Cover; contents clause 6','Bibliography verified via CEN-member preview; all 148 local dimensions not reverified against licensed tables. Not an allowable-stress standard.',
        'BIBLIOGRAPHY_ONLY','https://csnonlinefirmy.agentura-cas.cz/html_nahledy/42/69049/69049_nahled.htm'),
    SourceEvidence('DIN_EN10220_2003','DIN','DIN EN 10220:2003-03','German adoption','2003-03','month',
        'Publisher catalogue','National adoption date; must not replace the EN publication date.',
        'BIBLIOGRAPHY_ONLY','https://www.dinmedia.de/en/standard/din-en-10220/54122066'),
    SourceEvidence('HI_NPSH_2024','Hydraulic Institute','ANSI/HI 9.6.1-2024','2024',None,None,
        'Publisher catalogue','Edition identified; full margin tables/applicability not obtained. ANSI approval 2024-07-29 is not established as publication date.',
        'BIBLIOGRAPHY_ONLY','https://www.pumps.org/what-we-do/standards/page/2/?tab=individual-standards'),
    SourceEvidence('SKUM_ZF_04','Johnson Controls / SKUM','FDS-2017084-04','04',None,None,
        'p.2 Calculations','Hazen-Williams equation/unit package only. Does not authorize seawater applicability or a universal C value.',
        'EQUATION_UNITS_ONLY','https://docs.johnsoncontrols.com/specialhazards/api/khub/documents/dEMK03nJ_8bSJITUY0xc0Q/content',copyright_year='2024'),
    SourceEvidence('EPA_EPANET22','US EPA','EPA/600/R-20/133','EPANET 2.2','2020','year',
        '3.1; Tables 3.1-3.2','Water-distribution method context; not marine approval or verification of D243 loss coefficients.',
        'METHOD_CONTEXT_ONLY','https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P10113EM.txt'),
    SourceEvidence('SHARQAWY_2010','MIT / Sharqawy, Lienhard, Zubair','Desalination and Water Treatment 16 (2010) 354-380','April 2010','2010-04','month',
        'Density Eqs. 8-9; dynamic viscosity Eqs. 22-23',
        'Atmospheric-pressure correlations, 0-180 degC, 0-150 g/kg (density +/-0.1 %, viscosity +/-1.5 % as published). Pressure dependence not applied; pressure limited to 1 MPa. Computed values reproduce the stored MIT table points to rounding.',
        'LIMITED_VALUE_SCOPE','https://dspace.mit.edu/handle/1721.1/69157'),
    SourceEvidence('CGPM_GRAVITY','BIPM / CGPM','3rd CGPM Declaration 2','1901','1901','year',
        'Declaration 2','Conventional standard gravity; not a measured local acceleration.',
        'VALUE_ONLY','https://www.bipm.org/en/committees/cg/cgpm/3-1901/resolution-2'),
    SourceEvidence('IMO_MSC98','IMO','MSC.98(73)','As adopted',None,None,
        'Annex chapters 6, 7, 8, 14','Adopted 2000-12-05; effective 2002-07-01. Historical instrument, not current consolidated compliance.',
        'HISTORICAL_INSTRUMENT','https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.98%2873%29.pdf',
        adoption_date='2000-12-05',effective_date='2002-07-01'),
    SourceEvidence('IMO_FSS2026','IMO','FSS Code IC155E','2026',None,None,
        'Current publications list','Edition listed; full consolidated normative text not reviewed.',
        'BIBLIOGRAPHY_ONLY','https://www.imo.org/en/publications/pages/currentpublications.aspx'),
    SourceEvidence('VIKING_XMAX','Viking','F_081620 / XMAX','Unrecorded',None,None,
        'Product description','Product-specific volumetric concentration example; no D243 default or product recommendation.',
        'PRODUCT_ONLY','https://www.vikinggroupinc.com/products/foam-products/high-ex-fff/xmax'),
    SourceEvidence('FOMTEC_XMAX','Dafo Fomtec AB','LS xMax','Revised 2025-04-22',None,None,
        'pp.1-2','Product-specific application/concentration; revision date is not established as publication date.',
        'PRODUCT_ONLY','https://www.fomtec.com/wp-content/uploads/2022/04/Fomtec%E2%94%AC%C2%AE-LS-xMax.pdf',revision_date='2025-04-22'),
    SourceEvidence('NAFFCO_FILMPLUS','NAFFCO','FILMPLUS AFFF','Unrecorded',None,None,
        'Use Concentration table','Product-specific examples; no dated revision supplied.',
        'PRODUCT_ONLY','https://www.naffco.com/en/aqueous-film-forming-foam-afff'),
    SourceEvidence('VIKING_NOZZLE','Viking','F_062104','20.06.15 Rev.20.1',None,None,
        'Model E VK810-VK817 technical data','Date code retained verbatim; no unsupported date interpretation or Nozzle activation.',
        'PRODUCT_ONLY','https://www.vikinggroupinc.com/sites/default/files/migrated/062104.pdf'),
    SourceEvidence('NFPA13_2025','NFPA','NFPA 13','2025',None,None,
        'LiNK edition page','Full standard unavailable to this audit; no C-table verification from edition number.',
        'NOT_ACCESSIBLE','https://link.nfpa.org/all-publications/13/2025'),
    SourceEvidence('NFPA13_BALLOT','NFPA','NFPA13 A2024 second-draft ballot','2023-12-06 memorandum',None,None,
        'SR-1169 / SR-1171','Committee draft is not an issued normative standard.',
        'DRAFT_ONLY','https://docinfofiles.nfpa.org/files/AboutTheCodes/13/13_A2024_AUT_SSD_SD__ballot_final.pdf',revision_date='2023-12-06'),
    SourceEvidence('TEOS10','IOC / SCOR / IAPSO','TEOS-10','2010',None,None,
        'Official overview','Thermodynamic framework identified. Does not verify stored seawater values, viscosity defaults or Hazen-Williams applicability.',
        'METHOD_CONTEXT_ONLY','https://www.teos-10.org/'),
)
BY_KEY = {source.key: source for source in SOURCES}

# Fingerprints bind evidence to the reviewed numbers, temperatures, units and
# applicability. A changed value, edition or scope cannot inherit verification.
FINGERPRINT_FIELDS = '''source_authority source_document source_edition source_clause
fluid_group property_name unit source_min source_max source_nominal default_value
default_method reference_temperature_c reference_salinity_g_kg system_family service
line_type material parameter rule_nature recommended_min recommended_max hard_min
hard_max applicability verification'''.split()
REVIEWED = {
    'F76_DENSITY': ('F76_R','0c071efda4f970e31dffeabaea51612459c5ffcece8da85e46469dbe8867b421'),
    'F76_KINEMATIC_VISCOSITY': ('F76_R','48827730a94b6ad443d4897c10316da3652a592a5e2feeec728807bb46d66e32'),
    'F44_DENSITY': ('F44_X','dca67fd526edf9c1ac80e4d81ce34201b5b2c958896a5c6b1eecdbd3954e8ad8'),
    'F44_KINEMATIC_VISCOSITY': ('F44_X','0bb208fb150df27cd4a435e8291503b018b558a25a9ced96ca9cb6591fb83cc6'),
    'TL_FFS_SUCTION': ('TL_FFS_2019','1bbdeb87f48419e26057e41a46b8fc12e76edd30e20de1a5125ef80f11fc6249'),
    'TL_FFS_DELIVERY': ('TL_FFS_2019','65cae9d0ebd76bb3bc23b35293f868a10db568e4d795fe080ea04a7660a172c4'),
    'TL_FFS_NPSH': ('TL_FFS_2019','fc803d7b80ae80632f1c529b53e193013a563521f2b343ee1f8c8c54adb48db0'),
}


def fingerprint(record):
    values={name:getattr(record,name) for name in FINGERPRINT_FIELDS if hasattr(record,name)}
    values={key:float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) else value
            for key,value in values.items()}
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def record_evidence(record):
    reviewed=REVIEWED.get(getattr(record,'code',None))
    if reviewed and fingerprint(record)==reviewed[1]:return BY_KEY[reviewed[0]]
    if getattr(record,'source_document',None)=='ISO 8217:2024':return BY_KEY['ISO8217_2024']
    return None


from i18n.catalog_text import catalog_text


def evidence_rows(evidence, translate):
    """Render only recorded/frozen metadata; never look up a historical source."""
    if not evidence:return ()
    tr=translate
    rows=[(tr('sourceaudit.publication_date'),evidence.get('publication_date') or tr('sourceaudit.unknown')),
          (tr('sourceaudit.verification_date'),evidence['verification_date']),
          (tr('sourceaudit.scope'),tr('sourceaudit.scope.'+evidence['scope']))]
    for key in ('document_number','edition','adoption_date','revision_date','effective_date','amendments','clause','applicability','url'):
        if evidence.get(key):rows.append((tr('sourceaudit.'+key),evidence[key] if key=='url' else catalog_text(tr,evidence[key])))
    return tuple(rows)


def source_label_key(source):
    """DPO is explicit confirmed criterion ownership, never inferred from a number."""
    if source.source_type.value in ('D243_CRITERION','PROJECT_CRITERION') and (
        source.source_organization in ('DPO','Dizayn Proje Ofisi') and
        getattr(source.verification_status,'value',None) in ('USER_SUPPLIED','VERIFIED')):
        return 'sourceaudit.dpo'
    return 'formula2.source_type.'+source.source_type.value
