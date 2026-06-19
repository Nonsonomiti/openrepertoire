#!/bin/bash
cd "$(dirname "$0")"
xattr -dr com.apple.quarantine . 2>/dev/null
python3 -m pip install --user --quiet flask chess 2>/dev/null \
  || python3 -m pip install --user --quiet --break-system-packages flask chess
lsof -ti tcp:5001 | xargs kill -9 2>/dev/null   # chiude eventuale istanza vecchia sulla porta
python3 app.py &
sleep 2
URL="http://127.0.0.1:5001"
CHROME=$(pgrep -f "Google Chrome.app" >/dev/null && echo 1)
SAFARI=$(pgrep -f "Safari.app" >/dev/null && echo 1)
if [ "$CHROME" ] && [ "$SAFARI" ]; then open "$URL"
elif [ "$CHROME" ]; then open -a "Google Chrome" "$URL"
elif [ "$SAFARI" ]; then open -a "Safari" "$URL"
else open "$URL"; fi
