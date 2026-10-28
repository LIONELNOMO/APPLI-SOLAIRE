"""Création des tables et chargement des catalogues au premier démarrage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .modeles import (
    Base,
    BatterieDb,
    EquipementDb,
    MetaDb,
    OnduleurDb,
    PanneauDb,
)
from .session import moteur, session_portee

journal = logging.getLogger(__name__)

DOSSIER_SEED = Path(__file__).parent / "seed"
VERSION_SEED = "1.0.0"
CLE_VERSION_SEED = "version_seed"


def _charger(nom: str) -> list[dict[str, Any]]:
    chemin = DOSSIER_SEED / f"{nom}.json"
    if not chemin.exists():
        journal.warning("Catalogue absent : %s", chemin)
        return []
    with chemin.open(encoding="utf-8") as fichier:
        return json.load(fichier)


def _semer_panneaux(session) -> int:
    nombre = 0
    for fiche in _charger("panneaux"):
        session.merge(
            PanneauDb(
                id=fiche["id"],
                nom=fiche["nom"],
                fabricant=fiche.get("fabricant", ""),
                technologie=fiche.get("technologie", ""),
                pmax=fiche["pmax"],
                vmp=fiche["vmp"],
                imp=fiche["imp"],
                fiche=fiche,
                source="systeme",
            )
        )
        nombre += 1
    return nombre


def _semer_onduleurs(session) -> int:
    nombre = 0
    for fiche in _charger("onduleurs"):
        session.merge(
            OnduleurDb(
                id=fiche["id"],
                nom=fiche["nom"],
                fabricant=fiche.get("fabricant", ""),
                pnom_ac=fiche["pnom_ac"],
                u_ac=fiche.get("u_ac", 400.0),
                nb_mppt=fiche["nb_mppt"],
                fiche=fiche,
                source="systeme",
            )
        )
        nombre += 1
    return nombre


def _semer_batteries(session) -> int:
    nombre = 0
    for fiche in _charger("batteries"):
        session.merge(
            BatterieDb(
                id=fiche["id"],
                nom=fiche["nom"],
                fabricant=fiche.get("fabricant", ""),
                technologie=fiche.get("technologie", "lithium"),
                u_nom=fiche["u_nom"],
                capacite_ah=fiche["capacite_ah"],
                fiche=fiche,
                source="systeme",
            )
        )
        nombre += 1
    return nombre


def _semer_equipements(session) -> int:
    nombre = 0
    for fiche in _charger("equipements"):
        session.merge(
            EquipementDb(
                id=fiche["id"],
                nom=fiche["appareil"],
                fabricant="",
                categorie=fiche.get("categorie", ""),
                puissance_w=fiche["puissance_w"],
                fiche=fiche,
                source="systeme",
            )
        )
        nombre += 1
    return nombre


def semer(force: bool = False) -> dict[str, int]:
    """Charge les catalogues système si leur version a changé.

    Les fiches utilisateur ne sont jamais touchées.
    """
    with session_portee() as session:
        actuelle = session.get(MetaDb, CLE_VERSION_SEED)
        if actuelle is not None and actuelle.valeur == VERSION_SEED and not force:
            return {}

        comptes = {
            "panneaux": _semer_panneaux(session),
            "onduleurs": _semer_onduleurs(session),
            "batteries": _semer_batteries(session),
            "equipements": _semer_equipements(session),
        }
        session.merge(MetaDb(cle=CLE_VERSION_SEED, valeur=VERSION_SEED))
        journal.info("Catalogues chargés : %s", comptes)
        return comptes


def init_db(creer_tables: bool = True, charger_seed: bool = True) -> None:
    """Prépare la base au démarrage (modes `dev` et `desktop`).

    En mode `web`, les migrations Alembic sont lancées au déploiement.
    """
    if creer_tables:
        Base.metadata.create_all(bind=moteur())
    if charger_seed:
        semer()


def catalogue_systeme(session, table) -> list[dict[str, Any]]:
    """Fiches système d'un catalogue, triées par nom."""
    requete = select(table).where(table.actif.is_(True)).order_by(table.nom)
    return [ligne.fiche for ligne in session.scalars(requete)]
