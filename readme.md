# openrepertoire

motore di ripetizione spaziata open source

1. completamente offline / dati salvati in locale
2. algoritmo SM-2 di ripetizione spaziata 

come scaricare e utilizzare:
scarica il codice e avvia l'eseguibile corrispondente al tuo sistema operativo
- richiede python3, pythonchess, flask

funzionamento: con il box "load pgn" carichi il pgn di un corso / studio personale di lichess (specificando il colore / se è un corso di tattica/strategia) che verrà salvato in un file repertoire.json. le varianti così caricate andarano inizialmente nelle sezioni "da imparare" e "repertorio". in "repertorio" saranno sempre visibili tutte le varianti che hai caricato. nella sezione "da imparare" cliccando una variante la giocherai  (ti dirà il programma cosa giocare, insieme al commento associato alla mossa nel pgn (se presente)) fino a che la finisci. a tal punto scomparirà da "da imparare" e dopo un pò di tempo (funzione degli errori commessi) verrà riproposta nella sezione "da ripassare". la variante continuerà ad apparire nella sezione "da ripassare" con una frequenza che è funzione degli errori commessi. 

per segnalazioni di bug / suggerimenti @nonsonomiti instagram 
