"""Small published point subset; no interpolation, extrapolation or new hydraulic rule."""
from engineering.catalog_seeds import identity
from engineering.catalog_completion import OperatingFluidProperty, MechanicalGrade, MechanicalGradeProperty

# Identity aliases are user-requested vocabulary, not a claim of physical equivalence.
FLUID_IDENTITIES = (
    ('LUBE_OIL','Yağlama Yağı','Lubricating Oil','LUBE_OIL',('Lube Oil','Lubricating Oil','Yağlama Yağı')),
    ('WASTE_OIL','Atık / Kirli Yağ','Waste / Dirty Oil','WASTE_OIL',('Waste Oil','Dirty Oil','Waste / Dirty Oil','Atık Yağ','Kirli Yağ')),
    ('SEAWATER','Deniz Suyu','Seawater','SEA_WATER',('Seawater','Sea water','Deniz Suyu','DenizSuyu')),
    ('WATER','Tatlı Su','Fresh Water','FRESH_WATER',('Fresh Water','Freshwater','Tatlı Su')),
    ('F44','NATO F-44 / JP-5','NATO F-44 / JP-5','AVIATION_FUEL',('NATO F-44','F-44','JP-5','NATO F-44 / JP-5')),
    ('F76','NATO F-76','NATO F-76','DIESEL_FUEL',('NATO F-76','F-76','NATO F-76 Naval Distillate')),
    ('FOAM_SOLUTION','Köpük Çözeltisi','Foam Solution','FOAM_SOLUTION',('Foam Solution','Köpük Çözeltisi')),
    ('BLACK_WATER','Siyah Su','Black Water','BLACK_WATER',('Black Water','Blackwater','Siyah Su')),
    ('GREY_WATER','Gri Su','Grey Water','GREY_WATER',('Grey Water','Gray Water','Greywater','Gri Su')),
    ('HVAC_AIR','HVAC Havası','HVAC Air','HVAC_AIR',('HVAC Air','HVAC Havası')),
    ('COMPRESSED_AIR','Basınçlı Hava','Compressed Air','COMPRESSED_AIR',('Compressed Air','Basınçlı Hava')),
)
REQUIREMENTS = {
    'LUBE_OIL':'catalog.condition.oil', 'WASTE_OIL':'catalog.condition.waste',
    'SEA_WATER':'catalog.condition.seawater', 'FRESH_WATER':'catalog.condition.water',
    'AVIATION_FUEL':'catalog.condition.fuel', 'DIESEL_FUEL':'catalog.condition.fuel',
    'FOAM_SOLUTION':'catalog.condition.foam', 'BLACK_WATER':'catalog.condition.wastewater',
    'GREY_WATER':'catalog.condition.wastewater', 'HVAC_AIR':'catalog.condition.hvac',
    'COMPRESSED_AIR':'catalog.condition.compressed',
}

# MIT table 21 density kg/m³; table 3 printed nu*10^7 m²/s.
# Multiplication by 0.1 converts that printed column to mm²/s (cSt).
# Three temperatures, pure-water and three seawater salinities. Source precision retained.
POINTS = (
    (10,0,999.5,13.07),(20,0,998.0,10.04),(40,0,992.2,6.58),
    (10,30,1023.0,13.51),(10,35,1027.0,13.60),(10,40,1030.9,13.69),
    (20,30,1021.1,10.43),(20,35,1024.9,10.50),(20,40,1028.8,10.58),
    (40,30,1014.6,6.89),(40,35,1018.3,6.95),(40,40,1022.1,7.00),
)


def operating_seeds(fluid_ids):
    rows=[]
    for temperature,salinity,density,printed_nu in POINTS:
        fluid_id=fluid_ids['WATER' if salinity==0 else 'SEAWATER']
        for prop,value,unit in (('density',density,'kg/m³'),('kinematic_viscosity',round(printed_nu*.1,3),'cSt')):
            code=f'MIT_WATER_T{temperature}_S{salinity}_{prop.upper()}'
            rows.append(OperatingFluidProperty(code=code,fluid_id=fluid_id,property_name=prop,value=value,unit=unit,
                reference_temperature_c=temperature,reference_salinity_g_kg=salinity,reference_pressure_mpa=.101325,
                source_key='MIT_WATER_TABLES_2023',applicability='catalog.point_scope',verification='VERIFIED',id=identity('operating:'+code)))
    return tuple(rows)


def mechanical_seeds():
    grade=MechanicalGrade(code='P235TR2',designation='P235TR2',material_number='1.0255',standard='EN 10216-1:2013',
        source_key='EN10216_1_2013',applicability='catalog.grade_scope',id=identity('grade:P235TR2:EN10216-1:2013'))
    rows=[]
    for prop,lo,hi,above,up_to in (('Rm',360.,500.,0.,60.),('ReH',235.,None,0.,16.),
                                  ('ReH',225.,None,16.,40.),('ReH',215.,None,40.,60.)):
        code=f'P235TR2_{prop}_{above:g}_{up_to:g}'
        rows.append(MechanicalGradeProperty(code=code,grade_id=grade.id,property_name=prop,minimum_value=lo,
            maximum_value=hi,thickness_above_mm=above,thickness_up_to_mm=up_to,unit='MPa',source_key=grade.source_key,
            applicability='catalog.grade_scope',verification='VERIFIED',id=identity('grade-property:'+code)))
    return grade,tuple(rows)
