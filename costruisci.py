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
import difflib, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, unicodedata

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

def impronta(s):
    """SHA-256 troncato a 16 esadecimali: serve a riconoscere un risultato, mai a produrlo."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ il formato
BLOCCHI = {
    "PIANETA": (("id", "nome", "tema", "meccanica"), ("codice_alfabeto", "codice_ordine")),
    "TESTO":   (("sigillo", "pianeta", "titolo", "tipo"), ("cita", "rivela")),
    "PAROLA":  (("parola", "pianeta"), ("apre",)),
    "LOG":     (("sigillo", "pianeta", "titolo"), ()),
    "ENIGMA":  (("id", "pianeta", "nome", "parola"), ()),
    "STANZA":  (("id", "pianeta", "nome", "puzzle"), ("griglia",)),
}
NOME_DI = {"PIANETA": "id", "TESTO": "sigillo", "PAROLA": "parola", "LOG": "sigillo", "ENIGMA": "id", "STANZA": "id"}
PERCHE_CAMPO = {
    ("PIANETA", "tema"): "(sofferenza, isolamento, amicizia...)",
    ("PIANETA", "meccanica"): "(la regola del loop che il pianeta restituisce)",
    ("TESTO", "tipo"): "(lore, aiuto oppure propedeutico)",
    ("TESTO", "pianeta"): "(l'id di un blocco PIANETA)",
    ("PAROLA", "pianeta"): "(la stessa parola puo' avere una voce per pianeta: dimmi di quale)",
    ("ENIGMA", "parola"): "(la parola decifrata che ne apre l'ingresso)",
    ("STANZA", "puzzle"): "(bordi, separazione oppure simmetria)",
}
TIPI_TESTO = ("lore", "aiuto", "propedeutico")
PARTI = ("alfabeto", "ordine", "chiave")
PUZZLE = ("bordi", "separazione", "simmetria")
# come si trova la chiave su ogni pianeta (SPECIFICA §3): e' il lavoro del Consultatore
PROCEDIMENTO = {
    "HUSA": "il numero del sigillo del testo stesso",
    "POLIS": "il numero del sigillo citato dal testo",
    "IRIS": "la parola che apre la voce di registro citata dal testo",
}
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
        elif re.search(r"\s", grezza):
            err(f"riga {riga}, === TESTO === {b['campi'].get('sigillo', '')}: fra graffe va una parola sola, "
                f"non  {{{grezza}}}. Se sono due parole chiave, mettile fra graffe una per una.")
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
            pianeti.append(dict(b=b, id=c["id"].upper(), nome=c["nome"], tema=c["tema"],
                                meccanica=c["meccanica"].upper(), mecc_desc=corpo_di(b),
                                codice_alfabeto=c.get("codice_alfabeto", ""), codice_ordine=c.get("codice_ordine", "")))
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
                              cita=c.get("cita", "").upper(), rivela=rivela, pezzi=segmenta(b)))
        elif t == "PAROLA":
            parole.append(dict(b=b, parola=c["parola"].strip().upper(), pianeta=c["pianeta"].upper(),
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

    # ---- 1. ogni parola fra graffe ha il suo blocco PAROLA, sullo stesso pianeta
    occorrenze = []                                   # (testo, parola, riga)
    for t in testi:
        for pz in t["pezzi"]:
            if pz[0] == "p" and pz[1] and not re.search(r"\s", pz[1]):
                occorrenze.append((t, pz[1], pz[2]))
    for t, w, riga in occorrenze:
        if t["pianeta"] in P and t["pianeta"] not in C.CIFRARI:
            err(f"riga {riga}, === TESTO === {t['id']}: {{{w}}} e' fra graffe, ma il pianeta {t['pianeta']} non ha un cifrario "
                f"(cifrari.py conosce {', '.join(C.CIFRARI)}).")
        elif (w, t["pianeta"]) not in coppie:
            stesso = sorted(x["parola"] for x in parole if x["pianeta"] == t["pianeta"])
            simili = difflib.get_close_matches(w, stesso, 2)
            altrove = sorted({x["pianeta"] for x in parole if x["parola"] == w})
            consiglio = (f" Forse volevi {' o '.join(simili)}?" if simili else "") + \
                        (f" C'e' un blocco per {', '.join(altrove)}: una parola vuole un blocco per ogni pianeta su cui compare." if altrove else "")
            err(f"riga {riga}, === TESTO === {t['id']}: {{{w}}} non ha un blocco  === PAROLA ===  per {t['pianeta']}.{consiglio} "
                f"Se e' una parola nuova, aggiungi:  === PAROLA ===  parola: {w}  pianeta: {t['pianeta']}")

    # ---- 3 e 4. le citazioni, che su Polis e Iris portano la chiave
    sigilli = {t["id"] for t in testi}
    log_id = {L["id"] for L in logs}
    apre_log = {}                                      # LOG -> parole che lo aprono
    for w in parole:
        if w["apre"]:
            if w["apre"] not in log_id:
                err(f"{dove(w['b'], 'apre')}: apre  {w['apre']}, ma quella voce di registro non esiste. "
                    f"Voci definite: {', '.join(sorted(log_id)) or 'nessuna'}.")
            apre_log.setdefault(w["apre"], set()).add(w["parola"])
    for t in testi:
        b = t["b"]
        if t["pianeta"] == "POLIS":
            if not t["cita"]:
                err(f"{dove(b)}: un testo di Polis deve avere  cita:  con il sigillo di un altro testo: il suo numero e' la chiave.")
            elif t["cita"] not in sigilli:
                err(f"{dove(b, 'cita')}: cita  {t['cita']}, ma nessun testo ha quel sigillo.")
            elif t["cita"] == t["id"]:
                err(f"{dove(b, 'cita')}: un testo di Polis cita se stesso: la chiave sarebbe il suo numero, come su Husa. Cita un altro sigillo.")
        elif t["pianeta"] == "IRIS":
            if not t["cita"]:
                err(f"{dove(b)}: un testo di Iris deve avere  cita:  con una voce di registro: la parola che la apre e' la chiave.")
            elif t["cita"] not in log_id:
                err(f"{dove(b, 'cita')}: cita  {t['cita']}, ma quella voce di registro non esiste.")
            elif not apre_log.get(t["cita"]):
                err(f"{dove(b, 'cita')}: cita  {t['cita']}, ma nessuna PAROLA la apre (apre: {t['cita']}): "
                    f"su Iris quella parola e' la chiave, e senza non c'e' chiave.")
            elif len(apre_log[t["cita"]]) > 1:
                err(f"{dove(b, 'cita')}: {t['cita']} e' aperta da piu' parole ({', '.join(sorted(apre_log[t['cita']]))}): "
                    f"su Iris la chiave sarebbe ambigua. Una voce citata da Iris la apre una parola sola.")
        elif t["cita"] and t["cita"] not in sigilli and t["cita"] not in log_id:
            err(f"{dove(b, 'cita')}: cita  {t['cita']}, che non e' ne' un sigillo ne' una voce di registro.")

    # ---- 5. ogni pianeta insegna il suo alfabeto e il suo ordine
    for p in cifrati:
        for parte in ("alfabeto", "ordine"):
            if not any(t["pianeta"] == p["id"] and t["tipo"] == "propedeutico" and parte in t["rivela"] for t in testi):
                err(f"{dove(p['b'])}: {p['nome']} non ha un testo propedeutico che riveli l'{parte}. "
                    f"Serve almeno un  === TESTO ===  con  pianeta: {p['id']},  tipo: propedeutico,  rivela: {parte}.")

    # ---- 7. gli enigmi si aprono con parole che esistono
    parole_note = {w["parola"] for w in parole}
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
    def chiave_per(t):
        if t["pianeta"] == "HUSA":
            return numero_sigillo(t["id"])
        if t["pianeta"] == "POLIS":
            return numero_sigillo(t["cita"]) if t["cita"] in sigilli else None
        if t["pianeta"] == "IRIS":
            w = apre_log.get(t["cita"], set())
            return C.chiave_da_parola(next(iter(w))) if len(w) == 1 else None
        return None
    cifrate = []                                       # (testo, parola, riga, chiave, cifrato)
    for t, w, riga in occorrenze:
        if t["pianeta"] not in C.CIFRARI:
            continue
        k = chiave_per(t)
        if k is None:
            continue                                   # l'errore sulla citazione e' gia' stato detto
        guai = C.controlla_parola(t["pianeta"], w, k)
        for g in guai:
            err(f"riga {riga}, === TESTO === {t['id']}: {{{w}}} su {t['pianeta']} con chiave {k}: {g}.")
        if not guai:
            c = C.cifra(t["pianeta"], w, k)
            if C.decifra(t["pianeta"], c, k) != w:
                err(f"riga {riga}: {w} cifrata e decifrata non torna uguale. E' un guasto di cifrari.py: non stampare niente.")
            cifrate.append((t, w, riga, k, c))

    # ---- raggiungibilita': ogni parola si puo' aprire, partendo da quello che si legge
    # Husa e Polis hanno chiavi numeriche, sempre alla portata; su Iris la chiave e'
    # una parola, che dev'essere gia' aperta.
    aperte, cambiato = set(), True
    while cambiato:
        cambiato = False
        for t, w, riga, k, c in cifrate:
            if w in aperte:
                continue
            if t["pianeta"] != "IRIS" or next(iter(apre_log[t["cita"]])) in aperte:
                aperte.add(w); cambiato = True
    for w in sorted({w for _, w, _, _, _ in cifrate} - aperte):
        chi = sorted({f"{t['id']} (chiave: la parola che apre {t['cita']})" for t, x, _, _, _ in cifrate if x == w})
        err(f"la parola {w} non si potra' mai aprire: compare solo su Iris, in {', '.join(chi)}, e quella parola "
            f"a sua volta non si apre. Metti la parola-chiave anche in un testo di Husa o di Polis, o cambia la citazione.")
    for E in enigmi:
        if E["parola"] in parole_note and E["parola"] not in aperte:
            err(f"{dove(E['b'], 'parola')}: si apre con {E['parola']}, che non e' fra graffe in nessun testo "
                f"da cui si possa decifrare: il luogo non si aprirebbe mai.")
    for w in parole:
        if not any(x == w["parola"] and t["pianeta"] == w["pianeta"] for t, x, _ in occorrenze):
            avv(f"{dove(w['b'])}: {w['parola']} non compare fra graffe in nessun testo di {w['pianeta']}.")
    for L in logs:
        if L["id"] not in apre_log:
            avv(f"{dove(L['b'])}: nessuna parola apre {L['id']} (apre: {L['id']}): nell'app non si leggera' mai.")

    # ---- 6. una parola chiave non compare in chiaro altrove: cifrarla non servirebbe
    chiave_di = sorted({w for _, w, _ in occorrenze} | parole_note)
    campi_pubblici = []
    for t in testi:
        campi_pubblici.append((t["b"], "titolo", t["titolo"]))
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
    # e un codice delle regole non puo' stare in un testo: dati.js e' pubblico (§4.2)
    for p, parte, cod in codici:
        for b, campo, testo in campi_pubblici:
            spaz = " " + " ".join(re.findall(r"[A-Z0-9]+", senza_accenti(testo or "").upper())) + " "
            parti = re.findall(r"[A-Z0-9]+", senza_accenti(cod).upper())
            if (" " + " ".join(parti) + " ") in spaz or (" " + "".join(parti) + " ") in spaz:
                err(f"{dove(b, campo)}: contiene in chiaro il codice dell'{parte} di {p['id']}. dati.js e' pubblico: "
                    f"un codice li' dentro e' un codice regalato. Fallo arrivare ai giocatori in un altro modo.")

    if ERRORI:
        print("\n  NON HO COSTRUITO NIENTE. Da correggere in contenuti.md:\n")
        for e in ERRORI:
            print("   -", e)
        print()
        return 1

    # ------------------------------------------------------------------ dati.js
    ordine = {p["id"]: i for i, p in enumerate(pianeti)}
    id_parola, contatore = {}, {}
    for w in parole:
        contatore[w["pianeta"]] = contatore.get(w["pianeta"], 0) + 1
        id_parola[(w["parola"], w["pianeta"])] = f"{w['pianeta']}-{contatore[w['pianeta']]}"
    cifrato_di = {(t["id"], riga, w): c for t, w, riga, k, c in cifrate}
    dati_testi = []
    for t in testi:
        corpo = []
        for pz in t["pezzi"]:
            if pz[0] == "c":
                corpo.append({"t": "c", "v": pz[1]})
            else:
                corpo.append({"t": "p", "w": id_parola[(pz[1], t["pianeta"])], "c": cifrato_di[(t["id"], pz[2], pz[1])]})
        # cita: vero o falso, mai il sigillo citato: su Polis sarebbe la chiave in chiaro
        dati_testi.append({"id": t["id"], "pianeta": t["pianeta"], "titolo": t["titolo"], "tipo": t["tipo"],
                           "cita": bool(t["cita"]), "corpo": corpo})
    dati = {
        "schema": 2,
        "pianeti": [dict({"id": p["id"], "nome": p["nome"], "tema": p["tema"], "meccanica": p["meccanica"],
                          "mecc_desc": p["mecc_desc"]},
                         **({"alfabeto_hash": impronta(norm_codice(p["codice_alfabeto"])),
                             "ordine_hash": impronta(norm_codice(p["codice_ordine"]))} if p["id"] in C.CIFRARI else {}))
                    for p in pianeti],
        "testi": dati_testi,
        "parole": [{"id": id_parola[(w["parola"], w["pianeta"])], "pianeta": w["pianeta"], "hash": impronta(w["parola"]),
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

    # ------------------------------------------------------------------ il foglio del narratore
    usa = lambda p: next((x for x in pianeti if x["id"] == p), {"nome": p})["nome"]
    fm = ["# CHIAVI — solo per il narratore", "",
          "Non pubblicare questo file. Generato da costruisci.py: le modifiche vanno in contenuti.md.", "",
          "## I codici delle regole", "",
          "| Pianeta | Alfabeto · Decifratore | Ordine · Apritore | Chiave · Consultatore |", "|---|---|---|---|"]
    for p in cifrati:
        fm.append(f"| {p['nome']} | `{p['codice_alfabeto']}` | `{p['codice_ordine']}` | {PROCEDIMENTO.get(p['id'], '')} |")
    fm += ["", "## Le parole, testo per testo", "",
           "La sigla (HUSA-1...) e' quella che la console mostra nel pannello Parole aperte.", ""]
    for t in testi:
        mie = [x for x in cifrate if x[0] is t]
        if not mie:
            continue
        fm += [f"### {t['id']} · {t['titolo']} ({usa(t['pianeta'])})", "",
               "| Sigla | Nel testo | Parola | Chiave | Apre |", "|---|---|---|---|---|"]
        for _, w, riga, k, c in mie:
            v = next(x for x in parole if x["parola"] == w and x["pianeta"] == t["pianeta"])
            chiave = (f"{k}" if not isinstance(k, list) else f"{next(iter(apre_log[t['cita']]))} ({', '.join(map(str, k))})")
            apre = ", ".join(x for x in (v["apre"], (f"luogo {enigma_di[w]}" if w in enigma_di else "")) if x) or "—"
            fm.append(f"| {id_parola[(w, t['pianeta'])]} | `{c}` | **{w}** | {chiave} | {apre} |")
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
           "Se il tavolo si blocca: leggi la parola da qui e considerala aperta. Il Consultatore la registra,",
           "l'Apritore la digita all'ingresso: sui loro telefoni si apre come se l'avessero decifrata.", ""]
    master = "\n".join(fm)

    # ------------------------------------------------------------------ i segreti
    segreti = set(chiave_di)
    for _, _, cod in codici:
        segreti |= forme_codice(cod)
    segreti = sorted(s for s in segreti if len(s) >= 3)

    # ------------------------------------------------------------------ prima di scrivere: niente fughe
    f_dati = fughe(dati, chiave_di, [c for _, _, c in codici])
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
    for g in ("genera_stampe.py", "genera_offline.py"):
        if not os.path.exists(g):
            err(f"manca {g}: senza, {'stampa.html' if 'stampe' in g else 'prova-offline.html'} resterebbe vecchio.")
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
        dopo = fughe(ricaricati, chiave_di, [c for _, _, c in codici])
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
    with open(".segreti", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(segreti) + "\n")

    n_uniche = len({w["parola"] for w in parole})
    print(f"\n  Costruito: {len(pianeti)} pianeti, {len(testi)} testi, {len(cifrate)} parole cifrate nei testi "
          f"({n_uniche} parole distinte), {len(logs)} voci di registro, {len(enigmi)} luoghi, {len(stanze)} porte")
    print("  Scritti: dati.js, CHIAVI-MASTER.md, .segreti")
    for s in stanze:
        print(f"  porta {s['id']}: {s['puzzle']}, griglia {s['griglia']}"
              + (" (pannello d'insegnamento, facile di proposito)" if griglie.get(s["griglia"], {}).get("insegna") else ""))
    for a in AVVISI:
        print("  avviso:", a)

    # ------------------------------------------------------------------ stampe e copia offline
    for g in ("genera_stampe.py", "genera_offline.py"):
        sys.stdout.flush()
        r = subprocess.run([sys.executable, g])
        if r.returncode != 0:
            print(f"\n  !! {g} e' fallito: {'stampa.html' if 'stampe' in g else 'prova-offline.html'} NON e' aggiornato.")
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
    print("  Nessuna chiave nei file pubblicabili.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
