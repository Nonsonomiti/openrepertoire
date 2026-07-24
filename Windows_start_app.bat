@echo off
setlocal EnableDelayedExpansion
title OpenRepertoire

:: Si sposta nella cartella di questo file
cd /d "%~dp0"

:: ================= 1) PYTHON: lo cerca e, se manca, lo installa =================
call :detect_py
if not defined PY (
  call :install_py
  call :detect_py
)
if not defined PY (
  echo.
  echo   Non sono riuscito a installare Python automaticamente.
  echo   Apro la pagina ufficiale: scarica ed esegui l'installer,
  echo   spuntando "Add python.exe to PATH", poi rilancia questo file.
  echo.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)

:: ================= 2) DIPENDENZE: le installa se mancanti =================
:: Silenzioso quando e' gia' tutto a posto; se fallisce MOSTRA l'errore vero di pip.
"%PY%" -c "import flask, chess" 2>nul
if errorlevel 1 (
  echo.
  echo   Prima configurazione: installo le dipendenze, un attimo...
  echo.
  "%PY%" -m pip --version >nul 2>&1 || "%PY%" -m ensurepip --upgrade
  "%PY%" -m pip install --user flask chess
  :: --user non e' valido dentro un virtualenv: in quel caso si riprova senza
  "%PY%" -c "import flask, chess" 2>nul || "%PY%" -m pip install flask chess
)
"%PY%" -c "import flask, chess" 2>nul
if errorlevel 1 (
  echo.
  echo   Installazione delle dipendenze non riuscita ^(l'errore vero e' qui sopra^).
  echo   Puoi riprovare a mano con:
  echo       "%PY%" -m pip install --user flask chess
  echo.
  pause
  exit /b 1
)

:: ================= 3) AVVIO SERVER (senza finestra) =================
:: pythonw.exe accanto all'interprete usato sopra = stesso ambiente delle dipendenze
set "PYW="
for /f "delims=" %%P in ('"%PY%" -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do (
  if exist "%%P" set "PYW=%%P"
)
if not defined PYW ( where pythonw >nul 2>&1 && set "PYW=pythonw" )
if not defined PYW ( where pyw     >nul 2>&1 && set "PYW=pyw" )

if defined PYW (
  start "" "!PYW!" "%~dp0app.py"
) else (
  :: Nessun pythonw disponibile (tipico con Python dal Microsoft Store):
  :: si ripiega su una console minimizzata, cosi' resta fuori dai piedi.
  start "OpenRepertoire" /min "%PY%" "%~dp0app.py"
)

:: ================= 4) ATTESA SERVER PRONTO (max ~20s) =================
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

:: ================= 5) BROWSER GIA' APERTO (altrimenti il predefinito) =================
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


:: ===================== SUBROUTINE =====================

:detect_py
:: Non basta che il comando esista: gli alias del Microsoft Store sono presenti
:: anche senza Python installato e aprono lo Store invece di eseguire il codice.
:: Per questo si verifica che l'interprete ESEGUA davvero.
set "PY="
for %%C in (python py python3) do (
  if not defined PY (
    %%C -c "print(1)" >nul 2>&1 && set "PY=%%C"
  )
)
:: Appena installato "per utente" il PATH di QUESTA finestra non e' ancora
:: aggiornato: si cerca l'eseguibile nei percorsi standard.
if not defined PY (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if not defined PY if exist "%%D\python.exe" set "PY=%%D\python.exe"
  )
)
if not defined PY (
  for /d %%D in ("%ProgramFiles%\Python3*") do (
    if not defined PY if exist "%%D\python.exe" set "PY=%%D\python.exe"
  )
)
goto :eof


:install_py
echo.
echo   Python non e' installato su questo PC: lo installo ora.
echo   Serve una connessione a Internet; ci vorranno un paio di minuti.
echo.
:: --- A) winget (presente su Windows 11 e Windows 10 aggiornati) ---
where winget >nul 2>&1
if not errorlevel 1 (
  echo   [1/2] Installazione tramite winget ^(Microsoft^)...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  call :detect_py
  if defined PY (
    echo   Python installato.
    goto :eof
  )
)
:: --- B) Installer ufficiale python.org ---
where curl >nul 2>&1
if errorlevel 1 goto :eof
set "PYVER=3.12.7"
set "PYSETUP=%TEMP%\python-%PYVER%-amd64.exe"
echo   [2/2] Scarico l'installer ufficiale da python.org...
curl -L --fail -o "%PYSETUP%" "https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
if not exist "%PYSETUP%" goto :eof
echo   Installazione in corso...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
del "%PYSETUP%" >nul 2>&1
echo   Python installato.
goto :eof
