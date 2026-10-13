"""Header-command sizing and distinct library-icon contracts."""

from pathlib import Path

from ui.assets import action_icon_fit_mode, action_icon_path


ROOT = Path(__file__).resolve().parents[1]


def test_library_commands_resolve_to_four_distinct_approved_paths() -> None:
    paths = {
        "library_materials": action_icon_path("library_materials"),
        "library_pipe_sizes": action_icon_path("library_pipe_sizes"),
        "library_engineering_constants": action_icon_path("library_engineering_constants"),
        "library_corrosion_circuits": action_icon_path("library_corrosion_circuits"),
    }
    assert None not in paths.values()
    assert len(set(paths.values())) == 4
    assert all(path.is_file() for path in paths.values() if path is not None)
    assert paths["library_materials"].name == "malzemeler.png"
    assert paths["library_pipe_sizes"].name == "boru_olculeri.png"
    assert paths["library_engineering_constants"].name == "muhendislik_sabitleri.png"
    assert paths["library_corrosion_circuits"].name == "devre_korozyon_artimi.png"
    assert all(action_icon_fit_mode(name) == "full_asset_safe" for name in paths)


def test_header_uses_distinct_library_keys_and_larger_fixed_command_surface() -> None:
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    for name in (
        "library_materials", "library_pipe_sizes",
        "library_engineering_constants", "library_corrosion_circuits",
    ):
        assert f'icon_name="{name}"' in source
    factory = source.split("def _create_header_button", 1)[1].split("def _add_header_logo", 1)[0]
    assert "icon_size=72" in factory
    assert "square_size=86" in factory


def test_loader_cache_identity_keeps_path_and_fit_mode_separate() -> None:
    source = (ROOT / "ui/widgets/asset_loader.py").read_text(encoding="utf-8")
    assert "str(path.resolve())" in source
    assert "fit_mode, alpha_threshold, padding_percent" in source
