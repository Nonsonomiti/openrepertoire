#!/bin/bash
# OpenRepertoire — avvio macOS
cd "$(dirname "$0")" || exit 1

URL="http://127.0.0.1:5001"
LOG="$PWD/.openrepertoire.log"

# Toglie la quarantena Gatekeeper (silenzioso)
xattr -dr com.apple.quarantine . 2>/dev/null

# Python: su macOS arriva con gli Strumenti da riga di comando di Apple.
# Se manca, si avvia l'installer ufficiale Apple (finestra grafica) e si esce.
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e "display alert \"Manca Python\" message \"Avvio l'installer ufficiale di Apple (Strumenti da riga di comando). Completa la procedura, poi riapri OpenRepertoire.\"" >/dev/null 2>&1
  xcode-select --install >/dev/null 2>&1
  exit 1
fi

# Dipendenze: installa solo se mancanti (log su file, niente rumore a schermo)
python3 -c "import flask, chess" 2>/dev/null || {
  python3 -m pip install --user --quiet flask chess \
    || python3 -m pip install --user --quiet --break-system-packages flask chess
} >"$LOG" 2>&1

# Se le dipendenze mancano ancora, avvisa invece di aprire una pagina morta
python3 -c "import flask, chess" 2>/dev/null || {
  osascript -e "display alert \"Dipendenze mancanti\" message \"Non sono riuscito a installare flask e chess. Apri il Terminale ed esegui: python3 -m pip install --user flask chess\"" >/dev/null 2>&1
  exit 1
}

# Chiude eventuale istanza vecchia sulla porta
lsof -ti tcp:5001 | xargs kill -9 2>/dev/null

# Avvia il server scollegato dal Terminale (sopravvive alla chiusura della finestra)
nohup python3 app.py >>"$LOG" 2>&1 &
disown

# Attende che il server risponda (max ~10s)
for _ in $(seq 1 50); do
  curl -s -o /dev/null "$URL" && break
  sleep 0.2
done

# --- Apertura nel browser gia' in uso ---
BROWSERS=(
  "Google Chrome" "Brave Browser" "Microsoft Edge" "Arc" "Vivaldi"
  "Opera" "Chromium" "Firefox" "Firefox Developer Edition" "Safari"
)
is_running() { pgrep -f "/$1.app/" >/dev/null 2>&1; }
open_url() {
  local front
  front=$(lsappinfo info -only name "$(lsappinfo front)" 2>/dev/null | sed -E 's/.*="([^"]*)".*/\1/')
  for b in "${BROWSERS[@]}"; do [ "$front" = "$b" ] && { open -a "$b" "$URL"; return; }; done
  for b in "${BROWSERS[@]}"; do is_running "$b" && { open -a "$b" "$URL"; return; }; done
  open "$URL"
}
open_url

# --- Chiude da sola la finestra del Terminale ---
MYTTY=$(tty)
( osascript >/dev/null 2>&1 <<OSA
tell application "Terminal"
  repeat with w in windows
    try
      if tty of selected tab of w is "$MYTTY" then close w saving no
    end try
  end repeat
end tell
OSA
) & disown
exit 0
