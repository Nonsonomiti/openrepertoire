from flask import Flask, render_template, request, jsonify, Response, redirect
import chess
import chess.pgn
import io
import json
import os
import re
import hashlib
import mimetypes
import hmac
import secrets
import socket
import ssl
import subprocess
import sys
import threading
import time
import webbrowser
import http.client
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

__version__ = '1.0.0'

# --- BLINDATURA DEI PERCORSI ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
mimetypes.add_type('application/manifest+json', '.webmanifest')   # Python 3.9 non lo conosce

# App impacchettata (.app / .exe, PyInstaller): templates e static stanno dentro il pacchetto, i dati
# nella cartella dell'utente (il pacchetto si sposta, si aggiorna, su macOS e' pure di sola lettura).
# Dal codice sorgente i dati restano accanto ad app.py, come sempre. OPENREP_DATA_DIR li sposta ovunque.
FROZEN = getattr(sys, 'frozen', False)
RES_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
if FROZEN and 'LD_LIBRARY_PATH' in os.environ:
    # Linux: PyInstaller mette le sue librerie in LD_LIBRARY_PATH; browser e xdg-open (processi figli) devono
    # usare quelle di sistema. Questo processo non cambia: il linker legge la variabile solo all'avvio.
    _lp = os.environ.pop('LD_LIBRARY_PATH_ORIG', None)
    if _lp is None:
        del os.environ['LD_LIBRARY_PATH']
    else:
        os.environ['LD_LIBRARY_PATH'] = _lp

def _user_data_dir():
    home = os.path.expanduser('~')
    if sys.platform == 'darwin':
        return os.path.join(home, 'Library', 'Application Support', 'OpenRepertoire')
    if os.name == 'nt':
        return os.path.join(os.environ.get('APPDATA') or home, 'OpenRepertoire')
    return os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.join(home, '.local', 'share'), 'openrepertoire')

DATA_DIR = os.environ.get('OPENREP_DATA_DIR') or (_user_data_dir() if FROZEN else BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__,
            template_folder=os.path.join(RES_DIR, 'templates'),
            static_folder=os.path.join(RES_DIR, 'static'),
            instance_path=DATA_DIR)   # evita os.getcwd() (avvio robusto da qualsiasi cwd)

DATA_FILE = os.path.join(DATA_DIR, "repertoire.json")
# Area "Personale" (partite, avversari, finali) in un file a parte: i corsi restano in repertoire.json
PERSONAL_FILE = os.path.join(DATA_DIR, "personal.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")   # piccolo: letto a ogni richiesta (accesso dal telefono)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024   # tetto upload PGN: 8 MB
app.config['TEMPLATES_AUTO_RELOAD'] = True   # ricarica index.html senza riavvio del server
# -------------------------------

def load_data(path=None):
    # Prova il file principale, poi il backup .bak se corrotto/mancante
    path = path or DATA_FILE
    for p in (path, path + ".bak"):
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    return json.load(f)
            except (ValueError, OSError):
                continue
    return {}

def save_data(data, path=None):
    # Scrittura atomica: tmp + fsync + rename, con backup del precedente in .bak
    path = path or DATA_FILE
    tmp = path + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(path):
        os.replace(path, path + ".bak")
    os.replace(tmp, path)

def load_personal():
    p = load_data(PERSONAL_FILE)
    for k in ('games', 'accounts', 'opponents', 'endgames'):
        p.setdefault(k, {})
    return p

def save_personal(p):
    save_data(p, PERSONAL_FILE)

def derive_chapter(title):
    # Deduce un sottocapitolo dal titolo grezzo del PGN (Chessable-style)
    t = title or ""
    t = re.sub(r'\s*#\d+\s*$', '', t)          # rimuove numerazione finale "#4"
    if ' vs ' in t:
        t = t.split(' vs ')[0]                  # "A vs B" -> "A"
    t = t.replace('-----', '-')
    t = re.sub(r'\s+', ' ', t).strip(' -')
    return t if t else 'Generale'

HEADER_KEYS = ('Event', 'Site', 'White', 'Black')

def pick_header_roles(headers_list):
    """Decide QUALE header porta il nome della variante e quale il capitolo.

    I PGN dei corsi non sono coerenti: in alcuni la linea sta in Event, in altri (export
    Chessable) Event e' il CORSO ripetuto identico, il capitolo sta in White e la linea in
    Black; certi tool (ChessBase/SCID) svuotano Event/Site a "?" e troncano i valori a ~30
    caratteri, per cui i titoli distinti crollano. Niente soglie assolute, quindi: si
    confrontano gli header FRA LORO su tre segnali misurati sul file intero.

      distinti -> il titolo cambia quasi a ogni partita, il capitolo raggruppa
      contiguita' -> le partite di un capitolo sono consecutive nel file (runs ~= distinti);
                     i nomi dei giocatori di un database di partite sono invece sparsi
      copertura -> un header buono e' valorizzato quasi ovunque ('' e '?' non contano)

    Sotto le 3 partite le statistiche non dicono nulla: si resta su Event.
    """
    n = len(headers_list)
    if n < 3:
        return 'Event', None

    stats = {}
    for k in HEADER_KEYS:
        vals = [(h.get(k) or '').strip() for h in headers_list]
        usable = [v for v in vals if v and v != '?']
        runs = sum(1 for i, v in enumerate(vals) if i == 0 or v != vals[i - 1])
        stats[k] = (len(set(usable)), runs, len(usable))

    title_key = max(HEADER_KEYS, key=lambda k: stats[k][0])
    if stats[title_key][0] < 2:
        return None, None          # tutti gli header costanti: titolo dedotto dalle mosse

    # Database di partite (White/Black = giocatori): anche l'ALTRO dei due e' quasi unico,
    # cosa che un capitolo non e' mai. Nessuno dei due e' il nome di una linea: meglio il
    # fallback "Tizio vs Caio". Il capitolo, se ripetuto, sta in blocchi contigui.
    if title_key in ('White', 'Black'):
        d_o, runs_o, _ = stats['Black' if title_key == 'White' else 'White']
        if d_o >= n * 0.9 or (d_o > n * 0.3 and runs_o > d_o * 1.2):
            title_key = None

    d_title = stats[title_key][0] if title_key else n

    def raggruppa(k):
        d, runs, cov = stats[k]
        return (k != title_key
                and 1 < d < d_title      # piu' di un gruppo, ma piu' grosso del titolo
                and d * 2 <= n           # in media >= 2 partite per capitolo: niente frammentazione
                and runs <= d * 1.5      # blocchi contigui, non valori sparsi per il file
                and cov >= n * 0.5)      # valorizzato su almeno meta' delle partite

    # Fra i candidati validi si prende il piu' fine: e' il capitolo, non la sezione che lo contiene.
    chapter_key = max((k for k in HEADER_KEYS if raggruppa(k)), key=lambda k: stats[k][0], default=None)
    return title_key, chapter_key

def default_stats():
    return {'reviews': 0, 'correct': 0, 'lapses': 0, 'last_quality': None, 'history': []}

def mai_studiata(v):
    """Vera solo se la variante non e' MAI stata ripassata. Basta srs.rep == 0 per dirlo: un lapse
       lo riazzera (SM-2), ma una variante gia' studiata non torna 'da imparare'. rep > 0 senza
       ripassi registrati = dati di prima delle statistiche: e' studiata (come la vede il client)."""
    return not ((v.get('stats') or {}).get('reviews') or (v.get('srs') or {}).get('rep'))

# Calibrazione SRS per un repertorio di aperture (non flashcard di vocaboli):
#  - LEARN_STEPS: i primi ripassi corretti sono ravvicinati, in giorni (frazionari ammessi).
#    Il primo e' a ore, non l'indomani: una linea vista una volta sola va rivista PRIMA di
#    dormirci sopra, e' li' che si consolida (Chessable fa lo stesso).
#  - MAX_INTERVAL: tetto a ~6 mesi. Senza tetto SM-2 arriva a 1 anno dopo 6 ripassi e continua a
#    crescere (2-3 anni): una linea del repertorio va rivista almeno un paio di volte l'anno,
#    anche se la ricordi bene.
#  - RELEARN_STEP: dopo un errore grave la variante NON va rimessa in scadenza "adesso", o resta
#    incollata nella lista di oggi anche dopo averla ripassata (sembra un bug). Torna fra poco,
#    come il passo di riapprendimento di Anki.
# Linea sempre corretta: 6h -> 1g -> 3g -> 7g -> 18g -> 49g -> 141g -> 180g (tetto).
LEARN_STEPS = [0.25, 1, 3, 7]
RELEARN_STEP = 10 / 1440.0        # 10 minuti
MAX_INTERVAL = 180

def update_srs(srs, quality):
    rep, interval, ease = srs.get('rep', 0), srs.get('interval', 0), srs.get('ease', 2.5)

    if quality < 3:
        rep = 0                      # lapse: azzera la sequenza (SM-2), si riparte dai passi brevi
        interval = RELEARN_STEP      # ma fra 10 minuti, non adesso: esce dalla lista di oggi
    else:
        interval = LEARN_STEPS[rep] if rep < len(LEARN_STEPS) else int(round(interval * ease))
        interval = min(interval, MAX_INTERVAL)
        rep += 1

    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    next_review = (datetime.now() + timedelta(days=interval)).isoformat()
    
    return {'rep': rep, 'interval': interval, 'ease': ease, 'next_review': next_review}

@app.route('/')
def index():
    # local: dal computer (non dal telefono) compaiono anche cartella dei dati e "chiudi l'app"
    return render_template('index.html', local=request.remote_addr in LOCAL_ADDRS, version=__version__)

