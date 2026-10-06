"""Contracts for visible, localized ribbon button labels."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ribbon_buttons_receive_translated_text_when_created() -> None:
    """Ribbon commands have visible labels before any language refresh occurs."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

    expected_text_keys = (
        "text=self._translate(\"action.new\")",
        "text=self._translate(\"action.open\")",
        "text=self._translate(\"action.save\")",
        "text=self._translate(\"action.save_as\")",
        "text=self._translate(\"menu.library.materials\")",
        "text=self._translate(\"menu.library.pipe_sizes\")",
        "text=self._translate(\"menu.library.engineering_constants\")",
        "text=self._translate(\"menu.help.about\")",
    )

    for text_key in expected_text_keys:
        assert text_key in source


def test_ribbon_button_text_is_independent_of_icon_configuration() -> None:
    """The ribbon does not rely on an image or compound setting for its text."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    ribbon_section = source[source.index("self._ribbon_project"):source.index("self._ribbon_help")]

    assert "image=" not in ribbon_section
    assert "compound=" not in ribbon_section


def test_ribbon_callbacks_and_live_text_refresh_are_preserved() -> None:
    """Presentation changes retain the existing callbacks and EN/TR refresh path."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

    for callback in (
        "command=self._open_new_project",
        "command=self._open_project",
        "command=self._save_project",
        "command=self._save_project_as",
        "command=self._open_material_library",
        "command=self._open_pipe_size_library",
        "command=self._open_constants_library",
    ):
        assert callback in source

    assert "self._toolbar_new.configure(text=self._translate(\"action.new\"))" in source
    assert (
        "self._toolbar_constants.configure(text=self._translate(\"menu.library.engineering_constants\"))"
        in source
    )
    assert "command=self._show_about" in source
    assert "self._toolbar_about.configure(text=self._translate(\"menu.help.about\"))" in source


def test_ribbon_language_selector_is_not_created_for_turkish_only_ui() -> None:
    """The D243 shell has no visible runtime language selector."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "self._ribbon_language = ttk.Combobox" not in source
