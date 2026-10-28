"""Recette de la version autonome : un seul serveur sert l'API et l'interface."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).parent.parent
EXE = RACINE / "backend" / "dist" / "dimsolaire-api.exe"
STATIQUE = RACINE / "frontend" / "dist"


def port_libre() -> int:
    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        return prise.getsockname()[1]


def obtenir(url: str, timeout: float = 30.0):
    with urllib.request.urlopen(url, timeout=timeout) as reponse:
        return reponse.status, reponse.read(), dict(reponse.headers)


def main() -> int:
    for chemin, quoi in ((EXE, "moteur compilé"), (STATIQUE / "index.html", "interface")):
        if not chemin.exists():
            print(f"  ECHEC : {quoi} absent — {chemin}")
            return 1

    port = port_libre()
    base = f"http://127.0.0.1:{port}"
    dossier = Path(tempfile.mkdtemp(prefix="dimsolaire-autonome-"))

    processus = subprocess.Popen(
        [
            str(EXE),
            "--port", str(port),
            "--db", str(dossier / "dimsolaire.db"),
            "--static", str(STATIQUE),
            "--log", str(dossier / "api.log"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        debut = time.monotonic()
        sante = None
        while time.monotonic() - debut < 40:
            try:
                _, corps, _ = obtenir(f"{base}/api/v1/health", timeout=2)
                sante = json.loads(corps)
                if sante.get("statut") == "ok":
                    break
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                pass
            time.sleep(0.25)

        if not sante or sante.get("statut") != "ok":
            print("  ECHEC : le moteur ne répond pas")
            return 1

        duree = time.monotonic() - debut
        print(f"  Démarrage              {duree:.2f} s")
        print(f"  Mode                   {sante['mode']} (attendu : web)")
        if sante["mode"] != "web":
            print("  ECHEC : le mode autonome n'est pas activé")
            return 1

        # --- L'interface doit être servie à la racine ---
        statut, corps, entetes = obtenir(f"{base}/")
        html = corps.decode("utf-8", errors="replace")
        print(f"  Interface à /          {statut}, {len(corps)} octets")
        if statut != 200 or "DimSolaire" not in html:
            print("  ECHEC : l'interface n'est pas servie correctement")
            return 1
        if "index-" not in html or ".js" not in html:
            print("  ECHEC : le script de l'interface n'est pas référencé")
            return 1
        print("  Titre et bundle        présents dans le HTML")

        # --- Les fichiers du build doivent être joignables ---
        for ligne in html.split('"'):
            if ligne.startswith("./assets/") and ligne.endswith(".js"):
                statut_actif, corps_actif, _ = obtenir(f"{base}/{ligne[2:]}")
                print(f"  Bundle JS              {statut_actif}, {len(corps_actif)} octets")
                if statut_actif != 200:
                    print("  ECHEC : le bundle n'est pas joignable")
                    return 1
                break

        # --- Sans jeton : le mode autonome n'en exige pas ---
        statut_cat, corps_cat, _ = obtenir(f"{base}/api/v1/catalogue/panneaux")
        panneaux = json.loads(corps_cat)
        print(f"  Catalogue sans jeton   {statut_cat}, {len(panneaux)} panneaux")
        if len(panneaux) != 14:
            print("  ECHEC : catalogue incomplet")
            return 1

        # --- Un calcul réel, depuis le projet par défaut ---
        _, corps_defaut, _ = obtenir(f"{base}/api/v1/projets/defaut")
        requete = urllib.request.Request(
            f"{base}/api/v1/calcul",
            data=corps_defaut,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            resultats = json.loads(reponse.read())
        print(f"  Calcul par défaut      statut {resultats['statut_global']}")

        # --- Le routage de l'interface ne doit pas casser l'API ---
        try:
            obtenir(f"{base}/api/v1/projets/inexistant")
            print("  ECHEC : une route API inconnue devrait renvoyer 404")
            return 1
        except urllib.error.HTTPError as erreur:
            if erreur.code != 404:
                print(f"  ECHEC : code {erreur.code} au lieu de 404")
                return 1
        print("  Routage API            préservé (404 sur route inconnue)")

        return 0

    finally:
        processus.terminate()
        try:
            processus.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processus.kill()


if __name__ == "__main__":
    print("\n" + "─" * 70)
    print("RECETTE DE LA VERSION AUTONOME")
    print("─" * 70)
    code = main()
    print("─" * 70)
    print("  RECETTE RÉUSSIE" if code == 0 else "  RECETTE EN ÉCHEC")
    print("─" * 70 + "\n")
    sys.exit(code)
