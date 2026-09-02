/* The Ember Loop — terminale di rilevamento
   Nessuna chiave di cifratura è presente in questo file né in dati.js. */
'use strict';
const D = window.DATI, app = document.getElementById('app'),
      back = document.getElementById('back'), vt = document.getElementById('vt'), vs = document.getElementById('vs');
const el = (t, a = {}, ...kids) => { const n = document.createElement(t);
  for (const k in a) k === 'html' ? n.innerHTML = a[k] : k.startsWith('on') ? n.addEventListener(k.slice(2), a[k]) : n.setAttribute(k, a[k]);
  kids.flat().forEach(c => n.append(c && c.nodeType ? c : document.createTextNode(c))); return n; };
const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); };

/* ---------------- stato locale (per dispositivo) ---------------- */
const SK = 'emberloop.v1';
let S = { testi: [], log: [], stanze: [], mecc: [], plain: {}, storico: [] };
try { Object.assign(S, JSON.parse(localStorage.getItem(SK) || '{}')); } catch (e) {}
const save = () => { try { localStorage.setItem(SK, JSON.stringify(S)); } catch (e) {} };
const add = (k, v) => { if (!S[k].includes(v)) { S[k].push(v); save(); } };
/** Registra un'azione nello storico locale, con il suo costo in minuti. */
function segna(tipo, cosa, minuti) {
  S.storico = S.storico || [];
  S.storico.push({ t: tipo, c: cosa, m: minuti, q: new Date().toISOString().slice(11, 16) });
  save();
}

/* ---------------- decifratura ---------------- */
const MARCA = '\u25c6KINDLER\u00b7ARCHIVIO\u00b7v1\u25c6\n';
function decifra(b64, chiave) {
  const raw = atob(b64), k = new TextEncoder().encode(chiave.toUpperCase());
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i) ^ k[i % k.length];
  const t = new TextDecoder('utf-8', { fatal: true }).decode(out); // chiave errata -> lancia
  if (!t.startsWith(MARCA)) throw new Error('marcatore assente'); // chiave errata ma UTF-8 valido
  return t.slice(MARCA.length);
}
const prova = (b64, k) => { try { return decifra(b64, k); } catch (e) { return null; } };

/* ---------------- Cesare + riconoscimento italiano ---------------- */
const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
function cesare(t, sc) {
  let o = '';
  for (const ch of t) { const u = ch.toUpperCase(); const i = AZ.indexOf(u);
    if (i < 0) { o += ch; continue; }
    const n = AZ[(i + sc % 26 + 26) % 26]; o += (ch === u ? n : n.toLowerCase()); }
  return o;
}
const COMUNI = [' di ',' che ',' la ',' il ',' e ',' non ',' per ',' una ',' del ',' con ',
                ' si ',' in ',' un ',' le ',' ci ',' era ',' come ',' della ',' nel ',' piu'];
function punteggioItaliano(t) {
  const s = ' ' + t.toLowerCase() + ' '; let n = 0;
  for (const w of COMUNI) { let i = 0; while ((i = s.indexOf(w, i)) >= 0) { n++; i++; } }
  return n;
}
/** Prova tutti i 25 scorrimenti e tiene quello che somiglia di piu' all'italiano. */
function craccaCesare(testoCifrato) {
  let best = null, bestSc = 0, bestP = -1;
  for (let sc = 1; sc <= 25; sc++) {
    const p = cesare(testoCifrato, -sc), q = punteggioItaliano(p);
    if (q > bestP) { bestP = q; best = p; bestSc = sc; }
  }
  return { testo: best, scorrimento: bestSc, punteggio: bestP };
}

