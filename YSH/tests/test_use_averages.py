"""Opt-in specification averages: blank by default, midpoint only when requested, never an operating point."""
from engineering.system_context import ContextReference, SystemContext
from engineering.catalog_seeds import identity
from .test_project_engineering_context import catalog, chosen  # noqa: F401


def test_blank_by_default_and_midpoint_when_requested(catalog):
    context = chosen(catalog)
    off = catalog.hydraulic_references(context)
    assert off['kinematic_viscosity']['default_value'] is None and off['density']['default_value'] is None
    on = catalog.hydraulic_references(context, True)
    assert on['kinematic_viscosity']['default_value'] == 3 and on['density']['default_value'] == 838
    assert on['kinematic_viscosity']['default_method'] == 'DERIVED_MIDPOINT'


def test_source_required_fuel_stays_blank_even_with_averages(catalog):
    heavy = catalog.hydraulic_references(chosen(catalog, fuel='RMG_380'), True)
    assert heavy['kinematic_viscosity']['default_value'] is None
