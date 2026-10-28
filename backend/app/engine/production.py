"""Module 3, étapes 1 à 3 — Production et puissance crête (F-09, F-10)."""

from __future__ import annotations

from . import constantes as C
from .messages import Message, fmt, fmt_pct, msg
from .modeles import (
    BilanValeurs,
    PotentielValeurs,
    ProductionEntree,
    ProductionSerie,
    ProductionValeurs,
)
from .unites import wh_vers_kwh

TAUX_COUVERTURE_MAX = 1.5


def production_mensuelle(
    pc_kwc: float, h_mensuel: list[float], performance_ratio: float
) -> list[float]:
    """F-10 — Production mensuelle, en kWh : E_m = Pc × Hₘ × PR × dₘ.

    L'irradiation réelle de chaque mois est toujours utilisée, même si la
    puissance crête a été dimensionnée sur le mois le plus défavorable.
    """
    return [
        pc_kwc * h * performance_ratio * jours
        for h, jours in zip(h_mensuel, C.JOURS_MOIS, strict=True)
    ]


def serie_production(
    pc_kwc: float, h_mensuel: list[float], performance_ratio: float
) -> ProductionSerie:
    """Production mensuelle, annuelle, journalière et productible spécifique."""
    mensuel = production_mensuelle(pc_kwc, h_mensuel, performance_ratio)
    an = sum(mensuel)
    return ProductionSerie(
        mensuel_kwh=mensuel,
        an_kwh=an,
        j_kwh=an / C.JOURS_AN,
        y_kwh_kwc=an / pc_kwc if pc_kwc > 0 else 0.0,
    )


