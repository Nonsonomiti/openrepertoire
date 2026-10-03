# openrepertoire

motore di ripetizione spaziata open source

1. completamente offline / dati salvati in locale
2. algoritmo SM-2 di ripetizione spaziata 

come scaricare e utilizzare:
scarica il codice e avvia l'eseguibile corrispondente al tuo sistema operativo
- richiede python3 (pythonchess e flask dovrebbero essere installati automaticamente dagli eseguibili, se non funzia comunque scaricali a mano)

funzionamento: con il box "load pgn" carichi il pgn di un corso / studio personale di lichess (specificando il colore / se è un corso di tattica/strategia) che verrà salvato in un file repertoire.json. le varianti così caricate andarano inizialmente nelle sezioni "da imparare" e "repertorio". in "repertorio" saranno sempre visibili tutte le varianti che hai caricato. nella sezione "da imparare" cliccando una variante la giocherai  (ti dirà il programma cosa giocare, insieme al commento associato alla mossa nel pgn (se presente)) fino a che la finisci. a tal punto scomparirà da "da imparare" e dopo un pò di tempo (funzione degli errori commessi) verrà riproposta nella sezione "da ripassare". la variante continuerà ad apparire nella sezione "da ripassare" con una frequenza che è funzione degli errori commessi. 

database lichess (opzionale, sezione "esplora"): il pannello "database lichess" confronta le mosse del tuo repertorio con quelle davvero giocate (OTB o partite online, filtrabili per cadenza ed elo). serve un token personale gratuito, lo crei su https://lichess.org/account/oauth/token/create e lo incolli nel pannello la prima volta. resta sul tuo computer in lichess_token.txt.

se al salvataggio del token l'app dice che lichess non risponde e ti mostra un errore di certificato: è python che non ha i certificati installati (il browser ne ha di suoi, per questo lichess.org ti si apre lo stesso). su mac si risolve aprendo applicazioni → python 3.x → install certificates.command e riavviando l'app, oppure con `python3 -m pip install --user certifi`. i lanciatori installano certifi da soli, quindi di norma non serve fare niente.

scorciatoie: premi "?" nell'app. tasto destro sulla scacchiera per disegnare frecce e cerchi; le frecce e i cerchi dei commenti dei corsi ([%cal] / [%csl]) compaiono da soli.

per segnalazioni di bug / suggerimenti @nonsonomiti instagram 
