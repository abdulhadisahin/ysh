"""Regression tests for the single public YSH application entry point."""
from __future__ import annotations
from pathlib import Path

def test_root_main_is_non_empty_and_exposes_main() -> None:
    """The repository-root launcher remains the public executable entry point."""
    root_main = Path(__file__).resolve().parents[2] / "main.py"
    source = root_main.read_text(encoding="utf-8")
    assert source.strip()
    assert "def main() -> None:" in source
    assert "from YSH.app import YSHApplication" in source
    assert 'if __name__ == "__main__":' in source
    assert "main()" in source