def calculer_production(
    e: ProductionEntree,
    potentiel: PotentielValeurs | None,
    bilan: BilanValeurs | None,
) -> tuple[ProductionValeurs | None, list[Message]]:
    """Puissance crête retenue et production attendue (F-09, F-10)."""
    messages: list[Message] = []

    # --- Contrôles des paramètres (bornes métier du cahier) ---
    if not 0 < e.performance_ratio <= 1:
        messages.append(
            msg(
                "PROD-E04",
                pr=e.performance_ratio,
                valeur=e.performance_ratio,
                limite=1.0,
                champs=("production.performance_ratio",),
            )
        )
    elif not C.PR_PLAGE_USUELLE[0] <= e.performance_ratio <= C.PR_PLAGE_USUELLE[1]:
        messages.append(
            msg(
                "PROD-A03",
                pr=e.performance_ratio,
                valeur=e.performance_ratio,
                champs=("production.performance_ratio",),
            )
        )

    if not 0 < e.taux_couverture <= TAUX_COUVERTURE_MAX:
        messages.append(
            msg(
                "PROD-E05",
                taux=fmt_pct(e.taux_couverture, 0),
                valeur=e.taux_couverture,
                limite=TAUX_COUVERTURE_MAX,
                champs=("production.taux_couverture",),
            )
        )

    if not 0 < e.tension_systeme_v <= C.US_MAX_V:
        messages.append(
            msg(
                "PROD-E02",
                us=e.tension_systeme_v,
                us_max=fmt(C.US_MAX_V, 0),
                valeur=e.tension_systeme_v,
                limite=C.US_MAX_V,
                unite="V",
                champs=("production.tension_systeme_v",),
            )
        )

    # --- Données amont ---
    if potentiel is None:
        messages.append(
            msg("PROD-I02", cause="l'irradiation n'est pas disponible")
        )
        return None, messages

    ir = (
        potentiel.h_min_kwh_m2_j
        if e.critere_ir == "mois_defavorable"
        else potentiel.h_kwh_m2_j
    )

    e_zone_kwh_j = wh_vers_kwh(bilan.e_zone_wh_j) if bilan else 0.0
    e_cible = e_zone_kwh_j * e.taux_couverture

    # --- F-09 : puissance crête calculée ---
    # Ir en kWh/m²/j vaut le nombre d'heures équivalentes à 1 kW/m², donc
    # kWh/j ÷ h/j donne des kW, c'est-à-dire des kWc.
    pc_calculee: float | None = None
    if e_cible > 0 and ir > 0 and e.performance_ratio > 0:
        pc_calculee = e_cible / (ir * e.performance_ratio)
        if pc_calculee > C.PC_MAX_KWC:
            messages.append(
                msg(
                    "PROD-E03",
                    pc=pc_calculee / 1000.0,
                    # Paramètre du modèle de message, distinct du champ
                    # structuré `limite` qui doit rester numérique.
                    limite_mwc=fmt(C.PC_MAX_KWC / 1000.0, 0),
                    valeur=pc_calculee,
                    limite=C.PC_MAX_KWC,
                    unite="kWc",
                    champs=("production.taux_couverture",),
                )
            )

    # --- Étape 3 : puissance retenue ---
    if e.mode_pc == "imposee":
        if e.pc_imposee_kwc is None:
            messages.append(
                msg("PROD-E06", champs=("production.pc_imposee_kwc",))
            )
            return None, messages
        pc_retenue = e.pc_imposee_kwc
        if not 0 < pc_retenue <= C.PC_MAX_KWC:
            messages.append(
                msg(
                    "PROD-E01",
                    pc=pc_retenue,
                    pc_max=fmt(C.PC_MAX_KWC, 0),
                    valeur=pc_retenue,
                    limite=C.PC_MAX_KWC,
                    unite="kWc",
                    champs=("production.pc_imposee_kwc",),
                )
            )
        if pc_calculee and pc_calculee > 0:
            rapport = pc_retenue / pc_calculee
            if rapport < 0.90:
                messages.append(
                    msg(
                        "PROD-A01",
                        couverture=fmt_pct(rapport, 0),
                        valeur=pc_retenue,
                        limite=pc_calculee,
                        unite="kWc",
                        champs=("production.pc_imposee_kwc",),
                    )
                )
            elif rapport > 1.10:
                messages.append(
                    msg("PROD-I01", exces=fmt_pct(rapport - 1.0, 0))
                )
    else:
        if pc_calculee is None:
            messages.append(
                msg(
                    "PROD-I02",
                    cause="la consommation de la zone n'est pas disponible",
                )
            )
            return None, messages
        pc_retenue = pc_calculee

    if pc_retenue <= 0:
        messages.append(msg("PROD-I02", cause="la puissance retenue est nulle"))
        return None, messages

    # --- Surface disponible (si connue) ---
    if (
        potentiel.pc_max_surface_kwc is not None
        and pc_retenue > potentiel.pc_max_surface_kwc
    ):
        messages.append(
            msg(
                "PROD-A02",
                pc_max=potentiel.pc_max_surface_kwc,
                pc=pc_retenue,
                valeur=pc_retenue,
                limite=potentiel.pc_max_surface_kwc,
                unite="kWc",
                champs=("potentiel.surface_valeur",),
            )
        )

    # --- F-10 : production théorique, sur la puissance retenue ---
    theorique = serie_production(
        pc_retenue, potentiel.h_mensuel_kwh_m2_j, e.performance_ratio
    )

    valeurs = ProductionValeurs(
        ir_kwh_m2_j=ir,
        e_cible_kwh_j=e_cible,
        pc_calculee_kwc=pc_calculee,
        pc_retenue_kwc=pc_retenue,
        prod_theorique=theorique,
        taux_couverture_effectif=(
            theorique.j_kwh / e_zone_kwh_j if e_zone_kwh_j > 0 else None
        ),
    )
    return valeurs, messages


def completer_production_installee(
    valeurs: ProductionValeurs,
    pc_installee_kwc: float,
    h_mensuel: list[float],
    performance_ratio: float,
    e_zone_kwh_j: float,
) -> None:
    """Deuxième exécution de F-10, sur la puissance réellement installée.

    C'est cette série que l'onglet 4 utilise pour le bilan d'injection.
    """
    valeurs.prod_installee = serie_production(
        pc_installee_kwc, h_mensuel, performance_ratio
    )
    if e_zone_kwh_j > 0:
        valeurs.taux_couverture_effectif = (
            valeurs.prod_installee.j_kwh / e_zone_kwh_j
        )
