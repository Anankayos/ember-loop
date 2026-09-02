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

Tre telefoni, tre ruoli. Il quarto dispositivo e' la tua Console.

**Il ciclo che tiene insieme i ruoli:**

1. Il **Decifratore** apre un testo *comune*. Il software lo cracca da solo (Cesare, 25 scorrimenti, 1 minuto) e gli mostra delle **parole evidenziate**.
2. Le legge **ad alta voce**. E' il passaggio che rende i ruoli interdipendenti: l'app non le trasmette da sola.
3. Il **Consultatore** le digita nel diario di bordo. Se l'archivio conosce quella parola, restituisce un **indizio** — che punta a una chiave di decifrazione oppure alla meccanica di un enigma porta.
4. Il **Decifratore** usa quella chiave su un testo *chiave* (Vigenere: la forza bruta non basta). L'**Apritore** usa i suggerimenti sugli enigmi.

**I costi in minuti, e perche' contano:**

| Azione | Costo |
|---|---|
| Crack automatico di un testo comune | 1 min |
| Interrogare il diario con una parola | 1 min |
| Tentare una chiave (giusta o sbagliata) | **1d4+1** |

Insistere da soli su una chiave costa in media 3,5 minuti a tentativo. Passare dagli altri due ne costa 2 in tutto. **La scorciatoia passa sempre dai compagni** — e' conveniente collaborare, non obbligatorio.

**Lo storico.** Ogni app registra le proprie azioni con il costo. La Console mostra le ultime dodici e ha un campo per scalare a mano i minuti che i giocatori ti riferiscono.

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
