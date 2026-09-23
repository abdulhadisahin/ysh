[CmdletBinding()]
param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pytestBaseTemp = Join-Path $repositoryRoot "work\pytest-release-build"

if ($PythonPath) {
    $python = (Resolve-Path -LiteralPath $PythonPath).Path
    $pythonArguments = @()
}
else {
    $python = (Get-Command py.exe -ErrorAction Stop).Source
    $pythonArguments = @("-3.14")
}

& (Join-Path $PSScriptRoot "clean_build.ps1")
if (Test-Path -LiteralPath $pytestBaseTemp) {
    Remove-Item -LiteralPath $pytestBaseTemp -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $pytestBaseTemp -Force | Out-Null
Push-Location $repositoryRoot
try {
    & $python @pythonArguments -m pytest .\YSH\tests -q --basetemp $pytestBaseTemp -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed; packaging stopped." }

    & $python @pythonArguments -m PyInstaller "$($repositoryRoot)\build\ysh.spec" --noconfirm --clean --workpath "$($repositoryRoot)\build\pyinstaller" --distpath "$($repositoryRoot)\dist"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    $executable = Join-Path $repositoryRoot "dist\YSH\YSH.exe"
    if (-not (Test-Path -LiteralPath $executable)) { throw "Expected executable missing: $executable" }
    $distribution = Join-Path $repositoryRoot "dist\YSH"
    $zip = Join-Path $repositoryRoot "dist\YSH-Test-Build.zip"
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path $distribution -DestinationPath $zip -Force

    $exeSize = (Get-Item -LiteralPath $executable).Length / 1MB
    $distSize = (Get-ChildItem -LiteralPath $distribution -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
    $zipSize = (Get-Item -LiteralPath $zip).Length / 1MB
    Write-Host ("EXE: {0} ({1:N2} MB)" -f $executable, $exeSize)
    Write-Host ("Distribution: {0} ({1:N2} MB)" -f $distribution, $distSize)
    Write-Host ("ZIP: {0} ({1:N2} MB)" -f $zip, $zipSize)
    Write-Host "Launch: .\dist\YSH\YSH.exe"
}
finally {
    Pop-Location
}
