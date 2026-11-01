# -*- coding: utf-8 -*-
"""Un QR disegnato nel terminale, per far entrare i telefoni senza digitare l'indirizzo.

Lo chiama servi.ps1 dopo aver trovato l'IP del PC. I telefoni lo inquadrano con la
fotocamera normale: Android apre Chrome da solo.

    python qr_terminale.py http://192.168.1.37:8000/prova-offline.html

I moduli scuri del QR si disegnano come spazi e i chiari come blocchi pieni: in un
terminale scuro viene scuro-su-chiaro, che e' il verso che i lettori si aspettano.
Due caratteri per modulo in larghezza, mezzo blocco in altezza: cosi' resta quadrato
e ci sta in 80 colonne.
"""
import sys


def disegna(testo, uscita=sys.stdout):
    try:
        import qrcode
    except ImportError:
        uscita.write("  (per il QR nel terminale serve:  pip install qrcode)\n")
        return False
    q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    q.add_data(testo)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    # due righe di moduli per riga di testo: mezzo blocco sopra e mezzo sotto
    PIENO, ALTO, BASSO, VUOTO = "██", "▀▀", "▄▄", "  "
    for r in range(0, n, 2):
        riga = []
        for c in range(n):
            su = m[r][c]                                   # True = modulo scuro
            giu = m[r + 1][c] if r + 1 < n else False
            riga.append(VUOTO if (su and giu) else BASSO if su else ALTO if giu else PIENO)
        uscita.write("  " + "".join(riga) + "\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python qr_terminale.py <indirizzo>")
        sys.exit(2)
    try:
        sys.stdout.reconfigure(encoding="utf-8")           # i blocchi non passano in cp1252
    except AttributeError:
        pass
    sys.exit(0 if disegna(sys.argv[1]) else 1)
