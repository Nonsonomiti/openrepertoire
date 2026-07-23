@echo off
setlocal EnableDelayedExpansion
title OpenRepertoire

:: Si sposta nella cartella di questo file
cd /d "%~dp0"

:: ---- 1) Trova un interprete Python ----
set "PY="
where python  >nul 2>&1 && set "PY=python"
if not defined PY ( where py      >nul 2>&1 && set "PY=py" )
if not defined PY ( where python3 >nul 2>&1 && set "PY=python3" )
if not defined PY (
  echo.
  echo   Python non risulta installato ^(o non e' nel PATH^).
  echo   Scaricalo da https://www.python.org/downloads/
  echo   IMPORTANTE: spunta "Add python.exe to PATH" durante l'installazione.
  echo.
  pause
  exit /b 1
)

:: ---- 2) Dipendenze: installa solo se mancanti (silenzioso) ----
%PY% -c "import flask, chess" 2>nul
if errorlevel 1 %PY% -m pip install flask chess >nul 2>&1
%PY% -c "import flask, chess" 2>nul
if errorlevel 1 (
  echo.
  echo   Impossibile installare le dipendenze ^(flask, chess^).
  echo   Controlla la connessione a Internet e riprova.
  echo.
  pause
  exit /b 1
)

:: ---- 3) Cerca un interprete SENZA finestra (niente console/avvisi Flask) ----
:: Prima pythonw.exe accanto all'interprete usato sopra: stesso ambiente delle dipendenze.
set "PYW="
for /f "delims=" %%P in ('%PY% -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do (
  if exist "%%P" set "PYW=%%P"
)
if not defined PYW ( where pythonw >nul 2>&1 && set "PYW=pythonw" )
if not defined PYW ( where pyw     >nul 2>&1 && set "PYW=pyw" )

:: ---- 4) Avvia il server scollegato ----
if defined PYW (
  start "" "!PYW!" "%~dp0app.py"
) else (
  :: Nessun pythonw disponibile (tipico con Python dal Microsoft Store):
  :: si ripiega su una console minimizzata, cosi' resta fuori dai piedi.
  start "OpenRepertoire" /min "%PY%" "%~dp0app.py"
)

:: ---- 5) Attende che il server risponda (max ~20s) ----
set "URL=http://127.0.0.1:5001"
set "READY="
where curl >nul 2>&1
if not errorlevel 1 (
  for /l %%i in (1,1,20) do (
    if not defined READY (
      curl -s -o nul "%URL%" >nul 2>&1 && set "READY=1"
      if not defined READY timeout /t 1 /nobreak >nul
    )
  )
) else (
  timeout /t 3 /nobreak >nul
)

:: ---- 6) Apre nel browser gia' aperto; altrimenti quello predefinito ----
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
