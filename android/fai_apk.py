# -*- coding: utf-8 -*-
"""Compila l'APK.

Perche' non si compila sul posto: il percorso del progetto contiene una &, e gli script
.bat di Gradle e dell'SDK la leggono come separatore di comandi e si rompono. Quindi i
sorgenti si copiano in una cartella di lavoro dal nome pulito, si compila li', e l'APK
torna indietro.

    python android/fai_apk.py            # debug, firmato con la chiave di debug
    python android/fai_apk.py --pulisci  # butta via la cartella di lavoro e ricomincia

Serve: JDK 17 e l'Android SDK. Se non li trova, dice dove li ha cercati.

L'APK che ne esce CONTIENE i testi in chiaro. Si manda ai giocatori, non si pubblica.
"""
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

QUI = os.path.dirname(os.path.abspath(__file__))
PROGETTO = os.path.dirname(QUI)
LAVORO = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                      "Temp", "emberloop-apk")
GRADLE = "8.10.2"
GRADLE_URL = "https://services.gradle.org/distributions/gradle-%s-bin.zip" % GRADLE
# cosa si copia nella cartella di lavoro: i sorgenti, non le build vecchie
SORGENTI = ["settings.gradle", "build.gradle", "gradle.properties", "app"]
SALTA = {"build", ".gradle", "__pycache__"}


def trova_jdk():
    for v in (os.environ.get("JAVA_HOME"),):
        if v and os.path.exists(os.path.join(v, "bin", "java.exe")):
            return v
    base = r"C:\Program Files\Eclipse Adoptium"
    if os.path.isdir(base):
        for n in sorted(os.listdir(base), reverse=True):
            if n.startswith("jdk-17") and os.path.exists(os.path.join(base, n, "bin", "java.exe")):
                return os.path.join(base, n)
    return None


def trova_sdk():
    for v in (os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
              r"C:\Android\Sdk",
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk")):
        if v and os.path.isdir(os.path.join(v, "platforms")):
            return v
    return None


def prendi_gradle():
    """-> la cartella di gradle, scaricandolo la prima volta."""
    casa = os.path.join(os.path.dirname(LAVORO), "gradle-" + GRADLE)
    if os.path.exists(os.path.join(casa, "bin", "gradle.bat")):
        return casa
    zipname = casa + ".zip"
    if not os.path.exists(zipname):
        print("  scarico Gradle %s (una volta sola, ~130 MB)..." % GRADLE)
        os.makedirs(os.path.dirname(zipname), exist_ok=True)
        urllib.request.urlretrieve(GRADLE_URL, zipname)
    print("  scompatto Gradle...")
    with zipfile.ZipFile(zipname) as z:
        z.extractall(os.path.dirname(casa))
    return casa


def copia_sorgenti():
    if os.path.exists(LAVORO):
        shutil.rmtree(LAVORO)
    os.makedirs(LAVORO)
    for n in SORGENTI:
        src = os.path.join(QUI, n)
        if not os.path.exists(src):
            return "manca %s" % n
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(LAVORO, n),
                            ignore=shutil.ignore_patterns(*SALTA))
        else:
            shutil.copy2(src, os.path.join(LAVORO, n))
    return None


def main():
    if "--pulisci" in sys.argv:
        for d in (LAVORO,):
            if os.path.exists(d):
                shutil.rmtree(d)
                print("  buttata via", d)
        return 0

    jdk, sdk = trova_jdk(), trova_sdk()
    if not jdk:
        print("\n  JDK 17 non trovato. Installalo:\n"
              "     winget install EclipseAdoptium.Temurin.17.JDK\n"
              "  oppure imposta JAVA_HOME.\n")
        return 1
    if not sdk:
        print("\n  Android SDK non trovato. L'ho cercato in ANDROID_HOME, C:\\Android\\Sdk e\n"
              "  %LOCALAPPDATA%\\Android\\Sdk. Serve platforms;android-35 e build-tools;35.0.0.\n")
        return 1
    print("\n  JDK: %s\n  SDK: %s" % (jdk, sdk))

    # 1. gli assets, con la guardia anti-fuga
    r = subprocess.run([sys.executable, os.path.join(QUI, "prepara_apk.py")])
    if r.returncode != 0:
        return r.returncode

    # 2. i sorgenti in una cartella dal nome pulito (la & del percorso rompe i .bat)
    guaio = copia_sorgenti()
    if guaio:
        print("\n  %s\n" % guaio)
        return 1
    with open(os.path.join(LAVORO, "local.properties"), "w", encoding="utf-8") as f:
        f.write("sdk.dir=" + sdk.replace("\\", "\\\\") + "\n")

    # 3. gradle
    casa = prendi_gradle()
    amb = dict(os.environ, JAVA_HOME=jdk, ANDROID_HOME=sdk, ANDROID_SDK_ROOT=sdk)
    amb.pop("ANDROID_NDK_HOME", None)
    print("  compilo...\n")
    r = subprocess.run([os.path.join(casa, "bin", "gradle.bat"), "assembleDebug",
                        "--no-daemon", "--console=plain"],
                       cwd=LAVORO, env=amb)
    if r.returncode != 0:
        print("\n  La compilazione e' fallita. L'errore sta qui sopra.\n")
        return r.returncode

    # 4. l'APK torna a casa
    fuori = os.path.join(LAVORO, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if not os.path.exists(fuori):
        print("\n  Gradle dice ok ma l'APK non c'e': %s\n" % fuori)
        return 1
    dove = os.path.join(QUI, "EmberLoop.apk")
    shutil.copy2(fuori, dove)
    print("\n  FATTO: %s  (%d KB)" % (dove, os.path.getsize(dove) // 1024))
    print("\n  Mandalo ai tre giocatori. Sul telefono: apri il file, Android chiede di\n"
          "  permettere l'installazione da quella app - una volta sola - e poi installa.")
    print("  DENTRO CI SONO I TESTI IN CHIARO: non pubblicarlo da nessuna parte.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
