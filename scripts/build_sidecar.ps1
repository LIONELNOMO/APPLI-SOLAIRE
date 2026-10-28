# Compile le moteur de calcul Python en exécutable, puis le place là où
# Tauri l'attend. Le nom doit porter le triplet de la cible, sinon Tauri
# ne reconnaît pas le sidecar.

$ErrorActionPreference = "Stop"

$racine = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $racine "backend"
$binaires = Join-Path $racine "frontend\src-tauri\binaries"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Environnement Python absent : $python. Créez-le avec 'python -m venv .venv' dans backend."
}

Write-Host "== Triplet de la cible ==" -ForegroundColor Cyan
$triplet = (& rustc -vV | Select-String '^host:').Line -replace '^host:\s*', ''
if (-not $triplet) { throw "Impossible de lire le triplet via 'rustc -vV'." }
Write-Host "   $triplet"

Write-Host "== Installation de PyInstaller ==" -ForegroundColor Cyan
& $python -m pip install --quiet --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Installation de PyInstaller en échec." }

Write-Host "== Compilation du moteur ==" -ForegroundColor Cyan
Push-Location $backend
try {
    & $python -m PyInstaller --noconfirm --clean dimsolaire-api.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller a échoué." }
}
finally {
    Pop-Location
}

$source = Join-Path $backend "dist\dimsolaire-api.exe"
if (-not (Test-Path $source)) { throw "Exécutable introuvable : $source" }

Write-Host "== Vérification du démarrage ==" -ForegroundColor Cyan
# Un exécutable qui ne démarre pas produirait une version PC inutilisable :
# on le lance sur un port libre avant de le livrer.
$port = 8777
$baseTest = Join-Path $env:TEMP "dimsolaire-verif.db"
$processus = Start-Process -FilePath $source `
    -ArgumentList "--port", $port, "--db", $baseTest `
    -PassThru -WindowStyle Hidden
try {
    $pret = $false
    foreach ($essai in 1..40) {
        Start-Sleep -Milliseconds 500
        try {
            $reponse = Invoke-RestMethod "http://127.0.0.1:$port/api/v1/health" -TimeoutSec 2
            if ($reponse.statut -eq "ok") { $pret = $true; break }
        }
        catch { }
    }
    if (-not $pret) { throw "Le moteur compilé ne répond pas sur /health." }
    Write-Host "   Moteur fonctionnel (mode $($reponse.mode), version $($reponse.version))"
}
finally {
    if (-not $processus.HasExited) { Stop-Process -Id $processus.Id -Force }
    if (Test-Path $baseTest) { Remove-Item $baseTest -Force -ErrorAction SilentlyContinue }
}

Write-Host "== Copie vers Tauri ==" -ForegroundColor Cyan
if (-not (Test-Path $binaires)) { New-Item -ItemType Directory -Path $binaires -Force | Out-Null }
$destination = Join-Path $binaires "dimsolaire-api-$triplet.exe"
Copy-Item $source $destination -Force

$taille = [math]::Round((Get-Item $destination).Length / 1MB, 1)
Write-Host "   $destination ($taille Mo)" -ForegroundColor Green
Write-Host "`nSidecar prêt." -ForegroundColor Green
