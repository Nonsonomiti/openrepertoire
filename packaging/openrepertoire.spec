# Pacchetto con PyInstaller:   pyinstaller packaging/openrepertoire.spec --noconfirm
# macOS   -> dist/OpenRepertoire.app  (niente icona nel Dock: e' un server, l'interfaccia e' il browser;
#                                       si chiude dal menu "..." dell'app)
# Windows -> dist/OpenRepertoire.exe  (un solo file, senza finestra)
# Linux   -> dist/OpenRepertoire      (un solo file; l'icona viene ignorata)
# I dati non stanno nel pacchetto ma nella cartella dell'utente (vedi DATA_DIR in app.py).
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
with open(os.path.join(ROOT, 'app.py'), encoding='utf-8') as f:
    VERSION = re.search(r"__version__ = '([^']+)'", f.read()).group(1)

a = Analysis(
    [os.path.join(ROOT, 'app.py')],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, 'templates'), 'templates'), (os.path.join(ROOT, 'static'), 'static')],
    excludes=['tkinter', 'PIL', 'numpy'],
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OpenRepertoire', console=False,
              icon=os.path.join(SPECPATH, 'icon.icns'))
    coll = COLLECT(exe, a.binaries, a.datas, name='OpenRepertoire')
    app = BUNDLE(coll, name='OpenRepertoire.app', icon=os.path.join(SPECPATH, 'icon.icns'),
                 bundle_identifier='org.openrepertoire.app', version=VERSION,
                 info_plist={'LSUIElement': True, 'CFBundleDisplayName': 'OpenRepertoire',
                             'NSHighResolutionCapable': True})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='OpenRepertoire', console=False,
              icon=os.path.join(SPECPATH, 'icon.ico'), upx=False)
