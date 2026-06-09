#!/bin/bash

# Si sposta nella cartella dello script
cd "$(dirname "$0")"

# Installa le dipendenze se mancanti
python3 -m pip install --user --quiet flask chess 2>/dev/null \
  || python3 -m pip install --user --quiet --break-system-packages flask chess

# Avvia il server Python in background
python3 app.py &

# Aspetta 2 secondi per far avviare il server
sleep 2

# Apre l'app nel browser predefinito di Linux
xdg-open http://127.0.0.1:5001