@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 tools\native\prepare_platinum.py --gui --platform windows
) else (
  python --version >nul 2>&1
  if errorlevel 1 (
    echo Python 3 est necessaire. Installe-le depuis https://www.python.org/downloads/windows/
    echo Puis relance PREPARER-PLATINE.bat.
    pause
    exit /b 1
  )
  python tools\native\prepare_platinum.py --gui --platform windows
)
if errorlevel 1 (
  echo Preparation interrompue. Le dossier existant et ses sauvegardes sont conserves.
  pause
  exit /b 1
)
echo Preparation terminee. Lance JOUER-PLATINE.bat.
pause
