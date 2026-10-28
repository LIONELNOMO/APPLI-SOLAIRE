"""Module 3, étapes 15 à 19 — Batteries (F-21 à F-23, arbitrage A-03)."""

from __future__ import annotations

from . import constantes as C
from .arrondis import arrondi_demi_haut, ceil_safe
from .messages import Message, fmt, fmt_entier, fmt_pct, msg
from .modeles import Batterie, BatteriesEntree, BatteriesValeurs, BilanValeurs
from .unites import kwh_vers_wh

AUTONOMIE_LONGUE_J = 7.0
AUTONOMIE_MAX_J = 10.0
NP_PLOMB_MAX = 4


def fiche_batterie_valide(b: Batterie) -> bool:
    """Validation d'une fiche de batterie (§8.5)."""
    if not 0 < b.u_nom <= 60 or b.capacite_ah <= 0 or b.i_nom <= 0:
        return False
    if not 0 < b.dod_recommandee <= b.dod_max <= 1:
        return False
    if b.cycles < 1 or not 0 < b.rendement <= 1:
        return False
    if not b.u_decharge_min < b.u_nom < b.u_charge_max:
        return False
    return b.ns_max >= 1


def tension_recommandee(p_base_w: float) -> int:
    """Tension de parc recommandée, pour un courant de décharge raisonnable.

    Les seuils de 1 000 et 3 000 W maintiennent le courant sous environ 125 A.
    """
    for seuil, tension in C.SEUILS_TENSION_PARC:
        if p_base_w <= seuil:
            return tension
    return 48


def plage_convertisseur(u_visee_v: float) -> tuple[float, float]:
    """Plage de tension par défaut de l'onduleur-chargeur, selon la classe."""
    for seuil, u_min, u_max in C.PLAGES_CONVERTISSEUR:
        if u_visee_v <= seuil:
            return u_min, u_max
    return C.PLAGES_CONVERTISSEUR[-1][1], C.PLAGES_CONVERTISSEUR[-1][2]


def _base_energie(
    e: BatteriesEntree, bilan: BilanValeurs | None
) -> tuple[float, float, int | None, str | None]:
    """Énergie et puissance de base : (E_base en Wh/j, P_base en W, abonnés, cause)."""
    if e.base_energie == "personnalisee":
        if e.energie_perso_kwh_j is None or e.puissance_perso_w is None:
            return 0.0, 0.0, None, "les valeurs personnalisées sont incomplètes"
        return (
            kwh_vers_wh(e.energie_perso_kwh_j),
            e.puissance_perso_w,
            None,
            None,
        )

    if bilan is None:
        return 0.0, 0.0, None, "le bilan énergétique n'est pas disponible"

    if e.base_energie == "zone":
        return bilan.e_zone_wh_j, bilan.p_app_zone_w, None, None

    # Base « un abonné » : le profil demandé, ou le premier.
    profil = next(
        (p for p in bilan.profils if p.id == e.profil_id), None
    ) or (bilan.profils[0] if bilan.profils else None)
    if profil is None:
        return 0.0, 0.0, None, "aucune catégorie d'abonnés n'est définie"
    return profil.e_cons_wh_j, profil.p_app_w, profil.nb_abonnes, None


