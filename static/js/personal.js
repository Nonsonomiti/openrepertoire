// ===== AREA PERSONALE =====
// Le funzioni che non partono da un corso: le tue partite (Lichess / Chess.com) contro il repertorio,
// l'avversario da preparare, il repertorio costruito dal database, lo sparring, i finali contro la
// tablebase. In fondo l'accesso dal telefono. Usa scacchiera e helper di index.html (makeBoard,
// cgPosition, cgMovable, playUci, sanToUci, escHtml, esc, showToast, uiConfirm, openEditor...).
// Vincolo del progetto: nelle varianti non si scrive testo; numeri e nomi delle aperture restano qui.

// ---------- utilita' comuni ----------
function pxPost(url, body) {
    return $.ajax({ url: url, type: 'POST', contentType: 'application/json', data: JSON.stringify(body || {}) });
}
function pxGame(path) { let g = new Chess(); (path || []).forEach(function(u) { playUci(g, u); }); return g; }
function pxLabel(ply, san) { return (ply % 2 === 0 ? (ply / 2 + 1) + '.' : (Math.floor(ply / 2) + 1) + '...') + san; }
function pxSans(path) {   // ["e2e4","e7e5"] -> "1. e4 e5"
    let g = new Chess();
    return (path || []).map(function(u, i) {
        let mv = playUci(g, u);
        return (i % 2 === 0 ? (i / 2 + 1) + '. ' : '') + (mv ? mv.san : u);
    }).join(' ');
}
function pxTail(path) {   // le ultime due mosse col numero: "5.Nf3 Nc6" / "5...Nc6 6.O-O"
    let g = new Chess(), sans = (path || []).map(function(u) { let mv = playUci(g, u); return mv ? mv.san : u; });
    let out = [];
    for (let i = Math.max(0, sans.length - 2); i < sans.length; i++) {
        out.push(i % 2 === 0 ? (i / 2 + 1) + '.' + sans[i] : (out.length ? '' : (Math.floor(i / 2) + 1) + '...') + sans[i]);
    }
    return out.join(' ');
}
function pxErr(code) {   // codici del server -> italiano (HTML)
    if (code === 'not_found') return 'Utente non trovato.';
    if (code === 'rate_limit') return 'Troppe richieste: il sito chiede di aspettare un minuto.';
    if (code === 'bad_token') return 'Token Lichess non valido: rimettilo da Corsi → Esplora → Database Lichess.';
    if (code === 'no_token') return 'Serve il token Lichess (gratuito): impostalo da Corsi → Esplora → Database Lichess.';
    if (code === 'ssl_cert') return dbErrMsg('ssl_cert');
    return 'Errore: <code>' + escHtml(String(code || '?')) + '</code>';
}
function pxBar(m) {   // vittorie Bianco / patte / vittorie Nero, come il database Lichess
    let g = m.games || 1;
    return '<span class="db-bar"><i class="db-w" style="width:' + (100 * m.white / g) + '%"></i><i class="db-d" style="width:' +
        (100 * m.draws / g) + '%"></i><i class="db-b" style="width:' + (100 * m.black / g) + '%"></i></span>';
}
function pxWhen(iso) {
    let d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleString('it-IT', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}
function pxGameRef(g) {   // "vs Rossi (1850) · 2026-09-12 · persa", col link alla partita
    let res = { win: 'vinta', draw: 'patta', loss: 'persa' }[g.result] || '';
    return '<a href="' + escHtml(g.url || '#') + '" target="_blank" rel="noopener" onclick="event.stopPropagation()">vs ' + escHtml(g.opp || '?') +
        (g.opp_rating ? ' (' + g.opp_rating + ')' : '') + '</a>' + (g.date ? ' · ' + g.date : '') + (res ? ' · ' + res : '');
}
// Database Lichess: livelli e cadenze come nel pannello di Esplora (stesse opzioni, valore ricordato)
function pxFillDbSelects() {
    $('.px-ratings, .px-speeds').each(function() {
        if (this.options.length) return;
        $(this).html($($(this).hasClass('px-ratings') ? '#db-ratings' : '#db-speeds').html());
        let saved = lsGet(this.id);
        if (saved && $(this).find('option[value="' + saved + '"]').length) this.value = saved;
    });
}
$(document).on('change', '.px-ratings, .px-speeds', function() { lsSet(this.id, this.value); });
function pxBoard(id, onMove) {
    let cg = makeBoard(id, onMove);
    extraBoards.push(cg);
    changeBoardTheme();
    return cg;
}
// La risposta che manca, da preparare nell'editor: la linea arriva gia' giocata fino alla mossa
// dell'avversario e va in un corso tuo (i corsi importati restano com'erano).
function pxPrepare(x, color, back) {
    openEditor(null, { moves: x.path, perspective: color, course: 'Il mio repertorio', chapter: x.course || '',
                       title: 'Risposta a ' + x.move, back: back });
}

// Scacchiera navigabile (Partite, Avversario, Costruisci): percorso di mosse, avanti/indietro, frecce
function pxNav(id, onChange) {
    let el = document.getElementById(id);
    let nav = { path: [], fwd: [], game: new Chess(), orient: 'white', top: null, base: [] };
    nav.board = pxBoard(id, function(orig, dest) {
        let mv = nav.game.move({ from: orig, to: dest, promotion: 'q' });
        if (!mv) { nav.sync(false); return; }
        playMoveSound(mv);
        nav.path.push(mv.from + mv.to + (mv.promotion || ''));
        nav.fwd = [];
        nav.sync();
        onChange();
    });
    nav.sync = function(animate) {
        nav.game = pxGame(nav.path);
        cgPosition(nav.board, nav.game, nav.path[nav.path.length - 1], animate);
        cgMovable(nav.board, nav.game, turnColor(nav.game));
        nav.setBase([]);
    };
    nav.go = function(uci) { if (!uci) return; nav.path.push(uci); nav.fwd = []; nav.sync(); onChange(); };
    nav.goPath = function(p) { nav.path = (p || []).slice(); nav.fwd = []; nav.sync(false); onChange(); };
    nav.back = function() { if (!nav.path.length) return; nav.fwd.push(nav.path.pop()); nav.sync(); onChange(); };
    nav.forward = function() {   // redo, altrimenti la continuazione piu' comune
        let u = nav.fwd.length ? nav.fwd.pop() : nav.top;
        if (!u) return;
        nav.path.push(u); nav.sync(); onChange();
    };
    nav.reset = function() { nav.goPath([]); };
    nav.setOrient = function(o) { nav.orient = o; nav.board.set({ orientation: o }); };
    nav.flip = function() { nav.setOrient(nav.orient === 'white' ? 'black' : 'white'); };
    // forme su una board nascosta = misure zero: si mettono solo se si vede
    nav.setBase = function(shapes) { nav.base = shapes || []; if (el.offsetWidth || !nav.base.length) nav.board.setAutoShapes(nav.base); };
    nav.hover = function(uci) {
        if (el.offsetWidth) nav.board.setAutoShapes(uci && uci !== '0000' ? nav.base.concat([moveArrow(uci, 'paleBlue')]) : nav.base);
    };
    return nav;
}

// Righe "da questa posizione" (partite tue o dell'avversario) confrontate col repertorio:
// ✓ nel repertorio · ✗ tua mossa fuori repertorio · ⚠ risposta dell'avversario non coperta
function pxTreeRows(t, who, markMine) {
    let rep = {}, hasRep = (t.rep || []).length > 0;
    (t.rep || []).forEach(function(r) { rep[r.uci] = true; });
    let tot = t.moves.reduce(function(a, m) { return a + m.games; }, 0) || 1;
    let rows = t.moves.map(function(m) {
        let mark = !hasRep ? '' : (rep[m.uci] ? '<span class="db-ok" title="Nel repertorio">✓</span>'
                 : (!t.mine ? '<span class="db-gap" title="Nessuna risposta preparata">⚠</span>'
                 : (markMine ? '<span class="px-bad" title="Fuori repertorio">✗</span>' : '')));
        return '<div class="exp-move" onclick="' + who + '.nav.go(\'' + m.uci + '\')" onmouseenter="' + who + '.nav.hover(\'' + m.uci +
            '\')" onmouseleave="' + who + '.nav.hover()"><span class="exp-san">' + escHtml(m.san) + ' ' + mark + '</span>' + pxBar(m) +
            '<span class="exp-count">' + m.games + ' · ' + Math.round(100 * m.games / tot) + '%</span></div>';
    }).join('');
    let repLine = (t.mine && hasRep) ? '<div class="px-rep-line">Il tuo repertorio qui: ' + t.rep.map(function(r) {
        return '<span class="px-move" role="button" tabindex="0" onclick="' + who + '.nav.go(\'' + r.uci + '\')">' + escHtml(r.san) + '</span>';
    }).join(' · ') + '</div>' : '';
    return repLine + (rows || '<div class="empty-msg">Nessuna partita arriva qui.</div>');
}
function pxExitRows(exits, who, color, back) {
    return exits.map(function(x, i) {
        let g = x.games[0];
        return '<div class="px-item" role="button" tabindex="0" onclick="' + who + '.nav.goPath(' + who + '.report.exits[' + i + '].path.slice(0, -1))">' +
            '<div class="px-item-main"><b class="db-gap">' + escHtml(x.move) + '</b> · nessuna risposta preparata</div>' +
            pxAfter(x.path.slice(0, -1)) +
            '<div class="px-item-sub">' + x.count + (x.count === 1 ? ' partita' : ' partite') + (g ? ' · ultima ' + pxGameRef(g) : '') + '</div>' +
            '<button class="btn-delete px-act" onclick="event.stopPropagation(); pxPrepare(' + who + '.report.exits[' + i + '], \'' + color + '\', \'' + back +
            '\')" title="Prepara la risposta nell\'editor"><i class="ico i-plus"></i> Prepara</button></div>';
    }).join('');
}
function pxAfter(path) {   // il contesto di una voce: le mosse che portano alla posizione
    return path.length ? '<div class="px-item-sub px-after">dopo ' + escHtml(pxSans(path)) + '</div>' : '';
}
function pxKpis(list) {
    return list.map(function(k) { return '<div class="kpi"><div class="kpi-val">' + k[1] + '</div><div class="kpi-lab">' + k[0] + '</div></div>'; }).join('');
}

// =====================================================================================
// ---------- PARTITE: le tue partite contro il repertorio ----------
var gm = { nav: null, color: 'white', colorSet: false, report: null, req: 0, treeReq: 0 };
function openGames() {
    showView('games');
    setTimeout(function() {
        if (!gm.nav) gm.nav = pxNav('games-board', gmLoadTree);
        gmLoadState();
    }, 20);
}
function gmLoadState() {
    $.get('/api/personal/state', function(s) {
        let acc = s.accounts || [];
        let li = acc.find(function(a) { return a.site === 'lichess'; }), cc = acc.find(function(a) { return a.site === 'chesscom'; });
        if (li && !$('#acc-lichess').val()) $('#acc-lichess').val(li.name);
        if (cc && !$('#acc-chesscom').val()) $('#acc-chesscom').val(cc.name);
        $('#acc-list').html(acc.map(function(a) {
            return '<div class="px-acc"><span>' + (a.site === 'lichess' ? 'Lichess' : 'Chess.com') + ' · <b>' + escHtml(a.name) + '</b> · ' + a.count +
                ' partite' + (a.synced ? ' · aggiornato ' + pxWhen(a.synced) : '') + '</span><button class="btn-delete" onclick="gmRemove(\'' + esc(a.key) +
                '\')" title="Togli l\'account e le sue partite" aria-label="Togli l\'account"><i class="ico i-x"></i></button></div>';
        }).join(''));
        $('#acc-head').text(acc.length ? 'Account · ' + acc.map(function(a) { return a.name + ' (' + a.count + ')'; }).join(', ') : 'Account e download');
        let sel = $('#games-account'), cur = sel.val();
        sel.html('<option value="">Tutti</option>' + acc.map(function(a) {
            return '<option value="' + escHtml(a.key) + '">' + (a.site === 'lichess' ? 'Lichess' : 'Chess.com') + ' · ' + escHtml(a.name) + '</option>';
        }).join(''));
        if (acc.some(function(a) { return a.key === cur; })) sel.val(cur);
        let has = s.games > 0;
        $('#games-main').toggle(has);
        if (!has) { $('#acc-content').show(); return; }
        if (!gm.accFolded) { gm.accFolded = true; $('#acc-content').hide(); }   // a regime l'account sta chiuso
        if (!gm.colorSet) {   // il colore dell'ultima volta, o quello con piu' partite
            gm.colorSet = true;
            gm.color = lsGet('gamesColor') || ((s.by_color.black > s.by_color.white) ? 'black' : 'white');
            $('#games-color').val(gm.color);
        }
        gm.nav.setOrient(gm.color);
        gmReload();
    });
}
function gmSync() {
    let jobs = [['lichess', $('#acc-lichess').val().trim()], ['chesscom', $('#acc-chesscom').val().trim()]].filter(function(j) { return j[1]; });
    if (!jobs.length) { $('#acc-status').text('Scrivi almeno un nome utente.').css('color', 'var(--accent-red)'); return; }
    let max = parseInt($('#acc-max').val(), 10), msgs = [];
    gm.accFolded = true;   // dopo un download il pannello resta aperto: mostra com'e' andata
    $('#acc-sync').prop('disabled', true);
    let next = function() {
        let j = jobs.shift();
        if (!j) { $('#acc-sync').prop('disabled', false); $('#acc-status').html(msgs.join('<br>')).css('color', 'var(--text-dim)'); gmLoadState(); return; }
        let name = j[0] === 'lichess' ? 'Lichess' : 'Chess.com';
        $('#acc-status').text('Scarico da ' + name + '… (qualche secondo ogni cento partite)').css('color', 'var(--text-faint)');
        pxPost('/api/games/sync', { site: j[0], user: j[1], max: max, full: true })
            .done(function(r) {
                msgs.push(name + ': ' + (r.success
                    ? (r.added ? r.added + (r.added === 1 ? ' partita nuova' : ' partite nuove') : 'nessuna partita nuova') + ' · ' + r.count + ' in tutto' +
                      (r.error ? ' · interrotto: ' + pxErr(r.error) : '')
                    : pxErr(r.error)));
            })
            .fail(function() { msgs.push(name + ': il server non ha risposto.'); })
            .always(next);
    };
    next();
}
function gmRemove(key) {
    uiConfirm('Togliere l\'account e le sue partite scaricate?', { danger: true, okText: 'Togli' }).then(function(ok) {
        if (ok) pxPost('/api/games/remove', { key: key }).done(gmLoadState);
    });
}
function gmColorChanged() { gm.color = $('#games-color').val(); lsSet('gamesColor', gm.color); gm.nav.setOrient(gm.color); gmReload(); }
function gmReload() { gmLoadReport(); gm.nav.goPath([]); }
function gmLoadReport() {
    let my = ++gm.req;
    $('#games-devs, #games-exits').html('<div class="empty-msg">Confronto col repertorio…</div>');
    $.get('/api/games/report', { color: gm.color, account: $('#games-account').val() || '' }, function(r) {
        if (my !== gm.req) return;
        gm.report = r;
        let t = r.tally, pct = function(n) { return t.in_rep ? Math.round(100 * n / t.in_rep) + '%' : '—'; };
        $('#games-kpis').html(pxKpis([
            ['Partite col ' + (gm.color === 'white' ? 'Bianco' : 'Nero'), t.games],
            ['Rimaste nel repertorio fino alla fine della preparazione', pct(t.covered)],
            ['Volte che hai deviato tu', t.dev],
            ['Volte che l\'avversario è uscito', t.exit]
        ]));
        let other = r.other || [], nOther = other.reduce(function(a, o) { return a + o.count; }, 0);
        $('#games-other').html(nOther ? nOther + (nOther === 1 ? ' partita aperta' : ' partite aperte') + ' con un\'altra prima mossa, fuori dal repertorio: ' +
            other.map(function(o) { return '<b>' + escHtml(o.move) + '</b> ' + o.count; }).join(' · ') : '');
        $('#games-devs-n').text(r.devs.length || '');
        $('#games-devs').html(r.devs.length ? r.devs.map(function(d, i) {
            let g = d.games[0];
            return '<div class="px-item" role="button" tabindex="0" onclick="gm.nav.goPath(gm.report.devs[' + i + '].path)">' +
                '<div class="px-item-main">' + d.played.map(function(p) { return '<b class="px-bad">' + escHtml(p.move) + '</b>' + (p.count > 1 ? ' ×' + p.count : ''); }).join(', ') +
                ' invece di ' + d.expected.map(function(e) { return '<b class="db-ok">' + escHtml(e) + '</b>'; }).join(' o ') + '</div>' + pxAfter(d.path) +
                '<div class="px-item-sub">' + d.count + (d.count === 1 ? ' partita' : ' partite') + (g ? ' · ultima ' + pxGameRef(g) : '') + '</div>' +
                '<button class="btn-delete px-act" onclick="event.stopPropagation(); gmReviewDev(' + i + ')" title="Rimetti in ripasso le linee di questa posizione"><i class="ico i-clock"></i> Ripassa</button></div>';
        }).join('') : '<div class="empty-msg">Nessuna: dove il repertorio aveva una mossa, l\'hai giocata.</div>');
        $('#games-exits-n').text(r.exits.length || '');
        $('#games-exits').html(r.exits.length ? pxExitRows(r.exits, 'gm', gm.color, 'partite')
            : '<div class="empty-msg">Nessuna: gli avversari sono sempre rimasti nella tua preparazione.</div>');
    });
}
function gmReviewDev(i) {
    let d = gm.report.devs[i];
    pxPost('/api/review_now', { ids: d.var_ids }).done(function(r) {
        showToast(r.count ? r.count + (r.count === 1 ? ' linea da ripassare adesso (Corsi → Ripassa)' : ' linee da ripassare adesso (Corsi → Ripassa)')
                          : 'Le linee di questa posizione sono già da ripassare.', r.count ? 'success' : null);
        loadDueVariations();
    });
}
function gmLoadTree() {
    let my = ++gm.treeReq;
    $('#games-crumb').text(gm.nav.path.length ? pxSans(gm.nav.path) : 'Posizione iniziale');
    pxPost('/api/games/tree', { color: gm.color, account: $('#games-account').val() || '', path: gm.nav.path }).done(function(t) {
        if (my !== gm.treeReq) return;
        gm.nav.top = t.moves.length ? t.moves[0].uci : null;
        gm.nav.setBase(t.mine ? t.rep.map(function(r) { return moveArrow(r.uci, 'green'); }) : []);
        $('#games-moves').html(pxTreeRows(t, 'gm', true));
    });
}

// =====================================================================================
// ---------- AVVERSARIO: le sue partite contro il tuo repertorio ----------
var op = { nav: null, key: null, color: 'white', report: null, treeReq: 0 };
function openOpponent() {
    showView('opp');
    setTimeout(function() {
        if (!op.nav) {
            op.nav = pxNav('opp-board', opLoadTree);
            $('#opp-color').val(lsGet('oppColor') || dominantPerspective());
        }
        opLoadRecent();
    }, 20);
}
function opLoadRecent() {
    $.get('/api/personal/state', function(s) {
        $('#opp-recent').html((s.opponents || []).map(function(o) {
            return '<button class="px-chip" onclick="opPick(\'' + esc(o.site) + '\', \'' + esc(o.name) + '\')">' + escHtml(o.name) +
                ' <span>' + (o.site === 'lichess' ? 'Lichess' : 'Chess.com') + ' · ' + o.n + '</span></button>';
        }).join(''));
    });
}
function opPick(site, name) { $('#opp-site').val(site); $('#opp-user').val(name); opScan(false); }
function opColorChanged() { lsSet('oppColor', $('#opp-color').val()); if (op.key) opScan(false); }
function opScan(refresh) {
    let user = $('#opp-user').val().trim();
    if (!user) { $('#opp-status').text('Scrivi il nome utente.').css('color', 'var(--accent-red)'); return; }
    op.color = $('#opp-color').val();
    $('#opp-status').text('Scarico e analizzo le sue partite…').css('color', 'var(--text-faint)');
    pxPost('/api/opponent/scan', { site: $('#opp-site').val(), user: user, max: parseInt($('#opp-max').val(), 10), color: op.color, refresh: !!refresh })
        .done(function(r) {
            if (!r.success) { $('#opp-status').html(pxErr(r.error)).css('color', 'var(--accent-red)'); return; }
            op.key = r.key; op.report = r;
            $('#opp-status').html('Partite scaricate ' + pxWhen(r.fetched) + ' · <span class="sfn-clear" role="button" tabindex="0" onclick="opScan(true)">riscarica</span>' +
                ' · <span class="sfn-clear" role="button" tabindex="0" onclick="opRemove()">dimentica</span>').css('color', 'var(--text-faint)');
            $('#opp-main').show();
            opRender(r);
            op.nav.setOrient(op.color);
            op.nav.goPath([]);
            opLoadRecent();
        });
}
function opRemove() {
    pxPost('/api/opponent/remove', { key: op.key }).done(function() {
        op.key = null; op.report = null;
        $('#opp-main').hide(); $('#opp-status').text('');
        opLoadRecent();
    });
}
function opRender(r) {
    let theirs = op.color === 'white' ? 'Nero' : 'Bianco', n = r.games, s = r.score, cov = r.coverage;
    let pct = function(x, tot) { return (tot ? Math.round(100 * x / tot) : 0) + '%'; };
    let html = '<div class="px-sum-h"><b>' + escHtml(r.name) + '</b> col ' + theirs + ': ' + n + (n === 1 ? ' partita' : ' partite') + ' (su ' + r.total + ' scaricate)';
    if (n) html += ' · vince il ' + pct(s.win, n) + ', patta il ' + pct(s.draw, n) + ', perde il ' + pct(s.loss, n);
    html += '</div>';
    if (!n) html += '<div class="empty-msg">Nessuna partita col ' + theirs + ': prova l\'altro colore o scarica più partite.</div>';
    if (r.openings.length) html += '<div class="px-sum-row">Gioca soprattutto: ' + r.openings.map(function(o) { return escHtml(o.name) + ' <span class="row-meta">' + pct(o.count, n) + '</span>'; }).join(' · ') + '</div>';
    // le percentuali contano solo le partite che partono come il tuo repertorio: le altre non dicono nulla
    let inRep = n - cov.out;
    if (n) html += '<div class="px-sum-row">' + (inRep
        ? 'Contro il tuo repertorio: ' + inRep + (inRep === 1 ? ' sua partita parte' : ' sue partite partono') + ' come le tue linee' +
          (cov.out ? ' (le altre ' + cov.out + ' iniziano con mosse che non giochi)' : '') + '. Di queste il <b>' + pct(cov.covered, inRep) +
          '</b> resta nella tua preparazione fino in fondo, il <b>' + pct(cov.exit, inRep) + '</b> ne esce prima per una sua mossa (elenco sotto)' +
          (cov.dev ? ', il ' + pct(cov.dev, inRep) + ' per una mossa dei suoi avversari' : '') + '.'
        : 'Nessuna sua partita entra nel tuo repertorio col ' + (op.color === 'white' ? 'Bianco' : 'Nero') + '.') + '</div>';
    $('#opp-summary').html(html);
    $('#opp-exits-n').text(r.exits.length || '');
    $('#opp-exits').html(r.exits.length ? pxExitRows(r.exits, 'op', op.color, 'avversario') : '<div class="empty-msg">Nessuna uscita: dove arriva, sei preparato.</div>');
    $('#opp-lines').html(r.lines.length
        ? '<button class="btn" style="margin:0 0 10px;" onclick="opTrain()">Ripassa queste ' + r.lines.length + ' linee</button>' + r.lines.map(function(l) {
            return '<div class="px-item" role="button" tabindex="0" onclick="openExploreLine(\'' + l.id + '\', 0)"><div class="px-item-main">' + escHtml(l.title) +
                '</div><div class="px-item-sub">' + escHtml(l.course) + ' · ci arrivano ' + l.count + (l.count === 1 ? ' sua partita' : ' sue partite') + '</div></div>';
        }).join('')
        : '<div class="empty-msg">Le sue partite non entrano nel tuo repertorio.</div>');
}
function opTrain() {
    if (!op.report) return;
    startCustomSession(op.report.lines.map(function(l) { return l.id; }), 'Contro ' + op.report.name);
}
function opLoadTree() {
    if (!op.key) return;
    let my = ++op.treeReq;
    $('#opp-crumb').text(op.nav.path.length ? pxSans(op.nav.path) : 'Posizione iniziale');
    pxPost('/api/opponent/tree', { key: op.key, color: op.color, path: op.nav.path }).done(function(t) {
        if (my !== op.treeReq) return;
        op.nav.top = t.moves.length ? t.moves[0].uci : null;
        op.nav.setBase(t.mine ? t.rep.map(function(r) { return moveArrow(r.uci, 'green'); }) : []);
        $('#opp-moves').html(pxTreeRows(t, 'op', false));
    });
}

// =====================================================================================
// ---------- COSTRUISCI: un repertorio tuo partendo dal database ----------
var bd = { nav: null, color: 'white', tree: null, db: null, reqTree: 0, reqDb: 0, timer: null, names: {} };
function openBuilder() {
    showView('build');
    setTimeout(function() {
        let courses = {};
        Object.keys(globalVariantsMap).forEach(function(k) { courses[globalVariantsMap[k].course || 'Varie'] = 1; });
        $('#dl-build-courses').html(Object.keys(courses).sort().map(function(c) { return '<option value="' + escHtml(c) + '">'; }).join(''));
        if (!bd.nav) {
            bd.nav = pxNav('build-board', bdLoad);
            pxFillDbSelects();
            $('#build-course').val(lsGet('buildCourse') || 'Il mio repertorio');
            $('#build-db').val(lsGet('buildDb') || 'lichess');
            $('#build-thr').val(lsGet('buildThr') || '5');
            bd.color = lsGet('buildColor') || dominantPerspective();
            $('#build-color').val(bd.color);
            bd.nav.setOrient(bd.color);
            $('.build-online').toggle($('#build-db').val() === 'lichess');
            bd.nav.goPath([]);
        } else bdLoad();
    }, 20);
}
function bdSettingsChanged(colorChanged) {
    bd.color = $('#build-color').val();
    lsSet('buildColor', bd.color); lsSet('buildDb', $('#build-db').val());
    $('.build-online').toggle($('#build-db').val() === 'lichess');
    if (colorChanged) bd.nav.setOrient(bd.color);
    bdLoad();
}
function bdLoad() {
    let path = bd.nav.path.slice(), fen = bd.nav.game.fen();
    $('#build-crumb').text(path.length ? pxSans(path) : 'Posizione iniziale');
    $('#build-status').text('');
    bd.tree = null; bd.db = null;
    // dopo un salvataggio l'indice del repertorio si ricostruisce (qualche secondo): mai l'elenco vecchio
    $('#build-moves').html('<div class="empty-msg">Carico…</div>'); $('#build-cov, #build-meta').empty();
    let myT = ++bd.reqTree;
    pxPost('/api/tree', { path: path, perspective: bd.color }).done(function(t) { if (myT === bd.reqTree) { bd.tree = t; bdRender(); } });
    // scorrendo a raffica non si spara una richiesta per mossa: Lichess risponderebbe 429
    let myD = ++bd.reqDb;
    clearTimeout(bd.timer);
    bd.timer = setTimeout(function() {
        let p = { db: $('#build-db').val(), fen: fen };
        if (p.db === 'lichess') { p.speeds = $('#build-speeds').val(); p.ratings = $('#build-ratings').val(); }
        $.get('/api/explorer', p)
            .done(function(d) { if (myD === bd.reqDb) { bd.db = d; bdRender(); } })
            .fail(function() { if (myD === bd.reqDb) { bd.db = { error: 'server non raggiungibile' }; bdRender(); } });
    }, 180);
}
function bdRender() {
    let t = bd.tree, d = bd.db;
    if (!t) return;
    let mine = t.turn === (bd.color === 'white' ? 'w' : 'b');
    let rep = {};
    (t.children || []).forEach(function(c) { if (c.uci !== '0000') rep[c.uci] = c; });
    $('#build-head').text(mine ? 'Tocca a te: scegli la mossa del tuo repertorio' : 'Tocca all\'avversario: copri le sue risposte più giocate');
    bd.nav.setBase(mine ? Object.keys(rep).map(function(u) { return moveArrow(u, 'green'); }) : []);
    let row = function(u, san, mark, bar, count) {
        return '<div class="exp-move" onclick="bd.nav.go(\'' + u + '\')" onmouseenter="bd.nav.hover(\'' + u + '\')" onmouseleave="bd.nav.hover()">' +
            '<span class="exp-san">' + escHtml(san) + ' ' + mark + '</span>' + bar + '<span class="exp-count">' + count + '</span></div>';
    };
    let ok = '<span class="db-ok" title="Nel repertorio">✓</span>';
    if (!d || d.error || !d.moves.length) {
        let msg = !d ? 'Interrogo il database…' : (d.error ? pxErr(d.error) : 'Nessuna partita nel database da questa posizione.');
        $('#build-cov').empty(); $('#build-meta').empty();
        $('#build-moves').html(Object.keys(rep).map(function(u) { return row(u, rep[u].san, ok, '<span class="exp-bar-wrap"></span>', 'nel repertorio'); }).join('') +
            '<div class="empty-msg">' + msg + '</div>');
        return;
    }
    if (d.opening) bd.names[bd.nav.path.join(' ')] = d.opening;   // per il titolo delle linee salvate
    let thr = parseInt($('#build-thr').val(), 10);
    lsSet('buildThr', String(thr));
    let tot = d.moves.reduce(function(a, m) { return a + m.games; }, 0) || 1, seen = {}, covered = 0, todo = 0;
    let rows = d.moves.map(function(m) {
        let u = sanToUci(bd.nav.game, m.san) || m.uci, pct = 100 * m.games / tot;
        seen[u] = true;
        if (rep[u]) covered += m.games;
        else if (!mine && pct >= thr) todo++;
        let mark = rep[u] ? ok : ((!mine && pct >= thr) ? '<span class="db-gap" title="Da coprire">⚠</span>' : '');
        return row(u, m.san, mark, pxBar(m), fmtGames(m.games) + ' · ' + Math.round(pct) + '%');
    }).join('');
    // mosse del repertorio che il database non conosce (rare o novita'): in cima
    let extra = Object.keys(rep).filter(function(u) { return !seen[u]; })
        .map(function(u) { return row(u, rep[u].san, ok, '<span class="exp-bar-wrap"></span>', 'poco giocata'); }).join('');
    let cov = '';
    if (!mine) {
        let p = Math.round(100 * covered / tot);
        cov = '<div class="db-cov"><span class="db-cov-n" style="color:' + (p >= 90 ? 'var(--accent-green)' : (p >= 70 ? 'var(--accent-orange)' : 'var(--accent-red)')) + '">' + p +
            '%</span> delle partite qui è coperto' + (todo ? ' · ' + todo + (todo === 1 ? ' risposta' : ' risposte') + ' da coprire (⚠)' : ' · risposte sopra soglia tutte coperte') + '</div>';
    }
    $('#build-cov').html(cov);
    $('#build-moves').html(extra + rows);
    $('#build-meta').html(fmtGames(d.total) + ' partite' + (d.opening ? ' · ' + escHtml(d.opening) : '') + ' · barra: vittorie Bianco / patte / vittorie Nero');
}
function bdSave() {
    let path = bd.nav.path.slice();
    if (!path.length) { $('#build-status').text('Gioca almeno una mossa.').css('color', 'var(--accent-red)'); return; }
    let course = ($('#build-course').val() || '').trim() || 'Il mio repertorio';
    lsSet('buildCourse', course);
    let opening = '';   // il nome della posizione con nome piu' vicina lungo la linea (non tutte ne hanno uno)
    for (let i = path.length; i >= 0 && !opening; i--) opening = bd.names[path.slice(0, i).join(' ')] || '';
    $('#build-status').text('Salvataggio…').css('color', 'var(--text-faint)');
    pxPost('/api/save_variation', {
        title: (opening || 'Linea') + ' · ' + pxTail(path), course: course, chapter: opening.split(':')[0].trim() || 'Generale',
        perspective: bd.color, moves: path.map(function(u) { return { uci: u, comment: '' }; }), extend: true
    }).done(function(r) {
        $('#build-status').text('');
        showToast(r.extended ? 'Linea allungata in «' + course + '».' : 'Linea salvata in «' + course + '».', 'success');
        loadDueVariations();
        // torna al bivio dell'avversario piu' vicino: la prossima risposta da coprire
        for (let i = path.length - 1; i >= 0; i--) {
            if ((i % 2 === 0) !== (bd.color === 'white')) { bd.nav.goPath(path.slice(0, i)); return; }
        }
        bd.nav.goPath([]);
    }).fail(function() { $('#build-status').text(''); });
}
function bdSparring() {
    sp.startPath = bd.nav.path.slice();
    $('#spar-color').val(bd.color);
    sp.pending = true;
    navTo('sparring');
}

// =====================================================================================
// ---------- SPARRING: l'avversario gioca come i giocatori veri del database ----------
const SPAR_MIN_GAMES = 10;   // sotto queste partite il database non e' piu' un avversario credibile
var sp = { board: null, game: new Chess(), path: [], startPath: [], color: 'white', active: false, req: 0, rep: [],
           errors: 0, errAt: {}, holes: [], inBook: true, bookEnd: null, pending: false };
function openSparring() {
    showView('spar');
    setTimeout(function() {
        if (!sp.board) {
            sp.board = pxBoard('spar-board', spOnMove);
            pxFillDbSelects();
            if (!sp.pending) $('#spar-color').val(lsGet('sparColor') || dominantPerspective());
            sp.board.set({ orientation: $('#spar-color').val() });
            cgMovable(sp.board, sp.game, null);
        }
        spStartLabel();
        if (sp.pending) { sp.pending = false; spStart(); }
    }, 20);
}
function spStartLabel() {
    $('#spar-start').html(sp.startPath.length ? escHtml(pxSans(sp.startPath)) + ' · <span class="sfn-clear" role="button" tabindex="0" onclick="sp.startPath = []; spStartLabel()">dall\'inizio</span>' : 'Posizione iniziale');
}
function spStatus(html, state) { $('#spar-status').html(html).attr('class', 'px-status' + (state ? ' is-' + state : '')); }
function spLog(kind, html) { $('#spar-log').append('<div class="px-log px-log-' + kind + '">' + html + '</div>'); }
function spFlip() { sp.board.toggleOrientation(); }
function spLast() { return sp.path[sp.path.length - 1]; }
function spRenderMoves() {
    let g = new Chess(), n0 = sp.startPath.length;
    $('#spar-moves').html(sp.path.map(function(u, i) {
        let mv = playUci(g, u);
        return '<span class="em-move' + (i < n0 ? ' px-dim' : '') + '">' + (i % 2 === 0 ? (i / 2 + 1) + '. ' : '') + escHtml(mv ? mv.san : u) + '</span>';
    }).join(' ') || '<span class="empty-msg">—</span>');
}
function spStart() {
    sp.color = $('#spar-color').val();
    lsSet('sparColor', sp.color);
    sp.path = sp.startPath.slice();
    sp.game = pxGame(sp.path);
    sp.active = true; sp.errors = 0; sp.errAt = {}; sp.holes = []; sp.inBook = true; sp.bookEnd = null;
    sp.req++;
    sp.board.set({ orientation: sp.color });
    cgPosition(sp.board, sp.game, spLast(), false);
    sp.board.setAutoShapes([]);
    $('#spar-summary').empty(); $('#spar-log').empty();
    spRenderMoves();
    spNext();
}
function spNext() {
    if (!sp.active) return;
    if (sp.game.game_over()) { spEnd(sp.game.in_checkmate() ? 'Scacco matto.' : 'Partita patta.'); return; }
    let my = ++sp.req, mine = turnColor(sp.game) === sp.color;
    pxPost('/api/tree', { path: sp.path, perspective: sp.color }).done(function(t) {
        if (my !== sp.req || !sp.active) return;
        sp.rep = (t.children || []).filter(function(c) { return c.uci !== '0000'; });
        if (mine) spUserTurn(); else spOppTurn(my);
    });
}
function spUserTurn() {
    if (sp.inBook && !sp.rep.length) {
        sp.inBook = false; sp.bookEnd = sp.path.length;
        spLog('info', sp.path.length > sp.startPath.length ? 'Qui finisce la tua preparazione: da adesso giochi libero.' : 'Il tuo repertorio non copre questa posizione: giochi libero.');
    }
    spStatus('Tocca a te' + (sp.rep.length ? ' · nel repertorio' : ''), null);
    cgMovable(sp.board, sp.game, sp.color);
}
function spOnMove(orig, dest) {
    if (!sp.active || turnColor(sp.game) !== sp.color) { cgPosition(sp.board, sp.game, spLast(), false); return; }
    let fen = sp.game.fen(), ply = sp.path.length;
    let mv = sp.game.move({ from: orig, to: dest, promotion: 'q' });
    if (!mv) { cgPosition(sp.board, sp.game, spLast(), false); cgMovable(sp.board, sp.game, sp.color); return; }
    let uci = mv.from + mv.to + (mv.promotion || '');
    if (sp.rep.length && !sp.rep.some(function(c) { return c.uci === uci; })) {
        sp.game.undo();
        playSound('error');
        cgPosition(sp.board, sp.game, spLast(), false);
        sp.board.setAutoShapes(sp.rep.map(function(c) { return moveArrow(c.uci, 'green'); }));
        if (!sp.errAt[fen]) {
            sp.errAt[fen] = true; sp.errors++;
            spLog('bad', '<b class="px-bad">' + escHtml(pxLabel(ply, mv.san)) + '</b> è fuori repertorio: qui giochi ' + sp.rep.map(function(c) { return '<b class="db-ok">' + escHtml(pxLabel(ply, c.san)) + '</b>'; }).join(' o ') + '.');
        }
        spStatus('Fuori repertorio: gioca la tua mossa (freccia verde)', 'bad');
        cgMovable(sp.board, sp.game, sp.color);
        return;
    }
    playMoveSound(mv);
    sp.path.push(uci);
    cgPosition(sp.board, sp.game, uci);
    sp.board.setAutoShapes([]);
    cgMovable(sp.board, sp.game, null);
    spRenderMoves();
    spNext();
}
function spOppTurn(my) {
    spStatus('L\'avversario pensa…', 'muted');
    $.get('/api/explorer', { db: 'lichess', fen: sp.game.fen(), speeds: $('#spar-speeds').val(), ratings: $('#spar-ratings').val() })
        .done(function(d) {
            if (my !== sp.req || !sp.active) return;
            if (d.error) { spEnd(pxErr(d.error), true); return; }
            let tot = d.moves.reduce(function(a, m) { return a + m.games; }, 0);
            if (tot < SPAR_MIN_GAMES) {
                spEnd('Il database finisce qui' + (tot ? ' (solo ' + tot + (tot === 1 ? ' partita' : ' partite') + ')' : '') + ': da questa posizione non ci sono abbastanza partite vere.');
                return;
            }
            let r = Math.random() * tot, m = d.moves[0];   // scelta pesata: come giocano davvero a questo livello
            for (let i = 0; i < d.moves.length; i++) { r -= d.moves[i].games; if (r < 0) { m = d.moves[i]; break; } }
            let uci = sanToUci(sp.game, m.san) || m.uci, pct = Math.round(100 * m.games / tot), ply = sp.path.length;
            if (sp.rep.length && !sp.rep.some(function(c) { return c.uci === uci; })) {
                sp.holes.push({ path: sp.path.concat([uci]), move: pxLabel(ply, m.san), pct: pct });
                spLog('gap', '<b class="db-gap">' + escHtml(pxLabel(ply, m.san)) + '</b> (' + pct + '% delle partite): nessuna risposta preparata.');
            }
            setTimeout(function() {
                if (my !== sp.req || !sp.active) return;
                let mv = playUci(sp.game, uci);
                playMoveSound(mv);
                sp.path.push(uci);
                cgPosition(sp.board, sp.game, uci);
                spRenderMoves();
                spNext();
            }, 350);
        })
        .fail(function() { if (my === sp.req && sp.active) spEnd('Server non raggiungibile.', true); });
}
function spEnd(reason, isError) {
    if (!sp.active) return;
    sp.active = false; sp.req++;
    cgMovable(sp.board, sp.game, null);
    spStatus(reason, isError ? 'bad' : 'info');
    let played = sp.path.length - sp.startPath.length;
    let book = sp.bookEnd == null ? 'sempre nel repertorio' : (sp.bookEnd > sp.startPath.length ? 'nel repertorio fino alla mossa ' + (Math.floor(sp.bookEnd / 2) + 1) : 'fuori dal repertorio');
    let html = '<div class="panel-box"><div class="panel-title">Com\'è andata</div><div class="px-sum-row">' + Math.ceil(played / 2) + ' mosse · ' + book + ' · ' +
        sp.errors + (sp.errors === 1 ? ' errore' : ' errori') + '</div>';
    if (sp.holes.length) {
        html += '<div class="px-sum-h">Risposte da preparare</div>' + sp.holes.map(function(h, i) {
            return '<div class="px-item"><div class="px-item-main"><b class="db-gap">' + escHtml(h.move) + '</b> · ' + h.pct + '% delle partite a questo livello</div>' +
                '<button class="btn-delete px-act" onclick="pxPrepare(sp.holes[' + i + '], sp.color, \'sparring\')" title="Prepara la risposta nell\'editor"><i class="ico i-plus"></i> Prepara</button></div>';
        }).join('');
    }
    html += '<div class="px-save-row"><button class="btn" onclick="spStart()">Rigioca</button><button class="btn btn-read" onclick="spSaveLine()">Salva come linea</button></div></div>';
    $('#spar-summary').html(html);
}
function spSaveLine() {
    openEditor(null, { moves: sp.path, perspective: sp.color, course: 'Il mio repertorio', title: 'Sparring · ' + pxTail(sp.path), back: 'sparring' });
}

// =====================================================================================
// ---------- FINALI: giochi contro la tablebase di Lichess (difesa perfetta) ----------
const EG_DRAW_MOVES = 15;   // tenere la patta per 15 mosse = esercizio riuscito
var eg = { board: null, list: [], cur: null, game: new Chess(), tb: null, userColor: 'white', last: null, sans: [],
           mistakes: 0, errAt: {}, userMoves: 0, active: false, busy: false, queue: [], cache: {} };
function openEndgames() {
    showView('end');
    setTimeout(function() {
        if (!eg.board) {
            eg.board = pxBoard('end-board', egOnMove);
            eg.board.set({ fen: '8/8/8/8/8/8/8/8' });   // vuota finche' non scegli una posizione
            cgMovable(eg.board, eg.game, null);
        }
        egLoadList();
    }, 20);
}
function egLoadList(cb) { $.get('/api/endgames', function(r) { eg.list = r.endgames; egRenderList(); if (cb) cb(); }); }
function egTodo(e) { return srsState(e).cls !== 'srs-ok'; }   // nuova o da ripassare
function egRenderList() {
    let todo = eg.list.filter(egTodo), rest = eg.list.filter(function(e) { return !egTodo(e); });
    $('#end-list').html(todo.concat(rest).map(function(e) {
        let st = srsState(e);
        let when = st.cls === 'srs-new' ? 'nuova' : (st.cls === 'srs-due' ? 'da ripassare' : 'tra ' + intervalLabel(Math.max(0, (new Date(e.srs.next_review) - Date.now()) / 86400000)));
        return '<div class="px-item px-item-row' + (eg.cur && eg.cur.id === e.id ? ' is-active' : '') + '" role="button" tabindex="0" onclick="eg.queue = []; egStart(\'' + e.id + '\')">' +
            '<span class="srs-dot ' + st.cls + '" title="' + st.lab + '"></span><div class="px-item-main">' + escHtml(e.title) +
            '<span class="row-meta">' + (e.goal === 'win' ? 'vinci' : 'patta') + ' · ' + when + '</span></div>' +
            '<button class="btn-delete" onclick="event.stopPropagation(); egDelete(\'' + e.id + '\')" title="Elimina la posizione" aria-label="Elimina la posizione"><i class="ico i-x"></i></button></div>';
    }).join('') || '<div class="empty-msg">Nessuna posizione.</div>');
    $('#end-due-n').text(todo.length ? todo.length + ' da fare' : '');
    $('#end-due-btn').toggle(todo.length > 0).text('Allena quelle da fare (' + todo.length + ')');
}
function egStatus(text, state) { $('#end-status').text(text).attr('class', 'px-status' + (state ? ' is-' + state : '')); }
function tbFetch(fen) {
    if (eg.cache[fen]) return Promise.resolve(eg.cache[fen]);
    return fetch('https://tablebase.lichess.ovh/standard?fen=' + encodeURIComponent(fen)).then(function(r) {
        if (r.status === 429) throw new Error('429');
        if (r.status === 400) throw new Error('bad');
        if (!r.ok) throw new Error('http');
        return r.json();
    }).then(function(d) { eg.cache[fen] = d; return d; });
}
function egNetErr(e) {
    eg.busy = false;
    egStatus(e && e.message === '429' ? 'La tablebase chiede di aspettare: riprova tra un minuto.' : 'Tablebase non raggiungibile (sei offline?).', 'bad');
}
function egStartDue() {
    eg.queue = eg.list.filter(egTodo).map(function(e) { return e.id; });
    if (eg.queue.length) egStart(eg.queue.shift());
}
function egStart(id) {
    let e = eg.list.find(function(x) { return x.id === id; });
    if (!e) return;
    eg.cur = e; eg.game = new Chess(e.fen); eg.userColor = turnColor(eg.game); eg.last = null; eg.sans = [];
    eg.mistakes = 0; eg.errAt = {}; eg.userMoves = 0; eg.active = true; eg.busy = true;
    eg.board.set({ orientation: eg.userColor });
    cgPosition(eg.board, eg.game, null, false);
    cgMovable(eg.board, eg.game, null);
    eg.board.setAutoShapes([]);
    $('#end-title').text(e.title);
    $('#end-goal').html((e.goal === 'win' ? 'Obiettivo: <b>vincere</b>' : 'Obiettivo: <b>tenere la patta</b> per ' + EG_DRAW_MOVES + ' mosse') +
        ' · giochi col ' + (eg.userColor === 'white' ? 'Bianco' : 'Nero'));
    $('#end-after').empty(); $('#end-moves').hide().empty();
    egRenderList();
    egStatus('Interrogo la tablebase…', 'muted');
    tbFetch(eg.game.fen()).then(function(d) { if (eg.cur === e && eg.active) { eg.tb = d; egUserTurn(); } }).catch(egNetErr);
}
function egRestart() { if (eg.cur) egStart(eg.cur.id); }
function egFlip() { if (eg.board) eg.board.toggleOrientation(); }
function egUserTurn() {
    eg.busy = false;
    egStatus(eg.cur.goal === 'win' ? 'Tocca a te: vinci' : 'Tocca a te: tieni la patta', null);
    cgMovable(eg.board, eg.game, eg.userColor);
}
function egRenderMoves() {
    let f = eg.cur.fen.split(' '), ply0 = (parseInt(f[5], 10) - 1) * 2 + (f[1] === 'b' ? 1 : 0);
    $('#end-moves').show().html(eg.sans.map(function(s, i) {
        let p = ply0 + i;
        return '<span class="em-move">' + (p % 2 === 0 ? (p / 2 + 1) + '. ' : (i === 0 ? Math.floor(p / 2) + 1 + '… ' : '')) + escHtml(s) + '</span>';
    }).join(' '));
}
// La tablebase ordina le mosse dalla migliore; tra quelle equivalenti se ne sceglie una a caso, cosi'
// la stessa posizione non si gioca sempre uguale.
function egPick(moves) {
    if (!moves.length) return null;
    let b = moves[0], eq = moves.filter(function(m) { return m.category === b.category && m.dtz === b.dtz && m.dtm === b.dtm; });
    return eq[Math.floor(Math.random() * eq.length)];
}
function egOnMove(orig, dest) {
    if (!eg.active || eg.busy || turnColor(eg.game) !== eg.userColor) { cgPosition(eg.board, eg.game, eg.last, false); return; }
    let fen = eg.game.fen();
    let mv = eg.game.move({ from: orig, to: dest, promotion: 'q' });
    if (!mv) { cgPosition(eg.board, eg.game, eg.last, false); cgMovable(eg.board, eg.game, eg.userColor); return; }
    let uci = mv.from + mv.to + (mv.promotion || '');
    let entry = (eg.tb.moves || []).find(function(m) { return m.uci === uci; });
    let cat = entry ? entry.category : 'unknown';   // dal punto di vista dell'avversario, dopo la tua mossa
    let ok = eg.cur.goal === 'win' ? (cat === 'loss' || cat === 'maybe-loss') : (cat !== 'win' && cat !== 'maybe-win');
    if (!ok) {
        eg.game.undo();
        playSound('error');
        cgPosition(eg.board, eg.game, eg.last, false);
        if (!eg.errAt[fen]) { eg.errAt[fen] = true; eg.mistakes++; }
        egStatus(eg.cur.goal === 'win' ? 'Con ' + mv.san + ' non vinci più' + (cat === 'draw' || cat === 'blessed-loss' ? ': diventa patta' : '') + '. Riprova.'
                                       : 'Con ' + mv.san + ' perdi. Riprova.', 'bad');
        cgMovable(eg.board, eg.game, eg.userColor);
        return;
    }
    playMoveSound(mv);
    eg.last = uci; eg.userMoves++; eg.sans.push(mv.san);
    egRenderMoves();
    cgPosition(eg.board, eg.game, uci);
    eg.board.setAutoShapes([]);
    if (egCheckEnd()) return;
    eg.busy = true;
    cgMovable(eg.board, eg.game, null);
    let e = eg.cur;
    tbFetch(eg.game.fen()).then(function(d) {
        if (eg.cur !== e || !eg.active) return;
        let best = egPick(d.moves || []);
        if (!best) { egCheckEnd(); return; }
        setTimeout(function() {
            if (eg.cur !== e || !eg.active) return;
            let m = playUci(eg.game, best.uci);
            playMoveSound(m);
            eg.last = best.uci; eg.sans.push(m.san);
            egRenderMoves();
            cgPosition(eg.board, eg.game, best.uci);
            if (egCheckEnd()) return;
            tbFetch(eg.game.fen()).then(function(d2) { if (eg.cur === e && eg.active) { eg.tb = d2; egUserTurn(); } }).catch(egNetErr);
        }, 300);
    }).catch(egNetErr);
}
function egCheckEnd() {
    let g = eg.game, win = eg.cur.goal === 'win';
    if (g.in_checkmate()) { egFinish(turnColor(g) !== eg.userColor, 'Scacco matto!'); return true; }
    if (g.in_draw()) {
        let why = g.in_stalemate() ? 'Stallo' : (g.insufficient_material() ? 'Materiale insufficiente' : (g.in_threefold_repetition() ? 'Tre volte la stessa posizione' : 'Regola delle 50 mosse'));
        if (win) { eg.mistakes++; egFinish(false, why + ': è patta.'); }
        else egFinish(true, why + ': patta tenuta.');
        return true;
    }
    if (!win && eg.userMoves >= EG_DRAW_MOVES) { egFinish(true, 'Patta tenuta per ' + EG_DRAW_MOVES + ' mosse.'); return true; }
    return false;
}
function egFinish(success, text) {
    eg.active = false; eg.busy = false;
    cgMovable(eg.board, eg.game, null);
    egStatus(text, success ? 'good' : 'bad');
    let q = !success ? 1 : (eg.mistakes === 0 ? 5 : (eg.mistakes === 1 ? 3 : 1));   // come i ripassi delle linee
    let e = eg.cur;
    pxPost('/api/endgames/review', { id: e.id, quality: q }).done(function(r) {
        e.srs = r.srs; e.stats = r.stats;
        egRenderList();
        let nextBtn = eg.queue.length ? '<button class="btn" onclick="egStart(eg.queue.shift())">Prossima posizione<span class="kbd">Spazio</span></button>' : '';
        $('#end-after').html('<div class="review-recent">' + (success ? (eg.mistakes ? eg.mistakes + (eg.mistakes === 1 ? ' errore' : ' errori') : 'Nessun errore') : 'Non riuscito') +
            ' · prossimo ripasso tra ' + intervalLabel(r.srs.interval) + '</div><div class="px-save-row">' + nextBtn + '<button class="btn btn-read" onclick="egRestart()">Rigioca</button></div>');
    });
}
function egHint() {
    if (!eg.active || eg.busy || !eg.tb || !(eg.tb.moves || []).length) return;
    let fen = eg.game.fen(), best = eg.tb.moves[0];
    if (!eg.errAt[fen]) { eg.errAt[fen] = true; eg.mistakes++; }
    eg.board.setAutoShapes([moveArrow(best.uci, 'yellow')]);
    egStatus('Suggerimento: ' + best.san + ' (conta come errore)', 'warn');
}
function egDelete(id) {
    uiConfirm('Eliminare questa posizione dagli allenamenti?', { danger: true, okText: 'Elimina' }).then(function(ok) {
        if (!ok) return;
        pxPost('/api/endgames/delete', { id: id }).done(function() {
            if (eg.cur && eg.cur.id === id) { eg.cur = null; eg.active = false; $('#end-title').text('Scegli una posizione'); $('#end-goal, #end-after').empty(); egStatus(''); }
            egLoadList();
        });
    });
}
function egAdd() {
    let fen = $('#end-fen').val().trim();
    if (!fen) { showToast('Incolla un FEN.', 'error'); return; }
    if (!new Chess().load(fen)) { showToast('FEN non valido.', 'error'); return; }
    tbFetch(fen).then(function(d) {
        let goal = d.category === 'win' ? 'win' : (['draw', 'cursed-win', 'blessed-loss'].indexOf(d.category) >= 0 ? 'draw' : null);
        if (!goal) { showToast(d.category === 'loss' || d.category === 'maybe-loss' ? 'Chi ha il tratto perde: cambia il tratto nel FEN.' : 'La tablebase non conosce questa posizione.', 'error'); return; }
        pxPost('/api/endgames/add', { fen: fen, title: $('#end-name').val().trim(), goal: goal }).done(function(r) {
            showToast('Posizione aggiunta: ' + (goal === 'win' ? 'si gioca per vincere.' : 'si gioca per la patta.'), 'success');
            $('#end-fen, #end-name').val('');
            egLoadList(function() { eg.queue = []; egStart(r.id); });
        });
    }).catch(function(e) {
        showToast(e.message === 'bad' ? 'La tablebase non accetta questa posizione (al massimo 7 pezzi).' : 'Tablebase non raggiungibile.', 'error');
    });
}

// ---------- tastiera nelle viste personali ----------
$(document).on('keydown', function(e) {
    let tag = (e.target && e.target.tagName) || '';
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(tag) || (e.target && e.target.isContentEditable) || $('#modal-overlay').length) return;
    let v = $('.view.active').attr('id');
    let nav = v === 'view-games' ? gm.nav : (v === 'view-opp' ? op.nav : (v === 'view-build' ? bd.nav : null));
    if (nav) {
        if (e.code === 'ArrowLeft') { e.preventDefault(); nav.back(); }
        else if (e.code === 'ArrowRight') { e.preventDefault(); nav.forward(); }
        else if (e.key === 'f' || e.key === 'F') { e.preventDefault(); nav.flip(); }
    } else if (v === 'view-end') {
        if (e.key === 'h' || e.key === 'H') { e.preventDefault(); egHint(); }
        else if (e.key === 'f' || e.key === 'F') { e.preventDefault(); egFlip(); }
        else if (e.code === 'Space') { let b = $('#end-after .btn').first(); if (b.length) { e.preventDefault(); if (!e.repeat) b.click(); } }
    } else if (v === 'view-spar') {
        if (e.key === 'f' || e.key === 'F') { e.preventDefault(); spFlip(); }
    }
});

