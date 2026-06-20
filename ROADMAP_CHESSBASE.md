# openrepertoire → anche ChessBase-like: roadmap

_Prodotto da workflow multi-agente 2026-06-19 (19 agenti: verifica avversariale + panel di design). App locale mono-utente, file-based, offline-first._

Tutta la roadmap rispetta i **vincoli inviolabili**: zero testo generato nei `moves[].comment` (eval/statistiche numeriche e mosse legali NON sono "testo generato" → ammesse), nessuna dipendenza server pesante imposta di default, modifiche `app.py` = restart segnalato.

---

## 1. Stato attuale vs ChessBase — gap analysis

| Capacità ChessBase | openrepertoire | Note |
|---|---|---|
| Import PGN | **C'è** | `/api/import`, ma SOLO mainline; diramazioni ripiegate a testo "Altra opzione:", hash-dedup |
| Training/ripasso SRS | **C'è** (oltre CB) | SM-2 server-side, LEARN→CONSOLIDATE→REVIEW |
| Ricerca per posizione (FEN esatto) | **C'è** | `/api/search_position` (board-walk + piece-placement) |
| Statistiche base | **Parziale** | `/api/stats`: reviews/correct/lapses globali, upcoming, hardest |
| Opening tree / albero del repertorio | **Manca** | storage piatto `var_<hash>`, varianti isolate |
| Rilevamento trasposizioni | **Manca** | nessun merge per posizione |
| Copertura difensiva / buchi | **Manca** | non sai "cosa NON hai coperto" |
| Authoring in-app (build/edit mossa per mossa) | **Manca** | solo import; editare un refuso = re-import |
| Annotazione utente (commenti/NAG) | **Parziale** | `comment` esiste ma read-only; nessun NAG |
| Board-editor FEN / posizioni tematiche | **Parziale** | `startFen` nello schema, ma entra solo via header PGN |
| Riorganizzazione (sposta corso, rename corso, merge capitoli) | **Parziale** | solo `set_chapter`/`rename_chapter` |
| Eval bar / linee motore | **Manca** | nessun motore; `stockfish` assente dal PATH |
| Blunder-check del repertorio | **Manca** | — |
| Explorer master/DB (frequenze, win%) | **Manca** | solo link `analyzeOnLichess()` |
| Database di partite di consultazione | **Manca** | PGN multi-game distrutto in varianti SRS lossy |
| Merge partite in albero / SQLite scala | **Manca** | — |

---

## 2. Correzioni preliminari (bug confermati — DA FARE PRIMA)

Verificati nel codice. Tutti in `app.py` (= **restart**) tranne XSS (`templates/index.html`).

### 2.1 [MEDIUM] SM-2 errato: lapse non azzera la ripetizione
`app.py:61-68`. Nel ramo `quality < 3` viene impostato `rep = 1` invece di `rep = 0`. Conseguenza: il primo successo dopo un errore salta a `interval = 6` (ramo `rep == 1`) invece di ripartire da `interval = 1`. Il materiale sbagliato torna troppo tardi.

```diff
     if quality < 3:
-        rep = 1
+        rep = 0
         interval = 0
```
Così il primo successo post-lapse passa per `if rep == 0: interval = 1`.

### 2.2 [LOW] Migrazione lazy non ripristina `srs`/`next_review` → KeyError su dati editati a mano
`app.py:~180-201`. Il loop di migrazione backfilla solo `chapter` e `stats`, mai `srs`. Una variante editata a mano senza `srs` (o senza `next_review`) fa **KeyError** a riga 199/201 → `/api/due` va in 500 → tutte le viste falliscono il caricamento.

```diff
     for vdata in data.values():
         if 'chapter' not in vdata:
             vdata['chapter'] = derive_chapter(vdata.get('title', ''))
             dirty = True
         if 'stats' not in vdata:
             vdata['stats'] = default_stats()
             dirty = True
+        srs = vdata.get('srs')
+        if not isinstance(srs, dict) or 'next_review' not in srs:
+            vdata['srs'] = {'rep': 0, 'interval': 0, 'ease': 2.5,
+                            'next_review': datetime.now().isoformat()}
+            dirty = True
```

