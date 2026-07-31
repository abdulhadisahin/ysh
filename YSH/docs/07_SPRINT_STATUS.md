# Sprint Status

## Completed Epic 4 - GUI Foundation and Open Project Workflow

The reusable GUI foundation, Open Project workflow, active-project summary,
and close-project state management are complete.

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
- `tests/conftest.py`
- `tests/test_project_model.py`
- `tests/test_project_repository.py`
- `tests/test_project_service.py`
- `tests/test_main_window.py`
- `pyproject.toml`

## Automated Test Command

```powershell
py -3.14 -m pytest
```

## Latest Test Result

0 tests executed: the available Codex Python runtime does not include pytest.
The suite contains 25 isolated tests and is ready to run with
`py -3.14 -m pytest` in a Python 3.14 environment where pytest is installed.

## Runtime Standard

Python 3.14 is the official YSH runtime. Python 3.12 is no longer a supported
project target.

## Next Planned Feature

Save-project workflow with unsaved-change tracking.
