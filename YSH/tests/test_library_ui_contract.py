"""Display-independent regression checks for the shared library UI contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_common_library_dialog_uses_scrollable_table_search_and_empty_state() -> None:
    """Every shared library editor retains its table/search/status structure."""
    source = (ROOT / "ui/dialogs/library_dialog.py").read_text(encoding="utf-8")
    assert "ScrollableTreeview" in source
    assert '"library.search"' in source
    assert '"library.no_records"' in source


def test_material_ui_uses_rp02_terminology_without_inventing_values() -> None:
    """Material labels explicitly identify Rp0.2 and missing values stay visible."""
    material_source = (ROOT / "ui/dialogs/material_library_dialog.py").read_text(encoding="utf-8")
    dialog_source = (ROOT / "ui/dialogs/library_dialog.py").read_text(encoding="utf-8")
    assert "Akma Dayanımı Rp0,2 (MPa)" in material_source
    assert '"library.not_verified"' in dialog_source


def test_constants_primary_table_hides_internal_key_and_blocks_arbitrary_add_delete() -> None:
    """Engineering constants expose names while retaining their stable internal keys."""
    source = (ROOT / "ui/dialogs/constants_library_dialog.py").read_text(encoding="utf-8")
    assert '("display_name","Mühendislik Sabiti")' in source
    assert "allow_create=False" in source
    assert "allow_delete=False" in source


def test_pump_reference_search_is_service_backed_and_case_insensitive() -> None:
    """Ship-reference filtering does not access SQLite directly from the UI."""
    source = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    assert '"field.search_references"' in source
    assert "record.ship_name.casefold()" in source
    assert "get_all_references()" in source
