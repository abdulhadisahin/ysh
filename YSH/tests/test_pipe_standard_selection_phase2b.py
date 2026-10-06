"""Phase 2B contracts for visible, standard-scoped pipe selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from engineering.pipe_design.models import PipeDiameterInput
from engineering.validation import ValidationError
from services.pipe_design_service import PipeDesignService


ROOT = Path(__file__).resolve().parents[1]


def test_diameter_recommendation_uses_only_the_explicitly_selected_standard(
    material_service: object,
    pipe_size_service: object,
    engineering_constant_service: object,
) -> None:
    """An alternate standard can recommend its own geometry without EN fallback."""
    alternate = pipe_size_service.create_standard(
        code="PHASE2B_ALT", display_name="Özel Test Standardı"
    )
    pipe_size_service.create_pipe_size(
        nominal_diameter="DN200",
        outside_diameter_mm=219.1,
        wall_thickness_mm=6.0,
        inside_diameter_mm=207.1,
        standard_id=alternate.id,
    )
    service = PipeDesignService(
        material_service, pipe_size_service, engineering_constant_service
    )

    result = service.calculate(
        diameter=PipeDiameterInput(100.0, 2.0), standard_code=alternate.code
    )

    assert result.trace["pipe_standard_code"] == alternate.code
    assert result.diameter is not None
    assert result.diameter.recommended_dn == "DN200"
    assert result.diameter.recommended_outside_diameter_mm == 219.1


def test_missing_explicit_standard_never_falls_back_to_en_10220(
    material_service: object,
    pipe_size_service: object,
    engineering_constant_service: object,
) -> None:
    """A stale persisted selection must fail safely instead of mixing standards."""
    service = PipeDesignService(
        material_service, pipe_size_service, engineering_constant_service
    )

    with pytest.raises(ValidationError) as error:
        service.calculate(
            diameter=PipeDiameterInput(100.0, 2.0),
            standard_code="MISSING_STANDARD",
        )

    assert error.value.issue.code == "pipe_standard_not_found"


def test_selected_standard_without_geometry_has_a_safe_semantic_warning(
    material_service: object,
    pipe_size_service: object,
    engineering_constant_service: object,
) -> None:
    """An empty selected standard is not silently searched in another standard."""
    empty = pipe_size_service.create_standard(
        code="PHASE2B_EMPTY", display_name="Boş Test Standardı"
    )
    service = PipeDesignService(
        material_service, pipe_size_service, engineering_constant_service
    )

    result = service.calculate(
        diameter=PipeDiameterInput(100.0, 2.0), standard_code=empty.code
    )

    assert result.diameter is not None
    assert result.diameter.recommended_dn is None
    assert result.diameter.warnings == ["selected_standard_empty"]


def test_pipe_design_persists_a_standard_code_and_passes_it_to_the_service() -> None:
    """The UI has a visible selector and keeps the stable code in project state."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")

    assert '"pipe_standard_code": self._selected_pipe_standard_code()' in source
    assert 'text=self._translate("field.pipe_standard")' in source
    assert "standard_code=standard_code" in source
    assert "PipeSizeService.DEFAULT_STANDARD_CODE" in source
    assert "field.pipe_standard')} = {self._selected_pipe_standard_name()}" in source


def test_pipe_library_filters_rows_and_creates_with_the_selected_standard() -> None:
    """The dialog never presents or creates cross-standard pipe geometry."""
    source = (ROOT / "ui/dialogs/pipe_size_library_dialog.py").read_text(encoding="utf-8")

    assert "self._pipe_size_service.get_pipe_sizes_for_standard" in source
    assert "standard_id=self._selected_standard_id" in source
    assert "PipeSizeService.DEFAULT_STANDARD_CODE" in source
    assert "Mevcut Kütüphane:" not in source
    assert "LEGACY_" not in source
