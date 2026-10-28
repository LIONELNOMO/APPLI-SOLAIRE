"""Route de santé : seule route accessible sans jeton en mode desktop."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...config import Settings
from ...engine.modeles import VERSION_MOTEUR

routeur = APIRouter()


class Sante(BaseModel):
    statut: str
    version: str
    mode: str


@routeur.get("/health", response_model=Sante)
def sante() -> Sante:
    return Sante(statut="ok", version=VERSION_MOTEUR, mode=Settings().mode)