@app.route('/api/import', methods=['POST'])
def import_pgn():
    req = request.get_json(silent=True) or {}
    pgn_text = req.get('pgn')
    if not isinstance(pgn_text, str) or not pgn_text.strip():
        return jsonify({"success": False, "error": "PGN mancante o non valido."}), 400
    course_name = req.get('course', 'Varie')
    perspective = req.get('perspective', 'white')
    tree = bool(req.get('tree'))   # ogni ramo del PGN = una linea (default: solo la principale)

    pgn_io = io.StringIO(pgn_text)
    data = load_data()

    # Passata sui soli header (read_headers salta il parsing delle mosse) per capire dove
    # stanno nome-variante e capitolo in QUESTO file, poi si riavvolge e si importa.
    all_headers = []
    while True:
        h = chess.pgn.read_headers(pgn_io)
        if h is None: break
        all_headers.append(h)
    title_key, chapter_key = pick_header_roles(all_headers)
    pgn_io.seek(0)

    count = 0
    imported = 0
    skipped = 0
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None: break

        count += 1
        title = (game.headers.get(title_key) or '').strip() if title_key else ''
        if not title or title == "?":
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            title = f"{white} vs {black}" if white or black else f"Linea {count}"

        # Header non-standard dei nostri export PGN: restore fedele di corso/capitolo/colore
        hdr_course = game.headers.get("Course")
        hdr_chapter = game.headers.get("Chapter")
        hdr_persp = game.headers.get("Perspective")

        # Capitolo: header nostro > header che raggruppa in questo file (es. Black nei PGN
        # Chessable) > deduzione dal titolo.
        chapter = (hdr_chapter or '').strip()
        if not chapter and chapter_key:
            chapter = (game.headers.get(chapter_key) or '').strip()
        if not chapter or chapter == '?':
            chapter = derive_chapter(title)

        # Posizione di partenza: se il PGN ha un FEN (tattica/strategia) la salva
        start_fen = None
        if game.headers.get("SetUp") == "1" or "FEN" in game.headers:
            start_fen = game.headers.get("FEN")

        # Colore: header Perspective (nostri export) > 'auto' (dal FEN) > scelta utente
        var_perspective = perspective
        if hdr_persp in ('white', 'black'):
            var_perspective = hdr_persp
        elif perspective == 'auto':
            if start_fen:
                var_perspective = 'white' if start_fen.split(' ')[1] == 'w' else 'black'
            else:
                var_perspective = 'white'

        # Linea principale (diramazioni ripiegate a testo) oppure, con tree, una linea per ramo.
        # I game con mosse illegali si saltano.
        try:
            lines = _tree_lines(game) if tree else [(_main_line(game), None)]
        except Exception:
            skipped += 1
            continue

        for moves_data, branch in lines:
            if not moves_data:
                continue
            moves_str = (start_fen or "") + "".join([m["uci"] for m in moves_data])
            moves_hash = hashlib.md5(moves_str.encode()).hexdigest()[:10]
            var_id = f"var_{moves_hash}"

            if var_id not in data:
                data[var_id] = {
                    "course": hdr_course or course_name,
                    "chapter": chapter,
                    "title": title + (" · " + branch if branch else ""),
                    "moves": moves_data,
                    "perspective": var_perspective,
                    "startFen": start_fen,
                    "stats": default_stats(),
                    "srs": {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
                }
                imported += 1

    save_data(data)
    return jsonify({"success": True, "imported": imported, "skipped": skipped})

def _main_line(game):
    """Solo la linea principale (variazioni[0]): le diramazioni diventano TESTO accodato al commento
       ("Altra opzione: ..."), come servono i corsi in cui i rami sono idee dell'autore, non linee."""
    moves_data = []
    node = game
    while node.variations:
        main_node = node.variations[0]
        combined_comment = main_node.comment if main_node.comment else ""
        if len(node.variations) > 1:
            alt_lines = []
            for alt_node in node.variations[1:]:
                exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
                alt_text = alt_node.accept(exporter).replace('\n', ' ')
                alt_lines.append(f"Altra opzione: {alt_text}")
            combined_comment = (combined_comment + "\n\n" if combined_comment else "") + "\n".join(alt_lines)
        moves_data.append({"uci": main_node.move.uci(), "san": main_node.san(), "comment": combined_comment})
        node = main_node
    return moves_data

def _tree_lines(game):
    """Import ad albero (repertori propri: ChessBase/SCID/studi con rami): ogni foglia del PGN e' una
       linea dalla radice alla foglia, coi commenti di ogni mossa. Ritorna [(mosse, etichetta)]:
       etichetta = le mosse in cui la linea lascia la principale ("8...Qb6 10.Rb1"), None per la
       principale."""
    leaves = []
    stack = [(game, [], ())]
    while stack:
        node, path, branch = stack.pop()
        if not node.variations:
            if path:
                leaves.append((path, branch))
            continue
        for i in range(len(node.variations) - 1, -1, -1):   # al contrario: la principale esce per prima
            child = node.variations[i]
            stack.append((child, path + [child], branch + (child,) if i else branch))
    lines = []
    for path, branch in leaves:
        board = game.board()
        marks = set(map(id, branch))
        moves, labels = [], []
        for n in path:
            san = board.san(n.move)
            if id(n) in marks:
                labels.append("%d%s%s" % (board.fullmove_number, '.' if board.turn else '...', san))
            # il commento prima di un ramo ("( {perche'} 8...Qb6") spiega proprio quel ramo
            comment = "\n".join(c for c in (n.starting_comment, n.comment) if c)
            moves.append({"uci": n.move.uci(), "san": san, "comment": comment})
            board.push(n.move)
        lines.append((moves, " ".join(labels) or None))
    return lines

@app.route('/api/due', methods=['GET'])
def get_due():
    data = load_data()
    now = datetime.now()

    # Migrazione lazy: aggiunge campi mancanti ai dati esistenti
    dirty = False
    for vdata in data.values():
        if 'chapter' not in vdata:
            vdata['chapter'] = derive_chapter(vdata.get('title', ''))
            dirty = True
        if 'stats' not in vdata:
            vdata['stats'] = default_stats()
            dirty = True
        srs = vdata.get('srs')
        if not isinstance(srs, dict) or 'next_review' not in srs:
            vdata['srs'] = {'rep': 0, 'interval': 0, 'ease': 2.5,
                            'next_review': datetime.now().isoformat()}
            dirty = True
    if dirty:
        save_data(data)

    # Elenco LEGGERO: senza mosse e commenti (il 95% dei byte), che arrivano da /api/variation
    # solo quando una variante si apre. learn/review sono id, non copie: prima la risposta pesava
    # ~80 MB e si riscaricava dopo ogni variante.
    learn = []
    review = []
    repertoire = []

    for vid, vdata in data.items():
        light = {k: v for k, v in vdata.items() if k != 'moves'}
        light['id'] = vid
        repertoire.append(light)

        # "Mai studiata" != "sbagliata di recente": quando sbagli troppo SM-2 azzera rep, ma la
        # variante resta imparata. Deve tornare in Ripassa (scade subito), non in Impara.
        if mai_studiata(vdata):
            learn.append(vid)
        elif datetime.fromisoformat(vdata['srs']['next_review']) <= now:
            review.append(vid)

    return jsonify({"learn": learn, "review": review, "repertoire": repertoire})

@app.route('/api/variation', methods=['GET'])
def get_variation():
    """Mosse e commenti di UNA variante (caricati quando la apri)."""
    vid = request.args.get('id')
    v = load_data().get(vid)
    if not v:
        return jsonify({"error": "Variante non trovata."}), 404
    return jsonify({"id": vid, "moves": v.get('moves') or [], "startFen": v.get('startFen')})

@app.route('/api/review', methods=['POST'])
def review():
    req = request.get_json(silent=True) or {}
    vid = req.get('id')
    quality = req.get('quality')
    if not isinstance(vid, str) or isinstance(quality, bool) or not isinstance(quality, int) or not (0 <= quality <= 5):
        return jsonify({"success": False, "error": "Dati di valutazione non validi."}), 400
    data = load_data()
    if vid not in data:
        return jsonify({"success": False, "error": "Variante non trovata (eliminata?)."}), 404

    apply_review(data[vid], quality)
    save_data(data)

    # Il client aggiorna la variante sul posto invece di riscaricare tutto l'elenco
    return jsonify({"success": True, "srs": data[vid]['srs'], "stats": data[vid]['stats']})

def apply_review(v, quality):
    """Una valutazione (0-5) su una scheda (variante o finale): cadenza SM-2 + statistiche."""
    v['srs'] = update_srs(v.get('srs') or {}, quality)
    st = v.get('stats') or default_stats()
    st['reviews'] = st.get('reviews', 0) + 1
    if quality >= 3:
        st['correct'] = st.get('correct', 0) + 1
    else:
        st['lapses'] = st.get('lapses', 0) + 1
    st['last_quality'] = quality
    hist = st.get('history') or []
    hist.append({'date': datetime.now().isoformat(), 'q': quality})
    st['history'] = hist[-20:]   # mantiene le ultime 20 valutazioni
    v['stats'] = st

@app.route('/api/review_now', methods=['POST'])
def review_now():
    """Anticipa a ORA il ripasso di tutte le varianti gia' imparate di un corso (o di un suo
       capitolo): utile per ripassare una linea prima di un torneo senza aspettare la scadenza.
       Non tocca rep/ease/interval -> la cadenza successiva resta quella dell'algoritmo."""
    req = request.get_json(silent=True) or {}
    course = req.get('course')
    chapter = req.get('chapter') or None
    # ids: varianti precise (dalle partite: le linee che hai dimenticato giocando)
    ids = set(x for x in req.get('ids') if isinstance(x, str)) if isinstance(req.get('ids'), list) else None
    if not ids and (not isinstance(course, str) or not course):
        return jsonify({"success": False, "error": "Corso mancante."}), 400

    data = load_data()
    now = datetime.now()
    count = 0
    for vid, v in data.items():
        if ids:
            if vid not in ids:
                continue
        elif (v.get('course') or 'Varie') != course:
            continue
        if chapter and (v.get('chapter') or 'Generale') != chapter:
            continue
        srs = v.get('srs') or {}
        if mai_studiata(v):
            continue                      # mai imparata: sta gia' in "Impara"
        try:
            if datetime.fromisoformat(srs['next_review']) <= now:
                continue                  # gia' scaduta
        except (KeyError, ValueError):
            pass
        srs['next_review'] = now.isoformat()
        count += 1

    if count:
        save_data(data)
    return jsonify({"success": True, "count": count})

@app.route('/api/delete', methods=['POST'])
def delete_variation():
    req = request.get_json(silent=True) or {}
    data = load_data()
    vid = req.get('id')
    
    if vid in data:
        del data[vid]
        save_data(data)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Variante non trovata"})

@app.route('/api/delete_course', methods=['POST'])
def delete_course():
    req = request.get_json(silent=True) or {}
    data = load_data()
    course = req.get('course')

    to_del = [vid for vid, vdata in data.items() if (vdata.get('course') or 'Varie') == course]
    for vid in to_del:
        del data[vid]

    save_data(data)
    return jsonify({"success": True, "deleted": len(to_del)})

@app.route('/api/stats', methods=['GET'])
def stats():
    data = load_data()
    now = datetime.now()
    today = now.date()

    total = len(data)
    learn = 0
    due_today = 0
    reviews_total = 0
    correct_total = 0
    lapses_total = 0
    upcoming = {}      # 'YYYY-MM-DD' -> conteggio (prossimi 30 gg)
    hardest = []

    for v in data.values():
        srs = v.get('srs', {})
        st = v.get('stats') or {}
        reviews_total += st.get('reviews', 0)
        correct_total += st.get('correct', 0)
        lapses_total += st.get('lapses', 0)
        if st.get('lapses', 0) > 0:
            hardest.append({
                'title': v.get('title', ''),
                'course': v.get('course', ''),
                'lapses': st.get('lapses', 0),
                'reviews': st.get('reviews', 0)
            })

        if mai_studiata(v):
            learn += 1
            continue
        try:
            nr = datetime.fromisoformat(srs['next_review'])
        except Exception:
            continue
        if nr <= now:
            due_today += 1
        else:
            delta = (nr.date() - today).days
            if 0 <= delta <= 30:
                key = nr.date().isoformat()
                upcoming[key] = upcoming.get(key, 0) + 1

    hardest.sort(key=lambda x: x['lapses'], reverse=True)
    accuracy = round(100 * correct_total / reviews_total) if reviews_total else 0

    # A2: breakdown per corso, per colore, e tasso di richiamo (retention) ultimi 14 gg
    by_course = {}
    by_color = {}
    RET_DAYS = 14
    ret_buckets = {}   # 'YYYY-MM-DD' -> [reviews, recalled(q>=3)]
    study_days = set()   # giorni con almeno un ripasso (corsi + finali): da qui la serie

    for v in data.values():
        course = v.get('course') or 'Varie'
        color = v.get('perspective') or 'white'
        st = v.get('stats') or {}
        srs = v.get('srs', {})
        r, c, l = st.get('reviews', 0), st.get('correct', 0), st.get('lapses', 0)

        bc = by_course.setdefault(course, {'course': course, 'total': 0, 'reviews': 0,
                                           'correct': 0, 'lapses': 0, 'learn': 0, 'due': 0})
        bc['total'] += 1; bc['reviews'] += r; bc['correct'] += c; bc['lapses'] += l
        bk = by_color.setdefault(color, {'color': color, 'total': 0, 'reviews': 0,
                                         'correct': 0, 'lapses': 0})
        bk['total'] += 1; bk['reviews'] += r; bk['correct'] += c; bk['lapses'] += l

        if mai_studiata(v):
            bc['learn'] += 1
        else:
            try:
                if datetime.fromisoformat(srs['next_review']) <= now:
                    bc['due'] += 1
            except Exception:
                pass

        for h in st.get('history', []):
            try:
                hd = datetime.fromisoformat(h['date']).date()
            except Exception:
                continue
            study_days.add(hd)
            if 0 <= (today - hd).days < RET_DAYS:
                b = ret_buckets.setdefault(hd.isoformat(), [0, 0])
                b[0] += 1
                if h.get('q', 0) >= 3:
                    b[1] += 1

    for bc in by_course.values():
        bc['accuracy'] = round(100 * bc['correct'] / bc['reviews']) if bc['reviews'] else 0
    for bk in by_color.values():
        bk['accuracy'] = round(100 * bk['correct'] / bk['reviews']) if bk['reviews'] else 0

    retention_series = []
    ret_rv = ret_rc = 0
    for i in range(RET_DAYS - 1, -1, -1):
        d = today - timedelta(days=i)
        rv, rc = ret_buckets.get(d.isoformat(), [0, 0])
        ret_rv += rv; ret_rc += rc
        retention_series.append({'date': d.isoformat(), 'reviews': rv, 'recalled': rc,
                                 'rate': round(100 * rc / rv) if rv else None})
    retention_overall = round(100 * ret_rc / ret_rv) if ret_rv else 0

    by_course_list = sorted(by_course.values(), key=lambda x: x['total'], reverse=True)
    by_color_list = [by_color[k] for k in ('white', 'black') if k in by_color]

    for e in load_personal()['endgames'].values():
        for h in (e.get('stats') or {}).get('history', []):
            try:
                study_days.add(datetime.fromisoformat(h['date']).date())
            except Exception:
                pass
    # Serie: giorni consecutivi di studio fino a oggi. Se oggi non hai ancora studiato conta da ieri
    # (la serie e' ancora viva fino a stasera).
    streak, d = 0, (today if today in study_days else today - timedelta(days=1))
    while d in study_days:
        streak += 1
        d -= timedelta(days=1)

    return jsonify({
        'total': total, 'learn': learn, 'due_today': due_today,
        'reviews_total': reviews_total, 'accuracy': accuracy, 'lapses_total': lapses_total,
        'upcoming': upcoming, 'hardest': hardest[:10],
        'by_course': by_course_list, 'by_color': by_color_list,
        'retention': {'overall': retention_overall, 'series': retention_series},
        'streak': streak, 'studied_today': today in study_days
    })

@app.route('/api/set_chapter', methods=['POST'])
def set_chapter():
    req = request.get_json(silent=True) or {}
    data = load_data()
    vid = req.get('id')
    chapter = (req.get('chapter') or '').strip() or 'Generale'
    if vid in data:
        data[vid]['chapter'] = chapter
        save_data(data)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/rename_chapter', methods=['POST'])
def rename_chapter():
    req = request.get_json(silent=True) or {}
    data = load_data()
    course = req.get('course')
    old = req.get('old')
    new = (req.get('new') or '').strip()
    if not new:
        return jsonify({"success": False, "error": "Nome non valido"})
    n = 0
    for v in data.values():
        if (v.get('course') or 'Varie') == course and (v.get('chapter') or 'Generale') == old:
            v['chapter'] = new
            n += 1
    save_data(data)
    return jsonify({"success": True, "updated": n})

@app.route('/api/set_course', methods=['POST'])
def set_course():
    req = request.get_json(silent=True) or {}
    data = load_data()
    vid = req.get('id')
    course = (req.get('course') or '').strip() or 'Varie'
    if vid in data:
        data[vid]['course'] = course
        save_data(data)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/rename_course', methods=['POST'])
def rename_course():
    req = request.get_json(silent=True) or {}
    data = load_data()
    old = req.get('old')
    new = (req.get('new') or '').strip()
    if not new:
        return jsonify({"success": False, "error": "Nome non valido"})
    n = 0
    for v in data.values():
        if (v.get('course') or 'Varie') == old:
            v['course'] = new
            n += 1
    save_data(data)
    return jsonify({"success": True, "updated": n})

@app.route('/api/merge_chapter', methods=['POST'])
def merge_chapter():
    req = request.get_json(silent=True) or {}
    data = load_data()
    course = req.get('course')
    src = req.get('from')
    dst = (req.get('to') or '').strip()
    if not dst:
        return jsonify({"success": False, "error": "Capitolo di destinazione non valido"})
    if src == dst:
        return jsonify({"success": False, "error": "Capitoli identici"})
    n = 0
    for v in data.values():
        if (v.get('course') or 'Varie') == course and (v.get('chapter') or 'Generale') == src:
            v['chapter'] = dst
            n += 1
    save_data(data)
    return jsonify({"success": True, "updated": n})

@app.route('/api/search_position', methods=['POST'])
def search_position():
    req = request.get_json(silent=True) or {}
    fen = (req.get('fen') or '').strip()
    course = req.get('course')
    if not fen:
        return jsonify({"matches": []})
    target = fen.split(' ')[0]   # solo disposizione pezzi

    data = load_data()
    matches = []
    for vid, v in data.items():
        if course and (v.get('course') or 'Varie') != course:
            continue
        try:
            board = chess.Board(v['startFen']) if v.get('startFen') else chess.Board()
        except Exception:
            board = chess.Board()

        found_idx = None
        if board.fen().split(' ')[0] == target:
            found_idx = 0
        else:
            for i, m in enumerate(v.get('moves', [])):
                try:
                    board.push_uci(m['uci'])
                except Exception:
                    break
                if board.fen().split(' ')[0] == target:
                    found_idx = i + 1
                    break

        if found_idx is not None:
            matches.append({
                'id': vid,
                'title': v.get('title', ''),
                'course': v.get('course', ''),
                'chapter': v.get('chapter', ''),
                'moveIndex': found_idx
            })

    return jsonify({"matches": matches})

# ===== B1/B2: indice ad albero delle posizioni (trie) + trasposizioni, con cache su mtime e filtro =====
_index_cache = {'mtime': None, 'sig': None, 'by_filter': {}}

def _pos_key(board):
    # Chiave di trasposizione = le prime 4 parti del FEN (pezzi, tratto, arrocchi, en passant legale)
    # ma senza costruire la stringa: board.fen() a ogni mossa era il 70% del tempo dell'albero.
    return (board.pawns, board.knights, board.bishops, board.rooks, board.queens, board.kings,
            board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK], board.turn,
            board.clean_castling_rights(), board.ep_square if board.has_legal_en_passant() else None)

