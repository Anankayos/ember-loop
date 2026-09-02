# The Ember Loop — software di sessione

Quattro applicazioni in una pagina sola. Girano su qualsiasi telefono, non serve installare niente.

## Cosa c'è dentro

| File | Cosa fa |
|---|---|
| `index.html` + `app.js` + `dati.js` | L'app: Decifratore, Consultatore, Apritore, Console Master |
| `stampa.html` | Tutti i materiali da stampare: fogli reperto, sigilli QR, carte-stanza |
| `contenuti.py` | ⚠️ **MAI pubblicare.** Contiene chiavi, codici e tutti i testi in chiaro: e' il gioco intero. Resta solo sul tuo disco |
| `genera_stampe.py` | Rigenera `stampa.html` |
| `CHIAVI-MASTER.md` | ⚠️ **MAI pubblicare.** Le chiavi. Stampalo e tienilo con te |

## Pubblicare su GitHub Pages (5 minuti)

```bash
# 1. nuovo repo su github.com, poi:
git init && git add index.html app.js dati.js stampa.html README.md .gitignore 00-progetto.md
git commit -m "The Ember Loop"
git branch -M main
git remote add origin git@github.com:TUO-UTENTE/ember-loop.git
git push -u origin main
```

Poi su GitHub: **Settings → Pages → Source: `main` / root → Save**.
Dopo un paio di minuti l'app è su `https://TUO-UTENTE.github.io/ember-loop/`.

> **Nota importante:** `git add` sopra elenca i file uno a uno di proposito.
> Non fare `git add .` — ci finirebbe dentro `CHIAVI-MASTER.md` e i giocatori
> potrebbero leggere le chiavi. C'è anche un `.gitignore` che lo blocca.

## Perché GitHub Pages e non un file locale

La fotocamera (`getUserMedia`) è bloccata dai browser su `file://`.
Serve **https**, e Pages lo dà gratis. Una volta caricata, la pagina resta in cache:
funziona anche se il wifi cade a metà serata.

## Come si usa la sera

1. Ognuno dei tre apre il link e sceglie il proprio ruolo. **Non serve coordinarsi:** ogni telefono tiene il proprio stato.
2. Tu apri **Console di Sistema** su un quarto dispositivo.
3. I 30 minuti sono un **budget**, non un cronometro. Ogni azione (spostamento, traduzione, consultazione, enigma) costa **1d4+1** minuti: premi il bottone corrispondente e la console tira e scala da sola.
4. A zero: luce bianca. Premi **Nuovo loop** e si riparte da 30.

## Verifiche già fatte

- I 7 testi si aprono con la chiave giusta e **rifiutano 11 chiavi sbagliate** su 11, prefissi inclusi
- Nessuna chiave di cifratura è presente in `dati.js` o `app.js`
- I 4 enigmi di percorso sono **dimostrati risolvibili** per forza bruta
- Difficoltà misurata (percorsi validi / totali): 29% → 4,6% → 0,97% → 0,87%
- Il validatore JS concorda al 100% con quello Python su 24 casi
- Tutti i 13 sigilli QR renderizzati sono stati **riletti e decodificati** correttamente

## Modificare i testi

```bash
# apri contenuti.py, cambia quello che vuoi, poi:
python3 contenuti.py        # rigenera dati.js + CHIAVI-MASTER.md
python3 genera_stampe.py    # rigenera stampa.html
```
`contenuti.py` si auto-verifica: se una chiave sbagliata riuscisse ad aprire un testo, si ferma con un errore.
