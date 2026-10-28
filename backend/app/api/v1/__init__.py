"""Routeur de la version 1 de l'API."""

from fastapi import APIRouter

from . import calcul, catalogue, projets, rapports, sante, selection

routeur = APIRouter()
routeur.include_router(sante.routeur, tags=["santé"])
routeur.include_router(calcul.routeur, tags=["calcul"])
routeur.include_router(selection.routeur, tags=["sélection"])
routeur.include_router(catalogue.routeur, tags=["catalogue"])
routeur.include_router(projets.routeur, tags=["projets"])
routeur.include_router(rapports.routeur, tags=["rapports"])

__all__ = ["routeur"]