def _data_sig(data):
    # Cio' che conta per l'albero: quali varianti (l'id e' l'hash delle mosse), con che corso,
    # colore, titolo. Un ripasso cambia solo srs/statistiche e l'albero resta valido.
    return hash(tuple((vid, v.get('course'), v.get('perspective'), v.get('title'), v.get('startFen'))
                      for vid, v in data.items()))

def _board_for(v):
    try:
        return chess.Board(v['startFen']) if v.get('startFen') else chess.Board()
    except Exception:
        return chess.Board()

def _build_index(course=None, perspective=None):
    """children[key][uci] = {uci,san,count,comment,sample_var_id}; reach[key] = {by_var:{vid:ply},
       paths:set, owner_moves:set, fen, turn}; ends[key] = [vid]. Filtrabile per corso/colore;
       cache per (mtime, corso, colore) — un albero separato per ogni combinazione."""
    try:
        mtime = os.path.getmtime(DATA_FILE)
    except OSError:
        mtime = None
    if _index_cache['mtime'] != mtime:
        _index_cache['mtime'] = mtime
        sig = _data_sig(load_data())
        if sig != _index_cache['sig']:
            _index_cache['sig'] = sig
            _index_cache['by_filter'] = {}
    fkey = (course or '', perspective or '')
    if fkey in _index_cache['by_filter']:
        return _index_cache['by_filter'][fkey]

    data = load_data()
    children, reach, ends = {}, {}, {}
    for vid, v in data.items():
        if course and (v.get('course') or 'Varie') != course:
            continue
        if perspective and (v.get('perspective') or 'white') != perspective:
            continue
        board = _board_for(v)
        persp_white = (v.get('perspective', 'white') == 'white')
        path = []
        for m in v.get('moves', []):
            uci = m.get('uci')
            if not uci:
                break
            k = _pos_key(board)
            try:
                mv = chess.Move.from_uci(uci)
            except ValueError:
                break
            if mv and board.piece_at(mv.from_square) is None:   # (mv falso = mossa nulla "--", valida)
                break                    # dati incoerenti: la linea si ferma qui
            san = m.get('san') or board.san(mv)   # la SAN salvata all'import: ricalcolarla costava
            node = children.setdefault(k, {})
            ch = node.get(uci)
            if ch is None:
                ch = {'uci': uci, 'san': san, 'count': 0, 'comment': '', 'sample_var_id': vid}
                node[uci] = ch
            ch['count'] += 1
            if not ch['comment'] and m.get('comment'):
                ch['comment'] = m['comment']
            r = reach.get(k)
            if r is None:
                r = {'by_var': {}, 'paths': set(), 'owner_moves': set(),
                     'turn': ('w' if board.turn else 'b')}
                reach[k] = r
            if vid not in r['by_var']:
                r['by_var'][vid] = len(path)
            r['paths'].add(tuple(path))
            if board.turn == persp_white:   # mossa del LATO dell'utente da questa posizione
                r['owner_moves'].add(uci)
            board.push(mv)           # mosse gia' validate all'import/salvataggio
            path.append(uci)
        ends.setdefault(_pos_key(board), []).append(vid)

    result = {'children': children, 'reach': reach, 'ends': ends, 'data': data}
    _index_cache['by_filter'][fkey] = result
    return result

@app.route('/api/tree', methods=['POST'])
def api_tree():
    req = request.get_json(silent=True) or {}
    path = req.get('path') if isinstance(req.get('path'), list) else []
    course = req.get('course') or None
    perspective = req.get('perspective') if req.get('perspective') in ('white', 'black') else None
    idx = _build_index(course, perspective)

    board = chess.Board()
    applied = []
    for uci in path:
        try:
            board.push_uci(uci)
            applied.append(uci)
        except Exception:
            break
    key = _pos_key(board)

    kids = sorted(idx['children'].get(key, {}).values(), key=lambda c: -c['count'])
    total = sum(c['count'] for c in kids) or 1
    children = [{'uci': c['uci'], 'san': c['san'], 'count': c['count'],
                 'pct': round(100 * c['count'] / total),
                 'comment': c['comment'], 'sample_var_id': c['sample_var_id']} for c in kids]

    data = idx['data']
    ends = idx['ends'].get(key, [])
    ends_info = [{'id': vid, 'title': data.get(vid, {}).get('title', ''),
                  'course': data.get(vid, {}).get('course', '')} for vid in ends[:30]]
    r = idx['reach'].get(key, {})
    owner = ('w' if perspective == 'white' else 'b') if perspective else None
    turn = 'w' if board.turn else 'b'
    is_hole = bool(owner and turn == owner and not children and ends)
    return jsonify({
        'fen': board.fen(), 'turn': turn,
        'ply': len(applied), 'path': applied, 'children': children,
        'ends': ends_info, 'ends_count': len(ends), 'is_hole': is_hole,
        'reached_by': len(r.get('by_var', {})), 'transposition': len(r.get('paths', ())) >= 2
    })

