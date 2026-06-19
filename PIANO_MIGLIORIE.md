# openrepertoire — Review + Piano migliorie

_Run schedulato 2026-06-19 04:00. Pesato sul grafico, con sezione tecnica. Rispetta i vincoli: no testo generato nelle varianti; pezzi Wikipedia PNG default (selettore set ok)._

---

## 1. Review funzionale (cosa c'è e cosa funziona)

Trainer SRS stile Chessable. Stack: Flask + python-chess (`app.py`), storage `repertoire.json` (atomico + `.bak`), frontend single-file `templates/index.html` (jQuery + chessboard.js + chess.js), CSS estratto in `static/css/app.css`.

**Funziona (verificato a codice):**
- Import PGN → albero corso/capitolo/variante; solo mainline, diramazioni ripiegate come testo nei commenti; dedup md5; skip game con mosse illegali (try/except); FEN di partenza (tattica) + perspective `auto` dal tratto.
- SRS SM-2 server-side; `/api/review` aggiorna stats + history (ultime 20); migrazione lazy dei campi mancanti.
- 4 viste: Impara / Repertorio / Ripassa / Statistiche.
- Training: LEARN → CONSOLIDATE → REVIEW_ERRORS (3 cicli); REVIEW con 4 bottoni autovalutazione + intervallo previsto + storico.
- Read mode, preview alternative (SAN cliccabili nei commenti), ricerca posizione per FEN, stats (KPI + forecast 14gg + varianti più difficili).
- Tema chiaro/scuro, 4 temi scacchiera, slider dimensione (height-aware), salvataggio atomico+bak.

---

## 2. Bug / debito trovati (file:riga)

