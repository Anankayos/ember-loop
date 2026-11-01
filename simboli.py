# -*- coding: utf-8 -*-
"""L'alfabeto di simboli: come i Kindler scrivono davvero.

Sul foglio stampato il reperto non e' in italiano: e' trascritto segno per segno in
questo alfabeto. Chi lo trova vede un documento alieno. Scansionando il sigillo, l'app
gli restituisce il testo leggibile - **tranne le parole fra graffe**, che restano cifrate
con il cifrario kindler, in lettere normali. Due serrature diverse, una dentro l'altra:
l'app apre la prima, i tre giocatori insieme aprono la seconda.

Non e' un cifrario e non deve esserlo: il testo in chiaro l'app lo regala a chiunque
scansioni, gratis. E' il modo in cui il mondo e' scritto, e il motivo per cui serve
il terminale per leggerlo.

    python simboli.py          # la tabella, da stampare per te
"""
import re
import unicodedata

# I tre simboli dei mondi (e quello del Rewinder) restano FUORI dall'alfabeto: accanto a
# una parola cifrata devono volere dire una cosa sola.
MONDI = "◆▲●◇"                       # diamante, triangolo, cerchio, rombo vuoto

# 36 segni per 26 lettere e 10 cifre. Tutti disegnabili con i font di sistema: niente
# font remoti (regola 2), e in monospazio restano della stessa larghezza.
SEGNI = ("▼○□■△▽◁▷◀▶"
         "┌┐└┘├┤┬┴┼─"
         "│╱╲╳⌐¬±∴∵≈"
         "≠≡⊂⊃⊕⊗")

# L'ordine e' mescolato una volta per tutte: nessuno deve poter indovinare che la prima
# lettera e' il primo segno. Mescolato qui a mano, non a caso, cosi' non cambia mai.
LETTERE = "ABCDEFGHILMNOPQRSTUVZJKWXY"                   # prima le 21 kindler, poi le altre 5
CIFRE = "0123456789"
_MESCOLA = [19, 7, 30, 2, 24, 11, 33, 5, 16, 28, 1, 22, 9, 35, 13, 26, 4, 18, 31, 0,
            21, 8, 29, 14, 3, 25, 12, 34, 6, 17, 27, 10, 23, 32, 15, 20]

MAPPA = {}
for _i, _c in enumerate(LETTERE + CIFRE):
    MAPPA[_c] = SEGNI[_MESCOLA[_i]]


def _base(c):
    """Le lettere accentate si scrivono come la loro vocale: l'alfabeto non ha accenti."""
    d = unicodedata.normalize("NFD", c)
    return "".join(x for x in d if unicodedata.category(x) != "Mn")


def trascrivi(testo):
    """Il testo in simboli. Spazi, a capo e punteggiatura restano come sono: e' quello che
       fa sembrare un documento un documento, invece di un blocco di rumore."""
    fuori = []
    for c in testo:
        b = _base(c).upper()
        fuori.append(MAPPA.get(b, c) if len(b) == 1 else c)
    return "".join(fuori)


def tabella():
    """La corrispondenza, da tenere per te: serve se un giocatore vuole provare a mano."""
    righe = ["| segno | lettera | segno | lettera | segno | lettera |", "|---|---|---|---|---|---|"]
    voci = [(MAPPA[c], c) for c in LETTERE + CIFRE]
    for i in range(0, len(voci), 3):
        righe.append("| " + " | ".join("%s | %s" % v for v in voci[i:i + 3]) + " |")
    return "\n".join(righe)


# ------------------------------------------------------------------ guardie
def controlla():
    """Tutti i motivi per cui questo alfabeto non andrebbe bene. Lista vuota = ok."""
    guai = []
    if len(set(SEGNI)) != len(SEGNI):
        guai.append("due segni uguali nell'alfabeto")
    if len(SEGNI) < len(LETTERE) + len(CIFRE):
        guai.append("i segni non bastano: %d per %d caratteri" % (len(SEGNI), len(LETTERE) + len(CIFRE)))
    if sorted(_MESCOLA) != list(range(len(LETTERE) + len(CIFRE))):
        guai.append("il mescolamento non e' una permutazione")
    if len(set(MAPPA.values())) != len(MAPPA):
        guai.append("due caratteri finiscono sullo stesso segno")
    doppi = set(SEGNI) & set(MONDI)
    if doppi:
        guai.append("un segno dell'alfabeto e' anche un simbolo di mondo: " + "".join(sorted(doppi)))
    if len(set(LETTERE)) != len(LETTERE):
        guai.append("una lettera compare due volte")
    return guai


if __name__ == "__main__":
    guai = controlla()
    if guai:
        print("\n  L'ALFABETO NON VA:")
        for g in guai:
            print("   -", g)
        raise SystemExit(1)
    print("\n# L'alfabeto di simboli\n")
    print(tabella())
    print("\n## Una prova\n")
    p = "Bolla di carico 76530000023"
    print("  ", p)
    print("  ", trascrivi(p))
    print()
