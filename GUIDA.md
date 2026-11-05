# OpenRepertoire: guida all'uso

OpenRepertoire ti aiuta a memorizzare le aperture di scacchi. Carichi un corso o uno studio, l'app ti insegna ogni linea mossa per mossa e poi te la ripropone al momento giusto, così non la dimentichi. Gira sul tuo computer, i dati restano tuoi ed è gratuita.

English version: [GUIDE.md](GUIDE.md)

## Indice

1. [Installazione e avvio](#1-installazione-e-avvio)
2. [Le basi](#2-le-basi)
3. [Importare corsi e studi](#3-importare-corsi-e-studi)
4. [Imparare e ripassare](#4-imparare-e-ripassare)
5. [Gestire il repertorio](#5-gestire-il-repertorio)
6. [Esplora](#6-esplora)
7. [Statistiche](#7-statistiche)
8. [L'area Personale](#8-larea-personale)
9. [Usarla dal telefono](#9-usarla-dal-telefono)
10. [Token Lichess](#10-token-lichess)
11. [Backup e passaggio a un altro computer](#11-backup-e-passaggio-a-un-altro-computer)
12. [Scorciatoie da tastiera](#12-scorciatoie-da-tastiera)
13. [Se qualcosa non va](#13-se-qualcosa-non-va)

## 1. Installazione e avvio

Scarica il file per il tuo sistema dalla [pagina delle release](https://github.com/Nonsonomiti/openrepertoire/releases). Non serve installare altro.

**Windows.** Scarica `OpenRepertoire-Windows.zip`, estrai `OpenRepertoire.exe` e aprilo. La prima volta Windows può dire "Windows ha protetto il PC" perché l'app non è firmata: Ulteriori informazioni, poi Esegui comunque.

**Mac.** Scarica `OpenRepertoire-macOS-AppleSilicon.zip` (chip M1, M2, M3, M4) oppure `OpenRepertoire-macOS-Intel.zip`. Estrai `OpenRepertoire.app` e spostala in Applicazioni. La prima volta macOS la blocca perché non è firmata da Apple: Impostazioni di Sistema → Privacy e sicurezza → Apri comunque.

**Linux.** Scarica `OpenRepertoire-Linux.tar.gz`, estrai `OpenRepertoire` e aprilo con un doppio clic o con `./OpenRepertoire` da terminale.

L'app si apre nel browser e resta attiva in sottofondo. Sul Mac non ha icona nel Dock. Riaprendola si riapre la pagina. Per chiuderla: menu "⋯" in alto → Chiudi l'app.

**Lingua.** Il pulsante IT/EN in alto passa dall'italiano all'inglese. L'app ricorda la scelta. Al primo avvio segue la lingua del browser.

**Dal codice (facoltativo).** Se preferisci il codice, scaricalo e avvia `MacOS_start_app.command`, `Windows_start_app.bat` o `start.sh`. Serve Python 3; le altre dipendenze si installano da sole.

## 2. Le basi

In alto a sinistra ci sono due aree:

- **Corsi**: i PGN che hai caricato. Sezioni: Impara, Repertorio, Esplora, Ripassa, Statistiche.
- **Personale**: strumenti che non partono da un corso. Sezioni: Partite, Avversario, Costruisci, Sparring, Finali.

Qualche parola che torna spesso:

- **Variante** o **linea**: una sequenza di mosse da memorizzare.
- **Corso** e **capitolo**: come sono raggruppate le linee.
- Il numero in alto a destra indica quante linee sono da ripassare oggi.
- L'icona del tema offre cinque temi di colore. Repertorio → Personalizza grafica cambia scacchiera, pezzi, dimensione, velocità di animazione e suoni.

Non hai ancora file? Nella pagina Repertorio vuota premi "Carica un corso d'esempio" e prova l'app in un minuto.

## 3. Importare corsi e studi

Vai in Repertorio → **Importa corso (PGN)**.

1. Scegli il colore: Bianco, Nero o Automatico.
2. Scegli il file PGN.
3. Premi Carica file.

Il corso prende il nome del file. Se importi due volte le stesse linee, i doppioni vengono saltati e i tuoi progressi restano. Le linee con mosse illegali vengono saltate e l'app ti dice quante sono.

**Automatico** prende il colore dalla scacchiera dello studio Lichess. Se non c'è e il PGN parte da una posizione impostata, giochi il lato che ha il tratto. Va bene per i corsi di tattica e strategia.

**Studi Lichess.** Scarica il PGN dello studio da Lichess e importalo. L'app usa il nome dello studio come corso, il nome del capitolo come capitolo e l'orientamento della scacchiera come tuo colore (scegli Automatico).

**"Ogni ramo è una linea da studiare".** Spuntala per gli studi Lichess e per i repertori fatti da te con ChessBase o SCID: ogni ramo diventa una linea a sé. Lasciala spenta per i corsi acquistati: lì i rami sono idee dell'autore, quindi si studia solo la linea principale e le mosse secondarie stanno nel commento, dove puoi cliccarle per vederle sulla scacchiera.

Le frecce e i cerchi disegnati dall'autore nel PGN compaiono da soli sulla scacchiera.

## 4. Imparare e ripassare

**Impara** sceglie la prima linea che non hai ancora studiato. Una linea nuova passa da queste fasi:

1. **Fase 1**: l'app mostra la mossa da giocare con il commento dell'autore e una freccia. Giocala sulla scacchiera, oppure premi prima "Fammi muovere" (Spazio).
2. **Fase 2**: rigiochi tutta la linea a memoria, due volte.
3. **Revisione errori**: se hai sbagliato, ripeti proprio quelle posizioni per tre cicli.

A quel punto la linea esce da "da imparare" e torna in **Ripassa** quando è il momento.

**Come funziona la cadenza.** Non ti dai un voto: l'app conta gli errori. In un ripasso, nessun errore vale Facile, uno vale A fatica, due o più valgono Dimenticata. Una linea giocata bene torna dopo 6 ore, 1 giorno, 3 giorni, 7 giorni, poi a intervalli crescenti fino a un massimo di 6 mesi. Una linea dimenticata torna dopo 10 minuti e riparte dall'inizio della sequenza.

**Durante l'allenamento:**

- **Suggerimento** (H): mostra prima il pezzo, poi la mossa. Conta come errore.
- **Alla cieca** (B): nasconde i pezzi.
- **Gira** (F): ruota la scacchiera.
- **Analizza su Lichess**: apre la posizione sul sito di Lichess.

**Leggere una linea.** Clicca una linea in Repertorio per scorrerla con i commenti, senza essere interrogato. Usa Spazio o le frecce.

**Ripassare in anticipo.** Prima di un torneo, l'icona dell'orologio su un corso o un capitolo rende le sue linee ripassabili subito. Il resto della cadenza non cambia.

**Saltare quello che sai.** In Repertorio → Personalizza grafica puoi attivare "Nel ripasso salta l'inizio già giocato bene oggi". Le linee che condividono le prime mosse partono da dove cambiano.

## 5. Gestire il repertorio

La pagina Repertorio elenca tutte le linee per corso e capitolo. Il campo filtro cerca in titoli, corsi e capitoli. Il pallino colorato accanto a ogni linea ne indica lo stato: da imparare, da ripassare o programmata.

Le icone su ogni riga servono a:

- **Corso**: impararlo, renderlo ripassabile subito, rinominarlo, eliminarlo. Per eliminare un corso intero devi scrivere `delete` come conferma.
- **Capitolo**: aggiungere una linea, renderlo ripassabile subito, rinominarlo, unirlo a un altro capitolo.
- **Linea**: modificare le mosse, duplicarla in una nuova linea, esportarla, spostarla in un altro corso o capitolo, eliminarla.

**Crea / modifica → Nuova variante** apre l'editor. Gioca le mosse sulla scacchiera, poi scegli titolo, corso, capitolo e colore. Scrivendo un nome nuovo crei quel corso o capitolo. "Imposta posizione" ti fa partire da qualsiasi posizione: trascini i pezzi e imposti tratto, arrocchi ed en passant.

**Cerca posizione** ti dice quali linee arrivano a una posizione: incolla un FEN o usa quello della scacchiera.

**Esporta / backup** scarica le linee in PGN: tutto, un corso, un capitolo o le linee che spunti a mano. Opzioni:

- **Solo mosse**: senza commenti, per un file pulito.
- **Unisci le varianti in un albero**: su Lichess ottieni un capitolo ramificato invece di tanti quasi uguali.
- **Fondi anche i capitoli**: un capitolo per corso, e puoi scegliere quali capitoli includere.

Senza "solo mosse", reimportando il file tornano corso, capitolo e colore.

## 6. Esplora

Esplora mostra tutto il repertorio come un albero. Scegli colore e corso in alto, poi gioca le mosse sulla scacchiera o cliccale negli elenchi. Le frecce sinistra e destra vanno indietro e avanti.

- **Continuazioni nel repertorio**: le tue mosse da questa posizione e quante linee le usano.
- **Buco di copertura**: un avviso quando tocca a te e non hai una mossa preparata.
- **Linee che finiscono qui**: cliccale per aprirle.
- **Nota**: scrivi le tue note su una posizione e segnale come Posizione chiave, Manca analisi o Idea. La nota appartiene alla posizione, quindi compare anche se ci arrivi con un altro ordine di mosse. **Note sulle posizioni** le elenca tutte, con un filtro per tipo e un link a Lichess. Le tue note non toccano mai i commenti del corso.
- **Database Lichess**: le mosse giocate davvero, dai maestri o online, con filtri per anno, cadenza ed Elo. Una spunta segna le mosse del tuo repertorio; un segnale di avviso quelle dell'avversario a cui non hai risposta. Mostra quante partite copre il tuo repertorio e, coi maestri, le partite modello. Serve il [token](#10-token-lichess).
- **Analisi Lichess (cloud)**: valutazione del motore e linee migliori, quando Lichess le ha per quella posizione. Il token non serve.
- **Trasposizioni & conflitti**: posizioni raggiunte da più ordini di mosse. "Conflitto" vuol dire che dalla stessa posizione hai due tue mosse diverse: conviene controllare.

## 7. Statistiche

Totali, precisione, giorni di studio di fila, tasso di richiamo degli ultimi 14 giorni, accuratezza per corso e colore, ripassi in arrivo nei prossimi 14 giorni e le linee più difficili.

## 8. L'area Personale

Partite, avversari e finali stanno separati dai corsi (`personal.json`). Costruisci e Sparring richiedono il [token](#10-token-lichess).

**Partite.** Scrivi il tuo nome utente Lichess e/o Chess.com e premi Scarica: le partite sono pubbliche, la password non serve. L'app le confronta col repertorio e ti mostra:

- **Dove hai deviato tu**: hai giocato altro dove avevi una mossa preparata. "Ripassa" rimette quelle linee in ripasso.
- **Dove l'avversario è uscito dal repertorio**: una mossa a cui non hai risposta. "Prepara" apre l'editor con la linea già giocata fino a lì.

Sulla scacchiera scorri cosa hai giocato da ogni posizione, con i risultati.

**Avversario.** Scrivi il nome utente di chi stai per affrontare e il tuo colore. L'app scarica le sue partite pubbliche e ti dice cosa gioca, dove esce dal tuo repertorio e quali tue linee contano contro di lui. "Ripassa queste linee" avvia una sessione solo con quelle.

**Costruisci.** Crea un repertorio senza corso. Quando tocca a te scegli la mossa; quando tocca all'avversario l'app mostra le sue risposte più giocate nel database e segna quelle ancora da coprire. La soglia la decidi tu (per esempio le risposte giocate in almeno il 5% delle partite). "Salva questa linea" la memorizza e ti riporta all'ultimo bivio dell'avversario. Le linee finiscono in un tuo corso, "Il mio repertorio" di base, e si studiano da Corsi.

**Sparring.** Giochi contro il database: l'avversario sceglie le mosse come i giocatori veri del livello scelto, in proporzione a quanto sono giocate. Le tue mosse vengono controllate col repertorio. Alla fine vedi le risposte che ti mancano e puoi prepararle o salvare la partita come linea. La partita finisce quando il database non ha più partite.

**Finali.** Lucena, Philidor, re e pedone, i matti di base e altro. Giochi contro la tablebase di Lichess, che difende in modo perfetto, e le posizioni tornano con la stessa ripetizione spaziata delle linee. Puoi aggiungere le tue da "Aggiungi una posizione": un FEN con al massimo 7 pezzi. Giochi il lato che ha il tratto e la tablebase decide se l'obiettivo è vincere o tenere la patta.

## 9. Usarla dal telefono

1. Sul computer, icona del telefono in alto → Attiva.
2. Inquadra il codice QR con la fotocamera del telefono. Telefono e computer devono stare sulla stessa rete Wi-Fi.
3. Inserisci il PIN che vedi sul computer. Viene chiesto una volta sola.

Sul telefono, Condividi → Aggiungi alla schermata Home la apre a tutto schermo come un'app. I dati restano sul computer, che deve essere acceso con l'app aperta. La prima volta il computer può chiederti se consentire le connessioni in arrivo: rispondi Consenti. "Nuovo PIN" scollega i telefoni già collegati.

Fuori casa funziona con una rete privata come Tailscale (gratuita), installata su computer e telefono.

## 10. Token Lichess

Il database Lichess (Esplora, Costruisci, Sparring) richiede un token personale gratuito.

1. Accedi a Lichess e apri [la pagina dei token](https://lichess.org/account/oauth/token/create?description=openrepertoire). Non serve spuntare nessun permesso.
2. Crea il token e copialo.
3. Nell'app vai in Corsi → Esplora → apri "Database Lichess", incollalo e premi Salva.

Il token resta sul tuo computer in `lichess_token.txt`.

## 11. Backup e passaggio a un altro computer

Menu "⋯" → **Cartella dei dati** mostra dove sta tutto e la apre. Per un backup o per spostare i dati, copia questi file:

- `repertoire.json`: corsi e progressi
- `personal.json`: partite, avversari, finali, note
- `lichess_token.txt`: il token

Le cartelle predefinite sono `Library/Application Support/OpenRepertoire` nella tua cartella Inizio su Mac, `%APPDATA%\OpenRepertoire` su Windows e `~/.local/share/openrepertoire` su Linux. Con la versione col codice, i file stanno accanto ad `app.py`.

Puoi anche tenere una copia in PGN con Esporta / backup, che però non contiene i progressi.

## 12. Scorciatoie da tastiera

| Tasto | Azione |
| --- | --- |
| Spazio | Avanti / conferma |
| ← → | Mossa precedente / successiva (lettura, Esplora, Partite, Avversario, Costruisci) |
| F | Gira la scacchiera |
| H | Suggerimento (ripasso e finali) |
| B | Alla cieca |
| ? | Mostra le scorciatoie |
| Esc | Chiude menu e finestre |
| Tasto destro sulla scacchiera | Disegna frecce e cerchi (un clic li cancella) |

## 13. Se qualcosa non va

- **Cosa funziona senza internet?** Imparare, ripassare e gestire il repertorio. Database Lichess, analisi cloud, tablebase e download delle partite richiedono la connessione.
- **"Lichess non risponde" con un errore di certificato** (solo versione col codice): a Python mancano i certificati. Su Mac apri Applicazioni → Python 3.x → Install Certificates.command e riavvia l'app, oppure esegui `python3 -m pip install --user certifi`.
- **Troppe richieste**: Lichess limita la velocità delle richieste. Aspetta un minuto.
- **Il telefono non si collega**: controlla che siano sulla stessa rete Wi-Fi e che l'app sia aperta sul computer, poi riapri la finestra del telefono sul computer.

Per segnalazioni e suggerimenti: @nonsonomiti su Instagram.
