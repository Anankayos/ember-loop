# -*- coding: utf-8 -*-
"""Legge contenuti.md e costruisce tutto: dati.js, CHIAVI-MASTER.md, .segreti, stampa.html
   Uso:  python costruisci.py
   Se qualcosa non va, si ferma e ti dice esattamente cosa, in italiano."""
import base64, json, re, sys, os, subprocess

MARCA = "◆KINDLER·ARCHIVIO·v1◆\n"
ERRORI, AVVISI = [], []
def err(msg):  ERRORI.append(msg)
def avv(msg):  AVVISI.append(msg)

# ---------------------------------------------------------------- lettura
def leggi(path="contenuti.md"):
    if not os.path.exists(path):
        print(f"Non trovo {path}. Deve stare nella stessa cartella di questo script."); sys.exit(1)
    blocchi, corrente = [], None
    for n, riga in enumerate(open(path, encoding="utf-8"), 1):
        grezza = riga.rstrip("\n")
        if grezza.strip().startswith("#") and (corrente is None or not corrente["_corpo_aperto"]):
            continue
        m = re.match(r"^\s*===\s*([A-Z]+)\s*===\s*$", grezza)
        if m:
            if corrente: blocchi.append(corrente)
            corrente = {"_tipo": m.group(1), "_riga": n, "_corpo": [], "_corpo_aperto": False}
            continue
        if corrente is None:
            if grezza.strip(): avv(f"riga {n}: testo fuori da ogni blocco, ignorato -> {grezza.strip()[:50]}")
            continue
        if grezza.strip() == "---":
            corrente["_corpo_aperto"] = True; continue
        if corrente["_corpo_aperto"]:
            corrente["_corpo"].append(grezza); continue
        m = re.match(r"^\s*([a-zA-Zàèéìòù]+)\s*:\s*(.*)$", grezza)
        if m: corrente[m.group(1).lower()] = m.group(2).strip()
        elif grezza.strip(): err(f"riga {n}: non capisco questa riga. Serve  campo: valore  oppure  ---  -> {grezza.strip()[:50]}")
    if corrente: blocchi.append(corrente)
    for b in blocchi: b["_corpo"] = "\n".join(b["_corpo"]).strip()
    return blocchi

def campi(b, *nomi):
    for n in nomi:
        if not b.get(n):
            err(f"blocco {b['_tipo']} alla riga {b['_riga']}: manca il campo obbligatorio  {n}:")
    return all(b.get(n) for n in nomi)

# ---------------------------------------------------------------- cifrari
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def cesare(testo, scorrimento):
    """Sposta solo A-Z e a-z. Accenti e punteggiatura restano, cosi' il testo
       resta riconoscibilmente italiano una volta trovato lo scorrimento."""
    out = []
    for ch in testo:
        u = ch.upper()
        if u in AZ:
            n = AZ[(AZ.index(u) + scorrimento) % 26]
            out.append(n if ch.isupper() else n.lower())
        else:
            out.append(ch)
    return "".join(out)

def scorrimento_da(seme):
    """Scorrimento deterministico dal sigillo: 1..25, mai 0 (che non cifrerebbe)."""
    h = 0
    for c in seme: h = (h * 31 + ord(c)) % 25
    return h + 1

def cifra(testo, chiave):
    b = (MARCA + testo).encode("utf-8"); k = chiave.upper().encode("utf-8")
    return base64.b64encode(bytes(c ^ k[i % len(k)] for i, c in enumerate(b))).decode()
def decifra(b64, chiave):
    raw = base64.b64decode(b64); k = chiave.upper().encode("utf-8")
    t = bytes(c ^ k[i % len(k)] for i, c in enumerate(raw)).decode("utf-8")
    if not t.startswith(MARCA): raise ValueError("marcatore assente")
    return t[len(MARCA):]

