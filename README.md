# The Ember Loop — software di sessione

Quattro applicazioni in una pagina sola: **Decifratore**, **Consultatore**, **Apritore** e la
**Console** del narratore. Girano su qualsiasi telefono, non serve installare niente, e a
serata iniziata non chiedono niente alla rete.

## Cosa c'è dentro

| File | Cosa fa |
|---|---|
| `index.html` + `app.js` | l'app: le quattro modalità, nessuna dipendenza |
| `cifrari.js` | l'aritmetica dei cifrari; la verità è `cifrari.py`, che resta locale |
| `jsQR.min.js` | lettura dei sigilli QR, **locale apposta** |
| `dati.js` | *generato*: testi in chiaro, parole chiave **solo cifrate**, impronte |
| `stampa.html` | *generato*: un foglio-sigillo per testo e le carte-porta del narratore |
| `prova-offline.html` | *generato*: tutto in un file solo, zero richieste di rete |
| `costruisci.py` | da `contenuti.md` a tutto il resto; si ferma e spiega se qualcosa non va |
| `genera_stampe.py`, `genera_offline.py` | li lancia `costruisci.py` |
| `push.ps1`, `servi.ps1` | pubblicazione e rete locale, con la guardia sui segreti |
| `diagnostica.html` | prova della fotocamera dal telefono |

Restano **solo sul disco** (sono in `.gitignore`): `contenuti.md`, `CHIAVI-MASTER.md`, `.segreti`,
`cifrari.py`, i documenti di progetto, i verificatori e la cartella `prove/`.
Il formato di `contenuti.md` è descritto in `SPECIFICA-APP.md` §4.1, anche lei locale.

`dati.js`, `stampa.html` e `prova-offline.html` **non si modificano a mano**: si rigenerano.

## Costruire

```bash
pip install qrcode          # una volta: serve a disegnare i sigilli
python costruisci.py        # contenuti.md -> dati.js, CHIAVI-MASTER.md, .segreti, stampa.html, prova-offline.html
```

`costruisci.py` controlla tutto **prima** di scrivere: parole fra graffe senza il loro blocco,
chiavi che renderebbero un cifrario trasparente, citazioni mancanti, pianeti senza testi che
insegnino le regole, parole o codici lasciati in chiaro, griglie delle porte non verificate,
parole che non si potrebbero mai aprire. Se trova qualcosa si ferma, dice blocco, riga e cosa
fare, e non tocca niente. Alla fine rilegge `dati.js` dal disco e cerca i segreti in tutti i file
pubblicabili; se è tutto a posto dice **«Nessuna chiave nei file pubblicabili.»**

Con un `contenuti.md` ancora nel formato vecchio si ferma e dice cosa cambia.

## Provare

```bash
python cifrari.py                     # i cifrari: andata e ritorno, ogni parte portante
python controlla_testi.py             # i testi, prima di costruire
python verifica_griglie.py            # le porte di pietra, per forza bruta
pip install playwright                # una volta, per le prove del browser
python prove/confronto_cifrari.py     # cifrari.js contro cifrari.py, migliaia di casi
python prove/prova_costruisci.py      # una costruzione giusta, e ogni validazione che scatta
python prove/prova_app.py             # Playwright sulle quattro modalità, fotocamera compresa
```

Le prove del browser usano il Chromium di Playwright (`python -m playwright install chromium`)
oppure, se manca, Chrome o Edge già installati. Costruiscono un contenuto **finto** in una
cartella temporanea: non toccano mai `dati.js`, le stampe o il foglio chiavi del progetto.
Ogni prova stampa `OK` o `FALLITO` e cosa; un errore JavaScript è un fallimento.

## Servire la sera

```powershell
./servi.ps1                 # rete di casa: serve SOLO i file pubblicabili
```

Dai telefoni: `http://<indirizzo del PC>:8000/prova-offline.html`. In `http` sulla rete di casa la
fotocamera non parte (i browser la danno solo in `https` o su `localhost`): si digita il codice
stampato sotto il sigillo, e l'app lo dice invece di restare muta. Tutto il resto funziona.

`push.ps1` pubblica su GitHub Pages (https, quindi anche la fotocamera). Prima di pubblicare
rilegge `.segreti` e cerca quei contenuti **dentro** ogni file: se ne trova uno, si ferma.
Con i testi in chiaro in `dati.js`, se il repository resta pubblico è una scelta da fare prima.

## Come si usa

Tre telefoni, tre ruoli, più la Console del narratore. **Ogni telefono tiene il proprio stato**:
quello che si apre su un telefono si dice a voce agli altri.

- I costi stanno in un oggetto solo, `COSTI`, in cima ad `app.js`. Le app tirano da sole e
  dicono quanto è costato; il narratore scala dalla Console.
- In fondo alle schermate dei ruoli c'è un **codice stato**: il narratore lo scrive nel pannello
  *Parole aperte* della Console e vede quali parole ha già aperto quel telefono.
- **Failsafe:** se il tavolo si blocca, il narratore legge dal foglio chiavi stampato
  (`CHIAVI-MASTER.md`) e considera aperto. Le chiavi non stanno nell'app, di proposito.
