@echo off
setlocal EnableDelayedExpansion
title OpenRepertoire

:: Si sposta nella cartella di questo file
cd /d "%~dp0"

:: Dipendenze: installa solo se mancanti (silenzioso)
python -c "import flask, chess" 2>nul || python -m pip install flask chess >nul 2>&1

:: Avvia il server SENZA finestra e scollegato (pythonw = niente console/avvisi)
start "" pythonw "%~dp0app.py"

:: Attende che il server sia pronto
timeout /t 2 /nobreak >nul

set "URL=http://127.0.0.1:5001"

:: Apre nel browser gia' aperto (in ordine di preferenza); altrimenti il predefinito
set "BROWSER="
for %%B in (chrome msedge brave vivaldi opera firefox) do (
  if not defined BROWSER (
    tasklist /FI "IMAGENAME eq %%B.exe" 2>nul | find /I "%%B.exe" >nul && set "BROWSER=%%B.exe"
  )
)

if defined BROWSER (
  start "" "!BROWSER!" "%URL%"
) else (
  start "" "%URL%"
)

:: Fine: la finestra si chiude da sola
exit
