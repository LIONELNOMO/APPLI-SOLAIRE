"""Enchaînement des modules de calcul (§6.0 du cahier des charges).

Le moteur calcule tout ce qui peut l'être (principe P3) : un module dont les
données amont manquent renvoie des valeurs nulles et un message d'information,
sans interrompre les autres.
"""

from __future__ import annotations

from .batteries import dimensionner_batteries
from .bilan import calculer_bilan
from .cables import calculer_cables_dc
from .champ_pv import configurer_champ, message_courant_eleve
from .injection import calculer_injection
from .messages import Message, statut, statut_global
from .modeles import (
    BatteriesValeurs,
    BilanValeurs,
    CablesValeurs,
    InjectionValeurs,
    OnduleurValeurs,
    PotentielValeurs,
    ProductionValeurs,
    ProjetEntree,
    PvValeurs,
    ResultatsProjet,
    SortieModule,
)
from .potentiel import calculer_potentiel
from .production import calculer_production, completer_production_installee


def calculer_projet(entree: ProjetEntree) -> ResultatsProjet:
    """Calcule un projet complet et renvoie tous les résultats et messages."""
    tous: list[Message] = []

    # --- Onglet 1 : potentiel solaire ---
    potentiel, messages = calculer_potentiel(
        entree.potentiel, entree.production.performance_ratio
    )
    tous.extend(messages)
    sortie_potentiel: SortieModule[PotentielValeurs] = SortieModule(
        statut=statut(messages, calcule=potentiel is not None), valeurs=potentiel
    )

    # --- Onglet 2 : bilan énergétique ---
    bilan, messages = calculer_bilan(entree.bilan)
    tous.extend(messages)
    sortie_bilan: SortieModule[BilanValeurs] = SortieModule(
        statut=statut(messages, calcule=bilan is not None), valeurs=bilan
    )

    # --- Étapes 1 à 3 : production et puissance crête ---
    production, messages = calculer_production(entree.production, potentiel, bilan)
    tous.extend(messages)
    messages_production = list(messages)

    # --- Étapes 4 à 11 : champ photovoltaïque ---
    pv: PvValeurs | None = None
    messages_pv: list[Message] = []
    if production is not None:
        pv, messages_pv = configurer_champ(
            entree.pv,
            production.pc_retenue_kwc,
            entree.production.tension_systeme_v,
        )
    else:
        messages_pv = []

    # --- Étapes 12 à 14 : onduleurs ---
    onduleur: OnduleurValeurs | None = None
    messages_onduleur: list[Message] = []
    if pv is not None:
        from .onduleur import dimensionner_onduleurs

        onduleur, messages_onduleur = dimensionner_onduleurs(
            entree.onduleur, pv, entree.pv.fiche, entree.production.tension_systeme_v
        )

    # PV-I03 n'est émis que si aucun onduleur ne répartit le courant (A-06).
    if pv is not None:
        messages_pv.extend(
            message_courant_eleve(pv, onduleurs_repartissent=onduleur is not None)
        )

    tous.extend(messages_pv)
    sortie_pv: SortieModule[PvValeurs] = SortieModule(
        statut=statut(messages_pv, calcule=pv is not None), valeurs=pv
    )
    tous.extend(messages_onduleur)
    sortie_onduleur: SortieModule[OnduleurValeurs] = SortieModule(
        statut=statut(messages_onduleur, calcule=onduleur is not None),
        valeurs=onduleur,
    )

    # --- Deuxième exécution de F-10, sur la puissance installée ---
    if production is not None and pv is not None and potentiel is not None:
        completer_production_installee(
            production,
            pv.pc_installee_kwc,
            potentiel.h_mensuel_kwh_m2_j,
            entree.production.performance_ratio,
            bilan.e_zone_wh_j / 1000.0 if bilan else 0.0,
        )

    sortie_production: SortieModule[ProductionValeurs] = SortieModule(
        statut=statut(messages_production, calcule=production is not None),
        valeurs=production,
    )

    # --- Étapes 15 à 19 : batteries ---
    batteries, messages = dimensionner_batteries(entree.batteries, bilan)
    tous.extend(messages)
    sortie_batteries: SortieModule[BatteriesValeurs] = SortieModule(
        statut=statut(messages, calcule=batteries is not None), valeurs=batteries
    )

    # --- Étapes 20 et 21 : câbles continus ---
    cables, messages = calculer_cables_dc(
        entree.cables, pv, onduleur, batteries, entree.pv.fiche
    )
    tous.extend(messages)
    sortie_cables: SortieModule[CablesValeurs] = SortieModule(
        statut=statut(messages, calcule=cables is not None), valeurs=cables
    )

    # --- Onglet 4 : injection ---
    injection, messages = calculer_injection(
        entree.injection,
        onduleur,
        entree.onduleur.fiche,
        production.prod_installee.mensuel_kwh
        if production and production.prod_installee
        else None,
        bilan.e_zone_wh_j if bilan else 0.0,
        entree.onduleur.cos_phi,
        entree.cables.rho_mode,
        entree.cables.rho_perso_cu,
        entree.cables.rho_perso_al,
    )
    tous.extend(messages)
    sortie_injection: SortieModule[InjectionValeurs] = SortieModule(
        statut=statut(messages, calcule=injection is not None), valeurs=injection
    )

    return ResultatsProjet(
        statut_global=statut_global(tous),
        messages=tous,
        potentiel=sortie_potentiel,
        bilan=sortie_bilan,
        production=sortie_production,
        pv=sortie_pv,
        onduleur=sortie_onduleur,
        batteries=sortie_batteries,
        cables=sortie_cables,
        injection=sortie_injection,
    )
