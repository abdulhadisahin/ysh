"""Release packaging contracts for the offline Windows one-folder build."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_spec_bundles_resources_icon_and_matplotlib_tkagg() -> None:
    """The canonical spec packages all local visual and chart runtime assets."""
    source = (REPOSITORY_ROOT / "build" / "ysh.spec").read_text(encoding="utf-8")
    assert '"resources" / "branding" / "d243_logo.ico"' in source

    assert 'main_entry = repository_root / "main.py"' in source
    assert '"resources"' in source
    assert '"d243_logo.ico"' in source
    assert 'collect_all(\n    "matplotlib"' in source
    assert '"matplotlib.backends.backend_tkagg"' in source
    assert '"_tcl_data"' in source
    assert '"_tk_data"' in source
    assert '"_tkinter.pyd"' in source
    assert '"tcl86t.dll"' in source
    assert '"tk86t.dll"' in source
    assert 'hookspath=[str(repository_root / "build" / "hooks")]' in source
    assert "legacy_module_imports" in source
    assert "*legacy_module_imports" in source
    assert "exclude_binaries=True" in source
    excludes = source.split("excludes=", 1)[1].split(")", 1)[0]
    assert '"matplotlib"' not in excludes
    assert '"numpy"' not in excludes


def test_spec_resource_and_icon_paths_are_repository_relative() -> None:
    """Packaging configuration contains no machine-specific filesystem roots."""
    source = (REPOSITORY_ROOT / "build" / "ysh.spec").read_text(encoding="utf-8")

    for asset_name in (
        "d243_logo_main.png",
        "d243_logo_medium.png",
        "d243_logo_small.png",
        "d243_logo_watermark.png",
        "d243_logo.ico",
    ):
        assert (REPOSITORY_ROOT / "YSH" / "resources" / "branding" / asset_name).is_file()
    assert "C:\\Users\\" not in source
    assert "repository_root" in source


def test_build_script_uses_a_portable_python_resolution_strategy() -> None:
    """The reproducible Windows build does not embed a developer interpreter path."""
    source = (REPOSITORY_ROOT / "build" / "build_exe.ps1").read_text(encoding="utf-8")

    assert "Get-Command py.exe" in source
    assert '"-3.14"' in source
    assert "PythonPath" in source
    assert 'Join-Path $repositoryRoot "work\\pytest-release-build"' in source
    assert "C:\\Users\\USER" not in source


def test_custom_tkinter_hook_preserves_module_discovery() -> None:
    """Explicit YSH Tcl/Tk collection must not allow host probing to exclude Tkinter."""
    source = (
        REPOSITORY_ROOT / "build" / "hooks" / "pre_find_module_path" / "hook-tkinter.py"
    ).read_text(encoding="utf-8")

    assert "def pre_find_module_path" in source
    assert "search_dirs" not in source
