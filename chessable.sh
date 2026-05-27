#!/bin/bash

# Si sposta nella cartella dello script
cd "$(dirname "$0")"

# Avvia il server Python in background
python3 app.py &

# Aspetta 2 secondi per far avviare il server
sleep 2

# Apre l'app nel browser predefinito di Linux
xdg-open http://127.0.0.1:5001