"""Approved initial records; absent source data stays absent. One factory rule source."""
from uuid import uuid5,NAMESPACE_URL
from functools import lru_cache
from engineering.catalog import FluidSpecification,MaterialSurface,EngineeringRule

def identity(code): return uuid5(NAMESPACE_URL,'d243:engineering:'+code)
PROFILES=('D243','EVERLLENCE','TL_FFS','TL_LT500','CUNI_REFERENCE','WARTSILA')

# ISO 8217:2017 Table 1 (distillates) as printed in a supplier table (Monjasa, 2020); the licensed
# standard text itself was not read. Viscosity bounds are kinematic viscosity at 40 °C in mm²/s (= cSt).
ISO_8217_2017_DISTILLATE={'DMA':{'viscosity_40c':(2.0,6.0),'density_15c_max':890.0},
    'DMZ':{'viscosity_40c':(2.0,6.0),'density_15c_max':890.0},
    'DMB':{'viscosity_40c':(2.0,11.0),'density_15c_max':900.0}}
ISO_SUPPLIER_NOTE='ISO 8217:2017 kinematic viscosity at 40 °C as printed in a supplier table (Monjasa, 2020); licensed standard not read.'

@lru_cache(maxsize=1)
def fluid_seeds():
    definitions=[('F76','NATO F-76 Naval Distillate','DIESEL_FUEL','MIL-DTL-16884R',800,876,838,1.7,4.3,3.,40),
        ('F44','NATO F-44 / JP-5','AVIATION_FUEL','MIL-DTL-5624X',788,845,816.5,None,7.,None,-20)]
    result=[]
    for code,name,group,document,dmin,dmax,ddefault,vmin,vmax,vdefault,temp in definitions:
        for parameter,unit,lo,hi,default,temperature in (('density','kg/m³',dmin,dmax,ddefault,15),('kinematic_viscosity','cSt',vmin,vmax,vdefault,temp)):
            result.append(FluidSpecification(code=code+'_'+parameter.upper(),fluid_id=identity('fluid:'+code),
                name=name,fluid_group=group,property_name=parameter,unit=unit,source_min=lo,source_max=hi,
                default_value=default,default_method='DERIVED_MIDPOINT' if default is not None else 'SOURCE_REQUIRED',
                reference_temperature_c=temperature,source_authority='US Department of Defense',source_document=document,
                source_edition=document[-1],source_note='User-approved specification range. Midpoint is a D243 derived default, not a source nominal.',
                verification='VERIFIED',is_factory=True,id=identity('property:'+code+':'+parameter)))
    for code,name,group,authority,document in [
        ('DMA','ISO-F-DMA / MGO','DIESEL_FUEL','ISO','ISO 8217:2024'),('DMZ','ISO-F-DMZ','DIESEL_FUEL','ISO','ISO 8217:2024'),
        ('DMB','ISO-F-DMB / MDO','DIESEL_FUEL','ISO','ISO 8217:2024'),
        *[(c,c.replace('_',' '),'HEAVY_FUEL','ISO','ISO 8217:2024') for c in ('RMA_20','RME_180','RMG_380','RMK_500')],
        ('WATER','Fresh Water','FRESH_WATER','',''),('SEAWATER','Seawater','SEA_WATER','',''),
        ('LUBE_OIL','Lubricating Oil','LUBE_OIL','',''),('CONTROL_AIR','Control Air','CONTROL_AIR','',''),('STARTING_AIR','Starting Air','STARTING_AIR','','')]:
        for parameter,unit in (('density','kg/m³'),('kinematic_viscosity','cSt')):
            limits=ISO_8217_2017_DISTILLATE.get(code)
            if limits and parameter=='kinematic_viscosity':
                lo,hi=limits['viscosity_40c']
                result.append(FluidSpecification(code=code+'_'+parameter.upper(),fluid_id=identity('fluid:'+code),name=name,fluid_group=group,
                    property_name=parameter,unit=unit,source_min=lo,source_max=hi,default_value=(lo+hi)/2,default_method='DERIVED_MIDPOINT',
                    reference_temperature_c=40,source_authority='ISO (via supplier table)',source_document='ISO 8217:2017',source_edition='2017',
                    source_note=ISO_SUPPLIER_NOTE+' Midpoint is a D243 derived default (average), not a source nominal; enter a measured or contract value to override.',
                    verification='LIMITED_APPLICABILITY',is_factory=True,id=identity('property:'+code+':'+parameter)))
                continue
            note='Exact applicable property and reference temperature require source verification.'
            maximum=None
            if limits and parameter=='density':
                maximum=limits['density_15c_max']
                note=('Maximum density at 15 °C per ISO 8217:2017 as printed in a supplier table ('+str(maximum)+' kg/m³); a limit, not a typical value. '
                      'The standard gives no minimum, so no average is offered. Enter the supplier or lab value.')
            result.append(FluidSpecification(code=code+'_'+parameter.upper(),fluid_id=identity('fluid:'+code),name=name,fluid_group=group,
                property_name=parameter,unit=unit,source_max=maximum,reference_temperature_c=15 if maximum else None,
                source_authority=authority,source_document=document,source_note=note,
                is_factory=True,id=identity('property:'+code+':'+parameter)))
    return tuple(result)

