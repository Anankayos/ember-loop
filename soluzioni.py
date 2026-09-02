# -*- coding: utf-8 -*-
"""Calcola le soluzioni degli enigmi e le traduce in indicazioni leggibili."""
import re, json, sys
sys.path.insert(0, '.')
import verifica_puzzle as V

# legge le definizioni direttamente da app.js, cosi' non possono divergere
src = open('app.js', encoding='utf-8').read()
blocco = src[src.index('const PZ = {'):src.index('const key = n =>')]
blocco = re.sub(r'//.*', '', blocco)
js = blocco[blocco.index('{'):blocco.rindex('}')+1]
js = re.sub(r"'([^']*)'", r'"\1"', js)
js = re.sub(r'(\w+)\s*:', r'"\1":', js)
js = re.sub(r'""(\w+)"":', r'"\1":', js)
js = re.sub(r',\s*}', '}', js); js = re.sub(r',\s*]', ']', js)
PZ = json.loads(js)

def to_py(p):
    return dict(rows=p['rows'], cols=p['cols'], start=tuple(p['start']), end=tuple(p['end']),
                dots=[tuple(d) for d in p['dots']],
                squares=[dict(r=s['r'], c=s['c'], k=s['k']) for s in p['squares']])

def direzioni(path):
    """trasforma un percorso di nodi in  su/giu/destra/sinistra  con i conteggi"""
    passi, i = [], 1
    while i < len(path):
        dr = path[i][0]-path[i-1][0]; dc = path[i][1]-path[i-1][1]
        nome = {(-1,0):'su', (1,0):'giu', (0,1):'destra', (0,-1):'sinistra'}[(dr,dc)]
        n = 1
        while i+1 < len(path) and (path[i+1][0]-path[i][0], path[i+1][1]-path[i][1]) == (dr,dc):
            n += 1; i += 1
        passi.append(f"{nome} {n}" if n > 1 else nome)
        i += 1
    # compatta ripetizioni consecutive uguali
    return " -> ".join(passi)

ORDINE = [('S-P1','La Sala Comune'), ('S-P2','La Camera Centrale'),
          ('S-P3',"L'Osservatorio"), ('S-FIN','Il Cuore del Sistema')]
righe = []
for pid, nome in ORDINE:
    P = to_py(PZ[pid])
    sol = V.soluzioni(P, limite=1)
    if not sol:
        righe.append(f"- **{nome}** ({pid}): NESSUNA SOLUZIONE — enigma rotto!"); continue
    s = sol[0]
    tot, val = 0, 0
    def dfs(path, vis):
        global tot, val
        n = path[-1]
        if n == P['end']:
            tot += 1
            if V.valido(P, path): val += 1
            return
        for d in ((-1,0),(1,0),(0,-1),(0,1)):
            m = (n[0]+d[0], n[1]+d[1])
            if 0 <= m[0] < P['rows'] and 0 <= m[1] < P['cols'] and m not in vis:
                vis.add(m); path.append(m); dfs(path, vis); path.pop(); vis.remove(m)
    dfs([P['start']], {P['start']})
    pct = 100*val/tot if tot else 0
    diff = 'tutorial' if pct > 20 else 'medio' if pct > 3 else 'difficile'
    righe.append(f"- **{nome}** ({pid}) — {diff}, {val} soluzioni su {tot} percorsi ({pct:.1f}%)\n"
                 f"  - dal nodo pieno: `{direzioni(s)}`")

blocco_md = "\n## Soluzioni degli enigmi\n\nSolo per il failsafe: se il gruppo si blocca, guidali o considera la stanza aperta.\n\n" + "\n".join(righe) + "\n"
km = open('CHIAVI-MASTER.md', encoding='utf-8').read()
km = re.sub(r'\n## Soluzioni degli enigmi.*', '', km, flags=re.S).rstrip() + "\n" + blocco_md
open('CHIAVI-MASTER.md','w',encoding='utf-8').write(km)
print(blocco_md)
