"""Application entry point for YSH."""

from __future__ import annotations

from app import YSHApplication


def main() -> None:
    """Initialize and run the YSH desktop application."""
    application = YSHApplication()
    application.run()


if __name__ == "__main__":
    main()