/* ---------------- costi in minuti ---------------- */
const COSTO = { crack: 1, consulta: 1, tentativo: null };  // null = tira 1d4+1
const d4p1 = () => 1 + Math.floor(Math.random() * 4) + 1;

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
      this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    } catch (e) { return false; }
    v.srcObject = this.stream; v.setAttribute('playsinline', ''); v.muted = true; await v.play();
    box.style.display = 'block';
    const tick = () => {
      if (v.readyState === v.HAVE_ENOUGH_DATA) {
        const w = Math.min(520, v.videoWidth); const sc = w / v.videoWidth;
        cv.width = w; cv.height = v.videoHeight * sc;
        cx.drawImage(v, 0, 0, cv.width, cv.height);
        const d = cx.getImageData(0, 0, cv.width, cv.height);
        const r = window.jsQR && jsQR(d.data, d.width, d.height, { inversionAttempts: 'dontInvert' });
        if (r && r.data) { this.stop(box); onCode(r.data.trim().toUpperCase()); return; }
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
      if (Cam.stream) { Cam.stop(box); b.textContent = '⌘  Scansiona sigillo'; return; }
      b.textContent = 'Avvio fotocamera…';
      const ok = await Cam.start(box, c => { b.textContent = '⌘  Scansiona sigillo'; onCode(c); });
      b.textContent = ok ? '✕  Chiudi fotocamera' : 'Fotocamera non disponibile — usa il codice';
    } }, '⌘  Scansiona sigillo');
  return [b, box];
}

/* ---------------- viste ---------------- */
const V = {};

V.ruoli = () => {
  back.classList.add('hide'); vt.textContent = 'The Ember Loop'; vs.textContent = 'Terminale di rilevamento';
  const R = [
    ['01', 'decifra', 'Il Decifratore', 'Scansiona i sigilli Kindler e apri i testi cifrati. Serve la chiave giusta.'],
    ['02', 'log', 'Il Consultatore', 'Sblocca le voci del diario di bordo e tieni insieme gli indizi.'],
    ['03', 'stanze', "L'Apritore", 'Risolvi gli enigmi di percorso per aprire le stanze sulle mappe.']
  ];
  clear(app);
  app.append(el('p', { class: 'hint', style: 'margin:0 0 18px' },
    'Tre rilevatori, tre terminali. Ognuno apre ciò che gli altri non possono.'));
  const g = el('div', { class: 'roles' });
  R.forEach(([n, id, t, d]) => g.append(el('button', { class: 'role', type: 'button', onclick: () => go(id) },
    el('div', { class: 'n' }, 'Ruolo ' + n), el('h3', {}, t), el('p', {}, d))));
  g.append(el('button', { class: 'role gm', type: 'button', onclick: () => go('master') },
    el('div', { class: 'n' }, 'Master'), el('h3', {}, 'Console di Sistema'),
    el('p', {}, 'Cronometro del loop, costi in minuti, stato dei tre pianeti. Solo per il narratore.')));
  app.append(g);
};

