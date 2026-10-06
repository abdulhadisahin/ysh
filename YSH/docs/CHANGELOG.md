# Changelog

## D243 V2 — Phase 8A

- Added an immutable, source-backed engineering-warning rule architecture with
  ERROR, ENGINEERING_WARNING, and CRITICAL_WARNING taxonomy.
- Added MAN / Everllence recommended velocity ranges and the ANSI/HI NPSH
  comparison rule as domain definitions only; no warning UI is included.

## D243 V2 — Phase 7

- Added direct `Hacim [m³]` and `Kütle [ton]` new-ship input modes to Transfer
  Pump. Ton input uses the fixed D243 V2 basis `0.83 t/m³` and preserves full
  precision before entering the existing regression path.
- Added the separate reference output `Q12 = V / 12`; it does not replace the
  regression prediction or existing emptying-time calculation.

## D243 V2 — Phase 6

- Added persisted D243 bend-radius modes (`1.5D`, `2D`, `3D`, `5D`, `10D`, and
  Manual) with a default of `3D`.
- Automatic modes now derive `R = multiplier × da`; Manual keeps a user-entered
  positive radius. The established bend-allowance formula is unchanged.
- Added Formula View audit context and an explicit D243-only convention note;
  no Türk Loydu 3D requirement is claimed.

## D243 V2 - Phase 5 Safety Factor B

- Safety factor `B` visibly defaults to 1,80 and remains manually authoritative.
- Added an informational Türk Loydu Bölüm 8, Tablo 8.9 reference dialog and
  formula note; no automatic B/material/pipe-class selection was introduced.

## D243 V2 - Phase 4 Weld Factor v

- Weld factor `v` defaults to 1,00, remains manually editable, and the entered
  value remains authoritative in the existing wall-thickness calculation.
- Added an informational Türk Loydu note to Formula View. No pipe-type logic,
  lookup table, or automatic update based on pipe standard or circuit exists.

## D243 V2 - Phase 3 Circuit Corrosion-Allowance Defaults

- Added the editable `Devre / Korozyon Artımı Kütüphanesi` with D243 product
  defaults: Yakıt Devresi 1,00 mm, Deniz Suyu Devresi 3,00 mm, and Kazan Blöf
  Devresi 1,50 mm.
- Pipe Design now persists a circuit selection, displays default and used `c`
  separately, and keeps manual `c` overrides local to the calculation.
- These are editable D243 defaults, not claims of mandatory external-standard
  requirements. The visual redesign remains deferred.

## D243 V2 - Phase 2B Visible Pipe Standard Selection

- Added a Turkish `Boru Standardı` selector to Pipe Design and to the Pipe Size
  Library dialog, both populated from active standard entities.
- Pipe recommendations now query only the explicitly selected standard; the
  selected standard is shown with the recommendation and is saved in project
  page state. Legacy V1 state with no standard still defaults to EN 10220.
- Pipe-library rows are filtered by the selected standard and new geometry is
  explicitly attached to that standard. ISO 1127 production geometry remains
  intentionally absent.

## D243 V2 - Phase 2A Standard-Based Pipe Library Architecture

- Added standard-owned pipe-library schema version 3 with `pipe_standards` and
  standard-scoped pipe geometry natural keys.
- Migrated legacy free-text EN 10220 rows to the canonical `EN_10220` standard;
  preserved unknown historic labels as explicit legacy metadata instead of
  assigning an unverified standard.
- Kept EN 10220 as the invisible compatibility default for the existing Pipe
  Design workflow. No ISO 1127 production data or standard-selector UI was
  added; both are deferred to Phase 2B.

## D243 V2 - Phase 1 Product Foundation

- Introduced D243 visible product identity without renaming the YSH package.
- Fixed the visible interface to Turkish and removed the language selector.
- Added centralized two-decimal, Turkish-comma display formatting while
  preserving internal calculation and database precision.

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
## D243 V2 — Phase 8B

- Added stable fluid and line-role context for the enabled engineering warning
  rules, with persisted Pipe, Discharge, and Suction selections.
- Added reusable result-preserving presentation for source-backed engineering
  and critical warnings, including simultaneous suction velocity and ENPY/NPSH
  findings.
- Kept formulas, database schema, material-specific rules, and Transfer Pump
  warning behavior unchanged.