@app.route('/api/transpositions', methods=['GET'])
def api_transpositions():
    course = request.args.get('course') or None
    perspective = request.args.get('perspective')
    if perspective not in ('white', 'black'):
        perspective = None
    idx = _build_index(course, perspective)
    data = idx['data']
    items = []
    for key, r in idx['reach'].items():
        if len(r['paths']) < 2:
            continue
        by_var = r['by_var']
        reached_by = [{'id': vid, 'title': data.get(vid, {}).get('title', ''), 'ply': ply,
                       'course': data.get(vid, {}).get('course', '')}
                      for vid, ply in list(by_var.items())[:12]]
        sans = [c['san'] for c in idx['children'].get(key, {}).values()]
        items.append({'turn': r['turn'],
                      'reached_by': reached_by, 'reached_count': len(by_var),
                      'conflict': len(r['owner_moves']) >= 2, 'continuations': sans})
    items.sort(key=lambda x: (-int(x['conflict']), -x['reached_count']))
    return jsonify({'transpositions': items[:80], 'total': len(items)})

# ===== Opening explorer di Lichess (proxy) =====
# Gli endpoint explorer.lichess.org non sono piu' anonimi (401 nginx): vogliono un token OAuth
# personale, gratuito e senza scope. Il token vive sul server, mai nel browser e mai in git:
#   1) variabile d'ambiente LICHESS_TOKEN, oppure
#   2) lichess_token.txt accanto ad app.py, scritto dall'app quando lo incolli nel pannello.
# Chi clona la repo trova tutto cablato: incolla il token una volta e la feature va.
TOKEN_FILE = os.path.join(DATA_DIR, "lichess_token.txt")
EXPLORER_HOST = "https://explorer.lichess.org/"
# Le stesse posizioni si rivisitano in continuazione (avanti/indietro sull'albero): senza cache
# si martella l'API per niente. Chiave = URL completo, quindi i filtri fanno parte della chiave.
_explorer_cache = {}
EXPLORER_PARAMS = ('fen', 'play', 'speeds', 'ratings', 'since', 'until', 'moves')

def lichess_token():
    tok = (os.environ.get('LICHESS_TOKEN') or '').strip()
    if not tok and os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                tok = f.read().strip()
        except OSError:
            pass
    return tok

def _ssl_context():
    """I Python presi da python.org (macOS in testa) arrivano SENZA certificati installati:
       urllib fallisce la verifica anche dove il browser va liscio, ed e' la causa numero uno
       di "non raggiungibile" su una macchina nuova. certifi porta il suo bundle; se manca si
       usa quello di sistema."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

_SSL_CTX = _ssl_context()
USER_AGENT = 'openrepertoire (+https://github.com/Nonsonomiti/openrepertoire)'   # Chess.com lo chiede

class _IPv4HTTPS(urllib.request.HTTPSHandler):
    """Connessione solo IPv4: legando il socket a 0.0.0.0 gli indirizzi IPv6 falliscono subito e si passa
       ai v4."""
    def https_open(self, req):
        return self.do_open(lambda host, **kw: http.client.HTTPSConnection(host, source_address=('0.0.0.0', 0), **kw),
                            req, context=self._context)

def http_get(url, headers=None, timeout=20):
    """GET verso i siti esterni, prima in IPv4. Su reti con l'IPv6 rotto (hotspot del telefono, certi
       router) Python, che non ha il "happy eyeballs" di browser e curl, resterebbe appeso minuti sui
       tentativi IPv6; e Lichess limita certi indirizzi IPv6 ("una richiesta alla volta"). Senza IPv4
       (reti solo IPv6) si riprova normale."""
    req = urllib.request.Request(url, headers=dict({'User-Agent': USER_AGENT}, **(headers or {})))
    try:
        return urllib.request.build_opener(_IPv4HTTPS(context=_SSL_CTX)).open(req, timeout=timeout)
    except urllib.error.HTTPError:
        raise                                  # il server ha risposto: l'errore e' suo, non della rete
    except (urllib.error.URLError, OSError):
        return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)

def _net_error(e):
    """Errore di rete -> codice per il client (che lo traduce). Va riportato TESTUALE: "non
       raggiungibile" e basta non si debugga."""
    if isinstance(e, urllib.error.HTTPError):
        return {401: 'bad_token', 403: 'bad_token', 404: 'not_found', 429: 'rate_limit'}.get(e.code, 'http_%d' % e.code)
    if isinstance(e, urllib.error.URLError):
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            return 'ssl_cert'
        return 'rete: %s' % str(e.reason)[:120]
    return '%s: %s' % (type(e).__name__, str(e)[:120])

