"""Semantic validation contracts for editable engineering libraries."""

from __future__ import annotations

import pytest

from engineering.validation import ValidationError
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from services.engineering_constant_service import EngineeringConstantService
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService


def test_pipe_size_validation_renders_through_the_active_language(
    pipe_size_service: PipeSizeService,
) -> None:
    """A missing nominal diameter has no embedded English service sentence."""
    with pytest.raises(ValidationError) as error:
        pipe_size_service.create_pipe_size(
            nominal_diameter="",
            outside_diameter_mm=60.3,
            wall_thickness_mm=3.2,
            inside_diameter_mm=53.9,
        )

    assert error.value.issue.field_key == "field.dn"
    assert render_validation_issue(error.value.issue, Translator("en")) == "DN is required."
    assert render_validation_issue(error.value.issue, Translator("tr")) == "DN gereklidir."


def test_material_duplicate_uses_a_localizable_domain_code(
    material_service: MaterialService,
) -> None:
    """Designation conflicts remain language-neutral below the UI boundary."""
    with pytest.raises(ValidationError) as error:
        material_service.create_material(
            name="Duplicate",
            designation="AISI 304L",
            yield_strength_mpa=190.0,
            roughness_mm=0.015,
        )

    assert error.value.issue.code == "material_duplicate"
    assert render_validation_issue(error.value.issue, Translator("tr")) == (
        "Bu tanıma sahip bir malzeme zaten var."
    )


def test_constant_value_range_uses_a_localizable_semantic_issue(
    engineering_constant_service: EngineeringConstantService,
) -> None:
    """The display-precision range remains unchanged while its error localizes."""
    constant = engineering_constant_service.get_constant("display_decimal_places")
    constant.value = 12.5

    with pytest.raises(ValidationError) as error:
        engineering_constant_service.update_constant(constant)

    assert error.value.issue.code == "constant_value_invalid"
    assert render_validation_issue(error.value.issue, Translator("en")) == (
        "Value must be a whole number from 0 through 12."
    )
