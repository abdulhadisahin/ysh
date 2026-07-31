"""Compatibility launcher that delegates to the repository-root entry point."""

from __future__ import annotations

from pathlib import Path
from runpy import run_path


def main() -> None:
    """Run the primary repository-root YSH entry point."""
    repository_entry_point = Path(__file__).resolve().parents[1] / "main.py"
    run_path(str(repository_entry_point), run_name="__main__")


if __name__ == "__main__":
    main()
