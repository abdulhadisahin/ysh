"""Static regression tests for independently scrollable editable tables."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_scrollable_treeview_links_both_scrollbars() -> None:
    """Require the reusable widget to link both Treeview axes."""
    source = (PROJECT_ROOT / "ui" / "widgets" / "scrollable_treeview.py").read_text(encoding="utf-8")

    assert "yscrollcommand" in source
    assert "xscrollcommand" in source
    assert "orient=\"vertical\"" in source
    assert "orient=\"horizontal\"" in source


def test_primary_editable_tables_use_scrollable_treeview() -> None:
    """Keep local and ship reference tables on the shared implementation."""
    page_paths = (
        "ui/pages/transfer_pump_page.py",
        "ui/pages/discharge_head_loss_page.py",
        "ui/pages/suction_npsh_page.py",
    )

    for relative_path in page_paths:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "ScrollableTreeview" in source or "TechnicalTable" in source
        assert "self._tree_container" in source


def test_transfer_pump_page_initializes_tree_before_refresh() -> None:
    """Require the page to create the Treeview before calling refresh()."""
    source = (PROJECT_ROOT / "ui" / "pages" / "transfer_pump_page.py").read_text(encoding="utf-8")

    assert "def _build" in source
    assert "self._tree = self._tree_container.tree" in source
    assert "self._tree.bind(\"<Double-1>\"" in source


def test_transfer_pump_page_embeds_and_refreshes_the_regression_chart() -> None:
    """The existing page redraws one embedded chart after every relevant change."""
    source = (PROJECT_ROOT / "ui" / "pages" / "transfer_pump_page.py").read_text(encoding="utf-8")

    assert "TransferPumpChart" in source
    assert "TransferPumpChartModel.from_authoritative" in source
    assert "self._refresh_chart(all_records)" in source
    assert "self._refresh_chart()" in source
    assert "_estimate_capacity_m3" in source
