"""Routes des listes de choix d'équipement (étapes 4, 12 et 15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...db.session import obtenir_session
from ...engine.modeles import ProjetEntree
from ...services.selection import (
    FiltresSelection,
    Proposition,
    selectionner_batteries,
    selectionner_onduleurs,
    selectionner_panneaux,
)

routeur = APIRouter(prefix="/selection")


class DemandeSelection(BaseModel):
    projet: ProjetEntree
    filtres: FiltresSelection = Field(default_factory=FiltresSelection)


@routeur.post("/panneaux", response_model=list[Proposition])
def panneaux(
    demande: DemandeSelection, session: Session = Depends(obtenir_session)
) -> list[Proposition]:
    return selectionner_panneaux(session, demande.projet, demande.filtres)


@routeur.post("/onduleurs", response_model=list[Proposition])
def onduleurs(
    demande: DemandeSelection, session: Session = Depends(obtenir_session)
) -> list[Proposition]:
    return selectionner_onduleurs(session, demande.projet, demande.filtres)


@routeur.post("/batteries", response_model=list[Proposition])
def batteries(
    demande: DemandeSelection, session: Session = Depends(obtenir_session)
) -> list[Proposition]:
    return selectionner_batteries(session, demande.projet, demande.filtres)
