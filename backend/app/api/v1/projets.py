"""Routes de gestion des projets."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.modeles import Projet
from ...db.session import obtenir_session
from ...engine.modeles import ProjetEntree, ResultatsProjet
from ...engine.pipeline import calculer_projet
from ...services import projets as service
from ...services.fichiers import entete_fichier

routeur = APIRouter(prefix="/projets")


class ProjetComplet(BaseModel):
    id: str
    entree: ProjetEntree
    resultats: ResultatsProjet


class ReponseImport(BaseModel):
    id: str
    entree: ProjetEntree
    resultats: ResultatsProjet
    empreinte_valide: bool
    avertissements: list[str]


def _recuperer(session: Session, identifiant: str) -> Projet:
    projet = session.get(Projet, identifiant)
    if projet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projet introuvable")
    return projet


@routeur.get("/defaut", response_model=ProjetEntree)
def defaut(session: Session = Depends(obtenir_session)) -> ProjetEntree:
    """Projet neuf, avec le profil « Ménage type » pré-rempli."""
    return service.projet_par_defaut(session)


@routeur.get("", response_model=list[service.ResumeProjet])
def lister(session: Session = Depends(obtenir_session)) -> list[service.ResumeProjet]:
    return service.lister(session)


@routeur.post("", response_model=ProjetComplet, status_code=status.HTTP_201_CREATED)
def creer(
    entree: ProjetEntree, session: Session = Depends(obtenir_session)
) -> ProjetComplet:
    projet, resultats = service.creer(session, entree)
    session.commit()
    return ProjetComplet(id=projet.id, entree=entree, resultats=resultats)


@routeur.get("/{identifiant}", response_model=ProjetComplet)
def lire(
    identifiant: str, session: Session = Depends(obtenir_session)
) -> ProjetComplet:
    projet = _recuperer(session, identifiant)
    entree = ProjetEntree.model_validate(projet.entree)
    if projet.resultats:
        resultats = ResultatsProjet.model_validate(projet.resultats)
    else:
        resultats = calculer_projet(entree)
    return ProjetComplet(id=projet.id, entree=entree, resultats=resultats)


@routeur.put("/{identifiant}", response_model=ProjetComplet)
def enregistrer(
    identifiant: str,
    entree: ProjetEntree,
    session: Session = Depends(obtenir_session),
) -> ProjetComplet:
    projet = _recuperer(session, identifiant)
    resultats = service.enregistrer(session, projet, entree)
    session.commit()
    return ProjetComplet(id=projet.id, entree=entree, resultats=resultats)


@routeur.delete("/{identifiant}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(identifiant: str, session: Session = Depends(obtenir_session)) -> None:
    projet = _recuperer(session, identifiant)
    session.delete(projet)
    session.commit()


@routeur.post(
    "/{identifiant}/dupliquer",
    response_model=ProjetComplet,
    status_code=status.HTTP_201_CREATED,
)
def dupliquer(
    identifiant: str, session: Session = Depends(obtenir_session)
) -> ProjetComplet:
    projet = _recuperer(session, identifiant)
    copie = service.dupliquer(session, projet)
    session.commit()
    return ProjetComplet(
        id=copie.id,
        entree=ProjetEntree.model_validate(copie.entree),
        resultats=ResultatsProjet.model_validate(copie.resultats),
    )


@routeur.get("/{identifiant}/export")
def exporter(
    identifiant: str, session: Session = Depends(obtenir_session)
) -> JSONResponse:
    projet = _recuperer(session, identifiant)
    charge = service.exporter(projet)
    return JSONResponse(
        content=charge,
        headers=entete_fichier(projet.nom, "dimsolaire.json"),
    )


@routeur.post("/import", response_model=ReponseImport, status_code=status.HTTP_201_CREATED)
def importer(
    charge: dict[str, Any], session: Session = Depends(obtenir_session)
) -> ReponseImport:
    try:
        resultat = service.importer(charge)
    except ValueError as erreur:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erreur)
        ) from erreur

    entree = resultat.entree
    entree.meta.nom = service.nom_unique(session, entree.meta.nom)
    projet, resultats = service.creer(session, entree)
    session.commit()
    return ReponseImport(
        id=projet.id,
        entree=entree,
        resultats=resultats,
        empreinte_valide=resultat.empreinte_valide,
        avertissements=resultat.avertissements,
    )
