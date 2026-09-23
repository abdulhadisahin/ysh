"""Shared-library presentation contracts for Visual Phase 5G."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_library_dialog_uses_one_modern_engineering_table() -> None:
    """All library windows inherit table styling without changing service ownership."""
    source = (ROOT / "ui" / "dialogs" / "library_dialog.py").read_text(encoding="utf-8")
    assert 'self._tree.configure(style="Library.Treeview")' in source
    assert "self._list_items()" in source
    assert "self._create_item(**values)" in source
    assert "self._update_item(item)" in source


def test_library_dialog_retains_keyboard_validation_and_delete_confirmation() -> None:
    """The shared dialog retains local CRUD, validation, and confirmation paths."""
    source = (ROOT / "ui" / "dialogs" / "library_dialog.py").read_text(encoding="utf-8")
    for event in ('"<Double-1>"', '"<Return>"', '"<Delete>"', '"<Escape>"'):
        assert event in source
    assert "messagebox.askyesno" in source
    assert "parse_engineering_float" in source
