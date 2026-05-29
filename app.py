from flask import Flask, render_template, request, jsonify
import chess.pgn
import io
import json
import os
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
            moves_str = "".join([m["uci"] for m in moves_data])
            moves_hash = hashlib.md5(moves_str.encode()).hexdigest()[:10]
            var_id = f"var_{moves_hash}"
            
            if var_id not in data:
                data[var_id] = {
                    "course": course_name, 
                    "title": title,
                    "moves": moves_data,
                    "perspective": perspective, 
                    "srs": {'rep': 0, 'interval': 0, 'ease': 2.5, 'next_review': datetime.now().isoformat()}
                }
                imported += 1
                
    save_data(data)
    return jsonify({"success": True, "imported": imported})

@app.route('/api/due', methods=['GET'])
def get_due():
    data = load_data()
    now = datetime.now()
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)