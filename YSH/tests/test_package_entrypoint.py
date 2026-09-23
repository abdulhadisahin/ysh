"""Regression contracts for package-based YSH startup."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_package_main_is_an_executable_module_entrypoint() -> None:
    """``python -m YSH.main`` has one explicit application lifecycle entry."""
    source = (ROOT / "YSH/main.py").read_text(encoding="utf-8")
    assert "from YSH.app import YSHApplication" in source
    assert "def main() -> None:" in source
    assert 'if __name__ == "__main__":' in source
    assert "application.run()" in source


def test_package_composition_uses_ysh_qualified_imports() -> None:
    """The startup composition root does not depend on root-script path setup."""
    source = (ROOT / "YSH/app.py").read_text(encoding="utf-8")
    assert "from YSH.database.project_database import ProjectDatabase" in source
    assert "from YSH.ui.main_window import MainWindow" in source
    assert "from database.project_database" not in source
