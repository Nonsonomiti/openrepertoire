@echo off
echo Avvio del server Local Chessable...

:: Si sposta nella cartella in cui si trova questo file
cd /d "%~dp0"

:: Controlla e installa le dipendenze in modo silenzioso
pip install flask chess >nul 2>&1

:: Avvia l'app in background (non blocca la finestra)
start /B python app.py

:: Attende 2 secondi per far avviare il server
timeout /t 2 /nobreak >nul

:: Apre il sito nel browser predefinito di Windows
start http://127.0.0.1:5001