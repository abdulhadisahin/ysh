# YSH AI Handover

The active repository contains the application beneath `YSH/`, with domain
models in `YSH/core`, SQLite schema definitions in `YSH/database`, persistence
repositories in `YSH/repositories`, service workflows in `YSH/services`, and
Tkinter ttk UI in `YSH/ui`.

Python 3.14 is the required runtime. Epic 7, Pipe Diameter and Wall Thickness,
is complete. The current test command is:

```powershell
"C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest .\YSH\tests -v --basetemp .\work\pytest-epic6 -p no:cacheprovider
```

Latest passing-test count: 96. The next planned Epic has not been specified.
PDF reporting is outside scope unless explicitly reintroduced. YSH is a
single-user, local, fully offline Windows desktop application; multi-user and
network operation are outside scope.

## Epic 11 Packaging State

YSH runtime data is now stored outside the repository and bundle under
`%LOCALAPPDATA%\YSH`: `data\projects.db`, `data\libraries.db`, `logs\ysh.log`,
and `backups`. The PyInstaller diagnostic onedir configuration is in
`build\ysh.spec`; build it with `build\build_exe.ps1`. The latest pre-build
pytest result is 116 passed. PyInstaller could not be installed in the Codex
environment because PyPI network access is blocked, so no EXE has been built or
visually smoke-tested here.

## Epic 12 Input Policy

Numeric UI fields use `engineering.input_parsing`: `12.5`, `12,5`, and decimal
comma scientific notation are accepted. Thousands separators and mixed `.`/`,`
forms are rejected. Pipe Design operations are independent. The `i18n` package
provides stable English message keys and future Turkish catalogue registration;
the visible application is not yet translated.

Suction NPSH now calculates hydraulic suction loss before optional ENPY. Changing
hydraulic inputs invalidates both results; ENPY-only inputs preserve the prior
suction loss. Wheel behavior is page-scoped for Entry/Combobox and consumed by
Treeviews. No Spinbox or Scale widgets currently exist.
