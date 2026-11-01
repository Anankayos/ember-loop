# -*- coding: utf-8 -*-
"""
Legge contenuti.md e costruisce tutto:

    dati.js             l'app: testi in chiaro, parole chiave SOLO cifrate, impronte
    CHIAVI-MASTER.md    il foglio del narratore               (NON pubblicare)
    .segreti            cio' che la guardia di push.ps1 cerca  (NON pubblicare)
    stampa.html         con genera_stampe.py
    prova-offline.html  con genera_offline.py

Uso:  python costruisci.py

Se qualcosa non va si ferma PRIMA di scrivere e dice in italiano il blocco, la
riga e cosa fare. E' voluto: quel materiale si stampa, e meglio fermarsi che
stampare una cosa sbagliata. Il formato di contenuti.md e' in SPECIFICA-APP.md §4.1;
i cifrari sono in cifrari.py, che e' la verita' e qui si usa soltanto.
"""
import base64, difflib, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
if QUI not in sys.path:
    sys.path.insert(0, QUI)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")      # una console cp1252 non deve far crollare niente

ERRORI, AVVISI = [], []
def err(msg): ERRORI.append(msg)
def avv(msg): AVVISI.append(msg)


# ------------------------------------------------------------------ normalizzazione e impronte
# Le stesse regole di cifrari.js: prove/confronto_cifrari.py controlla che coincidano.
def senza_accenti(x):
    return "".join(ch for ch in unicodedata.normalize("NFD", x) if unicodedata.category(ch) != "Mn")

def norm_parola(s):
    return re.sub(r"[^A-Z]", "", senza_accenti(s).upper())

def norm_codice(s):
    return re.sub(r"[^A-Z0-9]", "", senza_accenti(s).upper())

# ------------------------------------------------------------------ il codice del sigillo
# Il numero del reperto NON puo' essere anche il codice per aprirlo: visto un HUSA-2,
# chiunque indovina HUSA-3 e legge un reperto che non ha trovato. Il numero resta
# stampato - al Custode serve, e' dentro due chiavi su tre - ma per aprire il testo
# si digita un codice opaco di quattro segni, che dal numero non si ricava.
#
# Base32 di Crockford: niente I L O U, cosi' non si confondono con 1 0 e fra loro.
# Deriva dall'id, quindi non cambia da una costruzione all'altra: i fogli gia' stampati
# restano buoni.
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def codice_sigillo(sid, presi):
    grezzo = int(hashlib.sha256(("sigillo:" + sid).encode("utf-8")).hexdigest(), 16)
    for salto in range(200):                           # se due cadessero uguali, il secondo scala
        n, c = grezzo + salto, ""
        for _ in range(4):
            n, r = divmod(n, 32)
            c = B32[r] + c
        if c not in presi:
            presi.add(c)
            return c
    raise RuntimeError("non riesco a dare un codice distinto a " + sid)


def qr_compatto(testo):
    """La matrice del QR impacchettata bit a bit. Una pagina con 58 QR disegnati dentro
       peserebbe mezzo mega: cosi' sono 6 KB, e li disegna chi li mostra."""
    try:
        import qrcode
    except ImportError:
        return ""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2)
    q.add_data(testo)
    q.make(fit=True)
    m = q.get_matrix()
    bit = "".join("1" if c else "0" for r in m for c in r)
    grezzo = bytes(int(bit[i:i + 8].ljust(8, "0"), 2) for i in range(0, len(bit), 8))
    return "%d:%s" % (len(m), base64.b64encode(grezzo).decode("ascii"))


