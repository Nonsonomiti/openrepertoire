#!/bin/bash
# OpenRepertoire — avvio Linux
cd "$(dirname "$0")" || exit 1

URL="http://127.0.0.1:5001"
LOG="$PWD/.openrepertoire.log"

# Dipendenze: installa solo se mancanti (log su file)
python3 -c "import flask, chess" 2>/dev/null || {
  python3 -m pip install --user --quiet flask chess \
    || python3 -m pip install --user --quiet --break-system-packages flask chess
} >"$LOG" 2>&1

# Chiude eventuale istanza vecchia sulla porta
command -v fuser >/dev/null && fuser -k 5001/tcp 2>/dev/null

# Avvia il server scollegato dal terminale (sopravvive alla chiusura)
setsid nohup python3 app.py >>"$LOG" 2>&1 &
disown 2>/dev/null

# Attende che il server risponda (max ~10s)
for _ in $(seq 1 50); do
  { command -v curl >/dev/null && curl -s -o /dev/null "$URL"; } && break
  { command -v wget >/dev/null && wget -q -O /dev/null "$URL"; } && break
  sleep 0.2
done

# --- Apertura nel browser gia' in esecuzione; altrimenti quello predefinito ---
# coppie "pattern-processo:comando-lancio", in ordine di preferenza
launch() {
  for pair in \
    "chrome:google-chrome" "chrome:google-chrome-stable" \
    "chromium:chromium" "chromium:chromium-browser" \
    "brave:brave-browser" "microsoft-edge:microsoft-edge" \
    "vivaldi:vivaldi" "opera:opera" "firefox:firefox"; do
    pat="${pair%%:*}"; cmd="${pair##*:}"
    if pgrep -x "$pat" >/dev/null 2>&1 || pgrep -f "$cmd" >/dev/null 2>&1; then
      command -v "$cmd" >/dev/null 2>&1 && { setsid "$cmd" "$URL" >/dev/null 2>&1 & return; }
    fi
  done
  setsid xdg-open "$URL" >/dev/null 2>&1 &
}
launch

# Il terminale (se aperto dal file manager) si chiude uscendo subito
exit 0
