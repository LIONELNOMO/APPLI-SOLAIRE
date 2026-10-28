"""Connexion à la base et session SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..config import ParamsBase

_moteur: Engine | None = None
_Session: sessionmaker[Session] | None = None


def _activer_cles_etrangeres(connexion, _record) -> None:
    """SQLite n'applique pas les clés étrangères par défaut."""
    curseur = connexion.cursor()
    curseur.execute("PRAGMA foreign_keys=ON")
    curseur.close()


def _normaliser(url: str) -> str:
    """Rend l'URL utilisable par SQLAlchemy 2.

    Render, Heroku et Koyeb distribuent une URL en `postgres://`, un
    préfixe que SQLAlchemy 2 ne reconnaît plus. Le pilote attendu ici est
    psycopg 3, d'où `postgresql+psycopg`.
    """
    for prefixe in ("postgres://", "postgresql://"):
        if url.startswith(prefixe):
            return "postgresql+psycopg://" + url[len(prefixe):]
    return url


def creer_moteur(url: str | None = None) -> Engine:
    """Crée le moteur SQLAlchemy et prépare le dossier de la base SQLite."""
    params = ParamsBase()
    url_finale = _normaliser(url or params.database_url)

    options: dict[str, object] = {"future": True, "pool_pre_ping": True}
    if url_finale.startswith("sqlite"):
        # Le sidecar sert plusieurs requêtes depuis des fils différents.
        options["connect_args"] = {"check_same_thread": False}
        chemin = url_finale.split("///", 1)[-1]
        if chemin and chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)

    moteur = create_engine(url_finale, **options)
    if url_finale.startswith("sqlite"):
        event.listen(moteur, "connect", _activer_cles_etrangeres)
    return moteur


def moteur() -> Engine:
    global _moteur
    if _moteur is None:
        _moteur = creer_moteur()
    return _moteur


def fabrique_session() -> sessionmaker[Session]:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=moteur(), expire_on_commit=False, future=True)
    return _Session


def reinitialiser(url: str | None = None) -> Engine:
    """Remplace le moteur courant. Réservé aux tests et au démarrage."""
    global _moteur, _Session
    _moteur = creer_moteur(url)
    _Session = sessionmaker(bind=_moteur, expire_on_commit=False, future=True)
    return _moteur


@contextmanager
def session_portee() -> Iterator[Session]:
    """Session transactionnelle : commit en sortie, rollback en cas d'erreur."""
    session = fabrique_session()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def obtenir_session() -> Iterator[Session]:
    """Dépendance FastAPI."""
    session = fabrique_session()()
    try:
        yield session
    finally:
        session.close()
