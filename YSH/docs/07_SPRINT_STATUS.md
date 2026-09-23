# Sprint Status

## Epic 7 - Pipe Diameter and Wall Thickness

Implemented Version 1 pipe diameter, editable-library DN recommendation, and
minimum wall thickness calculation. Manual and library material workflows are
supported without persisting overrides.

## Epic 6 - Material and Engineering Data Library

Completed: local, editable material, pipe-size, and engineering-constant
libraries are available through the Library menu. `libraries.db` has a
versioned schema and is created automatically. Materials and constants are
seeded only into empty tables; pipe sizes remain empty until verified values
are entered. The automated test command is:

```powershell
"C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest .\YSH\tests -v --basetemp .\work\pytest-epic6 -p no:cacheprovider
```

Latest test result: 96 passed, 0 failed.

## Completed Epic 5 - Engineering Core Foundation

The reusable engineering unit conversion, validation, precision, and result
infrastructure is complete.

## Files Modified

- `database/project_database.py`
- `repositories/project_repository.py`
- `services/project_service.py`
- `ui/dialogs/__init__.py`
- `ui/dialogs/new_project_dialog.py`
- `ui/dialogs/open_project_dialog.py`
- `ui/widgets/__init__.py`
- `ui/widgets/status_bar.py`
- `ui/widgets/project_summary.py`
- `ui/main_window.py`
- `engineering/__init__.py`
- `engineering/exceptions.py`
- `engineering/units.py`
- `engineering/validation.py`
- `engineering/precision.py`
- `engineering/result.py`
- `tests/conftest.py`
- `tests/test_project_model.py`
- `tests/test_project_repository.py`
- `tests/test_project_service.py`
- `tests/test_main_window.py`
- `tests/test_engineering_units.py`
- `tests/test_engineering_validation.py`
- `tests/test_engineering_precision.py`
- `tests/test_engineering_result.py`
- `pyproject.toml`

## Automated Test Command

```powershell
py -3.14 -m pytest
```

## Latest Test Result

71 tests passed, 0 tests failed using Python 3.14.6 and pytest 9.1.1.

## Runtime Standard

Python 3.14 is the official YSH runtime. Python 3.12 is no longer a supported
project target.

## Engineering Core Standards

- Supported internal units: m, Pa, m³/s, m²/s, and kg/m³.
- Calculations retain full precision; only display/reporting values are rounded.
- User-facing numerical values use six decimal places by default.

## Next Planned Feature

First engineering calculation module.

## Epic 11 - First Windows Test EXE Packaging

- Added PyInstaller onedir build configuration and PowerShell build/clean scripts.
- Added `%LOCALAPPDATA%\YSH\data` database paths and `%LOCALAPPDATA%\YSH\logs\ysh.log`.
- Added source/frozen resource-path separation and path regression tests.
- Diagnostic build command: `powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1`.
- Latest pre-build test result: 116 passed, 0 failed.
- Build execution is pending a PyInstaller-capable Windows environment; this
  environment blocks access to PyPI and has no installed PyInstaller package.

## Epic 12 - Input and Usability Improvements

- Engineering numeric inputs accept decimal points or commas, including scientific notation.
- Mixed decimal/thousands-style separators are rejected; database values remain numeric.
- Pipe diameter and wall thickness calculations now run as independent operations.
- Added offline translation-key infrastructure; Turkish translation is planned for a later sprint.
- Latest test result: 134 passed, 0 failed.

## Epic 12 Final Completion

- Suction-line hydraulic loss and ENPY are independent page actions.
- Hydraulic changes invalidate both stages; pressure/NPSH changes preserve suction loss.
- Mouse wheel is scoped: page controls route to their page and Treeviews consume table scrolling.
- No Spinbox, Scale, Slider, or Listbox widgets currently exist in YSH.
- Latest test result: 139 passed, 0 failed.
