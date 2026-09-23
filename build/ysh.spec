# -*- mode: python ; coding: utf-8 -*-
"""Reproducible onedir diagnostic PyInstaller build for YSH."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


repository_root = Path(SPECPATH).resolve().parent
application_root = repository_root / "YSH"
main_entry = repository_root / "main.py"
python_root = Path(sys.base_prefix)
tcl_root = python_root / "tcl"
tk_runtime_data = [
    (str(tcl_root / "tcl8.6"), "_tcl_data"),
    (str(tcl_root / "tk8.6"), "_tk_data"),
]
tk_runtime_binaries = [
    (str(python_root / "DLLs" / filename), ".")
    for filename in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll")
]
matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all(
    "matplotlib"
)
branding_resources = [(str(application_root / "resources"), "resources")]
legacy_module_imports = [
    ".".join(module_path.relative_to(application_root).with_suffix("").parts)
    for module_path in application_root.rglob("*.py")
    if "tests" not in module_path.parts and module_path.name != "__init__.py"
]

analysis = Analysis(
    [str(main_entry)],
    pathex=[str(repository_root), str(application_root)],
    binaries=tk_runtime_binaries + matplotlib_binaries,
    datas=tk_runtime_data + matplotlib_datas + branding_resources,
    hiddenimports=[
        "tkinter",
        "tkinter.ttk",
        "_tkinter",
        "matplotlib.backends.backend_tkagg",
        *legacy_module_imports,
        *matplotlib_hiddenimports,
    ],
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
    name="YSH",
    console=True,
    exclude_binaries=True,
    debug=False,
    strip=False,
    upx=False,
    icon=str(application_root / "resources" / "ysh.ico"),
)
COLLECT(
    executable,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="YSH",
)
