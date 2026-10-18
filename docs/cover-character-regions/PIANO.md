# PR 1 - Immagini del personaggio ricavate dalle copertine e scelte con un voto

## Contesto
La pagina del personaggio (`show_character`, apps/gcd/views/details.py:4207) mostra una
copertina intera a caso (`randint`, e `cover_set.first()` che puo' dare una copertina
cancellata): spesso il personaggio e' piccolo o in un gruppo.
Obiettivo: gli indicizzatori tracciano il personaggio sulle copertine e segnano le zone
candidate a immagine ufficiale; gli indicizzatori votano 1-2-3 tra le candidate; la scheda
mostra al massimo le 3 scelte.

Decisioni dell'utente:
- prima si inseriscono i personaggi nella sequenza di copertina, poi li si seleziona sulla
  copertina (integrita' dei riferimenti); l'immagine si ricava dalla copertina, nessun file nuovo;
- solo rettangolo, approvazione normale;
- la grandezza non basta a dire se un'immagine e' significativa (Superman ferito, anziano,
  disegnatori diversi): l'indicizzatore spunta "candidate for official image" quando traccia
  la zona; le zone non spuntate restano salvate (utili per l'evoluzione nel tempo) ma non
  entrano nel voto;
- votano gli indicizzatori (`indexer.can_reserve`), classifica 1-2-3 (3, 2, 1 punti),
  voti separati per scheda (generale e per universo);
- senza voti la scheda resta com'e' oggi;
- scansione sostituita: zona "da ricontrollare", esclusa da candidate e scheda finche' non
  viene risalvata sulla nuova scansione; i voti restano;
- copertine avvolgenti: zone solo sul fronte;
- prova con almeno 10 scansioni dell'utente dello stesso personaggio da fonti diverse;
- modifiche minime, direttive del manutentore, wiki come legge.
- In futuro i topic (altro progetto: le keyword diventano topic) potranno descrivere la scena
  raffigurata; questa PR non ne dipende.

## Verdetto sull'integrita' (revisione esperta, punti chiave verificati nel codice)
- La zona punta all'apparizione (StoryCharacter) che esiste nella stessa modifica come
  `StoryCharacterRevision`, anche appena aggiunta. Al contrario (prima la zona) la zona perde
  universo, cancellazioni e blocchi; creare l'apparizione in automatico rifarebbe il modulo
  dei personaggi (identita' civili, gruppi, doppioni): non minimo.
- Zone nella modifica della sequenza, clonate e bloccate insieme alle apparizioni. Una modifica
  separata bloccherebbe le prenotazioni del numero (apps/oi/views.py:588-595) o lascerebbe orfani.
- Varianti "Only Scan Difference" (status 2) hanno la propria Cover ma usano la sequenza del
  numero base (apps/gcd/models/issue.py:271-282): la FK a Cover resta necessaria.
  **Regola di validita' unica (I3)**: copertina non cancellata e
  `cover.issue == story.issue` oppure (`cover.issue.variant_of == story.issue` e
  `variant_cover_status == 2`); usata al salvataggio, all'approvazione e in visualizzazione.
- Diversamente dagli ordini dei personaggi (orfani solo nascosti), una zona invalida va
  cancellata all'approvazione: una zona orfana non verrebbe piu' clonata, quindi mai piu'
  modificabile.

## Dati
- gcd (apps/gcd/models/cover.py, migrazione 0072):
  - `CoverCharacterRegion(GcdLink)`: `story_character` FK StoryCharacter, `cover` FK Cover,
    `left`, `top`, `width`, `height` PositiveSmallIntegerField (unita' = 1/10000 della
    larghezza del fronte su entrambi gli assi, origine in alto a sinistra del fronte;
    width, height >= 1), `is_candidate` BooleanField(default=False),
    `scan_date` DateTimeField(null);
    `unique_together = (story_character, cover)` (indice che parte dalla colonna della query).
  - `CoverCharacterRegionVote`: `voter` FK User, `character` FK Character (la scheda votata),
    `region` FK CoverCharacterRegion (CASCADE), `rank` 1-3;
    `unique_together = [(character, region, voter), (character, voter, rank)]`.
- oi (apps/oi/models.py accanto a `StoryCharacterRevision`, migrazione 0068):
  `CoverCharacterRegionRevision(Revision)`: FK alla zona (`null=True`, `related_name='revisions'`),
  FK a `StoryCharacterRevision`, FK a Cover, stessi campi (compreso `is_candidate`).

## Regole per ogni evento (all'approvazione nel `commit_to_display` della revisione di zona,
salvo dove indicato)
| Evento | Zona | Voti |
|---|---|---|
| Apparizione cancellata (o sequenza cancellata) | cancellata | cancellati (CASCADE) |
| Personaggio dell'apparizione cambiato (es. Superman -> Superboy) o universo cambiato | resta | cancellati |
| Sequenza non piu' di tipo copertina | cancellata | cancellati |
| Sequenza o copertina spostata tra numeri | cancellata se I3 non vale | cancellati |
| Numero cancellato | clonata con `deleted=True` nel ciclo di clonazione | cancellati |
| Revisione aggiunta e poi tolta nella stessa modifica | solo segnata come registrata (niente `None.delete()`) | - |
| Casella "candidate" tolta | resta, esce dalle candidate | restano, non contano |
| Scansione sostituita (`scan_date != last_upload`, confronto con NULL) | resta, esclusa finche' risalvata | restano |
| Copertina cancellata o `limit_display` | nascosta (filtro di visualizzazione) | restano |
| Ruolo, gruppi, flashback cambiati | niente | niente |

## Passi
Ramo `feat/cover-character-regions` nel worktree `.worktrees/cover-character-regions`
(dentro la cartella montata da Docker), da `upstream/beta` 55325d09.

1. **Revisione di zona** (apps/oi/models.py): sorgente, `_pre_initial_save`, `_pre_save_object`,
   override di `commit_to_display` con le regole della tabella; `_imps_for` = 1 punto per zona
   cambiata (cosi' una modifica di sole zone si invia senza casi speciali); classe aggiunta
   all'elenco delle cancellazioni in `calculate_imps` (~974-984); una riga in `_revision_sets`
   (~344-356) dopo copertine e ordini, cancellazioni prima.
2. **Clonazione e blocco**: nel ciclo delle apparizioni (apps/oi/models.py ~4500-4517) ogni
   zona dell'apparizione e' clonata con il suo `RevisionLock` (senza blocco scarto e
   approvazione vanno in errore, apps/oi/models.py:1089-1094).
3. **Confronto**: `StoryRevision.compare_changes` (~6207-6221) tiene conto delle zone; il
   confronto della sequenza mostra prima e dopo con il ritaglio e la casella "candidate".
4. **Pagina "Mark characters on cover"**: pulsante nel modulo della sequenza di tipo copertina
   con personaggi (apps/oi/forms/story.py ~769, apps/oi/views.py ~970); vista con
   `story_revision_id`, solo con modifica aperta e per chi l'ha prenotata. Copertine
   permesse secondo I3; immagine w400, per le avvolgenti la w200 (solo fronte, quindi senza
   conversioni). Si sceglie il personaggio, si trascina, si spunta o no "Candidate for
   official image", "Remove" per togliere. `scan_date` = `last_upload` letto all'apertura
   (campo nascosto). Controlli: valori >= 0, width e height >= 1, left+width <= 10000;
   scrive solo le zone cambiate.
5. **Acquisitore** `static/js/oi/cover_character_region.js`, ~40 righe senza librerie: eventi
   pointer (mouse, dito, penna); x e y divisi per la larghezza mostrata
   (`getBoundingClientRect`) e moltiplicati per 10000 a ogni evento; rettangolo in un SVG
   sovrapposto alto `10000 * naturalHeight / naturalWidth`; quattro campi nascosti; `<noscript>`.
   Niente Jcrop: del 2013, chiede jQuery, e `gatefoldcover.js` sbaglia se la finestra cambia misura.
6. **Ritaglio** `get_region_tag(region, alt_text)` in apps/gcd/views/covers.py accanto a
   `get_image_tag` (stessi casi `limit_display` e `FAKE_IMAGES`): SVG con `viewBox` = zona e
   `<image href=w400|w200 width="10000" height="100000" preserveAspectRatio="xMinYMin meet">`.
7. **Candidate**: una funzione in apps/gcd/views/details.py con il filtro di universo di
   `show_character`, regola I3, apparizione e sequenza non cancellate, `is_candidate`,
   `scan_date == last_upload`; punti annotati con i voti della scheda (`character`).
8. **Pagina "Cover images of <personaggio>"** (url sotto `/character/<id>/`): griglia
   django-tables2 (come gli elenchi del sito) dei ritagli candidati, con numero, anno,
   disegnatore (matite della sequenza di copertina, dai crediti esistenti), grandezza e punti;
   ordinabile per ogni colonna e divisa in pagine. Per chi ha `indexer.can_reserve` un menu
   "-, 1, 2, 3" per ritaglio con le scelte gia' fatte e "Save" (modulo semplice, niente JS).
   Il server accetta ogni posizione una volta sola e solo zone candidate; in una transazione
   sostituisce i voti di quell'indicizzatore per quella scheda (al massimo 3 righe).
9. **Scheda** (`show_character`, templates/gcd/details/tw_character.html): con voti, fino a 3
   ritagli per punti (pari: piu' primi posti, poi area maggiore, poi id), ognuno con link al
   numero; senza voti la copertina a caso di oggi, invariata. Link alla pagina delle immagini
   quando c'e' almeno una candidata.
10. **Classi Tailwind mancanti** (`inset-0`, `touch-none`, `cursor-crosshair`): output.css
    ricostruito solo con aggiunte (memoria tailwind-output-build).

## Prima del codice
- A ogni ripresa: `git status`, fetch di upstream e origin, avanzamento di beta (AGENTS.md).
- Wiki in XML (Cloudflare blocca gli script), salvate dall'utente in `.cache/`: Covers_FAQ,
  Adding_Covers, Character_Appearances, Type, Variant_Issues. Contrasti col piano: li dico prima.
- Migrazioni gcd 0072 e oi 0068 come nel ramo topic-manager: chi arriva secondo rinumera.
- Docker e database sono condivisi con l'altro progetto dell'utente: prima di `migrate`,
  pytest o server di prova, chiedere.

## Copertine di prova (solo locale, mai nel repository)
- L'utente fornisce almeno 10 scansioni dello stesso personaggio da fonti diverse, ognuna con
  il numero (serie e numero) a cui appartiene; almeno una variante "solo scansione diversa" e
  una copertina avvolgente se disponibili; anche casi da non candidare (es. Superman ferito o
  anziano).
- Uno script in `.cache/cover-regions/` crea le righe Cover e le misure w100/w200/w400 con
  `generate_sizes` (apps/oi/covers.py:219) in una `MEDIA_ROOT` di prova sotto
  `.cache/cover-regions/media` (mai in `media/`).
- Impostazioni locali non committate sopra `settings_dev`: `FAKE_IMAGES = False`,
  `MEDIA_ROOT` di prova, `IMAGE_SERVER_URL = '/media'`.
- Personaggi mancanti nelle sequenze: li aggiungo con la modifica normale (prova anche del flusso).

## Verifica
- pytest nel container, uno alla volta, una prova per ogni riga della tabella degli eventi;
  inoltre: limiti dei valori; I3 con variante status 2; clonazione con blocco, scarto e
  approvazione senza errori; punti di una modifica di sole zone; candidate solo con la
  casella e senza le zone da ricontrollare; voti: posizione doppia rifiutata, zona non
  candidata rifiutata, voto sostituito, schede separate, solo `indexer.can_reserve`; griglia
  ordinata per ogni colonna; scheda: 3 per punti con i pareggi, senza voti copertina a caso;
  `get_region_tag` con `limit_display` e `FAKE_IMAGES`.
- flake8; `git diff --numstat upstream/beta -- static/css/output.css` con 0 righe tolte.
- Sito di sviluppo con le scansioni: tracciamento con e senza casella, approvazione,
  sostituzione, pagina delle candidate, voti di almeno due indicizzatori di prova (mai gli
  account di sviluppo esistenti), scheda.
- Prova dell'utente sul tablet (dito e penna), con l'elenco numerato delle registrazioni.
- Revisione dell'intero diff `upstream/beta...HEAD` con la lista dei controlli prima del commit.
