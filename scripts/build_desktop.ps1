# Produit les installateurs Windows de DimSolaire : moteur de calcul,
# interface, puis NSIS et MSI.

$ErrorActionPreference = "Stop"

$racine = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $racine "frontend"

Write-Host "`n=== 1/4 Tests du moteur ===" -ForegroundColor Cyan
$python = Join-Path $racine "backend\.venv\Scripts\python.exe"
Push-Location (Join-Path $racine "backend")
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Des tests échouent : build interrompu." }
}
finally {
    Pop-Location
}

Write-Host "`n=== 2/4 Compilation du moteur ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "build_sidecar.ps1")
if ($LASTEXITCODE -ne 0) { throw "Compilation du moteur en échec." }

Write-Host "`n=== 3/4 Dépendances de l'interface ===" -ForegroundColor Cyan
Push-Location $frontend
try {
    if (-not (Test-Path "node_modules")) {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci en échec." }
    }

    Write-Host "`n=== 4/4 Installateurs Tauri ===" -ForegroundColor Cyan
    & npx tauri build
    if ($LASTEXITCODE -ne 0) { throw "tauri build en échec." }
}
finally {
    Pop-Location
}

$bundle = Join-Path $frontend "src-tauri\target\release\bundle"
Write-Host "`nInstallateurs produits :" -ForegroundColor Green
Get-ChildItem $bundle -Recurse -Include *.exe, *.msi -ErrorAction SilentlyContinue |
    ForEach-Object {
        $mo = [math]::Round($_.Length / 1MB, 1)
        Write-Host "   $($_.FullName) ($mo Mo)"
    }

Write-Host "`nPour les postes sans internet, passez webviewInstallMode à" -ForegroundColor Yellow
Write-Host "offlineInstaller dans tauri.conf.json et relancez ce script." -ForegroundColor Yellow
