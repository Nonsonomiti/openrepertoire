from flask import Flask, render_template, request, jsonify
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
            static_folder=os.path.join(BASE_DIR, 'static'))

DATA_FILE = os.path.join(BASE_DIR, "repertoire.json")
# -------------------------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
    return {'reviews': 0, 'correct': 0, 'lapses': 0, 'last_quality': None}

def update_srs(srs, quality):
    rep, interval, ease = srs.get('rep', 0), srs.get('interval', 0), srs.get('ease', 2.5)
    
    if quality < 3:
        rep = 1
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
    req = request.json
    pgn_text = req.get('pgn')
    course_name = req.get('course', 'Varie') 
    perspective = req.get('perspective', 'white') 
    
    pgn_io = io.StringIO(pgn_text)
    data = load_data()
    
    count = 0
    imported = 0
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None: break
        
        count += 1
        title = game.headers.get("Event")
        if not title or title == "?":
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            title = f"{white} vs {black}" if white or black else f"Linea {count}"

        # Posizione di partenza: se il PGN ha un FEN (tattica/strategia) la salva
        start_fen = None
        if game.headers.get("SetUp") == "1" or "FEN" in game.headers:
            start_fen = game.headers.get("FEN")

        # Colore flessibile: 'auto' deduce il lato dal tratto nel FEN, per variante
        var_perspective = perspective
        if perspective == 'auto':
            if start_fen:
                var_perspective = 'white' if start_fen.split(' ')[1] == 'w' else 'black'
            else:
                var_perspective = 'white'

        moves_data = []
        node = game
        
        # Scorre SOLO la linea principale (variazioni[0])
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
            
        if moves_data:
            moves_str = (start_fen or "") + "".join([m["uci"] for m in moves_data])
            moves_hash = hashlib.md5(moves_str.encode()).hexdigest()[:10]
            var_id = f"var_{moves_hash}"

            if var_id not in data:
                data[var_id] = {
                    "course": course_name,
                    "chapter": derive_chapter(title),
                    "title": title,
                    "moves": moves_data,
                    "perspective": var_perspective,
                    "startFen": start_fen,
                    "stats": default_stats(),
                    "srs": {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
                }
                imported += 1
                
    save_data(data)
    return jsonify({"success": True, "imported": imported})

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
    req = request.json
    data = load_data()
    vid = req.get('id')
    quality = req.get('quality')
    
    if vid in data:
        data[vid]['srs'] = update_srs(data[vid]['srs'], quality)
        st = data[vid].get('stats') or default_stats()
        st['reviews'] = st.get('reviews', 0) + 1
        if quality >= 3:
            st['correct'] = st.get('correct', 0) + 1
        else:
            st['lapses'] = st.get('lapses', 0) + 1
        st['last_quality'] = quality
        data[vid]['stats'] = st
        save_data(data)

    return jsonify({"success": True})

@app.route('/api/delete', methods=['POST'])
def delete_variation():
    req = request.json
    data = load_data()
    vid = req.get('id')
    
    if vid in data:
        del data[vid]
        save_data(data)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Variante non trovata"})

@app.route('/api/delete_course', methods=['POST'])
def delete_course():
    req = request.json
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

    return jsonify({
        'total': total, 'learn': learn, 'due_today': due_today,
        'reviews_total': reviews_total, 'accuracy': accuracy, 'lapses_total': lapses_total,
        'upcoming': upcoming, 'hardest': hardest[:10]
    })

@app.route('/api/set_chapter', methods=['POST'])
def set_chapter():
    req = request.json
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
    req = request.json
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

@app.route('/api/search_position', methods=['POST'])
def search_position():
    req = request.json
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)