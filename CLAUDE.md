# The Ember Loop — istruzioni di progetto

App di supporto per una sessione di gioco da tavolo di una sera. Gira su tre telefoni
più quello del narratore, da `index.html` — pagina sola, nessun framework, nessun build step
per il front-end. Lingua del progetto: **italiano**, codice compreso (nomi, commenti, messaggi).

## Regole dure

1. **Non pubblicare mai segreti.** `contenuti.md`, `CHIAVI-MASTER.md`, `.segreti`, i documenti
   di progetto e i verificatori sono in `.gitignore` e ci restano. Prima di ogni push,
   `push.ps1` rilegge `.segreti` e cerca quei contenuti dentro i file pubblicabili: se ne trova
   uno, si ferma. **Non aggirare quella guardia — sistema il file.**
2. **Niente rete a runtime.** Nessun CDN, nessun font remoto, nessuna chiamata esterna.
   `jsQR.min.js` è locale apposta: da un CDN falliva in sala e lo scanner moriva in silenzio.
3. **Non modificare a mano i file generati.** `dati.js`, `stampa.html`, `prova-offline.html`
   escono da `costruisci.py`. Le modifiche vanno nei sorgenti.
4. **Non inventare contenuto di gioco.** Testi, nomi, parole chiave, enigmi e mappe li scrive
   Alessandro. Se per far compilare qualcosa servirebbe inventare un testo, fermati e chiedi.
5. **Non cambiare le regole dei cifrari.** `cifrari.py` è la verità. Se una porta JS non torna
   con Python, è la porta JS a essere sbagliata.
6. **Un nome solo per cosa.** La tabella qui sotto è vincolante per tutto ciò che un giocatore
   o il narratore legge — schermate, fogli stampati, `master.html`, `CHIAVI-MASTER.md`. Un
   sinonimo in più sembra innocuo e costa mezz'ora al tavolo.

## I nomi

| La cosa | Si chiama | **Non** si chiama |
|---|---|---|
| il cartellino QR posato nel mondo | **sigillo** | — |
| il numero dentro `HUSA-1`, cioè `1` | **numero del sigillo** | ~~numero d'archivio~~, ~~reperto n.~~ |
| i quattro segni opachi, `VVSX`, che aprono | **codice del sigillo** | ~~codice~~ da solo, dov'è ambiguo |
| l'oggetto che si legge una volta aperto | **reperto** | ~~testo~~, nelle frasi per i giocatori |
| il corpo scritto del reperto | **testo** (e il blocco `=== TESTO ===`) | — |
| l'elenco di ciò che il tavolo ha aperto | **archivio** | ~~registro~~ |
| una voce `=== LOG ===` | **voce di registro**, il **registro** | — |
| chi ha scritto una parola (il simbolo) | **mondo** | ~~pianeta~~, per questo significato |
| dove sta la voce di una parola | **pianeta** | — |
| l'etichetta di una parola, `HUSA-A` | **sigla** | — |
| le tre parti del cifrario | **alfabeto**, **chiave**, **ordine** | — |
| la porta che apre l'Apritore da solo | **porta di pietra** | ~~stanza~~, nelle frasi per i giocatori |
| ciò che apre una parola decifrata | **ingresso del luogo dell'enigma** | — |
| i tre ruoli | **Traduttore**, **Custode**, **Apritore** | ~~Decifratore~~, ~~Consultatore~~ |

Le chiavi dei dati restano quelle che sono (`testi`, `stanze`, `enigmi`, `pianeta`): sono il
contratto di `dati.js`. **La regola vale sulle parole, non sugli identificatori.**

Due coppie **non sono sinonimi**: il **numero del sigillo** (`1`, in alto sul foglio) apre la
*chiave*, il **codice del sigillo** (`VVSX`, sotto il sigillo) apre il *reperto*; il **mondo**
di una parola dice chi l'ha scritta e quindi il cifrario, il **pianeta** dice dove sta la voce.

## Come si costruisce

```bash
python da_excel.py --forza  # Materials.xlsx -> contenuti.md (il contenuto nasce nell'Excel)
python costruisci.py        # contenuti.md -> dati.js, CHIAVI-MASTER.md, soluzioni.json, .segreti,
                            # poi genera_stampe.py, genera_offline.py e genera_master.py
python controlla_testi.py   # controlla i testi prima di costruire
```

`master.html` e' lo strumento del narratore: tutte le soluzioni, un banco che decifra al volo,
le griglie disegnate. Come `CHIAVI-MASTER.md` e `soluzioni.json`, **non esce mai dal disco.**

`costruisci.py` si rifiuta di costruire se qualcosa non va e spiega cosa, in italiano.
Quel comportamento è voluto: **meglio fermarsi che produrre materiale sbagliato da stampare.**

