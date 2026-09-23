"""Canonical package entry point for the YSH desktop application."""

from __future__ import annotations

from YSH.app import YSHApplication


def main() -> None:
    """Create and run the YSH application from package execution."""
    application = YSHApplication()
    application.run()


if __name__ == "__main__":
    main()
