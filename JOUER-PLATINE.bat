@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 tools\native\launch_platinum.py
) else (
  python tools\native\launch_platinum.py
)
if not errorlevel 1 exit /b 0
echo Le lancement ou le jeu a rencontre une erreur. Conserver le message ci-dessus.
echo Voir aussi native-runtime\windows-fr\DbgLog.txt si le jeu a demarre.
pause
exit /b 1
