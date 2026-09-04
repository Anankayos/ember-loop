# -*- coding: utf-8 -*-
"""
Ricostruisce prova-offline.html a partire da index.html.

Perche' esiste: la copia offline era stata montata a mano una volta e poi
e' andata in deriva due volte — la prima perdendo il <meta charset> (tutti
gli accenti diventati mojibake), la seconda restando indietro rispetto ad
app.js. Un file generato non puo' fare nessuna delle due cose.

Il risultato e' un documento unico, senza nessuna richiesta di rete:
jsQR, i dati e l'applicazione finiscono dentro il file.
"""
import re, sys, pathlib, html

QUI = pathlib.Path(__file__).parent
SORGENTE = QUI / 'index.html'
USCITA = QUI / 'prova-offline.html'
DA_INCORPORARE = ['jsQR.min.js', 'dati.js', 'app.js']

AVVISO = """
<div style="max-width:560px;margin:0 auto;padding:14px 18px;border:1px solid #3A2F22;
     background:#191410;color:#C6A268;font:13px/1.5 system-ui,sans-serif">
  <b>Copia unica di prova.</b> Questo file contiene tutto: non chiede niente alla rete.
  Generato da <code>genera_offline.py</code> — non modificarlo a mano, le modifiche
  vanno in <code>index.html</code>, <code>app.js</code> o <code>contenuti.md</code>.
</div>
"""


def main():
    if not SORGENTE.exists():
        print('  !! manca index.html'); return 1

    doc = SORGENTE.read_text(encoding='utf-8')

    if '<meta charset' not in doc.lower():
        print('  !! index.html non dichiara il charset: mi fermo, gli accenti si romperebbero')
        return 1

    for nome in DA_INCORPORARE:
        f = QUI / nome
        if not f.exists():
            print('  !! manca %s' % nome); return 1
        codice = f.read_text(encoding='utf-8')
        # </script> dentro una stringa chiuderebbe il tag ospite
        codice = codice.replace('</script>', '<\\/script>')
        tag = '<script src="%s"></script>' % nome
        if tag not in doc:
            print('  !! index.html non carica %s con il tag atteso' % nome); return 1
        doc = doc.replace(tag, '<script>\n/* ---- %s ---- */\n%s\n</script>' % (nome, codice))

    doc = doc.replace('<body>', '<body>' + AVVISO, 1)
    doc = doc.replace('<title>', '<title>[offline] ', 1)

    USCITA.write_text(doc, encoding='utf-8')

    # controlli: nessun riferimento esterno rimasto, charset presente
    resti = re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="(?!data:|#)([^"]+)"', doc)
    if resti:
        print('  !! restano riferimenti esterni: %s' % ', '.join(sorted(set(resti)))); return 1
    if 'charset' not in doc[:400].lower():
        print('  !! il charset non e\' nei primi byte del file'); return 1

    print('prova-offline.html generato · %d KB · 0 richieste di rete' % (len(doc.encode('utf-8')) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
