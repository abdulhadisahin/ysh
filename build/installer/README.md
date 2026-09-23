# YSH Windows Installer

`ysh.iss` packages the accepted `dist\YSH` onedir payload as an offline,
per-user Windows installer.

## Build

Install Inno Setup locally, then run:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\build\installer\ysh.iss
```

The output is `dist\installer\YSH-Setup-0.1.0.exe`.

## Release properties

- Installs to `%LOCALAPPDATA%\Programs\YSH` without administrator rights.
- Creates a Start Menu shortcut and offers an optional Desktop shortcut.
- Preserves `%LOCALAPPDATA%\YSH\data` and `%LOCALAPPDATA%\YSH\logs` on uninstall.
- Works offline and bundles the complete onedir payload.
- Is unsigned unless a trusted code-signing certificate is supplied; Windows
  SmartScreen may warn users before installation.