// =====================================================================================
// ---------- MENU "ALTRO" (solo dal computer): scorciatoie, cartella dei dati, chiudi l'app ----------
function toggleMoreMenu(open) {
    let list = document.getElementById('more-list');
    if (!list) return;
    if (open === undefined) open = list.hidden;
    list.hidden = !open;
    $('#more-btn').attr('aria-expanded', open);
    if (open) $(list).find('button').first().focus();
}
$(document).on('mousedown', function(e) { if (!$(e.target).closest('.top-menu').length) toggleMoreMenu(false); });
$(document).on('keydown', function(e) {
    let list = document.getElementById('more-list');
    if (!list || list.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); toggleMoreMenu(false); $('#more-btn').focus(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        let items = $(list).find('button'), i = items.index(document.activeElement);
        items.eq((i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length).focus();
    }
});
function showDataDir() {
    $.get('/api/data_dir', function(r) {
        uiHtmlModal('Cartella dei dati',
            '<p>Corsi, ripassi, partite e impostazioni stanno in:</p><p><b class="px-url">' + escHtml(r.path) + '</b></p>' +
            '<p class="panel-hint">Per portarli su un altro computer copia i file di questa cartella (repertoire.json, personal.json, lichess_token.txt). ' +
            'Se prima usavi la versione col codice, copia qui i file che avevi accanto ad app.py.</p>',
            [{ label: 'Chiudi', cls: 'btn-read' }, { label: 'Apri la cartella', fn: function() { pxPost('/api/data_dir'); } }]);
    });
}
function quitApp() {
    uiConfirm('Chiudere openrepertoire? I dati sono già salvati: per riaprirla avvia di nuovo l\'app.', { title: 'Chiudi l\'app', okText: 'Chiudi l\'app' }).then(function(ok) {
        if (!ok) return;
        pxPost('/api/quit').always(function() {
            document.body.innerHTML = '<div class="app-closed"><h1>openrepertoire è chiusa</h1><p>Puoi chiudere questa scheda.</p></div>';
        });
    });
}

// =====================================================================================
// ---------- ACCESSO DAL TELEFONO (stessa rete Wi-Fi, con PIN) ----------
function uiHtmlModal(title, html, buttons) {
    $('#modal-overlay').remove();
    let ov = $('<div id="modal-overlay"></div>');
    let card = $('<div class="modal-card" role="dialog" aria-modal="true"></div>').attr('aria-label', title);
    card.append($('<div class="modal-title"></div>').text(title), $('<div class="modal-body modal-msg"></div>').html(html));
    let act = $('<div class="modal-actions"></div>');
    let close = function() { $(document).off('keydown.modal'); ov.remove(); };
    buttons.forEach(function(b) {
        act.append($('<button class="btn"></button>').addClass(b.cls || '').text(b.label).on('click', function() { close(); if (b.fn) b.fn(); }));
    });
    card.append(act);
    ov.append(card).on('mousedown', function(e) { if (e.target === ov[0]) close(); }).appendTo('body');
    $(document).on('keydown.modal', function(e) { if (e.key === 'Escape') { e.preventDefault(); close(); } });
    setTimeout(function() { act.find('.btn').last().focus(); }, 30);
}
function showPhone() {
    $.get('/api/lan', phoneModal).fail(function() { showToast('Le impostazioni del telefono si cambiano dal computer.', 'error'); });
}
function phoneSet(body) { pxPost('/api/lan', body).done(phoneModal); }
function phoneModal(s) {
    if (!s.enabled) {
        uiHtmlModal('Usa dal telefono',
            '<p>Apri l\'app dal telefono o dal tablet, sulla stessa rete Wi-Fi del computer. Per entrare serve un PIN; i dati restano su questo computer, che deve essere acceso con l\'app aperta.</p>',
            [{ label: 'Chiudi', cls: 'btn-read' }, { label: 'Attiva', fn: function() { phoneSet({ enabled: true }); } }]);
        return;
    }
    let urls = (s.urls || []).map(function(u) { return '<b class="px-url">' + escHtml(u) + '</b>'; }).join('<span class="px-or">oppure</span>');
    let warn = s.running ? '' : '<div class="px-warn">' + (s.error === 'no_network'
        ? 'Il computer non è collegato a nessuna rete: collegalo al Wi-Fi e riapri questa finestra.'
        : 'L\'accesso dalla rete non si è aperto' + (s.error ? ' (' + escHtml(s.error) + ')' : '') + ': riprova riaprendo questa finestra.') + '</div>';
    uiHtmlModal('Usa dal telefono', warn +
        (s.running && s.urls && s.urls.length ? '<div id="phone-qr" class="px-qr" role="img" aria-label="Codice QR con l\'indirizzo"></div>' : '') +
        '<ol class="px-steps"><li>Telefono e computer sulla stessa rete Wi-Fi.</li>' +
        '<li>Inquadra il codice con la fotocamera del telefono, oppure apri ' + (urls || 'l\'indirizzo del computer') + '</li>' +
        '<li>Inserisci il PIN <b class="px-pin">' + escHtml(s.pin || '') + '</b></li></ol>' +
        '<p class="panel-hint">La prima volta il computer può chiederti se l\'app accetta connessioni in arrivo: rispondi Consenti. Sul telefono, Condividi → Aggiungi alla schermata Home la apre a tutto schermo come un\'app. Fuori casa funziona con una rete privata come Tailscale (gratuita), installata su computer e telefono.</p>',
        [{ label: 'Disattiva', cls: 'btn-read', fn: function() { phoneSet({ enabled: false }); } },
         { label: 'Nuovo PIN', cls: 'btn-read', fn: function() { phoneSet({ new_pin: true }); } },
         { label: 'Chiudi' }]);
    if (s.running && s.urls && s.urls.length) pxQr(document.getElementById('phone-qr'), s.urls[0]);
}
// Codice QR (static/js/qrcode.js, MIT): si carica solo quando serve
function pxQr(el, text) {
    let draw = function() {
        let qr = qrcode(0, 'M');
        qr.addData(text);
        qr.make();
        el.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 3, scalable: true });
    };
    if (window.qrcode) draw();
    else $.getScript('/static/js/qrcode.js').done(draw);
}