# ---------------------------------------------------------------- costruzione
blocchi = leggi()
pianeti, testi, log, stanze = [], [], [], []
for b in blocchi:
    t = b["_tipo"]
    if t == "PIANETA":
        if campi(b, "id", "nome", "chiave", "meccanica"):
            pianeti.append(dict(id=b["id"], nome=b["nome"], sub=b.get("sottotitolo", ""),
                                chiave=b["chiave"].upper(), meccanica=b["meccanica"].upper(),
                                mecc_desc=b["_corpo"]))
    elif t == "TESTO":
        if campi(b, "sigillo", "pianeta", "titolo"):
            if not b["_corpo"]: err(f"TESTO {b['sigillo']}: manca il testo dopo la riga  ---")
            tipo = b.get("tipo", "chiave").lower()
            if tipo not in ("comune", "chiave"):
                err(f"TESTO {b['sigillo']}: tipo '{tipo}' non valido. Usa  tipo: comune  oppure  tipo: chiave")
            parole = [p.strip().upper() for p in b.get("parole", "").split(",") if p.strip()]
            if tipo == "comune" and not parole:
                err(f"TESTO {b['sigillo']}: e' di tipo comune ma non ha  parole:. "
                    f"I testi comuni servono a produrre le parole che il Consultatore digita nel log.")
            if tipo == "chiave" and parole:
                avv(f"TESTO {b['sigillo']}: e' di tipo chiave ma ha delle parole:. Verranno ignorate.")
            testi.append(dict(sigillo=b["sigillo"].upper(), pianeta=b["pianeta"].upper(),
                              titolo=b["titolo"], testo=b["_corpo"], tipo=tipo, parole=parole))
    elif t == "LOG":
        if campi(b, "sigillo", "pianeta", "titolo"):
            if not b.get("parola"):
                err(f"LOG {b['sigillo']}: manca  parola:. E' la parola che il Consultatore digita per aprire questa voce.")
            log.append(dict(id=b["sigillo"].upper(), sigillo=b["sigillo"].upper(),
                            pianeta=b["pianeta"].upper(), titolo=b["titolo"],
                            corpo=b["_corpo"], indizio=b.get("indizio", ""),
                            parola=b.get("parola", "").upper()))
    elif t == "STANZA":
        if campi(b, "id", "pianeta", "nome", "codice"):
            stanze.append(dict(id=b["id"].upper(), pianeta=b["pianeta"].upper(), nome=b["nome"],
                               codice=b["codice"].upper(), sblocca=b["_corpo"]))
    else:
        err(f"riga {b['_riga']}: tipo di blocco sconosciuto  === {t} ===  (ammessi: PIANETA, TESTO, LOG, STANZA)")

# ---------------------------------------------------------------- controlli
idp = {p["id"] for p in pianeti}
CHIAVI = {p["id"]: p["chiave"] for p in pianeti}
for t in testi:
    if t["pianeta"] not in idp and t["pianeta"] != "FIN":
        err(f"TESTO {t['sigillo']}: il pianeta '{t['pianeta']}' non esiste. Pianeti definiti: {sorted(idp)} (oppure FIN per il testo finale)")
for L in log:
    if L["pianeta"] not in idp: err(f"LOG {L['sigillo']}: pianeta '{L['pianeta']}' inesistente")
for s in stanze:
    if s["pianeta"] not in idp and s["pianeta"] != "FIN": err(f"STANZA {s['id']}: pianeta '{s['pianeta']}' inesistente")
# Nessuna chiave di ripiego nel codice: il testo finale deve avere il suo blocco PIANETA
# con  id: FIN  in contenuti.md, altrimenti e' un errore esplicito.
if any(t["pianeta"] == "FIN" for t in testi) and "FIN" not in CHIAVI:
    err("c'e' un TESTO con  pianeta: FIN  ma manca il blocco  === PIANETA ===  con  id: FIN  "
        "che ne definisce la chiave. Aggiungilo in contenuti.md.")

for nome, lista, chiave in (("TESTO", testi, "sigillo"), ("LOG", log, "sigillo"), ("STANZA", stanze, "id")):
    visti = {}
    for x in lista:
        if x[chiave] in visti: err(f"{nome} {x[chiave]}: sigillo/id duplicato, gia' usato")
        visti[x[chiave]] = 1

