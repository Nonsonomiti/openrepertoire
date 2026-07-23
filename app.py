from flask import Flask, render_template, request, jsonify, Response
import chess
import chess.pgn
import io
import json
import os
import re
import hashlib
from datetime import datetime, timedelta

# --- BLINDATURA DEI PERCORSI ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'),
            instance_path=BASE_DIR)   # evita os.getcwd() (avvio robusto da qualsiasi cwd)

DATA_FILE = os.path.join(BASE_DIR, "repertoire.json")
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024   # tetto upload PGN: 8 MB
app.config['TEMPLATES_AUTO_RELOAD'] = True   # ricarica index.html senza riavvio del server
# -------------------------------

def load_data():
    # Prova il file principale, poi il backup .bak se corrotto/mancante
    for path in (DATA_FILE, DATA_FILE + ".bak"):
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except (ValueError, OSError):
                continue
    return {}

def save_data(data):
    # Scrittura atomica: tmp + fsync + rename, con backup del precedente in .bak
    tmp = DATA_FILE + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(DATA_FILE):
        os.replace(DATA_FILE, DATA_FILE + ".bak")
    os.replace(tmp, DATA_FILE)

def derive_chapter(title):
    # Deduce un sottocapitolo dal titolo grezzo del PGN (Chessable-style)
    t = title or ""
    t = re.sub(r'\s*#\d+\s*$', '', t)          # rimuove numerazione finale "#4"
    if ' vs ' in t:
        t = t.split(' vs ')[0]                  # "A vs B" -> "A"
    t = t.replace('-----', '-')
    t = re.sub(r'\s+', ' ', t).strip(' -')
    return t if t else 'Generale'

def default_stats():
    return {'reviews': 0, 'correct': 0, 'lapses': 0, 'last_quality': None, 'history': []}

def update_srs(srs, quality):
    rep, interval, ease = srs.get('rep', 0), srs.get('interval', 0), srs.get('ease', 2.5)
    
    if quality < 3:
        rep = 0          # lapse: azzera la sequenza (SM-2) -> primo successo riparte da interval=1
        interval = 0
    else:
        if rep == 0: interval = 1
        elif rep == 1: interval = 6
        else: interval = int(round(interval * ease))
        rep += 1
        
    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    next_review = (datetime.now() + timedelta(days=interval)).isoformat()
    
    return {'rep': rep, 'interval': interval, 'ease': ease, 'next_review': next_review}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/import', methods=['POST'])
