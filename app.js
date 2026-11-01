/* The Ember Loop — terminale di rilevamento
   Quattro modalita' in una pagina. In questo file e in dati.js non c'e' nessuna
   chiave, nessun codice delle regole e nessuna parola chiave in chiaro: dati.js
   porta solo le impronte, e una parola esiste in chiaro solo sul telefono che l'ha aperta. */
'use strict';

/* ---------------- COSTI — si tarano qui ----------------
   Un numero sono minuti fissi, '1d6+1' si tira. Le app dei ruoli tirano da sole
   e dicono quanto e' costato; il narratore scala dalla console. */
const COSTI = {
  decifra: '1d6+1',   // ogni tentativo al decodificatore con i tre campi pieni, giusto o sbagliato
  porta: '1d6+1',     // una parola sbagliata all'ingresso di un luogo dell'enigma
  indovina: '1d6+1',  // una parola che non esiste, digitata nell'archivio: indovinare costa come decifrare
  registro: 0,        // registrare una parola vera, consultare l'archivio
  lettura: 0,         // aprire un testo dal suo sigillo
};

const D = window.DATI || {}, app = document.getElementById('app'),
      back = document.getElementById('back'), vt = document.getElementById('vt'), vs = document.getElementById('vs');
const el = (t, a = {}, ...kids) => { const n = document.createElement(t);
  for (const k in a) k === 'html' ? n.innerHTML = a[k] : k.startsWith('on') ? n.addEventListener(k.slice(2), a[k]) : n.setAttribute(k, a[k]);
  kids.flat().forEach(c => n.append(c && c.nodeType ? c : document.createTextNode(c))); return n; };
const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); };

/* ---------------- guasti: un errore si vede, non si nasconde ---------------- */
function mostraGuasto(msg) {
  let b = document.getElementById('guasto');
  if (!b) { b = el('div', { id: 'guasto', role: 'alert' }); document.querySelector('.wrap').prepend(b); }
  b.textContent = '⚠ Errore dell’app: ' + msg +
    ' — ricarica la pagina. Se si ripete, il narratore va avanti con il foglio chiavi.';
}
window.addEventListener('error', e => mostraGuasto(e.message || 'sconosciuto'));
window.addEventListener('unhandledrejection', e => mostraGuasto(String(e.reason)));

/* ---------------- dati ---------------- */
const DATI_OK = D.schema === 2 &&
  ['pianeti', 'testi', 'parole', 'log', 'enigmi', 'stanze'].every(k => Array.isArray(D[k]));
const perId = lista => new Map((Array.isArray(lista) ? lista : []).map(x => [x.id, x]));
const PIANETI = perId(D.pianeti), TESTI = perId(D.testi), PAROLE = perId(D.parole),
      LOG = perId(D.log), ENIGMI = perId(D.enigmi);
// impronta -> le voci di quella parola, una per pianeta, nell'ordine dei pianeti
const VOCI = new Map();
if (DATI_OK) {
  const ordine = id => D.pianeti.findIndex(p => p.id === id);
  D.parole.forEach(v => { if (!VOCI.has(v.hash)) VOCI.set(v.hash, []); VOCI.get(v.hash).push(v); });
  VOCI.forEach(l => l.sort((a, b) => ordine(a.pianeta) - ordine(b.pianeta)));
}
const UNICHE = [...VOCI.keys()];            // ordine stabile: serve al codice di stato
const nomePianeta = id => (PIANETI.get(id) || {}).nome || id || '';
/** Il simbolo del mondo che ha scritto una parola: dice con quale cifrario si apre.
    Non e' un segreto — sta accanto alla parola come sta sul muro — ma i codici di quel
    mondo si trovano solo andandoci. */
const simboloDi = mondo => (PIANETI.get(mondo) || {}).simbolo || '?';
/** Trova per sigillo, tollerando la scrittura: "kndl 3" e "KNDL-03" sono lo stesso. */
function perSigillo(lista, code) {
  const forma = s => { const m = /^([A-Z]*)(\d+)$/.exec(Cifrari.normCodice(s));
    return m ? m[1] + '#' + parseInt(m[2], 10) : Cifrari.normCodice(s); };
  const q = forma(code);
  return q ? (Array.isArray(lista) ? lista : []).find(x => forma(x.id) === q) : undefined;
}
/* Un reperto si apre con il suo CODICE, quattro segni, non con il numero del sigillo:
   se bastasse il numero, chi vede HUSA-2 indovina HUSA-3 e legge un reperto che non ha
   trovato. Il numero resta stampato perche' al Custode serve per la chiave. */
const trovaTesto = code => {
  const q = Cifrari.normCodice(code);
  return q ? (D.testi || []).find(t => Cifrari.normCodice(t.codice || '') === q) : undefined;
};
/** Vero se quello che hanno scritto e' il numero del sigillo di un reperto che esiste:
    serve a dirglielo invece di rispondere "non riconosciuto". */
const eNumeroSigillo = code => !!perSigillo(D.testi, code);

/* ---------------- stato locale (per dispositivo) ---------------- */
const SK = 'emberloop.v1';
const vuoto = () => ({ v: 2, testi: [], parole: {}, log: [], stanze: [], enigmi: [], mecc: [], archivio: [], storico: [] });
let S = vuoto(), STATO_VECCHIO = false;
try {
  const x = JSON.parse(localStorage.getItem(SK) || 'null');
  if (x && x.v === 2) S = Object.assign(vuoto(), x);
  else if (x) STATO_VECCHIO = true;   // di una versione precedente dell'app: si ignora, non si mescola
} catch (e) {}
const save = () => { try { localStorage.setItem(SK, JSON.stringify(S)); } catch (e) {} };
const ora = () => new Date().toTimeString().slice(0, 5);

/* ---------------- costi ---------------- */
function tira(spec) {
  if (typeof spec === 'number') return { min: spec, come: spec + ' min' };
  const m = /^(\d+)d(\d+)([+-]\d+)?$/i.exec(String(spec).replace(/\s+/g, ''));
  if (!m) throw new Error('COSTI: non capisco il costo «' + spec + '». Scrivi un numero di minuti oppure qualcosa come 1d6+1.');
  const dadi = [];
  for (let i = 0; i < +m[1]; i++) dadi.push(1 + Math.floor(Math.random() * +m[2]));
  const b = m[3] ? parseInt(m[3], 10) : 0, tot = Math.max(0, dadi.reduce((a, x) => a + x, 0) + b);
  return { min: tot, come: m[0].toLowerCase() + ' = ' + dadi.join('+') + (b ? (b > 0 ? '+' : '') + b : '') + ' = ' + tot + ' min' };
}
const etichettaCosto = spec => typeof spec === 'number' ? (spec ? spec + ' min' : 'gratis') : spec + ' min';
/** Registra un'azione nello storico locale, con il suo costo in minuti. */
function segna(tipo, cosa, minuti) { S.storico.push({ t: tipo, c: cosa, m: minuti, q: ora() }); save(); }
/** Tira il costo di un'azione e lo scrive nello storico. */
function spendi(voce, cosa) { const t = tira(COSTI[voce]); if (t.min > 0) segna(voce, cosa, t.min); return t; }
const rigaCosto = t => t.min > 0 ? 'Costo ' + t.come + ' — ditelo al narratore.' : 'Nessun costo.';

/* ---------------- la conoscenza: si apre e non si richiude ---------------- */
function visita(id) {
  if (S.testi.includes(id)) return false;
  S.testi.push(id); S.archivio.push({ k: 't', id, q: ora() }); save(); return true;
}
/** Una parola aperta resta aperta per sempre, su questo telefono e in tutti i testi.
    Il reset del loop non la tocca: niente in questo file la richiude. */
function apriParola(h, parola) {
  const voci = VOCI.get(h) || [], nuova = !S.parole[h];
  if (nuova) { S.parole[h] = parola; S.archivio.push({ k: 'p', h, q: ora() }); }
  voci.forEach(v => { if (v.apre_log && !S.log.includes(v.apre_log)) S.log.push(v.apre_log); });
  save(); aggiornaPiede();
  return { nuova, log: [...new Set(voci.map(v => v.apre_log).filter(Boolean))],
           enigmi: [...new Set(voci.map(v => v.apre_enigma).filter(Boolean))] };
}

/* ---------------- codice di stato, per il narratore ----------------
   Ogni telefono tiene il proprio stato e non c'e' rete. Il codice in fondo alle
   schermate dei ruoli dice quali parole sono aperte li': il narratore lo scrive
   nella console. Due segni di controllo e una firma dei dati lo fanno fallire
   forte se e' letto male (sfugge un errore su 1024) o viene da un'altra versione. */
