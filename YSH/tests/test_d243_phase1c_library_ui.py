"""Turkish-only visible-library UI contracts for D243 Phase 1C."""

from __future__ import annotations

from pathlib import Path

from i18n.translator import Translator


ROOT = Path(__file__).resolve().parents[1]


def test_library_catalogue_renders_representative_visible_text_in_turkish() -> None:
    """Common library labels, actions, empty state, and confirmations are Turkish."""
    translate = Translator("tr").translate

    assert translate("library.materials") == "Malzeme Kütüphanesi"
    assert translate("library.pipe_sizes") == "Boru Ölçüleri Kütüphanesi"
    assert translate("library.constants") == "Mühendislik Sabitleri"
    assert translate("library.no_records") == "Kayıt bulunamadı."
    assert translate("common.add") == "Ekle"
    assert translate("common.edit") == "Düzenle"
    assert translate("common.delete") == "Sil"
    assert translate("common.close") == "Kapat"
    assert translate("dialog.delete_library_record") == "Kütüphane Kaydını Sil"


def test_library_wrappers_have_turkish_fallbacks_and_keep_technical_designations() -> None:
    """Fallback labels do not leak English outside the fully localized shell."""
    material = (ROOT / "ui/dialogs/material_library_dialog.py").read_text(encoding="utf-8")
    pipe_size = (ROOT / "ui/dialogs/pipe_size_library_dialog.py").read_text(encoding="utf-8")
    constants = (ROOT / "ui/dialogs/constants_library_dialog.py").read_text(encoding="utf-8")

    assert '"Malzeme Kütüphanesi"' in material
    assert '"Boru Ölçüleri Kütüphanesi"' in pipe_size
    assert '"Mühendislik Sabitleri"' in constants
    assert '"Dış Çap (mm)"' in pipe_size
    assert '"Akma Dayanımı Rp0,2 (MPa)"' in material
    assert '"DN"' in pipe_size
    assert '"Mühendislik Sabiti"' in constants


def test_library_editor_and_reference_modals_receive_turkish_translation() -> None:
    """Standalone editors and page-owned modals share the active Turkish translator."""
    library = (ROOT / "ui/dialogs/library_dialog.py").read_text(encoding="utf-8")
    transfer = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    suction = (ROOT / "ui/pages/suction_npsh_page.py").read_text(encoding="utf-8")

    assert 'Translator("tr").translate' in library
    assert '"description": "project.description"' in library
    assert '"display_name": "library.engineering_constant"' in library
    assert "PumpReferenceDialog(self, self._service._references, translate=self._translate)" in transfer
    assert "LocalLossItemDialog(self,translate=self._translate)" in discharge
    assert "LocalLossItemDialog(self, translate=self._translate)" in suction
    assert 'Translator("tr").translate' in (ROOT / "ui/dialogs/pump_reference_dialog.py").read_text(encoding="utf-8")
    assert 'Translator("tr").translate' in (ROOT / "ui/dialogs/local_loss_item_dialog.py").read_text(encoding="utf-8")
