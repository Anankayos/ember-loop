/* The Ember Loop — i tre cifrari kindler, porta JS di cifrari.py.
   cifrari.py e' la verita': se questa porta non torna con Python, e' sbagliata
   questa, non quella. La prova e' prove/confronto_cifrari.py.
   Qui non c'e' nessuna chiave, nessun codice e nessuna parola: solo l'aritmetica. */
'use strict';
const Cifrari = (() => {
  const ALFA = 'ABCDEFGHILMNOPQRSTUVZ', N = ALFA.length;   // 21 segni
  const VOC = 'AEIOU', CON = 'BCDFGHLMNPQRSTVZ';
  const mod = (a, n) => ((a % n) + n) % n;                 // il % di Python, anche sui negativi
  const segni = s => Array.from(s);
  const posto = (anello, c) => { const i = anello.indexOf(c);
    if (i < 0) throw new RangeError('segno fuori dall’alfabeto kindler: ' + c); return i; };
  // una chiave-parola da' un passo per lettera, poi ricomincia; un numero vale per tutte
  const passo = (k, i) => Array.isArray(k) ? k[i % k.length] : k;

  /* ---------------- ORDINE: permutazioni pure ---------------- */
  const inverso = s => segni(s).reverse().join('');
  function coppie(s) {
    const l = segni(s);
    for (let i = 0; i + 1 < l.length; i += 2) [l[i], l[i + 1]] = [l[i + 1], l[i]];
    return l.join('');
  }
  function colonne(s, col = 3) {
    const l = segni(s), righe = Math.ceil(l.length / col), fuori = [];
    for (let c = 0; c < col; c++)
      for (let r = 0; r < righe; r++) { const i = r * col + c; if (i < l.length) fuori.push(l[i]); }
    return fuori.join('');
  }
  function colonneInv(s, col = 3) {
    const l = segni(s), righe = Math.ceil(l.length / col), alt = [], dentro = [];
    for (let c = 0; c < col; c++) {
      let n = 0; for (let r = 0; r < righe; r++) if (r * col + c < l.length) n++;
      alt.push(n);
    }
    for (let c = 0, k = 0; c < col; c++) { dentro.push(l.slice(k, k + alt[c])); k += alt[c]; }
    const fuori = new Array(l.length);
    for (let c = 0; c < col; c++) dentro[c].forEach((ch, r) => { fuori[r * col + c] = ch; });
    return fuori.join('');
  }
  const ORDINI = {
    inverso: { avanti: inverso, indietro: inverso },
    coppie:  { avanti: coppie,  indietro: coppie },
    colonne: { avanti: s => colonne(s), indietro: s => colonneInv(s) },
  };

  /* ---------------- ALFABETO: sostituzioni ---------------- */
  // Su scorrimento e specchio cifrari.py accetta solo un numero. Una chiave-parola
  // li' e' fuori dal suo dominio: qui si applica lettera per lettera come fa
  // anelli, cosi' esce spazzatura invece di un errore. Non apre mai niente che
  // il numero giusto non aprirebbe.
  const sost = f => (s, k) => segni(s).map((c, i) => f(c, passo(k, i))).join('');
  const ALFABETI = {
    scorrimento: {
      avanti:   sost((c, p) => ALFA[mod(posto(ALFA, c) + p, N)]),
      indietro: sost((c, p) => ALFA[mod(posto(ALFA, c) - p, N)]) },
    specchio: {
      avanti:   sost((c, p) => ALFA[mod(N - 1 - posto(ALFA, c) + p, N)]),
      indietro: sost((c, p) => ALFA[mod(N - 1 - mod(posto(ALFA, c) - p, N), N)]) },
    anelli: {
      avanti:   sost((c, p) => { const a = VOC.includes(c) ? VOC : CON; return a[mod(posto(a, c) + p, a.length)]; }),
      indietro: sost((c, p) => { const a = VOC.includes(c) ? VOC : CON; return a[mod(posto(a, c) - p, a.length)]; }) },
  };

  /* ---------------- CHIAVE ---------------- */
  const chiaveDaParola = parola =>
    segni(parola.toUpperCase()).filter(c => ALFA.includes(c)).map(c => ALFA.indexOf(c) + 1);

  /* ---------------- i tre cifrari ---------------- */
  /* Ogni cifrario si porta dietro la propria spiegazione in una riga per parte. Non e' un
     segreto che non sia gia' qui sopra in forma di codice: serve alla console del narratore,
     che la mostra quando deve spiegare o sbloccare il tavolo. Le frasi che i giocatori
     digitano NON stanno qui: quelle si leggono nei reperti propedeutici. */
  /* Un esempio svolto per ogni passaggio, con parole INVENTATE: PIETRA, SOGLIA, LEGAME
     non sono parole del gioco, cosi' il narratore puo' spiegare senza regalare niente.
     I valori escono da questi stessi cifrari: prove/confronto_cifrari.py li ricalcola. */
  const CIFRARI = {
    HUSA: {
      alfabeto: 'scorrimento', ordine: 'inverso',
      esempi: {
        alfabeto: { da: 'PIETRA', a: 'TOIAVE', nota: 'ogni lettera avanti di 4' },
        ordine: { da: 'PIETRA', a: 'ARTEIP', nota: 'la stessa parola, letta al contrario' },
        chiave: { da: 'sigillo n. 10, parola di 6 segni', a: '16', nota: '10 + 6' },
        insieme: { da: 'PIETRA', a: 'EVAIOT', nota: 'prima l’alfabeto, poi l’ordine, con la chiave 4' },
      },
      dice: {
        alfabeto: 'Ogni lettera avanza di tanti posti quanti dice la chiave, sempre in avanti; arrivata in fondo riparte dalla A.',
        ordine: 'La parola si legge al contrario: l’ultimo segno inciso è il primo che si legge.',
        chiave: 'Il numero del sigillo più quante lettere ha la parola cifrata.',
      },
    },
    POLIS: {
      alfabeto: 'specchio', ordine: 'coppie',
      esempi: {
        alfabeto: { da: 'SOGLIA', a: 'IOURSD', nota: 'prima lo specchio, poi avanti di 4' },
        ordine: { da: 'SOGLIA', a: 'OSLGAI', nota: 'scambiate a due a due' },
        chiave: { da: 'sigillo n. 7, seconda parola guasta', a: '14', nota: '7 × 2' },
        insieme: { da: 'SOGLIA', a: 'OIRUDS', nota: 'prima l’alfabeto, poi l’ordine, con la chiave 4' },
      },
      dice: {
        alfabeto: 'Prima l’alfabeto si rovescia (A diventa Z, B diventa V…), poi scorre in avanti di quanto dice la chiave. In quest’ordine.',
        ordine: 'Le lettere si scambiano a due a due: 1ª con 2ª, 3ª con 4ª. Se ne avanza una, resta dov’è.',
        chiave: 'Il numero del sigillo per il posto della parola nel reperto: 1ª, 2ª, 3ª parola guasta.',
      },
    },
    IRIS: {
      alfabeto: 'anelli', ordine: 'colonne',
      esempi: {
        alfabeto: { da: 'LEGAME', a: 'NEGIPE', nota: 'ogni lettera col suo passo, nel suo anello' },
        ordine: { da: 'LEGAME', a: 'LAEMGE', nota: 'tre colonne, lette in giù' },
        chiave: { da: 'il reperto comincia con «Berg»', a: '2-5-16-7', nota: 'B E R G nell’alfabeto kindler' },
        insieme: { da: 'LEGAME', a: 'NIEPGE', nota: 'prima l’alfabeto, poi l’ordine, con la chiave BERG' },
      },
      dice: {
        alfabeto: 'Due ruote separate: le 5 vocali girano fra le vocali, le 16 consonanti fra le consonanti. Mai un salto da una ruota all’altra.',
        ordine: 'La parola si scrive in tre colonne, riga per riga, e si legge in giù: prima colonna, poi seconda, poi terza.',
        chiave: 'Non un numero: la prima parola in chiaro del reperto. Ogni sua lettera dà il passo di una lettera, poi si ricomincia.',
      },
    },
  };
  function cifra(pianeta, parola, k) {
    const c = CIFRARI[pianeta];
    return ORDINI[c.ordine].avanti(ALFABETI[c.alfabeto].avanti(parola.toUpperCase(), k));
  }
  /** Decifra con parti prese da cifrari qualunque: e' quello che fa il decodificatore
      quando il tavolo gli da' un alfabeto e un ordine. */
  const applica = (alfabeto, ordine, cifrato, k) =>
    ALFABETI[alfabeto].indietro(ORDINI[ordine].indietro(cifrato.toUpperCase()), k);
  const decifra = (pianeta, cifrato, k) =>
    applica(CIFRARI[pianeta].alfabeto, CIFRARI[pianeta].ordine, cifrato, k);

  /* ---------------- guardie ---------------- */
  function chiaveDegenere(pianeta, k) {
    if (pianeta === 'HUSA') return (Array.isArray(k) ? k : [k]).every(p => mod(p, N) === 0);
    if (pianeta === 'POLIS') return false;
    if (pianeta === 'IRIS') return (Array.isArray(k) ? k : [k]).every(p => mod(p, 5) === 0 && mod(p, 16) === 0);
    throw new RangeError(pianeta);
  }
  const ordineTrasparente = (pianeta, parola) =>
    ORDINI[CIFRARI[pianeta].ordine].avanti(parola.toUpperCase()) === parola.toUpperCase();
  const comePython = k => Array.isArray(k) ? '[' + k.join(', ') + ']' : String(k);
  function controllaParola(pianeta, parola, k) {
    const guai = [], p = parola.toUpperCase();
    if (!segni(p).every(c => ALFA.includes(c)))
      guai.push('contiene segni fuori dall\'alfabeto kindler (' +
        [...new Set(segni(p).filter(c => !ALFA.includes(c)))].sort().join('') + ')');
    if (segni(p).length < 3) guai.push('e\' troppo corta: sotto le tre lettere si indovina a occhio');
    if (chiaveDegenere(pianeta, k)) guai.push('la chiave ' + comePython(k) + ' rende il cifrario trasparente');
    if (ordineTrasparente(pianeta, p)) guai.push('la permutazione la lascia identica: la parte dell\'Apritore sparirebbe');
    return guai;
  }

  /* ---------------- normalizzazione e impronte ---------------- */
  // Stesse regole di costruisci.py: senza accenti, maiuscolo, solo lettere (e cifre
  // nei codici). Cosi' "pietra-che scende" e "PIETRA CHE SCENDE" sono lo stesso codice.
  const senzaAccenti = s => String(s).normalize('NFD').replace(/\p{Mn}/gu, '');
  const normParola = s => senzaAccenti(s).toUpperCase().replace(/[^A-Z]/g, '');
  const normCodice = s => senzaAccenti(s).toUpperCase().replace(/[^A-Z0-9]/g, '');

  /** La chiave come la digita il Custode: un numero oppure una parola. */
  function leggiChiave(s) {
    const t = senzaAccenti(s).toUpperCase().replace(/\s+/g, '');
    if (/^\d{1,6}$/.test(t)) return { k: parseInt(t, 10), tipo: 'numero' };
    if (/^[A-Z]+$/.test(t)) { const k = chiaveDaParola(t); if (k.length) return { k, tipo: 'parola' }; }
    return null;
  }

  // SHA-256 scritto qui e non preso da crypto.subtle: quello esiste solo in https,
  // e la sera l'app puo' girare da servi.ps1 in http sulla rete di casa.
  const K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const ror = (x, n) => (x >>> n) | (x << (32 - n));
  function sha256(testo) {
    const b = new TextEncoder().encode(testo), blocchi = (b.length + 9 + 63) >> 6;
    const m = new Uint8Array(blocchi * 64); m.set(b); m[b.length] = 0x80;
    const dv = new DataView(m.buffer), bit = b.length * 8;
    dv.setUint32(m.length - 8, Math.floor(bit / 0x100000000)); dv.setUint32(m.length - 4, bit >>> 0);
    const H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    const W = new Uint32Array(64);
    for (let q = 0; q < blocchi; q++) {
      for (let t = 0; t < 16; t++) W[t] = dv.getUint32(q * 64 + t * 4);
      for (let t = 16; t < 64; t++) {
        const s0 = ror(W[t - 15], 7) ^ ror(W[t - 15], 18) ^ (W[t - 15] >>> 3);
        const s1 = ror(W[t - 2], 17) ^ ror(W[t - 2], 19) ^ (W[t - 2] >>> 10);
        W[t] = (W[t - 16] + s0 + W[t - 7] + s1) >>> 0;
      }
      let [a, bb, c, d, e, f, g, h] = H;
      for (let t = 0; t < 64; t++) {
        const t1 = (h + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + K[t] + W[t]) >>> 0;
        const t2 = ((ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = bb; bb = a; a = (t1 + t2) >>> 0;
      }
      [a, bb, c, d, e, f, g, h].forEach((v, i) => { H[i] = (H[i] + v) >>> 0; });
    }
    return H.map(x => x.toString(16).padStart(8, '0')).join('');
  }
  /** Impronta di una parola o di un codice gia' normalizzati: SHA-256, 16 esadecimali.
      Serve solo a RICONOSCERE un risultato giusto, mai a produrlo. */
  const impronta = s => sha256(s).slice(0, 16);

  return { ALFA, N, VOC, CON, ORDINI, ALFABETI, CIFRARI, chiaveDaParola,
           cifra, decifra, applica, chiaveDegenere, ordineTrasparente, controllaParola,
           senzaAccenti, normParola, normCodice, leggiChiave, sha256, impronta };
})();
if (typeof window !== 'undefined') window.Cifrari = Cifrari;
