# openrepertoire

Open-source spaced repetition for chess openings. Works in English and Italian, your data stays on your computer. / Ripetizione spaziata open source per le aperture di scacchi. Funziona in inglese e in italiano, i dati restano sul tuo computer.

**Full guide: [English](GUIDE.md) · [Italiano](GUIDA.md)**

## Get it / Scaricala

Download the app for your system from the [releases page](https://github.com/Nonsonomiti/openrepertoire/releases), no Python needed. / Scarica l'app per il tuo sistema dalla [pagina delle release](https://github.com/Nonsonomiti/openrepertoire/releases), Python non serve.

- Windows: `OpenRepertoire-Windows.zip`
- Mac: `OpenRepertoire-macOS-AppleSilicon.zip` or/o `OpenRepertoire-macOS-Intel.zip`
- Linux: `OpenRepertoire-Linux.tar.gz`

From source / dal codice: run `MacOS_start_app.command`, `Windows_start_app.bat` or/o `start.sh` (Python 3 required; flask and python-chess install themselves).

## Building packages / Costruire i pacchetti

`pip install pyinstaller`, then `pyinstaller packaging/openrepertoire.spec` (output in `dist/`). On GitHub the `pacchetti` workflow builds and tests them on every push, and a `v*` tag attaches them to a release.

## Licence / Licenza

GPL-3.0 (see `LICENSE`, also included in the packages). The app contains Lichess's chessground and python-chess, both GPL-3.0: anyone redistributing it, even modified, must use the same licence and provide the source code. It also uses flask (BSD-3), chess.js (BSD-2), certifi (MPL-2.0), chessboard.js, jquery and qrcode-generator (MIT).

Bug reports and suggestions / segnalazioni e suggerimenti: @nonsonomiti on Instagram.
