"""Module 1 — Potentiel solaire (onglet 1, formules F-01 à F-04)."""

from __future__ import annotations

from . import constantes as C
from .messages import Message, fmt, fmt_entier, msg
from .modeles import PotentielEntree, PotentielValeurs
from .unites import (
    ghi_vers_h_kwh_m2_j,
    h_vers_irradiance_moy24h_w_m2,
    surface_vers_m2,
)


def _h_mensuel(e: PotentielEntree, h_unique: float) -> tuple[list[float], list[Message]]:
    """Profil mensuel retenu : celui saisi, sinon la valeur unique répétée."""
    messages: list[Message] = []
    profil = e.profil_mensuel_kwh_m2_j

    if profil is None:
        return [h_unique] * 12, messages

    if len(profil) != 12 or any(v <= 0 for v in profil):
        messages.append(msg("POT-E03", champs=("potentiel.profil_mensuel_kwh_m2_j",)))
        return [h_unique] * 12, messages

    # F-01 : moyenne pondérée par le nombre de jours de chaque mois.
    moyenne = sum(h * d for h, d in zip(profil, C.JOURS_MOIS, strict=True)) / C.JOURS_AN
    if h_unique > 0 and abs(moyenne - h_unique) / h_unique > 0.05:
        messages.append(
            msg(
                "POT-A02",
                moyenne=moyenne,
                unique=h_unique,
                ecart=fmt(abs(moyenne - h_unique) / h_unique * 100.0, 1),
                valeur=moyenne,
                limite=h_unique,
                unite="kWh/m²/j",
                champs=("potentiel.ghi_valeur",),
            )
        )
    return list(profil), messages


def calculer_potentiel(
    e: PotentielEntree, performance_ratio: float
) -> tuple[PotentielValeurs | None, list[Message]]:
    """Irradiation et potentiel énergétique de la zone (F-01 à F-04).

    `performance_ratio` vient de l'onglet 3 et ne sert qu'au potentiel
    technique (F-04).
    """
    messages: list[Message] = []

    if e.ghi_valeur <= 0:
        messages.append(
            msg("POT-E01", valeur=e.ghi_valeur, champs=("potentiel.ghi_valeur",))
        )
        return None, messages

    # --- F-01 : irradiation journalière moyenne ---
    h_unique = ghi_vers_h_kwh_m2_j(e.ghi_valeur, e.ghi_unite)
    h_mensuel, messages_profil = _h_mensuel(e, h_unique)
    messages.extend(messages_profil)

    h = sum(v * d for v, d in zip(h_mensuel, C.JOURS_MOIS, strict=True)) / C.JOURS_AN
    h_an = sum(v * d for v, d in zip(h_mensuel, C.JOURS_MOIS, strict=True))
    h_min = min(h_mensuel)
    mois_defavorable = h_mensuel.index(h_min) + 1
    g_moy = h_vers_irradiance_moy24h_w_m2(h)

    # --- Vraisemblance de la conversion ---
    h_bas, h_haut = C.H_PLAGE_VRAISEMBLABLE
    if not h_bas <= h <= h_haut:
        messages.append(
            msg(
                "POT-A01",
                h=h,
                h_min=fmt(h_bas, 1),
                h_max=fmt(h_haut, 1),
                valeur=h,
                unite="kWh/m²/j",
                champs=("potentiel.ghi_valeur", "potentiel.ghi_unite"),
            )
        )

    an_bas, an_haut = C.H_AN_PLAGE_PLAUSIBLE
    if not an_bas <= h_an <= an_haut:
        messages.append(
            msg(
                "POT-A03",
                h_an=h_an,
                h_min=fmt_entier(an_bas),
                h_max=fmt_entier(an_haut),
                valeur=h_an,
                unite="kWh/m²/an",
                champs=("potentiel.ghi_valeur", "potentiel.ghi_unite"),
            )
        )

    yao_bas, yao_haut = C.H_PLAGE_YAOUNDE
    if not yao_bas <= h <= yao_haut:
        messages.append(
            msg(
                "POT-I01",
                h=h,
                h_min=fmt(yao_bas, 1),
                h_max=fmt(yao_haut, 1),
                valeur=h,
                unite="kWh/m²/j",
                champs=("potentiel.source_ghi",),
            )
        )

    if "à confirmer" in e.source_ghi.lower():
        messages.append(msg("POT-I02", champs=("potentiel.source_ghi",)))

    messages.append(msg("POT-I04"))

    valeurs = PotentielValeurs(
        h_kwh_m2_j=h,
        h_an_kwh_m2_an=h_an,
        g_moy_w_m2=g_moy,
        h_mensuel_kwh_m2_j=h_mensuel,
        h_min_kwh_m2_j=h_min,
        mois_defavorable=mois_defavorable,
    )

    # --- Surface : facultative (question ouverte Q-02) ---
    if e.surface_valeur is None:
        messages.append(msg("POT-I03", champs=("potentiel.surface_valeur",)))
        return valeurs, messages

    if e.surface_valeur <= 0:
        messages.append(
            msg(
                "POT-E02",
                valeur=e.surface_valeur,
                champs=("potentiel.surface_valeur",),
            )
        )
        return valeurs, messages

    surface_m2 = surface_vers_m2(e.surface_valeur, e.surface_unite)
    valeurs.surface_m2 = surface_m2

    # --- F-02 : potentiel brut ---
    valeurs.e_pot_j_kwh = h * surface_m2
    valeurs.e_pot_mensuel_kwh = [
        v * d * surface_m2 for v, d in zip(h_mensuel, C.JOURS_MOIS, strict=True)
    ]
    valeurs.e_pot_an_kwh = h_an * surface_m2

    # --- F-03 : puissance crête maximale installable ---
    # En conditions STC, un module de rendement η produit η kW par m².
    valeurs.pc_max_surface_kwc = (
        surface_m2 * e.taux_occupation * e.rendement_module
    )

    # --- F-04 : potentiel technique ---
    valeurs.e_tech_an_kwh = valeurs.pc_max_surface_kwc * h_an * performance_ratio

    return valeurs, messages
