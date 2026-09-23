# YSH Windows release build

This is an offline, 64-bit Windows one-folder release build, not an installer.

## Requirements

- Windows 10/11 64-bit
- Python 3.14 available through the Windows `py` launcher
- PyInstaller installed for that interpreter

Build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1
```

To use a specific interpreter instead of the Windows launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -PythonPath "C:\Path\To\python.exe"
```

The script runs the complete test suite, builds `dist\YSH\YSH.exe`, and creates
`dist\YSH-Test-Build.zip`. Copy and extract the complete onedir ZIP on another
Windows computer, then launch `YSH.exe`; Python, pip, Git, and internet access
are not required there.

Runtime databases and logs are per-user under `%LOCALAPPDATA%\YSH\data` and
`%LOCALAPPDATA%\YSH\logs`. Existing user data is retained across restarts.
The build includes the local YSH branding resources and Matplotlib's TkAgg
runtime for the embedded transfer-pump chart. NumPy is not a declared YSH
dependency; any bundled NumPy runtime is Matplotlib's transitive requirement.

## Clean-PC offline validation

1. Copy and extract the complete `dist\YSH-Test-Build.zip` folder to a Windows PC.
2. Disconnect the PC from the internet and launch `YSH.exe`.
3. Verify the title-bar icon, logo, and both ship assets.
4. Switch between English and Turkish, then open all four calculation tabs.
5. Perform one simple calculation in each applicable module and open Formula View.
6. Edit one library item and one reference ship or project, then close YSH.
7. Relaunch `YSH.exe` and verify project, library, and reference data persist.
8. Confirm no Python installation is required on the target PC.
