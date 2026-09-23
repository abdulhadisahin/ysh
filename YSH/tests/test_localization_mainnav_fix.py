"""Regression contracts for live localized main navigation."""

from __future__ import annotations

from pathlib import Path

from i18n.translator import Translator


ROOT = Path(__file__).resolve().parents[1]


def test_main_navigation_catalogue_has_exact_english_and_turkish_labels() -> None:
    """Top-menu and tab labels follow the approved Phase 1 terminology."""
    english = Translator("en")
    turkish = Translator("tr")
    expected = {
        "page.pipe.tab": ("Pipe Design", "Boru Tasarımı"),
        "page.transfer.tab": ("Fuel Transfer Pump", "Yakıt Transfer Tulumbası"),
        "page.discharge.tab": ("Discharge Head Loss", "Tulumba Basma Yük Kaybı"),
        "page.suction.tab": ("Suction NPSH", "Tulumba Emme Yük Kaybı ve ENPY"),
        "menu.file": ("File", "Dosya"),
        "menu.library": ("Library", "Kütüphane"),
        "menu.project": ("Project", "Proje"),
        "menu.help": ("Help", "Yardım"),
    }
    for key, (english_text, turkish_text) in expected.items():
        assert english.translate(key) == english_text
        assert turkish.translate(key) == turkish_text


def test_file_library_project_and_help_items_have_stable_keys() -> None:
    """Main navigation labels do not depend on their currently displayed text."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    for key in (
        "menu.file.new_project",
        "menu.file.open_project",
        "menu.file.save_project",
        "menu.file.save_project_as",
        "menu.file.close_project",
        "menu.file.delete_project",
        "menu.file.exit",
        "menu.library.materials",
        "menu.library.pipe_sizes",
        "menu.library.engineering_constants",
        "menu.project.refresh",
        "menu.help.about",
    ):
        assert key in source
    assert "FILE_MENU_INDEX" in source
    assert 'entryconfigure("Save Project"' not in source
    assert 'entryconfigure("Close Project"' not in source


def test_tab_title_refresh_uses_stable_page_keys_without_page_recreation() -> None:
    """The notebook maps stable calculation IDs to its existing page hosts."""
    source = (ROOT / "ui/widgets/scrollable_page_host.py").read_text(encoding="utf-8")
    main = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "self._page_keys" in source
    assert "page_key: str" in source
    assert "def set_page_title(self, page_key: str, title: str)" in source
    for key in ("pipe_design", "transfer_pump", "discharge_head_loss", "suction_npsh"):
        assert key in main
    assert "set_page_title(page_name" in main
    assert "selected_tab = self._page_host.select()" in main
    assert "self._page_host.select(selected_tab)" in main


def test_menu_cascades_use_stable_indexes_and_are_explicitly_refreshed() -> None:
    """Cascade labels refresh independently of page or header widget failures."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "MENU_CASCADE_INDEX" in source
    for key in ("file", "library", "project", "help"):
        assert f'MENU_CASCADE_INDEX["{key}"]' in source
    assert "self._root.configure(menu=self._menu_bar)" in source


def test_file_menu_translation_preserves_approved_actions() -> None:
    """Runtime switching changes labels only, retaining the existing commands."""
    english = Translator("en")
    turkish = Translator("tr")
    assert english.translate("menu.file.new_project") == "New Project..."
    assert turkish.translate("menu.file.new_project") == "Yeni Proje..."
    assert english.translate("menu.file.exit") == "Exit"
    assert turkish.translate("menu.file.exit") == "Çıkış"
