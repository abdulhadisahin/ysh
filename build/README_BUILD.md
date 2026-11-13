# D243 V2 Windows onedir release

## V2 Final accepted package

Current release: **D243-V2-FINAL** at
`c9c8dfe8096a128302867d2ece630d9ebb3b5dd7`; **2080 passed, 0 failed**;
Windows smoke **RELEASE_READY**, one normal packaged launch **5.76 s**.
See [V2 Final release evidence](../docs/V2_FINAL_RELEASE.md) for exact sizes,
ZIP hash, build command and the user-assisted smoke scope.

The final acceptance used the existing spec directly, without rerunning the
wrapper's full pytest step. Matching standalone Tcl/Tk 9.0.4 scripts were supplied
as build-process environment variables. No packaging script or production code
was changed. The optional legacy package probe was not run for this acceptance;
its presence is not evidence for a new smoke run. The trusted regression and
manual packaged-app checks are recorded separately.

The following wrapper recipe still runs full pytest and its build-only probe;
do not invoke it for a documentation-only task or an instruction forbidding a
new full regression. Historical Phase 17 manual-acceptance wording below does
not supersede the scoped V2 Final Windows decision. Clean-machine/no-Python and
all-DPI checks are not newly claimed.

Product: D243 Boru ve Tulumba Boyutlandırma Programı.
The existing manifest version remains 0.1.0. The Python package and writable
runtime directory retain the internal YSH name. This workflow builds the
onedir application; the older Inno Setup files are not the Phase 17 artifact.

Use Python 3.14 x64 and PyInstaller 6.22.3 (hooks-contrib 2026.8). For this
checkout, use only `.venv314/Scripts/python.exe`.

```powershell
.\build\build_exe.ps1 -PythonPath .\.venv314\Scripts\python.exe
```

If the interpreter's Tcl/Tk scripts are unavailable, supply matching standalone
script directories without changing the Python installation:

```powershell
.\build\build_exe.ps1 -PythonPath .\.venv314\Scripts\python.exe `
  -TclLibrary C:\BuildResources\tcl9.0 -TkLibrary C:\BuildResources\tk9.0
```

The directories must match the interpreter's linked Tcl/Tk DLL patch versions.
The Phase 17 build used Tcl/Tk 9.0.4, including upstream license files. Sources,
archive hashes, actual build command and validation evidence are recorded in
[YSH/docs/V2_RELEASE_PHASE17.md](../YSH/docs/V2_RELEASE_PHASE17.md).
No build-time download is performed by the spec or build script.

The wrapper runs the full pytest suite, builds `dist/D243/D243.exe`, copies the
payload into a disposable validation directory, runs a build-only frozen probe,
and creates `dist/D243_V2_Windows_x64.zip` only if the probe succeeds. It prints
the ZIP SHA-256. `run_build_via_python.py` forwards its current interpreter and
arguments to this wrapper. Prior validation directories are retained.

The optional probe is generated under `build/pyinstaller/ysh/` and is absent
from the release directory and ZIP. It shares the release PYZ/runtime hooks and
checks real Tk widgets, bundled paths, PNG/MathText/TkAgg, project persistence,
SQLite integrity/foreign keys, calculations, Library and History. Its profile
is disposable; it never uses the normal user data directory.

The final release contains no runtime/user database, source tree, tests, venv,
logs, build outputs, or profiling data. All production resource maps remain
available. Official Matplotlib hooks collect data/fonts and only the TkAgg
backend. Standard Tcl/Tk hooks discover version-appropriate DLLs, and redirect
TCL_LIBRARY/TK_LIBRARY to `_internal/_tcl_data` and `_internal/_tk_data` at runtime.
Missing script resources abort the build instead of silently producing an
incomplete runtime.

Runtime data remains `%LOCALAPPDATA%\YSH\data` (`libraries.db` v5 and
`projects.db` v1). No schema or path change is made. Copy/extract the complete
D243 folder, then launch **D243.exe** directly. Python, pip, Git and internet
are not required on the target machine. Do not copy only the EXE.

The application is unsigned. Final manual Windows acceptance, including the
clean-machine/no-Python check, remains required; see the 20-item checklist in
the Phase 17 release report. Do not claim acceptance from build success alone.
