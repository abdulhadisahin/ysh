# Changelog

## Epic 4 - GUI Foundation and Open Project Workflow

- Added reusable ttk status-bar and project-summary widgets.
- Added the service-backed Open Project dialog with keyboard navigation.
- Added active-project opening and closing workflows in the main window.
- Added display-independent tests for opening, ordering, empty lists, and
  closing active projects.

## Python 3.14 Migration

- Set Python 3.14 as the official YSH runtime.
- Removed Python 3.12 as a supported project target.
- Updated the test command to `py -3.14 -m pytest`.

## Epic 3 - Project Management and Test Foundation

- Added complete ProjectService CRUD and validation workflows.
- Added duplicate project-name prevention with case-insensitive matching.
- Connected New Project creation from the File menu through SQLite persistence.
- Updated the active-project title and status message after project creation.
- Added isolated pytest coverage for project models, repositories, and services.
- Added the test command: `py -3.14 -m pytest` (requires pytest in the active
  Python 3.14 environment).
