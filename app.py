"""
YSH - Engineering Calculation System

Application controller.
"""

from core.database_manager import DatabaseManager
from ui.main_window import MainWindow


class YSHApplication:
    """Main application."""

    def __init__(self) -> None:
        self.database_manager = DatabaseManager()

    def initialize(self) -> None:
        """Initialize application resources."""

        self.database_manager.connect()
        self.database_manager.create_tables()

    def shutdown(self) -> None:
        """Release application resources."""

        self.database_manager.disconnect()

    def run(self) -> None:
        """Run the application."""

        self.initialize()

        try:
            window = MainWindow()
            window.run()
        finally:
            self.shutdown()