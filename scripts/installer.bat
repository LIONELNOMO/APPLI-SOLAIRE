@echo off
rem ===================================================================
rem  DimSolaire - installation des dependances
rem
rem  A lancer une seule fois, avant le premier demarrage.
rem  Prerequis : Python 3.12 et Node.js 20 ou plus recents.
rem ===================================================================

setlocal
cd /d "%~dp0.."

set "RACINE=%cd%"
set "BACKEND=%RACINE%\backend"
set "FRONTEND=%RACINE%\frontend"

title DimSolaire - installation

echo.
echo  ==============================================================
echo    DimSolaire - installation des dependances
echo  ==============================================================
echo.

rem --- Recherche de Python 3.12 ---------------------------------------
set "PY_SYS="
for %%c in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "C:\Python312\python.exe"
) do (
    if exist %%c set "PY_SYS=%%~c"
)
if not defined PY_SYS (
    where python >nul 2>&1 && set "PY_SYS=python"
)
if not defined PY_SYS (
    echo  [ERREUR] Python 3.12 est introuvable.
    echo.
    echo  Installez-le depuis https://www.python.org/downloads/
    echo  en cochant "Add Python to PATH", puis relancez ce script.
    echo.
    pause
    exit /b 1
)
echo  Python detecte : %PY_SYS%
"%PY_SYS%" --version

rem --- Verification de Node.js ----------------------------------------
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERREUR] Node.js est introuvable.
    echo.
    echo  Installez-le depuis https://nodejs.org/ (version 20 ou plus),
    echo  puis relancez ce script.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo  Node.js detecte : %%v

rem --- 1. Environnement Python ----------------------------------------
echo.
echo  [1/3] Environnement Python...
if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    "%PY_SYS%" -m venv "%BACKEND%\.venv"
    if errorlevel 1 (
        echo  [ERREUR] Creation de l'environnement virtuel en echec.
        pause
        exit /b 1
    )
    echo        Environnement cree.
) else (
    echo        Environnement deja present.
)

rem --- 2. Dependances du moteur ---------------------------------------
echo.
echo  [2/3] Dependances du moteur de calcul...
pushd "%BACKEND%"
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -e ".[dev]"
if errorlevel 1 (
    echo  [ERREUR] Installation des dependances Python en echec.
    popd
    pause
    exit /b 1
)
echo        Dependances installees.

echo.
echo        Verification du moteur par les tests...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo  [AVERTISSEMENT] Des tests echouent : l'installation continue,
    echo                  mais signalez-le avant utilisation reelle.
) else (
    echo        Tous les tests passent.
)
popd

rem --- 3. Dependances de l'interface ----------------------------------
echo.
echo  [3/3] Dependances de l'interface...
pushd "%FRONTEND%"
if exist "package-lock.json" (
    call npm ci
) else (
    call npm install
)
if errorlevel 1 (
    echo  [ERREUR] Installation des dependances de l'interface en echec.
    popd
    pause
    exit /b 1
)
echo        Dependances installees.
popd

echo.
echo  ==============================================================
echo    Installation terminee.
echo.
echo    Lancez DimSolaire avec : DimSolaire.bat
echo  ==============================================================
echo.
pause
exit /b 0
