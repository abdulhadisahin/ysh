"""
YSH - Engineering Calculation System

Application entry point.
"""

from app import YSHApplication


def main() -> None:
    """Application entry point."""

    application = YSHApplication()
    application.run()


if __name__ == "__main__":
    main()