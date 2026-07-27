"""
YSH - Engineering Calculation System

Application constants.
"""

from pathlib import Path

# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------

APPLICATION_NAME = "YSH"
APPLICATION_FULL_NAME = "YSH - Engineering Calculation System"
APPLICATION_VERSION = "1.0.0"

# ----------------------------------------------------------------------
# Window
# ----------------------------------------------------------------------

MAIN_WINDOW_TITLE = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"

MAIN_WINDOW_WIDTH = 1400
MAIN_WINDOW_HEIGHT = 900

MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700

# ----------------------------------------------------------------------
# Directories
# ----------------------------------------------------------------------

ROOT_DIRECTORY = Path.cwd()

DATABASE_DIRECTORY = ROOT_DIRECTORY / "database"
LIBRARY_DIRECTORY = ROOT_DIRECTORY / "libraries"
REPORT_DIRECTORY = ROOT_DIRECTORY / "reports"
EXPORT_DIRECTORY = ROOT_DIRECTORY / "exports"

# ----------------------------------------------------------------------
# Databases
# ----------------------------------------------------------------------

PROJECT_DATABASE = DATABASE_DIRECTORY / "projects.db"
LIBRARY_DATABASE = DATABASE_DIRECTORY / "libraries.db"
SETTINGS_DATABASE = DATABASE_DIRECTORY / "settings.db"

# ----------------------------------------------------------------------
# Default Values
# ----------------------------------------------------------------------

DEFAULT_PROJECT_NAME = "New Project"

# ----------------------------------------------------------------------
# Company
# ----------------------------------------------------------------------

COMPANY_NAME = ""