const B32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const dueSegni = s => { const n = parseInt(Cifrari.impronta(s).slice(0, 3), 16) & 1023; return B32[n >> 5] + B32[n & 31]; };
const firmaDati = () => dueSegni('dati:' + UNICHE.join(','));
const controllo = s => dueSegni('stato:' + s);
function codiceStato(aperte) {
  let s = firmaDati();
  for (let i = 0; i < UNICHE.length; i += 5) {
    let v = 0;
    for (let j = 0; j < 5; j++) v = v * 2 + (aperte[UNICHE[i + j]] ? 1 : 0);
    s += B32[v];
  }
  s += controllo(s);
  return s.match(/.{1,4}/g).join('-');
}
function leggiCodiceStato(testo) {
  const s = String(testo).toUpperCase().replace(/[^0-9A-Z]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1');
  const attesa = 2 + Math.ceil(UNICHE.length / 5) + 2;
  if (!s) return { errore: 'Scrivi il codice che compare in fondo alla schermata del telefono.' };
  if (s.length !== attesa) return { errore: 'Il codice ha ' + attesa + ' segni, qui ne leggo ' + s.length + '. Ricontrollalo.' };
  if (Array.from(s).some(c => B32.indexOf(c) < 0)) return { errore: 'Nel codice c’è un segno che non esiste (la U). Ricontrollalo.' };
  if (controllo(s.slice(0, -2)) !== s.slice(-2)) return { errore: 'Il codice non torna: un segno è stato letto male. Ricontrollalo.' };
  if (s.slice(0, 2) !== firmaDati()) return { errore: 'Il codice viene da un telefono con dati diversi da questi: ricaricate la pagina su tutti e due.' };
  const corpo = s.slice(2, -2), aperte = new Set();
  UNICHE.forEach((h, i) => { if ((B32.indexOf(corpo[Math.floor(i / 5)]) >> (4 - i % 5)) & 1) aperte.add(h); });
  return { aperte };
}
let piedeEl = null;
function aggiornaPiede() {
  if (!piedeEl) return;
  clear(piedeEl);
  if (!DATI_OK || !Object.keys(S.parole).length) return;
  piedeEl.append('Per il narratore, se lo chiede · codice stato ', el('span', { class: 'mono' }, codiceStato(S.parole)));
}
function piede() { piedeEl = el('p', { class: 'piede' }); aggiornaPiede(); return piedeEl; }

/* ---------------- glifi Kindler (deterministici dal sigillo) ---------------- */
const GL = '▲▼◆◇○●□■△▽◁▷◀▶┌┐└┘├┤┬┴┼─│╱╲╳⌐¬±∴∵≈≠≡⊂⊃⊕⊗⌂'.split('');
function glifi(seme, n) {
  let h = 2166136261;
  for (const ch of seme) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
  let s = '';
  for (let i = 0; i < n; i++) { h ^= h << 13; h >>>= 0; h ^= h >> 17; h ^= h << 5; h >>>= 0;
    s += GL[h % GL.length]; if (i % 5 === 4) s += ' '; }
  return s;
}

/* ---------------- scanner QR ---------------- */
const Cam = {
  stream: null, raf: 0,
  async start(box, onCode) {
    const v = box.querySelector('video'), cv = document.createElement('canvas'), cx = cv.getContext('2d', { willReadFrequently: true });
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' },
                 width: { ideal: 1280 }, height: { ideal: 720 } } });
    } catch (e) { this.errore = (e && e.name) || 'errore'; return false; }

    // ORDINE CRITICO PER iOS: il contenitore va reso visibile PRIMA di play().
    // Safari non riproduce un video dentro un elemento display:none, quindi
    // videoWidth resterebbe 0 e il ciclo di scansione girerebbe a vuoto.
    box.style.display = 'block';
    v.setAttribute('playsinline', '');
    v.setAttribute('webkit-playsinline', '');
    v.muted = true; v.defaultMuted = true;
    v.srcObject = this.stream;
    try { await v.play(); }
    catch (e) { this.errore = 'play:' + ((e && e.name) || 'rifiutato'); this.stop(box); return false; }
    let frame = 0, muti = 0;
    const cerca = (sx, sy, sw, sh, dw) => {
      const dh = Math.round(sh * dw / sw);
      cv.width = dw; cv.height = dh;
      cx.drawImage(v, sx, sy, sw, sh, 0, 0, dw, dh);
      const d = cx.getImageData(0, 0, dw, dh);
      return jsQR(d.data, dw, dh, { inversionAttempts: 'attemptBoth' });
    };
    const tick = () => {
      if (v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth) {
        frame++;
        const W = v.videoWidth, H = v.videoHeight;
        // passata A: tutto il fotogramma, ridotto quanto basta
        let r = cerca(0, 0, W, H, Math.min(800, W));
        // passata B: solo il centro, a piena risoluzione. Serve quando il sigillo
        // e' lontano o piccolo: nella passata A i moduli sarebbero troppo fini.
        if (!r) {
          const lato = Math.round(Math.min(W, H) * 0.72);
          r = cerca(Math.round((W - lato) / 2), Math.round((H - lato) / 2), lato, lato, Math.min(800, lato));
        }
        const cap = box.querySelector('.cap');
        if (cap && frame % 8 === 0) cap.textContent = 'cerco un sigillo… ' + frame + ' fotogrammi';
        if (r && r.data) { this.stop(box); onCode(r.data.trim().toUpperCase()); return; }
      } else {
        // il video non sta producendo fotogrammi: dopo qualche secondo avvisa,
        // invece di restare in silenzio come faceva prima.
        muti++;
        const cap = box.querySelector('.cap');
        if (cap && muti === 120) cap.textContent = 'il video non parte (readyState ' + v.readyState + ')';
      }
      this.raf = requestAnimationFrame(tick);
    };
    tick(); return true;
  },
  stop(box) {
    cancelAnimationFrame(this.raf);
    if (this.stream) { this.stream.getTracks().forEach(t => t.stop()); this.stream = null; }
    if (box) { box.style.display = 'none'; const v = box.querySelector('video'); if (v) v.srcObject = null; }
  }
};
function scanner(onCode) {
  const box = el('div', { id: 'cam' }, el('video', { playsinline: '' }),
    el('div', { class: 'ret' }), el('div', { class: 'cap' }, 'inquadra il sigillo'));
  const b = el('button', { class: 'big', type: 'button', onclick: async () => {
      if (typeof jsQR !== 'function') {
        b.textContent = '✕  Decodificatore QR non caricato';
        b.style.borderColor = 'var(--bad)'; b.style.color = 'var(--bad)';
        box.insertAdjacentElement('beforebegin', el('p', { class: 'err' },
          'Manca jsQR.min.js accanto alla pagina. Usa il codice scritto sotto il sigillo.'));
        return;
      }
      if (Cam.stream) { Cam.stop(box); b.textContent = '⌘  Scansiona sigillo'; return; }
      b.textContent = 'Avvio fotocamera…';
      // il primo fotogramma puo' contenere gia' il codice: in quel caso start()
      // ritorna DOPO il callback, e non dobbiamo riscrivere l'etichetta.
      let letto = false;
      const ok = await Cam.start(box, c => { letto = true; b.textContent = '⌘  Scansiona sigillo'; onCode(c); });
      if (letto) {
        // il codice e' stato letto sul primo fotogramma: il callback ha gia' sistemato tutto
      } else if (ok) {
        b.textContent = '✕  Chiudi fotocamera';
      } else {
        const perche = Cam.errore === 'NotAllowedError' ? 'permesso negato'
          : Cam.errore === 'NotFoundError' ? 'nessuna fotocamera'
          : !window.isSecureContext ? 'serve https (o localhost)'
          : (Cam.errore || 'non disponibile');
        b.textContent = '✕  Fotocamera: ' + perche;
        b.style.borderColor = 'var(--bad)'; b.style.color = 'var(--bad)';
      }
    } }, '⌘  Scansiona sigillo');
  return [b, box];
}

/* ---------------- viste ---------------- */
const V = {};
function titolo(t, s) { vt.textContent = t; vs.textContent = s; clear(app); piedeEl = null; }
/** Con dati.js vecchio o assente le viste dei ruoli si fermano e dicono chi rimedia. */
function avvisoDati() {
  return el('div', { class: 'card bad' },
    el('div', { class: 'eyebrow', style: 'color:var(--bad)' }, 'Dati da rigenerare'),
    el('p', { style: 'margin:8px 0 0' }, window.DATI
      ? 'dati.js è nel formato vecchio, di prima della specifica nuova: questa app non lo sa leggere, e preferisce fermarsi che mostrarvi cose sbagliate.'
      : 'Manca dati.js accanto alla pagina.'),
    el('p', { class: 'hint' }, 'Chi rimedia: Alessandro. Porta contenuti.md al formato nuovo e rilancia  python costruisci.py. Il narratore intanto va avanti con il foglio chiavi stampato.'));
}
function datiPronti() { if (DATI_OK) return true; app.append(avvisoDati()); return false; }

V.ruoli = () => {
  back.classList.add('hide'); titolo('The Ember Loop', 'Terminale di rilevamento');
  const R = [
    ['01', 'decifra', 'Il Traduttore', 'Scansiona i sigilli: i reperti si aprono da soli. Le parole cifrate dentro si aprono solo in tre.'],
    ['02', 'log', 'Il Custode', 'Tiene l’archivio di ciò che il tavolo apre, e i rimandi fra i reperti.'],
    ['03', 'stanze', "L'Apritore", 'Apre le porte di pietra tracciando i percorsi, e gli ingressi dei luoghi con le parole decifrate.']
  ];
  if (!DATI_OK) app.append(avvisoDati());
  app.append(el('p', { class: 'hint', style: 'margin:0 0 18px' },
    'Tre rilevatori, tre terminali. Ognuno apre ciò che gli altri non possono.'));
  const g = el('div', { class: 'roles' });
  R.forEach(([n, id, t, d]) => g.append(el('button', { class: 'role', type: 'button', onclick: () => go(id) },
    el('div', { class: 'n' }, 'Ruolo ' + n), el('h3', {}, t), el('p', {}, d))));
  g.append(el('button', { class: 'role gm', type: 'button', onclick: () => go('master') },
    el('div', { class: 'n' }, 'Master'), el('h3', {}, 'Console di Sistema'),
    el('p', {}, 'Budget del loop, costi in minuti, parole aperte, failsafe. Solo per il narratore.')));
  app.append(g);
};

/** Il corpo di un testo: il chiaro com'e', le parole cifrate come blocchi,
    quelle gia' aperte su questo telefono in chiaro e sottolineate. */
function corpoTesto(t, onParola) {
  const box = el('div', { class: 'plain' });
  (t.corpo || []).forEach(s => {
    if (s.t === 'c') { box.append(s.v); return; }
    const v = PAROLE.get(s.w);
    if (!v) { box.append(el('span', { class: 'cw rotta', title: 'dato incoerente: rigenera dati.js' }, s.c)); return; }
    const chiaro = S.parole[v.hash], seg = el('span', { class: 'cw-s' }, simboloDi(v.mondo));
    if (chiaro) box.append(el('span', { class: 'cw aperta', 'data-w': s.w }, chiaro));
    else if (onParola) box.append(el('button', { class: 'cw', type: 'button', 'data-w': s.w, onclick: () => onParola(s, v) }, seg, s.c));
    else box.append(el('span', { class: 'cw', 'data-w': s.w }, seg, s.c));
  });
  return box;
}

