# -*- coding: utf-8 -*-
"""Genera stampa.html: sigilli QR + fogli reperto + carte-stanza.
   I glifi sono resi dal browser con LA STESSA funzione dell'app, cosi' combaciano sempre."""
import qrcode, qrcode.image.svg, io, re, json

d = json.loads(re.sub(r'^.*?window\.DATI = ', '', open('dati.js', encoding='utf-8').read(), flags=re.S).rstrip().rstrip(';'))

def qr_svg(dati, px=150):
    q = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    q.add_data(dati); q.make(fit=True)
    m = q.get_matrix(); n = len(m)
    celle = "".join(f'<rect x="{x}" y="{y}" width="1" height="1"/>'
                    for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg viewBox="0 0 {n} {n}" width="{px}" height="{px}" shape-rendering="crispEdges" '
            f'role="img" aria-label="sigillo {dati}"><rect width="{n}" height="{n}" fill="#fff"/>'
            f'<g fill="#111">{celle}</g></svg>')

def sigillo(codice, px=104):
    """QR dentro una cornice esagonale: sembra un sigillo, non un QR."""
    return f'''<div class="sig" style="width:{px+80}px;height:{px+80}px">
      <svg class="ring" viewBox="0 0 100 100" aria-hidden="true" style="width:{px+80}px;height:{px+80}px">
        <polygon points="50,3 91,26 91,74 50,97 9,74 9,26" fill="none" stroke="#111" stroke-width="1.6"/>
        <polygon points="50,9 86,29 86,71 50,91 14,71 14,29" fill="none" stroke="#111" stroke-width=".6"/>
      </svg>
      <div class="qr">{qr_svg(codice, px)}</div>
    </div>
    <div class="cod">{codice}</div>'''

P = {p['id']: p for p in d['pianeti']}
pag = []

# --- fogli reperto (testi cifrati) ---
for t in d['testi']:
    pia = P.get(t['pianeta'], {'sub': 'registrazione terminale', 'nome': 'Il Cuore del Sistema'})
    pag.append(f'''<section class="foglio">
  <div class="hd"><div class="eb">Archivio Kindler &middot; reperto</div>
    <h2>{t['titolo']}</h2><div class="sub">{pia['sub']}</div></div>
  <div class="mid">{sigillo(t['sigillo'])}</div>
  <div class="gly" data-seme="{t['sigillo']}" data-n="260"></div>
  <div class="ft">Decifrabile solo con la chiave corretta. Il Decifratore inquadra il sigillo, oppure digita <b>{t['sigillo']}</b>.</div>
</section>''')

# --- carte log (4 per pagina) ---
carte = "".join(f'''<div class="carta">
  <div class="eb">Diario di bordo</div><h3>{L['sigillo']}</h3>
  <div class="mini">{sigillo(L['sigillo'], 88)}</div>
  <div class="ft2">{P.get(L['pianeta'],{}).get('sub','')}</div></div>''' for L in d['log'])
pag.append(f'<section class="foglio"><div class="hd"><div class="eb">Da ritagliare</div><h2>Sigilli del diario di bordo</h2>'
           f'<div class="sub">uno per ogni voce &middot; il Consultatore li scansiona</div></div><div class="griglia">{carte}</div></section>')

# --- carte stanza ---
st = "".join(f'''<div class="carta stanza">
  <div class="eb">Stanza</div><h3>{s['nome']}</h3>
  <div class="codbig">{s['codice']}</div>
  <div class="ft2">{s['sblocca']}</div></div>''' for s in d['stanze'])
pag.append(f'<section class="foglio"><div class="hd"><div class="eb">Solo per il Master &middot; da ritagliare</div>'
           f'<h2>Carte-stanza</h2><div class="sub">consegnale quando l\'Apritore comunica il codice</div></div>'
           f'<div class="griglia">{st}</div></section>')

GLYPH_JS = open('app.js', encoding='utf-8').read()
GLYPH_JS = GLYPH_JS[GLYPH_JS.index("const GL ="):GLYPH_JS.index("/* ---------------- scanner")]

html = f'''<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>The Ember Loop — materiali da stampare</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ margin:0; background:#8a8f96; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:#111; }}
.foglio {{ background:#fff; width:210mm; min-height:297mm; margin:0 auto 10mm; padding:20mm 18mm; box-sizing:border-box;
  page-break-after:always; display:flex; flex-direction:column; }}
.hd {{ border-bottom:1px solid #111; padding-bottom:10px; margin-bottom:26px; }}
.eb {{ font-family:ui-monospace,Menlo,monospace; font-size:9.5pt; letter-spacing:.18em; text-transform:uppercase; color:#666; }}
h2 {{ margin:6px 0 2px; font-size:23pt; font-weight:600; letter-spacing:-.01em; }}
.sub {{ font-style:italic; color:#555; font-size:11pt; }}
.mid {{ text-align:center; margin:6mm 0 8mm; }}
.sig {{ position:relative; display:inline-block; }}
.sig .ring {{ position:absolute; inset:0; }}
.sig .qr {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; }}
.cod {{ font-family:ui-monospace,Menlo,monospace; font-size:12pt; letter-spacing:.28em; margin-top:6px; }}
.gly {{ font-family:ui-monospace,Menlo,monospace; font-size:14pt; line-height:1.85; letter-spacing:.2em;
  color:#333; word-break:break-all; text-align:justify; flex:1; border-top:1px solid #ddd; padding-top:8mm; }}
.ft {{ border-top:1px solid #111; margin-top:8mm; padding-top:6px; font-size:9.5pt; color:#444; }}
.griglia {{ display:grid; grid-template-columns:1fr 1fr; gap:8mm; }}
.carta {{ border:1.5px solid #111; border-radius:3px; padding:7mm; text-align:center; min-height:62mm;
  display:flex; flex-direction:column; align-items:center; justify-content:center; page-break-inside:avoid; }}
.carta h3 {{ margin:4px 0 8px; font-size:13pt; font-family:ui-monospace,Menlo,monospace; letter-spacing:.12em; }}
.mini {{ margin:2mm 0; }} 
.ft2 {{ font-size:9pt; color:#555; font-style:italic; margin-top:6px; }}
.carta.stanza {{ background:#f4f2ee; }}
.codbig {{ font-family:ui-monospace,Menlo,monospace; font-size:19pt; letter-spacing:.24em; margin:5mm 0; }}
@media print {{ body {{ background:#fff; }} .foglio {{ margin:0; box-shadow:none; }} }}
</style></head><body>
{"".join(pag)}
<script src="dati.js"></script>
<script>
{GLYPH_JS}
document.querySelectorAll('.gly').forEach(function(n){{
  n.textContent = glifi(n.dataset.seme, parseInt(n.dataset.n,10));
}});
</script>
</body></html>'''
open('stampa.html','w',encoding='utf-8').write(html)
print("stampa.html generato ·", len(d['testi']), "fogli reperto +", len(d['log']), "sigilli log +", len(d['stanze']), "carte-stanza")