def impronta(s):
    """SHA-256 troncato a 16 esadecimali: serve a riconoscere un risultato, mai a produrlo."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ il formato
BLOCCHI = {
    "PIANETA": (("id", "nome", "tema", "meccanica"), ("codice_alfabeto", "codice_ordine", "simbolo", "rune")),
    "TESTO":   (("sigillo", "pianeta", "titolo", "tipo"), ("cita", "rivela", "luogo", "posto")),
    "PAROLA":  (("parola", "pianeta", "mondo"), ("apre",)),
    "LOG":     (("sigillo", "pianeta", "titolo"), ()),
    "ENIGMA":  (("id", "pianeta", "nome", "parola"), ()),
    "STANZA":  (("id", "pianeta", "nome", "puzzle"), ("griglia",)),
}
NOME_DI = {"PIANETA": "id", "TESTO": "sigillo", "PAROLA": "parola", "LOG": "sigillo", "ENIGMA": "id", "STANZA": "id"}
PERCHE_CAMPO = {
    ("PIANETA", "tema"): "(sofferenza, isolamento, amicizia...)",
    ("PIANETA", "meccanica"): "(la regola del loop che il pianeta restituisce)",
    ("TESTO", "tipo"): "(lore, aiuto oppure propedeutico)",
    ("TESTO", "luogo"): "(la locazione sulla mappa dove sta il sigillo)",
    ("TESTO", "posto"): "(il punto preciso: coordinata e descrizione, per il narratore che lo mette)",
    ("TESTO", "pianeta"): "(l'id di un blocco PIANETA)",
    ("PAROLA", "pianeta"): "(dove compare: la stessa parola puo' avere una voce per pianeta)",
    ("PAROLA", "mondo"): "(il mondo che l'ha scritta: decide il simbolo accanto alla parola e quindi il cifrario)",
    ("ENIGMA", "parola"): "(la parola decifrata che ne apre l'ingresso)",
    ("STANZA", "puzzle"): "(bordi, separazione oppure simmetria)",
}
TIPI_TESTO = ("lore", "aiuto", "propedeutico")
PARTI = ("alfabeto", "ordine", "chiave")
PUZZLE = ("bordi", "separazione", "simmetria")
# gli strumenti che girano in coda alla costruzione, e cosa rifanno
GENERATORI = {"genera_stampe.py": "stampa.html", "genera_offline.py": "prova-offline.html",
              "genera_master.py": "master.html"}
SIMBOLI = {"HUSA": "◆", "POLIS": "▲", "IRIS": "●"}       # se PIANETA non ne sceglie uno
# Come si trova la chiave, mondo per mondo: e' il lavoro del Custode, e vale il mondo
# che ha SCRITTO la parola, non il pianeta dove la parola compare. Tutte e tre si applicano
# con quello che si ha davanti, senza cercare altrove (cifrari.py, sezione CHIAVE).
PROCEDIMENTO = {
    "HUSA": "il numero del sigillo piu' le lettere della parola cifrata",
    "POLIS": "il numero del sigillo per il posto della parola nel reperto (1a, 2a, 3a...)",
    "IRIS": "la prima parola in chiaro del reperto",
}
# ------------------------------------------------------------------ la scala di difficolta'
# Un sigillo e' difficile per quanto lavoro a mano chiede al tavolo, non per come e' scritto.
# Il peso di una parola sono le lettere da trasformare piu' i passi della chiave: uno su Husa
# e Polis, uno per lettera su Iris.
#
# Ma il peso si paga in due momenti, e vanno tenuti separati:
#   ORA   le parole che quel mondo ha scritto da se'. Si aprono appena si imparano le sue tre
#         regole, cioe' alla prima visita: e' questa la difficolta' che il tavolo sente.
#   POI   le parole scritte da un altro mondo. Non sono piu' difficili: sono rinviate, e il
#         sigillo si riapre al ritorno. Un sigillo pesante di POI non e' un muro.
# La salita e' la salita di ORA. SCALA: fino a quanto peso, che livello.
SCALA = (0, 8, 18, 32)
TRATTO = "—"
NOME_LIVELLO = {0: "lettura", 1: "facile", 2: "medio", 3: "duro", 4: "finale"}

def livello_di(peso):
    if peso == 0:
        return 0
    return sum(1 for s in SCALA if peso > s)

CAMPI_VECCHI = {("PIANETA", "chiave"), ("PIANETA", "sottotitolo"), ("TESTO", "parole"),
                ("LOG", "parola"), ("LOG", "indizio"), ("STANZA", "codice")}


def leggi(path):
    blocchi, cur = [], None
    with open(path, encoding="utf-8-sig") as f:
        righe = f.read().split("\n")
    for n, riga in enumerate(righe, 1):
        grezza = riga.rstrip("\r")
        s = grezza.strip()
        m = re.match(r"^===\s*([A-Za-z]+)\s*===$", s)
        if m:
            cur = {"tipo": m.group(1).upper(), "riga": n, "campi": {}, "righe": {}, "corpo": [], "aperto": False}
            blocchi.append(cur)
            continue
        if cur is None:
            if s and not s.startswith("#"):
                err(f"riga {n}: testo fuori da ogni blocco. Un blocco comincia con una riga come  === TESTO ===  -> {s[:60]}")
            continue
        if cur["aperto"]:
            cur["corpo"].append((n, grezza))
            continue
        if not s or s.startswith("#"):
            continue
        if s == "---":
            cur["aperto"] = True
            continue
        m = re.match(r"^([A-Za-z_]+)\s*:(.*)$", s)
        if not m:
            err(f"riga {n}, blocco {cur['tipo']} della riga {cur['riga']}: non capisco questa riga. "
                f"Prima di  ---  vanno solo righe  campo: valore  -> {s[:60]}")
            continue
        nome, val = m.group(1).lower(), m.group(2).strip()
        val = "" if val.startswith("#") else re.sub(r"\s+#.*$", "", val).strip()   # i commenti in coda
        if nome in cur["campi"]:
            err(f"riga {n}: il campo  {nome}:  compare due volte nello stesso blocco {cur['tipo']} "
                f"(la prima alla riga {cur['righe'][nome]}).")
        cur["campi"][nome], cur["righe"][nome] = val, n
    for b in blocchi:                                  # righe vuote in testa e in coda al corpo
        while b["corpo"] and not b["corpo"][0][1].strip(): b["corpo"].pop(0)
        while b["corpo"] and not b["corpo"][-1][1].strip(): b["corpo"].pop()
    return blocchi


def dove(b, campo=None):
    nome = b["campi"].get(NOME_DI.get(b["tipo"], ""), "")
    riga = b["righe"].get(campo, b["riga"]) if campo else b["riga"]
    return f"riga {riga}, === {b['tipo']} ===" + (f" {nome.upper()}" if nome else "")

def corpo_di(b):
    return "\n".join(r for _, r in b["corpo"]).strip()


def formato_vecchio(blocchi):
    """Il contenuti.md di prima (tipo comune/chiave, parole:, chiave:...) non si converte da solo:
       i codici, le parole fra graffe e i nuovi blocchi li sceglie Alessandro."""
    trovati = [f"riga {b['righe'][k]} {b['tipo']} {k}:" for b in blocchi for k in b["campi"] if (b["tipo"], k) in CAMPI_VECCHI]
    trovati += [f"riga {b['righe']['tipo']} TESTO tipo: {b['campi']['tipo']}" for b in blocchi
                if b["tipo"] == "TESTO" and b["campi"].get("tipo", "").lower() in ("comune", "chiave")]
    if not trovati:
        return False
    print("\n  NON HO COSTRUITO NIENTE: contenuti.md e' ancora nel formato vecchio.\n")
    print("  Il formato nuovo (SPECIFICA-APP.md §4.1) cambia queste cose:")
    print("   - PIANETA: niente piu'  chiave:  e  sottotitolo:  -- servono  tema:,  codice_alfabeto:  e")
    print("              codice_ordine:  (i codici kindler, le frasi che i giocatori digitano)")
    print("   - TESTO:   tipo:  diventa  lore | aiuto | propedeutico ; niente piu'  parole:  --")
    print("              le parole chiave si marcano fra graffe dentro il testo")
    print("   - PAROLA:  blocco nuovo, uno per ogni parola fra graffe (parola:, pianeta:, apre:)")
    print("   - LOG:     niente piu'  parola:  e  indizio:  -- e' la PAROLA a dire quale voce apre")
    print("   - ENIGMA:  blocco nuovo (id:, pianeta:, nome:, parola:)")
    print("   - STANZA:  niente piu'  codice:  -- serve  puzzle: bordi | separazione | simmetria")
    print("\n  Dove l'ho visto:")
    for t in trovati[:12]:
        print("     " + t)
    if len(trovati) > 12:
        print(f"     ... e altri {len(trovati) - 12}")
    print("\n  Chi rimedia: Alessandro. I testi, le parole chiave e i codici li scegli tu: non li invento io.")
    print("  dati.js, CHIAVI-MASTER.md e .segreti restano quelli di prima.\n")
    return True


# ------------------------------------------------------------------ le parole fra graffe
def segmenta(b):
    """Il corpo di un TESTO in pezzi: ("c", chiaro) e ("p", PAROLA, riga)."""
    testo = "\n".join(r for _, r in b["corpo"])
    if not b["corpo"]:
        return []
    riga_di = lambda off: b["corpo"][testo.count("\n", 0, off)][0]
    pezzi, pos, coperti = [], 0, set()
    for m in re.finditer(r"\{([^{}\n]*)\}", testo):
        if m.start() > pos:
            pezzi.append(("c", testo[pos:m.start()]))
        coperti.update(range(m.start(), m.end()))
        grezza, riga = m.group(1).strip(), riga_di(m.start())
        if not grezza:
            err(f"riga {riga}, === TESTO === {b['campi'].get('sigillo', '')}: graffe vuote. Fra graffe va la parola da cifrare.")
        # "Monte Alto" si cifra come MONTEALTO: il cifrario conosce solo le lettere kindler
        pezzi.append(("p", grezza.upper(), riga))
        pos = m.end()
    if pos < len(testo):
        pezzi.append(("c", testo[pos:]))
    for i, ch in enumerate(testo):
        if ch in "{}" and i not in coperti:
            err(f"riga {riga_di(i)}, === TESTO === {b['campi'].get('sigillo', '')}: una graffa  {ch}  senza la sua compagna. "
                f"Una parola chiave si scrive cosi':  {{PAROLA}}  (sulla stessa riga).")
    # il primo e l'ultimo pezzo in chiaro non portano gli a capo del file
    if pezzi and pezzi[0][0] == "c":
        pezzi[0] = ("c", pezzi[0][1].lstrip("\n"))
    if pezzi and pezzi[-1][0] == "c":
        pezzi[-1] = ("c", pezzi[-1][1].rstrip())
    return [p for p in pezzi if p[0] == "p" or p[1]]


def numero_sigillo(s):
    m = re.search(r"(\d+)$", s or "")
    return int(m.group(1)) if m else None


def parola_intera(w, testo):
    return re.search(r"(?<![A-Z])" + re.escape(w) + r"(?![A-Z])", senza_accenti(testo).upper()) is not None


def forme_codice(c):
    """Come un codice puo' comparire scritto: con i suoi trattini, con gli spazi, tutto attaccato."""
    parti = re.findall(r"[A-Z0-9]+", senza_accenti(c).upper())
    return {c.strip().upper(), " ".join(parti), "".join(parti)} - {""}


def contiene_codice(testo, cod):
    """Vero se il testo contiene quella frase, comunque sia scritta (trattini, spazi, maiuscole)."""
    spaziato = " " + " ".join(re.findall(r"[A-Z0-9]+", senza_accenti(testo or "").upper())) + " "
    parti = re.findall(r"[A-Z0-9]+", senza_accenti(cod).upper())
    return (" " + " ".join(parti) + " ") in spaziato or (" " + "".join(parti) + " ") in spaziato


def chiaro_di(t):
    """Quello che di un testo si legge senza decifrare niente: titolo e pezzi in chiaro."""
    return t["titolo"] + "\n" + "\n".join(p[1] for p in t["pezzi"] if p[0] == "c")


def fughe(dati, parole, codici):
    """Cerca in ogni stringa di dati.js (le impronte escluse) le parole chiave intere
       e i codici delle regole. -> [descrizioni]"""
    trovate = []
    def dentro(x, dove_):
        if isinstance(x, dict):
            etichetta = x.get("id", dove_)
            for k, v in x.items():
                if not k.endswith("hash"):
                    dentro(v, f"{etichetta}.{k}" if isinstance(etichetta, str) else k)
        elif isinstance(x, list):
            for v in x:
                dentro(v, dove_)
        elif isinstance(x, str):
            su = senza_accenti(x).upper()
            spaziato = " " + " ".join(re.findall(r"[A-Z0-9]+", su)) + " "
            for w in parole:
                if parola_intera(w, x):
                    trovate.append(f"la parola chiave {w} in chiaro in {dove_}")
            for c in codici:
                parti = re.findall(r"[A-Z0-9]+", senza_accenti(c).upper())
                if (" " + " ".join(parti) + " ") in spaziato or (" " + "".join(parti) + " ") in spaziato:
                    trovate.append(f"il codice {c} in chiaro in {dove_}")
    dentro(dati, "dati.js")
    return trovate


def pubblicabili():
    """I file che push.ps1 pubblicherebbe e servi.ps1 servirebbe: tutti tranne quelli in .gitignore.
       L'elenco si legge da .gitignore, cosi' aggiungere una riga li' aggiorna anche questo."""
    esclusi = set()
    if os.path.exists(".gitignore"):
        esclusi = {r.strip().rstrip("/") for r in open(".gitignore", encoding="utf-8")
                   if r.strip() and not r.strip().startswith("#")}
    else:
        avv(".gitignore non trovato: considero pubblicabile qualunque file.")
    return [f for f in sorted(os.listdir(".")) if os.path.isfile(f) and f not in esclusi]


