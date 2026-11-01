# -*- coding: utf-8 -*-
"""Serve la cartella corrente in https, con un certificato fatto in casa.

Perche' esiste: i browser danno la fotocamera solo in "contesto sicuro". http://192.168.x.x
non lo e', quindi dalla rete di casa in http lo scanner QR non parte e i giocatori devono
digitare il codice stampato sotto il sigillo. In https parte - a patto che sul telefono si
accetti una volta l'avviso del certificato (Avanzate -> Procedi).

Lo lancia servi.ps1 -Https. Il certificato vale 30 giorni e sta in .cert/, che e' in
.gitignore: e' legato all'indirizzo IP del PC, quindi si rifa' se l'indirizzo cambia.

    python servi_tls.py <porta> <cartella-cert> <ip>
"""
import os
import ssl
import subprocess
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler


def trova_openssl():
    """openssl arriva con Git per Windows ma non finisce nel PATH: lo si cerca accanto
       a git, che nel PATH c'e' quasi sempre."""
    import shutil
    trovato = shutil.which("openssl")
    if trovato:
        return trovato
    git = shutil.which("git")
    if git:
        radice = os.path.dirname(os.path.dirname(git))          # ...\Git\cmd\git.exe -> ...\Git
        for sotto in ("usr/bin", "mingw64/bin", "ucrt64/bin", "mingw32/bin"):
            c = os.path.join(radice, sotto.replace("/", os.sep), "openssl.exe")
            if os.path.exists(c):
                return c
    for radice in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        for sotto in ("Git/usr/bin", "Git/mingw64/bin", "Git/ucrt64/bin"):
            c = os.path.join(radice, sotto.replace("/", os.sep), "openssl.exe")
            if radice and os.path.exists(c):
                return c
    return None


def fai_certificato(cartella, ip):
    """-> (cert, chiave) oppure (None, perche')."""
    cert = os.path.join(cartella, "cert.pem")
    chiave = os.path.join(cartella, "key.pem")
    marca = os.path.join(cartella, "per.txt")
    if (os.path.exists(cert) and os.path.exists(chiave) and os.path.exists(marca)
            and open(marca, encoding="utf-8").read().strip() == ip):
        return cert, chiave
    exe = trova_openssl()
    if not exe:
        return None, ("openssl non si trova. Arriva con Git per Windows: se Git c'e', cercalo in\n"
                      "     ...\\Git\\usr\\bin\\openssl.exe e mettilo nel PATH. Oppure servi in http,\n"
                      "     senza -Https: funziona tutto tranne lo scanner.")
    os.makedirs(cartella, exist_ok=True)
    cmd = [exe, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30",
           "-keyout", chiave, "-out", cert, "-subj", "/CN=" + ip,
           "-addext", "subjectAltName=IP:%s,IP:127.0.0.1,DNS:localhost" % ip]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        return None, "non riesco a lanciare %s: %s" % (exe, e)
    if r.returncode != 0:
        return None, "openssl ha risposto male:\n     " + (r.stderr or "").strip()[:300]
    open(marca, "w", encoding="utf-8").write(ip + "\n")
    return cert, chiave


class Silenzioso(SimpleHTTPRequestHandler):
    """Un errore TLS per ogni telefono che rifiuta il certificato riempirebbe lo schermo."""
    def log_message(self, fmt, *a):
        if "code 400" not in (fmt % a):
            sys.stderr.write("  %s\n" % (fmt % a))


def main():
    if len(sys.argv) < 4:
        print("uso: python servi_tls.py <porta> <cartella-cert> <ip>")
        return 2
    porta, cartella, ip = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    cert, chiave = fai_certificato(cartella, ip)
    if cert is None:
        print("\n  NON POSSO SERVIRE IN HTTPS: %s\n" % chiave)
        return 1
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, chiave)
    srv = HTTPServer(("0.0.0.0", porta), partial(Silenzioso, directory=os.getcwd()))
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  server fermato.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
