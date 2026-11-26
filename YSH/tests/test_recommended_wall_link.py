from math import pi

from services.discharge_source_adapter import apply_recommended_wall
from .test_pipe_transfer_phase7_v2 import selection


def state(**changes):
    base = {'fields': {'da': '159'}, 'wall_result': {'final_wall_thickness_mm': 2.4},
            'wall_standard_basis': {'nominal_wall_mm': 3.0, 'nominal_standard': 'EEMUA 234/1'}}
    return base | changes


def test_hydraulic_pages_use_recommended_wall_and_outside_diameter():
    source = selection()
    result = apply_recommended_wall(source, state())
    assert result.outside_diameter_mm == 159 and result.selected_wall_thickness_mm == 3.0
    assert result.actual_internal_diameter_mm == 153
    assert result.actual_velocity_m_s == 20 / 3600 / (pi / 4 * 0.153 ** 2)
    assert result.selected_pipe.id != source.selected_pipe.id  # revision tracking sees the change
    assert apply_recommended_wall(source, state()).selected_pipe.id == result.selected_pipe.id  # stable


def test_without_a_matching_recommended_wall_the_library_selection_is_kept():
    source = selection()
    assert apply_recommended_wall(source, state(wall_standard_basis={'nominal_wall_mm': None})) is source
    assert apply_recommended_wall(source, state(wall_result={})) is source
    assert apply_recommended_wall(source, state(fields={'da': ''})) is source
    assert apply_recommended_wall(source, state(fields={'da': '5'})) is source  # wall would exceed the radius
