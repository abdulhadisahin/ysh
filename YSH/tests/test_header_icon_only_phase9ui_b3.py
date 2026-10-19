"""Presentation contracts for the Phase 9UI-B3 compact command correction."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_rounded_button_supports_icon_only_native_commands_and_tooltips() -> None:
    button = _source("ui/widgets/rounded_button.py")
    tooltip = _source("ui/widgets/tooltip.py")

    assert "icon_only: bool = False" in button
    assert "tooltip_text: str | None = None" in button
    assert "self._icon_only" in button
    assert "self._tooltip = Tooltip" in button
    assert "return (self._square_size, self._square_size)" in button
    assert 'widget.bind("<Enter>", self._schedule, add="+")' in tooltip
    assert 'widget.bind("<Leave>", self._hide, add="+")' in tooltip


def test_header_reflows_commands_to_the_right_and_keeps_group_titles() -> None:
    shell = _source("ui/main_window.py")

    assert 'toolbar.grid(row=0, column=1, sticky="e")' in shell
    assert "header.columnconfigure(1, weight=1)" in shell
    assert "icon_only=True" in shell
    assert "tooltip_text=text" in shell
    assert "icon_size=79" in shell
    assert "square_size=86" in shell
    assert 'self._create_ribbon_group(toolbar, "ribbon.project")' in shell
    assert 'self._create_ribbon_group(toolbar, "ribbon.data_library")' in shell
    assert 'self._create_ribbon_group(toolbar, "ribbon.help")' in shell


def test_sidebar_restores_native_text_while_transfer_toolbar_stays_compact() -> None:
    shell = _source("ui/main_window.py")
    transfer = _source("ui/pages/transfer_pump_page.py")

    assert "icon_size=40" in shell
    assert "minimum_height=52" in shell
    assert "icon_only=True" not in shell.split("def _create_sidebar_button", 1)[1].split("def _add_decorative_image", 1)[0]
    for icon_name in ('icon_name="add", icon_only=True', 'icon_name="edit", icon_only=True', 'icon_name="delete", icon_only=True'):
        assert icon_name in transfer
    assert 'icon_name="calculate", icon_size=36' in transfer
    assert 'icon_name="formula", icon_size=36' in transfer
