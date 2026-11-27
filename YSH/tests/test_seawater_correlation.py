from engineering import seawater_properties as sw
import pytest

TABLE = {  # MIT table points (T, S): density kg/m3, kinematic viscosity cSt
    (10, 0): (999.5, 1.307), (10, 35): (1027.0, 1.360), (20, 0): (998.0, 1.004), (20, 30): (1021.1, 1.043),
    (20, 35): (1024.9, 1.050), (20, 40): (1028.8, 1.058), (40, 0): (992.2, 0.658), (40, 35): (1018.3, 0.695)}

@pytest.mark.parametrize('point', TABLE)
def test_reproduces_published_mit_table_points(point):
    density, viscosity = TABLE[point]
    assert sw.density_kg_m3(*point) == pytest.approx(density, abs=0.1)
    assert sw.kinematic_viscosity_cst(*point) == pytest.approx(viscosity, abs=0.0011)

def test_range_checks():
    assert sw.in_range(20, 35, 0.101325) and not sw.in_range(20, None, 0.1) and not sw.in_range(200, 35, 0.1)
    assert not sw.in_range(20, 35, 2.0) and not sw.in_range(20, 200, 0.1)
