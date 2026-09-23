"""Static contracts for the offline YSH Inno Setup installer."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_inno_setup_script_preserves_user_data_and_payload() -> None:
    """The installer must be per-user, offline, and preserve mutable data."""
    source = (
        REPOSITORY_ROOT / "build" / "installer" / "ysh.iss"
    ).read_text(encoding="utf-8")

    assert 'DefaultDirName={localappdata}\\Programs\\YSH' in source
    assert "PrivilegesRequired=lowest" in source
    assert 'Source: "{#SourceRoot}\\*"' in source
    assert "recursesubdirs createallsubdirs" in source
    assert "[UninstallDelete]" not in source
    assert "%LOCALAPPDATA%\\YSH" not in source
    assert "SetupIconFile=..\\..\\YSH\\resources\\ysh.ico" in source


def test_installer_version_matches_the_project_manifest() -> None:
    """Installer and project manifests use the same authoritative version."""
    installer = (
        REPOSITORY_ROOT / "build" / "installer" / "ysh.iss"
    ).read_text(encoding="utf-8")
    manifest = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in manifest
    assert '#define MyAppVersion "0.1.0"' in installer
