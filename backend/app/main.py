"""Fabrique de l'application FastAPI (§20.6 des annexes)."""

from __future__ import annotations

import hmac
import logging
from base64 import b64decode
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .api.v1 import routeur
from .config import Settings
from .db.init import init_db
from .engine.modeles import VERSION_MOTEUR

journal = logging.getLogger("dimsolaire")

ROUTES_LIBRES = frozenset({"/api/v1/health", "/openapi.json", "/docs", "/redoc"})

# La route de santé reste ouverte : l'hébergeur la sonde sans identifiants.
ROUTES_LIBRES_WEB = frozenset({"/api/v1/health"})


def _mot_de_passe_fourni(entete: str | None, attendu: str) -> bool:
    """Vérifie un en-tête `Authorization: Basic …`.

    L'identifiant est ignoré, seul le mot de passe compte : il n'y a qu'un
    secret partagé, pas de comptes. La comparaison passe par `hmac` pour
    que sa durée ne dépende pas du nombre de caractères justes.
    """
    if not entete or not entete.startswith("Basic "):
        return False
    try:
        decode = b64decode(entete[6:], validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    _, separateur, motdepasse = decode.partition(":")
    if not separateur:
        return False
    return hmac.compare_digest(motdepasse, attendu)


def _configurer_journal(cfg: Settings) -> None:
    niveau = logging.INFO
    if cfg.log_file:
        chemin = Path(cfg.log_file)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=niveau,
            filename=str(chemin),
            encoding="utf-8",
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        logging.basicConfig(level=niveau)


def create_app() -> FastAPI:
    cfg = Settings()
    _configurer_journal(cfg)

    app = FastAPI(
        title="DimSolaire API",
        version=VERSION_MOTEUR,
        description=(
            "Moteur de dimensionnement photovoltaïque et d'injection au réseau. "
            "La route de calcul ne renvoie jamais d'erreur pour une valeur "
            "métier : les problèmes sont des messages dans la réponse."
        ),
    )

    if cfg.jeton_requis:

        async def verifier_jeton(
            request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            if (
                request.method != "OPTIONS"
                and request.url.path not in ROUTES_LIBRES
                and request.headers.get("x-app-token") != cfg.token
            ):
                return JSONResponse({"detail": "Jeton invalide"}, status_code=401)
            return await call_next(request)

        app.add_middleware(BaseHTTPMiddleware, dispatch=verifier_jeton)

    if cfg.mot_de_passe_requis:

        async def verifier_mot_de_passe(
            request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            if request.method == "OPTIONS" or request.url.path in ROUTES_LIBRES_WEB:
                return await call_next(request)
            if _mot_de_passe_fourni(
                request.headers.get("authorization"), cfg.mot_de_passe
            ):
                return await call_next(request)
            # `WWW-Authenticate` déclenche la fenêtre de saisie du
            # navigateur : aucune page de connexion n'est à écrire.
            return JSONResponse(
                {"detail": "Mot de passe requis"},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="DimSolaire"'},
            )

        app.add_middleware(BaseHTTPMiddleware, dispatch=verifier_mot_de_passe)

    # Ajouté en dernier, donc le plus extérieur : les réponses 401 portent
    # aussi les en-têtes CORS, sinon le navigateur masquerait le motif.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.origines_cors(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Les tables sont créées au démarrage dans tous les modes.
    # `create_all` ne touche pas aux tables déjà présentes : au deuxième
    # démarrage, rien n'est recréé et les données restent en place.
    #
    # Aucune migration Alembic n'est écrite à ce jour. Le jour où le
    # schéma évoluera sur une base contenant des projets, il faudra en
    # écrire : `create_all` ne sait pas modifier une table existante.
    init_db(creer_tables=True)

    app.include_router(routeur, prefix="/api/v1")

    if cfg.mode == "web":
        dossier = Path(cfg.static_dir)
        if dossier.is_dir():
            app.mount("/", StaticFiles(directory=str(dossier), html=True), name="static")
        else:
            journal.warning("Dossier statique absent : %s", dossier)

    if cfg.mode == "web" and not cfg.mot_de_passe:
        journal.warning(
            "Aucun mot de passe : le service est ouvert à tous. "
            "Définissez DIMSOLAIRE_MOT_DE_PASSE avant de l'exposer."
        )

    journal.info(
        "DimSolaire démarré en mode %s (accès %s)",
        cfg.mode,
        "protégé" if cfg.mot_de_passe_requis else "libre",
    )
    return app