**Codice morto (orfano dopo il redesign con topnav — riferisce elementi che non esistono più):**
- `initResizer()` [index.html:1245] + CSS `#sidebar`/`#resizer` [app.css:49-51] — mai chiamato, nessun elemento.
- `loadDueVariations` scrive `#learn-count`/`#review-count` [index.html:519-520] — elementi inesistenti (c'è solo `#rep-count`).
- `initShuffle()`/`toggleShuffle()` + `#shuffle-review` [index.html:1269,502] — nessuna checkbox nel DOM.
- `$('#stats-modal').on('click')` + `closeStats()` [index.html:1274,574] — stats è una vista, non più modale.
- CSS morto: `.sponsor-*` [57-64], `#main` [52], `.hamburger`/`#overlay` [157-158], `.modal-*` [160-164].

**Gap UX/visivi:**
- Slider dimensione scacchiera sepolto in Repertorio → "Personalizza Grafica": regola la board di *training* che non vedi mentre la regoli. Disconnesso.
- Stili inline ovunque nell'HTML generato da JS (status/annotation/summary/quality) — difficili da tematizzare, incoerenti col design-token system.
- Mobile: CSS `.hamburger` esiste ma nessun elemento nav; la topnav va solo a capo. Incompleto.
- Type piccola (`--fs-xs 11px`, bar-lab 9px), stati solo-colore, `div` con `onclick` senza ruolo/tastiera → accessibilità.
- `#annotation-box` altezza `calc(100vh-150px)` fissa, slegata dall'altezza board → colonna destra può risultare sbilanciata.

**Tecnici:**
- **Stored XSS**: commenti PGN e header (course/title/chapter) iniettati via `.html()`/append senza escape HTML [renderList 477-484, parseCommentMoves, annotation/summary]. `esc()` scappa solo `'` per gli onclick. Locale mono-utente → rischio basso ORA, ma blocca condivisione sicura / import PGN non fidati.
- Nessun test (pytest). Template monolitico 1293 righe (JS+HTML+stili inline).
- `predictInterval` (client) duplica `update_srs` (server) → rischio drift.

---

## 3. Piano migliorie (prioritizzato — grafica prima)

### P0 — Quick win grafici ✅ FATTO 2026-06-19 (verificato in preview)
1. **Slider board accessibile durante il training**: spostare/duplicare "Dimensione scacchiera" come controllo discreto nella vista train (es. mini-slider o `+/–` sotto la board), così si regola guardando. [index.html:113, applyBoardSize]
2. **Pulizia codice morto** (riduce ~80 righe, niente regressioni): rimuovere `initResizer`, `#sidebar`/`#resizer`, `#learn/#review-count` writes, `initShuffle/toggleShuffle/#shuffle-review`, `#stats-modal`/`closeStats`, CSS `.sponsor-*`/`#main`/`.hamburger`/`#overlay`/`.modal-*`.
3. **Colonna destra bilanciata**: legare l'altezza di `#annotation-box`/`#right-col` all'altezza reale della board (JS in `applyBoardSize`) invece di `calc(100vh-150px)`.
4. **Status come "card" coerente**: convertire i blocchi inline (Corretto!/Sbagliato!/tocca a te) in classi CSS con i token (`--accent-green/red`), invece di `style=` inline. Più pulito e tematizzabile.

### P1 — Migliorie grafiche strutturali (med effort) — 5/6/8/9 ✅ FATTO 2026-06-19 (verificato preview); 7 ⛔ BLOCCATO (asset)
5. ✅ **De-inline degli stili JS**: estratti i `style="..."` di read/learn/miss/summary/quality/search in classi CSS (`.read-text`/`.rd-move`/`.san-link.is-current|future|past`/`.learn-prompt`/`.miss-prompt`/`.summary-moves`/`.q-grid`/`.qbtn.q-*`/`.preview-alert`/`.anno-*`); colori hardcoded (`#888`/`#6f6f6f`/`#5a5a5a`/`#ff9f43`/`#c07d2e`/`#3692e7`/`#ffcccc`) → token. `style=` 50→19 (resto funzionale/dinamico). Tema chiaro ora corretto su tutte le superfici.
6. ✅ **Mobile**: deciso topnav (hamburger già rimosso in P0); su `@820` nav full-width compatta. (Non verificato visivamente: il preview clampa innerWidth a ~980.)
7. ✅ **Selettore set pezzi** (sbloccato nel REVAMP 2026-06-19): scaricati cburnett/staunty/merida (SVG, lichess) in `static/img/chesspieces/`; `#piece-set-select` + `pieceThemeFn`/`changePieceSet` (destroy+recreate board); default **cburnett**, Wikipedia selezionabile.

### REVAMP UI techy ✅ FATTO 2026-06-19 (richiesta utente; verificato preview dark+light, 3 sezioni)
- **Palette techy**: dark slate blu-nero, accenti blu elettrico/ciano/viola; light "blueprint" cool; raggi più netti; nuovi token glass/accent.
- **Floating box "vetro"**: pannelli translucidi + `backdrop-filter` (board-card, annotation, panel-box, train-sidebar, topbar, modal, empty-state); shadow crisp + hairline blu; topgrad/logo gradiente blu→ciano→viola.
- **Set pezzi SVG** (cburnett default, staunty, merida) + **2 board tech** (slate, blue).
- Solo template+CSS+asset, **no app.py** → basta refresh. Funzioni (board/chat/selettore varianti) intatte.
8. ✅ **Polish stats**: barre con `title` tooltip (data estesa + conteggio) + hover brightness; `.bar-lab` 9→10px.
9. ✅ **A11y base**: `@media (prefers-reduced-motion: reduce)`; `role=button`+`tabindex`+handler Invio sui toggle (course/chapter/panel/h2) e su var-item (solo repertorio) + search-hit. Var-item della sidebar sessione lasciati senza tabindex (eviterebbero 569 tab-stop → roving tabindex = follow-up).

### P2 — Tecnici (abilitano il resto)
10. **Fix XSS (prerequisito a qualsiasi condivisione/import non fidato)**: helper `escapeHtml()` su tutti i contenuti utente/PGN prima dell'iniezione (course/title/chapter/comment). Mantenere `parseCommentMoves` ma escapando il testo non-SAN.
11. **Smoke test pytest**: import PGN (incl. game illegali → skip), `/api/due`, `/api/review` (validazione quality), round-trip save/load+`.bak`. Blinda i refactor grafici.
12. **Split del template**: estrarre il blocco `<script>` in `static/js/app.js`. Stesso vantaggio di app.css: design tool/refactor senza toccare il markup.
13. **Single source SRS**: o `predictInterval` deriva da un endpoint, o documentare che è una replica e testarne la parità.

---

## 4. Sequenza consigliata
P0 (2→3→4→1) in una sessione verificata in preview → P1 (5 sblocca 8/4) → P2 (10 prima di condividere; 11 a guardia). Allineato a [[openrepertoire-improvement-roadmap]] Fase 1/2.
