# Changelog

## Epic 7 - Pipe Diameter and Wall Thickness

- Added approved pipe diameter, DN recommendation, and wall thickness formulas.
- Added a service-backed Pipe Diameter and Wall Thickness workspace page.

## Epic 6 - Material and Engineering Data Library

- Added local versioned SQLite storage for materials, pipe sizes, and editable
  engineering constants.
- Added validated domain models, repositories, service layers, initial
  material/constant seed data, and Library menu dialogs.
- Added isolated automated tests for the new engineering data library.

## Epic 5 - Engineering Core Foundation

- Added explicit Version 1 unit conversions using SI internal units.
- Added reusable engineering validation and six-decimal display precision tools.
- Added reusable engineering result and traceability-message structures.
- Added deterministic engineering-core pytest coverage.

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

## Epic 11 - First Windows Test EXE Packaging

- Added central per-user runtime paths for SQLite databases, logs, and backups.
- Added local startup-error logging and packaged-resource path resolution.
- Added reproducible PyInstaller onedir specification and build documentation.

## Epic 12 - Input and Usability Improvements

- Added central point/comma engineering-number parsing for all numeric UI inputs.
- Split Pipe Design into independent diameter and wall-thickness calculation actions.
- Added an offline translation registry with English messages and Turkish registration support.

## Epic 12 Final Completion

- Split suction-line loss from ENPY evaluation without changing engineering formulas.
- Added scoped, non-global mouse-wheel ownership for pages and editable Treeviews.

## Epic 3 - Project Management and Test Foundation

- Added complete ProjectService CRUD and validation workflows.
- Added duplicate project-name prevention with case-insensitive matching.
- Connected New Project creation from the File menu through SQLite persistence.
- Updated the active-project title and status message after project creation.
- Added isolated pytest coverage for project models, repositories, and services.
- Added the test command: `py -3.14 -m pytest` (requires pytest in the active
  Python 3.14 environment).