# ogni parola che apre una voce di log deve essere prodotta da un testo comune,
# altrimenti quella voce e' irraggiungibile e il ciclo fra i ruoli si spezza.
prodotte = {p for t in testi if t["tipo"] == "comune" for p in t["parole"]}

import unicodedata
def senza_accenti(x):
    return "".join(ch for ch in unicodedata.normalize("NFD", x) if unicodedata.category(ch) != "Mn")

for t in testi:
    if t["tipo"] != "comune": continue
    corpo = senza_accenti(t["testo"]).upper()
    for p in t["parole"]:
        if senza_accenti(p).upper() not in corpo:
            err(f"TESTO {t['sigillo']}: la parola '{p}' non compare nel testo. "
                f"Il Decifratore non potrebbe leggerla ad alta voce.")

# nessuna parola indicizzata puo' essere anche una chiave: le parole viaggiano
# dentro dati.js, quindi la chiave finirebbe pubblicata.
for p in sorted(prodotte | {L["parola"] for L in log if L["parola"]}):
    if p in set(CHIAVI.values()):
        err(f"la parola '{p}' e' anche una chiave di cifratura. Le parole sono nell'app, "
            f"quindi la chiave sarebbe pubblica. Cambiane una delle due.")
for L in log:
    if L["parola"] and L["parola"] not in prodotte:
        err(f"LOG {L['sigillo']}: la parola '{L['parola']}' non compare in nessun testo di tipo comune. "
            f"Il Consultatore non potrebbe mai riceverla. Parole disponibili: {sorted(prodotte) or 'nessuna'}")
# e ogni parola prodotta dovrebbe aprire qualcosa, altrimenti e' rumore
usate = {L["parola"] for L in log}
for p in sorted(prodotte - usate):
    avv(f"la parola '{p}' viene prodotta da un testo comune ma non apre nessuna voce di log.")

# ogni testo di tipo chiave dovrebbe avere un indizio che punta alla sua chiave
for t in testi:
    if t["tipo"] == "chiave":
        k = CHIAVI.get(t["pianeta"], "")
        if k and not any(k.lower() in (L["indizio"] or "").lower() or
                         L["pianeta"] == t["pianeta"] for L in log):
            avv(f"TESTO {t['sigillo']}: nessuna voce di log sembra puntare alla sua chiave.")

# i codici stanza non devono coincidere con una chiave: trapelerebbero nell'app
for s in stanze:
    if s["codice"] in CHIAVI.values():
        err(f"STANZA {s['id']}: il codice '{s['codice']}' e' anche una chiave di cifratura. "
            f"L'app contiene i codici stanza, quindi la chiave finirebbe pubblicata. Cambiane uno.")

if len(MARCA.encode()) <= max((len(c) for c in CHIAVI.values()), default=0):
    err("una chiave e' piu' lunga del marcatore di verifica: un suo prefisso aprirebbe i testi.")

if ERRORI:
    print("\n  NON HO COSTRUITO NIENTE. Errori da correggere in contenuti.md:\n")
    for e in ERRORI: print("   -", e)
    print()
    sys.exit(1)

# ---------------------------------------------------------------- autoverifica
for t in testi:
    if t["tipo"] == "comune":
        sc = scorrimento_da(t["sigillo"])
        assert cesare(cesare(t["testo"], sc), -sc) == t["testo"], t["sigillo"]
        continue
    k = CHIAVI[t["pianeta"]]; c = cifra(t["testo"], k)
    assert decifra(c, k) == t["testo"], t["sigillo"]
    for sbagliata in ("SBAGLIATA", "XYZ", k[:-1], k[:-2], k + "A", k.lower()):
        if sbagliata.upper() == k.upper(): continue
        try:
            decifra(c, sbagliata)
            err(f"TESTO {t['sigillo']}: la chiave errata '{sbagliata}' lo aprirebbe. Cambia chiave.")
        except Exception: pass
