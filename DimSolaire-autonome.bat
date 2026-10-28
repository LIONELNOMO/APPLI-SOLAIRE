@echo off
rem ===================================================================
rem  DimSolaire - version autonome
rem
rem  Lance le moteur de calcul compile (dimsolaire-api.exe) et sert
rem  l'interface deja construite. Ne demande ni Python ni Node.js.
rem
rem  Prerequis : avoir lance une fois scripts\build_autonome.bat
rem ===================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "RACINE=%~dp0"
set "MOTEUR=%RACINE%backend\dist\dimsolaire-api.exe"
set "STATIQUE=%RACINE%frontend\dist"
set "PORT=8000"

title DimSolaire - Dimensionnement photovoltaique

echo.
echo  ==============================================================
echo    DimSolaire 1.0.0 - version autonome
echo  ==============================================================
echo.

if not exist "%MOTEUR%" (
    echo  [ERREUR] Moteur de calcul compile introuvable :
    echo           %MOTEUR%
    echo.
    echo  Lancez d'abord : scripts\build_autonome.bat
    echo.
    pause
    exit /b 1
)

if not exist "%STATIQUE%\index.html" (
    echo  [ERREUR] Interface compilee introuvable :
    echo           %STATIQUE%
    echo.
    echo  Lancez d'abord : scripts\build_autonome.bat
    echo.
    pause
    exit /b 1
)

rem --- Liberation du port si une session traine -----------------------
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:"TCP.*:%PORT% .*LISTENING"') do (
    echo  Port %PORT% occupe : arret du processus %%a
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)

rem --- Un seul serveur suffit : il sert l'API et l'interface ----------
echo  Demarrage du moteur et de l'interface sur le port %PORT%...

set "DIMSOLAIRE_MODE=web"
set "DIMSOLAIRE_STATIC_DIR=%STATIQUE%"
set "DIMSOLAIRE_CORS=http://localhost:%PORT%"

set "DOSSIER_DONNEES=%APPDATA%\cm.dimsolaire.app"
if not exist "%DOSSIER_DONNEES%" mkdir "%DOSSIER_DONNEES%"

start "DimSolaire - moteur" /min "%MOTEUR%" --port %PORT% --db "%DOSSIER_DONNEES%\dimsolaire.db" --log "%DOSSIER_DONNEES%\logs\api.log" --static "%STATIQUE%"

echo  Attente de la reponse du moteur...
set /a ESSAIS=0
:attente
set /a ESSAIS+=1
if !ESSAIS! gtr 60 (
    echo.
    echo  [ERREUR] Le moteur n'a pas demarre en 30 secondes.
    echo           Journal : %DOSSIER_DONNEES%\logs\api.log
    echo.
    pause
    exit /b 1
)
powershell -NoProfile -Command "try { $r = Invoke-RestMethod 'http://127.0.0.1:%PORT%/api/v1/health' -TimeoutSec 2; if ($r.statut -eq 'ok') { exit 0 } } catch { }; exit 1" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto attente
)

echo.
echo  ==============================================================
echo    DimSolaire est demarre.
echo.
echo      Interface        http://localhost:%PORT%
echo      Documentation    http://localhost:%PORT%/docs
echo      Donnees          %DOSSIER_DONNEES%
echo.
echo    Fermez cette fenetre pour arreter DimSolaire.
echo  ==============================================================
echo.

timeout /t 1 /nobreak >nul
start "" "http://localhost:%PORT%"

echo  Appuyez sur une touche pour arreter DimSolaire...
pause >nul

echo.
echo  Arret du moteur...
taskkill /IM dimsolaire-api.exe /F >nul 2>&1
echo  DimSolaire est arrete.
timeout /t 2 /nobreak >nul
exit /b 0
