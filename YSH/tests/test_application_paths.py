"""Tests for packaged-runtime resource and user-data path separation."""

from __future__ import annotations

import sys
from pathlib import Path

from YSH import app
from YSH.ui.assets import (
    d243_icon_path,
    d243_main_logo_path,
    d243_logo_path,
    d243_ui_logo_path,
    d243_watermark_logo_path,
    ysh_icon_path,
    ysh_logo_path,
    ysh_ship_bottom_left_path,
    ysh_ship_top_right_path,
)
from database.project_database import ProjectDatabase
from paths import ApplicationPaths


def test_user_data_paths_are_under_local_app_data(tmp_path: Path) -> None:
    """Keep writable application data outside the bundle and repository."""
    paths = ApplicationPaths(local_app_data=tmp_path / "Üser")

    assert paths.projects_database_path == tmp_path / "Üser" / "YSH" / "data" / "projects.db"
    assert paths.libraries_database_path == tmp_path / "Üser" / "YSH" / "data" / "libraries.db"
    assert paths.log_file_path == tmp_path / "Üser" / "YSH" / "logs" / "ysh.log"


def test_directories_are_created_for_unicode_user_path(tmp_path: Path) -> None:
    """Create all writable directories on Unicode-compatible paths."""
    paths = ApplicationPaths(local_app_data=tmp_path / "Çağrı")
    paths.ensure_directories()

    assert paths.data_directory.is_dir()
    assert paths.logs_directory.is_dir()
    assert paths.backups_directory.is_dir()


def test_existing_user_database_is_not_overwritten(tmp_path: Path) -> None:
    """Schema initialization preserves an existing user SQLite file."""
    database_path = ApplicationPaths(local_app_data=tmp_path).projects_database_path
    database = ProjectDatabase(database_path)
    database.initialize()
    with database.connection() as connection:
        connection.execute(
            "INSERT INTO projects (id, name, description, notes, created_at, modified_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("existing", "Existing", "", "", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
    database.initialize()
    with database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1


def test_resource_root_uses_meipass_only_when_frozen(monkeypatch: object, tmp_path: Path) -> None:
    """Resolve frozen read-only assets separately from writable user data."""
    paths = ApplicationPaths(local_app_data=tmp_path)
    source_root = paths.resource_root
    monkeypatch.setattr(sys, "frozen", True, raising=False)  # type: ignore[attr-defined]
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)  # type: ignore[attr-defined]
    try:
        assert paths.resource_root == tmp_path / "bundle"
        assert paths.projects_database_path != paths.resource_root / "projects.db"
    finally:
        monkeypatch.delattr(sys, "frozen", raising=False)  # type: ignore[attr-defined]
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)  # type: ignore[attr-defined]
    assert source_root.name == "YSH"


def test_application_initialization_does_not_create_bundle_directories() -> None:
    """Keep bundle-root paths read-only in both source and frozen execution."""
    source = Path(app.__file__).read_text(encoding="utf-8")

    assert "self._application_root" not in source
    assert "self._paths.ensure_directories()" in source


def test_approved_brand_assets_resolve_from_source_resources() -> None:
    """Resolve supplied branding only from the package-relative resource root."""
    paths = ApplicationPaths()

    assert ysh_logo_path(paths.resource_root) is None
    assert ysh_icon_path(paths.resource_root) is None
    assert d243_logo_path(paths.resource_root) == paths.resource_root / "resources" / "d243_logo.png"
    assert d243_ui_logo_path(paths.resource_root) == paths.resource_root / "resources" / "d243_logo_ui.png"
    assert d243_main_logo_path(paths.resource_root) == (
        paths.resource_root / "resources" / "branding" / "d243_logo_main.png"
    )
    assert d243_watermark_logo_path(paths.resource_root) == (
        paths.resource_root / "resources" / "branding" / "d243_logo_watermark.png"
    )
    assert d243_icon_path(paths.resource_root) == paths.resource_root / "resources" / "branding" / "d243_logo.ico"
    assert ysh_ship_top_right_path(paths.resource_root) == (
        paths.resource_root / "resources" / "ysh_ship_top_right.png"
    )
    assert ysh_ship_bottom_left_path(paths.resource_root) == (
        paths.resource_root / "resources" / "ysh_ship_bottom_left.png"
    )


def test_missing_brand_assets_remain_optional_in_frozen_resources(tmp_path: Path) -> None:
    """A missing optional visual asset never resolves to a developer path."""
    frozen_root = tmp_path / "bundle"

    assert ysh_logo_path(frozen_root) is None
    assert ysh_icon_path(frozen_root) is None
    assert d243_logo_path(frozen_root) is None
    assert d243_ui_logo_path(frozen_root) is None
    assert d243_main_logo_path(frozen_root) is None
    assert d243_watermark_logo_path(frozen_root) is None
    assert d243_icon_path(frozen_root) is None
    assert ysh_ship_top_right_path(frozen_root) is None
    assert ysh_ship_bottom_left_path(frozen_root) is None
