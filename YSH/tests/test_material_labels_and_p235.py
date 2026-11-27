from ui.material_labels import material_label
from engineering.pipe_design.wall_standards import cuni_wall_material, is_cuni10


def test_labels_never_repeat_and_show_equivalents():
    assert material_label('ST37', 'ST37') == 'ST37'
    assert material_label('AISI 316L', 'AISI 316L') == 'AISI 316L (1.4404)'
    assert material_label('P235TR2', 'TS EN 10216-1') == 'P235TR2 (TS EN 10216-1)'
    m = cuni_wall_material()
    assert material_label(m.name, m.designation) == 'CuNi10Fe1Mn (CW352H)' and is_cuni10(m.designation)


def test_p235tr2_added_to_existing_and_fresh_libraries(tmp_path):
    from database.library_database import LibraryDatabase
    from repositories.material_repository import MaterialRepository
    from services.material_service import MaterialService
    fresh = LibraryDatabase(tmp_path / 'a.db'); fresh.initialize()
    names = {m.name: m for m in MaterialService(MaterialRepository(fresh)).get_all_materials()}
    assert names['P235TR2'].yield_strength_mpa == 235 and names['P235TR2'].roughness_mm == .045 and 'AISI 316L' in names
    old = LibraryDatabase(tmp_path / 'b.db'); old.initialize()
    service = MaterialService(MaterialRepository(old))
    service.delete_material(names['P235TR2'].id)
    with old.connection() as c:
        c.execute('UPDATE schema_version SET version=10')
    LibraryDatabase(tmp_path / 'b.db').initialize()
    assert 'P235TR2' in {m.name for m in MaterialService(MaterialRepository(old)).get_all_materials()}


def test_st37_st52_have_minimum_yield_in_fresh_and_upgraded_libraries(tmp_path):
    from database.library_database import LibraryDatabase
    from repositories.material_repository import MaterialRepository
    from services.material_service import MaterialService
    db = LibraryDatabase(tmp_path / 'c.db'); db.initialize()
    service = MaterialService(MaterialRepository(db))
    got = {m.name: m.yield_strength_mpa for m in service.get_all_materials()}
    assert got['ST37'] == 235 and got['ST52'] == 355
    with db.connection() as c:  # old library: blank factory yield, schema 11
        c.execute("UPDATE materials SET yield_strength_mpa=NULL, description='' WHERE name IN ('ST37','ST52')")
        c.execute("UPDATE materials SET yield_strength_mpa=300 WHERE name='AISI 304L'")
        c.execute('UPDATE schema_version SET version=11')
    LibraryDatabase(tmp_path / 'c.db').initialize()
    got = {m.name: m.yield_strength_mpa for m in MaterialService(MaterialRepository(db)).get_all_materials()}
    assert got['ST37'] == 235 and got['ST52'] == 355 and got['AISI 304L'] == 300
