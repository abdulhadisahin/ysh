"""Read-only characterization of the visible diameter-only recommendation."""
from uuid import uuid4
import pytest
from .test_fire_phase5cd_navigation import application, shell


@pytest.mark.parametrize('flow,expected,inside,wall',[(350,'DN150',159.3,4.5),(240,'DN125',131.7,4.)])
def test_visible_page_reproduces_reported_cases_without_new_selection_policy(shell,flow,expected,inside,wall):
    w=shell
    assert w._create_project('DN audit '+str(uuid4()),'','','fuel')
    page=w._pages['pipe_design']
    assert page._selected_pipe_standard_code()=='EN_10220'
    page._fields['q'].set(str(flow));page._fields['v'].set('7')
    page._calculate_diameter()
    result=page._diameter_result
    assert result['recommended_dn']==expected
    assert result['recommended_inside_diameter_mm']==pytest.approx(inside)
    assert result['recommended_wall_thickness_mm']==wall
    assert not page._engineering_findings  # The existing warning observes entered V=7.