def explorer_get(db, params, token):
    """Chiama l'explorer. Ritorna (json, None) oppure (None, codice_errore)."""
    url = EXPLORER_HOST + db + '?' + urllib.parse.urlencode(params)
    if url in _explorer_cache:
        return _explorer_cache[url], None
    try:
        with http_get(url, {'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}, timeout=10) as r:
            body = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return None, _net_error(e)
    if len(_explorer_cache) > 400:
        _explorer_cache.clear()
    _explorer_cache[url] = body
    return body, None

@app.route('/api/explorer', methods=['GET'])
def api_explorer():
    db = request.args.get('db')
    if db not in ('masters', 'lichess'):
        return jsonify({'error': 'db_invalido'}), 400
    fen = request.args.get('fen', '')
    try:
        chess.Board(fen)
    except ValueError:
        return jsonify({'error': 'fen_invalido'}), 400
    token = lichess_token()
    if not token:
        return jsonify({'error': 'no_token'})
    params = {k: request.args[k] for k in EXPLORER_PARAMS if request.args.get(k)}
    # Maestri: anche le partite modello (le migliori che passano di qui), da aprire su Lichess
    params.update({'fen': fen, 'topGames': 4 if db == 'masters' else 0, 'recentGames': 0, 'moves': params.get('moves', 12)})
    if db == 'masters':
        params.pop('speeds', None); params.pop('ratings', None)   # filtri validi solo per il db online
    body, err = explorer_get(db, params, token)
    if err:
        return jsonify({'error': err})
    tot = (body.get('white', 0) + body.get('draws', 0) + body.get('black', 0))
    return jsonify({
        'total': tot,
        'opening': (body.get('opening') or {}).get('name'),
        'games': [{'id': g.get('id'), 'uci': g.get('uci'), 'year': g.get('year'), 'winner': g.get('winner'),
                   'white': (g.get('white') or {}).get('name'), 'wr': (g.get('white') or {}).get('rating'),
                   'black': (g.get('black') or {}).get('name'), 'br': (g.get('black') or {}).get('rating')}
                  for g in (body.get('topGames') or [])],
        'moves': [{'uci': m.get('uci'), 'san': m.get('san'),
                   'games': m.get('white', 0) + m.get('draws', 0) + m.get('black', 0),
                   'white': m.get('white', 0), 'draws': m.get('draws', 0), 'black': m.get('black', 0),
                   'rating': m.get('averageRating')} for m in body.get('moves', [])]
    })

@app.route('/api/lichess_token', methods=['GET', 'POST'])
def api_lichess_token():
    """GET: c'e' un token? POST {token}: salvalo (stringa vuota = rimuovilo) e provalo subito.
       Il token non viene mai rimandato al client."""
    if request.method == 'GET':
        return jsonify({'present': bool(lichess_token()), 'from_env': bool(os.environ.get('LICHESS_TOKEN'))})
    token = ((request.get_json(silent=True) or {}).get('token') or '').strip().strip('"\'')
    if not token:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return jsonify({'success': True, 'present': False})
    # Un token incollato male (a capo, spazi, virgolette smart) romperebbe l'header HTTP con
    # un errore incomprensibile: meglio dirlo subito.
    if not re.fullmatch(r'[A-Za-z0-9_\-\.]+', token):
        return jsonify({'success': False, 'error': 'token_formato'})
    _, err = explorer_get('masters', {'fen': chess.STARTING_FEN, 'moves': 1, 'topGames': 0}, token)
    if err:
        return jsonify({'success': False, 'error': err})
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # leggibile solo dall'utente
    with os.fdopen(fd, 'w') as f:
        f.write(token + '\n')
    return jsonify({'success': True, 'present': True})

# ===== B5: validazione FEN per il board-editor (posizione di partenza) =====
@app.route('/api/validate_fen', methods=['POST'])
def validate_fen():
    req = request.get_json(silent=True) or {}
    fen = (req.get('fen') or '').strip()
    if not fen:
        return jsonify({"valid": False, "error": "FEN vuoto."})
    try:
        board = chess.Board(fen)
    except Exception:
        return jsonify({"valid": False, "error": "FEN malformato."})
    if not board.is_valid():
        status = board.status()
        reasons = []
        if status & chess.STATUS_NO_WHITE_KING or status & chess.STATUS_NO_BLACK_KING:
            reasons.append("manca un re")
        if status & chess.STATUS_TOO_MANY_KINGS:
            reasons.append("troppi re")
        if status & chess.STATUS_PAWNS_ON_BACKRANK:
            reasons.append("pedoni in prima/ottava traversa")
        if status & chess.STATUS_OPPOSITE_CHECK or status & chess.STATUS_TOO_MANY_CHECKERS:
            reasons.append("posizione di scacco impossibile")
        if status & chess.STATUS_BAD_CASTLING_RIGHTS:
            reasons.append("diritti di arrocco incoerenti coi pezzi")
        msg = "Posizione illegale" + (": " + ", ".join(reasons) if reasons else ".")
        return jsonify({"valid": False, "error": msg})
    # normalizza azzerando i contatori (la variante riparte da qui)
    board.halfmove_clock = 0
    return jsonify({"valid": True, "fen": board.fen()})

# ===== B4: creazione/modifica variante dall'editor (unico endpoint di scrittura mosse) =====
@app.route('/api/save_variation', methods=['POST'])
def save_variation():
    req = request.get_json(silent=True) or {}
    title = (req.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Titolo mancante."}), 400
    moves_in = req.get('moves')
    if not isinstance(moves_in, list) or not moves_in:
        return jsonify({"success": False, "error": "Nessuna mossa."}), 400

    course = (req.get('course') or 'Varie').strip() or 'Varie'
    chapter = (req.get('chapter') or '').strip() or derive_chapter(title)
    perspective = req.get('perspective', 'white')
    if perspective not in ('white', 'black'):
        perspective = 'white'
    start_fen = req.get('startFen') or None

    # Ricostruisce e VALIDA ogni mossa lato server (verità python-chess); ricalcola i SAN
    try:
        board = chess.Board(start_fen) if start_fen else chess.Board()
    except Exception:
        return jsonify({"success": False, "error": "FEN di partenza non valido."}), 400
    if start_fen and not board.is_valid():
        return jsonify({"success": False, "error": "Posizione di partenza illegale."}), 400

    moves_data = []
    for i, m in enumerate(moves_in):
        uci = (m.get('uci') if isinstance(m, dict) else m) or ''
        try:
            mv = chess.Move.from_uci(uci)
        except Exception:
            return jsonify({"success": False, "error": "Mossa %d non valida (%s)." % (i + 1, uci)}), 400
        if mv and mv not in board.legal_moves:   # mv falso = mossa nulla "--" dei corsi: ammessa
            return jsonify({"success": False, "error": "Mossa %d illegale (%s)." % (i + 1, uci)}), 400
        comment = (m.get('comment') if isinstance(m, dict) else '') or ''
        moves_data.append({"uci": uci, "san": board.san(mv), "comment": comment})
        board.push(mv)

    data = load_data()
    moves_str = (start_fen or "") + "".join(m["uci"] for m in moves_data)
    new_id = "var_" + hashlib.md5(moves_str.encode()).hexdigest()[:10]
    old_id = req.get('id')
    extended = None
    # extend (dal costruttore): la linea che allunga una linea dello STESSO corso la sostituisce
    # (stessa scheda: srs e statistiche passano) invece di lasciare la vecchia come doppione troncato.
    # Mai su un altro corso: i corsi importati non si toccano.
    if not old_id and req.get('extend'):
        for vid, v in data.items():
            ms = v.get('moves') or []
            if ((v.get('course') or 'Varie') == course and (v.get('perspective') or 'white') == perspective
                    and (v.get('startFen') or None) == start_fen and 0 < len(ms) < len(moves_data)
                    and all(ms[i].get('uci') == moves_data[i]['uci'] for i in range(len(ms)))
                    and (extended is None or len(ms) > len(data[extended]['moves']))):
                extended = vid
        if extended:
            old_id = extended
            for i, m in enumerate(data[extended]['moves']):   # i commenti della linea vecchia restano
                if m.get('comment') and not moves_data[i]['comment']:
                    moves_data[i]['comment'] = m['comment']
    editing = bool(old_id) and old_id in data

    # Re-keying: l'identità (var_id) dipende da startFen+mosse. Collisione con ALTRA variante -> rifiuta.
    if new_id in data and new_id != old_id:
        return jsonify({"success": False, "error": "Esiste già una variante con questa identica sequenza di mosse.",
                        "existingId": new_id}), 409

    if editing:
        old = data[old_id]
        srs = old.get('srs') or {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
        stats = old.get('stats') or default_stats()
        if new_id != old_id:
            del data[old_id]   # le mosse sono cambiate -> nuova chiave, trasferisco srs/stats
    else:
        srs = {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
        stats = default_stats()

    data[new_id] = {
        "course": course, "chapter": chapter, "title": title,
        "moves": moves_data, "perspective": perspective, "startFen": start_fen,
        "stats": stats, "srs": srs
    }
    save_data(data)
    return jsonify({"success": True, "id": new_id, "rekeyed": bool(editing and new_id != old_id and not extended),
                    "extended": extended})

# ===== Export PGN (backup / condivisione): ricostruisce il PGN da moves+comment =====
@app.route('/api/export', methods=['GET'])
def export_pgn():
    """Esporta repertorio / corso / capitolo / varianti scelte come PGN scaricabile.
       Filtri: course, chapter (ripetibile: piu' capitoli), ids (id separati da virgola).
       strip=1 -> rimuove commenti e header non-standard (PGN pulito, solo mosse,
       per studi Lichess/analisi personali). Senza strip include Course/Chapter/
       Perspective per un re-import fedele (i lettori standard li ignorano).
       merge=1 -> fonde le varianti di uno stesso (corso, capitolo, posizione di
       partenza) in UN SOLO game ad albero (prefissi condivisi, rami sulle mosse
       diverse): Lichess importa 1 capitolo ramificato invece di N quasi-uguali.
       onechapter=1 (implica merge) -> ignora anche il capitolo nel raggruppamento:
       tutto il corso finisce in UN unico albero/capitolo."""
    course = request.args.get('course') or None
    chapters = set(x for x in request.args.getlist('chapter') if x)   # ripetibile: piu' capitoli
    ids = set(x for x in (request.args.get('ids') or '').split(',') if x)
    strip = request.args.get('strip') in ('1', 'true', 'yes')
    one_chapter = request.args.get('onechapter') in ('1', 'true', 'yes')
    merge = one_chapter or request.args.get('merge') in ('1', 'true', 'yes')
    data = load_data()

    # 1) filtra le varianti richieste (con mosse)
    selected = []
    for vid, v in data.items():
        if ids and vid not in ids:
            continue
        if course and (v.get('course') or 'Varie') != course:
            continue
        if chapters and (v.get('chapter') or 'Generale') not in chapters:
            continue
        if not (v.get('moves') or []):
            continue
        selected.append(v)

    def _start_board(fen):
        try:
            return chess.Board(fen) if fen else chess.Board()
        except Exception:
            return None

    games = []
    if merge:
        # Raggruppa per (corso, capitolo, startFen): un albero PGN ha UNA sola
        # posizione iniziale, quindi start diversi restano game separati.
        # Con one_chapter il capitolo esce dalla chiave: un solo albero per corso.
        groups = {}
        for v in selected:
            key = ((v.get('course') or 'Varie'),
                   (v.get('course') or 'Varie') if one_chapter else (v.get('chapter') or 'Generale'),
                   v.get('startFen') or '')
            groups.setdefault(key, []).append(v)
        for (gcourse, gchap, gfen), vs in groups.items():
            start_fen = gfen or None
            root = _start_board(start_fen)
            if root is None:
                start_fen, root = None, chess.Board()
            game = chess.pgn.Game()
            game.headers['Event'] = gchap        # il capitolo nomina il capitolo-studio Lichess
            game.headers['Site'] = 'openrepertoire'
            game.headers['White'] = gcourse
            game.headers['Black'] = gchap
            game.headers['Result'] = '*'
            if not strip:
                game.headers['Course'] = gcourse
                game.headers['Chapter'] = gchap
                game.headers['Perspective'] = vs[0].get('perspective') or 'white'
            if start_fen:
                game.setup(root)
            # linea piu lunga come principale (backbone), poi le altre si diramano
            for v in sorted(vs, key=lambda x: -len(x.get('moves') or [])):
                node = game
                board = chess.Board(start_fen) if start_fen else chess.Board()
                for m in (v.get('moves') or []):
                    try:
                        mv = chess.Move.from_uci(m.get('uci', ''))
                    except Exception:
                        break
                    if mv and mv not in board.legal_moves:   # le mosse nulle "--" passano
                        break
                    node = node.variation(mv) if node.has_variation(mv) else node.add_variation(mv)
                    if not strip and m.get('comment') and not node.comment:
                        node.comment = m['comment']   # 1o commento non vuoto sulla mossa condivisa
                    board.push(mv)
            games.append(str(game))
    else:
        for v in selected:
            game = chess.pgn.Game()
            game.headers['Event'] = v.get('title') or 'Linea'
            game.headers['Site'] = 'openrepertoire'
            game.headers['White'] = v.get('course') or 'Varie'
            game.headers['Black'] = v.get('chapter') or 'Generale'
            game.headers['Result'] = '*'
            if not strip:
                game.headers['Course'] = v.get('course') or 'Varie'
                game.headers['Chapter'] = v.get('chapter') or 'Generale'
                game.headers['Perspective'] = v.get('perspective') or 'white'
            start_fen = v.get('startFen')
            board = _start_board(start_fen) or chess.Board()
            if start_fen:
                game.setup(board)
            node, ok = game, True
            for m in (v.get('moves') or []):
                try:
                    mv = chess.Move.from_uci(m.get('uci', ''))
                    if mv and mv not in board.legal_moves:   # le mosse nulle "--" passano (prima la variante spariva dall'export)
                        ok = False; break
                    node = node.add_variation(mv)
                    board.push(mv)
                    if not strip and m.get('comment'):
                        node.comment = m['comment']
                except Exception:
                    ok = False; break
            if ok:
                games.append(str(game))

    pgn_text = "\n\n".join(games) + ("\n" if games else "")
    if chapters:
        scope = (course or 'corso') + '_' + (sorted(chapters)[0] if len(chapters) == 1 else '%dcapitoli' % len(chapters))
    else:
        scope = course or ('selezione' if ids else 'tutto')
    if merge:
        scope += '_albero'
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', scope)[:60]
    fname = "openrepertoire_%s_%s.pgn" % (safe, datetime.now().strftime('%Y%m%d'))
    return Response(pgn_text, mimetype='application/x-chess-pgn',
                    headers={'Content-Disposition': 'attachment; filename="%s"' % fname,
                             'X-Export-Count': str(len(games))})

# =====================================================================================
# ===== AREA PERSONALE: le tue partite, l'avversario, i finali (dati in personal.json) =====
# I corsi non si toccano: qui il repertorio si LEGGE (indice _build_index) per confrontarlo con le
# partite giocate davvero. Nelle varianti non finisce nessun testo.

GAME_PLIES = 60          # dell'apertura basta l'inizio: personal.json resta piccolo
MAX_OPPONENTS = 8        # avversari preparati che restano salvati (i piu' recenti)
USER_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_\-]{1,29}')
CC_DRAWS = {'agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient'}

def new_srs():
    return {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}

def _lichess_record(g, user):
    """Partita dell'export Lichess (NDJSON) -> record compatto dal punto di vista di `user`."""
    if g.get('variant') != 'standard' or g.get('initialFen') or g.get('status') in ('created', 'started', 'aborted', 'noStart'):
        return None
    players, me, color = g.get('players') or {}, user.lower(), None
    for c in ('white', 'black'):
        u = (players.get(c) or {}).get('user') or {}
        if (u.get('id') or (u.get('name') or '').lower()) == me:
            color = c
    if not color:
        return None
    opp = players.get('black' if color == 'white' else 'white') or {}
    sans, ucis, board = [], [], chess.Board()
    for s in (g.get('moves') or '').split()[:GAME_PLIES]:
        try:
            mv = board.parse_san(s)
        except ValueError:
            break
        sans.append(s); ucis.append(mv.uci()); board.push(mv)
    if not ucis:
        return None
    winner = g.get('winner')
    return {'site': 'lichess', 'id': g.get('id'), 'url': 'https://lichess.org/%s%s' % (g.get('id'), '/black' if color == 'black' else ''),
            'user': me, 'color': color,
            'opp': (opp.get('user') or {}).get('name') or ('Stockfish %s' % opp['aiLevel'] if opp.get('aiLevel') else '?'),
            'rating': (players.get(color) or {}).get('rating'), 'opp_rating': opp.get('rating'),
            'result': 'draw' if not winner else ('win' if winner == color else 'loss'),
            'speed': g.get('speed') or '', 'ts': g.get('createdAt') or 0,
            'opening': (g.get('opening') or {}).get('name') or '',
            'uci': ' '.join(ucis), 'san': ' '.join(sans)}

def _chesscom_record(g, user):
    """Partita dell'archivio mensile Chess.com -> stesso record di _lichess_record."""
    if g.get('rules') != 'chess':
        return None
    setup = g.get('initial_setup') or ''
    if setup and setup.split(' ')[0] != chess.STARTING_BOARD_FEN:
        return None
    me = user.lower()
    w, b = g.get('white') or {}, g.get('black') or {}
    if (w.get('username') or '').lower() == me:
        color, mine, opp = 'white', w, b
    elif (b.get('username') or '').lower() == me:
        color, mine, opp = 'black', b, w
    else:
        return None
    try:
        game = chess.pgn.read_game(io.StringIO(g.get('pgn') or ''))
    except Exception:
        game = None
    if game is None:
        return None
    sans, ucis, board = [], [], game.board()
    for mv in game.mainline_moves():
        if len(ucis) >= GAME_PLIES:
            break
        sans.append(board.san(mv)); ucis.append(mv.uci()); board.push(mv)
    if not ucis:
        return None
    res = mine.get('result')
    # ECOUrl: ".../openings/Sicilian-Defense-Open-Dragon-6...a6-7.Be3" -> "Sicilian Defense Open Dragon"
    eco = re.sub(r'-+', ' ', (game.headers.get('ECOUrl') or '').rstrip('/').split('/')[-1])
    eco = re.split(r'\.\.\.|\s\d+\.', eco)[0].strip()
    return {'site': 'chesscom', 'id': (g.get('url') or '').rstrip('/').split('/')[-1] or g.get('uuid') or '',
            'url': g.get('url') or '', 'user': me, 'color': color,
            'opp': opp.get('username') or '?', 'rating': mine.get('rating'), 'opp_rating': opp.get('rating'),
            'result': 'win' if res == 'win' else ('draw' if res in CC_DRAWS else 'loss'),
            'speed': g.get('time_class') or '', 'ts': (g.get('end_time') or 0) * 1000,
            'opening': eco, 'uci': ' '.join(ucis), 'san': ' '.join(sans)}

def _opening_family(name):
    """La famiglia di un'apertura: "Sicilian Defense: Alapin" (Lichess) o "Sicilian Defense French
       Variation" (Chess.com, senza i due punti) -> "Sicilian Defense"."""
    name = (name or '').split(':')[0]
    m = re.match(r'(.*?\b(?:Defense|Defence|Opening|Game|Attack|Gambit|System))\b', name)
    return (m.group(1) if m else name).strip()

def fetch_lichess_games(user, max_games, since=None):
    """Partite di un utente Lichess, dalla piu' recente. Sono pubbliche: il token, se c'e', alza solo il
       limite di velocita'. Ritorna (record, errore)."""
    params = {'max': max_games, 'moves': 'true', 'opening': 'true', 'clocks': 'false', 'evals': 'false'}
    if since:
        params['since'] = int(since) + 1
    url = 'https://lichess.org/api/games/user/%s?%s' % (urllib.parse.quote(user), urllib.parse.urlencode(params))
    tok = lichess_token()
    # Poi senza token: un token scaduto (401) o il limite di Lichess ("una richiesta alla volta",
    # 429) non devono bloccare la funzione.
    attempts = [bool(tok), False]
    err = None
    for i, auth in enumerate(attempts):
        headers = {'Accept': 'application/x-ndjson'}
        if auth:
            headers['Authorization'] = 'Bearer ' + tok
        out = []
        try:
            with http_get(url, headers, timeout=60) as r:
                for raw in r:
                    raw = raw.strip()
                    rec = _lichess_record(json.loads(raw), user) if raw else None
                    if rec:
                        out.append(rec)
            return out, None
        except urllib.error.HTTPError as e:
            err = _net_error(e)
            if e.code not in (401, 429) or i == len(attempts) - 1:
                return out, err
            if e.code == 429:
                time.sleep(1.5)
        except Exception as e:
            return out, _net_error(e)
    return [], err

def fetch_chesscom_games(user, max_games, since=None):
    """Partite Chess.com dagli archivi mensili pubblici, dal mese piu' recente."""
    base = 'https://api.chess.com/pub/player/%s/games/' % urllib.parse.quote(user.lower())
    try:
        with http_get(base + 'archives', timeout=20) as r:
            archives = json.load(r).get('archives') or []
    except Exception as e:
        return [], _net_error(e)
    out = []
    for aurl in reversed(archives):
        try:
            with http_get(aurl, timeout=30) as r:
                month = json.load(r).get('games') or []
        except Exception as e:
            return out, _net_error(e)
        for g in reversed(month):
            if since and (g.get('end_time') or 0) * 1000 <= since:
                return out, None
            rec = _chesscom_record(g, user)
            if rec:
                out.append(rec)
                if len(out) >= max_games:
                    return out, None
    return out, None

FETCHERS = {'lichess': fetch_lichess_games, 'chesscom': fetch_chesscom_games}

def _fetch_args(req):
    site, user = req.get('site'), (req.get('user') or '').strip()
    if site not in FETCHERS or not USER_RE.fullmatch(user):
        return None
    try:
        n = max(1, min(int(req.get('max') or 300), 3000))
    except (TypeError, ValueError):
        n = 300
    return site, user, n

def _move_label(ply, san):   # partite: sempre dalla posizione iniziale
    return '%d%s%s' % (ply // 2 + 1, '.' if ply % 2 == 0 else '...', san)

def _game_brief(g):
    return {'url': g.get('url'), 'opp': g.get('opp'), 'opp_rating': g.get('opp_rating'), 'result': g.get('result'),
            'speed': g.get('speed'), 'date': datetime.fromtimestamp(g['ts'] / 1000).strftime('%Y-%m-%d') if g.get('ts') else ''}

def _follow(ucis, idx, my_white):
    """Segue una partita (mosse UCI dalla posizione iniziale) nell'albero del repertorio.
       -> (esito, ply, chiave, board): 'end' = restando nel repertorio la preparazione e' finita (o la
       partita); 'dev' = qui ho giocato io una mossa fuori repertorio; 'exit' = qui l'avversario ha
       giocato una mossa che il repertorio non copre. board = la posizione a quel ply."""
    board = chess.Board()
    children = idx['children']
    for ply, u in enumerate(ucis):
        k = _pos_key(board)
        kids = [x for x in (children.get(k) or ()) if x != '0000']   # la mossa nulla chiude la linea
        if not kids:
            return 'end', ply, k, board
        if u not in kids:
            return ('dev' if board.turn == my_white else 'exit'), ply, k, board
        board.push_uci(u)
    return 'end', len(ucis), None, board

def _lines_through(idx, key, limit=5):
    """Varianti del repertorio che passano dalla posizione: le piu' corte, il cuore della linea."""
    by_var = (idx['reach'].get(key) or {}).get('by_var') or {}
    data = idx['data']
    return sorted(by_var, key=lambda vid: len(data.get(vid, {}).get('moves') or []))[:limit]

def _exit_bucket(exits, idx, k, ucis, sans, ply, board):
    """Un'uscita dal repertorio raggruppata per (posizione, mossa): da qui si prepara la risposta."""
    b = exits.get((k, ucis[ply]))
    if b is None:
        vids = _lines_through(idx, k, 1)
        sample = idx['data'].get(vids[0], {}) if vids else {}
        b = exits[(k, ucis[ply])] = {'ply': ply, 'path': ucis[:ply + 1], 'fen': board.fen(), 'count': 0,
                                     'move': _move_label(ply, sans[ply]), 'games': [],
                                     'course': sample.get('course') or '', 'chapter': sample.get('chapter') or ''}
    return b

def _games_report(games, color):
    """Le partite (giocate col colore `color`) contro il repertorio di quel colore: dove hai deviato tu
       (linee da ripassare) e dove e' uscito l'avversario (risposte da preparare)."""
    idx = _build_index(None, color)
    my_white = (color == 'white')
    devs, exits, depth, other = {}, {}, [], {}
    tally = {'games': len(games), 'in_rep': 0, 'covered': 0, 'dev': 0, 'exit': 0}
    for g in sorted(games, key=lambda x: -(x.get('ts') or 0)):   # i campioni mostrati = i piu' recenti
        ucis, sans = g['uci'].split(), g['san'].split()
        st, ply, k, board = _follow(ucis, idx, my_white)
        if st == 'end' and ply == 0:
            continue                       # mai entrata nel repertorio di questo colore
        if st == 'dev' and ply == 0:       # un'altra prima mossa: un'altra apertura, non una linea dimenticata
            lab = _move_label(0, sans[0])
            other[lab] = other.get(lab, 0) + 1
            continue
        tally['in_rep'] += 1
        depth.append(ply)
        if st == 'end':
            tally['covered'] += 1
            continue
        tally[st] += 1
        if st == 'dev':
            b = devs.get(k)
            if b is None:
                kids = idx['children'].get(k) or {}
                b = devs[k] = {'ply': ply, 'path': ucis[:ply], 'fen': board.fen(), 'count': 0, 'played': {},
                               'expected': [_move_label(ply, c['san']) for x, c in kids.items() if x != '0000'],
                               'games': [], 'var_ids': _lines_through(idx, k)}
            lab = _move_label(ply, sans[ply])
            b['played'][lab] = b['played'].get(lab, 0) + 1
        else:
            b = _exit_bucket(exits, idx, k, ucis, sans, ply, board)
        b['count'] += 1
        if len(b['games']) < 5:
            b['games'].append(_game_brief(g))
    devs_l = sorted(devs.values(), key=lambda b: (-b['count'], b['ply']))[:60]
    for b in devs_l:
        b['played'] = [{'move': m, 'count': n} for m, n in sorted(b['played'].items(), key=lambda kv: -kv[1])]
    tally['avg_ply'] = round(sum(depth) / len(depth), 1) if depth else 0
    return {'tally': tally, 'devs': devs_l, 'exits': sorted(exits.values(), key=lambda b: (-b['count'], b['ply']))[:60],
            'other': [{'move': m, 'count': n} for m, n in sorted(other.items(), key=lambda kv: -kv[1])]}

def _games_tree(games, path, rep_color):
    """Mosse giocate nelle partite dalla posizione dopo `path` (anche per trasposizione, a parita' di
       mosse), con i risultati, piu' le mosse del repertorio `rep_color` da quella posizione."""
    board, applied = chess.Board(), []
    for u in path:
        try:
            board.push_uci(u)
        except ValueError:
            break
        applied.append(u)
    tk, n = _pos_key(board), len(applied)
    moves = {}
    for g in games:
        ucis = g['uci'].split()
        if len(ucis) <= n:
            continue
        b = chess.Board()
        for u in ucis[:n]:
            b.push_uci(u)
        if _pos_key(b) != tk:
            continue
        u = ucis[n]
        m = moves.get(u)
        if m is None:
            m = moves[u] = {'uci': u, 'san': g['san'].split()[n], 'games': 0, 'white': 0, 'draws': 0, 'black': 0}
        m['games'] += 1
        if g['result'] == 'draw':
            m['draws'] += 1
        elif (g['result'] == 'win') == (g['color'] == 'white'):
            m['white'] += 1
        else:
            m['black'] += 1
    kids = _build_index(None, rep_color)['children'].get(tk) or {}
    return {'fen': board.fen(), 'path': applied, 'turn': 'w' if board.turn else 'b',
            'mine': board.turn == (rep_color == 'white'),
            'moves': sorted(moves.values(), key=lambda m: -m['games']),
            'rep': [{'uci': x, 'san': c['san']} for x, c in kids.items() if x != '0000']}

def _opponent_report(games, my_color):
    """L'avversario col colore opposto al mio: dove le sue partite escono dal MIO repertorio
       (risposte da preparare) e quali mie linee servono davvero contro di lui."""
    opp_color = 'black' if my_color == 'white' else 'white'
    gs = [g for g in games if g.get('color') == opp_color]
    score, openings = {'win': 0, 'draw': 0, 'loss': 0}, {}
    for g in gs:
        score[g['result']] += 1
        fam = _opening_family(g.get('opening'))
        if fam:
            openings[fam] = openings.get(fam, 0) + 1
    idx = _build_index(None, my_color)
    data = idx['data']
    cov = {'covered': 0, 'exit': 0, 'dev': 0, 'out': 0}
    exits, reached = {}, {}
    for g in sorted(gs, key=lambda x: -(x.get('ts') or 0)):
        ucis, sans = g['uci'].split(), g['san'].split()
        st, ply, k, board = _follow(ucis, idx, my_color == 'white')
        if ply == 0 and st != 'exit':      # i suoi avversari hanno aperto in un altro modo: non dice nulla
            cov['out'] += 1
            continue
        cov['covered' if st == 'end' else st] += 1
        if k is not None:
            reached.setdefault(k, [0, ply])[0] += 1
        if st == 'exit':
            b = _exit_bucket(exits, idx, k, ucis, sans, ply, board)
            b['count'] += 1
            if len(b['games']) < 5:
                b['games'].append(_game_brief(g))
    # Linee da ripassare: dalle posizioni del mio repertorio dove le sue partite arrivano piu' spesso e
    # piu' a fondo. Dove la mia preparazione finisce, le linee che finiscono li'; altrove le piu' corte.
    lines, seen = [], set()
    for k, (cnt, ply) in sorted(reached.items(), key=lambda kv: -(kv[1][0] * (kv[1][1] + 1))):
        for vid in ((idx['ends'].get(k) or [])[:3] or _lines_through(idx, k, 2)):
            if vid in seen or vid not in data:
                continue
            seen.add(vid)
            lines.append({'id': vid, 'title': data[vid].get('title', ''), 'course': data[vid].get('course', ''),
                          'count': cnt, 'ply': ply})
        if len(lines) >= 25:
            break
    return {'games': len(gs), 'score': score, 'coverage': cov,
            'openings': [{'name': n, 'count': c} for n, c in sorted(openings.items(), key=lambda kv: -kv[1])[:6]],
            'exits': sorted(exits.values(), key=lambda b: (-b['count'], b['ply']))[:40], 'lines': lines[:25]}

def _games_of(p, color, account=''):
    return [g for g in p['games'].values()
            if g.get('color') == color and (not account or g['site'] + ':' + g['user'] == account)]

def _color_arg(v):
    return v if v in ('white', 'black') else 'white'

@app.route('/api/personal/state', methods=['GET'])
def personal_state():
    p = load_personal()
    by_color = {'white': 0, 'black': 0}
    for g in p['games'].values():
        by_color[g['color']] = by_color.get(g['color'], 0) + 1
    opps = sorted(p['opponents'].items(), key=lambda kv: kv[1].get('fetched') or '', reverse=True)
    return jsonify({'accounts': sorted(p['accounts'].values(), key=lambda a: (a['site'], a['user'])),
                    'games': len(p['games']), 'by_color': by_color,
                    'opponents': [{'key': k, 'name': o.get('name'), 'site': o.get('site'), 'n': len(o.get('games') or []),
                                   'fetched': o.get('fetched')} for k, o in opps]})

@app.route('/api/games/sync', methods=['POST'])
def games_sync():
    """Scarica le TUE partite (Lichess o Chess.com) in personal.json: di default solo quelle nuove
       dall'ultima volta; full=1 riprende le ultime N (per andare piu' indietro)."""
    req = request.get_json(silent=True) or {}
    args = _fetch_args(req)
    if not args:
        return jsonify({'success': False, 'error': 'Nome utente non valido.'}), 400
    site, user, n = args
    p = load_personal()
    key = site + ':' + user.lower()
    acc = p['accounts'].get(key) or {}
    recs, err = FETCHERS[site](user, n, None if req.get('full') else acc.get('last_ts'))
    if err and not recs:
        return jsonify({'success': False, 'error': err})
    added = 0
    for r in recs:
        gid = site + ':' + r['id']
        if gid not in p['games']:
            p['games'][gid] = r
            added += 1
    mine = [g for g in p['games'].values() if g['site'] == site and g['user'] == user.lower()]
    p['accounts'][key] = {'key': key, 'site': site, 'user': user.lower(), 'name': user, 'count': len(mine),
                          'last_ts': max((g['ts'] for g in mine), default=None),
                          'synced': datetime.now().isoformat(timespec='seconds')}
    save_personal(p)
    return jsonify({'success': True, 'added': added, 'count': len(mine), 'error': err})

@app.route('/api/games/remove', methods=['POST'])
def games_remove():
    key = (request.get_json(silent=True) or {}).get('key')
    p = load_personal()
    if key not in p['accounts']:
        return jsonify({'success': False, 'error': 'Account non trovato.'}), 404
    site, user = key.split(':', 1)
    p['games'] = {k: g for k, g in p['games'].items() if not (g['site'] == site and g['user'] == user)}
    del p['accounts'][key]
    save_personal(p)
    return jsonify({'success': True})

@app.route('/api/games/report', methods=['GET'])
def games_report():
    color = _color_arg(request.args.get('color'))
    return jsonify(_games_report(_games_of(load_personal(), color, request.args.get('account') or ''), color))

@app.route('/api/games/tree', methods=['POST'])
def games_tree():
    req = request.get_json(silent=True) or {}
    color = _color_arg(req.get('color'))
    path = req.get('path') if isinstance(req.get('path'), list) else []
    return jsonify(_games_tree(_games_of(load_personal(), color, req.get('account') or ''), path, color))

@app.route('/api/opponent/scan', methods=['POST'])
def opponent_scan():
    """Partite pubbliche dell'avversario (salvate: le ultime MAX_OPPONENTS) contro il mio repertorio."""
    req = request.get_json(silent=True) or {}
    args = _fetch_args(req)
    if not args:
        return jsonify({'success': False, 'error': 'Nome utente non valido.'}), 400
    site, user, n = args
    my_color = _color_arg(req.get('color'))
    key = site + ':' + user.lower()
    p = load_personal()
    o = p['opponents'].get(key)
    if not o or req.get('refresh'):
        recs, err = FETCHERS[site](user, n)
        if err and not recs:
            return jsonify({'success': False, 'error': err})
        o = p['opponents'][key] = {'site': site, 'user': user.lower(), 'name': user, 'games': recs,
                                   'fetched': datetime.now().isoformat(timespec='seconds')}
        for old in sorted(p['opponents'], key=lambda k: p['opponents'][k].get('fetched') or '')[:-MAX_OPPONENTS]:
            del p['opponents'][old]
        save_personal(p)
    rep = _opponent_report(o['games'], my_color)
    rep.update({'success': True, 'key': key, 'name': o.get('name'), 'site': site, 'fetched': o.get('fetched'),
                'total': len(o['games'])})
    return jsonify(rep)

@app.route('/api/opponent/tree', methods=['POST'])
def opponent_tree():
    req = request.get_json(silent=True) or {}
    o = load_personal()['opponents'].get(req.get('key'))
    if not o:
        return jsonify({'error': 'Avversario non trovato: rianalizzalo.'}), 404
    my_color = _color_arg(req.get('color'))
    opp_color = 'black' if my_color == 'white' else 'white'
    path = req.get('path') if isinstance(req.get('path'), list) else []
    return jsonify(_games_tree([g for g in o['games'] if g.get('color') == opp_color], path, my_color))

@app.route('/api/opponent/remove', methods=['POST'])
def opponent_remove():
    key = (request.get_json(silent=True) or {}).get('key')
    p = load_personal()
    if p['opponents'].pop(key, None) is None:
        return jsonify({'success': False, 'error': 'Avversario non trovato.'}), 404
    save_personal(p)
    return jsonify({'success': True})

# ----- Finali contro la tablebase (la tablebase la interroga il browser: tablebase.lichess.ovh) -----
# Posizioni classiche verificate con la tablebase (chi muove vince / tiene la patta). Solo FEN e nome.
ENDGAME_CATALOG = [
    ("Matto di donna", "8/8/8/4k3/8/8/8/3QK3 w - - 0 1", "win"),
    ("Matto di torre", "8/8/8/4k3/8/8/8/4K2R w - - 0 1", "win"),
    ("Re e pedone: l'opposizione", "8/8/4k3/8/4K3/8/4P3/8 w - - 0 1", "win"),
    ("Re e pedone: la difesa", "4k3/8/8/4K3/4P3/8/8/8 b - - 0 1", "draw"),
    ("Donna contro pedone in settima", "8/8/8/8/8/8/1kp5/3K3Q w - - 0 1", "win"),
    ("Posizione di Lucena", "1K1k4/1P6/8/8/8/8/r7/2R5 w - - 0 1", "win"),
    ("Posizione di Philidor", "4k3/8/r7/4PK2/8/8/8/7R b - - 0 1", "draw"),
    ("Posizione di Vancura", "R7/6k1/P4r2/8/8/8/8/6K1 b - - 0 1", "draw"),
    ("Matto con i due alfieri", "8/8/8/4k3/8/8/8/2B1KB2 w - - 0 1", "win"),
    ("Matto di alfiere e cavallo", "8/8/8/4k3/8/8/8/2B1K1N1 w - - 0 1", "win"),
    ("Donna contro torre", "8/8/8/3rk3/8/8/8/3QK3 w - - 0 1", "win"),
]

def _eg_id(fen):
    return 'eg_' + hashlib.md5(' '.join(fen.split()[:4]).encode()).hexdigest()[:10]

@app.route('/api/endgames', methods=['GET'])
def endgames_list():
    p = load_personal()
    if not p.get('endgames_seeded'):    # le classiche arrivano una volta sola: se ne elimini una non torna
        for title, fen, goal in ENDGAME_CATALOG:
            p['endgames'].setdefault(_eg_id(fen), {'fen': fen, 'title': title, 'goal': goal, 'builtin': True,
                                                   'srs': new_srs(), 'stats': default_stats()})
        p['endgames_seeded'] = True
        save_personal(p)
    return jsonify({'endgames': [dict(e, id=eid) for eid, e in p['endgames'].items()]})

@app.route('/api/endgames/add', methods=['POST'])
def endgames_add():
    req = request.get_json(silent=True) or {}
    goal = req.get('goal')
    if goal not in ('win', 'draw'):
        return jsonify({'success': False, 'error': 'Obiettivo non valido.'}), 400
    try:
        board = chess.Board((req.get('fen') or '').strip())
    except ValueError:
        return jsonify({'success': False, 'error': 'FEN non valido.'}), 400
    if not board.is_valid():
        return jsonify({'success': False, 'error': 'Posizione illegale.'}), 400
    if chess.popcount(board.occupied) > 7:
        return jsonify({'success': False, 'error': 'Al massimo 7 pezzi (il limite della tablebase).'}), 400
    if board.is_game_over():
        return jsonify({'success': False, 'error': 'In questa posizione la partita è già finita.'}), 400
    board.halfmove_clock = 0
    fen = board.fen()
    p = load_personal()
    eid = _eg_id(fen)
    if eid in p['endgames']:
        return jsonify({'success': False, 'error': 'Questa posizione c\'è già.'}), 409
    p['endgames'][eid] = {'fen': fen, 'title': (req.get('title') or '').strip()[:120] or 'Posizione', 'goal': goal,
                          'builtin': False, 'srs': new_srs(), 'stats': default_stats()}
    save_personal(p)
    return jsonify({'success': True, 'id': eid})

@app.route('/api/endgames/delete', methods=['POST'])
def endgames_delete():
    eid = (request.get_json(silent=True) or {}).get('id')
    p = load_personal()
    if p['endgames'].pop(eid, None) is None:
        return jsonify({'success': False, 'error': 'Posizione non trovata.'}), 404
    save_personal(p)
    return jsonify({'success': True})

@app.route('/api/endgames/review', methods=['POST'])
def endgames_review():
    req = request.get_json(silent=True) or {}
    q = req.get('quality')
    if isinstance(q, bool) or not isinstance(q, int) or not (0 <= q <= 5):
        return jsonify({'success': False, 'error': 'Valutazione non valida.'}), 400
    p = load_personal()
    e = p['endgames'].get(req.get('id'))
    if not e:
        return jsonify({'success': False, 'error': 'Posizione non trovata.'}), 404
    apply_review(e, q)
    save_personal(p)
    return jsonify({'success': True, 'srs': e['srs'], 'stats': e['stats']})

# ----- Accesso dal telefono (stessa rete Wi-Fi) -----
# Di serie il server ascolta solo su 127.0.0.1. Con l'accesso attivo (settings.json) si accende anche un
# server sulla rete locale (lan_start, piu' sotto): chi non e' il computer stesso deve inserire un PIN,
# poi un cookie lo ricorda.
LOCAL_ADDRS = ('127.0.0.1', '::1', '::ffff:127.0.0.1')
LOCAL_HOSTS = ('127.0.0.1', 'localhost', '[::1]')
_settings_cache = {'mtime': None, 'data': {}}
_pin_fails = {}              # ip -> (tentativi falliti, bloccato fino a)

def load_settings():
    try:
        m = os.path.getmtime(SETTINGS_FILE)
    except OSError:
        return {}
    if _settings_cache['mtime'] != m:
        _settings_cache['data'] = load_data(SETTINGS_FILE)
        _settings_cache['mtime'] = m
    return _settings_cache['data']

def save_settings(s):
    save_data(s, SETTINGS_FILE)
    for f in (SETTINGS_FILE, SETTINGS_FILE + '.bak'):   # contiene il PIN
        try:
            os.chmod(f, 0o600)
        except OSError:
            pass

LOGIN_PAGE = '''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>openrepertoire</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#161615;color:#cfccc5;font:15px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
form{box-sizing:border-box;width:min(340px,calc(100vw - 32px));padding:24px;background:#1f1f1d;border:1px solid #2c2b28;border-radius:14px}
h1{margin:0 0 6px;font-size:18px;color:#edebe6}p{margin:0 0 18px;font-size:13px;line-height:1.5;color:#a29f97}
input{box-sizing:border-box;width:100%;padding:12px;font-size:22px;letter-spacing:.3em;text-align:center;color:#edebe6;background:#1a1a19;border:1px solid #3b3a36;border-radius:8px}
button{width:100%;margin-top:12px;padding:12px;font-size:15px;font-weight:600;color:#fff;background:#557a3e;border:0;border-radius:8px}
.m{margin-top:12px;min-height:18px;font-size:13px;color:#e5806f}</style></head><body>
<form method="post" action="/login"><h1>openrepertoire</h1><p>Inserisci il PIN che vedi sul computer (icona del telefono in alto).</p>
<input name="pin" inputmode="numeric" autocomplete="one-time-code" maxlength="6" autofocus>
<button type="submit">Entra</button><div class="m">{{msg}}</div></form></body></html>'''

@app.before_request
def lan_gate():
    if request.remote_addr in LOCAL_ADDRS:
        # Dal Mac stesso si entra senza PIN, ma solo coi nomi locali: un sito ostile non puo' farsi
        # passare per l'app ridirigendo il suo dominio su 127.0.0.1 (DNS rebinding).
        host = request.host if request.host.endswith(']') else request.host.rsplit(':', 1)[0]
        if host.lower() in LOCAL_HOSTS:
            return None
        return Response('Host non ammesso.', 403, mimetype='text/plain')
    s = load_settings()
    if not (s.get('lan') and s.get('pin') and s.get('secret')):
        return Response('Accesso dalla rete disattivato.', 403, mimetype='text/plain')
    if hmac.compare_digest(request.cookies.get('orep_auth', ''), s['secret']):
        return None
    ip, msg = request.remote_addr, ''
    fails, until = _pin_fails.get(ip, (0, 0))
    if request.method == 'POST' and request.path == '/login':
        if time.time() < until:
            msg = 'Troppi tentativi: riprova tra un minuto.'
        elif hmac.compare_digest((request.form.get('pin') or '').strip(), s['pin']):
            _pin_fails.pop(ip, None)
            resp = redirect('/')
            resp.set_cookie('orep_auth', s['secret'], max_age=365 * 86400, httponly=True, samesite='Lax')
            return resp
        else:
            fails += 1
            _pin_fails[ip] = (fails, time.time() + 60 if fails >= 5 else 0)
            msg = 'PIN errato.'
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Serve il PIN.'}), 401
    return Response(LOGIN_PAGE.replace('{{msg}}', msg), 401, mimetype='text/html')

def lan_ip():
    """L'indirizzo del computer sulla rete locale (connect su UDP non manda pacchetti)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.0.2.1', 80))
        ip = s.getsockname()[0]
        s.close()
        return None if ip.startswith('127.') else ip
    except OSError:
        return None

def lan_urls(ip, port):
    urls = ['http://%s:%s' % (ip, port)] if ip else []
    host = socket.gethostname()
    if host.endswith('.local'):
        urls.append('http://%s:%s' % (host, port))
    return urls

# Il server di sempre resta su 127.0.0.1. Per il telefono se ne accende un SECONDO, legato
# all'indirizzo di rete del computer e sulla stessa porta (indirizzi diversi: nessun conflitto):
# l'accesso si accende e si spegne al volo, senza riavviare l'app.
_lan = {'srv': None, 'ip': None, 'port': None, 'error': None}
_lan_lock = threading.Lock()

def _lan_stop_locked():
    if _lan['srv']:
        _lan['srv'].shutdown()
        _lan['srv'].server_close()
    _lan.update(srv=None, ip=None, port=None)

def lan_stop():
    with _lan_lock:
        _lan_stop_locked()

def lan_start(port):
    """Accende (o riallinea, se il computer ha cambiato rete) il server per il telefono."""
    with _lan_lock:
        ip = lan_ip()
        if _lan['srv'] and _lan['ip'] == ip and _lan['port'] == port:
            return True
        _lan_stop_locked()
        if not ip:
            _lan['error'] = 'no_network'
            return False
        try:
            from werkzeug.serving import make_server
            srv = make_server(ip, int(port), app, threaded=True)
        except OSError as e:
            _lan['error'] = str(e)[:120]
            return False
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _lan.update(srv=srv, ip=ip, port=port, error=None)
        return True

@app.route('/api/lan', methods=['GET', 'POST'])
def api_lan():
    if request.remote_addr not in LOCAL_ADDRS:   # il PIN si legge solo dal computer
        return jsonify({'error': 'Solo dal computer.'}), 403
    s = dict(load_settings())
    if request.method == 'POST':
        req = request.get_json(silent=True) or {}
        if 'enabled' in req:
            s['lan'] = bool(req['enabled'])
        if req.get('new_pin') or (s.get('lan') and not s.get('pin')):
            s['pin'] = '%06d' % secrets.randbelow(10 ** 6)
            s['secret'] = secrets.token_hex(16)   # PIN nuovo = i telefoni gia' collegati rientrano col nuovo
        save_settings(s)
    port = int(request.host.rsplit(':', 1)[-1]) if ':' in request.host.split(']')[-1] else 80
    on = bool(s.get('lan'))
    # Il debugger di Werkzeug (OPENREP_DEBUG) non va mai in rete: in quel caso niente server per il telefono
    if on and not app.debug:
        lan_start(port)
    elif not on:
        lan_stop()
    return jsonify({'enabled': on, 'running': bool(_lan['srv']), 'error': _lan['error'] if on else None,
                    'pin': s.get('pin') if on else None, 'urls': lan_urls(_lan['ip'] or lan_ip(), port) if on else []})

# ----- Servizio: c'e' gia' un'istanza? chiudi l'app, apri la cartella dei dati -----
@app.route('/api/ping')
def api_ping():
    return jsonify({'app': 'openrepertoire', 'version': __version__})

@app.route('/api/quit', methods=['POST'])
def api_quit():
    """Chiude l'app (solo dal computer): prima parte la risposta, poi il processo esce."""
    if request.remote_addr not in LOCAL_ADDRS:
        return jsonify({'error': 'Solo dal computer.'}), 403
    threading.Timer(0.4, lambda: os._exit(0)).start()
    return jsonify({'success': True})

@app.route('/api/data_dir', methods=['GET', 'POST'])
def api_data_dir():
    """Dove stanno i dati; POST apre la cartella nel Finder / Esplora risorse (solo dal computer)."""
    if request.remote_addr not in LOCAL_ADDRS:
        return jsonify({'error': 'Solo dal computer.'}), 403
    if request.method == 'POST':
        try:
            if sys.platform == 'darwin':
                subprocess.Popen(['open', DATA_DIR])
            elif os.name == 'nt':
                os.startfile(DATA_DIR)
            else:
                subprocess.Popen(['xdg-open', DATA_DIR])
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:120], 'path': DATA_DIR})
    return jsonify({'success': True, 'path': DATA_DIR})

def _ours_on(port):
    """Su quella porta risponde gia' openrepertoire? (app aperta due volte: basta il browser)"""
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/api/ping' % port, timeout=1.5) as r:
            return json.loads(r.read().decode('utf-8')).get('app') == 'openrepertoire'
    except Exception:
        return False

def _free_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
        return port
    except OSError:
        s.bind(('127.0.0.1', 0))      # occupata da altro: una libera qualsiasi
        return s.getsockname()[1]
    finally:
        s.close()

def _frozen_logs():
    """L'app impacchettata non ha terminale (su Windows stdout e' None e Flask si pianterebbe):
       i messaggi del server vanno in un file nella cartella dei dati, azzerato oltre i 2 MB."""
    path = os.path.join(DATA_DIR, 'openrepertoire.log')
    big = os.path.exists(path) and os.path.getsize(path) > 2 * 1024 * 1024
    sys.stdout = sys.stderr = open(path, 'w' if big else 'a', buffering=1, encoding='utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))   # PORT env -> avvio su porta libera (preview/multi-istanza)
    debug = os.environ.get('OPENREP_DEBUG') == '1' and not FROZEN
    if FROZEN:
        # .app / .exe: niente lanciatore, il browser lo apre l'app. Gia' aperta: solo il browser.
        _frozen_logs()
        if _ours_on(port):
            webbrowser.open('http://127.0.0.1:%d' % port)
            sys.exit(0)
        port = _free_port(port)
        if not os.environ.get('OPENREP_NO_BROWSER'):
            threading.Timer(1.0, webbrowser.open, ['http://127.0.0.1:%d' % port]).start()
    if load_settings().get('lan') and not debug:   # mai il debugger di Werkzeug sulla rete
        lan_start(port)
    app.run(host='127.0.0.1', port=port, debug=debug, threaded=True)