HI_DOCUMENT='Hydraulic Institute Data Tool, Fluid Flow - Pipe Frictional Losses, Table 3.A.1 (updated 2024-07-19)'
HI_SURFACE_NOTES={
    'PVC_NEW':'Absolute roughness epsilon. The table has no PVC row; 0.00152 mm is its plastic drawn-tubing value. Confirm for the actual pipe.',
    'CAST_IRON_NEW':'Absolute roughness epsilon. 0.122 mm is the table value for asphalt-dipped cast iron (the lower of the two cast iron rows). Uncoated cast iron is 0.26 mm (see Cast Iron / Uncoated). The table says to add 15 % for commercial installations.',
    'CAST_IRON_UNCOATED':'Absolute roughness epsilon. 0.26 mm is the table value for uncoated cast iron. The table says to add 15 % for commercial installations.'}

@lru_cache(maxsize=1)
def surface_seeds():
    definitions=(('CARBON_NEW','Carbon Steel / New Commercial','Carbon Steel','NEW_COMMERCIAL',.045),
        ('STAINLESS_NEW','Stainless Steel / New Clean','Stainless Steel','NEW_CLEAN',.015),
        ('GALVANIZED_NEW','Galvanized Steel / New','Galvanized Steel','NEW',.15),
        ('CUNI_9010_NEW','Cu-Ni 90/10 / New Drawn','Cu-Ni 90/10','NEW_DRAWN',.0015),
        ('COPPER_DRAWN','Copper / Drawn','Copper','DRAWN',.0015),
        ('HDPE_NEW','PE100 / HDPE','HDPE','NEW',.00152),
        ('PVC_NEW','PVC / Smooth','PVC','SMOOTH',.00152),('GRE_NEW','GRP / GRE','GRP / GRE','NEW',None),
        ('CAST_IRON_NEW','Cast Iron / New','Cast Iron','NEW',.122),
        ('CAST_IRON_UNCOATED','Cast Iron / Uncoated','Cast Iron','UNCOATED',.26),
        ('CARBON_CORRODED','Carbon Steel / Corroded','Carbon Steel','CORRODED',None))
    def build(code,name,material,condition,value):
        reference=HI_SURFACE_NOTES.get(code)
        return MaterialSurface(code=code,name=name,material_name=material,surface_condition=condition,roughness_mm=value,
            source_authority=('Hydraulic Institute' if reference else 'D243 user-approved engineering reference') if value is not None else '',
            source_document=HI_DOCUMENT if reference else '',
            source_note=reference or 'Absolute roughness epsilon, not Darcy f. Exact surface condition applies; source edition not supplied.',
            verification='RECOMMENDATION' if value is not None else 'SOURCE_REQUIRED',is_factory=True,id=identity('surface:'+code))
    return tuple(build(*row) for row in definitions)

