@echo off
rem ===================================================================
rem  DimSolaire - lancement du moteur de calcul et de l'interface
rem
rem  Ouvre deux serveurs :
rem    - le moteur Python (FastAPI) sur 127.0.0.1:8000
rem    - l'interface React (Vite)   sur 127.0.0.1:5173
rem  puis ouvre le navigateur sur l'interface.
rem
rem  Fermez cette fenetre pour arreter les deux serveurs.
rem ===================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "RACINE=%~dp0"
set "BACKEND=%RACINE%backend"
set "FRONTEND=%RACINE%frontend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"
set "PORT_API=8000"
set "PORT_WEB=5173"

title DimSolaire - Dimensionnement photovoltaique

echo.
echo  ==============================================================
echo    DimSolaire 1.0.0
echo    Dimensionnement photovoltaique et injection au reseau
echo  ==============================================================
echo.

rem --- Verifications prealables ---------------------------------------
if not exist "%PYTHON%" (
    echo  [ERREUR] Environnement Python introuvable :
    echo           %PYTHON%
    echo.
    echo  Premiere installation ? Lancez d'abord :
    echo           scripts\installer.bat
    echo.
    pause
    exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo  [ERREUR] Dependances de l'interface absentes.
    echo.
    echo  Lancez d'abord : scripts\installer.bat
    echo.
    pause
    exit /b 1
)

rem --- Liberation des ports si une session precedente traine ----------
call :liberer_port %PORT_API% "moteur de calcul"
call :liberer_port %PORT_WEB% "interface"

rem --- 1. Moteur de calcul --------------------------------------------
echo  [1/2] Demarrage du moteur de calcul sur le port %PORT_API%...
set "DIMSOLAIRE_MODE=dev"
set "DATABASE_URL=sqlite:///%BACKEND:\=/%/dimsolaire.db"
set "DIMSOLAIRE_CORS=http://localhost:%PORT_WEB%,http://127.0.0.1:%PORT_WEB%"

start "DimSolaire - moteur de calcul" /min cmd /c ^
  "cd /d "%BACKEND%" && "%PYTHON%" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port %PORT_API%"

rem --- Attente de la disponibilite du moteur --------------------------
echo        Attente de la reponse du moteur...
set /a ESSAIS=0
:attente_api
set /a ESSAIS+=1
if !ESSAIS! gtr 60 (
    echo.
    echo  [ERREUR] Le moteur de calcul n'a pas demarre en 30 secondes.
    echo           Consultez la fenetre "DimSolaire - moteur de calcul".
    echo.
    pause
    exit /b 1
)
"%PYTHON%" -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%PORT_API%/api/v1/health',timeout=2).status==200 else 1)" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto attente_api
)
echo        Moteur de calcul pret.

rem --- 2. Interface ---------------------------------------------------
echo  [2/2] Demarrage de l'interface sur le port %PORT_WEB%...
set "VITE_API_URL=http://127.0.0.1:%PORT_API%"

start "DimSolaire - interface" /min cmd /c ^
  "cd /d "%FRONTEND%" && npm run dev -- --port %PORT_WEB% --strictPort"

echo        Attente de la compilation de l'interface...
set /a ESSAIS=0
:attente_web
set /a ESSAIS+=1
if !ESSAIS! gtr 90 (
    echo.
    echo  [ERREUR] L'interface n'a pas demarre en 45 secondes.
    echo           Consultez la fenetre "DimSolaire - interface".
    echo.
    pause
    exit /b 1
)
"%PYTHON%" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(s.connect_ex(('127.0.0.1',%PORT_WEB%)))" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto attente_web
)
echo        Interface prete.

rem --- Ouverture du navigateur ----------------------------------------
echo.
echo  ==============================================================
echo    DimSolaire est demarre.
echo.
echo      Interface        http://localhost:%PORT_WEB%
echo      Moteur           http://127.0.0.1:%PORT_API%/api/v1/health
echo      Documentation    http://127.0.0.1:%PORT_API%/docs
echo.
echo    Fermez cette fenetre pour arreter les deux serveurs.
echo  ==============================================================
echo.

timeout /t 2 /nobreak >nul
start "" "http://localhost:%PORT_WEB%"

rem --- Maintien en vie puis arret propre ------------------------------
echo  Appuyez sur une touche pour arreter DimSolaire...
pause >nul

echo.
echo  Arret des serveurs...
call :liberer_port %PORT_API% "moteur de calcul"
call :liberer_port %PORT_WEB% "interface"
taskkill /FI "WINDOWTITLE eq DimSolaire - moteur*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DimSolaire - interface*" /T /F >nul 2>&1
echo  DimSolaire est arrete.
timeout /t 2 /nobreak >nul
exit /b 0

rem ===================================================================
rem  Libere un port encore occupe par une session precedente.
rem ===================================================================
:liberer_port
set "P=%~1"
set "QUOI=%~2"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:"TCP.*:%P% .*LISTENING"') do (
    echo        Port %P% occupe (%QUOI%) : arret du processus %%a
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)
exit /b 0
