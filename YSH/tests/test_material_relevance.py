from services.library_scope import material_relevant

def test_cuni_only_for_seawater():
    assert not material_relevant('fuel', 'Cu-Ni 90/10', 'x')
    assert not material_relevant('fire', 'CuNi10Fe', '')
    assert material_relevant('seawater', 'Cu-Ni 90/10')
    assert material_relevant('fuel', 'AISI 316L', 'AISI 316L')
    assert material_relevant(None, 'Cu-Ni 90/10')
