# Forum GCD

## Attivazione

Questa versione richiede le migrazioni forum 0002–0004. Sono preparate
nei file, NON applicate durante lo sviluppo. Prima di utilizzare il nuovo
codice occorre applicarle nello stack Django esistente; senza lo schema
aggiornato le pagine autenticate non possono funzionare.
Nessuna modifica a Docker o alla configurazione del database.

0002 aggiunge gerarchia, accessi riservati e riferimenti GCD.
0003 crea i 17 gruppi della FAQ, GCD e le quattro sezioni About.
0004 aggiunge lo storico ContentRevision. Non importa utenti o archivi.

## Account e accesso

Ogni URL del forum, incluse richieste HTMX, è protetto. Un anonimo riceve
HTTP 403 e la pagina “Iscriviti”, con registrazione e login GCD.
Profilo e logout riusano gli endpoint GCD: nessun account parallelo.
Gli utenti attivi possono leggere e pubblicare nei gruppi accessibili.
Le risposte richiedono topic non bloccati e non archiviati.
Creazione e modifica validano anche i gruppi inviati manualmente nel POST.

Editor, Board, Error e Contact sono creati riservati per prudenza:
uno staff assegna i membri nell'admin Category. Le restrizioni dei genitori
si ereditano; per accedere servono i permessi su ciascun antenato riservato.
Staff e superuser accedono a tutti i gruppi attivi. Una Category disattivata
nasconde anche i suoi discendenti. Il forum non espone archivi Board pubblici.
La migrazione non cambia le impostazioni delle Category già esistenti:
verificarne esplicitamente gli accessi prima della messa in servizio.

## Gruppi, topic e GCD

- `/forum/`: feed e ricerca sui soli contenuti accessibili.
- `/forum/?view=groups`: albero espandibile dei gruppi.
- `/forum/groups/<slug>/`: topic del gruppo e dei discendenti accessibili.
- `/forum/groups/<slug>/link/`: apertura/creazione di un gruppo per ID GCD.
- `/forum/new/?category=<slug>`: nuovo topic nel gruppo preselezionato.
- `/forum/<slug>/`: topic, risposte, upvote e segnalazioni.

Gerarchia massima: GCD → About Issues / Series / Authors / Publishers →
record per ID. Authors usa il modello GCD Creator. Il pulsante “+ GCD ID”
verifica l'esistenza del record e riusa il gruppo se già presente.
Il terzo livello contiene il collegamento interno al record GCD e i suoi
topic. I topic creati lì ereditano automaticamente il GenericForeignKey.
Nessun link Google Groups, invio email o collegamento esterno di navigazione.

La validazione del modello impedisce cicli, quarto livello e spostamenti
di sottoalberi oltre il limite. Le scritture SQL dirette e QuerySet.update
non devono essere usate per modificare la gerarchia: aggirano model.clean.

## Accountability

Discussioni e post conservano autore, created_by, updated_by, date e IP
di creazione. ContentRevision registra prima/dopo, attore, data e IP
della richiesta per salvataggi e soft delete, inclusi i percorsi admin.
Le nuove creazioni di gruppi per ID hanno un evento di audit.
Le revisioni sono consultabili solo nell'admin con i permessi previsti,
senza azioni di modifica/cancellazione. Non è un registro anti-manomissione
a livello database; modifiche SQL dirette non sono intercettate.
Per salvataggi senza richiesta HTTP l'IP della revisione è nullo.
Non viene ricostruito uno storico precedente all'attivazione.

Le rimozioni mantengono contenuti e revisioni nel DB. Autore o staff possono
modificare/rimuovere; il normale utente non può operare su contenuti altrui.
IP e revisioni non sono esposti nel forum. Di default l'IP proviene da
REMOTE_ADDR; abilitare FORUM_TRUST_X_FORWARDED_FOR solo dietro proxy fidato.
Markdown è filtrato; tutte le operazioni di scrittura richiedono CSRF.

## Verifica

Test aggiunti per accesso anonimo, permessi ereditati, creazione topic e
risposte, profondità/cicli, ID GCD, revisioni e CSRF. Da eseguire nello
stack di test esistente: non sono stati eseguiti durante questa modifica.
Nessun test deve essere indirizzato al database operativo.

## CSS

Logo locale: static/img/gcd_logo.png. Nessuna CDN o dipendenza runtime nuova.
Il CSS dedicato è già compilato. Per rigenerarlo con Tailwind 3.4.1:

```sh
tailwindcss -c tailwind.forum.config.js -i static/css/forum.input.css -o static/css/forum.css --minify
```
