"""Route de calcul.

Cette route ne renvoie jamais d'erreur pour une valeur métier : les problèmes
sont des messages dans la réponse (principe P3).
"""

from __future__ import annotations

from fastapi import APIRouter

from ...engine.modeles import ProjetEntree, ResultatsProjet
from ...engine.pipeline import calculer_projet

routeur = APIRouter()


@routeur.post("/calcul", response_model=ResultatsProjet)
def calculer(entree: ProjetEntree) -> ResultatsProjet:
    return calculer_projet(entree)
