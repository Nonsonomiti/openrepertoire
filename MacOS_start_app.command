#!/bin/bash
cd "$(dirname "$0")"
xattr -dr com.apple.quarantine . 2>/dev/null
python3 -m pip install --user --quiet flask chess 2>/dev/null \
  || python3 -m pip install --user --quiet --break-system-packages flask chess
python3 app.py &
sleep 2
open http://127.0.0.1:5001
