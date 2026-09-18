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

## Come si costruisce

```bash
python costruisci.py        # contenuti.md -> dati.js, CHIAVI-MASTER.md, .segreti,
                            # poi genera_stampe.py e genera_offline.py
python controlla_testi.py   # controlla i testi prima di costruire
```

`costruisci.py` si rifiuta di costruire se qualcosa non va e spiega cosa, in italiano.
Quel comportamento è voluto: **meglio fermarsi che produrre materiale sbagliato da stampare.**

## Come si prova

```bash
python -m http.server 8080          # servire e aprire http://localhost:8080
./servi.ps1                          # serve sulla LAN SOLO i file pubblicabili
```

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
| `$ErrorActionPreference = "Stop"` in PowerShell | git scrive su stderr: usare `$LASTEXITCODE` |

## Dove sta il resto

Le specifiche complete stanno in **`SPECIFICA-APP.md`**, che è locale e in `.gitignore`
perché contiene le soluzioni. Se stai per lavorare sull'app, **leggila prima.**
Se non c'è nel checkout, chiedi ad Alessandro invece di indovinare.