def dimensionner_batteries(
    e: BatteriesEntree, bilan: BilanValeurs | None
) -> tuple[BatteriesValeurs | None, list[Message]]:
    """Capacité, arrangement et vérification du parc de batteries."""
    messages: list[Message] = []

    if not e.actif:
        messages.append(msg("BAT-I03", champs=("batteries.actif",)))
        return None, messages

    b = e.fiche
    if b is None or not fiche_batterie_valide(b):
        messages.append(
            msg("BAT-E01", cause="aucune batterie valide n'est sélectionnée",
                champs=("batteries.fiche",))
        )
        return None, messages

    e_base, p_base, nb_abonnes, cause = _base_energie(e, bilan)
    if cause is not None:
        messages.append(msg("BAT-E01", cause=cause, champs=("batteries.base_energie",)))
        return None, messages
    if e_base <= 0:
        messages.append(
            msg("BAT-E01", cause="l'énergie de base est nulle",
                champs=("batteries.base_energie",))
        )
        return None, messages

    # --- Paramètres ---
    dod = e.dod if e.dod is not None else b.dod_recommandee
    rendement_bat = (
        e.rendement_batterie if e.rendement_batterie is not None else b.rendement
    )
    details: list[str] = []
    if not 0 < e.jours_autonomie <= AUTONOMIE_MAX_J:
        details.append(f"autonomie de {fmt(e.jours_autonomie, 1)} jours")
    if not 0 < e.part_stockee <= 1:
        details.append(f"part stockée de {fmt_pct(e.part_stockee, 0)} %")
    if not 0 < rendement_bat <= 1:
        details.append("rendement de la batterie")
    if not 0 < e.rendement_onduleur <= 1:
        details.append("rendement de l'onduleur-chargeur")
    if not 1 <= e.marge <= 1.5:
        details.append(f"marge de {fmt(e.marge, 2)}")
    if details:
        messages.append(
            msg("BAT-E07", detail=", ".join(details), champs=("batteries",))
        )
        return None, messages

    if dod > b.dod_max:
        messages.append(
            msg(
                "BAT-E05",
                dod=fmt_pct(dod, 0),
                dod_max=fmt_pct(b.dod_max, 0),
                valeur=dod,
                limite=b.dod_max,
                champs=("batteries.dod",),
            )
        )
        return None, messages

    if e.jours_autonomie > AUTONOMIE_LONGUE_J:
        messages.append(
            msg(
                "BAT-A06",
                jours=fmt(e.jours_autonomie, 1),
                valeur=e.jours_autonomie,
                champs=("batteries.jours_autonomie",),
            )
        )

    # --- Étape 16 : tension du parc ---
    u_reco = tension_recommandee(p_base)
    if e.mode_tension == "manuel":
        if e.tension_parc_v is None or e.tension_parc_v <= 0:
            messages.append(
                msg("BAT-E07", detail="tension du parc manquante",
                    champs=("batteries.tension_parc_v",))
            )
            return None, messages
        u_visee = e.tension_parc_v
        if abs(u_visee - u_reco) > 1e-9:
            messages.append(
                msg(
                    "BAT-A05",
                    u_visee=u_visee,
                    u_reco=fmt(float(u_reco), 0),
                    p_base=fmt_entier(p_base),
                    valeur=u_visee,
                    limite=float(u_reco),
                    unite="V",
                    champs=("batteries.tension_parc_v",),
                )
            )
    else:
        u_visee = float(u_reco)

    # --- F-21 : énergie et capacité à stocker ---
    denominateur = dod * rendement_bat * e.rendement_onduleur
    e_bat = e_base * e.part_stockee * e.jours_autonomie * e.marge / denominateur
    e_unit = b.u_nom * b.capacite_ah

    # --- F-22 : arrangement série/parallèle ---
    if e.mode_config == "manuel":
        if (
            e.ns_manuel is None
            or e.np_manuel is None
            or e.ns_manuel < 1
            or e.np_manuel < 1
        ):
            messages.append(
                msg("BAT-E08", champs=("batteries.ns_manuel", "batteries.np_manuel"))
            )
            return None, messages
        ns, np_ = e.ns_manuel, e.np_manuel
        n_min = ceil_safe(e_bat / e_unit)
    else:
        ns = max(1, arrondi_demi_haut(u_visee / b.u_nom))
        n_min = ceil_safe(e_bat / e_unit)
        np_ = max(ceil_safe(n_min / ns), 1)

    n_total = ns * np_

    # --- F-23 : grandeurs du parc ---
    u_parc = ns * b.u_nom
    i_parc = np_ * b.i_nom
    c_parc = np_ * b.capacite_ah
    e_inst = n_total * e_unit
    e_util = e_inst * dod
    besoin = e_base * e.part_stockee
    autonomie = (
        e_util * rendement_bat * e.rendement_onduleur / besoin if besoin > 0 else 0.0
    )
    i_dech = p_base / (u_parc * e.rendement_onduleur) if u_parc > 0 else 0.0
    u_parc_min = ns * b.u_decharge_min
    u_parc_max = ns * b.u_charge_max
    duree_vie = b.cycles / C.JOURS_AN

    # --- Étape 19 : vérifications ---
    if not 0 < u_parc <= e.tension_max_v:
        messages.append(
            msg(
                "BAT-E02",
                u_parc=u_parc,
                u_max=fmt(e.tension_max_v, 0),
                valeur=u_parc,
                limite=e.tension_max_v,
                unite="V",
                champs=("batteries.ns_manuel", "batteries.tension_max_v"),
            )
        )

    conv_min = e.u_conv_min_v
    conv_max = e.u_conv_max_v
    if conv_min is None or conv_max is None:
        defaut_min, defaut_max = plage_convertisseur(u_visee)
        conv_min = conv_min if conv_min is not None else defaut_min
        conv_max = conv_max if conv_max is not None else defaut_max
    if u_parc_min < conv_min or u_parc_max > conv_max:
        messages.append(
            msg(
                "BAT-E03",
                u_min=fmt(u_parc_min, 1),
                u_max=fmt(u_parc_max, 1),
                conv_min=fmt(conv_min, 1),
                conv_max=fmt(conv_max, 1),
                champs=("batteries.u_conv_min_v", "batteries.u_conv_max_v"),
            )
        )

    if u_visee > 0:
        ecart = abs(u_parc - u_visee) / u_visee
        if ecart > C.ECART_TENSION_PARC_MAX:
            messages.append(
                msg(
                    "BAT-E04",
                    u_visee=u_visee,
                    u_parc=u_parc,
                    ecart=fmt_pct(ecart, 1),
                    valeur=u_parc,
                    limite=u_visee,
                    unite="V",
                    champs=("batteries.fiche",),
                )
            )

    if ns > b.ns_max:
        messages.append(
            msg(
                "BAT-E06",
                ns=fmt_entier(ns),
                ns_max=fmt_entier(b.ns_max),
                valeur=float(ns),
                limite=float(b.ns_max),
                champs=("batteries.ns_manuel", "batteries.fiche"),
            )
        )

    # Arbitrage A-03 : deux niveaux de seuil sur le courant de décharge.
    if i_dech > C.I_DECH_ERREUR_A:
        messages.append(
            msg(
                "BAT-E09",
                i_dech=fmt_entier(i_dech),
                valeur=i_dech,
                limite=C.I_DECH_ERREUR_A,
                unite="A",
                champs=("batteries.base_energie", "batteries.tension_max_v"),
            )
        )
    elif i_dech > C.I_DECH_AVERT_A:
        messages.append(
            msg(
                "BAT-A02",
                i_dech=fmt_entier(i_dech),
                u_parc=fmt(u_parc, 1),
                valeur=i_dech,
                limite=C.I_DECH_AVERT_A,
                unite="A",
                champs=("batteries.base_energie",),
            )
        )

    if i_dech > i_parc:
        messages.append(
            msg(
                "BAT-A01",
                i_dech=fmt(i_dech, 1),
                i_parc=fmt(i_parc, 1),
                valeur=i_dech,
                limite=i_parc,
                unite="A",
                champs=("batteries.np_manuel",),
            )
        )

    if b.technologie == "plomb" and np_ > NP_PLOMB_MAX:
        messages.append(
            msg("BAT-A03", np=fmt_entier(np_), champs=("batteries.fiche",))
        )
    if b.np_max is not None and np_ > b.np_max:
        messages.append(
            msg(
                "BAT-A04",
                np=fmt_entier(np_),
                np_max=fmt_entier(b.np_max),
                valeur=float(np_),
                limite=float(b.np_max),
                champs=("batteries.np_manuel",),
            )
        )

    if n_total > n_min:
        messages.append(
            msg(
                "BAT-I02",
                ajoutes=fmt_entier(n_total - n_min),
                n_total=fmt_entier(n_total),
                n_min=fmt_entier(n_min),
            )
        )

    n_total_zone: int | None = None
    if e.base_energie == "abonne" and nb_abonnes:
        n_total_zone = n_total * nb_abonnes
        messages.append(
            msg(
                "BAT-I01",
                n_zone=fmt_entier(n_total_zone),
                n_abonnes=fmt_entier(nb_abonnes),
            )
        )

    messages.append(
        msg("BAT-I04", annees=fmt(duree_vie, 1), cycles=fmt_entier(b.cycles))
    )

    valeurs = BatteriesValeurs(
        e_base_wh_j=e_base,
        p_base_w=p_base,
        tension_recommandee_v=u_reco,
        u_parc_visee_v=u_visee,
        e_bat_wh=e_bat,
        c_bat_ah=e_bat / u_parc if u_parc > 0 else 0.0,
        ns=ns,
        n_min=n_min,
        np=np_,
        n_total=n_total,
        u_parc_v=u_parc,
        i_parc_a=i_parc,
        c_parc_ah=c_parc,
        e_inst_wh=e_inst,
        e_util_wh=e_util,
        autonomie_j=autonomie,
        i_dech_a=i_dech,
        u_parc_min_v=u_parc_min,
        u_parc_max_v=u_parc_max,
        duree_vie_ans=duree_vie,
        n_total_zone=n_total_zone,
    )
    return valeurs, messages