def import_pgn():
    req = request.get_json(silent=True) or {}
    pgn_text = req.get('pgn')
    if not isinstance(pgn_text, str) or not pgn_text.strip():
        return jsonify({"success": False, "error": "PGN mancante o non valido."}), 400
    course_name = req.get('course', 'Varie')
    perspective = req.get('perspective', 'white')

    pgn_io = io.StringIO(pgn_text)
    data = load_data()
    
    count = 0
    imported = 0
    skipped = 0
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None: break
        
        count += 1
        title = game.headers.get("Event")
        if not title or title == "?":
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            title = f"{white} vs {black}" if white or black else f"Linea {count}"

        # Header non-standard dei nostri export PGN: restore fedele di corso/capitolo/colore
        hdr_course = game.headers.get("Course")
        hdr_chapter = game.headers.get("Chapter")
        hdr_persp = game.headers.get("Perspective")

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

        moves_data = []
        node = game
        
        # Scorre SOLO la linea principale (variazioni[0]); salta i game con mosse illegali
        try:
            while node.variations:
                main_node = node.variations[0]

                combined_comment = main_node.comment if main_node.comment else ""

                # Se ci sono diramazioni, le esporta come TESTO e le accoda ai commenti
                if len(node.variations) > 1:
                    alt_lines = []
                    for alt_node in node.variations[1:]:
                        exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
                        alt_text = alt_node.accept(exporter)
                        alt_text = alt_text.replace('\n', ' ') # Rimuove a capo per pulizia
                        alt_lines.append(f"Altra opzione: {alt_text}")

                    if alt_lines:
                        if combined_comment:
                            combined_comment += "\n\n" + "\n".join(alt_lines)
                        else:
                            combined_comment = "\n".join(alt_lines)

                moves_data.append({
                    "uci": main_node.move.uci(),
                    "san": main_node.san(),
                    "comment": combined_comment
                })
                node = main_node
        except Exception:
            skipped += 1
            continue

        if moves_data:
            moves_str = (start_fen or "") + "".join([m["uci"] for m in moves_data])
            moves_hash = hashlib.md5(moves_str.encode()).hexdigest()[:10]
            var_id = f"var_{moves_hash}"

            if var_id not in data:
                data[var_id] = {
                    "course": hdr_course or course_name,
                    "chapter": hdr_chapter or derive_chapter(title),
                    "title": title,
                    "moves": moves_data,
                    "perspective": var_perspective,
                    "startFen": start_fen,
                    "stats": default_stats(),
                    "srs": {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
                }
                imported += 1
                
    save_data(data)
    return jsonify({"success": True, "imported": imported, "skipped": skipped})

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

    learn = []
    review = []
    repertoire = []

    for vid, vdata in data.items():
        vdata['id'] = vid
        repertoire.append(vdata)
        
        if vdata['srs']['rep'] == 0:
            learn.append(vdata)
        elif datetime.fromisoformat(vdata['srs']['next_review']) <= now:
            review.append(vdata)
            
    return jsonify({"learn": learn, "review": review, "repertoire": repertoire})

@app.route('/api/review', methods=['POST'])
def review():
    req = request.get_json(silent=True) or {}
    vid = req.get('id')
    quality = req.get('quality')
    if not isinstance(vid, str) or isinstance(quality, bool) or not isinstance(quality, int) or not (0 <= quality <= 5):
        return jsonify({"success": False, "error": "Dati di valutazione non validi."}), 400
    data = load_data()

    if vid in data:
        data[vid]['srs'] = update_srs(data[vid]['srs'], quality)
        st = data[vid].get('stats') or default_stats()
        st['reviews'] = st.get('reviews', 0) + 1
        if quality >= 3:
            st['correct'] = st.get('correct', 0) + 1
        else:
            st['lapses'] = st.get('lapses', 0) + 1
        st['last_quality'] = quality
        hist = st.get('history') or []
        hist.append({'date': datetime.now().isoformat(), 'q': quality})
        st['history'] = hist[-20:]   # mantiene le ultime 20 valutazioni
        data[vid]['stats'] = st
        save_data(data)

    return jsonify({"success": True})

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

        if srs.get('rep', 0) == 0:
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

        if srs.get('rep', 0) == 0:
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

    return jsonify({
        'total': total, 'learn': learn, 'due_today': due_today,
        'reviews_total': reviews_total, 'accuracy': accuracy, 'lapses_total': lapses_total,
        'upcoming': upcoming, 'hardest': hardest[:10],
        'by_course': by_course_list, 'by_color': by_color_list,
        'retention': {'overall': retention_overall, 'series': retention_series}
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
_index_cache = {'mtime': None, 'by_filter': {}}

def _pos_key(board):
    # FEN normalizzato: placement + tratto + arrocchi + en-passant (esclude i contatori di mossa)
    return ' '.join(board.fen().split(' ')[:4])

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
                san = board.san(chess.Move.from_uci(uci))
            except Exception:
                san = m.get('san', '')
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
                     'fen': board.fen(), 'turn': ('w' if board.turn else 'b')}
                reach[k] = r
            if vid not in r['by_var']:
                r['by_var'][vid] = len(path)
            r['paths'].add(tuple(path))
            if board.turn == persp_white:   # mossa del LATO dell'utente da questa posizione
                r['owner_moves'].add(uci)
            try:
                board.push_uci(uci)
            except Exception:
                break
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
        items.append({'key': key, 'fen': r['fen'], 'turn': r['turn'],
                      'reached_by': reached_by, 'reached_count': len(by_var),
                      'conflict': len(r['owner_moves']) >= 2, 'continuations': sans})
    items.sort(key=lambda x: (-int(x['conflict']), -x['reached_count']))
    return jsonify({'transpositions': items[:80], 'total': len(items)})

@app.route('/api/holes', methods=['GET'])
def api_holes():
    """Foglie premature (buchi di copertura): posizioni di fine-linea dove tocca al LATO
       dell'utente muovere e nessun'altra linea fornisce una continuazione. Le fini dove
       tocca all'avversario sono posizioni di riposo legittime, NON buchi."""
    course = request.args.get('course') or None
    perspective = request.args.get('perspective')
    if perspective not in ('white', 'black'):
        perspective = 'white'
    idx = _build_index(course, perspective)
    data = idx['data']
    owner = 'w' if perspective == 'white' else 'b'
    holes = []
    for key, vids in idx['ends'].items():
        if key.split(' ')[1] != owner:
            continue                        # tocca all'avversario -> fine legittima
        if idx['children'].get(key):
            continue                        # coperto: un'altra linea continua da qui
        sample = min(vids, key=lambda vid: len(data.get(vid, {}).get('moves', [])))
        v = data.get(sample, {})
        b = _board_for(v)
        sans, path = [], []
        for m in v.get('moves', []):
            uci = m.get('uci')
            if not uci:
                break
            try:
                mv = chess.Move.from_uci(uci)
                sans.append(b.san(mv)); b.push(mv); path.append(uci)
            except Exception:
                break
        holes.append({
            'fen': b.fen(), 'ply': len(path), 'path': path,
            'san_line': ' '.join(sans), 'last_move': sans[-1] if sans else '',
            'sample_var_id': sample, 'title': v.get('title', ''),
            'course': v.get('course', ''), 'chapter': v.get('chapter', ''),
            'end_count': len(vids)
        })
    holes.sort(key=lambda h: (h['ply'], -h['end_count']))
    return jsonify({'holes': holes[:120], 'count': len(holes)})

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
        if mv not in board.legal_moves:
            return jsonify({"success": False, "error": "Mossa %d illegale (%s)." % (i + 1, uci)}), 400
        comment = (m.get('comment') if isinstance(m, dict) else '') or ''
        moves_data.append({"uci": uci, "san": board.san(mv), "comment": comment})
        board.push(mv)

    data = load_data()
    moves_str = (start_fen or "") + "".join(m["uci"] for m in moves_data)
    new_id = "var_" + hashlib.md5(moves_str.encode()).hexdigest()[:10]
    old_id = req.get('id')
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
    return jsonify({"success": True, "id": new_id, "rekeyed": bool(editing and new_id != old_id)})

# ===== Export PGN (backup / condivisione): ricostruisce il PGN da moves+comment =====
@app.route('/api/export', methods=['GET'])
def export_pgn():
    """Esporta repertorio / corso / capitolo / varianti scelte come PGN scaricabile.
       Filtri: course, chapter, ids (id separati da virgola).
       strip=1 -> rimuove commenti e header non-standard (PGN pulito, solo mosse,
       per studi Lichess/analisi personali). Senza strip include Course/Chapter/
       Perspective per un re-import fedele (i lettori standard li ignorano).
       merge=1 -> fonde le varianti di uno stesso (corso, capitolo, posizione di
       partenza) in UN SOLO game ad albero (prefissi condivisi, rami sulle mosse
       diverse): Lichess importa 1 capitolo ramificato invece di N quasi-uguali."""
    course = request.args.get('course') or None
    chapter = request.args.get('chapter') or None
    ids = set(x for x in (request.args.get('ids') or '').split(',') if x)
    strip = request.args.get('strip') in ('1', 'true', 'yes')
    merge = request.args.get('merge') in ('1', 'true', 'yes')
    data = load_data()

    # 1) filtra le varianti richieste (con mosse)
    selected = []
    for vid, v in data.items():
        if ids and vid not in ids:
            continue
        if course and (v.get('course') or 'Varie') != course:
            continue
        if chapter and (v.get('chapter') or 'Generale') != chapter:
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
        groups = {}
        for v in selected:
            key = ((v.get('course') or 'Varie'), (v.get('chapter') or 'Generale'), v.get('startFen') or '')
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
                    if mv not in board.legal_moves:
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
                    if mv not in board.legal_moves:
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
    scope = (course or 'corso') + '_' + chapter if chapter else (course or ('selezione' if ids else 'tutto'))
    if merge:
        scope += '_albero'
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', scope)[:60]
    fname = "openrepertoire_%s_%s.pgn" % (safe, datetime.now().strftime('%Y%m%d'))
    return Response(pgn_text, mimetype='application/x-chess-pgn',
                    headers={'Content-Disposition': 'attachment; filename="%s"' % fname,
                             'X-Export-Count': str(len(games))})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))   # PORT env -> avvio su porta libera (preview/multi-istanza)
    app.run(port=port, debug=os.environ.get('OPENREP_DEBUG') == '1')