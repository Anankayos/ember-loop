# -*- coding: utf-8 -*-
"""Genera stampa.html: un foglio-sigillo per ogni testo, e le carte-porta per il narratore.
   I glifi sono resi dal browser con LA STESSA funzione dell'app, cosi' combaciano sempre.
   Lo lancia costruisci.py; da solo:  python genera_stampe.py"""
import html, json, re, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
try:
    import qrcode
except ImportError:
    print("  !! manca il modulo qrcode: pip install qrcode"); sys.exit(1)

d = json.loads(re.sub(r'^.*?window\.DATI = ', '', open('dati.js', encoding='utf-8').read(), flags=re.S).rstrip().rstrip(';'))
if d.get('schema') != 2:
    print("  !! dati.js e' nel formato vecchio: rigeneralo con  python costruisci.py"); sys.exit(1)
e = lambda s: html.escape(str(s or ''), quote=True)

def qr_svg(dati, px=150):
    q = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    q.add_data(dati); q.make(fit=True)
    m = q.get_matrix(); n = len(m)
    celle = "".join(f'<rect x="{x}" y="{y}" width="1" height="1"/>'
                    for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg viewBox="0 0 {n} {n}" width="{px}" height="{px}" shape-rendering="crispEdges" '
            f'role="img" aria-label="sigillo {e(dati)}"><rect width="{n}" height="{n}" fill="#fff"/>'
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
    <div class="cod">{e(codice)}</div>'''

P = {p['id']: p for p in d['pianeti']}
nome = lambda pid: (P.get(pid) or {}).get('nome', pid)
pag = []

# --- un foglio per testo: il sigillo da scansionare, il testo si apre da solo nell'app ---
for t in d['testi']:
    pag.append(f'''<section class="foglio">
  <div class="hd"><div class="eb">Archivio Kindler &middot; reperto</div>
    <h2>{e(t['titolo'])}</h2><div class="sub">{e(nome(t['pianeta']))}</div></div>
  <div class="mid">{sigillo(t['id'])}</div>
  <div class="gly" data-seme="{e(t['id'])}" data-n="260"></div>
  <div class="ft">Il Decifratore inquadra il sigillo, oppure digita <b>{e(t['id'])}</b>: il testo si apre da solo.</div>
</section>''')

# --- carte-porta, per il narratore ---
if d['stanze']:
    st = "".join(f'''<div class="carta stanza">
  <div class="eb">Porta di pietra &middot; {e(nome(s['pianeta']))}</div><h3>{e(s['nome'])}</h3>
  <div class="ft2">{e(s['sblocca'])}</div></div>''' for s in d['stanze'])
    pag.append(f'<section class="foglio"><div class="hd"><div class="eb">Solo per il narratore &middot; da ritagliare</div>'
               f'<h2>Carte-porta</h2><div class="sub">consegnale quando il telefono dell\'Apritore mostra la porta aperta</div></div>'
               f'<div class="griglia">{st}</div></section>')

GLYPH_JS = open('app.js', encoding='utf-8').read()
GLYPH_JS = GLYPH_JS[GLYPH_JS.index("const GL ="):GLYPH_JS.index("/* ---------------- scanner")]

pagina = f'''<!doctype html><html lang="it"><head><meta charset="utf-8">
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
.ft2 {{ font-size:9.5pt; color:#444; margin-top:6px; white-space:pre-wrap; }}
.carta.stanza {{ background:#f4f2ee; }}
@media print {{ body {{ background:#fff; }} .foglio {{ margin:0; box-shadow:none; }} }}
</style></head><body>
{"".join(pag)}
<script>
{GLYPH_JS}
document.querySelectorAll('.gly').forEach(function(n){{
  n.textContent = glifi(n.dataset.seme, parseInt(n.dataset.n,10));
}});
</script>
</body></html>'''
open('stampa.html', 'w', encoding='utf-8', newline='\n').write(pagina)
print("stampa.html generato ·", len(d['testi']), "fogli-sigillo +", len(d['stanze']), "carte-porta")
