# -*- coding: utf-8 -*-
"""Le icone dell'app, disegnate qui invece che importate.

Il marchio e' quello dell'intestazione della pagina: un anello con la brace dentro.
Si scrivono PNG a mano con zlib (sta nella libreria standard): cosi' il progetto non
ha bisogno ne' di Pillow ne' di file binari versionati.

    python fai_icone.py
"""
import os
import struct
import zlib

QUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(QUI, "app", "src", "main", "res")
FONDO = (0x0B, 0x0C, 0x10)
BRACE = (0xF0, 0x8A, 0x4B)
# mipmap classiche: densita' -> lato in pixel
DENSITA = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def png(larghezza, righe):
    """righe = lista di liste di (r,g,b). -> bytes di un PNG RGB a 8 bit."""
    grezzo = b"".join(b"\x00" + bytes(v for px in r for v in px) for r in righe)

    def pezzo(tipo, dati):
        return (struct.pack(">I", len(dati)) + tipo + dati
                + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + pezzo(b"IHDR", struct.pack(">IIBBBBB", larghezza, len(righe), 8, 2, 0, 0, 0))
            + pezzo(b"IDAT", zlib.compress(grezzo, 9))
            + pezzo(b"IEND", b""))


def disegna(lato, pieno):
    """L'anello con la brace. pieno=True riempie il fondo (icona classica),
       pieno=False lo lascia scuro lo stesso: l'adaptive icon ha il suo sfondo."""
    c = (lato - 1) / 2.0
    r_est = lato * 0.34                                  # raggio esterno dell'anello
    spessore = max(1.0, lato * 0.055)
    r_int = r_est - spessore
    r_brace = lato * 0.15
    righe = []
    for y in range(lato):
        riga = []
        for x in range(lato):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            if d <= r_brace or (r_int <= d <= r_est):
                riga.append(BRACE)
            else:
                riga.append(FONDO if pieno else FONDO)
        righe.append(riga)
    return righe


def scrivi(path, dati):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(dati)
    return path


def main():
    fatti = []
    for nome, lato in DENSITA.items():
        d = png(lato, disegna(lato, True))
        fatti.append(scrivi(os.path.join(RES, "mipmap-" + nome, "ic_launcher.png"), d))
        fatti.append(scrivi(os.path.join(RES, "mipmap-" + nome, "ic_launcher_round.png"), d))
    # il primo piano dell'adaptive icon: il sistema ne ritaglia il 72% centrale,
    # quindi il marchio si disegna piu' piccolo su una tela piu' grande
    for nome, lato in DENSITA.items():
        grande = int(lato * 1.5)
        c = (grande - 1) / 2.0
        r_est, spess = grande * 0.22, max(1.0, grande * 0.036)
        r_int, r_brace = r_est - spess, grande * 0.098
        righe = []
        for y in range(grande):
            riga = []
            for x in range(grande):
                d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
                riga.append(BRACE if (d <= r_brace or r_int <= d <= r_est) else FONDO)
            righe.append(riga)
        fatti.append(scrivi(os.path.join(RES, "mipmap-" + nome, "ic_fg.png"), png(grande, righe)))
    print("  %d icone scritte sotto %s" % (len(fatti), os.path.relpath(RES, QUI)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
