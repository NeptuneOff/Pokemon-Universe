@echo off
setlocal
cd /d "%~dp0native-runtime\windows-fr"
if errorlevel 1 goto missing
if not exist universe-install.json goto missing
if not exist main.exe goto missing
main.exe
if errorlevel 1 (
  echo Le port natif s'est ferme avec une erreur. Voir DbgLog.txt dans ce dossier.
  pause
  exit /b 1
)
exit /b 0
:missing
echo Lance d'abord PREPARER-PLATINE.bat a la racine du projet.
pause
exit /b 1
