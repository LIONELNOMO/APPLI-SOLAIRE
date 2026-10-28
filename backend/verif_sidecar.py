"""Recette de l'exécutable du moteur, tel qu'il sera livré avec la version PC.

Reproduit exactement ce que fait Tauri : port libre, jeton de session,
surveillance du parent, puis appels au moteur.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

EXE = Path(__file__).parent / "dist" / "dimsolaire-api.exe"


def port_libre() -> int:
    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        return prise.getsockname()[1]


def appel(base: str, chemin: str, jeton: str, charge=None, methode="GET"):
    donnees = json.dumps(charge).encode() if charge is not None else None
    requete = urllib.request.Request(
        f"{base}/api/v1{chemin}",
        data=donnees,
        method=methode,
        headers={"Content-Type": "application/json", "X-App-Token": jeton},
    )
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        brut = reponse.read()
        if reponse.headers.get("Content-Type", "").startswith("application/pdf"):
            return brut
        return json.loads(brut) if brut else None


def main() -> int:
    if not EXE.exists():
        print(f"ECHEC : exécutable absent — {EXE}")
        return 1

    taille_mo = EXE.stat().st_size / 1024 / 1024
    port = port_libre()
    jeton = uuid.uuid4().hex
    base_url = f"http://127.0.0.1:{port}"

    dossier = Path(tempfile.mkdtemp(prefix="dimsolaire-recette-"))
    base_donnees = dossier / "dimsolaire.db"
    journal = dossier / "api.log"

    environnement = {**os.environ, "DIMSOLAIRE_TOKEN": jeton}
    processus = subprocess.Popen(
        [
            str(EXE),
            "--port", str(port),
            "--db", str(base_donnees),
            "--parent-pid", str(os.getpid()),
            "--log", str(journal),
        ],
        env=environnement,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(f"  Exécutable              {taille_mo:.1f} Mo")
    print(f"  Port réservé            {port}")
    print(f"  Jeton de session        {jeton[:12]}…")

    try:
        # --- Attente du démarrage, comme l'interface Tauri ---
        debut = time.monotonic()
        pret = False
        while time.monotonic() - debut < 30:
            try:
                sante = appel(base_url, "/health", jeton)
                if sante and sante.get("statut") == "ok":
                    pret = True
                    break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                pass
            time.sleep(0.25)

        if not pret:
            print("  ECHEC : le moteur ne répond pas sur /health")
            return 1

        duree = time.monotonic() - debut
        print(f"  Démarrage               {duree:.2f} s "
              f"(mode {sante['mode']}, version {sante['version']})")

        # --- Le jeton doit être exigé ---
        try:
            requete = urllib.request.Request(f"{base_url}/api/v1/catalogue/panneaux")
            urllib.request.urlopen(requete, timeout=10)
            print("  ECHEC : le jeton n'est pas exigé")
            return 1
        except urllib.error.HTTPError as erreur:
            if erreur.code != 401:
                print(f"  ECHEC : code {erreur.code} au lieu de 401 sans jeton")
                return 1
        print("  Jeton exigé             oui (401 sans en-tête)")

        # --- Catalogues chargés au premier lancement ---
        comptes = {}
        for nom in ("panneaux", "onduleurs", "batteries", "equipements"):
            comptes[nom] = len(appel(base_url, f"/catalogue/{nom}", jeton))
        attendus = {"panneaux": 14, "onduleurs": 7, "batteries": 10, "equipements": 22}
        if comptes != attendus:
            print(f"  ECHEC : catalogues {comptes} au lieu de {attendus}")
            return 1
        print(f"  Catalogues             {comptes}")

        # --- Calcul complet d'un cas de référence ---
        sys.path.insert(0, str(Path(__file__).parent))
        from tests.engine.cas import projet_reference

        entree = projet_reference("R-10").model_dump(mode="json")
        resultats = appel(base_url, "/calcul", jeton, entree, "POST")
        pv = resultats["pv"]["valeurs"]
        inj = resultats["injection"]["valeurs"]
        if pv["n_total"] != 1582:
            print(f"  ECHEC : {pv['n_total']} panneaux au lieu de 1 582")
            return 1
        print(f"  Calcul R-10            {pv['n_total']} panneaux, "
              f"{pv['pc_installee_kwc']:.1f} kWc, {inj['n_tr']} transformateurs")
        print(f"  Énergie injectée       {inj['e_inj_an_kwh'] / 1000:.0f} MWh/an")

        # --- Enregistrement, export, réimport ---
        projet = appel(base_url, "/projets", jeton, entree, "POST")
        identifiant = projet["id"]
        export = appel(base_url, f"/projets/{identifiant}/export", jeton)
        reimport = appel(base_url, "/projets/import", jeton, export, "POST")
        if not reimport["empreinte_valide"]:
            print("  ECHEC : empreinte invalide au réimport")
            return 1
        print("  Export et réimport     empreinte vérifiée")

        # --- Rapport PDF ---
        pdf = appel(base_url, f"/projets/{identifiant}/rapport.pdf", jeton)
        if not pdf.startswith(b"%PDF"):
            print("  ECHEC : le rapport n'est pas un PDF")
            return 1
        print(f"  Rapport PDF            {len(pdf)} octets")

        chemin_pdf = dossier / "rapport.pdf"
        chemin_pdf.write_bytes(pdf)

        # --- Persistance de la base ---
        if not base_donnees.exists():
            print("  ECHEC : base SQLite non créée")
            return 1
        print(f"  Base SQLite            {base_donnees.stat().st_size / 1024:.0f} Ko")

        if journal.exists():
            print(f"  Journal                {journal.stat().st_size} octets")

        print(f"\n  Rapport conservé pour inspection : {chemin_pdf}")
        return 0

    finally:
        processus.terminate()
        try:
            processus.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processus.kill()


if __name__ == "__main__":
    print("\n" + "─" * 70)
    print("RECETTE DU MOTEUR COMPILÉ (version PC)")
    print("─" * 70)
    code = main()
    print("─" * 70)
    print("  RECETTE RÉUSSIE" if code == 0 else "  RECETTE EN ÉCHEC")
    print("─" * 70 + "\n")
    sys.exit(code)
