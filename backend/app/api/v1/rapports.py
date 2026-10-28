"""Routes de génération du rapport PDF."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...db.modeles import Projet
from ...db.session import obtenir_session
from ...engine.modeles import ProjetEntree, ResultatsProjet
from ...engine.pipeline import calculer_projet
from ...rapports.pdf import construire_rapport
from ...services.fichiers import entete_fichier

routeur = APIRouter()


def _reponse_pdf(contenu: bytes, nom: str) -> Response:
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers=entete_fichier(nom, "pdf"),
    )


@routeur.post("/rapports/pdf")
def rapport_depuis_entree(entree: ProjetEntree) -> Response:
    """Rapport d'un projet non enregistré."""
    resultats = calculer_projet(entree)
    return _reponse_pdf(construire_rapport(entree, resultats), entree.meta.nom)


@routeur.get("/projets/{identifiant}/rapport.pdf")
def rapport_projet(
    identifiant: str, session: Session = Depends(obtenir_session)
) -> Response:
    projet = session.get(Projet, identifiant)
    if projet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projet introuvable")

    entree = ProjetEntree.model_validate(projet.entree)
    if projet.resultats:
        resultats = ResultatsProjet.model_validate(projet.resultats)
    else:
        resultats = calculer_projet(entree)
    return _reponse_pdf(construire_rapport(entree, resultats), projet.nom)
