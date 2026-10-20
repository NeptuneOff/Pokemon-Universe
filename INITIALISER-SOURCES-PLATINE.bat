@echo off
setlocal
cd /d "%~dp0"
git --version >nul 2>&1
if errorlevel 1 (
  echo Git est necessaire. Installe Git pour Windows puis relance ce fichier.
  pause
  exit /b 1
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo Ce dossier doit provenir de git clone, pas de Download ZIP.
  echo git clone --recurse-submodules https://github.com/NeptuneOff/Pokemon-Universe.git
  pause
  exit /b 1
)
git submodule update --init engine/platinum
if errorlevel 1 (
  echo Preparation interrompue. Consulte le message Git ci-dessus.
  pause
  exit /b 1
)
echo Source Platine PC preparee. Revision :
git -C engine/platinum rev-parse HEAD
echo Aucun jeu Universe compile. Voir README.md et docs/PLATINUM-BASE.md.
pause
