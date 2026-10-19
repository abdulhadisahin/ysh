# -*- mode: python ; coding: utf-8 -*-
"""Offline D243 Windows onedir release with validated Tcl/Tk runtime."""

import sys
import os
from pathlib import Path

from PyInstaller.utils.hooks.tcl_tk import tcltk_info


repository_root = Path(SPECPATH).resolve().parent
application_root = repository_root / "YSH"
main_entry = repository_root / "main.py"
# Standard hooks discover the DLLs for this interpreter (including Tcl/Tk 9).
# Build-only TCL_LIBRARY/TK_LIBRARY may point to matching standalone scripts;
# the frozen runtime hook always redirects them to the bundled directories.
if not tcltk_info.available:
    raise SystemExit("Tcl/Tk probe failed: supply matching TCL_LIBRARY and TK_LIBRARY for the build.")
for directory, marker in ((tcltk_info.tcl_data_dir, "init.tcl"),
                          (tcltk_info.tk_data_dir, "tk.tcl")):
    if not directory or not (Path(directory) / marker).is_file():
        raise SystemExit(f"Missing Tcl/Tk script resource: {directory}/{marker}")
tk_runtime_data = [
    (str(tcltk_info.tcl_data_dir), "_tcl_data"),
    (str(tcltk_info.tk_data_dir), "_tk_data"),
]
tk_runtime_binaries = [
    (str(path), ".") for path in (
        tcltk_info.tkinter_extension_file,
        tcltk_info.tcl_shared_library, tcltk_info.tk_shared_library,
    ) if path
]
# Official Matplotlib hooks collect mpl-data/fonts and extension dependencies.
# D243 uses TkAgg and MathText; collecting every backend/submodule is unnecessary.
branding_resources = [(str(application_root / "resources"), "resources")]
legacy_module_imports = [
    ".".join(module_path.relative_to(application_root).with_suffix("").parts)
    for module_path in application_root.rglob("*.py")
    if "tests" not in module_path.parts and module_path.name != "__init__.py"
]

analysis = Analysis(
    [str(main_entry)],
    pathex=[str(repository_root), str(application_root)],
    binaries=tk_runtime_binaries,
    datas=tk_runtime_data + branding_resources,
    hiddenimports=[
        "tkinter",
        "tkinter.ttk",
        "_tkinter",
        "matplotlib.backends.backend_tkagg",
        *legacy_module_imports,
    ],
    hooksconfig={"matplotlib": {"backends": ["TkAgg"]}},
    hookspath=[str(repository_root / "build" / "hooks")],
    runtime_hooks=[
        str(repository_root / "build" / "hooks" / "rthooks" / "pyi_rth_ysh_legacy_packages.py")
    ],
    excludes=["pytest", "pandas"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    name="D243",
    console=False,
    exclude_binaries=True,
    debug=False,
    strip=False,
    upx=False,
    version=str(repository_root / "build" / "version_info.txt"),
    icon=str(application_root / "resources" / "branding" / "d243_logo.ico"),
)
# Optional build-only checker shares the release PYZ/hooks and is deliberately
# absent from COLLECT. Copy it only into an isolated validation directory.
if os.environ.get("D243_BUILD_PROBE") == "1":
    probe_scripts = [
        (name, str(repository_root / "build" / "package_probe.py"), kind)
        if name == "main" else (name, path, kind)
        for name, path, kind in analysis.scripts
    ]
    EXE(
        pyz, probe_scripts, [], name="D243-package-probe",
        console=True, exclude_binaries=True, debug=False, strip=False, upx=False,
    )
COLLECT(
    executable,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="D243",
)
