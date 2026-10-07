# openrepertoire

motore di ripetizione spaziata open source

1. completamente offline / dati salvati in locale
2. algoritmo SM-2 di ripetizione spaziata 

come scaricare e utilizzare:
scarica l'app per il tuo sistema dalla pagina releases (https://github.com/Nonsonomiti/openrepertoire/releases), senza installare python:
- windows: OpenRepertoire-Windows.zip → estrai OpenRepertoire.exe e aprilo. la prima volta windows può dire "windows ha protetto il pc" (l'app non è firmata): ulteriori informazioni → esegui comunque.
- mac: OpenRepertoire-macOS-AppleSilicon.zip (mac con chip m1/m2/m3/m4) o OpenRepertoire-macOS-Intel.zip → estrai OpenRepertoire.app e spostala in applicazioni. la prima volta macos la blocca (non è firmata da apple): impostazioni di sistema → privacy e sicurezza → "apri comunque". in alternativa, da terminale: `xattr -dr com.apple.quarantine /Applications/OpenRepertoire.app`.
- linux: OpenRepertoire-Linux.tar.gz → estrai OpenRepertoire e aprilo (doppio clic, o `./OpenRepertoire` da terminale).

l'app si apre nel browser e resta attiva in sottofondo (sul mac non ha icona nel dock); riaprendola si riapre la pagina. per chiuderla: menu "⋯" in alto → chiudi l'app. i tuoi dati stanno in una cartella tua, che trovi dal menu "⋯" → cartella dei dati (mac: libreria/application support/openrepertoire, windows: %appdata%\openrepertoire, linux: ~/.local/share/openrepertoire). se prima usavi la versione col codice, copia lì repertoire.json (e personal.json, lichess_token.txt) che avevi accanto ad app.py.

in alternativa, col codice: scaricalo e avvia il lanciatore del tuo sistema (MacOS_start_app.command, Windows_start_app.bat, start.sh). richiede python3; flask e python-chess si installano da soli. in questo caso i dati restano accanto ad app.py.

funzionamento: con il box "load pgn" carichi il pgn di un corso / studio personale di lichess (specificando il colore / se è un corso di tattica/strategia) che verrà salvato in un file repertoire.json. le varianti così caricate andarano inizialmente nelle sezioni "da imparare" e "repertorio". in "repertorio" saranno sempre visibili tutte le varianti che hai caricato. nella sezione "da imparare" cliccando una variante la giocherai  (ti dirà il programma cosa giocare, insieme al commento associato alla mossa nel pgn (se presente)) fino a che la finisci. a tal punto scomparirà da "da imparare" e dopo un pò di tempo (funzione degli errori commessi) verrà riproposta nella sezione "da ripassare". la variante continuerà ad apparire nella sezione "da ripassare" con una frequenza che è funzione degli errori commessi. 

pgn con varianti (repertori tuoi fatti con chessbase, scid o uno studio lichess con i rami): spunta "ogni ramo è una linea da studiare" quando lo carichi e ogni ramo diventa una variante. nei pgn dei corsi lasciala spenta: lì i rami sono idee dell'autore e restano nel commento.

l'app ha due aree, in alto a sinistra: "corsi" (tutto quello che sta sopra: impari e ripassi i pgn caricati) e "personale", che non parte da un corso:
- partite: scarichi le tue partite da lichess o chess.com (basta il nome utente) e l'app le confronta col repertorio. ti mostra dove hai giocato fuori dalla linea che avevi studiato (un clic e quelle linee tornano da ripassare) e dove l'avversario ti ha portato fuori dalla preparazione (un clic e prepari la risposta nell'editor).
- avversario: scrivi il nome utente di chi incontrerai, l'app scarica le sue partite pubbliche e ti dice cosa gioca, dove esce dal tuo repertorio e quali tue linee ripassare contro di lui (in una sessione sola).
- costruisci: fai un repertorio tuo senza corso. quando tocca a te scegli la mossa, quando tocca all'avversario l'app ti mostra le sue risposte più giocate nel database lichess e segna quelle ancora da coprire. le linee finiscono in un corso tuo ("il mio repertorio") e si studiano da corsi.
- sparring: giochi contro "il database": l'avversario sceglie le mosse come i giocatori veri del livello scelto. le tue mosse vengono controllate col repertorio, e a fine partita vedi le risposte che ti mancano.
- finali: lucena, philidor, re e pedone, i matti di base... giochi contro la tablebase di lichess, che difende in modo perfetto, con la stessa ripetizione spaziata delle linee. puoi aggiungere le tue posizioni (fen, massimo 7 pezzi).
le partite, gli avversari e i finali stanno in personal.json, separati dai corsi (repertoire.json). costruisci e sparring usano il database lichess, quindi il token qui sotto.

dal telefono: sul computer icona del telefono in alto → attiva. inquadra il codice qr con la fotocamera del telefono (stessa rete wi-fi) e inserisci il pin che vedi sul computer: lo chiede una volta sola. condividi → "aggiungi alla schermata home" la apre a tutto schermo come un'app. il computer deve restare acceso con l'app aperta; la prima volta può chiederti di consentire le connessioni in arrivo. fuori casa funziona con tailscale (gratuito) su computer e telefono.

database lichess (opzionale, sezione "esplora"): il pannello "database lichess" confronta le mosse del tuo repertorio con quelle davvero giocate (OTB o partite online, filtrabili per cadenza ed elo). serve un token personale gratuito, lo crei su https://lichess.org/account/oauth/token/create e lo incolli nel pannello la prima volta. resta sul tuo computer in lichess_token.txt.

(solo versione col codice) se al salvataggio del token l'app dice che lichess non risponde e ti mostra un errore di certificato: è python che non ha i certificati installati (il browser ne ha di suoi, per questo lichess.org ti si apre lo stesso). su mac si risolve aprendo applicazioni → python 3.x → install certificates.command e riavviando l'app, oppure con `python3 -m pip install --user certifi`. i lanciatori installano certifi da soli, quindi di norma non serve fare niente.

nel ripasso: "alla cieca" (o il tasto b) nasconde i pezzi; in personalizza grafica puoi far partire le linee da dove cambiano, saltando l'inizio già giocato bene oggi.

scorciatoie: premi "?" nell'app (o menu "⋯" → scorciatoie da tastiera). tasto destro sulla scacchiera per disegnare frecce e cerchi; le frecce e i cerchi dei commenti dei corsi ([%cal] / [%csl]) compaiono da soli.

per costruire i pacchetti da soli: `pip install pyinstaller` e poi `pyinstaller packaging/openrepertoire.spec` (escono in dist/). su github li costruisce e li prova il workflow "pacchetti" a ogni push, e un tag v* li allega a una release.

per segnalazioni di bug / suggerimenti @nonsonomiti instagram 