### 2.3 [MEDIUM] Stored XSS: commenti/header PGN iniettati raw in `.html()`
`templates/index.html` — commenti a :829, 965, 980, 1027, 1131; course/chapter/title a :491, 506, 520. `esc()` (riga 464) sostituisce SOLO l'apice singolo (contesto stringa-JS), NON fa escaping HTML. Il PGN importato finisce raw in `.html()`: un commento `<img src=x onerror=...>` esegue. App locale, ma il PGN può venire da terzi.

```js
function escHtml(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
```
- `comment` → `escHtml(comment)` **prima** di `parseCommentMoves` (i SAN restano ASCII: i match continuano a funzionare; `parseCommentMoves` va chiamata DOPO l'escape, mai prima).
- `course` / `chapter` / `v.displayTitle` / `v.title` → `escHtml(...)` nei template a :491/506/520.

Alternativa: escape lato server in `app.py` all'import. Preferibile l'escape client (nessun restart, copre anche dati già salvati).

---

## 3. Roadmap in FASI

Ordinata per punteggio giudici e rapporto impatto/effort. Verdetti chiave: **trie del repertorio 9/9/9/9**, **rilevatore trasposizioni 9/8/9**, **dashboard stats estesa 9/8/8**, **riordino capitoli 9/6/7**, **eval-bar WASM 8/8/8/8**, **annotazione NAG 8/8/7**.

### FASE A — Fondamenta e quick-win (basso effort, alto/medio valore, zero rischio dati)

#### A1. Riordino albero: sposta corso, rename corso, merge capitoli — **S/M**
- **Cosa**: `/api/set_course`, `/api/rename_course`, `/api/merge_chapter`.
- **CB**: spostare/rinominare/riorganizzare la gerarchia del database.
- **Impl**: clone 1:1 di `set_chapter` (`app.py:~310`) e `rename_chapter` (`~322`); iterazione sul dict piatto + `save_data` atomico. **ID stabile, nessun re-keying, nessuna migrazione.** Frontend: menu contestuale su `.var-item`/intestazioni corso riusando `editVarChapter`/`renameChapter` (`~578-600`).
- **Dipendenze**: nessuna. **Restart**.
- **Vincoli**: solo campi `course`/`chapter`. Non sfiora i comment. Cura: non orfanare i default ("Varie"/"Generale").

#### A2. Dashboard statistiche estesa: retention, accuracy per corso/colore, forecast — **M**
- **Cosa**: breakdown per `course` e per `perspective` (colore), retention rate (`quality>=3`/totali), curva da `stats.history`, forecast SRS per corso.
- **CB**: dashboard performance per apertura / retention.
- **Impl**: estendere `/api/stats` (già itera tutte le varianti). Aggiungere `by_course`, `by_color`, `retention_series` (bucket per giorno da `v['stats']['history']`). Frontend: `renderStats()` (`~620-640`), riuso `.hard-row` + barre CSS.
- **Dipendenze**: nessuna. Zero migrazioni (`.get` difensivo). **Restart**.
- **Vincoli**: metriche da dati di review. Conforme. Limite noto: `history` cappata a 20 voci → curva approssimata sul recente.

#### A3. Annotazione utente: commenti editabili + NAG per mossa — **M**
- **Cosa**: editing del `comment` (100% utente) + palette NAG fissa.
- **CB**: campo commento per mossa + palette simboli (!, ?, !?, +-, =).
- **Impl**: campo additivo `moves[i].nags = [int]` (default `[]`, nessuna migrazione). Palette statica client: `{1:'!',2:'?',3:'!!',4:'??',5:'!?',6:'?!',10:'=',14:'+/=',16:'+/-',18:'+-'}` (numeri NAG standard, **non** testo generato). Render: `.san-link` + simboli nell'`#annotation-box`. Persistenza via `/api/save_variation` (B4).
- **Dipendenze**: B4. **Restart** (con B4).
- **Vincoli**: commento SOLO utente, NAG manuali. **VIETATO** auto-suggerire simboli/eval.

> A1+A2 indipendenti e spedibili subito. A3 si appoggia all'authoring di Fase B.

---

### FASE B — Esploratore + gestione repertorio/database (cuore ChessBase-like)

#### B1. Albero del repertorio (trie di posizioni navigabile) — **L** — *PRIMITIVA ABILITANTE (top score)*
- **Cosa**: `/api/tree` che unisce TUTTE le varianti (o di un corso) in un trie: per ogni posizione, mosse-figlie con `count`, `san`, `comment` se presente, `sample_var_id`. Nuova vista **"Esplora"**: scacchiera + pannello continuazioni ordinate per frequenza, breadcrumb, click per avanzare.
- **CB**: Opening Tree / Reference / Repertoire.
- **Impl**: riusa il board-walk di `search_position` (`chess.Board` + `push_uci` su `moves[]`). Chiave posizione = `board.fen()` piece-placement + tratto + castling + ep (escludere halfmove/fullmove). Param `path` per spedire solo il sotto-albero. **Cache a livello modulo invalidata su `os.path.getmtime(repertoire.json)`.** Frontend: nuova `<section id="view-explore">`, riuso Chessboard + chess.js.
- **Dipendenze**: nessuna. **Restart**.
- **Vincoli**: conta percorsi/mosse, zero prosa. Conforme.

#### B2. Rilevatore di trasposizioni + conflict-flag — **M** — *sottoprodotto quasi gratuito di B1*
- **Cosa**: stessa `pos_key` raggiunta da varianti DIVERSE → trasposizione. `/api/transpositions` ritorna `{pos_key, reached_by:[...], conflict}`. `conflict=true` se i set di uci-figli divergono (= mosse diverse dalla stessa posizione = incoerenza).
- **CB**: Transposition detection / merge per posizione.
- **Impl**: accumulo `reached_by` nel trie di B1. Chiave compatta via `chess.polyglot.zobrist_hash(board)`. Distinguere conflitto VERO da foglia che finisce prima.
- **Dipendenze**: B1. **Restart**. **Vincoli**: solo dati numerici/booleani. Conforme.

#### B3. Copertura del repertorio (buchi / foglie premature) — **M**
- **Cosa**: per ogni nodo-AVVERSARIO del trie, segnala foglie premature (linea che finisce mentre tocca all'avversario in apertura). Flag `is_hole`. Contatore "N buchi in questo corso".
- **CB**: Repertoire coverage / opening report.
- **Impl**: sopra il trie B1. Chi muove da `turn` vs `perspective`. `legal_moves` per enumerare. Frontend: highlight rosso sui nodi-buco.
- **Dipendenze**: B1; potenza piena con C3 (frequenze). **Restart**. **Vincoli**: enumerazione legale ammessa. Limite: senza frequenze è rumoroso → limitare a "foglie premature".

#### B4. Editor di variante sulla board + `/api/save_variation` — **L** — *unico endpoint di scrittura mancante*
- **Cosa**: modalità EDIT in Repertorio: dalla posizione iniziale/`startFen` trascini i pezzi, ogni mossa legale si appende a `moves[]`. Undo/redo, troncamento, salva.
- **CB**: Enter/Insert moves nella notation.
- **Impl**: riusa `board`/`onDrop`/`game`/`replayTo`. `/api/save_variation` ri-valida ogni `uci` con `push_uci` (rifiuta su `IllegalMoveError`), ricalcola `san` server-side. **PUNTO CRITICO — re-keying**: `var_id = md5(startFen+uci)[:10]` cambia editando le mosse → ricomputare hash, **trasferire `srs`/`stats`, `del` della vecchia chiave, policy collisione**. `save_data` atomico esistente.
- **Dipendenze**: nessuna libreria nuova. Abilita A3. **Restart**.
- **Vincoli**: commenti SOLO utente. Rischio dati più alto della roadmap (invariante di identità) → test attento sul re-keying.

#### B5. Board-editor FEN (posizione di partenza) — **M**
- **Cosa**: pannello "Imposta posizione" con `sparePieces` per finali/tattica/posizioni tematiche.
- **CB**: Setup Position.
- **Impl**: chessboard.js v1.0.0 supporta **nativamente** `sparePieces:true` + `dropOffBoard:'trash'`. Validazione server `chess.Board(fen)` + `is_valid()` prima di salvare via `/api/save_variation`.
- **Dipendenze**: B4. **Restart**. **Vincoli**: setup posizione. Conforme. Limite: castling/ep non deducibili dai soli pezzi → default o campo manuale.

#### B6. Database di partite (`games.json`) + viewer ad albero + "Aggiungi linea al repertorio" — **M + L**
- **Cosa**: store SEPARATO `games.json` keyed `game_hash` con headers + **PGN GREZZO integrale** + derivati (`ply_count`, `opening`). `/api/games/import`, `/api/games/list` (filtri player/ECO/evento/risultato/Elo/data, paginazione). Viewer che naviga il PGN COMPLETO incluse diramazioni; bottone **"Aggiungi al repertorio"** che passa il PGN della linea a `/api/import` ESISTENTE.
- **CB**: aprire un .cbh, Lista partite con filtri, promuovere una linea.
- **Impl**: factory `load_store(path)`/`save_store(path)` dal pattern atomico di `load_data`/`save_data`. **Niente SRS, niente flatten** nel DB. Ponte = unico punto in cui un game entra nel flusso SRS.
- **Dipendenze**: nessuna libreria nuova. **Restart**. **Vincoli**: conserva PGN grezzo. Rischio: file cresce → alzare `MAX_CONTENT_LENGTH` (8MB stretto) o chunk; oltre ~3-5k partite → SQLite (C5).
- **Priorità interna**: prima store+import+list (M), poi viewer+ponte (L, il vero cuore CB-like).

---

### FASE C — Motore + avanzate

#### C1. Eval Bar + Live Engine Lines (Stockfish WASM) — **M** — *primitiva motore (no restart)*
- **Cosa**: barra di valutazione + pannello 2-3 linee principali (depth, eval cp/mate, PV in SAN) in LEARN/REVIEW/analisi. Solo numeri + sequenze.
- **CB**: eval bar + engine pane.
- **Impl**: self-hostare `stockfish.js`+`stockfish.wasm` in `static/js/` (build **single-thread** → niente header COOP/COEP → niente restart). Web Worker protocollo UCI; `analyzeFen(fen)` con debounce ~300ms agganciata all'update board. eval-bar = div CSS. PV UCI→SAN con chess.js. **Nessuna modifica `app.py`.**
- **Dipendenze**: asset WASM (~1-7MB) self-hostati. **Vincoli**: eval/PV solo in UI on-the-fly. **MAI** in `moves[].comment`.

#### C2. Engine-assisted Review check (post-tentativo) — **S**
- **Cosa**: in REVIEW, DOPO l'autovalutazione, bottone opt-in "Verifica col motore": eval della tua mossa vs top del motore.
- **Impl**: toggle che chiama `analyzeFen(game.fen())` (C1) o legge `analysis_cache.json` (C4). Gating: MAI prima dello svelamento.
- **Dipendenze**: C1 (o C4). **Vincoli**: solo numeri/SAN in UI. Opt-in e post-tentativo.

#### C3. Lichess Opening Explorer (frequenze master/DB) — **M**
- **Cosa**: dalla posizione in Esplora, statistiche da `explorer.lichess.ovh` (master/lichess) accanto alle continuazioni del repertorio. Pesa i buchi di B3.
- **CB**: Online Database / LiveBook.
- **Impl**: **client-side** (`fetch`, CORS ok) → zero dipendenze Python. Degrada con grazia offline. Gestire 429/cache.
- **Dipendenze**: B1. Rete OPZIONALE. **Vincoli**: statistiche da DB esterni AMMESSE, restano UI.

#### C4. Repertoire Blunder-Check (batch col motore) — **L** — *killer-feature, alto setup*
- **Cosa**: scansiona le varianti; per ogni mossa DAL TUO LATO confronta eval mossa-repertorio vs migliore. Drop > soglia = mossa dubbia. Lista navigabile.
- **CB**: Blunder check / Full analysis su tutto il repertorio.
- **Impl**: `/api/analyze_blunders` con polling (progress/cancel). `chess.engine.SimpleEngine.popen_uci(path)`, path da env `OPENREP_ENGINE`; `analyse(board, Limit(depth=16), multipv=2)`. Cache in **`analysis_cache.json`** keyed `var_id+fen-hash`, **MAI in repertoire.json**. Binario mancante → 503 + fallback WASM.
- **Dipendenze**: binario Stockfish UCI (**oggi ASSENTE dal PATH**) o fallback C1. **Restart**. **Vincoli**: output numerico in store separato. Soglia cp parametrica (falsi positivi nelle linee taglienti).

#### C5. Migrazione opzionale a SQLite (solo DB partite, oltre soglia) — **XL** — *solo se il corpus esplode*
- Oltre ~3000 partite, backend opzionale `games.db` (`sqlite3` stdlib) dietro la stessa interfaccia store. `repertoire.json` **resta JSON**. Giudici 3/2/3 → **NON ora**.

---

## 4. Decisioni tecniche chiave

**(a) Motore — WASM browser vs binario UCI server** → **IBRIDO, default WASM.** C1 (eval-bar live) interamente WASM client-side: zero modifiche `app.py`, offline, non richiede il binario assente dal PATH. Build **single-thread** (no COOP/COEP). Binario UCI server SOLO per C4 (batch), opzionale via env `OPENREP_ENGINE`, degrado 503→WASM. **Output motore mai nei comment.**

**(b) Explorer — dati propri vs Lichess** → **Prima i dati propri (trie B1), poi Lichess come overlay opzionale (C3).** B1 dà l'explorer del TUO repertorio senza rete. C3 additivo client-side, ammesso, ma deve degradare con grazia. Mai proxy server obbligatorio.

**(c) Quando JSON → SQLite** → **Mai per `repertoire.json`** (<500-600 varianti, in-memory ideale). SQLite SOLO per `games.json` (B6) e SOLO oltre ~3000 partite. Trigger misurabile (latenza/size), non a priori.

**(d) Chiave trasposizioni** → **`chess.polyglot.zobrist_hash(board)`** per i dict del trie; FEN normalizzato (piece-placement + tratto + castling + ep, **escluso** halfmove/fullmove) come definizione semantica. **Includere** castling/ep (più corretto, evita falsi merge). Zobrist di python-chess li codifica già.

---

## 5. Rischi e vincoli

- **Re-keying (B4)** — rischio dati più alto: `var_id` cambia editando le mosse. Trasferire `srs`/`stats`, gestire collisioni, validare server-side. Le feature read-only (B1/B2/B3, A2) e a ID stabile (A1) NON hanno questo rischio.
- **Performance trie/walk** — ricostruzione O(varianti × lunghezza) per richiesta. **Cache obbligatoria su `getmtime(repertoire.json)`** (import/delete invalidano). A <500 varianti trascurabile.
- **Rete (C3)** — offline-first: Lichess SOLO opzionale, degrado graceful, rate-limit gestito.
- **Setup binario motore (C4)** — assente oggi: 503 + istruzioni + fallback WASM, mai crash.
- **Crescita `games.json` (B6)** — PGN grezzo gonfia il file; `MAX_CONTENT_LENGTH` 8MB stretto → alzare o chunk.
- **Conflitto vero vs benigno (B2/B3)** — linea che finisce prima ≠ conflitto/buco: distinguere figlio-mancante-per-fine da incoerenza.
- **`stats.history` cappata a 20 (A2)** — retention approssimata; aumentare il cap se serve storico.
- **VINCOLO 1 (inviolabile)** — nessuna feature scrive testo generato nei `moves[].comment`. Eval/PV/frequenze/mosse-legali/NAG numerici vivono in UI on-the-fly o store separati. Parsing "Altra opzione:" **READ-ONLY**. Palette NAG manuale, **mai** auto-suggerita.
- **VINCOLO 3** — le voci "Restart" toccano `app.py` (template/CSS bastano refresh).

---

## Sequenza consigliata (impatto/effort decrescente)

`Bug 2.1/2.2/2.3` → **A1** + **A2** → **B1** trie (abilitante) → **B2** trasposizioni (quasi gratis) → **B4** editor+`save_variation` → **A3** NAG → **B3** buchi → **C1** eval-bar WASM → **B5** FEN-editor → **B6** games DB → **C2** review-check → **C3** Lichess → **C4** blunder-check → **C5** SQLite (solo se necessario).