/* ---- 01 · TRADUTTORE ---- */
V.decifra = () => {
  titolo('Traduttore', 'Sigilli, reperti e parole cifrate');
  if (!datiPronti()) return;
  const out = el('div'), gia = el('div');
  const errore = el('p', { class: 'err hide' });
  const codeIn = el('input', { type: 'text', placeholder: 'quattro segni', autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
  const mostra = t => { mostraTesto(out, t); disegnaGia(); };
  const apri = code => {
    const t = trovaTesto(code);
    if (!t) { errore.textContent = eNumeroSigillo(code)
        ? '⚠ «' + code + '» è il numero del sigillo, quello grande in alto: serve al Custode per la chiave, non ad aprire. Il codice del sigillo sono i quattro segni stampati sotto.'
        : '⚠ Codice non riconosciuto: «' + code + '». Sono quattro segni stampati sotto il sigillo.';
      errore.classList.remove('hide'); return; }
    errore.classList.add('hide'); codeIn.value = '';
    visita(t.id); mostra(t);
    if (out.scrollIntoView) out.scrollIntoView({ block: 'start', behavior: 'smooth' });
  };
  const daCampo = () => { const c = codeIn.value.trim();
    if (!c) { errore.textContent = '⚠ Scrivi il codice stampato sotto il sigillo: quattro segni.';
      errore.classList.remove('hide'); codeIn.focus(); return; }
    apri(c); };
  codeIn.addEventListener('keydown', e => { if (e.key === 'Enter') daCampo(); });
  const disegnaGia = () => {
    clear(gia);
    if (!S.testi.length) return;
    gia.append(el('div', { class: 'eyebrow', style: 'margin:22px 0 10px' }, 'Già aperti su questo telefono'));
    S.testi.forEach(id => { const t = TESTI.get(id);
      if (t) gia.append(el('button', { class: 'chip-btn', type: 'button', onclick: () => { mostra(t); out.scrollIntoView({ block: 'start' }); } },
        id + ' · ' + t.titolo)); });
  };
  const [scanBtn, camBox] = scanner(apri);
  app.append(scanBtn, camBox,
    el('div', { class: 'card' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Codice del sigillo'), codeIn),
      el('button', { class: 'big ghost', type: 'button', style: 'margin-top:12px', onclick: daCampo }, 'Apri reperto'),
      errore,
      el('p', { class: 'hint' }, 'Se la fotocamera non parte, digita il codice stampato sotto il sigillo.')),
    out, gia, piede());
  disegnaGia();
};

function mostraTesto(out, t) {
  clear(out);
  const card = el('div', { class: 'card testo' }), dec = el('div');
  const disegna = () => {
    clear(card);
    card.append(el('div', { class: 'eyebrow' }, t.id + ' · ' + nomePianeta(t.pianeta)),
      el('h3', { class: 'tit' }, t.titolo),
      el('div', { class: 'glifi-riga', 'aria-hidden': 'true' }, glifi(t.id, 25)),
      corpoTesto(t, (s, v) => decodificatore(dec, t, s, v, disegna)));
    if (t.cita) card.append(el('p', { class: 'cita' }, 'Questo reperto ne nomina un altro.'));
    if ((t.corpo || []).some(s => s.t === 'p' && PAROLE.get(s.w) && !S.parole[PAROLE.get(s.w).hash]))
      card.append(el('p', { class: 'hint' }, 'Tocca una parola cifrata per aprire il decodificatore. Servono tutti e tre.'));
  };
  disegna();
  out.append(card, dec);
}

/** Quale regola corrisponde a un codice digitato: il codice si confronta per impronta,
    mai in chiaro. Una regola di un altro pianeta si applica lo stesso: esce spazzatura. */
function regola(parte, codice) {
  const h = Cifrari.impronta(Cifrari.normCodice(codice));
  const p = D.pianeti.find(x => x[parte + '_hash'] === h);
  return p && Cifrari.CIFRARI[p.id] ? Cifrari.CIFRARI[p.id][parte] : null;
}
const elencoItaliano = l => l.length < 2 ? l.join('') : l.slice(0, -1).join(', ') + ' e ' + l[l.length - 1];

function decodificatore(dec, t, seg, voce, ridisegnaTesto) {
  clear(dec);
  const campo = (lbl, chi, ph, nome) => {
    const i = el('input', { type: 'text', name: nome, placeholder: ph, autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
    return [i, el('label', { class: 'fld' }, el('span', { class: 'lbl' }, lbl + ' ', el('span', { class: 'chi' }, '· ' + chi)), i)];
  };
  const [fA, lA] = campo('Alfabeto', 'lo porta il Traduttore', 'codice kindler', 'alfabeto');
  const [fK, lK] = campo('Chiave', 'la trova il Custode', 'un numero o una parola', 'chiave');
  const [fO, lO] = campo('Ordine', 'lo porta l’Apritore', 'codice kindler', 'ordine');
  const esito = el('div', { class: 'esito' });
  const vai = () => {
    clear(esito);
    // un campo vuoto non e' mai muto: dice cosa manca e chi lo porta
    const mancano = [];
    if (!Cifrari.normCodice(fA.value)) mancano.push(['l’alfabeto', 'lo porta il Traduttore', fA]);
    if (!fK.value.trim()) mancano.push(['la chiave', 'la trova il Custode', fK]);
    if (!Cifrari.normCodice(fO.value)) mancano.push(['l’ordine', 'lo porta l’Apritore', fO]);
    if (mancano.length) {
      esito.append(el('p', { class: 'err' }, '⚠ ' + (mancano.length === 1
        ? 'Manca ' + mancano[0][0] + ': ' + mancano[0][1] + '.'
        : 'Mancano ' + elencoItaliano(mancano.map(m => m[0] + ' (' + m[1] + ')')) + '.')));
      mancano[0][2].focus(); return;
    }
    const chiave = Cifrari.leggiChiave(fK.value);
    if (!chiave) {
      esito.append(el('p', { class: 'err' }, '⚠ La chiave è un numero oppure una parola: «' + fK.value.trim() +
        '» non è né l’uno né l’altra. La trova il Custode.'));
      fK.focus(); return;
    }
    // ogni tentativo completo costa, giusto o sbagliato
    const costo = spendi('decifra', t.id + ' · ' + seg.c);
    const ra = regola('alfabeto', fA.value), ro = regola('ordine', fO.value);
    const ignoti = [];
    if (!ra) ignoti.push('il codice dell’alfabeto «' + fA.value.trim() + '» (lo porta il Traduttore)');
    if (!ro) ignoti.push('il codice dell’ordine «' + fO.value.trim() + '» (lo porta l’Apritore)');
    if (ignoti.length) {
      esito.append(el('p', { class: 'err' }, '⚠ Non corrisponde a nessuna regola kindler: ' + elencoItaliano(ignoti) +
        '. Ricontrollate la frase che avete trovato.'), el('p', { class: 'costo' }, rigaCosto(costo)));
      return;
    }
    const uscita = Cifrari.applica(ra, ro, seg.c, chiave.k);
    if (Cifrari.impronta(uscita) === voce.hash) {
      const r = apriParola(voce.hash, uscita);
      ridisegnaTesto();
      clear(dec);
      dec.append(el('div', { class: 'card acc' },
        el('div', { class: 'eyebrow', style: 'color:var(--ember)' }, 'Parola aperta'),
        el('div', { class: 'aperta-big mono' }, uscita),
        el('p', { style: 'margin:6px 0 0' }, 'Si apre in tutti i reperti di questo telefono ed entra nell’archivio.'),
        r.log.length ? el('p', { style: 'margin:6px 0 0' }, '▸ Apre una voce del registro: ditela al Custode.') : '',
        r.enigmi.length ? el('p', { class: 'ok' }, '▸ Questa apre un luogo. Ditelo all’Apritore.') : '',
        el('p', { class: 'costo' }, rigaCosto(costo))));
    } else {
      // niente verdetto e niente indizi su quale parte sia sbagliata: devono capirlo loro
      esito.append(el('div', { class: 'uscita mono' }, uscita), el('p', { class: 'costo' }, rigaCosto(costo)));
    }
  };
  // Invio porta al prossimo campo vuoto; decifra solo quando sono pieni tutti e tre
  [fA, fK, fO].forEach(i => i.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const vuoto = [fA, fK, fO].find(x => !x.value.trim());
    if (vuoto) vuoto.focus(); else vai();
  }));
  dec.append(el('div', { class: 'card dec' },
    el('div', { class: 'eyebrow', style: 'color:var(--warm)' }, 'Decodificatore · ' + t.id),
    el('div', { class: 'cw-big mono' }, el('span', { class: 'cw-s grande' }, simboloDi(voce.mondo)), seg.c),
    el('p', { class: 'hint', style: 'margin:0 0 12px' },
      'Questa parola l’ha scritta ' + simboloDi(voce.mondo) + ': servono l’alfabeto e l’ordine di quel mondo, e la chiave si trova come si fa lì.'),
    lA, lK, lO,
    el('button', { class: 'big', type: 'button', style: 'margin-top:12px', onclick: vai }, 'Decifra · ' + etichettaCosto(COSTI.decifra)),
    esito));
  if (dec.scrollIntoView) dec.scrollIntoView({ block: 'nearest' });
}

/* ---- 02 · CUSTODE — archivio e rimandi ---- */
/** Lo strumento del Custode: la chiave di un mondo, con la calcolatrice.
    Si apre SOLO dopo che questo telefono ha scansionato il reperto di quel mondo che
    spiega la chiave. E' il mestiere del Custode, ma resta una cosa da scoprire:
    se l'app lo dicesse da sola, i reperti propedeutici non servirebbero a niente. */
function pannelloChiavi() {
  const box = el('div', { class: 'card' },
    el('div', { class: 'eyebrow' }, 'Le chiavi'));
  const mondi = (D.pianeti || []).filter(p => Cifrari.CIFRARI[p.id]);
  // quali chiavi ha imparato questo telefono: il reperto che le spiega l'ha visitato
  const saputa = p => (S.testi || []).some(id => {
    const t = TESTI.get(id);
    return t && t.pianeta === p.id && (t.rivela || []).includes('chiave');
  });
  const campo = (lbl, modo) => {
    const i = el('input', { type: 'text', inputmode: modo === 'n' ? 'numeric' : 'text',
      autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
    return [i, el('label', { class: 'fld' }, el('span', { class: 'lbl' }, lbl), i)];
  };
  let aperte = 0;
  mondi.forEach(p => {
    const riga = el('div', { class: 'cif-m' },
      el('div', { class: 'cif-h' }, el('span', { class: 'cif-s' }, p.simbolo || '?'), p.nome));
    if (!saputa(p)) {
      riga.append(el('p', { class: 'hint', style: 'margin:2px 0 0' },
        'Non ancora. Il reperto di ' + p.nome + ' che spiega come si trova la chiave è là fuori: ' +
        'quando il tavolo lo scansiona e tu lo registri, qui compare la regola e il conto si fa da solo.'));
      box.append(riga); return;
    }
    aperte++;
    const c = Cifrari.CIFRARI[p.id];
    riga.append(el('p', { class: 'cif-v', style: 'margin:2px 0 10px' }, (c.dice || {}).chiave || ''));
    const esito = el('div', { class: 'chiave-out mono' }, '—');
    let leggi;
    if (p.id === 'IRIS') {
      const [f, l] = campo('La prima parola in chiaro del reperto', 't');
      riga.append(l);
      leggi = () => { const k = Cifrari.leggiChiave(f.value);
        return k && k.tipo === 'parola' ? k.k.join('-') : null; };
      f.addEventListener('input', () => esito.textContent = leggi() || '—');
    } else {
      const somma = p.id === 'HUSA';
      const [a, la] = campo('Numero del sigillo', 'n');
      const [b, lb] = campo(somma ? 'Quante lettere ha la parola cifrata' : 'Che posto occupa la parola nel reperto', 'n');
      riga.append(el('div', { class: 'grid2' }, la, lb));
      leggi = () => { const x = parseInt(a.value, 10), y = parseInt(b.value, 10);
        if (!(x > 0) || !(y > 0)) return null;
        return String(somma ? x + y : x * y); };
      [a, b].forEach(i => i.addEventListener('input', () => esito.textContent = leggi() || '—'));
    }
    riga.append(esito);
    box.append(riga);
  });
  box.append(el('p', { class: 'hint', style: 'margin:12px 0 0' }, aperte
    ? 'Il numero che esce qui lo detti al Traduttore: lo scrive nel campo Chiave del decodificatore.'
    : 'Qui non c’è ancora niente: le regole delle chiavi si trovano nei reperti, uno per mondo.'));
  return box;
}

V.log = () => {
  titolo('Custode', 'Archivio e rimandi');
  if (!datiPronti()) return;
  let aperto = null;                                   // la voce dell'archivio aperta
  const lista = el('div'), conta = el('div', { class: 'eyebrow', style: 'margin:18px 0 10px' });
  const fb = el('p', { class: 'hint' }, 'Un sigillo mette un reperto nell’archivio. Una parola te la dice il Traduttore quando l’ha aperta: registrarla è gratis, una parola che non esiste costa ' + etichettaCosto(COSTI.indovina) + '.');
  const dice = (cls, testo) => { fb.className = cls; fb.textContent = testo; };
  const inp = el('input', { type: 'text', placeholder: 'codice del sigillo oppure una parola', autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
  const cerca = el('input', { type: 'text', placeholder: 'parola, sigillo, titolo, LOG…', autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
  const numero = pred => S.archivio.findIndex(pred) + 1;

  const registra = raw => {
    const v = String(raw || '').trim();
    if (!v) { dice('err', '⚠ Scrivi il codice di un sigillo (quattro segni) oppure una parola che il Traduttore ha aperto.'); inp.focus(); return; }
    const t = trovaTesto(v);
    if (t) {
      const nuovo = visita(t.id); aperto = 't:' + t.id; inp.value = '';
      // il reperto appena registrato puo' essere quello che spiega una chiave
      if (nuovo && (t.rivela || []).includes('chiave')) { go('log'); return; }
      dice('ok', (nuovo ? '✓ Nell’archivio come #' + numero(a => a.k === 't' && a.id === t.id) + ': ' : 'Era già nell’archivio: ') + t.titolo);
      disegna(); return;
    }
    if (eNumeroSigillo(v)) {
      dice('hint', '«' + v + '» è il numero del sigillo, non il codice. Il codice del sigillo sono i quattro segni stampati sotto.'); return;
    }
    if (perSigillo(D.log, v) || /^LOG\W*\d+$/i.test(v)) {
      dice('hint', 'Le voci del registro non si scansionano: si aprono con la parola che le apre. Chiedetela al Traduttore.'); return;
    }
    const w = Cifrari.normParola(v);
    if (!w) { dice('err', '⚠ «' + v + '» non è né un sigillo né una parola.'); return; }
    const h = Cifrari.impronta(w);
    if (VOCI.has(h)) {
      const r = apriParola(h, w); aperto = 'p:' + h; inp.value = '';
      dice('ok', r.nuova ? '✓ «' + w + '» entra nell’archivio come #' + numero(a => a.k === 'p' && a.h === h) + '.' : '«' + w + '» era già nell’archivio.');
      disegna(); return;
    }
    const costo = spendi('indovina', '«' + w + '» a vuoto');
    dice('err', '⚠ «' + w + '» non è una parola dei reperti. ' + rigaCosto(costo));
  };

  const testaVoce = (a, tipo, nome, sotto) => el('button', { class: 'arch-h', type: 'button', 'aria-expanded': String(aperto === a.chiave),
      onclick: () => { aperto = aperto === a.chiave ? null : a.chiave; disegna(); } },
    el('span', { class: 'arch-n mono' }, '#' + a.n),
    el('span', { class: 'arch-t' }, el('span', { class: 'meta' }, tipo + (sotto ? ' · ' + sotto : '') + ' · ' + a.q), el('b', {}, nome)));

  const voceTesto = (a, t) => {
    const it = el('div', { class: 'item arch' }, testaVoce(a, 'Reperto', t.id + ' · ' + t.titolo, nomePianeta(t.pianeta)));
    if (aperto === a.chiave) {
      it.append(corpoTesto(t, null));
      if (t.cita) it.append(el('p', { class: 'cita' }, 'Questo reperto ne nomina un altro.'));
      if ((t.corpo || []).some(s => s.t === 'p' && PAROLE.get(s.w) && !S.parole[PAROLE.get(s.w).hash]))
        it.append(el('p', { class: 'hint' }, 'Le parole cifrate si aprono dal Traduttore, in tre.'));
    }
    return it;
  };
  const voceParola = (a, w) => {
    const voci = VOCI.get(a.h) || [];
    const it = el('div', { class: 'item arch' },
      testaVoce(a, 'Parola', w, (voci.length ? simboloDi(voci[0].mondo) + ' · ' : '') + voci.map(v => nomePianeta(v.pianeta)).join(', ')));
    if (aperto !== a.chiave) return it;
    // una voce per pianeta, in ordine: il senso cambia scendendo indietro nel tempo
    voci.forEach(v => {
      const box = el('div', { class: 'voce' }, el('div', { class: 'meta' }, nomePianeta(v.pianeta)));
      if (v.nota) box.append(el('div', { class: 'body' }, v.nota));
      const L = v.apre_log && LOG.get(v.apre_log);
      if (L) box.append(el('div', { class: 'reg' }, el('div', { class: 'meta' }, L.id + ' · voce di registro'),
        el('h4', {}, L.titolo), el('div', { class: 'body' }, L.corpo)));
      const E = v.apre_enigma && ENIGMI.get(v.apre_enigma);
      if (E) box.append(el('div', { class: 'clue' }, '▸ Apre un luogo: ' + E.nome + '. Ditelo all’Apritore.'));
      if (!v.nota && !L && !E) box.append(el('div', { class: 'body' }, 'Nessuna nota per questo mondo.'));
      it.append(box);
    });
    // i rimandi: ogni testo che la contiene, visitato o no (di quelli non visitati, solo titolo e sigillo)
    const ids = new Set(voci.map(v => v.id));
    const dove = D.testi.filter(t => (t.corpo || []).some(s => s.t === 'p' && ids.has(s.w)));
    const rim = el('div', { class: 'rimandi' }, el('div', { class: 'meta' }, 'Compare in ' + dove.length + (dove.length === 1 ? ' testo' : ' testi')));
    dove.forEach(t => {
      const visto = S.testi.includes(t.id);
      rim.append(visto
        ? el('button', { class: 'rim visto', type: 'button', onclick: () => { aperto = 't:' + t.id; cerca.value = ''; disegna(); } },
            t.id + ' · ' + t.titolo + ' · ' + nomePianeta(t.pianeta) + '  ✓')
        : el('div', { class: 'rim' }, t.id + ' · ' + t.titolo + ' · ' + nomePianeta(t.pianeta) + '  · non ancora visitato'));
    });
    it.append(rim);
    return it;
  };
  const corrisponde = (a, q) => {
    if (!q) return true;
    if (a.k === 't') { const t = TESTI.get(a.id); return !!t && (Cifrari.normCodice(t.id).includes(Cifrari.normCodice(q)) || t.titolo.toUpperCase().includes(q)); }
    const w = S.parole[a.h] || '';
    const nq = Cifrari.normParola(q);
    return (nq && w.includes(nq)) || (VOCI.get(a.h) || []).some(v => {
      const L = v.apre_log && LOG.get(v.apre_log);
      return L && (Cifrari.normCodice(L.id) === Cifrari.normCodice(q) || L.titolo.toUpperCase().includes(q)); });
  };
  function disegna() {
    clear(lista);
    const q = cerca.value.trim().toUpperCase();
    let mostrate = 0;
    S.archivio.forEach((x, i) => {
      const a = Object.assign({ n: i + 1, chiave: x.k === 't' ? 't:' + x.id : 'p:' + x.h }, x);
      if (!corrisponde(a, q)) return;
      if (a.k === 't' && TESTI.get(a.id)) { lista.append(voceTesto(a, TESTI.get(a.id))); mostrate++; }
      else if (a.k === 'p' && S.parole[a.h]) { lista.append(voceParola(a, S.parole[a.h])); mostrate++; }
    });
    conta.textContent = S.testi.length + ' testi · ' + Object.keys(S.parole).length + ' parole' + (q ? ' · ' + mostrate + ' trovate' : '');
    if (!S.archivio.length) lista.append(el('p', { class: 'hint' }, 'L’archivio è vuoto. Scansiona un sigillo, o registra una parola che il Traduttore ha aperto.'));
    else if (q && !mostrate) lista.append(el('p', { class: 'hint' }, 'Niente nell’archivio per «' + cerca.value.trim() + '».'));
  }
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') registra(inp.value); });
  cerca.addEventListener('input', disegna);
  const [scanBtn, camBox] = scanner(c => registra(c));
  app.append(
    el('div', { class: 'card acc' },
      el('div', { class: 'eyebrow', style: 'color:var(--ember);margin-bottom:10px' }, 'Registra'),
      scanBtn, camBox,
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Sigillo o parola'), inp),
      el('button', { class: 'big log-go', type: 'button', style: 'margin-top:12px', onclick: () => registra(inp.value) }, 'Registra'),
      fb),
    pannelloChiavi(),
    el('label', { class: 'fld', style: 'margin-top:18px' }, el('span', { class: 'lbl' }, 'Cerca nell’archivio'), cerca),
    conta, lista, piede());
  disegna();
};

/* ---- 03 · APRITORE — porte di pietra e ingressi dei luoghi ----
   Due cose distinte, che non si mescolano: le porte si aprono da soli tracciando
   un percorso; gli ingressi solo con una parola decifrata, cioe' in tre. */
V.stanze = () => {
  titolo('Apritore', 'Porte e ingressi');
  if (!datiPronti()) return;
  const porte = el('div', { class: 'roles' });
  D.stanze.forEach(st => {
    const fatto = S.stanze.includes(st.id);
    porte.append(el('button', { class: 'role' + (fatto ? ' fatto' : ''), type: 'button', 'data-stanza': st.id, onclick: () => porta(st) },
      el('div', { class: 'n' }, nomePianeta(st.pianeta)),
      el('h3', {}, st.nome),
      el('p', {}, fatto ? '✓ Aperta' : 'Sigillata. Traccia il percorso per aprirla.')));
  });
  if (!D.stanze.length) porte.append(el('p', { class: 'hint' }, 'Nessuna porta di pietra nei dati.'));
  const ingressi = el('div');
  D.enigmi.forEach(E => ingressi.append(ingresso(E)));
  if (!D.enigmi.length) ingressi.append(el('p', { class: 'hint' }, 'Nessun luogo dell’enigma nei dati, per ora.'));
  app.append(
    el('div', { class: 'eyebrow sez' }, 'Porte di pietra'),
    el('p', { class: 'hint', style: 'margin:0 0 12px' }, 'Le apri da solo: traccia la linea dal nodo pieno all’uscita.'),
    porte,
    el('div', { class: 'eyebrow sez' }, 'Ingressi dei luoghi'),
    el('p', { class: 'hint', style: 'margin:0 0 12px' }, 'Si aprono solo con una parola decifrata, cioè in tre. Una parola sbagliata costa ' + etichettaCosto(COSTI.porta) + '.'),
    ingressi, piede());
};

function ingresso(E) {
  const box = el('div', { class: 'card', 'data-enigma': E.id });
  const disegna = () => {
    clear(box);
    box.append(el('div', { class: 'eyebrow' }, nomePianeta(E.pianeta)), el('h3', { class: 'tit' }, E.nome));
    if (S.enigmi.includes(E.id)) {
      box.className = 'card acc';
      box.append(el('div', { class: 'eyebrow', style: 'color:var(--ember);margin-top:8px' }, 'Ingresso aperto'),
        el('div', { class: 'plain', style: 'margin-top:8px' }, E.testo));
      return;
    }
    const inp = el('input', { type: 'text', placeholder: 'la parola decifrata', autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
    const fb = el('p', { class: 'hint' }, '');
    const prova = () => {
      const w = Cifrari.normParola(inp.value);
      if (!w) { fb.className = 'err'; fb.textContent = '⚠ Scrivi la parola decifrata: la legge il Traduttore dal suo reperto.'; inp.focus(); return; }
      if (Cifrari.impronta(w) === E.parola_hash) {
        S.enigmi.push(E.id); save();
        if (VOCI.has(E.parola_hash)) apriParola(E.parola_hash, w);
        disegna(); return;
      }
      const costo = spendi('porta', E.nome + ' · «' + w + '»');
      fb.className = 'err'; fb.textContent = '⚠ «' + w + '» non apre questo ingresso. ' + rigaCosto(costo);
      inp.value = '';
    };
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') prova(); });
    box.append(el('label', { class: 'fld', style: 'margin-top:10px' }, el('span', { class: 'lbl' }, 'Parola'), inp),
      el('button', { class: 'big', type: 'button', style: 'margin-top:12px', onclick: prova }, 'Apri'), fb);
  };
  disegna();
  return box;
}

/* ---------------- le porte di pietra: griglie ----------------
   Le griglie stanno fra i due marcatori qui sotto, in JSON puro: verifica_griglie.py
   le legge da qui e le verifica per forza bruta (una soluzione esiste, non e' banale,
   le strategie ovvie falliscono). Non cambiarne una senza rilanciare la verifica.
   "porta": true  e' la griglia che una STANZA usa quando non ne sceglie una con  griglia:
   "insegna": true  e' un pannello d'insegnamento: facile di proposito. */
const PZ = /*<griglie>*/{
  "SEP-1": {"tipo":"separazione", "insegna":true, "rows":4, "cols":4, "start":[3, 0], "end":[0, 3], "dots":[], "squares":[{"r":0, "c":0, "k":"a"}, {"r":2, "c":0, "k":"a"}, {"r":0, "c":2, "k":"b"}, {"r":2, "c":2, "k":"b"}]},
  "SEP-2": {"tipo":"separazione", "insegna":true, "rows":5, "cols":5, "start":[4, 0], "end":[2, 4], "dots":[[2, 2], [1, 3]], "squares":[{"r":0, "c":0, "k":"a"}, {"r":1, "c":1, "k":"a"}, {"r":2, "c":0, "k":"a"}, {"r":3, "c":1, "k":"a"}, {"r":0, "c":2, "k":"b"}, {"r":1, "c":3, "k":"b"}, {"r":2, "c":2, "k":"b"}, {"r":3, "c":3, "k":"b"}]},
  "SEP-3": {"tipo":"separazione", "porta":true, "rows":5, "cols":5, "start":[4, 2], "end":[0, 2], "dots":[[2, 0], [2, 4]], "squares":[{"r":0, "c":0, "k":"a"}, {"r":3, "c":1, "k":"a"}, {"r":1, "c":1, "k":"a"}, {"r":0, "c":3, "k":"b"}, {"r":3, "c":3, "k":"b"}, {"r":1, "c":2, "k":"b"}]},
  "SEP-4": {"tipo":"separazione", "rows":5, "cols":5, "start":[4, 2], "end":[0, 2], "dots":[[2, 0], [2, 4], [4, 0]], "squares":[{"r":0, "c":0, "k":"a"}, {"r":1, "c":1, "k":"a"}, {"r":3, "c":0, "k":"a"}, {"r":2, "c":1, "k":"a"}, {"r":0, "c":3, "k":"b"}, {"r":1, "c":2, "k":"b"}, {"r":3, "c":3, "k":"b"}, {"r":2, "c":3, "k":"b"}]},
  "BOR-1": {"tipo":"bordi", "rows":4, "cols":4, "start":[3, 0], "end":[0, 3], "numeri":[{"r":1, "c":0, "n":1}, {"r":2, "c":2, "n":2}, {"r":1, "c":2, "n":1}, {"r":0, "c":2, "n":1}, {"r":2, "c":0, "n":3}]},
  "BOR-2": {"tipo":"bordi", "porta":true, "rows":5, "cols":5, "start":[4, 0], "end":[0, 4], "numeri":[{"r":0, "c":2, "n":3}, {"r":0, "c":3, "n":2}, {"r":1, "c":3, "n":1}, {"r":2, "c":0, "n":1}, {"r":1, "c":0, "n":1}, {"r":0, "c":0, "n":2}, {"r":3, "c":3, "n":3}, {"r":3, "c":2, "n":1}, {"r":1, "c":2, "n":3}]},
  "BOR-3": {"tipo":"bordi", "rows":5, "cols":5, "start":[4, 2], "end":[0, 2], "numeri":[{"r":3, "c":0, "n":2}, {"r":2, "c":3, "n":3}, {"r":0, "c":1, "n":1}, {"r":1, "c":1, "n":2}, {"r":2, "c":0, "n":3}]},
  "SIM-1": {"tipo":"simmetria", "rows":4, "cols":6, "start":[3, 0], "end":[0, 2], "dots":[{"r":1, "c":2, "k":"a"}, {"r":0, "c":4, "k":"b"}, {"r":2, "c":0, "k":"a"}, {"r":3, "c":2, "k":"a"}], "tagli":[[[0, 0], [1, 0]]]},
  "SIM-2": {"tipo":"simmetria", "porta":true, "rows":5, "cols":6, "start":[4, 0], "end":[0, 2], "dots":[{"r":0, "c":5, "k":"b"}, {"r":1, "c":3, "k":"b"}, {"r":3, "c":2, "k":"a"}], "tagli":[[[3, 2], [4, 2]], [[1, 3], [1, 4]]]},
  "SIM-3": {"tipo":"simmetria", "rows":5, "cols":8, "start":[4, 0], "end":[0, 3], "dots":[{"r":0, "c":0, "k":"a"}, {"r":4, "c":4, "k":"b"}, {"r":1, "c":3, "k":"a"}, {"r":2, "c":7, "k":"b"}, {"r":0, "c":2, "k":"a"}, {"r":1, "c":6, "k":"b"}], "tagli":[[[1, 4], [2, 4]], [[2, 4], [3, 4]]]}
}/*</griglie>*/;

/* le regole: le stesse di verifica_griglie.py, che le prova per forza bruta */
const key = n => n[0] + ',' + n[1];
const stesso = (a, b) => a[0] === b[0] && a[1] === b[1];
const lato = (a, b) => { const x = key(a), y = key(b); return x < y ? x + '|' + y : y + '|' + x; };
function lati(path) { const E = new Set();
  for (let i = 0; i < path.length - 1; i++) E.add(lato(path[i], path[i + 1]));
  return E; }
const specchio = (P, n) => [n[0], P.cols - 1 - n[1]];
const tagliDi = P => new Set((P.tagli || []).map(([a, b]) => lato(a, b)));
/** Le regole comuni: dall'ingresso all'uscita, passi adiacenti, mai due volte lo
    stesso nodo, mai attraverso un taglio; nella simmetria l'ombra non tocca la linea. */
function formaValida(P, path) {
  if (path.length < 2) return false;
  if (!stesso(path[0], P.start) || !stesso(path[path.length - 1], P.end)) return false;
  const visti = new Set(path.map(key));
  if (visti.size !== path.length) return false;
  if (path.some(n => n[0] < 0 || n[0] >= P.rows || n[1] < 0 || n[1] >= P.cols)) return false;
  for (let i = 0; i < path.length - 1; i++)
    if (Math.abs(path[i][0] - path[i + 1][0]) + Math.abs(path[i][1] - path[i + 1][1]) !== 1) return false;
  const T = tagliDi(P);
  for (const l of lati(path)) if (T.has(l)) return false;
  if (P.tipo === 'simmetria') {
    const M = path.map(n => specchio(P, n));
    if (M.some(n => visti.has(key(n)))) return false;
    for (const l of lati(M)) if (T.has(l)) return false;
  }
  return true;
}
function separati(P, path) {
  if (!(P.dots || []).every(d => path.some(n => n[0] === d[0] && n[1] === d[1]))) return false;
  const E = lati(path), R = P.rows - 1, C = P.cols - 1, has = (a, b) => E.has(lato(a, b));
  const vis = new Set(), q = {};
  (P.squares || []).forEach(s => q[s.r + ',' + s.c] = s.k);
  for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
    if (vis.has(r + ',' + c)) continue;
    const pila = [[r, c]], col = new Set(); vis.add(r + ',' + c);
    while (pila.length) { const [cr, cc] = pila.pop();
      if (q[cr + ',' + cc]) col.add(q[cr + ',' + cc]);
      const push = (nr, nc) => { if (nr >= 0 && nr < R && nc >= 0 && nc < C && !vis.has(nr + ',' + nc)) { vis.add(nr + ',' + nc); pila.push([nr, nc]); } };
      if (cc + 1 < C && !has([cr, cc+1], [cr+1, cc+1])) push(cr, cc+1);
      if (cc - 1 >= 0 && !has([cr, cc], [cr+1, cc])) push(cr, cc-1);
      if (cr + 1 < R && !has([cr+1, cc], [cr+1, cc+1])) push(cr+1, cc);
      if (cr - 1 >= 0 && !has([cr, cc], [cr, cc+1])) push(cr-1, cc);
    }
    if (col.size > 1) return false;
  }
  return true;
}
const latiCella = (r, c) => [lato([r, c], [r, c + 1]), lato([r + 1, c], [r + 1, c + 1]), lato([r, c], [r + 1, c]), lato([r, c + 1], [r + 1, c + 1])];
function bordiGiusti(P, path) {
  const E = lati(path);
  return (P.numeri || []).every(x => latiCella(x.r, x.c).filter(l => E.has(l)).length === x.n);
}
function puntiSpeculari(P, path) {
  const mia = new Set(path.map(key)), ombra = new Set(path.map(n => key(specchio(P, n))));
  return (P.dots || []).every(d => { const k = key([d.r, d.c]);
    return d.k === 'a' ? mia.has(k) : d.k === 'b' ? ombra.has(k) : d.k === 'n' ? mia.has(k) || ombra.has(k) : true; });
}
function risolto(P, path) {
  if (!formaValida(P, path)) return false;
  if (P.tipo === 'separazione') return separati(P, path);
  if (P.tipo === 'bordi') return bordiGiusti(P, path);
  if (P.tipo === 'simmetria') return puntiSpeculari(P, path);
  return false;
}

const PZ_U = 62, PZ_PAD = 34, NS = 'http://www.w3.org/2000/svg';
function disegnaPuzzle(P, path, svg) {
  const U = PZ_U, PAD = PZ_PAD, W = (P.cols - 1) * U + PAD * 2, H = (P.rows - 1) * U + PAD * 2;
  const X = c => PAD + c * U, Y = r => PAD + r * U;
  const mk = (t, a) => { const n = document.createElementNS(NS, t);
    for (const k in a) n.setAttribute(k, a[k]); return n; };
  const esagono = (n, colore) => mk('polygon', { points: [[0,-8],[7,-4],[7,4],[0,8],[-7,4],[-7,-4]].map(p => (X(n[1]) + p[0]) + ',' + (Y(n[0]) + p[1])).join(' '), fill: colore });
  clear(svg); svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const T = tagliDi(P), simm = P.tipo === 'simmetria';
  if (simm) svg.append(mk('line', { x1: (X(0) + X(P.cols - 1)) / 2, y1: 6, x2: (X(0) + X(P.cols - 1)) / 2, y2: H - 6,
    stroke: '#5F6B7D', 'stroke-width': 2, 'stroke-dasharray': '3 7' }));
  (P.squares || []).forEach(s => svg.append(mk('rect', { x: X(s.c) + 16, y: Y(s.r) + 16, width: U - 32, height: U - 32, rx: 5,
    fill: s.k === 'a' ? '#DFE5EF' : '#0A0D13', stroke: s.k === 'a' ? '#DFE5EF' : '#8B96A8', 'stroke-width': 2 })));
  const binario = (a, b) => {
    const x1 = X(a[1]), y1 = Y(a[0]), x2 = X(b[1]), y2 = Y(b[0]), st = { stroke: '#242C3A', 'stroke-width': 9, 'stroke-linecap': 'round' };
    if (!T.has(lato(a, b))) { svg.append(mk('line', Object.assign({ x1, y1, x2, y2 }, st))); return; }
    // un taglio: due monconi con un vuoto in mezzo
    svg.append(mk('line', Object.assign({ x1, y1, x2: x1 + (x2 - x1) * .3, y2: y1 + (y2 - y1) * .3 }, st)));
    svg.append(mk('line', Object.assign({ x1: x1 + (x2 - x1) * .7, y1: y1 + (y2 - y1) * .7, x2, y2 }, st)));
  };
  for (let r = 0; r < P.rows; r++) for (let c = 0; c < P.cols; c++) {
    if (c + 1 < P.cols) binario([r, c], [r, c + 1]);
    if (r + 1 < P.rows) binario([r, c], [r + 1, c]);
  }
  (P.numeri || []).forEach(x => {
    const cx = X(x.c) + U / 2, cy = Y(x.r) + U / 2;
    for (let i = 0; i < x.n; i++) { const ox = cx + (i - (x.n - 1) / 2) * 14;
      svg.append(mk('polygon', { points: `${ox},${cy - 6} ${ox + 6},${cy + 5} ${ox - 6},${cy + 5}`, fill: '#D9C26A', class: 'tri' })); }
  });
  const linea = (nodi, colore) => { if (nodi.length > 1) svg.append(mk('polyline', { points: nodi.map(n => X(n[1]) + ',' + Y(n[0])).join(' '),
    fill: 'none', stroke: colore, 'stroke-width': 11, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })); };
  linea(path, '#F08A4B');
  const ombra = simm ? path.map(n => specchio(P, n)) : [];
  if (simm) linea(ombra, '#79B2D0');
  svg.append(mk('circle', { cx: X(P.start[1]), cy: Y(P.start[0]), r: 13, fill: path.length ? '#F08A4B' : '#5F6B7D' }));
  svg.append(mk('circle', { cx: X(P.end[1]), cy: Y(P.end[0]), r: 9, fill: 'none', stroke: '#F08A4B', 'stroke-width': 4 }));
  if (simm) {
    const s2 = specchio(P, P.start), e2 = specchio(P, P.end);
    svg.append(mk('circle', { cx: X(s2[1]), cy: Y(s2[0]), r: 13, fill: path.length ? '#79B2D0' : '#5F6B7D' }));
    svg.append(mk('circle', { cx: X(e2[1]), cy: Y(e2[0]), r: 9, fill: 'none', stroke: '#79B2D0', 'stroke-width': 4 }));
  }
  (P.dots || []).forEach(d => {
    if (Array.isArray(d)) svg.append(esagono(d, path.some(n => stesso(n, d)) ? '#F08A4B' : '#79B2D0'));
    else svg.append(esagono([d.r, d.c], d.k === 'a' ? '#F08A4B' : d.k === 'b' ? '#79B2D0' : '#DFE5EF'));
  });
  for (let r = 0; r < P.rows; r++) for (let c = 0; c < P.cols; c++) {
    const hit = mk('circle', { cx: X(c), cy: Y(r), r: 22, fill: 'transparent' });
    hit.dataset.n = r + ',' + c; svg.append(hit);
  }
}

const SPIEGA = {
  separazione: 'Le forme chiare e quelle scure non restano dalla stessa parte della linea. La linea passa per ogni esagono.',
  bordi: 'Ogni triangolo in una casella è un lato di quella casella che la linea percorre: né uno di più, né uno di meno.',
  simmetria: 'La linea ha un’ombra speculare che si muove con lei, e le due non si toccano. I punti caldi sono della linea, i freddi dell’ombra. Dove il binario è tagliato non passa nessuna delle due.',
};

function porta(st) {
  titolo('Apritore', st.nome);
  back.classList.remove('hide');
  const P = PZ[st.griglia];
  const indietro = el('button', { class: 'big ghost', type: 'button', onclick: () => go('stanze') }, 'Indietro');
  if (!P) {
    app.append(el('div', { class: 'card bad' },
      el('div', { class: 'eyebrow', style: 'color:var(--bad)' }, 'Griglia mancante'),
      el('p', {}, 'La porta «' + st.nome + '» chiede la griglia «' + st.griglia + '», che in questa app non c’è.'),
      el('p', { class: 'hint' }, 'Chi rimedia: Alessandro, in app.js (PZ), poi python verifica_griglie.py. Intanto il narratore può considerarla aperta.')), indietro);
    return;
  }
  let path = [], traccia = null;
  const svg = document.createElementNS(NS, 'svg');
  svg.id = 'pz'; svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'griglia della porta ' + st.nome);
  const fb = el('p', { class: 'hint' }, 'Parti dal nodo pieno.');
  const dice = (cls, t) => { fb.className = cls; fb.textContent = t; };
  const esito = el('div', { class: 'card acc hide' },
    el('div', { class: 'eyebrow', style: 'color:var(--ember)' }, 'Porta aperta'),
    el('h3', { style: 'margin:6px 0 10px;font-size:19px' }, st.nome),
    el('div', { class: 'plain', style: 'color:var(--dim);font-size:15px' }, st.sblocca));
  const giaAperta = () => S.stanze.includes(st.id);

  const controlla = () => {
    const fine = path.length && stesso(path[path.length - 1], P.end);
    if (fine && risolto(P, path)) {
      if (!giaAperta()) { S.stanze.push(st.id); save(); }
      dice('ok', '✓ La pietra si muove.');
    } else if (fine) dice('err', '✕ La pietra non si muove: qualcosa non torna.');
    else if (!path.length) dice('hint', giaAperta() ? 'Questa porta è già aperta. Puoi ritracciarla quanto vuoi.' : 'Parti dal nodo pieno.');
    else dice('hint', path.length + ' nodi. L’uscita è il cerchio vuoto.');
    esito.classList.toggle('hide', !giaAperta());
  };
  const ridisegna = () => { disegnaPuzzle(P, path, svg); controlla(); };

  /** Perche' non si puo' andare in n, oppure null se si puo'. */
  const perche = n => {
    const u = path[path.length - 1];
    if (stesso(u, P.end)) return 'Sei all’uscita: da qui la linea non prosegue.';
    if (Math.abs(n[0] - u[0]) + Math.abs(n[1] - u[1]) !== 1 || path.some(x => stesso(x, n))) return 'Solo nodi vicini, e mai due volte lo stesso.';
    const T = tagliDi(P);
    if (T.has(lato(u, n))) return 'Lì il binario è tagliato.';
    if (P.tipo === 'simmetria') {
      const sn = specchio(P, n);
      if (stesso(sn, n) || path.some(x => stesso(x, sn))) return 'La linea e la sua ombra non possono toccarsi.';
      if (T.has(lato(specchio(P, u), sn))) return 'Il binario dell’ombra è tagliato.';
    }
    return null;
  };
  /** Allunga la linea verso n: un passo, o piu' passi in fila se n e' sulla stessa riga o colonna. */
  const allunga = n => {
    const u = path[path.length - 1];
    if (u[0] !== n[0] && u[1] !== n[1]) { const m = perche(n); if (m) { dice('err', m); return false; } path.push(n); return true; }
    let mosso = false;
    for (let guard = 0; guard < 20 && !stesso(path[path.length - 1], n); guard++) {
      const c = path[path.length - 1], p = [c[0] + Math.sign(n[0] - c[0]), c[1] + Math.sign(n[1] - c[1])];
      const m = perche(p);
      if (m) { dice('err', m); break; }
      path.push(p); mosso = true;
    }
    return mosso;
  };
  const nodoSotto = (e, raggio) => {
    const m = svg.getScreenCTM(); if (!m) return null;
    const q = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    const c = Math.round((q.x - PZ_PAD) / PZ_U), r = Math.round((q.y - PZ_PAD) / PZ_U);
    if (r < 0 || r >= P.rows || c < 0 || c >= P.cols) return null;
    return Math.hypot(q.x - (PZ_PAD + c * PZ_U), q.y - (PZ_PAD + r * PZ_U)) <= raggio * PZ_U ? [r, c] : null;
  };
  // Un dito solo, o il mouse: si traccia trascinando, oppure toccando un nodo alla volta.
  // Un tocco secco sull'ultimo nodo torna indietro di un passo; un tocco su un nodo gia'
  // percorso riporta la linea li'.
  svg.addEventListener('pointerdown', e => {
    const n = nodoSotto(e, 0.45); if (!n) return;
    e.preventDefault();
    traccia = { id: e.pointerId, mosso: false, giu: n };
    try { svg.setPointerCapture(e.pointerId); } catch (_) {}
    if (!path.length) {
      if (stesso(n, P.start)) { path = [n]; traccia.mosso = true; ridisegna(); }
      else { traccia = null; dice('err', '⚠ Parti dal nodo pieno.'); }
      return;
    }
    const i = path.findIndex(x => stesso(x, n));
    if (i === path.length - 1) return;
    if (i >= 0) { path = path.slice(0, i + 1); traccia.mosso = true; ridisegna(); return; }
    if (allunga(n)) { traccia.mosso = true; disegnaPuzzle(P, path, svg); if (stesso(path[path.length - 1], n)) controlla(); }
  });
  svg.addEventListener('pointermove', e => {
    if (!traccia || e.pointerId !== traccia.id || !path.length) return;
    const n = nodoSotto(e, 0.34); if (!n) return;
    const u = path[path.length - 1];
    if (stesso(n, u)) return;
    if (path.length > 1 && stesso(n, path[path.length - 2])) { path.pop(); traccia.mosso = true; ridisegna(); return; }
    if (allunga(n)) { traccia.mosso = true; disegnaPuzzle(P, path, svg); if (stesso(path[path.length - 1], n)) controlla(); }
  });
  const fineTraccia = (e, annullato) => {
    if (!traccia || e.pointerId !== traccia.id) return;
    const t = traccia; traccia = null;
    if (!annullato && !t.mosso && path.length && stesso(t.giu, path[path.length - 1])) {
      path.pop(); ridisegna();
    }
  };
  svg.addEventListener('pointerup', e => fineTraccia(e, false));
  svg.addEventListener('pointercancel', e => fineTraccia(e, true));

  app.append(el('p', { class: 'hint', style: 'margin:0 0 10px' }, SPIEGA[P.tipo] || ''),
    svg,
    el('p', { class: 'hint', style: 'margin:8px 0 0' }, 'Trascina il dito dal nodo pieno, oppure tocca un nodo alla volta. Tocca l’ultimo nodo per tornare indietro.'),
    el('div', { class: 'pzrow' },
      el('button', { class: 'big ghost', type: 'button', onclick: () => { path = []; ridisegna(); } }, 'Azzera'),
      indietro),
    fb, esito);
  ridisegna();
}

/* ---- MASTER · console di sistema ----
   I 30 minuti sono un BUDGET, non un cronometro: ogni azione costa 1d6+1. */
/* Le tre regole si leggono dai dati, non si scrivono qui: se cambiano in
   contenuti.md la console si aggiorna da sola invece di mentire. */
const REGOLE = () => (D.pianeti || [])
  .filter(p => p.id !== 'FIN' && p.meccanica)
  .map(p => p.meccanica);

/** I tre cifrari in sintesi, solo sulla console: serve al narratore per spiegare una
    regola o sbloccare il tavolo senza andare a cercare il foglio. Le descrizioni stanno
    in cifrari.js accanto alle regole stesse, cosi' non possono divergere.
    NON ci sono le frasi che i giocatori digitano: quelle si trovano scansionando i
    reperti propedeutici, ed e' il punto del gioco. Stanno sul foglio chiavi stampato. */
function pannelloCifrari() {
  const parti = [['alfabeto', 'Alfabeto', 'Traduttore'], ['ordine', 'Ordine', 'Apritore'],
                 ['chiave', 'Chiave', 'Custode']];
  const box = el('div', { class: 'card cold' },
    el('div', { class: 'eyebrow', style: 'color:var(--cold)' }, 'I tre cifrari, in breve'));
  const mondi = (D.pianeti || []).filter(p => Cifrari.CIFRARI[p.id]);
  if (!mondi.length) {
    box.append(el('p', { class: 'hint', style: 'margin:8px 0 0' },
      'Nei dati non c’è nessun mondo con un cifrario.'));
    return box;
  }
  mondi.forEach(p => {
    const c = Cifrari.CIFRARI[p.id], righe = el('div', { class: 'cif' });
    // l'esempio e' su parole inventate: si puo' mostrare senza regalare niente
    const esempio = x => x ? el('div', { class: 'cif-e' },
      el('span', { class: 'mono' }, x.da), ' → ', el('b', { class: 'mono' }, x.a),
      x.nota ? el('span', { class: 'cif-n' }, ' · ' + x.nota) : '') : '';
    parti.forEach(([k, lbl, chi]) => righe.append(
      el('div', { class: 'cif-r' },
        el('div', { class: 'cif-k' }, lbl, el('span', {}, ' · ' + chi)),
        el('div', { class: 'cif-v' }, (c.dice || {})[k] || '—', esempio((c.esempi || {})[k])))));
    box.append(el('div', { class: 'cif-m' },
      el('div', { class: 'cif-h' }, el('span', { class: 'cif-s' }, p.simbolo || '?'), p.nome),
      righe, esempio((c.esempi || {}).insieme)));
  });
  box.append(el('p', { class: 'hint', style: 'margin:12px 0 0' },
    'Le due frasi che i giocatori digitano non sono qui: le trovano scansionando i reperti ' +
    'propedeutici. Se ti servono, sono sul foglio chiavi stampato.'));
  return box;
}

/* ---------------- tutti i reperti, sulla sola console ----------------
   Niente si stampa: il reperto si mostra da qui. Il narratore lo legge con le note
   sotto; poi tocca «Mostra ai giocatori» e gira lo schermo: a quel punto si vede il
   reperto com'e' scritto davvero, in simboli, con il suo QR. Loro lo scansionano dal
   tuo schermo e sul loro telefono si apre leggibile - tranne le parole cifrate.
   Le parole in chiaro qui non ci sono e non ci devono essere: dati.js sta anche sui
   loro telefoni. Quelle stanno sul foglio chiavi e in master.html. */
const trascrivi = t => {
  const m = D.simboli || {};
  let s = '';
  for (const c of String(t)) {
    const b = c.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
    s += (b.length === 1 && m[b]) ? m[b] : c;
  }
  return s;
};

/** Il QR disegnato dalla matrice impacchettata: una rect per ogni tratto orizzontale. */
function disegnaQR(dati) {
  const p = String(dati || '').split(':'), n = parseInt(p[0], 10);
  if (!n || !p[1]) return null;
  const b = atob(p[1]), q = [];
  for (let i = 0; i < b.length; i++) { const v = b.charCodeAt(i);
    for (let k = 7; k >= 0; k--) q.push((v >> k) & 1); }
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 ' + n + ' ' + n);
  svg.setAttribute('fill', '#000');
  for (let y = 0; y < n; y++) {
    let x = 0;
    while (x < n) {
      if (!q[y * n + x]) { x++; continue; }
      const x0 = x;
      while (x < n && q[y * n + x]) x++;
      const r = document.createElementNS(NS, 'rect');
      r.setAttribute('x', x0); r.setAttribute('y', y);
      r.setAttribute('width', x - x0); r.setAttribute('height', 1);
      svg.appendChild(r);
    }
  }
  return svg;
}

/** Il reperto come lo vede il tavolo: tutto in simboli, le parole cifrate nel loro
    riquadro col simbolo del mondo che le ha scritte. */
function corpoInSimboli(t) {
  const box = el('div', { class: 'rep-sim' });
  (t.corpo || []).forEach(z => {
    if (z.t === 'c') { box.append(trascrivi(z.v)); return; }
    const v = PAROLE.get(z.w);
    box.append(el('b', { class: 'rep-w' }, simboloDi(v && v.mondo), trascrivi(z.c)));
  });
  return box;
}

function pannelloReperti() {
  const box = el('div', { class: 'card' }, el('div', { class: 'eyebrow' }, 'Tutti i reperti'));
  const cerca = el('input', { type: 'text', placeholder: 'sigillo, titolo, codice…', autocapitalize: 'none', autocomplete: 'off', spellcheck: 'false' });
  const lista = el('div', { class: 'rep-l' });
  const scena = el('div', { class: 'rep-scena hide' });

  const mostraAiGiocatori = t => {
    clear(scena);
    const qr = disegnaQR((D.qr || {})[t.id]);
    scena.append(
      el('button', { class: 'rep-x', type: 'button', onclick: () => scena.classList.add('hide') }, 'chiudi'),
      el('div', { class: 'rep-in' },
        corpoInSimboli(t),
        el('div', { class: 'rep-qr' }, qr || el('p', { class: 'err' }, 'QR non disponibile: manca il modulo qrcode in costruzione.')),
        el('div', { class: 'rep-cod mono' }, t.codice)));
    scena.classList.remove('hide');
    scena.scrollTop = 0;
  };

  const apri = t => {
    clear(dettaglio);
    const parole = (t.corpo || []).filter(z => z.t === 'p');
    const note = el('div', { class: 'rep-note' },
      el('div', { class: 'eyebrow' }, 'Note'),
      el('p', { class: 'hint', style: 'margin:6px 0 0' },
        nomePianeta(t.pianeta) + ' · numero del sigillo ' + (String(t.id).match(/(\d+)$/) || [, '—'])[1] +
        ' · codice ' + t.codice + ' · ' + t.tipo +
        (t.rivela && t.rivela.length ? ' · rivela ' + t.rivela.join(', ') : '')));
    if (parole.length) {
      const tab = el('div', { class: 'rep-t' });
      parole.forEach(z => { const v = PAROLE.get(z.w);
        tab.append(el('div', { class: 'rep-r' },
          el('span', { class: 'rep-s' }, simboloDi(v && v.mondo)),
          el('span', { class: 'mono' }, z.c),
          el('span', { class: 'rep-k mono' }, z.k || '—'),
          el('span', { class: 'rep-c' }, z.come || '')));
      });
      note.append(tab, el('p', { class: 'hint', style: 'margin:8px 0 0' },
        'La parola in chiaro non è qui, di proposito: questi dati stanno anche sui telefoni dei giocatori. È sul foglio chiavi.'));
    } else {
      note.append(el('p', { class: 'hint', style: 'margin:6px 0 0' }, 'Nessuna parola cifrata: si legge e basta.'));
    }
    dettaglio.append(
      el('div', { class: 'eyebrow', style: 'margin-top:4px' }, t.id + ' · ' + t.titolo),
      el('div', { class: 'rep-chiaro' }, ...(t.corpo || []).map(z => z.t === 'c'
        ? z.v : el('b', { class: 'rep-w' }, simboloDi((PAROLE.get(z.w) || {}).mondo), z.c))),
      el('button', { class: 'big', type: 'button', style: 'margin-top:12px', onclick: () => mostraAiGiocatori(t) },
        'Mostra ai giocatori'),
      note);
    if (dettaglio.scrollIntoView) dettaglio.scrollIntoView({ block: 'nearest' });
  };

  const dettaglio = el('div');
  const disegna = () => {
    clear(lista);
    const q = cerca.value.trim().toLowerCase();
    const suoi = (D.testi || []).filter(t => !q ||
      (t.id + ' ' + t.titolo + ' ' + t.codice + ' ' + nomePianeta(t.pianeta)).toLowerCase().includes(q));
    if (!suoi.length) { lista.append(el('p', { class: 'hint' }, 'Nessun reperto per «' + cerca.value.trim() + '».')); return; }
    suoi.forEach(t => lista.append(el('button', { class: 'rep-b', type: 'button', onclick: () => apri(t) },
      el('b', { class: 'mono' }, t.codice), el('s', {}, t.id + ' · ' + t.titolo))));
  };
  cerca.addEventListener('input', disegna);
  disegna();
  box.append(el('label', { class: 'fld', style: 'margin-top:10px' }, el('span', { class: 'lbl' }, 'Cerca'), cerca),
    lista, dettaglio, scena);
  return box;
}

/** Parole aperte: quali parole ha gia' il tavolo, perche' il narratore possa fare da
    rete di sicurezza. Mostra questo dispositivo, e un telefono dei giocatori se il
    narratore ne scrive il codice di stato. Le parole in chiaro sono sul foglio chiavi. */
function pannelloParole() {
  const lista = el('div'), fb = el('p', { class: 'hint', style: 'margin:8px 0 0' });
  let dalCodice = null;
  const inp = el('input', { type: 'text', placeholder: 'codice di un telefono', autocapitalize: 'characters', autocomplete: 'off', spellcheck: 'false' });
  const disegna = () => {
    clear(lista);
    if (!DATI_OK) { lista.append(el('p', { class: 'err' }, 'dati.js è nel formato vecchio: niente parole da mostrare.')); return; }
    if (!UNICHE.length) { lista.append(el('p', { class: 'hint' }, 'Nei dati non ci sono parole cifrate.')); return; }
    const qui = UNICHE.filter(h => S.parole[h]).length;
    lista.append(el('div', { class: 'eyebrow', style: 'margin:14px 0 6px' },
      'Qui ' + qui + ' / ' + UNICHE.length + (dalCodice ? ' · dal codice ' + dalCodice.size + ' / ' + UNICHE.length : '')));
    UNICHE.forEach(h => {
      const voci = VOCI.get(h), ids = new Set(voci.map(v => v.id)), dove = [];
      D.testi.forEach(t => (t.corpo || []).forEach(s => { if (s.t === 'p' && ids.has(s.w)) dove.push(t.id + ' ' + s.c); }));
      const apre = [];
      voci.forEach(v => { if (v.apre_log) apre.push(v.apre_log);
        if (v.apre_enigma) apre.push('luogo: ' + ((ENIGMI.get(v.apre_enigma) || {}).nome || v.apre_enigma)); });
      const chiaro = S.parole[h], tel = dalCodice && dalCodice.has(h);
      lista.append(el('div', { class: 'pa-r' + (chiaro || tel ? ' on' : '') },
        el('span', { class: 'pa-id mono' }, simboloDi(voci[0].mondo) + ' ' + voci.map(v => v.id).join(' · ')),
        el('span', { class: 'pa-dove' }, (chiaro ? '«' + chiaro + '» · ' : '') + (dove.join(', ') || 'in nessun reperto') + (apre.length ? ' → ' + apre.join(', ') : '')),
        el('span', { class: 'pa-st mono' }, chiaro && tel ? 'qui+tel' : chiaro ? 'qui' : tel ? 'tel' : '—')));
    });
  };
  const leggi = () => {
    const r = leggiCodiceStato(inp.value);
    if (r.errore) { fb.className = 'err'; fb.textContent = '⚠ ' + r.errore; return; }
    dalCodice = r.aperte; fb.className = 'ok';
    fb.textContent = '✓ Codice letto: su quel telefono ' + r.aperte.size + (r.aperte.size === 1 ? ' parola aperta.' : ' parole aperte.');
    disegna();
  };
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') leggi(); });
  disegna();
  return el('div', { class: 'card', id: 'parole-aperte' },
    el('div', { class: 'eyebrow' }, 'Parole aperte'),
    el('p', { class: 'hint', style: 'margin:8px 0 10px' }, 'Quelle aperte su questo dispositivo e, se scrivi qui il codice che compare in fondo alla schermata di un giocatore, quelle del suo telefono. Le parole in chiaro sono sul foglio chiavi stampato, alla stessa sigla.'),
    inp, el('button', { class: 'big ghost', type: 'button', style: 'margin-top:10px', onclick: leggi }, 'Leggi codice'),
    fb, lista);
}

V.master = () => {
  titolo('Console di Sistema', 'Solo per il narratore');
  let M = { min: 30, loop: 1, storia: [] };
  try { Object.assign(M, JSON.parse(localStorage.getItem('emberloop.master') || '{}')); } catch (e) {}
  const salvaM = () => { try { localStorage.setItem('emberloop.master', JSON.stringify(M)); } catch (e) {} };

  const clock = el('div', { class: 'clock mono' });
  const sotto = el('div', { class: 'eyebrow', style: 'text-align:center;margin-bottom:4px' });
  const roll = el('div', { class: 'roll' }, ' ');
  const stato = el('div', { style: 'margin-top:6px' });

  const dipingi = () => {
    clock.textContent = M.min + "'";
    clock.className = 'clock mono' + (M.min <= 5 ? ' crit' : M.min <= 12 ? ' warn' : '');
    sotto.textContent = 'Loop ' + M.loop + ' · minuti rimasti nel loop';
    clear(stato);
    REGOLE().forEach(m =>
      stato.append(el('span', { class: 'chip' + (S.mecc.includes(m) ? ' on' : '') }, m)));
    stato.append(el('div', { class: 'hint', style: 'margin-top:8px' },
      S.mecc.length === 3 ? '▸ Tre meccaniche acquisite: possono restare oltre la luce. Sblocca Il Cuore del Sistema.'
                          : '▸ ' + S.mecc.length + '/3 meccaniche. Servono tutte e tre per vedere l’accensione.'));
    salvaM();
  };
  const scala = etichetta => {
    const d = 1 + Math.floor(Math.random() * 6), costo = d + 1;
    M.storia.push(costo);
    M.min = Math.max(0, M.min - costo);
    roll.textContent = etichetta + ' → 1d6+1 = ' + d + '+1 = ' + costo + ' min';
    if (M.min === 0) roll.textContent += '  ·  LUCE BIANCA';
    dipingi();
  };
  const B = (t, lbl) => el('button', { class: 'big ghost', type: 'button', onclick: () => scala(lbl) }, t);

  if (STATO_VECCHIO) app.append(el('p', { class: 'hint', style: 'margin:0 0 12px' },
    'Su questo dispositivo c’era lo stato di una versione precedente dell’app: è stato ignorato.'));
  app.append(el('div', { class: 'card' }, clock, sotto, roll,
      el('div', { class: 'grid2', style: 'margin-top:14px' },
        B('Spostamento', 'Spostamento'), B('Traduzione', 'Traduzione'),
        B('Archivio', 'Consultazione'), B('Enigma', 'Enigma')),
      el('div', { class: 'grid2', style: 'margin-top:10px' },
        el('button', { class: 'big ghost', type: 'button', onclick: () => {
            const u = M.storia.pop(); if (u) { M.min = Math.min(30, M.min + u); roll.textContent = 'annullato −' + u + ' min'; dipingi(); } } }, 'Annulla'),
        el('button', { class: 'big', type: 'button', onclick: () => {
            M.loop++; M.min = 30; M.storia = [];
            roll.textContent = 'Nuovo loop. Il mondo torna indietro.'; dipingi(); } }, 'Nuovo loop'))),
    el('div', { class: 'card cold' },
      el('div', { class: 'eyebrow', style: 'color:var(--cold)' }, 'Stato dei rilevatori su questo dispositivo'), stato),
    pannelloCifrari(),
    pannelloReperti(),
    pannelloParole(),
    el('div', { class: 'card' },
      el('div', { class: 'eyebrow' }, 'Costo riportato da un giocatore'),
      el('p', { class: 'hint', style: 'margin:8px 0 10px' },
        'Le app dei ruoli tirano da sole e dicono quanto e’ costato. Scala qui il numero che ti riferiscono.'),
      (() => {
        const n = el('input', { type: 'text', inputmode: 'numeric', placeholder: 'minuti', style: 'text-align:center' });
        const go = () => { const v = parseInt(n.value, 10);
          if (!v || v < 1) { roll.textContent = 'scrivi un numero di minuti (es. 3)'; n.focus(); return; }
          M.storia.push(v); M.min = Math.max(0, M.min - v);
          roll.textContent = 'riportato dal tavolo −' + v + ' min'; n.value = ''; dipingi(); };
        n.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
        const w = el('div');
        w.append(n, el('button', { class: 'big ghost', type: 'button', style: 'margin-top:10px', onclick: go }, 'Scala'));
        return w;
      })()),
    el('div', { class: 'card' },
      el('div', { class: 'eyebrow' }, 'Storico del loop'),
      (() => {
        const box = el('div', { style: 'margin-top:10px' });
        const dis = () => { clear(box);
          const st = (S.storico || []).slice(-12).reverse();
          if (!st.length) { box.append(el('p', { class: 'hint', style: 'margin:0' },
            'Nessuna azione registrata su questo dispositivo. Ogni app tiene il proprio storico.')); return; }
          st.forEach(a => box.append(el('div', { style: 'display:flex;gap:10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px' },
            el('span', { class: 'mono', style: 'color:var(--faint);flex:0 0 42px' }, a.q),
            el('span', { style: 'flex:1;color:var(--dim)' }, a.c),
            el('span', { class: 'mono', style: 'color:var(--ember)' }, '−' + a.m))));
        };
        dis(); return box;
      })()),
    el('div', { class: 'card' },
      el('div', { class: 'eyebrow' }, 'Failsafe del narratore'),
      el('p', { class: 'hint', style: 'margin:8px 0 0' },
        'Se il gruppo si blocca, il tuo compito è far avanzare la trama: leggi tu la parola dal foglio chiavi e considerala aperta. Le chiavi non sono in questa app di proposito — sono su CHIAVI-MASTER, stampato.'),
      el('button', { class: 'big ghost', type: 'button', style: 'margin-top:14px', onclick: () => {
          if (confirm('Azzerare tutti i progressi su QUESTO dispositivo?')) {
            S = vuoto(); save();
            M = { min: 30, loop: 1, storia: [] }; salvaM(); go('master'); } } }, 'Azzera dispositivo')));
  dipingi();
};

/* ---------------- router ---------------- */
function go(v) {
  Cam.stop(document.getElementById('cam'));
  (V[v] || V.ruoli)();
  if (v && v !== 'ruoli') back.classList.remove('hide');
  window.scrollTo(0, 0);
  try { location.hash = v === 'ruoli' ? '' : v; } catch (e) {}
}
back.addEventListener('click', () => go('ruoli'));
window.addEventListener('hashchange', () => go(location.hash.slice(1) || 'ruoli'));
go(location.hash.slice(1) || 'ruoli');