@lru_cache(maxsize=1)
def rule_seeds():
    result=[EngineeringRule(code='D243_FUEL_MAX',name='D243 Fuel Velocity Criterion',profile_id=identity('profile:D243'),
        system_family='fuel',rule_nature='D243_CRITERION',recommended_max=7.,source_authority='D243',source_document='D243',
        verification='VERIFIED',notes='Internal criterion; not a classification HARD_LIMIT. Does not prevent calculation.',
        is_factory=True,id=identity('rule:D243_FUEL_MAX'))]
    ranges={'DIESEL_FUEL':((.5,1.),(1.5,2.)), 'HEAVY_FUEL':((.3,.8),(1.,1.8)),
        'LUBE_OIL':((.5,1.),(1.5,2.5)), 'FRESH_WATER':((1.,2.),(1.5,3.)), 'SEA_WATER':((1.,1.5),(1.5,2.5))}
    for group,pairs in ranges.items():
        for line,(lo,hi) in zip(('SUCTION','DELIVERY'),pairs):
            code='EVERLLENCE_'+group+'_'+line
            result.append(EngineeringRule(code=code,name=group.replace('_',' ')+' / '+line.title(),profile_id=identity('profile:EVERLLENCE'),
                fluid_group=group,line_type=line,rule_nature='RECOMMENDED_RANGE',recommended_min=lo,recommended_max=hi,
                source_authority='Everllence',source_document='Project Guide reference profile',verification='RECOMMENDATION',
                applicability='',notes='User-approved starting profile. Engine/project guide edition must be selected before claiming applicability. Other editions may differ.',
                is_factory=True,id=identity('rule:'+code)))
    for group,lo,hi in (('CONTROL_AIR',2.,10.),('STARTING_AIR',25.,30.)):
        code='EVERLLENCE_'+group
        result.append(EngineeringRule(code=code,name=group.replace('_',' '),profile_id=identity('profile:EVERLLENCE'),fluid_group=group,
            rule_nature='RECOMMENDED_RANGE',recommended_min=lo,recommended_max=hi,source_authority='Everllence',source_document='Project Guide reference profile',
            verification='RECOMMENDATION',notes='Line length and pressure drop can require different design values. Exact edition/profile not supplied.',is_factory=True,id=identity('rule:'+code)))
    for line,limit in (('SUCTION',2.),('DELIVERY',4.)):
        code='TL_FFS_'+line
        result.append(EngineeringRule(code=code,name='TL Fire Fighting Ships / '+line.title(),profile_id=identity('profile:TL_FFS'),system_family='fire',line_type=line,
            rule_nature='HARD_LIMIT',hard_max=limit,source_authority='Türk Loydu',source_document='Chapter 11 - Fire Fighting Ships',source_edition='July 2019',source_clause='Section 1, C.5.3.3',
            applicability='TL_FFS',verification='LIMITED_APPLICABILITY',notes='Explicit Fire Fighting Ships applicability required; not universal to every vessel.',is_factory=True,id=identity('rule:'+code)))
    result.append(EngineeringRule(code='TL_FFS_NPSH',name='TL Fire Fighting Ships / NPSH Margin',profile_id=identity('profile:TL_FFS'),system_family='fire',
        parameter='npsh_margin',unit='m',rule_nature='HARD_LIMIT',hard_min=1.,source_authority='Türk Loydu',source_document='Chapter 11 - Fire Fighting Ships',source_edition='July 2019',source_clause='Section 1, C.5.1',applicability='TL_FFS',verification='LIMITED_APPLICABILITY',is_factory=True,id=identity('rule:TL_FFS_NPSH')))
    for material,limit in (('Galvanized Steel',3.),('Copper',2.)):
        code='TL_LT500_'+material.upper().replace(' ','_')
        result.append(EngineeringRule(code=code,name='TL <500 GT / '+material,profile_id=identity('profile:TL_LT500'),fluid_group='SEA_WATER',material=material,
            rule_nature='HARD_LIMIT',hard_max=limit,source_authority='Türk Loydu',source_document='User-approved ships less than 500 GT profile',applicability='TL_LT500',
            verification='LIMITED_APPLICABILITY',notes='Only explicit <500 GT scope. Exact document edition/clause requires confirmation; never universal TL.',is_factory=True,id=identity('rule:'+code)))
    result.extend(cuni_wartsila_rules())
    return tuple(result)

def d243_rule(): return rule_seeds()[0]


CDA_DOCUMENT = 'Copper Development Association - Copper-Nickel Seawater System Design (copper.org)'
CDA_CLAUSE = 'Typical maximum flow velocity table; cites BS MA 18 and DIN 85004-2'
CDA_NOTE = ('Typical maximum; depends on alloy, pipe diameter and specification. Reduce by 0.25-0.5 m/s with rolled-over flanges '
            'and by 1-1.5 m/s with entrained sand. Guidance, not a hard limit.')
WARTSILA_DOCUMENT = 'Wärtsilä 31 Product Guide'
WARTSILA_CLAUSE = 'Table 5-1, recommended maximum velocities on pump delivery side, for guidance'
WARTSILA_NOTE = 'Engine product-guide recommendation for sea water piping on the pump delivery side; not a classification rule.'


def cuni_wartsila_rules():
    """Cu-Ni and Wärtsilä seawater maxima that replace the old unfilled placeholder rows."""
    rows = []
    for code, name, material, limit in (('CUNI_9010', '90/10 Cu-Ni / typical maximum velocity', 'Cu-Ni 90/10', 3.5),
                                        ('CUNI_7030', '70/30 Cu-Ni / typical maximum velocity', 'Cu-Ni 70/30', 4.0)):
        rows.append(EngineeringRule(code=code, name=name, profile_id=identity('profile:CUNI_REFERENCE'), fluid_group='SEA_WATER', material=material,
            rule_nature='RECOMMENDED_MAX', recommended_max=limit, source_authority='Copper Development Association', source_document=CDA_DOCUMENT,
            source_edition='Web publication, read 2026-11-27', source_clause=CDA_CLAUSE, verification='RECOMMENDATION', notes=CDA_NOTE,
            is_factory=True, id=identity('rule:' + code)))
    for code, material, limit in (('WARTSILA_GALVANIZED', 'Galvanized Steel', 2.5), ('WARTSILA_ALBRASS', 'Aluminium Brass', 2.5),
                                  ('WARTSILA_CUNI9010', 'Cu-Ni 90/10', 3.0), ('WARTSILA_CUNI7030', 'Cu-Ni 70/30', 4.5)):
        rows.append(EngineeringRule(code=code, name='Wärtsilä / ' + material + ' / sea water delivery', profile_id=identity('profile:WARTSILA'),
            fluid_group='SEA_WATER', line_type='DELIVERY', material=material, rule_nature='RECOMMENDED_MAX', recommended_max=limit,
            source_authority='Wärtsilä', source_document=WARTSILA_DOCUMENT, source_edition='a1 - 18 October 2016', source_clause=WARTSILA_CLAUSE,
            verification='RECOMMENDATION', notes=WARTSILA_NOTE, is_factory=True, id=identity('rule:' + code)))
    return rows
