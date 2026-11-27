from types import SimpleNamespace as NS
from uuid import uuid4

from services.library_catalog import VISIBLE_CATEGORIES, CATEGORY_BY_CODE
from services.library_scope import (allowed_fluid_ids, category_visible, row_visible, visible_categories)
from ui.library_controller import LibraryController


def test_fuel_scope_hides_fire_and_corrosion_but_keeps_materials_and_roughness():
    groups = {c.group for c in visible_categories('fuel', VISIBLE_CATEGORIES)}
    assert {'fluids', 'materials', 'pipes', 'engineering_rules', 'pumps'} <= groups
    assert not groups & {'fire', 'corrosion', 'systems'}
    assert 'material_surfaces' in {c.code for c in visible_categories('fuel', VISIBLE_CATEGORIES)}


def test_seawater_scope_keeps_corrosion_not_pumps_and_none_means_everything():
    groups = {c.group for c in visible_categories('seawater', VISIBLE_CATEGORIES)}
    assert 'corrosion' in groups and 'pumps' not in groups and 'fire' not in groups
    assert visible_categories(None, VISIBLE_CATEGORIES) == VISIBLE_CATEGORIES
    assert category_visible('fire', CATEGORY_BY_CODE['fire_hw']) and not category_visible('fuel', CATEGORY_BY_CODE['fire_hw'])


def test_fluid_rows_follow_family_groups():
    diesel, sea, mixed = uuid4(), uuid4(), uuid4()
    specs = [NS(fluid_id=diesel, fluid_group='DIESEL_FUEL'), NS(fluid_id=sea, fluid_group='SEA_WATER'),
             NS(fluid_id=mixed, fluid_group='DIESEL_FUEL'), NS(fluid_id=mixed, fluid_group='SEA_WATER')]
    fuel = allowed_fluid_ids('fuel', specs)
    assert fuel == {diesel}
    assert row_visible('fuel', 'fluids', NS(id=diesel), fuel)
    assert not row_visible('fuel', 'fluids', NS(id=sea), fuel)
    assert not row_visible('fuel', 'fluid_properties', NS(fluid_id=sea), fuel)
    assert allowed_fluid_ids(None, specs) is None


def test_rules_filter_by_family_and_fluid_group():
    fuel_rule = NS(system_family='fuel', fluid_group='DIESEL_FUEL')
    fire_rule = NS(system_family='fire', fluid_group='')
    sea_rule = NS(system_family='', fluid_group='SEA_WATER')
    assert row_visible('fuel', 'engineering_rules', fuel_rule, None)
    assert not row_visible('fuel', 'engineering_rules', fire_rule, None)
    assert not row_visible('fuel', 'engineering_rules', sea_rule, None)
    assert row_visible('seawater', 'engineering_rules', sea_rule, None)


def test_controller_row_filter_applies_before_other_filters():
    controller = LibraryController.__new__(LibraryController)
    controller.records = (NS(n=1), NS(n=2)); controller.category = 'x'; controller.service = None
    controller.row_filter = lambda category, row: row.n == 2
    assert controller.filtered() == (NS(n=2),)


def test_v9_fills_blank_factory_rows_but_keeps_user_edits(tmp_path):
    from database.library_database import LibraryDatabase
    path = tmp_path / 'lib.db'

    class V8(LibraryDatabase):
        SCHEMA_VERSION = 8
    V8(path).initialize()
    import sqlite3
    raw = sqlite3.connect(path)
    raw.execute("UPDATE material_surfaces SET roughness_mm=0.5 WHERE code='PVC_NEW'")
    raw.execute("DELETE FROM material_surfaces WHERE code='CAST_IRON_UNCOATED'")
    raw.execute("UPDATE fluid_specifications SET default_value=NULL,source_min=NULL,source_max=NULL,default_method='SOURCE_REQUIRED' "
                "WHERE code='DMB_KINEMATIC_VISCOSITY'")
    raw.execute("UPDATE schema_version SET version=8")
    raw.commit(); raw.close()
    LibraryDatabase(path).initialize()
    raw = sqlite3.connect(path)
    assert raw.execute("SELECT version FROM schema_version").fetchone()[0] == 11
    assert raw.execute("SELECT default_value,source_min,source_max FROM fluid_specifications WHERE code='DMB_KINEMATIC_VISCOSITY'").fetchone() == (6.5, 2.0, 11.0)
    assert raw.execute("SELECT roughness_mm FROM material_surfaces WHERE code='PVC_NEW'").fetchone()[0] == 0.5
    assert raw.execute("SELECT roughness_mm FROM material_surfaces WHERE code='CAST_IRON_UNCOATED'").fetchone()[0] == 0.26


def test_v10_completes_cuni_and_wartsila_rules_and_drops_placeholders(tmp_path):
    from database.library_database import LibraryDatabase
    database = LibraryDatabase(tmp_path / 'lib.db')
    database.initialize()
    with database.connection() as c:  # recreate the pre-v10 state
        c.execute("UPDATE engineering_rules SET recommended_max=NULL, verification='SOURCE_REQUIRED', rule_nature='SOURCE_REQUIRED' WHERE code='CUNI_9010'")
        c.execute("DELETE FROM engineering_rules WHERE code LIKE 'WARTSILA_%'")
        c.execute("INSERT INTO engineering_rules(id,code,name,profile_id,is_factory,verification) SELECT 'x-1','BALLAST','Ballast',profile_id,1,'SOURCE_REQUIRED' FROM engineering_rules WHERE code='CUNI_7030'")
        c.execute('UPDATE schema_version SET version=9')
    LibraryDatabase(tmp_path / 'lib.db').initialize()
    with database.connection() as c:
        rows = {r[0]: r[1] for r in c.execute('SELECT code, recommended_max FROM engineering_rules')}
    assert rows['CUNI_9010'] == 3.5 and rows['WARTSILA_CUNI7030'] == 4.5 and 'BALLAST' not in rows
