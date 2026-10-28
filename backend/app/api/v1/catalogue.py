"""Routes des catalogues d'équipement."""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.modeles import TABLES_CATALOGUE
from ...db.session import obtenir_session
from ...engine.batteries import fiche_batterie_valide
from ...engine.champ_pv import fiche_panneau_valide
from ...engine.modeles import Batterie, Equipement, Onduleur, Panneau
from ...engine.onduleur import fiche_onduleur_valide

routeur = APIRouter(prefix="/catalogue")

TypeCatalogue = Literal["panneaux", "onduleurs", "batteries", "equipements"]

MODELES = {
    "panneaux": Panneau,
    "onduleurs": Onduleur,
    "batteries": Batterie,
    "equipements": Equipement,
}

VALIDATEURS = {
    "panneaux": fiche_panneau_valide,
    "onduleurs": fiche_onduleur_valide,
    "batteries": fiche_batterie_valide,
    "equipements": lambda e: e.puissance_w > 0
    and 0 <= e.heures_j <= 24
    and 0 <= e.ks <= 1
    and e.quantite_defaut >= 0
    and bool(e.appareil.strip()),
}

MOTIF_SLUG = re.compile(r"^[a-z0-9-]+$")


def _valider(type_catalogue: str, charge: dict[str, Any]):
    """Valide le type puis la cohérence métier de la fiche (§8.5)."""
    modele = MODELES[type_catalogue]
    try:
        fiche = modele.model_validate(charge)
    except ValidationError as erreur:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Fiche invalide", "erreurs": erreur.errors()},
        ) from erreur

    if not MOTIF_SLUG.match(fiche.id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Identifiant invalide",
                "champs": ["id"],
                "attendu": "lettres minuscules, chiffres et tirets",
            },
        )
    if not VALIDATEURS[type_catalogue](fiche):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Fiche incohérente : vérifier les valeurs électriques",
                "type": type_catalogue,
            },
        )
    return fiche


def _colonnes(type_catalogue: str, fiche) -> dict[str, Any]:
    """Colonnes de filtrage dupliquées hors du JSON."""
    if type_catalogue == "panneaux":
        return {
            "technologie": fiche.technologie,
            "pmax": fiche.pmax,
            "vmp": fiche.vmp,
            "imp": fiche.imp,
        }
    if type_catalogue == "onduleurs":
        return {
            "pnom_ac": fiche.pnom_ac,
            "u_ac": fiche.u_ac,
            "nb_mppt": fiche.nb_mppt,
        }
    if type_catalogue == "batteries":
        return {
            "technologie": fiche.technologie,
            "u_nom": fiche.u_nom,
            "capacite_ah": fiche.capacite_ah,
        }
    return {"categorie": fiche.categorie, "puissance_w": fiche.puissance_w}


def _nom(type_catalogue: str, fiche) -> str:
    return fiche.appareil if type_catalogue == "equipements" else fiche.nom


@routeur.get("/{type_catalogue}")
def lister(
    type_catalogue: TypeCatalogue,
    fabricant: str | None = None,
    recherche: str | None = None,
    session: Session = Depends(obtenir_session),
) -> list[dict[str, Any]]:
    table = TABLES_CATALOGUE[type_catalogue]
    requete = select(table).where(table.actif.is_(True)).order_by(table.nom)
    if fabricant:
        requete = requete.where(table.fabricant == fabricant)

    fiches = [ligne.fiche for ligne in session.scalars(requete)]
    if recherche:
        terme = recherche.lower()
        fiches = [
            f
            for f in fiches
            if terme in str(f.get("nom", "")).lower()
            or terme in str(f.get("appareil", "")).lower()
            or terme in str(f.get("fabricant", "")).lower()
        ]
    return fiches


@routeur.get("/{type_catalogue}/{identifiant}")
def lire(
    type_catalogue: TypeCatalogue,
    identifiant: str,
    session: Session = Depends(obtenir_session),
) -> dict[str, Any]:
    table = TABLES_CATALOGUE[type_catalogue]
    ligne = session.get(table, identifiant)
    if ligne is None or not ligne.actif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fiche introuvable")
    return ligne.fiche


@routeur.post("/{type_catalogue}", status_code=status.HTTP_201_CREATED)
def creer(
    type_catalogue: TypeCatalogue,
    charge: dict[str, Any],
    session: Session = Depends(obtenir_session),
) -> dict[str, Any]:
    fiche = _valider(type_catalogue, charge)
    table = TABLES_CATALOGUE[type_catalogue]

    if session.get(table, fiche.id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"L'identifiant « {fiche.id} » existe déjà",
        )

    donnees = fiche.model_dump(mode="json")
    donnees["source"] = "utilisateur"
    session.add(
        table(
            id=fiche.id,
            nom=_nom(type_catalogue, fiche),
            fabricant=getattr(fiche, "fabricant", ""),
            fiche=donnees,
            source="utilisateur",
            **_colonnes(type_catalogue, fiche),
        )
    )
    session.commit()
    return donnees


@routeur.put("/{type_catalogue}/{identifiant}")
def modifier(
    type_catalogue: TypeCatalogue,
    identifiant: str,
    charge: dict[str, Any],
    session: Session = Depends(obtenir_session),
) -> dict[str, Any]:
    table = TABLES_CATALOGUE[type_catalogue]
    ligne = session.get(table, identifiant)
    if ligne is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fiche introuvable")
    if ligne.source == "systeme":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Les fiches système sont en lecture seule ; créez une fiche utilisateur",
        )

    charge = {**charge, "id": identifiant}
    fiche = _valider(type_catalogue, charge)
    donnees = fiche.model_dump(mode="json")
    donnees["source"] = "utilisateur"

    ligne.nom = _nom(type_catalogue, fiche)
    ligne.fabricant = getattr(fiche, "fabricant", "")
    ligne.fiche = donnees
    for champ, valeur in _colonnes(type_catalogue, fiche).items():
        setattr(ligne, champ, valeur)
    session.commit()
    return donnees


@routeur.delete("/{type_catalogue}/{identifiant}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    type_catalogue: TypeCatalogue,
    identifiant: str,
    session: Session = Depends(obtenir_session),
) -> None:
    table = TABLES_CATALOGUE[type_catalogue]
    ligne = session.get(table, identifiant)
    if ligne is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fiche introuvable")
    if ligne.source == "systeme":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Les fiches système ne peuvent pas être supprimées",
        )
    session.delete(ligne)
    session.commit()