def perdite_nei_file(segreti, file, sostituti=None):
    """La stessa ricerca di push.ps1: ogni riga di .segreti, lettera per lettera, maiuscole comprese."""
    out = []
    for f in file:
        if sostituti and f in sostituti:
            testo = sostituti[f]
        else:
            try:
                testo = open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
        for sg in segreti:
            if sg in testo:
                i = testo.index(sg)
                attorno = testo[max(0, i - 25):i + len(sg) + 25].replace("\n", " ")
                out.append(f"{f} contiene {sg}  (…{attorno}…)")
    return out


# ------------------------------------------------------------------ la costruzione
def main():
    if not os.path.exists("contenuti.md"):
        print("\n  Non trovo contenuti.md. Deve stare nella cartella da cui lanci questo script.\n")
        return 1
    try:
        import cifrari as C
    except ImportError:
        print("\n  Non trovo cifrari.py: e' in .gitignore, sta solo sul disco di Alessandro. Senza non cifro niente.\n")
        return 1
    import simboli as SIM
    guai_alfabeto = SIM.controlla()
    if guai_alfabeto:
        print("\n  L'alfabeto di simboli non va: " + "; ".join(guai_alfabeto) + "\n")
        return 1

    blocchi = leggi("contenuti.md")
    if formato_vecchio(blocchi):
        return 1

    pianeti, testi, parole, logs, enigmi, stanze = [], [], [], [], [], []
    for b in blocchi:
        t = b["tipo"]
        if t not in BLOCCHI:
            err(f"riga {b['riga']}: blocco sconosciuto  === {t} ===. Quelli ammessi: {', '.join(BLOCCHI)}.")
            continue
        obbl, fac = BLOCCHI[t]
        ammessi = set(obbl) | set(fac)
        for k in b["campi"]:
            if k not in ammessi:
                simile = difflib.get_close_matches(k, sorted(ammessi), 1)
                err(f"{dove(b, k)}: campo sconosciuto  {k}:" + (f"  -- forse  {simile[0]}:  ?" if simile
                    else f"  -- in un blocco {t} vanno: {', '.join(sorted(ammessi))}."))
        mancano = [k for k in obbl if not b["campi"].get(k)]
        for k in mancano:
            err(f"{dove(b)}: manca il campo  {k}:  {PERCHE_CAMPO.get((t, k), '')}".rstrip())
        if mancano:
            continue
        c = b["campi"]
        if t == "PIANETA":
            # rune: le parole che si posano alla fine. Non sono un cancello dell'app (il
            # narratore le riconosce al tavolo), ma devono stare scritte da qualche parte
            # che si controlla, se no il giorno della partita non le sa nessuno.
            pianeti.append(dict(b=b, id=c["id"].upper(), nome=c["nome"], tema=c["tema"],
                                meccanica=c["meccanica"].upper(), mecc_desc=corpo_di(b),
                                simbolo=c.get("simbolo", "") or SIMBOLI.get(c["id"].upper(), "?"),
                                codice_alfabeto=c.get("codice_alfabeto", ""), codice_ordine=c.get("codice_ordine", ""),
                                rune=[norm_parola(x) for x in re.split(r"[,;]+", c.get("rune", "")) if x.strip()]))
        elif t == "TESTO":
            tipo = c["tipo"].lower()
            if tipo not in TIPI_TESTO:
                err(f"{dove(b, 'tipo')}: tipo  {c['tipo']}  non esiste. Usa  lore,  aiuto  oppure  propedeutico.")
            rivela = [x.lower() for x in re.split(r"[\s,]+", c.get("rivela", "")) if x]
            for x in rivela:
                if x not in PARTI:
                    err(f"{dove(b, 'rivela')}: rivela  {x}  non esiste. Un testo propedeutico rivela  alfabeto,  ordine  o  chiave.")
            if tipo == "propedeutico" and not rivela:
                err(f"{dove(b)}: e' propedeutico ma non dice cosa rivela. Aggiungi  rivela: alfabeto  (oppure ordine, "
                    f"chiave, o piu' d'una separate da virgola): serve a controllare che ogni pianeta insegni le sue regole.")
            if tipo != "propedeutico" and rivela:
                err(f"{dove(b, 'rivela')}:  rivela:  vale solo per i testi di tipo propedeutico.")
            sig = c["sigillo"].upper()
            if not re.match(r"^[A-Z]+-\d+$", sig):
                err(f"{dove(b, 'sigillo')}: il sigillo  {c['sigillo']}  va scritto come KNDL-03: lettere, trattino, numero. "
                    f"Il numero serve: su alcuni pianeti e' la chiave.")
            if not corpo_di(b):
                err(f"{dove(b)}: manca il testo dopo la riga  ---")
            testi.append(dict(b=b, id=sig, pianeta=c["pianeta"].upper(), titolo=c["titolo"], tipo=tipo,
                              luogo=c.get("luogo", ""), posto=c.get("posto", ""),
                              cita=[x.strip().upper() for x in re.split(r"[,;]+", c.get("cita", "")) if x.strip()],
                              rivela=rivela, pezzi=segmenta(b)))
        elif t == "PAROLA":
            mondo = c["mondo"].upper()
            if mondo not in C.CIFRARI:
                err(f"{dove(b, 'mondo')}: mondo  {c['mondo']}  non ha un cifrario. I mondi che scrivono sono: "
                    f"{', '.join(C.CIFRARI)}.")
            w = norm_parola(c["parola"])
            if w != c["parola"].strip().upper():
                # l'alfabeto kindler non ha accenti ne' spazi: "Monte Alto" si cifra MONTEALTO,
                # e chi la digita nell'app la ritrova lo stesso. Ma va detto, non fatto di nascosto.
                avv(f"{dove(b, 'parola')}: {c['parola'].strip()} viene cifrata come {w} "
                    f"(l'alfabeto kindler non ha accenti, spazi ne' segni). Nel foglio chiavi la trovi cosi'.")
            parole.append(dict(b=b, parola=w, scritta=c["parola"].strip(),
                               pianeta=c["pianeta"].upper(), mondo=mondo,
                               apre=c.get("apre", "").upper(), nota=corpo_di(b)))
        elif t == "LOG":
            if not corpo_di(b):
                err(f"{dove(b)}: manca il corpo della voce dopo la riga  ---")
            logs.append(dict(b=b, id=c["sigillo"].upper(), pianeta=c["pianeta"].upper(), titolo=c["titolo"], corpo=corpo_di(b)))
        elif t == "ENIGMA":
            if not corpo_di(b):
                err(f"{dove(b)}: manca, dopo la riga  ---, il testo che il narratore legge quando il luogo si apre.")
            enigmi.append(dict(b=b, id=c["id"].upper(), pianeta=c["pianeta"].upper(), nome=c["nome"],
                               parola=c["parola"].strip().upper(), testo=corpo_di(b)))
        elif t == "STANZA":
            pz = c["puzzle"].lower()
            if pz not in PUZZLE:
                err(f"{dove(b, 'puzzle')}: puzzle  {c['puzzle']}  non esiste. Usa  bordi,  separazione  oppure  simmetria.")
            if not corpo_di(b):
                err(f"{dove(b)}: manca, dopo la riga  ---, il testo che compare quando la porta si apre.")
            stanze.append(dict(b=b, id=c["id"].upper(), pianeta=c["pianeta"].upper(), nome=c["nome"], puzzle=pz,
                               griglia=c.get("griglia", "").upper(), sblocca=corpo_di(b)))

    # ---- identificativi unici
    for nome, lista in (("PIANETA", pianeti), ("TESTO", testi), ("LOG", logs), ("ENIGMA", enigmi), ("STANZA", stanze)):
        visti = {}
        for x in lista:
            if x["id"] in visti:
                err(f"{dove(x['b'])}: {x['id']} e' gia' usato alla riga {visti[x['id']]}. Ogni {nome} vuole il suo.")
            visti.setdefault(x["id"], x["b"]["riga"])
    for L in logs:
        if any(t["id"] == L["id"] for t in testi):
            err(f"{dove(L['b'])}: {L['id']} e' anche il sigillo di un TESTO. Una voce di registro e un testo non possono chiamarsi uguale.")
    coppie = {}
    for w in parole:
        k = (w["parola"], w["pianeta"])
        if k in coppie:
            err(f"{dove(w['b'])}: la parola {w['parola']} ha gia' un blocco per {w['pianeta']} alla riga {coppie[k]}.")
        coppie.setdefault(k, w["b"]["riga"])

    # ---- pianeti e codici delle regole
    P = {p["id"]: p for p in pianeti}
    cifrati = [p for p in pianeti if p["id"] in C.CIFRARI]
    for p in cifrati:
        for parte in ("alfabeto", "ordine"):
            if not norm_codice(p["codice_" + parte]):
                err(f"{dove(p['b'])}: manca  codice_{parte}:  -- la frase kindler che i giocatori digitano per "
                    f"l'{parte} di {p['nome']}. La scegli tu, Alessandro.")
    for p in pianeti:
        if p["id"] not in C.CIFRARI and (p["codice_alfabeto"] or p["codice_ordine"]):
            avv(f"{dove(p['b'])}: {p['id']} non ha un cifrario in cifrari.py, i suoi codici non servono a niente.")
    codici = [(p, parte, p["codice_" + parte]) for p in cifrati for parte in ("alfabeto", "ordine") if norm_codice(p["codice_" + parte])]
    for i, (p1, a1, c1) in enumerate(codici):
        for p2, a2, c2 in codici[i + 1:]:
            if norm_codice(c1) == norm_codice(c2):
                err(f"il codice dell'{a1} di {p1['id']} e quello dell'{a2} di {p2['id']} sono la stessa frase: "
                    f"l'app non saprebbe quale regola applicare. Cambiane uno.")
    for x in testi + parole + logs + enigmi + stanze:
        if x["pianeta"] not in P:
            err(f"{dove(x['b'], 'pianeta')}: il pianeta  {x['pianeta']}  non esiste. Pianeti definiti: {', '.join(P) or 'nessuno'}.")

    # ---- 1. ogni parola fra graffe ha il suo blocco PAROLA, sul pianeta dove compare
    occorrenze = []                                   # (testo, parola, riga, com'era scritta)
    for t in testi:
        for pz in t["pezzi"]:
            if pz[0] == "p" and norm_parola(pz[1]):
                occorrenze.append((t, norm_parola(pz[1]), pz[2], pz[1]))
    voce_di = {(w["parola"], w["pianeta"]): w for w in parole}
    parole_note = {w["parola"] for w in parole}
    for t, w, riga, grezza in occorrenze:
        if (w, t["pianeta"]) not in voce_di:
            stesso = sorted(x["parola"] for x in parole if x["pianeta"] == t["pianeta"])
            simili = difflib.get_close_matches(w, stesso, 2)
            altrove = sorted({x["pianeta"] for x in parole if x["parola"] == w})
            consiglio = (f" Forse volevi {' o '.join(simili)}?" if simili else "") + \
                        (f" C'e' un blocco per {', '.join(altrove)}: una parola vuole un blocco per ogni pianeta su cui compare." if altrove else "")
            err(f"riga {riga}, === TESTO === {t['id']}: {{{grezza}}} non ha un blocco  === PAROLA ===  per {t['pianeta']}.{consiglio} "
                f"Se e' una parola nuova, aggiungi:  === PAROLA ===  parola: {grezza}  pianeta: {t['pianeta']}  mondo: ...")

    # ---- il mondo che ha scritto una parola e' uno solo: e' il simbolo che le sta accanto,
    #      e decide il cifrario ovunque la parola compaia
    mondo_di = {}
    for w in parole:
        if not w["mondo"]:
            continue
        if w["parola"] in mondo_di and mondo_di[w["parola"]][0] != w["mondo"]:
            altro = mondo_di[w["parola"]]
            err(f"{dove(w['b'], 'mondo')}: {w['parola']} qui e' di {w['mondo']}, alla riga {altro[1]['riga']} e' di {altro[0]}. "
                f"Il simbolo di una parola e' uno solo: la stessa parola si legge nello stesso modo su tutti i pianeti.")
        mondo_di.setdefault(w["parola"], (w["mondo"], w["b"]))

    # ---- 3 e 4. le citazioni. Con le regole nuove non portano piu' nessuna chiave:
    # restano per il rimando che l'app mostra in fondo al testo, e devono esistere.
    sigilli = {t["id"] for t in testi}
    log_id = {L["id"] for L in logs}
    apre_log = {}                                      # LOG -> parole che lo aprono
    for w in parole:
        if w["apre"]:
            if w["apre"] not in log_id:
                err(f"{dove(w['b'], 'apre')}: apre  {w['apre']}, ma quella voce di registro non esiste. "
                    f"Voci definite: {', '.join(sorted(log_id)) or 'nessuna'}.")
            apre_log.setdefault(w["apre"], set()).add(w["parola"])

    risolte = {}
    def citate(t):
        """La riga  cita:  di un testo, risolta una volta sola: (sigilli, voci di registro, parole)."""
        if t["id"] in risolte:
            return risolte[t["id"]]
        sig = [x for x in t["cita"] if x in sigilli]
        voci = [x for x in t["cita"] if x in log_id]
        dette = [norm_parola(x) for x in t["cita"] if norm_parola(x) in parole_note]
        for x in t["cita"]:
            if x not in sigilli and x not in log_id and norm_parola(x) not in parole_note:
                err(f"{dove(t['b'], 'cita')}: cita  {x}, che non e' ne' un sigillo, ne' una voce di registro, ne' una parola chiave.")
        risolte[t["id"]] = (sig, voci, dette)
        return risolte[t["id"]]

    for t in testi:
        citate(t)                                      # basta che quello che cita esista

    # ---- 5. ogni pianeta insegna le sue tre regole, e le due frasi si trovano li' dentro
    IL = {"alfabeto": "l'alfabeto", "ordine": "l'ordine", "chiave": "la chiave"}
    for p in cifrati:
        for parte in PARTI:
            propedeutici = [t for t in testi if t["pianeta"] == p["id"] and t["tipo"] == "propedeutico" and parte in t["rivela"]]
            if not propedeutici:
                err(f"{dove(p['b'])}: {p['nome']} non ha un testo propedeutico che riveli {IL[parte]}"
                    + (f" ({PROCEDIMENTO[p['id']]})" if parte == "chiave" else "")
                    + f". Serve almeno un  === TESTO ===  con  pianeta: {p['id']},  tipo: propedeutico,  rivela: {parte}.")
                continue
            cod = p.get("codice_" + parte, "")          # la chiave non ha una frase da digitare: e' una regola
            if cod and not any(contiene_codice(chiaro_di(t), cod) for t in propedeutici):
                err(f"{dove(p['b'], 'codice_' + parte)}: la frase  {cod}  non compare in nessuno dei testi propedeutici di "
                    f"{p['nome']} ({', '.join(t['id'] for t in propedeutici)}). I giocatori la digitano: se non e' scritta "
                    f"da qualche parte, non la troveranno mai.")

    # ---- le rune: devono essere parole che il tavolo puo' davvero avere in mano
    for p in pianeti:
        for r in p["rune"]:
            if r not in parole_note:
                err(f"{dove(p['b'], 'rune')}: fra le rune di {p['nome']} c'e' {r}, che non e' una parola chiave. "
                    f"Le rune si posano alla fine: devono essere parole che il tavolo ha decifrato.")
        mondi = [mondo_di[r][0] for r in p["rune"] if r in mondo_di]
        if len(p["rune"]) > 1 and len(set(mondi)) < len(mondi):
            doppi = sorted({m for m in mondi if mondi.count(m) > 1})
            avv(f"{dove(p['b'], 'rune')}: le rune di {p['nome']} non vengono da mondi diversi "
                f"({', '.join(doppi)} compare piu' di una volta): per averle tutte bastera' meno di tre pianeti.")

    # ---- 7. gli enigmi si aprono con parole che esistono
    enigma_di = {}
    for E in enigmi:
        if E["parola"] not in parole_note:
            err(f"{dove(E['b'], 'parola')}: si apre con {E['parola']}, ma non c'e' nessun blocco PAROLA con quella parola.")
        if E["parola"] in enigma_di:
            err(f"{dove(E['b'], 'parola')}: {E['parola']} apre gia' il luogo {enigma_di[E['parola']]}. Un luogo, una parola.")
        enigma_di.setdefault(E["parola"], E["id"])

    # ---- le porte di pietra: la griglia deve esistere ed essere verificata
    griglie, esiti_griglie = {}, {}
    try:
        import verifica_griglie as VG
        griglie = VG.leggi_griglie("app.js")
    except ImportError:
        err("manca verifica_griglie.py (e' in .gitignore): senza, le griglie delle porte non sono verificate e non costruisco.")
    except (OSError, ValueError) as e:
        err(f"non riesco a leggere le griglie da app.js: {e}")
    if griglie:
        errori_g, esiti_griglie = VG.verifica(griglie)
        for e in errori_g:
            err(e + "  -> rilancia  python verifica_griglie.py  per i dettagli.")
        for s in stanze:
            if s["puzzle"] not in PUZZLE:
                continue
            if s["griglia"]:
                if s["griglia"] not in griglie:
                    err(f"{dove(s['b'], 'griglia')}: la griglia {s['griglia']} non esiste. Per {s['puzzle']} ci sono: "
                        f"{', '.join(k for k, g in griglie.items() if g['tipo'] == s['puzzle'])}.")
                elif griglie[s["griglia"]]["tipo"] != s["puzzle"]:
                    err(f"{dove(s['b'], 'griglia')}: la griglia {s['griglia']} e' di tipo {griglie[s['griglia']]['tipo']}, non {s['puzzle']}.")
            else:
                s["griglia"] = next((k for k, g in griglie.items() if g["tipo"] == s["puzzle"] and g.get("porta")), "")

    # ---- 2. le chiavi, occorrenza per occorrenza, e le guardie di cifrari.py
    # Il cifrario e' quello del MONDO della parola (il simbolo che le sta accanto), non del
    # pianeta dove la parola compare: e' cosi' che per leggere tutto servono tutti e tre.
    def prima_parola(t):
        """La prima parola in chiaro del reperto: quella che si legge per prima, graffe escluse."""
        for pz in t["pezzi"]:
            if pz[0] == "c":
                m = re.search(r"[A-Za-zÀ-ÿ]+", pz[1])
                if m:
                    return norm_parola(m.group(0))
        return ""

    def chiave_per(mondo, t, posto, parola):
        """La regola del mondo, applicata con quello che il tavolo ha davanti.
           -> (chiave, come si trova) oppure (None, perche' non si puo')"""
        n = numero_sigillo(t["id"])
        if mondo == "HUSA":
            return ((n + len(parola), f"{n} di {t['id']} + {len(parola)} lettere") if n is not None
                    else (None, "il sigillo non ha un numero"))
        if mondo == "POLIS":
            return ((n * posto, f"{n} di {t['id']} x {posto}ª parola") if n is not None
                    else (None, "il sigillo non ha un numero"))
        if mondo == "IRIS":
            p = prima_parola(t)
            return ((C.chiave_da_parola(p), f"la prima parola del reperto: {p}") if p
                    else (None, "il reperto non comincia con una parola in chiaro"))
        return None, "mondo senza cifrario"

    # il posto della parola nel suo testo: 1a, 2a, 3a parola cifrata, nell'ordine in cui si leggono
    posti, quante = [], {}
    for t, w, riga, grezza in occorrenze:
        quante[t["id"]] = quante.get(t["id"], 0) + 1
        posti.append(quante[t["id"]])
    cifrate = []                                       # (testo, parola, riga, mondo, chiave, come, cifrato, posto)
    for (t, w, riga, grezza), posto in zip(occorrenze, posti):
        mondo = mondo_di.get(w, (None,))[0]
        if not mondo or (w, t["pianeta"]) not in voce_di:
            continue                                   # l'errore e' gia' stato detto
        k, come = chiave_per(mondo, t, posto, w)
        if not k:
            err(f"riga {riga}, === TESTO === {t['id']}: {{{grezza}}} e' scritta da {mondo}, ma la sua chiave "
                f"non si puo' trovare: {come}"
                + (" -- nessuna delle sue lettere sta nell'alfabeto kindler" if k == [] else "") + ".")
            continue
        guai = C.controlla_parola(mondo, w, k)
        for g in guai:
            err(f"riga {riga}, === TESTO === {t['id']}: {{{grezza}}} e' scritta da {mondo} e qui la sua chiave e' "
                f"{come}: {g}.")
        if not guai:
            c = C.cifra(mondo, w, k)
            if C.decifra(mondo, c, k) != w:
                err(f"riga {riga}: {w} cifrata e decifrata non torna uguale. E' un guasto di cifrari.py: non stampare niente.")
            cifrate.append((t, w, riga, mondo, k, come, c, posto))

    # ---- raggiungibilita': con le tre regole nuove ogni chiave si trova guardando il reperto
    # che si ha in mano, quindi basta che la parola compaia da qualche parte.
    aperte = {x[1] for x in cifrate}
    for E in enigmi:
        if E["parola"] in parole_note and E["parola"] not in aperte:
            err(f"{dove(E['b'], 'parola')}: si apre con {E['parola']}, che non e' fra graffe in nessun testo "
                f"da cui si possa decifrare: il luogo non si aprirebbe mai.")
    for w in parole:
        if not any(x == w["parola"] and t["pianeta"] == w["pianeta"] for t, x, _, _ in occorrenze):
            avv(f"{dove(w['b'])}: {w['parola']} non compare fra graffe in nessun testo di {w['pianeta']}.")
    for L in logs:
        if L["id"] not in apre_log:
            avv(f"{dove(L['b'])}: nessuna parola apre {L['id']} (apre: {L['id']}): nell'app non si leggera' mai.")

    # ---- la scala: quanto chiede ogni sigillo ORA, quanto POI, e se la salita sale
    peso_ora, peso_poi, parole_di = {}, {}, {}
    for t, w, riga, mondo, k, come, c, posto in cifrate:
        passi = len(k) if isinstance(k, (list, tuple)) else 1
        mio = mondo == t["pianeta"]
        quale = peso_ora if mio else peso_poi
        quale[t["id"]] = quale.get(t["id"], 0) + len(w) + passi
        parole_di.setdefault(t["id"], []).append((w, mio))
    for t in testi:
        peso_ora.setdefault(t["id"], 0)
        peso_poi.setdefault(t["id"], 0)
    scala = {t["id"]: livello_di(peso_ora[t["id"]]) for t in testi}
    # dentro un pianeta, i sigilli si trovano nell'ordine del loro numero: e' quello il percorso.
    discese = []
    for p in pianeti:
        suoi = sorted((t for t in testi if t["pianeta"] == p["id"] and peso_ora[t["id"]]),
                      key=lambda t: (numero_sigillo(t["id"]) or 0))
        for prima, dopo in zip(suoi, suoi[1:]):
            if scala[dopo["id"]] < scala[prima["id"]] - 1:
                discese.append((p, prima, dopo))
    for p, prima, dopo in discese:
        avv(f"{dove(dopo['b'])}: su {p['nome']} la salita scende da livello {scala[prima['id']]} "
            f"({prima['id']}, peso {peso_ora[prima['id']]}) a livello {scala[dopo['id']]} "
            f"(peso {peso_ora[dopo['id']]}). Se deve essere una salita, scambia i due numeri di "
            f"sigillo, o sposta una parola in un altro reperto.")

    # ---- 6. una parola chiave non compare in chiaro altrove: cifrarla non servirebbe
    chiave_di = sorted({x[1] for x in occorrenze} | parole_note)
    campi_pubblici = []
    for t in testi:
        campi_pubblici.append((t["b"], "titolo", t["titolo"]))
        # luogo: e posto: non arrivano ai giocatori (restano nel foglio del narratore),
        # ma se nominano una parola chiave e' facile che prima o poi finiscano stampati:
        # meglio un avviso adesso che una parola regalata la sera.
        for campo in ("luogo", "posto"):
            for w in parole_note:
                if t[campo] and parola_intera(w, t[campo]):
                    avv(f"{dove(t['b'], campo)}: {campo}  nomina la parola chiave {w} in chiaro. "
                        f"Non esce dai tuoi fogli, ma non stamparlo su niente che tocchino loro.")
        for pz in t["pezzi"]:
            if pz[0] == "c":
                campi_pubblici.append((t["b"], None, pz[1]))
    for w in parole:
        campi_pubblici.append((w["b"], None, w["nota"]))
    for L in logs:
        campi_pubblici += [(L["b"], "titolo", L["titolo"]), (L["b"], None, L["corpo"])]
    for E in enigmi:
        campi_pubblici += [(E["b"], "nome", E["nome"]), (E["b"], None, E["testo"])]
    for s in stanze:
        campi_pubblici += [(s["b"], "nome", s["nome"]), (s["b"], None, s["sblocca"])]
    for p in pianeti:
        campi_pubblici += [(p["b"], "nome", p["nome"]), (p["b"], "tema", p["tema"]),
                           (p["b"], "meccanica", p["meccanica"]), (p["b"], None, p["mecc_desc"])]
    for w in chiave_di:
        for b, campo, testo in campi_pubblici:
            if testo and parola_intera(w, testo):
                riga = b["righe"].get(campo, b["riga"]) if campo else next(
                    (n for n, r in b["corpo"] if parola_intera(w, r)), b["riga"])
                err(f"riga {riga}, === {b['tipo']} === {b['campi'].get(NOME_DI[b['tipo']], '').upper()}: la parola chiave {w} "
                    f"compare in chiaro{' nel campo ' + campo if campo else ''}. Cifrarla altrove non servirebbe: "
                    f"mettila fra graffe anche qui, oppure toglila.")
    # Le frasi delle regole stanno in chiaro nei testi propedeutici: e' li' che i giocatori
    # le trovano (decisione di Alessandro). Percio' finiscono anche in dati.js, e il
    # repository non puo' restare pubblico: alla fine della costruzione c'e' l'avviso.
    # Qui si controlla solo che una frase non sia sparsa dove non deve stare.
    suo_propedeutico = {}
    for p, parte, cod in codici:
        for t in testi:
            if t["pianeta"] == p["id"] and t["tipo"] == "propedeutico" and parte in t["rivela"]:
                suo_propedeutico.setdefault((p["id"], parte), set()).add(t["b"]["riga"])
    for p, parte, cod in codici:
        giuste = suo_propedeutico.get((p["id"], parte), set())
        for b, campo, testo in campi_pubblici:
            if b["riga"] in giuste or not contiene_codice(testo, cod):
                continue
            err(f"{dove(b, campo)}: contiene la frase dell'{parte} di {p['id']}. Quella frase va detta una volta "
                f"sola, nel testo propedeutico di {p['nome']}: altrove e' un codice regalato.")

    if ERRORI:
        print("\n  NON HO COSTRUITO NIENTE. Da correggere in contenuti.md:\n")
        for e in ERRORI:
            print("   -", e)
        print()
        return 1

    # il codice opaco con cui si apre ogni reperto
    presi = set()
    codice_di = {t["id"]: codice_sigillo(t["id"], presi) for t in testi}

    # ------------------------------------------------------------------ dati.js
    ordine = {p["id"]: i for i, p in enumerate(pianeti)}
    # La sigla di una parola e' PIANETA-lettera (HUSA-A, HUSA-B...): LETTERE, non numeri,
    # perche' i sigilli sono PIANETA-numero e sul foglio del narratore si confonderebbero.
    id_parola, contatore = {}, {}
    for w in parole:
        n = contatore[w["pianeta"]] = contatore.get(w["pianeta"], 0) + 1
        sigla = ""
        while n:
            n, r = divmod(n - 1, 26)
            sigla = chr(65 + r) + sigla
        id_parola[(w["parola"], w["pianeta"])] = f"{w['pianeta']}-{sigla}"
    # la forma cifrata dipende anche dal posto della parola nel testo: si indicizza cosi'
    cifrato_di = {(t["id"], posto): c for t, w, riga, mondo, k, come, c, posto in cifrate}
    dati_testi = []
    for t in testi:
        corpo, n = [], 0
        for pz in t["pezzi"]:
            if pz[0] == "c":
                corpo.append({"t": "c", "v": pz[1]})
            else:
                n += 1
                w = norm_parola(pz[1])
                # k e come: le note del narratore. NON sono la soluzione: senza alfabeto e
                # ordine la chiave non apre niente, e quelli in dati.js non ci sono (solo
                # le loro impronte). La parola in chiaro resta fuori di qui, sempre.
                x = next((y for y in cifrate if y[0] is t and y[7] == n), None)
                corpo.append({"t": "p", "w": id_parola[(w, t["pianeta"])], "c": cifrato_di[(t["id"], n)],
                              "k": ("-".join(map(str, x[4])) if isinstance(x[4], (list, tuple)) else str(x[4])) if x else "",
                              "come": x[5] if x else ""})
        # cita: vero o falso, mai il riferimento: il rimando lo devono leggere loro
        # rivela: serve all'app del Custode, che apre lo strumento della chiave di un
        # mondo solo dopo che QUEL telefono ha scansionato il reperto che la spiega.
        dati_testi.append({"id": t["id"], "codice": codice_di[t["id"]], "rivela": t["rivela"],
                           "pianeta": t["pianeta"], "titolo": t["titolo"], "tipo": t["tipo"],
                           "cita": bool(t["cita"]), "corpo": corpo})
    dati = {
        "schema": 2,
        # Come si scrive un reperto: la console lo mostra in simboli, che e' la forma in cui
        # il tavolo lo vede. Non e' un segreto - l'app il testo in chiaro lo da' a chiunque
        # scansioni - ma senza questa tabella non potrebbe disegnarlo.
        "simboli": SIM.MAPPA,
        # Il QR di ogni codice, impacchettato bit a bit: l'app non sa disegnarne uno da se',
        # e il narratore deve poterlo mostrare dallo schermo invece che su carta.
        "qr": {t["id"]: qr_compatto(codice_di[t["id"]]) for t in testi},
        "pianeti": [dict({"id": p["id"], "nome": p["nome"], "tema": p["tema"], "meccanica": p["meccanica"],
                          "mecc_desc": p["mecc_desc"], "simbolo": p["simbolo"]},
                         **({"alfabeto_hash": impronta(norm_codice(p["codice_alfabeto"])),
                             "ordine_hash": impronta(norm_codice(p["codice_ordine"]))} if p["id"] in C.CIFRARI else {}))
                    for p in pianeti],
        "testi": dati_testi,
        # mondo: il simbolo accanto alla parola, cioe' quale cifrario la apre. Non e' un segreto:
        # sta sul muro, e serve al tavolo per sapere quali codici prendere.
        "parole": [{"id": id_parola[(w["parola"], w["pianeta"])], "pianeta": w["pianeta"], "mondo": w["mondo"],
                    "hash": impronta(w["parola"]),
                    "apre_log": w["apre"] or None, "apre_enigma": enigma_di.get(w["parola"]), "nota": w["nota"] or None}
                   for w in sorted(parole, key=lambda x: ordine.get(x["pianeta"], 99))],
        "log": [{"id": L["id"], "pianeta": L["pianeta"], "titolo": L["titolo"], "corpo": L["corpo"]} for L in logs],
        "enigmi": [{"id": E["id"], "pianeta": E["pianeta"], "nome": E["nome"], "testo": E["testo"],
                    "parola_hash": impronta(E["parola"])} for E in enigmi],
        "stanze": [{"id": s["id"], "pianeta": s["pianeta"], "nome": s["nome"], "puzzle": s["puzzle"],
                    "griglia": s["griglia"], "sblocca": s["sblocca"]} for s in stanze],
    }
    js = ("// GENERATO DA costruisci.py — non modificare a mano\n"
          "window.DATI = " + json.dumps(dati, ensure_ascii=False, indent=1) + ";\n")

    # ------------------------------------------------------------------ il percorso
    # L'ordine dei blocchi PIANETA e' la rotta: arrivando su un mondo se ne imparano le tre
    # regole, e da quel momento ogni parola con quel simbolo si apre, anche nei reperti gia'
    # letti altrove. Qui si dice, tappa per tappa, cosa si apre davvero.
    dove_sta = {}
    for t, w, riga, mondo, k, come, c, posto in cifrate:
        dove_sta.setdefault(w, set()).add(t["id"])
    percorso, noti, viste, aperte_fin_qui = [], set(), set(), set()
    for p in pianeti:
        if p["id"] in C.CIFRARI:
            noti.add(p["id"])
        viste.add(p["id"])
        nuove = sorted({w for w in dove_sta if mondo_di.get(w, ("",))[0] in noti} - aperte_fin_qui)
        aperte_fin_qui |= set(nuove)
        sue = lambda t: [w for w, mio in parole_di.get(t["id"], ())]
        qui = [t for t in testi if t["pianeta"] in viste]
        meta = [t for t in qui if any(w not in aperte_fin_qui for w in sue(t))]
        mancano = sorted({mondo_di[w][0] for t in meta for w in sue(t)
                          if w not in aperte_fin_qui and w in mondo_di})
        percorso.append({
            "pianeta": p["id"], "nome": p["nome"], "simbolo": p["simbolo"],
            "impara": p["id"] if p["id"] in C.CIFRARI else "",
            "parole": [{"parola": w, "mondo": mondo_di.get(w, ("",))[0],
                        "dove": sorted(dove_sta[w]),
                        "apre": ", ".join(sorted({x["apre"] for x in parole if x["parola"] == w and x["apre"]}
                                                 | ({enigma_di[w]} if w in enigma_di else set())))}
                       for w in nuove],
            "luoghi": [E["id"] for E in enigmi if E["parola"] in nuove],
            "porte": [s["id"] for s in stanze if s["pianeta"] == p["id"]],
            "a_meta": [t["id"] for t in meta], "mancano": mancano,
        })

    # ------------------------------------------------------------------ il foglio del narratore
    usa = lambda p: next((x for x in pianeti if x["id"] == p), {"nome": p})["nome"]
    fm = ["# CHIAVI — solo per il narratore", "",
          "Non pubblicare questo file. Generato da costruisci.py: le modifiche vanno in contenuti.md.", "",
          "## I codici delle regole", "",
          "| Mondo | Alfabeto · Traduttore | Ordine · Apritore | Chiave · Custode |", "|---|---|---|---|"]
    for p in cifrati:
        fm.append(f"| {p['nome']} | `{p['codice_alfabeto']}` | `{p['codice_ordine']}` | {PROCEDIMENTO.get(p['id'], '')} |")
    fm += ["", "## I simboli", "",
           "Il simbolo accanto a una parola dice chi l'ha scritta, e quindi con quale cifrario si apre.", ""]
    for p in cifrati:
        mie = sorted({w["parola"] for w in parole if w["mondo"] == p["id"]})
        fm.append(f"- **{p['simbolo']}  {p['nome']}** — {', '.join(mie) if mie else 'nessuna parola'}")
    posa = [t for t in testi if t["luogo"] or t["posto"]]
    if posa:
        fm += ["", "## Dove va ogni sigillo", "",
               "La lista di posa: stampa, taglia, e vai in giro con questa. La coordinata e'",
               "quella della mappa (colonna + riga).", ""]
        for p in pianeti:
            suoi = [t for t in posa if t["pianeta"] == p["id"]]
            if not suoi:
                continue
            fm += [f"### {p['simbolo']} {p['nome']}", ""]
            for lg in dict.fromkeys(t["luogo"] for t in suoi):
                fm += [f"**{lg or '(senza locazione)'}**", "",
                       "| Sigillo | N. | Codice | Punto | Livello |", "|---|---|---|---|---|"]
                for t in [x for x in suoi if x["luogo"] == lg]:
                    fm.append(f"| {t['id']} | {numero_sigillo(t['id']) or '—'} | `{codice_di[t['id']]}` |"
                              f" {t['posto'] or '—'} | {scala[t['id']]} |")
                fm.append("")
    fm += ["", "## Il percorso", "",
           "L'ordine dei blocchi PIANETA in contenuti.md e' la rotta. A ogni tappa si imparano",
           "le tre regole di quel mondo, e da li' in poi ogni parola con quel simbolo si apre,",
           "anche nei reperti letti prima altrove.", "",
           "| Tappa | Si aprono | Luoghi | Porte | Restano a meta' |", "|---|---|---|---|---|"]
    for i, tappa in enumerate(percorso, 1):
        if not (tappa["parole"] or tappa["luoghi"] or tappa["porte"]):
            continue
        fm.append(f"| {i}. {tappa['simbolo']} {tappa['nome']} "
                  f"| {', '.join(w['parola'] for w in tappa['parole']) or '—'} "
                  f"| {', '.join(tappa['luoghi']) or '—'} "
                  f"| {', '.join(tappa['porte']) or '—'} "
                  f"| {len(tappa['a_meta'])}"
                  + (f" (manca {', '.join(usa(m) for m in tappa['mancano'])})" if tappa["mancano"] else "") + " |")
    fm += ["", "## La salita", "",
           "Il peso di una parola sono le lettere da trasformare piu' i passi della chiave.",
           "**Ora** = le parole che quel mondo ha scritto da se': si aprono alla prima visita, ed e'",
           "questa la difficolta' che il tavolo sente. **Poi** = le parole di un altro mondo, che",
           "restano chiuse finche' non si e' stati la'. Un sigillo pesante di Poi non e' un muro:",
           "si apre a meta' e si riapre al ritorno. Fra parentesi, appunto, le parole del ritorno.", ""]
    for p in pianeti:
        tutti = [t for t in testi if t["pianeta"] == p["id"]]
        suoi = sorted((t for t in tutti if peso_ora[t["id"]] or peso_poi[t["id"]]),
                      key=lambda t: (numero_sigillo(t["id"]) or 0))
        if not suoi:
            continue
        letti = [t for t in tutti if not (peso_ora[t["id"]] or peso_poi[t["id"]])]
        fm += [f"### {p['nome']}", "", "| Sigillo | Livello | Ora | Poi | Parole |", "|---|---|---|---|---|"]
        for t in suoi:
            fm.append(f"| {t['id']} | {scala[t['id']]} · {NOME_LIVELLO[scala[t['id']]]} "
                      f"| {peso_ora[t['id']]} | {peso_poi[t['id']] or TRATTO} | "
                      + ", ".join(w if mio else f"({w})" for w, mio in parole_di[t["id"]]) + " |")
        if letti:
            fm.append(f"| {', '.join(t['id'] for t in letti)} | 0 · lettura | 0 | {TRATTO} | {TRATTO} |")
        fm.append("")
    if discese:
        fm += ["**La salita scende qui:**", ""] + [
            f"- {p['nome']}: {prima['id']} (livello {scala[prima['id']]}) poi {dopo['id']} "
            f"(livello {scala[dopo['id']]})" for p, prima, dopo in discese] + [""]
    fm += ["## Le parole, testo per testo", "",
           "La sigla (HUSA-A...) e' quella che la console mostra nel pannello Parole aperte:",
           "lettere, mentre i sigilli hanno numeri.", ""]
    for t in testi:
        mie = [x for x in cifrate if x[0] is t]
        if not mie:
            continue
        fm += [f"### {t['id']} · {t['titolo']} ({usa(t['pianeta'])}) — livello {scala[t['id']]}, "
               f"peso {peso_ora[t['id']]} ora"
               + (f" + {peso_poi[t['id']]} poi" if peso_poi[t["id"]] else ""), "",
               "| Sigla | Nel testo | Parola | Scritta da | Chiave | Apre |", "|---|---|---|---|---|---|"]
        for _, w, riga, mondo, k, come, c, posto in mie:
            v = voce_di[(w, t["pianeta"])]
            simbolo = next((x["simbolo"] for x in pianeti if x["id"] == mondo), "?")
            chiave = come if isinstance(k, list) else f"{k} ({come})"
            apre = ", ".join(x for x in (v["apre"], (f"luogo {enigma_di[w]}" if w in enigma_di else "")) if x) or "—"
            fm.append(f"| {id_parola[(w, t['pianeta'])]} | `{c}` | **{w}** | {simbolo} {usa(mondo)} | {chiave} | {apre} |")
        fm.append("")
    rune = [(p, r) for p in pianeti for r in p["rune"]]
    if rune:
        fm += ["## Le rune", "",
               "Si posano, non si digitano: le riconosci tu. Chi le ha decifrate le ha gia' nel registro.", ""]
        for p in pianeti:
            if not p["rune"]:
                continue
            fm.append(f"**{p['nome']}** — " + ", ".join(
                f"**{r}** ({next((x['simbolo'] for x in pianeti if x['id'] == mondo_di.get(r, ('',))[0]), '?')} "
                f"{usa(mondo_di.get(r, ('',))[0])})" for r in p["rune"]))
            manca = [r for r in p["rune"] if r not in aperte]
            if manca:
                fm.append(f"- attenzione: {', '.join(manca)} non si decifra in nessun reperto.")
        fm.append("")
    if enigmi:
        fm += ["## Ingressi dei luoghi", ""] + [f"- **{E['nome']}** ({usa(E['pianeta'])}) — parola **{E['parola']}**" for E in enigmi] + [""]
    if stanze:
        fm += ["## Porte di pietra", "", "Se il tavolo si blocca, una soluzione da dettare all'Apritore.", ""]
        for s in stanze:
            rap, sol = esiti_griglie.get(s["griglia"], ([], None))
            fm.append(f"- **{s['nome']}** ({usa(s['pianeta'])}) — {s['puzzle']}, griglia {s['griglia']}: "
                      + (VG.indicazioni(sol) if sol else "soluzione non calcolata"))
        fm.append("")
    fm += ["## Failsafe", "",
           "Se il tavolo si blocca: leggi la parola da qui e considerala aperta. Il Custode la registra,",
           "l'Apritore la digita all'ingresso: sui loro telefoni si apre come se l'avessero decifrata.", ""]
    master = "\n".join(fm)

    # ------------------------------------------------------------------ soluzioni.json
    # Tutto quello che il narratore puo' voler sapere, in forma leggibile da una macchina:
    # lo rende pagina genera_master.py. Qui sta la verita', li' solo il disegno.
    sol_sigilli = []
    for t in testi:
        pezzi, n = [], 0
        for pz in t["pezzi"]:
            if pz[0] == "c":
                pezzi.append({"t": "c", "v": pz[1]})
                continue
            n += 1
            w = norm_parola(pz[1])
            x = next((y for y in cifrate if y[0] is t and y[7] == n), None)
            if x is None:                              # scartata da una guardia: non c'e' cifrato
                pezzi.append({"t": "c", "v": "{" + pz[1] + "}"})
                continue
            _, _, _, mondo, k, come, c, posto = x
            pezzi.append({"t": "p", "parola": w, "sigla": id_parola[(w, t["pianeta"])], "cifrato": c,
                          "mondo": mondo, "posto": posto, "come": come,
                          "chiave": ("-".join(map(str, k)) if isinstance(k, (list, tuple)) else str(k)),
                          "apre": ", ".join(x for x in (voce_di[(w, t["pianeta"])]["apre"],
                                                        (enigma_di.get(w) or "")) if x)})
        sol_sigilli.append({"id": t["id"], "pianeta": t["pianeta"], "titolo": t["titolo"], "tipo": t["tipo"],
                            "luogo": t["luogo"], "posto": t["posto"], "codice": codice_di[t["id"]],
                            "rivela": t["rivela"], "numero": numero_sigillo(t["id"]),
                            "livello": scala[t["id"]], "peso_ora": peso_ora[t["id"]],
                            "peso_poi": peso_poi[t["id"]], "pezzi": pezzi})
    soluzioni = {
        "percorso": percorso,
        "scala": {"soglie": list(SCALA), "nomi": NOME_LIVELLO,
                  "discese": [{"pianeta": p["id"], "prima": a["id"], "dopo": b["id"]} for p, a, b in discese]},
        "pianeti": [{"id": p["id"], "nome": p["nome"], "tema": p["tema"], "meccanica": p["meccanica"],
                     "simbolo": p["simbolo"], "mecc_desc": p["mecc_desc"],
                     "codice_alfabeto": p["codice_alfabeto"], "codice_ordine": p["codice_ordine"],
                     "procedimento": PROCEDIMENTO.get(p["id"], ""),
                     "esempi": C.CIFRARI[p["id"]]["esempi"] if p["id"] in C.CIFRARI else {},
                     "dice": C.CIFRARI[p["id"]]["dice"] if p["id"] in C.CIFRARI else {},
                     "rune": [{"parola": r, "mondo": mondo_di.get(r, ("",))[0]} for r in p["rune"]],
                     "alfabeto": C.CIFRARI[p["id"]]["alfabeto"][0] if p["id"] in C.CIFRARI else "",
                     "ordine": C.CIFRARI[p["id"]]["ordine"][0] if p["id"] in C.CIFRARI else "",
                     "parole": sorted({w["parola"] for w in parole if w["mondo"] == p["id"]})}
                    for p in pianeti],
        "sigilli": sol_sigilli,
        "parole": [{"parola": w["parola"], "sigla": id_parola[(w["parola"], w["pianeta"])],
                    "pianeta": w["pianeta"], "mondo": w["mondo"], "impronta": impronta(w["parola"]),
                    "apre_log": w["apre"] or "", "apre_enigma": enigma_di.get(w["parola"], ""),
                    "dove": sorted({t["id"] for t, x, _, _ in occorrenze if x == w["parola"]})}
                   for w in sorted(parole, key=lambda x: (ordine.get(x["pianeta"], 99), x["parola"]))],
        "enigmi": [{"id": E["id"], "pianeta": E["pianeta"], "nome": E["nome"], "parola": E["parola"],
                    "testo": E["testo"]} for E in enigmi],
        "stanze": [{"id": s["id"], "pianeta": s["pianeta"], "nome": s["nome"], "puzzle": s["puzzle"],
                    "griglia": s["griglia"], "sblocca": s["sblocca"],
                    "dati": griglie.get(s["griglia"], {}),
                    "soluzione": [list(x) for x in (esiti_griglie.get(s["griglia"], ([], None))[1] or [])],
                    "indicazioni": (VG.indicazioni(esiti_griglie[s["griglia"]][1])
                                    if esiti_griglie.get(s["griglia"], ([], None))[1] else "")}
                   for s in stanze],
        "costi": re.search(r"const COSTI = \{(.*?)\}", open("app.js", encoding="utf-8").read(), re.S).group(1).strip()
                 if re.search(r"const COSTI = \{(.*?)\}", open("app.js", encoding="utf-8").read(), re.S) else "",
    }

    # ------------------------------------------------------------------ i segreti
    # Le frasi delle regole NON sono qui dentro: stanno per scelta nei testi propedeutici,
    # quindi in dati.js. Quello che non deve uscire mai e' l'elenco delle parole in chiaro.
    segreti = sorted(s for s in set(chiave_di) if len(s) >= 3)

    # ------------------------------------------------------------------ prima di scrivere: niente fughe
    f_dati = fughe(dati, chiave_di, [])
    for f in f_dati:
        err(f + ".")
    rigenerati = {"dati.js", "stampa.html", "prova-offline.html"}
    for f in pubblicabili():
        if f in rigenerati:
            continue
        for p in perdite_nei_file(segreti, [f]):
            err(f"{p}  -- un file pubblico non puo' contenere una parola chiave o un codice: la guardia di push.ps1 "
                f"lo fermerebbe. Sistema il file (o, se e' materiale di lavoro, mettilo in .gitignore).")
    for p in perdite_nei_file(segreti, ["dati.js"], {"dati.js": js}):
        err(p + "  -- lo fermerebbe push.ps1. Di solito e' una forma cifrata che per caso contiene una parola chiave: "
                "cambia la parola, o il sigillo che ne fa la chiave.")
    # stampa.html si genera con qrcode: se manca, meglio saperlo adesso che dopo aver scritto dati.js
    if importlib.util.find_spec("qrcode") is None:
        err("manca il modulo Python qrcode, che serve a genera_stampe.py per disegnare i sigilli. Installalo:  pip install qrcode")
    for g in GENERATORI:
        if not os.path.exists(g):
            err(f"manca {g}: senza, {GENERATORI[g]} resterebbe vecchio.")
    if ERRORI:
        print("\n  NON HO COSTRUITO NIENTE:\n")
        for e in ERRORI:
            print("   -", e)
        print()
        return 1

    # ------------------------------------------------------------------ scrittura
    copia = "dati.js.prima"
    if os.path.exists("dati.js"):
        shutil.copyfile("dati.js", copia)
    with open("dati.js", "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    # §7.1: si rilegge il file scritto davvero, non la stringa in memoria
    riletto = open("dati.js", encoding="utf-8").read()
    try:
        ricaricati = json.loads(re.sub(r"^.*?window\.DATI = ", "", riletto, flags=re.S).rstrip().rstrip(";"))
        dopo = fughe(ricaricati, chiave_di, [])      # le frasi delle regole ci stanno di proposito
    except ValueError as e:
        dopo = [f"dati.js riletto non e' JSON valido ({e})"]
    if dopo:
        if os.path.exists(copia):
            shutil.copyfile(copia, "dati.js")
            os.remove(copia)
        print("\n  !! dati.js RILETTO DAL DISCO contiene quello che non deve. Ho rimesso quello di prima.")
        for d in dopo:
            print("     -", d)
        print()
        return 1
    if os.path.exists(copia):
        os.remove(copia)
    with open("CHIAVI-MASTER.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(master)
    with open("soluzioni.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(soluzioni, f, ensure_ascii=False, indent=1)
    with open(".segreti", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(segreti) + "\n")

    n_uniche = len({w["parola"] for w in parole})
    print(f"\n  Costruito: {len(pianeti)} pianeti, {len(testi)} testi, {len(cifrate)} parole cifrate nei testi "
          f"({n_uniche} parole distinte), {len(logs)} voci di registro, {len(enigmi)} luoghi, {len(stanze)} porte")
    print("  Scritti: dati.js, CHIAVI-MASTER.md, soluzioni.json, .segreti")
    for s in stanze:
        print(f"  porta {s['id']}: {s['puzzle']}, griglia {s['griglia']}"
              + (" (pannello d'insegnamento, facile di proposito)" if griglie.get(s["griglia"], {}).get("insegna") else ""))
    for a in AVVISI:
        print("  avviso:", a)

    # ------------------------------------------------------------------ stampe e copia offline
    for g in GENERATORI:
        sys.stdout.flush()
        r = subprocess.run([sys.executable, g])
        if r.returncode != 0:
            print(f"\n  !! {g} e' fallito: {GENERATORI[g]} NON e' aggiornato.")
            print("     dati.js si': non stampare niente finche' non lo sistemi.\n")
            return 1

    # ------------------------------------------------------------------ l'ultima guardia, come push.ps1
    perdite = perdite_nei_file(segreti, pubblicabili())
    if perdite:
        print("\n  !! SEGRETI IN FILE PUBBLICABILI:")
        for p in perdite:
            print("     -", p)
        print("     push.ps1 si fermerebbe. Sistema il file.\n")
        return 1
    print("  Nessuna chiave nei file pubblicabili.")
    if codici:
        print("\n  Le frasi delle regole stanno nei testi propedeutici, quindi in chiaro dentro dati.js:")
        print("  e' voluto (i giocatori le leggono scansionando), ma vuol dire che QUESTO REPOSITORY NON PUO'")
        print("  RESTARE PUBBLICO. La sera servi l'app dalla rete di casa con  ./servi.ps1")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
