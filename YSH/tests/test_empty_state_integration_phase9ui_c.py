"""Focused contracts for contextual D243 empty-state presentation."""

from pathlib import Path

from ui.assets import EMPTY_STATE_FILENAMES, empty_state_path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_empty_state_manifest_resolves_every_approved_context() -> None:
    assert {
        "project", "result", "reference", "local_loss", "formula",
        "library", "chart", "workspace",
    } <= set(EMPTY_STATE_FILENAMES)
    for name in ("project", "result", "reference", "formula", "chart", "workspace"):
        assert empty_state_path(name) is not None
    # Do not substitute an unrelated approved image where no semantically
    # correct local-loss or library artwork has been supplied.
    assert empty_state_path("local_loss") is None
    assert empty_state_path("library") is None


def test_shared_empty_state_uses_central_loader_and_native_text() -> None:
    source = _source("ui/widgets/engineering_components.py")
    assert "class EmptyState" in source
    assert "AssetImageLoader.load" in source
    assert "self._title" in source and "self._body" in source


def test_contextual_states_swap_instead_of_overlaying_live_content() -> None:
    transfer = _source("ui/pages/transfer_pump_page.py")
    discharge = _source("ui/pages/discharge_head_loss_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")
    formula = _source("ui/widgets/formula_view.py")
    library = _source("ui/dialogs/library_dialog.py")
    assert "_set_reference_empty_state" in transfer and "_chart_empty_state" in transfer
    assert "_local_loss_empty_state" in discharge
    assert "_local_loss_empty_state" in suction
    assert "Formül referansı henüz hazır değil" in formula
    assert "self._empty_state" in library


def test_sidebar_state_is_contextual_and_keeps_actions_separate() -> None:
    source = _source("ui/main_window.py")
    assert "_project_empty_state" in source
    assert "actions.grid(row=4" in source
    assert "tree_container.grid_remove" in source
