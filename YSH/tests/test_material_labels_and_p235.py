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
