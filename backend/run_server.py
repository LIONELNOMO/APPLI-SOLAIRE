"""Point d'entrée du sidecar de la version PC (§20.7 des annexes).

Lancé par Tauri avec un port libre, le chemin de la base et le PID du parent.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

INTERVALLE_SURVEILLANCE_S = 2.0


def surveiller_parent(pid: int) -> None:
    """Arrête l'API si Tauri disparaît, pour ne jamais laisser d'orphelin.

    Tauri tue normalement le sidecar à la fermeture, mais pas s'il plante
    lui-même. `os._exit` est délibéré : il court-circuite les gestionnaires
    de sortie d'un serveur qui n'a plus de client.
    """
    import psutil

    while True:
        if not psutil.pid_exists(pid):
            os._exit(0)
        time.sleep(INTERVALLE_SURVEILLANCE_S)


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Moteur de calcul DimSolaire")
    analyseur.add_argument("--port", type=int, required=True)
    analyseur.add_argument("--db", required=True, help="Chemin du fichier SQLite")
    analyseur.add_argument("--parent-pid", type=int, default=None)
    analyseur.add_argument("--log", default=None, help="Fichier journal")
    analyseur.add_argument(
        "--static",
        default=None,
        help="Dossier du build de l'interface. Fourni, le serveur sert aussi "
        "l'interface et aucun jeton n'est exigé : c'est le mode autonome.",
    )
    arguments = analyseur.parse_args()

    chemin_base = Path(arguments.db)
    chemin_base.parent.mkdir(parents=True, exist_ok=True)

    # L'environnement doit être posé avant l'import de l'application.
    # Un dossier statique, passé en argument ou par l'environnement, place
    # le serveur en mode autonome : il sert l'interface et l'API ensemble.
    dossier_statique = arguments.static or os.environ.get("DIMSOLAIRE_STATIC_DIR")
    if dossier_statique and Path(dossier_statique).is_dir():
        os.environ["DIMSOLAIRE_MODE"] = "web"
        os.environ["DIMSOLAIRE_STATIC_DIR"] = dossier_statique
    else:
        os.environ["DIMSOLAIRE_MODE"] = "desktop"

    os.environ["DATABASE_URL"] = f"sqlite:///{chemin_base.as_posix()}"
    if arguments.log:
        os.environ["DIMSOLAIRE_LOG_FILE"] = arguments.log

    if arguments.parent_pid:
        threading.Thread(
            target=surveiller_parent,
            args=(arguments.parent_pid,),
            daemon=True,
        ).start()

    import uvicorn

    from app.main import create_app

    # Tauri lit cette ligne pour savoir que le démarrage a commencé.
    print(f"DimSolaire : démarrage sur 127.0.0.1:{arguments.port}", flush=True)

    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=arguments.port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
