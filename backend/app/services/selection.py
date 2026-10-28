"""Listes de choix calculées des étapes 4, 12 et 15.

Chaque fiche du catalogue est évaluée avec la configuration courante du
projet, puis triée du plus adapté au moins adapté.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.modeles import BatterieDb, OnduleurDb, PanneauDb
from ..engine import constantes as C
from ..engine.batteries import dimensionner_batteries
from ..engine.bilan import calculer_bilan
from ..engine.champ_pv import configurer_champ
from ..engine.messages import Niveau, statut
from ..engine.modeles import (
    Batterie,
    Onduleur,
    Panneau,
    ProjetEntree,
)
from ..engine.onduleur import dimensionner_onduleurs
from ..engine.potentiel import calculer_potentiel
from ..engine.production import calculer_production

Statut = Literal["ok", "avertissement", "erreur"]


class FiltresSelection(BaseModel):
    recherche: str | None = None
    fabricant: str | None = None
    technologie: str | None = None
    compatibles_uniquement: bool = False
    pmax_min: float | None = None
    pmax_max: float | None = None
    vmp_min: float | None = None
    vmp_max: float | None = None
    imp_min: float | None = None
    imp_max: float | None = None
    pnom_ac_min: float | None = None
    pnom_ac_max: float | None = None
    u_ac: float | None = None
    nb_mppt_min: int | None = None
    u_nom: float | None = None
    capacite_min: float | None = None


class Proposition(BaseModel):
    fiche: dict[str, Any]
    apercu: dict[str, Any]
    statut: Statut
    motif: str | None = None


def _motif(messages) -> str | None:
    """Message le plus grave, pour expliquer un statut en une ligne."""
    for niveau in (Niveau.ERREUR, Niveau.AVERTISSEMENT):
        for message in messages:
            if message.niveau is niveau:
                return message.titre
    return None


def _statut_sans_info(messages) -> Statut:
    resultat = statut(messages, calcule=True)
    return "ok" if resultat == "non_calcule" else resultat  # type: ignore[return-value]


def _texte_correspond(filtres: FiltresSelection, *champs: str) -> bool:
    if not filtres.recherche:
        return True
    recherche = filtres.recherche.lower()
    return any(recherche in (champ or "").lower() for champ in champs)


def _contexte(projet: ProjetEntree):
    """Puissance retenue et irradiation, calculées une seule fois."""
    potentiel, _ = calculer_potentiel(
        projet.potentiel, projet.production.performance_ratio
    )
    bilan, _ = calculer_bilan(projet.bilan)
    production, _ = calculer_production(projet.production, potentiel, bilan)
    return potentiel, bilan, production


def selectionner_panneaux(
    session: Session, projet: ProjetEntree, filtres: FiltresSelection
) -> list[Proposition]:
    """Étape 4 — Liste de choix des panneaux."""
    _, _, production = _contexte(projet)
    if production is None:
        return []

    pc_retenue = production.pc_retenue_kwc
    us = projet.production.tension_systeme_v

    requete = select(PanneauDb).where(PanneauDb.actif.is_(True))
    if filtres.fabricant:
        requete = requete.where(PanneauDb.fabricant == filtres.fabricant)
    if filtres.technologie:
        requete = requete.where(PanneauDb.technologie == filtres.technologie)
    if filtres.pmax_min is not None:
        requete = requete.where(PanneauDb.pmax >= filtres.pmax_min)
    if filtres.pmax_max is not None:
        requete = requete.where(PanneauDb.pmax <= filtres.pmax_max)
    if filtres.vmp_min is not None:
        requete = requete.where(PanneauDb.vmp >= filtres.vmp_min)
    if filtres.vmp_max is not None:
        requete = requete.where(PanneauDb.vmp <= filtres.vmp_max)
    if filtres.imp_min is not None:
        requete = requete.where(PanneauDb.imp >= filtres.imp_min)
    if filtres.imp_max is not None:
        requete = requete.where(PanneauDb.imp <= filtres.imp_max)

    propositions: list[Proposition] = []
    for ligne in session.scalars(requete):
        if not _texte_correspond(filtres, ligne.nom, ligne.fabricant, ligne.technologie):
            continue

        panneau = Panneau.model_validate(ligne.fiche)
        entree_pv = projet.pv.model_copy(deep=True)
        entree_pv.fiche = panneau
        entree_pv.mode_config = "auto"

        valeurs, messages = configurer_champ(entree_pv, pc_retenue, us)
        etat = _statut_sans_info(messages)
        if filtres.compatibles_uniquement and etat == "erreur":
            continue

        apercu: dict[str, Any] = {}
        if valeurs is not None:
            apercu = {
                "n_min": valeurs.n_min,
                "ns": valeurs.ns,
                "np": valeurs.np,
                "n_total": valeurs.n_total,
                "pc_installee_kwc": valeurs.pc_installee_kwc,
                "surplus_pct": (
                    (valeurs.pc_installee_kwc - pc_retenue) / pc_retenue * 100.0
                    if pc_retenue > 0
                    else None
                ),
                "u_dc_v": valeurs.u_dc_v,
                "i_dc_a": valeurs.i_dc_a,
                "voc_max_v": valeurs.voc_max_v,
                "taux_utilisation_us": valeurs.taux_utilisation_us,
            }

        propositions.append(
            Proposition(
                fiche=ligne.fiche,
                apercu=apercu,
                statut=etat,
                motif=_motif(messages),
            )
        )

    ordre = {"ok": 0, "avertissement": 1, "erreur": 2}
    propositions.sort(
        key=lambda p: (
            ordre[p.statut],
            abs(p.apercu.get("surplus_pct") or 999),
            -(p.apercu.get("taux_utilisation_us") or 0),
            -(p.fiche.get("pmax") or 0),
        )
    )
    return propositions


def selectionner_onduleurs(
    session: Session, projet: ProjetEntree, filtres: FiltresSelection
) -> list[Proposition]:
    """Étape 12 — Liste de choix des onduleurs."""
    _, _, production = _contexte(projet)
    if production is None or projet.pv.fiche is None:
        return []

    pv, _ = configurer_champ(
        projet.pv, production.pc_retenue_kwc, projet.production.tension_systeme_v
    )
    if pv is None:
        return []

    requete = select(OnduleurDb).where(OnduleurDb.actif.is_(True))
    if filtres.fabricant:
        requete = requete.where(OnduleurDb.fabricant == filtres.fabricant)
    if filtres.pnom_ac_min is not None:
        requete = requete.where(OnduleurDb.pnom_ac >= filtres.pnom_ac_min)
    if filtres.pnom_ac_max is not None:
        requete = requete.where(OnduleurDb.pnom_ac <= filtres.pnom_ac_max)
    if filtres.u_ac is not None:
        requete = requete.where(OnduleurDb.u_ac == filtres.u_ac)
    if filtres.nb_mppt_min is not None:
        requete = requete.where(OnduleurDb.nb_mppt >= filtres.nb_mppt_min)

    propositions: list[Proposition] = []
    for ligne in session.scalars(requete):
        if not _texte_correspond(filtres, ligne.nom, ligne.fabricant):
            continue

        onduleur = Onduleur.model_validate(ligne.fiche)
        entree = projet.onduleur.model_copy(deep=True)
        entree.fiche = onduleur
        entree.mode_nombre = "auto"

        valeurs, messages = dimensionner_onduleurs(
            entree, pv, projet.pv.fiche, projet.production.tension_systeme_v
        )
        etat = _statut_sans_info(messages)
        if filtres.compatibles_uniquement and etat == "erreur":
            continue

        apercu: dict[str, Any] = {}
        if valeurs is not None:
            apercu = {
                "n_ond": valeurs.n_ond,
                "ratio_dc_ac": valeurs.ratio_dc_ac,
                "n_ond_max": valeurs.n_ond_max,
                "n_mppt_max": valeurs.n_mppt_max,
                "i_mppt_a": valeurs.i_mppt_a,
                "p_racc_max_kwc": valeurs.p_racc_max_kwc,
                "ns_min": valeurs.ns_min,
                "ns_max": valeurs.ns_max,
                "iac_a": valeurs.iac_a,
                "entrees_libres": valeurs.entrees_libres,
            }

        propositions.append(
            Proposition(
                fiche=ligne.fiche,
                apercu=apercu,
                statut=etat,
                motif=_motif(messages),
            )
        )

    ordre = {"ok": 0, "avertissement": 1, "erreur": 2}
    propositions.sort(
        key=lambda p: (
            ordre[p.statut],
            abs((p.apercu.get("ratio_dc_ac") or 99) - C.RATIO_DC_AC_REFERENCE),
            p.apercu.get("n_ond") or 999,
        )
    )
    return propositions


def selectionner_batteries(
    session: Session, projet: ProjetEntree, filtres: FiltresSelection
) -> list[Proposition]:
    """Étape 15 — Liste de choix des batteries."""
    _, bilan, _ = _contexte(projet)
    if bilan is None:
        return []

    requete = select(BatterieDb).where(BatterieDb.actif.is_(True))
    if filtres.fabricant:
        requete = requete.where(BatterieDb.fabricant == filtres.fabricant)
    if filtres.technologie:
        requete = requete.where(BatterieDb.technologie == filtres.technologie)
    if filtres.u_nom is not None:
        requete = requete.where(BatterieDb.u_nom == filtres.u_nom)
    if filtres.capacite_min is not None:
        requete = requete.where(BatterieDb.capacite_ah >= filtres.capacite_min)

    propositions: list[Proposition] = []
    for ligne in session.scalars(requete):
        if not _texte_correspond(filtres, ligne.nom, ligne.fabricant, ligne.technologie):
            continue

        batterie = Batterie.model_validate(ligne.fiche)
        entree = projet.batteries.model_copy(deep=True)
        entree.fiche = batterie
        entree.actif = True
        entree.mode_config = "auto"
        entree.dod = None
        entree.rendement_batterie = None

        valeurs, messages = dimensionner_batteries(entree, bilan)
        etat = _statut_sans_info(messages)
        if filtres.compatibles_uniquement and etat == "erreur":
            continue

        apercu: dict[str, Any] = {}
        if valeurs is not None:
            apercu = {
                "ns": valeurs.ns,
                "np": valeurs.np,
                "n_total": valeurs.n_total,
                "u_parc_v": valeurs.u_parc_v,
                "i_parc_a": valeurs.i_parc_a,
                "e_inst_wh": valeurs.e_inst_wh,
                "autonomie_j": valeurs.autonomie_j,
                "surplus_wh": valeurs.e_inst_wh - valeurs.e_bat_wh,
                "duree_vie_ans": valeurs.duree_vie_ans,
            }

        propositions.append(
            Proposition(
                fiche=ligne.fiche,
                apercu=apercu,
                statut=etat,
                motif=_motif(messages),
            )
        )

    ordre = {"ok": 0, "avertissement": 1, "erreur": 2}
    propositions.sort(
        key=lambda p: (
            ordre[p.statut],
            p.apercu.get("surplus_wh") or 1e12,
            -(p.fiche.get("cycles") or 0),
            p.apercu.get("n_total") or 999,
        )
    )
    return propositions
