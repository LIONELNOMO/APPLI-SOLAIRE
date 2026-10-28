@echo off
rem ===================================================================
rem  DimSolaire - construction de la version autonome
rem
rem  Compile le moteur de calcul en executable et construit l'interface.
rem  Le resultat se lance avec DimSolaire-autonome.bat, sans Python
rem  ni Node.js sur le poste cible.
rem ===================================================================

setlocal
cd /d "%~dp0.."

set "RACINE=%cd%"
set "BACKEND=%RACINE%\backend"
set "FRONTEND=%RACINE%\frontend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"

title DimSolaire - construction de la version autonome

echo.
echo  ==============================================================
echo    DimSolaire - construction de la version autonome
echo  ==============================================================
echo.

if not exist "%PYTHON%" (
    echo  [ERREUR] Environnement Python absent.
    echo           Lancez d'abord scripts\installer.bat
    pause
    exit /b 1
)

rem --- 1. Tests du moteur ---------------------------------------------
echo  [1/4] Tests du moteur de calcul...
pushd "%BACKEND%"
"%PYTHON%" -m pytest -q
if errorlevel 1 (
    echo.
    echo  [ERREUR] Des tests echouent : construction interrompue.
    popd
    pause
    exit /b 1
)
echo        Tous les tests passent.

rem --- 2. Compilation du moteur ---------------------------------------
echo.
echo  [2/4] Compilation du moteur en executable...
"%PYTHON%" -m pip install --quiet --upgrade pyinstaller pillow
"%PYTHON%" -m PyInstaller --noconfirm --clean dimsolaire-api.spec
if errorlevel 1 (
    echo  [ERREUR] PyInstaller en echec.
    popd
    pause
    exit /b 1
)
popd

if not exist "%BACKEND%\dist\dimsolaire-api.exe" (
    echo  [ERREUR] Executable non produit.
    pause
    exit /b 1
)
echo        Executable produit.

rem --- 3. Recette de l'executable -------------------------------------
echo.
echo  [3/4] Recette de l'executable...
pushd "%BACKEND%"
"%PYTHON%" verif_sidecar.py
if errorlevel 1 (
    echo  [ERREUR] L'executable ne fonctionne pas correctement.
    popd
    pause
    exit /b 1
)
popd

rem --- 4. Construction de l'interface ---------------------------------
echo.
echo  [4/4] Construction de l'interface...
pushd "%FRONTEND%"
if not exist "node_modules" (
    call npm ci
    if errorlevel 1 (
        echo  [ERREUR] npm ci en echec.
        popd
        pause
        exit /b 1
    )
)
call npm run build
if errorlevel 1 (
    echo  [ERREUR] Construction de l'interface en echec.
    popd
    pause
    exit /b 1
)
popd
echo        Interface construite.

echo.
echo  ==============================================================
echo    Version autonome prete.
echo.
echo    Lancez-la avec : DimSolaire-autonome.bat
echo.
echo    Pour distribuer, copiez ces elements sur le poste cible :
echo      DimSolaire-autonome.bat
echo      backend\dist\dimsolaire-api.exe
echo      frontend\dist\
echo  ==============================================================
echo.
pause
exit /b 0
