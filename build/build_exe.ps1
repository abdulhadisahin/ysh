[CmdletBinding()]
param(
    [string]$PythonPath = "",
    [string]$TclLibrary = "",
    [string]$TkLibrary = ""
)
$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pytestBaseTemp = Join-Path $repositoryRoot "work\pytest-release-build"
if ($PythonPath) {
    $python = (Resolve-Path -LiteralPath $PythonPath).Path
    $pythonArguments = @()
} else {
    $python = (Get-Command py.exe -ErrorAction Stop).Source
    $pythonArguments = @("-3.14")
}
$oldTcl = $env:TCL_LIBRARY
$oldTk = $env:TK_LIBRARY
$oldProbe = $env:D243_BUILD_PROBE
Push-Location $repositoryRoot
try {
    if ($TclLibrary) { $env:TCL_LIBRARY = (Resolve-Path -LiteralPath $TclLibrary).Path }
    if ($TkLibrary) { $env:TK_LIBRARY = (Resolve-Path -LiteralPath $TkLibrary).Path }
    $env:D243_BUILD_PROBE = "1"
    & $python @pythonArguments -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed; packaging stopped." }
    & $python @pythonArguments -m PyInstaller .\build\ysh.spec --noconfirm --clean --workpath .\build\pyinstaller --distpath .\dist
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
    $distribution = Join-Path $repositoryRoot "dist\D243"
    $executable = Join-Path $distribution "D243.exe"
    if (-not (Test-Path -LiteralPath $executable)) { throw "Expected executable missing: $executable" }
    # A new validation directory retains prior evidence; no recursive cleanup.
    $checkRoot = Join-Path $repositoryRoot ("work\package-check-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $checkRoot | Out-Null
    Copy-Item -LiteralPath $distribution -Destination $checkRoot -Recurse
    $isolated = Join-Path $checkRoot "D243"
    $probe = Join-Path $repositoryRoot "build\pyinstaller\ysh\D243-package-probe.exe"
    Copy-Item -LiteralPath $probe -Destination $isolated
    $profile = Join-Path $checkRoot "profile"
    Push-Location $isolated
    try {
        & (Join-Path $isolated "D243-package-probe.exe") $profile
        if ($LASTEXITCODE -ne 0) { throw "Frozen package probe failed; ZIP not created. See $profile" }
    } finally { Pop-Location }
    $zip = Join-Path $repositoryRoot "dist\D243_V2_Windows_x64.zip"
    Compress-Archive -LiteralPath $distribution -DestinationPath $zip -Force
    Get-FileHash -LiteralPath $zip -Algorithm SHA256
    Write-Host "Release: $zip"
    Write-Host "Manual Windows acceptance of D243.exe is still required."
} finally {
    $env:TCL_LIBRARY = $oldTcl
    $env:TK_LIBRARY = $oldTk
    $env:D243_BUILD_PROBE = $oldProbe
    Pop-Location
}
