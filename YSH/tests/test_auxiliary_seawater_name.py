"""Family presentation changes without changing fluids, saved IDs or rules."""
import pytest

from core.project_family import FAMILY_KEYS, family_navigation, project_family
from i18n.translator import Translator
from ui.workspace_navigation import FAMILIES, MODULES
from services.system_context_service import DEFAULT_SYSTEMS
from engineering.pipe_design.wall_standards import auxiliary_cuni_stress


@pytest.mark.parametrize('language,label,fluid',[
    ('tr','Yardımcı Deniz Suyu','Deniz Suyu'),
    ('en','Auxiliary Seawater','Seawater'),
])
def test_shared_family_labels_leave_fluid_and_identity_unchanged(language,label,fluid):
    tr=Translator(language).translate
    assert tr(FAMILY_KEYS['seawater'])==label
    assert tr(FAMILIES['seawater'])==label
    assert tr('word.family.seawater')==label
    assert tr('engineering.fluid.seawater')==fluid
    assert project_family({'navigation':family_navigation('seawater')})=='seawater'
    assert MODULES['seawater']==('pipe_design','discharge_head_loss','suction_npsh')
    assert next(s for s in DEFAULT_SYSTEMS if s.code=='SEA_WATER').name_tr=='Deniz Suyu'


def test_display_rename_cannot_expand_stress_scope():
    assert auxiliary_cuni_stress('CuNi10Fe','seawater',50)['value_mpa']==68
    assert auxiliary_cuni_stress('CuNiFe10','seawater',75)['value_mpa']==68
    assert auxiliary_cuni_stress('316L','seawater',50) is None
    assert auxiliary_cuni_stress('CuNi10Fe','fuel',50) is None
    from engineering.validation import ValidationError
    with pytest.raises(ValidationError):auxiliary_cuni_stress('CuNi10Fe','seawater',100)
