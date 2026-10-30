@echo off
setlocal
set "universe_ps=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 set "universe_ps=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
set "universe_args=%*"
if "%~1"=="" set "universe_args=-Menu"
"%universe_ps%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\native\start_windows.ps1" %universe_args%
set "universe_result=%errorlevel%"
if not "%universe_result%"=="0" (
  echo.
  echo Le lancement a echoue. Le chemin du diagnostic est indique ci-dessus.
  pause
)
exit /b %universe_result%
