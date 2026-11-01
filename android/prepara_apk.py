# -*- coding: utf-8 -*-
"""Mette l'app dentro il progetto Android, e controlla che non ci finisca altro.

Gli assets non stanno nel repository: si copiano qui prima di ogni build, cosi' l'APK
ha sempre l'ultimo dati.js e non si rischia di impacchettare una versione vecchia.

    python android/prepara_apk.py

Attenzione: l'APK che ne esce CONTIENE i testi in chiaro, frasi delle regole comprese.
Si manda ai tre giocatori e basta. Non si pubblica, non si mette su uno store.
"""
import os
import shutil
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
PROGETTO = os.path.dirname(QUI)
ASSETS = os.path.join(QUI, "app", "src", "main", "assets")

# Esattamente quello che index.html carica, niente di piu'.
FILE = ["index.html", "app.js", "cifrari.js", "dati.js", "jsQR.min.js"]


def main():
    sys.path.insert(0, PROGETTO)
    try:
        import costruisci as K
    except ImportError as e:
        print("\n  non riesco a importare costruisci.py: %s\n" % e)
        return 1

    manca = [f for f in FILE if not os.path.exists(os.path.join(PROGETTO, f))]
    if manca:
        print("\n  mancano: %s\n  Lancia prima  python costruisci.py\n" % ", ".join(manca))
        return 1

    segreti_f = os.path.join(PROGETTO, ".segreti")
    if not os.path.exists(segreti_f):
        print("\n  manca .segreti: lo scrive costruisci.py, e senza non posso controllare\n"
              "  che nell'APK non finisca una parola chiave.\n")
        return 1
    segreti = [s.strip() for s in open(segreti_f, encoding="utf-8").read().split("\n") if s.strip()]

    # la stessa guardia di costruisci.py, sugli stessi file ma guardati da qui
    vecchia = os.getcwd()
    os.chdir(PROGETTO)
    try:
        perdite = K.perdite_nei_file(segreti, FILE)
    finally:
        os.chdir(vecchia)
    if perdite:
        print("\n  NON PREPARO NIENTE - una parola chiave finirebbe dentro l'APK:\n")
        for p in perdite:
            print("   -", p)
        print()
        return 1

    if os.path.exists(ASSETS):
        shutil.rmtree(ASSETS)
    os.makedirs(ASSETS)
    peso = 0
    for f in FILE:
        shutil.copy2(os.path.join(PROGETTO, f), os.path.join(ASSETS, f))
        peso += os.path.getsize(os.path.join(ASSETS, f))

    print("\n  Assets pronti: %d file, %d KB" % (len(FILE), peso // 1024))
    print("  Nessuna parola chiave negli assets.")
    print("\n  Adesso:   cd android  &&  .\\gradlew assembleDebug")
    print("  L'APK esce in  android/app/build/outputs/apk/debug/app-debug.apk")
    print("\n  QUELL'APK CONTIENE I TESTI IN CHIARO. Mandalo ai tre giocatori e basta.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