## Come si prova

```bash
python -m http.server 8080          # servire e aprire http://localhost:8080
./servi.ps1                          # serve sulla LAN SOLO i file pubblicabili
./servi.ps1 -Https                   # idem, ma in https: e' l'unico modo di avere lo scanner
python android/fai_apk.py            # l'APK da installare sui telefoni
```

In `http://192.168.x.x` **la fotocamera non parte**: i browser la danno solo in contesto
sicuro. Senza scanner si digita il codice sotto il sigillo e funziona tutto il resto.
`-Https` fa un certificato per l'IP del PC (serve `openssl`, arriva con Git per Windows):
sul telefono si accetta l'avviso una volta e lo scanner torna.

Le prove del browser girano con Playwright su Chromium headless. Ogni modifica all'app va
verificata così prima di dichiararla fatta — questo progetto ha già avuto tre bug che
sembravano funzionare e non funzionavano.

```bash
python verifica_griglie.py            # le porte di pietra, per forza bruta (le griglie stanno in app.js)
python prove/confronto_cifrari.py     # cifrari.js contro cifrari.py
python prove/prova_costruisci.py      # costruzione giusta + ogni validazione che scatta
python prove/prova_app.py             # Playwright sulle quattro modalità, fotocamera finta compresa
```

Le prove costruiscono `prove/fixture/contenuti.md` (contenuto **finto**) in una cartella
temporanea: non toccano mai i file generati del progetto. Servono `pip install playwright qrcode`
e un Chromium (quello di Playwright, o Chrome/Edge installati).

## Cose che si sono già rotte una volta: non rifarle

| Trappola | Regola |
|---|---|
| Video dentro un contenitore `display:none` | su iOS il contenitore va reso visibile **prima** di `play()` |
| jsQR da CDN | resta locale, e lo scanner deve fallire **rumorosamente** |
| `prova-offline.html` montato a mano | si rigenera con `genera_offline.py`, mai a mano |
| Campo vuoto → `return` muto | ogni campo vuoto deve dire cosa manca e chi lo fornisce |
| Chiavi in file pubblicabili | la guardia legge il **contenuto**, non il nome del file |
| Sigle delle parole uguali ai sigilli | le parole hanno sigle a lettere (`HUSA-A`), i sigilli numeri |
| Regole dei cifrari spiegate ai giocatori | il riassunto sta **solo** nella console; le frasi da digitare non sono in `cifrari.js` |
| `$ErrorActionPreference = "Stop"` in PowerShell | git scrive su stderr: usare `$LASTEXITCODE` |
| Lista nera dei file da servire | `servi.ps1` usa una **lista bianca di estensioni**: una nera lasciava passare `Materials*.xlsx` |
| Compilare dentro `E:\D&D\...` | la `&` rompe gli script `.bat`: `fai_apk.py` copia i sorgenti in una cartella dal nome pulito |
| `INTERNET` nel manifest Android | **non si aggiunge**: e' il sistema operativo a far rispettare la regola 2 |
| Parole in chiaro dentro `dati.js` | non ci vanno **mai**: quel file sta anche sui telefoni dei giocatori. Le note della console danno chiave e forma cifrata, non la soluzione |
| Blocco di glifi decorativo sul foglio | il foglio porta il **reperto trascritto** con `simboli.py`: se torna rumore casuale, e' un bug |
| Numero del sigillo come codice d'apertura | il numero apre la **chiave**, non il reperto: per aprire c'e' un codice opaco di 4 segni, se no da `HUSA-2` si indovina `HUSA-3` |
| Due nomi per la stessa cosa | la tabella **I nomi** qui sopra e' vincolante: lo stesso numero chiamato in tre modi ha fatto perdere tempo al tavolo |

## Dove sta il resto

| Documento | Cosa c'è dentro |
|---|---|
| **`CODIFICA.md`** | **i tre aspetti del cifrario, l'ordine dei passaggi e come si sblocca ognuno.** Da leggere prima di toccare `cifrari.*`, il decodificatore o il banco delle chiavi |
| **`SPECIFICA-APP.md`** | le specifiche dell'app: contratto dei dati, le quattro modalità, gli invarianti |
| `cifrari.md` | il racconto dei tre cifrari, in prosa |
| `locazioni.md`, `enigmi.md` | le locazioni e i tre enigmi |

Sono tutti locali e in `.gitignore` perché contengono le soluzioni. Se stai per lavorare
sull'app, **leggi `CODIFICA.md` e `SPECIFICA-APP.md` prima.**
Se non ci sono nel checkout, chiedi ad Alessandro invece di indovinare.
