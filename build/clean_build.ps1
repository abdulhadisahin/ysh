[CmdletBinding()]
param()

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targets = @(
    (Join-Path $repositoryRoot "build\pyinstaller"),
    (Join-Path $repositoryRoot "dist")
)

foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

Get-ChildItem -LiteralPath $repositoryRoot -Filter "*.spec.cache" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force

Write-Host "Generated PyInstaller artifacts removed."
