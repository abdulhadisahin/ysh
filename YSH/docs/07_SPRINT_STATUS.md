# Sprint Status

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
