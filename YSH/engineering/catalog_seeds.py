"""Approved initial records; absent source data stays absent. One factory rule source."""
from uuid import uuid5,NAMESPACE_URL
from functools import lru_cache
from engineering.catalog import FluidSpecification,MaterialSurface,EngineeringRule

def identity(code): return uuid5(NAMESPACE_URL,'d243:engineering:'+code)
PROFILES=('D243','EVERLLENCE','TL_FFS','TL_LT500','CUNI_REFERENCE','WARTSILA')

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
            result.append(FluidSpecification(code=code+'_'+parameter.upper(),fluid_id=identity('fluid:'+code),name=name,fluid_group=group,
                property_name=parameter,unit=unit,source_authority=authority,source_document=document,
                source_note='Exact applicable property and reference temperature require source verification.',
                is_factory=True,id=identity('property:'+code+':'+parameter)))
    return tuple(result)

@lru_cache(maxsize=1)
def surface_seeds():
    definitions=(('CARBON_NEW','Carbon Steel / New Commercial','Carbon Steel','NEW_COMMERCIAL',.045),
        ('STAINLESS_NEW','Stainless Steel / New Clean','Stainless Steel','NEW_CLEAN',.015),
        ('GALVANIZED_NEW','Galvanized Steel / New','Galvanized Steel','NEW',.15),
        ('CUNI_9010_NEW','Cu-Ni 90/10 / New Drawn','Cu-Ni 90/10','NEW_DRAWN',.0015),
        ('COPPER_DRAWN','Copper / Drawn','Copper','DRAWN',.0015),
        ('HDPE_NEW','PE100 / HDPE','HDPE','NEW',.00152),
        ('PVC_NEW','PVC / Smooth','PVC','SMOOTH',None),('GRE_NEW','GRP / GRE','GRP / GRE','NEW',None),
        ('CAST_IRON_NEW','Cast Iron / New','Cast Iron','NEW',None),
        ('CARBON_CORRODED','Carbon Steel / Corroded','Carbon Steel','CORRODED',None))
    return tuple(MaterialSurface(code=code,name=name,material_name=material,surface_condition=condition,roughness_mm=value,
        source_authority='D243 user-approved engineering reference' if value is not None else '',
        source_note='Absolute roughness epsilon, not Darcy f. Exact surface condition applies; source edition not supplied.',
        verification='RECOMMENDATION' if value is not None else 'SOURCE_REQUIRED',is_factory=True,id=identity('surface:'+code))
        for code,name,material,condition,value in definitions)

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
    for code,name in (('BALLAST','Ballast'),('BILGE','Bilge'),('CUNI_9010','90/10 Cu-Ni source-specific maximum'),('CUNI_7030','70/30 Cu-Ni source-specific maximum'),('WARTSILA','Wärtsilä applicable profile')):
        result.append(EngineeringRule(code=code,name=name,profile_id=identity('profile:WARTSILA' if code=='WARTSILA' else 'profile:CUNI_REFERENCE' if code.startswith('CUNI') else 'profile:D243'),
            service=code if code in ('BALLAST','BILGE') else '',source_authority='Wärtsilä' if code=='WARTSILA' else '',notes='Exact applicable source/profile required; no invented numeric rule.',is_factory=True,id=identity('rule:'+code)))
    return tuple(result)

def d243_rule(): return rule_seeds()[0]
