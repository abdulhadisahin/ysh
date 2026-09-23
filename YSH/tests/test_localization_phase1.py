"""No-display contracts for the Phase 1 English/Turkish localization system."""

from __future__ import annotations

from pathlib import Path

from i18n.manager import LocalizationManager
from i18n.messages_en import MESSAGES as ENGLISH_MESSAGES
from i18n.messages_tr import MESSAGES as TURKISH_MESSAGES
from i18n.translator import Translator


ROOT = Path(__file__).resolve().parents[1]


def test_english_is_the_default_language_and_resolves_approved_text() -> None:
    """A new translator defaults to the approved English interface."""
    translator = Translator()
    assert translator.language == "en"
    assert translator.translate("page.pipe.tab") == "Pipe Design"
    assert translator.translate("result.available_npsh") == "Available NPSH"


def test_turkish_lookup_preserves_symbols_and_approved_enpy_policy() -> None:
    """Turkish terms use UTF-8 text while engineering symbols stay unchanged."""
    translator = Translator("tr")
    assert translator.translate("page.suction.tab") == "Tulumba Emme Yük Kaybı ve ENPY"
    assert translator.translate("field.yield_strength") == "Akma Dayanımı Rp0,2"
    assert translator.translate("result.available_npsh") == "Mevcut ENPY"
    assert translator.translate("field.flow_rate") == "Debi"


def test_missing_turkish_translation_falls_back_to_english() -> None:
    """Partial Turkish catalogues never expose a raw key when English exists."""
    translator = Translator("tr")
    assert translator.translate("app.title") == "YSH"
    assert translator.translate("validation.required", field_name="Debi") == "Debi gereklidir."


def test_language_preference_persists_outside_project_state(tmp_path: Path) -> None:
    """Language lives in a local settings file, not a project database contract."""
    settings_path = tmp_path / "YSH" / "data" / "settings.json"
    manager = LocalizationManager(settings_path)
    manager.set_language("tr")
    restored = LocalizationManager(settings_path)
    assert restored.language == "tr"
    assert restored.translate("page.transfer.tab") == "Yakıt Transfer Tulumbası"
    assert settings_path.read_text(encoding="utf-8") == '{"language": "tr"}'


def test_runtime_switch_notifies_ui_only_listener_without_project_dirty_callback(
    tmp_path: Path,
) -> None:
    """Language changes refresh live surfaces without invoking project state work."""
    manager = LocalizationManager(tmp_path / "settings.json")
    refreshes: list[str] = []
    dirty_calls: list[bool] = []
    manager.register(lambda: refreshes.append(manager.language))
    manager.set_language("tr")
    manager.set_language("en")
    assert refreshes == ["tr", "en"]
    assert dirty_calls == []


def test_listener_failure_does_not_block_later_live_page_refreshes(tmp_path: Path) -> None:
    """One broken surface cannot prevent other live pages from refreshing."""
    manager = LocalizationManager(tmp_path / "settings.json")
    refreshed: list[str] = []

    def broken_listener() -> None:
        raise RuntimeError("intentional listener failure")

    manager.register(broken_listener)
    manager.register(lambda: refreshed.append(manager.language))
    manager.set_language("tr")

    assert refreshed == ["tr"]


def test_main_and_calculation_sources_register_runtime_refresh_paths() -> None:
    """The translated shell and four pages refresh labels without recreation."""
    main = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    chart = (ROOT / "ui/widgets/transfer_pump_chart.py").read_text(encoding="utf-8")
    assert "def refresh_texts" in main
    assert "set_page_title" in main
    assert "set_translate" in chart
    for name in (
        "pipe_design_page.py",
        "transfer_pump_page.py",
        "discharge_head_loss_page.py",
        "suction_npsh_page.py",
    ):
        source = (ROOT / "ui/pages" / name).read_text(encoding="utf-8")
        assert "def refresh_texts" in source
        assert "FormulaReferencePanel" in source
        assert "self._translate" in source


def test_formula_headings_are_translated_without_altering_equations() -> None:
    """Formula semantic headings switch through keys while equation text remains native."""
    source = (ROOT / "ui/widgets/formula_view.py").read_text(encoding="utf-8")
    for key in (
        "formula.formula",
        "formula.variables",
        "formula.current_substitution",
        "formula.result",
    ):
        assert key in source
    pipe = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert "s0 = (da × pc) / ((20 × σallow × w) + pc)" in pipe


def test_language_infrastructure_does_not_depend_on_engineering_modules() -> None:
    """Localization remains a presentation service with no calculation imports."""
    source = (ROOT / "i18n/manager.py").read_text(encoding="utf-8")
    assert "engineering." not in source
    assert "project_state" not in source


def test_runtime_page_refresh_contract_covers_dynamic_tables_and_results() -> None:
    """Every primary page refreshes existing dynamic presentation in place."""
    expected = {
        "pipe_design_page.py": ("_update_diameter_summary", "pipe.warning.no_suitable_dn"),
        "transfer_pump_page.py": ("_render_estimate", "field.ship_name"),
        "discharge_head_loss_page.py": ("_render_result", "table.quantity_times_k"),
        "suction_npsh_page.py": ("_render_current_results", "action.calculate_enpy"),
    }
    for name, required in expected.items():
        source = (ROOT / "ui/pages" / name).read_text(encoding="utf-8")
        for value in required:
            assert value in source


def test_main_window_owns_one_deterministic_full_refresh_transaction() -> None:
    """The shell refreshes registered live surfaces in a failure-isolated order."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "def register_localizable" in source
    assert "def unregister_localizable" in source
    assert "def _refresh_all_localized_ui" in source
    assert "self._localization.register(self._refresh_all_localized_ui)" in source
    assert "LOCALIZATION component refresh failed" in source


def test_runtime_validation_and_delete_catalogue_is_complete_in_turkish() -> None:
    """User-facing validation and delete semantics never require English fallback."""
    keys = (
        "validation.required",
        "validation.valid_number",
        "validation.greater_than_zero",
        "validation.suction_loss_required",
        "dialog.delete_project",
        "dialog.delete_local_loss",
        "confirm.delete_project",
        "confirm.delete_local_loss",
        "message.no_suitable_dn",
        "pipe.warning.no_suitable_dn",
    )
    for key in keys:
        assert key in ENGLISH_MESSAGES
        assert key in TURKISH_MESSAGES

    translator = Translator("tr")
    assert translator.translate("validation.required", field_name=translator.translate("field.flow_rate")) == "Debi gereklidir."
    assert translator.translate("validation.valid_number", field_name=translator.translate("field.kinematic_viscosity")) == "Kinematik Viskozite geçerli bir sayı olmalıdır."
    assert translator.translate("validation.greater_than_zero", field_name=translator.translate("field.fuel_capacity")) == "Yakıt Kapasitesi sıfırdan büyük olmalıdır."
    assert translator.translate("validation.suction_loss_required") == "ENPY hesabından önce Emme Hattı Yük Kaybını hesaplayın."
