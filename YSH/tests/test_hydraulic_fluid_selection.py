"""Operating properties are exact-condition references, never fuel limit defaults."""
import json
import pytest
from engineering.system_context import SystemContext
from services.system_context_service import reference
from services.engineering_catalog_service import EngineeringCatalogService
from engineering.basis import basis_rows
from i18n.translator import Translator
from reporting.word_presentation import basis_explanations


@pytest.fixture
def catalog(library_database):return EngineeringCatalogService(library_database)


@pytest.mark.parametrize('code,temp,salinity,rho,nu',[('WATER',20,None,998.,1.004),('SEAWATER',20,35,1024.9,1.05),('SEAWATER',40,35,1018.3,.695)])
def test_exact_mapping_and_units(catalog,code,temp,salinity,rho,nu):
    fluid=catalog.completion.resolve_fluid(code)
    context=SystemContext(fluid=reference(fluid),fluid_temperature_c=temp,fluid_salinity_g_kg=salinity,fluid_reference_pressure_mpa=.101325)
    refs=catalog.hydraulic_references(context)
    assert refs['density']['default_value']==rho and refs['density']['unit']=='kg/m³'
    assert refs['kinematic_viscosity']['default_value']==nu and refs['kinematic_viscosity']['unit']=='cSt'
    assert refs['density']['source_evidence']['revision_date']=='2023-12-09'
    between=catalog.hydraulic_references(context.changed(fluid_temperature_c=temp+1))  # computed from the published correlation
    assert between['density']['default_method']=='CORRELATION' and between['density']['source_evidence']['document_number'].startswith('Desalination')
    assert abs(between['density']['default_value']-rho)<1.5 and abs(between['kinematic_viscosity']['default_value']-nu)<.06
    assert all(catalog.hydraulic_references(context.changed(fluid_temperature_c=200))[n]['default_value'] is None for n in ('density','kinematic_viscosity'))
    for change in ({'fluid_reference_pressure_mpa':None},{'fluid_reference_pressure_mpa':8}):
        assert all(catalog.hydraulic_references(context.changed(**change))[n]['default_value'] is None for n in ('density','kinematic_viscosity'))
    if code=='SEAWATER':
        assert catalog.hydraulic_references(context.changed(fluid_salinity_g_kg=None))['density']['default_value'] is None


@pytest.mark.parametrize('code',['F76','F44','LUBE_OIL','WASTE_OIL','FOAM_SOLUTION','HVAC_AIR','COMPRESSED_AIR'])
def test_missing_operating_data_never_uses_specification_midpoint(catalog,code):
    fluid=catalog.completion.resolve_fluid(code)
    context=SystemContext(fluid=reference(fluid),fluid_temperature_c=15,fluid_reference_pressure_mpa=.101325)
    for row in catalog.hydraulic_references(context).values():
        if row['property_name'] not in ('density','kinematic_viscosity'):continue
        assert row['default_value'] is None and row['verification']=='SOURCE_REQUIRED'


def test_conditions_roundtrip_and_frozen_presentation(catalog,monkeypatch):
    fluid=catalog.completion.resolve_fluid('SEAWATER')
    context=SystemContext(fluid=reference(fluid),fluid_temperature_c=20,fluid_salinity_g_kg=35,fluid_reference_pressure_mpa=.101325)
    assert SystemContext.from_workspace({'system_context':context.to_payload()})==context
    legacy=context.to_payload();legacy.pop('fluid_reference_pressure_mpa')
    assert SystemContext.from_workspace({'system_context':legacy}).fluid_reference_pressure_mpa is None
    payload={'fluid_conditions':{'temperature_c':20,'salinity_g_kg':35,'pressure_mpa':.101325},
        'values':[{'reference':r,'used_value':r['default_value'],'status':'LINKED'} for r in catalog.hydraulic_references(context).values()]}
    frozen=json.dumps(payload)
    monkeypatch.setattr(catalog,'hydraulic_references',lambda _:pytest.fail('live historical lookup'))
    for language in ('tr','en'):
        tr=Translator(language).translate
        assert (tr('hydro.condition.pressure_mpa'),'0.101325') in basis_rows(payload,tr)
        assert any(tr('hydro.condition.salinity_g_kg') in p for p in basis_explanations(payload,language))
    assert json.dumps(payload)==frozen


@pytest.mark.parametrize('pressure',[0,-.1,float('nan')])
def test_absolute_property_pressure_must_be_positive_finite(pressure):
    with pytest.raises(ValueError):SystemContext(fluid_reference_pressure_mpa=pressure)
