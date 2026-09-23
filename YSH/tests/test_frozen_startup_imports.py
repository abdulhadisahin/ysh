"""Import-order contracts required by the packaged YSH entry point."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_spec_collects_tcl_runtime_directories_for_the_hook() -> None:
    """The frozen Tcl runtime hook receives its required onedir data directories."""
    source = (ROOT.parent / "build" / "ysh.spec").read_text(encoding="utf-8")

    assert '(str(tcl_root / "tcl8.6"), "_tcl_data")' in source
    assert '(str(tcl_root / "tk8.6"), "_tk_data")' in source
    assert 'hookspath=[str(repository_root / "build" / "hooks")]' in source


def test_release_spec_collects_legacy_package_import_names() -> None:
    """Frozen startup supports established package-local import names."""
    source = (ROOT.parent / "build" / "ysh.spec").read_text(encoding="utf-8")

    assert "legacy_module_imports" in source
    assert 'str(application_root)' in source


def test_release_runtime_hook_preserves_legacy_package_roots() -> None:
    """The frozen bridge cannot replace collected legacy package roots."""
    hook = (
        ROOT.parent / "build" / "hooks" / "rthooks" / "pyi_rth_ysh_legacy_packages.py"
    ).read_text(encoding="utf-8")

    assert 'importlib.import_module(package_name)' in hook
    assert '"core"' in hook