if ERRORI:
    print("\n  AUTOVERIFICA FALLITA:\n"); [print("   -", e) for e in ERRORI]; print(); sys.exit(1)

# ---------------------------------------------------------------- scrittura
def h(k):
    import hashlib; return hashlib.sha256(("ember::" + k.upper()).encode()).hexdigest()[:16]

dati = {
 "pianeti": [{kk: vv for kk, vv in p.items() if kk != "chiave"} | {"chiave_hash": h(p["chiave"])} for p in pianeti],
 "testi": [
   (dict(id=t["sigillo"], pianeta=t["pianeta"], titolo=t["titolo"], sigillo=t["sigillo"],
         tipo="comune", scorrimento=scorrimento_da(t["sigillo"]),
         cesare=cesare(t["testo"], scorrimento_da(t["sigillo"])), parole=t["parole"])
    if t["tipo"] == "comune" else
    dict(id=t["sigillo"], pianeta=t["pianeta"], titolo=t["titolo"], sigillo=t["sigillo"],
         tipo="chiave", cifra=cifra(t["testo"], CHIAVI[t["pianeta"]])))
   for t in testi],
 "log": log, "stanze": stanze, "fin_hash": h(CHIAVI["FIN"]),
}
with open("dati.js", "w", encoding="utf-8") as f:
    f.write("// GENERATO DA costruisci.py — non modificare a mano\n")
    f.write("window.DATI = " + json.dumps(dati, ensure_ascii=False, indent=1) + ";\n")

with open("CHIAVI-MASTER.md", "w", encoding="utf-8") as f:
    f.write("# CHIAVI — solo per il Master\n\nNon pubblicare questo file.\n\n## Chiavi di decifrazione\n\n")
    for p in pianeti: f.write(f"- **{p['nome']}** -> `{p['chiave']}`  (meccanica: {p['meccanica']})\n")
    f.write(f"- **Testo finale** -> `{CHIAVI['FIN']}`\n\n## Codici stanza\n\n")
    for s in stanze: f.write(f"- {s['nome']} -> `{s['codice']}` — {s['sblocca']}\n")

open(".segreti", "w", encoding="utf-8").write("\n".join(sorted(set(CHIAVI.values()))) + "\n")

# ---------------------------------------------------------------- perdite
# l'elenco dei file esclusi si legge da .gitignore, non e' scritto qui:
# cosi' aggiungere una riga a .gitignore aggiorna anche questo controllo.
esclusi = set()
if os.path.exists(".gitignore"):
    esclusi = {r.strip() for r in open(".gitignore", encoding="utf-8")
               if r.strip() and not r.strip().startswith("#")}
else:
    avv(".gitignore non trovato: considero pubblicabile qualunque file.")
pubblicabili = [f for f in os.listdir(".") if os.path.isfile(f) and f not in esclusi]
perdite = []
for f in pubblicabili:
    try: testo = open(f, encoding="utf-8", errors="ignore").read()
    except Exception: continue
    for sg in set(CHIAVI.values()):
        if sg in testo: perdite.append(f"{f} contiene la chiave {sg}")

print(f"\n  Costruito: {len(pianeti)} pianeti, {len(testi)} testi, {len(log)} voci di log, {len(stanze)} stanze")
print(f"  Scritti: dati.js, CHIAVI-MASTER.md, .segreti")
for a in AVVISI: print("  avviso:", a)
if perdite:
    print("\n  !! CHIAVI IN FILE PUBBLICABILI:")
    for p in perdite: print("     -", p)
    print("     Aggiungi quei file a .gitignore, oppure togli la chiave dal loro contenuto.\n")
    sys.exit(1)
print("  Nessuna chiave nei file pubblicabili.")
if os.path.exists("genera_stampe.py"):
    subprocess.run([sys.executable, "genera_stampe.py"])

# la copia offline si rigenera sempre, cosi' non puo' restare indietro
if os.path.exists("genera_offline.py"):
    subprocess.run([sys.executable, "genera_offline.py"])
print()