/* ---- 01 · DECIFRATORE ---- */
V.decifra = () => {
  vt.textContent = 'Decifratore'; vs.textContent = 'Software di decifrazione testi';
  clear(app);
  const out = el('div');
  const codeIn = el('input', { type: 'text', placeholder: 'KNDL-01', autocapitalize: 'characters' });
  const apri = code => {
    const t = D.testi.find(x => x.sigillo.toUpperCase() === code);
    if (!t) { clear(out); out.append(el('p', { class: 'err' }, '⚠ Sigillo non riconosciuto: ' + code)); return; }
    mostraTesto(out, t);
  };
  const [scanBtn, camBox] = scanner(apri);
  app.append(scanBtn, camBox,
    el('div', { class: 'card' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Codice sigillo'), codeIn),
      el('button', { class: 'big ghost', type: 'button', style: 'margin-top:12px',
        onclick: () => apri(codeIn.value.trim().toUpperCase()) }, 'Apri reperto'),
      el('p', { class: 'hint' }, 'Se la fotocamera non parte, digita il codice stampato sotto il sigillo.')),
    out);
};

function mostraTesto(out, t) {
  clear(out);
  const pia = D.pianeti.find(p => p.id === t.pianeta);
  const box = el('div', { class: 'card' });
  box.append(el('div', { class: 'eyebrow' }, t.sigillo + ' · ' + (pia ? pia.sub : 'registrazione terminale')),
    el('h3', { style: 'margin:6px 0 12px;font-size:19px' }, t.titolo));

  if (S.plain[t.id]) { rivela(box, t); out.append(box); return; }

  if (t.tipo === 'comune') {
    /* ---- Cesare: il software lo rompe da solo ---- */
    box.append(el('div', { class: 'eyebrow', style: 'color:var(--cold);margin-bottom:8px' },
        'Cifratura semplice · a scorrimento'),
      el('div', { class: 'glyphs', style: 'letter-spacing:.05em;font-size:14px' }, t.cesare.slice(0, 420)));
    const esito = el('p', { class: 'hint' }, 'Il software prova tutti e 25 gli scorrimenti. Costa 1 minuto.');
    box.append(el('button', { class: 'big crack-go', type: 'button', style: 'margin-top:14px', onclick: () => {
        const r = craccaCesare(t.cesare);
        S.plain[t.id] = r.testo; add('testi', t.id); save();
        segna('crack', t.sigillo, COSTO.crack);
        rivela(box, t, true, r.scorrimento);
      } }, '⟳  Crack automatico  ·  1 min'), esito);
  } else {
    /* ---- Vigenère: serve la parola esatta ---- */
    box.append(el('div', { class: 'eyebrow', style: 'color:var(--ember);margin-bottom:8px' },
        'Cifratura a chiave · la forza bruta non basta'),
      el('div', { class: 'glyphs' }, glifi(t.sigillo, 120)));
    const kIn = el('input', { type: 'text', class: 'k-in', placeholder: 'parola chiave', autocapitalize: 'characters' });
    const fb = el('p', { class: 'hint' }, 'Ogni tentativo costa 1d4+1 minuti, giusto o sbagliato. Il Consultatore puo\u2019 farti risparmiare.');
    const tenta = () => {
      const k = kIn.value.trim(); if (!k) return;
      const costo = d4p1();
      const p = prova(t.cifra, k);
      segna('tentativo', t.sigillo + ' · ' + (p ? 'riuscito' : 'a vuoto'), costo);
      if (p) { S.plain[t.id] = p; add('testi', t.id); save(); rivela(box, t, true); }
      else { fb.className = 'err';
        fb.textContent = '⚠ La chiave non tiene. Persi ' + costo + ' minuti.'; kIn.value = ''; }
    };
    kIn.addEventListener('keydown', e => { if (e.key === 'Enter') tenta(); });
    box.append(el('label', { class: 'fld', style: 'margin-top:14px' },
        el('span', { class: 'lbl' }, 'Chiave di decifrazione'), kIn),
      el('button', { class: 'big k-go', type: 'button', style: 'margin-top:12px', onclick: tenta },
        'Decifra  ·  1d4+1 min'), fb);
  }
  out.append(box);
}

function rivela(box, t, anim, scorrimento) {
  clear(box);
  const pia = D.pianeti.find(p => p.id === t.pianeta);
  box.className = 'card acc';
  box.append(el('div', { class: 'eyebrow', style: 'color:var(--ember)' },
      t.sigillo + ' · decifrato' + (scorrimento ? ' · scorrimento ' + scorrimento : '')),
    el('h3', { style: 'margin:6px 0 12px;font-size:19px' }, t.titolo),
    el('div', { class: 'plain' + (anim ? ' rev' : '') }, S.plain[t.id] || ''));

  if (t.tipo === 'comune' && t.parole && t.parole.length) {
    const w = el('div', { class: 'card cold', style: 'margin:16px 0 0' },
      el('div', { class: 'eyebrow', style: 'color:var(--cold)' }, 'Parole da passare al Consultatore'),
      el('p', { style: 'margin:6px 0 10px;font-size:13.5px;color:var(--dim)' },
        'Leggile ad alta voce. Lui le digita nel diario di bordo per ottenere gli indizi.'));
    t.parole.forEach(p => w.append(el('span', { class: 'chip on', style: 'font-size:13px;padding:6px 12px' }, p)));
    box.append(w);
  }
  if (pia && t.tipo === 'chiave') {
    const nuova = !S.mecc.includes(pia.meccanica);
    if (nuova) add('mecc', pia.meccanica);
    box.append(el('div', { class: 'card cold', style: 'margin:16px 0 0' },
      el('div', { class: 'eyebrow', style: 'color:var(--cold)' }, nuova ? 'Meccanica acquisita' : 'Meccanica gi\u00e0 in tuo possesso'),
      el('h3', { style: 'margin:6px 0 6px;font-size:17px;color:var(--cold)' }, pia.meccanica),
      el('p', { style: 'margin:0;font-size:14px;color:var(--dim)' }, pia.mecc_desc)));
  }
}

/* ---- 02 · CONSULTATORE DEL LOG ---- */
V.log = () => {
  vt.textContent = 'Consultatore'; vs.textContent = 'Diario di bordo · interrogazione per parola';
  clear(app);
  const lista = el('div'), cont = el('div', { class: 'eyebrow', style: 'margin:22px 0 10px' });
  const fb = el('p', { class: 'hint' },
    'Il Decifratore ti legge le parole trovate nei testi. Digitane una: se l\u2019archivio la conosce, restituisce un indizio. Costa 1 minuto.');

  const disegna = () => {
    clear(lista);
    D.log.forEach(L => {
      const ap = S.log.includes(L.id);
      const it = el('div', { class: 'item' + (ap ? '' : ' lock') });
      it.append(el('div', { class: 'meta' }, ap ? L.sigillo + ' · ' + L.parola : 'voce sigillata'),
        el('h4', {}, ap ? L.titolo : '— — —'));
      if (ap) {
        it.append(el('div', { class: 'body' }, L.corpo));
        if (L.indizio) it.append(el('div', { class: 'clue' }, '▸ ' + L.indizio));
      } else it.append(el('div', { class: 'body' }, 'Serve la parola giusta.'));
      lista.append(it);
    });
    cont.textContent = S.log.length + ' / ' + D.log.length + ' voci aperte';
  };

  const chiedi = parola => {
    const p = parola.trim().toUpperCase();
    if (!p) return;
    const L = D.log.find(x => x.parola === p);
    const costo = COSTO.consulta;
    segna('consulta', p + (L ? ' · trovata' : ' · nulla'), costo);
    if (!L) { fb.className = 'err';
      fb.textContent = '⚠ L\u2019archivio non conosce «' + p + '». Persi ' + costo + ' minuto.'; return; }
    if (S.log.includes(L.id)) { fb.className = 'hint';
      fb.textContent = '«' + p + '» era gi\u00e0 stata usata: ' + L.titolo; disegna(); return; }
    add('log', L.id); fb.className = 'ok';
    fb.textContent = '✓ ' + L.titolo + ' — costo ' + costo + ' minuto'; disegna();
  };

  const wIn = el('input', { type: 'text', placeholder: 'parola', autocapitalize: 'characters' });
  wIn.addEventListener('keydown', e => { if (e.key === 'Enter') chiedi(wIn.value); });
  app.append(
    el('div', { class: 'card acc' },
      el('div', { class: 'eyebrow', style: 'color:var(--ember)' }, 'Interroga l\u2019archivio'),
      el('label', { class: 'fld', style: 'margin-top:10px' },
        el('span', { class: 'lbl' }, 'Parola udita dal Decifratore'), wIn),
      el('button', { class: 'big log-go', type: 'button', style: 'margin-top:12px',
        onclick: () => chiedi(wIn.value) }, 'Cerca  ·  1 min'),
      fb),
    cont, lista);
  disegna();
};

/* ---- 03 · APRITORE DELLE STANZE (enigmi di percorso) ---- */
const PZ = {
 'S-P1': { rows:4, cols:4, start:[3,0], end:[0,3], dots:[],
   squares:[{r:0,c:0,k:'a'},{r:2,c:0,k:'a'},{r:0,c:2,k:'b'},{r:2,c:2,k:'b'}] },
 'S-P2': { rows:5, cols:5, start:[4,0], end:[2,4], dots:[[2,2],[1,3]],
   squares:[{r:0,c:0,k:'a'},{r:1,c:1,k:'a'},{r:2,c:0,k:'a'},{r:3,c:1,k:'a'},
            {r:0,c:2,k:'b'},{r:1,c:3,k:'b'},{r:2,c:2,k:'b'},{r:3,c:3,k:'b'}] },
 'S-P3': { rows:5, cols:5, start:[4,2], end:[0,2], dots:[[2,0],[2,4]],
   squares:[{r:0,c:0,k:'a'},{r:3,c:1,k:'a'},{r:1,c:1,k:'a'},
            {r:0,c:3,k:'b'},{r:3,c:3,k:'b'},{r:1,c:2,k:'b'}] },
 'S-FIN':{ rows:5, cols:5, start:[4,2], end:[0,2], dots:[[2,0],[2,4],[4,0]],
   squares:[{r:0,c:0,k:'a'},{r:1,c:1,k:'a'},{r:3,c:0,k:'a'},{r:2,c:1,k:'a'},
            {r:0,c:3,k:'b'},{r:1,c:2,k:'b'},{r:3,c:3,k:'b'},{r:2,c:3,k:'b'}] },
};
const key = n => n[0] + ',' + n[1];
function lati(path) { const E = new Set();
  for (let i = 0; i < path.length - 1; i++) { const a = key(path[i]), b = key(path[i+1]); E.add(a < b ? a + '|' + b : b + '|' + a); }
  return E; }
function risolto(P, path) {
  if (path.length < 2) return false;
  if (key(path[0]) !== key(P.start) || key(path[path.length-1]) !== key(P.end)) return false;
  if (!P.dots.every(d => path.some(n => n[0] === d[0] && n[1] === d[1]))) return false;
  const E = lati(path), R = P.rows - 1, C = P.cols - 1, has = (a, b) => {
    const x = key(a), y = key(b); return E.has(x < y ? x + '|' + y : y + '|' + x); };
  const vis = new Set(), q = {};
  P.squares.forEach(s => q[s.r + ',' + s.c] = s.k);
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
function disegnaPuzzle(P, path, svg) {
  const U = 62, PAD = 34, W = (P.cols - 1) * U + PAD * 2, H = (P.rows - 1) * U + PAD * 2;
  const X = c => PAD + c * U, Y = r => PAD + r * U;
  const NS = 'http://www.w3.org/2000/svg', mk = (t, a) => { const n = document.createElementNS(NS, t);
    for (const k in a) n.setAttribute(k, a[k]); return n; };
  clear(svg); svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  P.squares.forEach(s => svg.append(mk('rect', { x: X(s.c) + 16, y: Y(s.r) + 16, width: U - 32, height: U - 32, rx: 5,
    fill: s.k === 'a' ? '#DFE5EF' : '#0A0D13', stroke: s.k === 'a' ? '#DFE5EF' : '#8B96A8', 'stroke-width': 2 })));
  for (let r = 0; r < P.rows; r++) for (let c = 0; c < P.cols; c++) {
    if (c + 1 < P.cols) svg.append(mk('line', { x1: X(c), y1: Y(r), x2: X(c+1), y2: Y(r), stroke: '#242C3A', 'stroke-width': 9, 'stroke-linecap': 'round' }));
    if (r + 1 < P.rows) svg.append(mk('line', { x1: X(c), y1: Y(r), x2: X(c), y2: Y(r+1), stroke: '#242C3A', 'stroke-width': 9, 'stroke-linecap': 'round' }));
  }
  if (path.length > 1) svg.append(mk('polyline', { points: path.map(n => X(n[1]) + ',' + Y(n[0])).join(' '),
    fill: 'none', stroke: '#F08A4B', 'stroke-width': 11, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
  svg.append(mk('circle', { cx: X(P.start[1]), cy: Y(P.start[0]), r: 13, fill: path.length ? '#F08A4B' : '#5F6B7D' }));
  svg.append(mk('circle', { cx: X(P.end[1]), cy: Y(P.end[0]), r: 9, fill: 'none', stroke: '#F08A4B', 'stroke-width': 4 }));
  P.dots.forEach(d => svg.append(mk('polygon', { points: [[0,-8],[7,-4],[7,4],[0,8],[-7,4],[-7,-4]].map(p => (X(d[1])+p[0]) + ',' + (Y(d[0])+p[1])).join(' '),
    fill: path.some(n => n[0]===d[0] && n[1]===d[1]) ? '#F08A4B' : '#79B2D0' })));
  for (let r = 0; r < P.rows; r++) for (let c = 0; c < P.cols; c++) {
    const hit = mk('circle', { cx: X(c), cy: Y(r), r: 22, fill: 'transparent', style: 'cursor:pointer' });
    hit.dataset.n = r + ',' + c; svg.append(hit);
  }
}
V.stanze = () => {
  vt.textContent = 'Apritore'; vs.textContent = 'Enigmi di percorso · apertura stanze';
  clear(app);
  const sel = el('div', { class: 'roles' });
  D.stanze.forEach(st => {
    const fatto = S.stanze.includes(st.id);
    sel.append(el('button', { class: 'role', type: 'button', onclick: () => enigma(st) },
      el('div', { class: 'n' }, (D.pianeti.find(p => p.id === st.pianeta) || { sub: 'sistema' }).sub),
      el('h3', {}, st.nome),
      el('p', {}, fatto ? '✓ Aperta — codice ' + st.codice : 'Sigillata. Risolvi il percorso per aprirla.')));
  });
  app.append(el('p', { class: 'hint', style: 'margin:0 0 18px' },
    'Traccia un percorso dal nodo pieno al nodo cerchiato. Separa i quadrati chiari dai quadrati scuri. Tocca i punti esagonali lungo la via. Tocca l\'ultimo nodo per tornare indietro.'), sel);
};
function enigma(st) {
  const P = PZ[st.id]; let path = [];
  clear(app);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.id = 'pz';
  const fb = el('p', { class: 'hint' }, 'Percorso vuoto.');
  const ridisegna = () => { disegnaPuzzle(P, path, svg);
    svg.querySelectorAll('[data-n]').forEach(h => h.addEventListener('click', () => {
      const [r, c] = h.dataset.n.split(',').map(Number);
      if (!path.length) { if (r === P.start[0] && c === P.start[1]) path = [[r, c]]; else { fb.className = 'err'; fb.textContent = '⚠ Parti dal nodo pieno.'; return; } }
      else { const last = path[path.length - 1];
        if (path.length > 1 && r === last[0] && c === last[1]) path.pop();
        else if (Math.abs(r - last[0]) + Math.abs(c - last[1]) === 1 && !path.some(n => n[0] === r && n[1] === c)) path.push([r, c]);
        else if (r === last[0] && c === last[1]) path = [];
        else { fb.className = 'err'; fb.textContent = '⚠ Solo nodi adiacenti, e mai due volte lo stesso.'; return; } }
      fb.className = 'hint'; fb.textContent = path.length + ' nodi.';
      if (risolto(P, path)) {
        add('stanze', st.id);
        fb.className = 'ok'; fb.textContent = '';
        esito.classList.remove('hide');
      } else esito.classList.add('hide');
      ridisegna();
    }));
  };
  const esito = el('div', { class: 'card acc hide' },
    el('div', { class: 'eyebrow', style: 'color:var(--ember)' }, 'Stanza aperta'),
    el('h3', { style: 'margin:6px 0 10px;font-size:19px' }, st.nome),
    el('p', { style: 'margin:0 0 4px;color:var(--dim);font-size:14px' }, st.sblocca),
    el('p', { class: 'mono', style: 'margin:12px 0 0;font-size:26px;letter-spacing:.24em;color:var(--ember)' }, st.codice),
    el('p', { class: 'hint', style: 'margin-top:6px' }, 'Comunica questo codice al Master per ricevere la carta-stanza.'));
  app.append(svg,
    el('div', { class: 'pzrow' },
      el('button', { class: 'big ghost', type: 'button', onclick: () => { path = []; fb.textContent = 'Percorso vuoto.'; fb.className = 'hint'; esito.classList.add('hide'); ridisegna(); } }, 'Azzera'),
      el('button', { class: 'big ghost', type: 'button', onclick: () => go('stanze') }, 'Indietro')),
    fb, esito);
  if (S.stanze.includes(st.id)) esito.classList.remove('hide');
  ridisegna();
}

/* ---- MASTER · console di sistema ----
   I 30 minuti sono un BUDGET, non un cronometro: ogni azione costa 1d4+1. */
V.master = () => {
  vt.textContent = 'Console di Sistema'; vs.textContent = 'Solo per il narratore';
  clear(app);
  let M = { min: 30, loop: 1, storia: [] };
  try { Object.assign(M, JSON.parse(localStorage.getItem('emberloop.master') || '{}')); } catch (e) {}
  const salvaM = () => { try { localStorage.setItem('emberloop.master', JSON.stringify(M)); } catch (e) {} };

  const clock = el('div', { class: 'clock mono' });
  const sotto = el('div', { class: 'eyebrow', style: 'text-align:center;margin-bottom:4px' });
  const roll = el('div', { class: 'roll' }, ' ');
  const stato = el('div', { style: 'margin-top:6px' });

  const dipingi = () => {
    clock.textContent = M.min + "'";
    clock.className = 'clock mono' + (M.min <= 5 ? ' crit' : M.min <= 12 ? ' warn' : '');
    sotto.textContent = 'Loop ' + M.loop + ' · minuti rimasti nel loop';
    clear(stato);
    ['PORTARE', 'PERCEPIRE', 'SCEGLIERE'].forEach(m =>
      stato.append(el('span', { class: 'chip' + (S.mecc.includes(m) ? ' on' : '') }, m)));
    stato.append(el('div', { class: 'hint', style: 'margin-top:8px' },
      S.mecc.length === 3 ? '▸ Tre meccaniche acquisite: possono restare oltre la luce. Sblocca Il Cuore del Sistema.'
                          : '▸ ' + S.mecc.length + '/3 meccaniche. Servono tutte e tre per vedere l’accensione.'));
    salvaM();
  };
  const spendi = etichetta => {
    const d = 1 + Math.floor(Math.random() * 4), costo = d + 1;
    M.storia.push(costo);
    M.min = Math.max(0, M.min - costo);
    roll.textContent = etichetta + ' → 1d4+1 = ' + d + '+1 = ' + costo + ' min';
    if (M.min === 0) roll.textContent += '  ·  LUCE BIANCA';
    dipingi();
  };
  const B = (t, lbl) => el('button', { class: 'big ghost', type: 'button', onclick: () => spendi(lbl) }, t);

  app.append(el('div', { class: 'card' }, clock, sotto, roll,
      el('div', { class: 'grid2', style: 'margin-top:14px' },
        B('Spostamento', 'Spostamento'), B('Traduzione', 'Traduzione'),
        B('Registro', 'Consultazione'), B('Enigma', 'Enigma')),
      el('div', { class: 'grid2', style: 'margin-top:10px' },
        el('button', { class: 'big ghost', type: 'button', onclick: () => {
            const u = M.storia.pop(); if (u) { M.min = Math.min(30, M.min + u); roll.textContent = 'annullato −' + u + ' min'; dipingi(); } } }, 'Annulla'),
        el('button', { class: 'big', type: 'button', onclick: () => {
            M.loop++; M.min = 30; M.storia = []; roll.textContent = 'Nuovo loop. Il mondo torna indietro.'; dipingi(); } }, 'Nuovo loop'))),
    el('div', { class: 'card cold' },
      el('div', { class: 'eyebrow', style: 'color:var(--cold)' }, 'Stato dei rilevatori su questo dispositivo'), stato),
    el('div', { class: 'card' },
      el('div', { class: 'eyebrow' }, 'Costo riportato da un giocatore'),
      el('p', { class: 'hint', style: 'margin:8px 0 10px' },
        'Le app dei ruoli tirano da sole e dicono quanto e\u2019 costato. Scala qui il numero che ti riferiscono.'),
      (() => {
        const n = el('input', { type: 'text', inputmode: 'numeric', placeholder: 'minuti', style: 'text-align:center' });
        const go = () => { const v = parseInt(n.value, 10);
          if (!v || v < 1) return;
          M.storia.push(v); M.min = Math.max(0, M.min - v);
          roll.textContent = 'riportato dal tavolo \u2212' + v + ' min'; n.value = ''; dipingi(); };
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
            el('span', { class: 'mono', style: 'color:var(--ember)' }, '\u2212' + a.m))));
        };
        dis(); return box;
      })()),
    el('div', { class: 'card' },
      el('div', { class: 'eyebrow' }, 'Failsafe del narratore'),
      el('p', { class: 'hint', style: 'margin:8px 0 0' },
        'Se il gruppo si blocca, il tuo compito è far avanzare la trama: leggi tu il testo dal foglio chiavi e considera la stanza aperta. Le chiavi non sono in questa app di proposito — sono su CHIAVI-MASTER, stampato.'),
      el('button', { class: 'big ghost', type: 'button', style: 'margin-top:14px', onclick: () => {
          if (confirm('Azzerare tutti i progressi su QUESTO dispositivo?')) {
            S = { testi: [], log: [], stanze: [], mecc: [], plain: {}, storico: [] }; save();
            M = { min: 30, loop: 1, storia: [] }; salvaM(); dipingi(); } } }, 'Azzera dispositivo')));
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
