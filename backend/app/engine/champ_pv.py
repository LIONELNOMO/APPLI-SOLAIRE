"""Module 3, étapes 4 à 11 — Champ photovoltaïque (F-11 à F-18, arbitrage A-02)."""

from __future__ import annotations

from . import constantes as C
from .arrondis import ceil_safe, floor_safe
from .messages import Message, fmt, fmt_entier, fmt_pct, msg
from .modeles import Panneau, PvEntree, PvValeurs

ECART_FICHE_AVERTISSEMENT = 0.02
ECART_FICHE_REFUS = 0.10
TAUX_UTILISATION_FAIBLE = 0.80


def fiche_panneau_valide(p: Panneau) -> bool:
    """Validation d'une fiche de panneau (§8.5).

    Un écart entre Vmp × Imp et Pmax supérieur à 10 % rend la fiche
    inutilisable ; entre 2 et 10 %, elle est acceptée avec PV-A03.
    """
    if min(p.pmax, p.vmp, p.voc, p.imp, p.isc, p.noct, p.vsys_max) <= 0:
        return False
    if not p.vmp < p.voc or not p.imp < p.isc:
        return False
    if not -1.0 <= p.coef_voc <= 0.0 or not -1.0 <= p.coef_vmp <= 0.0:
        return False
    if not 35.0 <= p.noct <= 60.0 or p.vsys_max <= p.voc:
        return False
    return abs(p.vmp * p.imp - p.pmax) / p.pmax <= ECART_FICHE_REFUS


def temperatures_cellule(e: PvEntree, noct: float) -> tuple[float, float]:
    """F-18 — Températures de cellule extrêmes.

    Par forte chaleur : T_cell = T_amb + (NOCT − 20) / 800 × G.
    Par temps froid : T_cell = T_amb. Au lever du soleil, l'éclairement est
    trop faible pour que les cellules s'échauffent au-dessus de l'air.
    """
    t_max = e.t_amb_max_c + (noct - 20.0) / 800.0 * e.g_ref_w_m2
    return e.t_amb_min_c, t_max


def tension_corrigee(u_stc: float, coef_pct_par_c: float, t_cell: float) -> float:
    """Tension d'un panneau ou d'une chaîne à la température de cellule donnée."""
    return u_stc * (1.0 + coef_pct_par_c / 100.0 * (t_cell - C.T_STC_C))


def tension_reference(
    e: PvEntree, p: Panneau, t_cell_min: float
) -> tuple[float, str]:
    """Tension de référence du calcul de Ns et son libellé (arbitrage A-02).

    Le cahier des charges parle de « Umax d'un panneau » sans la définir
    (correction C-07). Trois lectures sont proposées :
    - `vmp` : tension de fonctionnement, règle de l'art, défaut ;
    - `voc` : tension à vide en conditions STC, plus prudent ;
    - `voc_froid` : tension à vide par temps froid, Us devient une limite absolue.
    """
    if e.tension_reference_ns == "voc":
        return p.voc, "Voc"
    if e.tension_reference_ns == "voc_froid":
        return tension_corrigee(p.voc, p.coef_voc, t_cell_min), "Voc par temps froid"
    return p.vmp, "Vmp"


def ns_maximal_sous(limite_v: float, u_unitaire_froid_v: float) -> int:
    """Nombre en série dont la tension à vide par temps froid reste sous la limite."""
    if u_unitaire_froid_v <= 0:
        return 0
    return max(floor_safe(limite_v / u_unitaire_froid_v), 0)


def configurer_champ(
    e: PvEntree, pc_retenue_kwc: float, us_v: float
) -> tuple[PvValeurs | None, list[Message]]:
    """Configuration série/parallèle et vérification du champ (F-11 à F-18)."""
    messages: list[Message] = []
    p = e.fiche

    if p is None or not fiche_panneau_valide(p):
        messages.append(msg("PV-E01", champs=("pv.fiche",)))
        return None, messages

    # Cohérence de la fiche : avertissement entre 2 et 10 % d'écart.
    ecart_fiche = abs(p.vmp * p.imp - p.pmax) / p.pmax
    if ecart_fiche > ECART_FICHE_AVERTISSEMENT:
        messages.append(
            msg(
                "PV-A03",
                produit=p.vmp * p.imp,
                pmax=fmt(p.pmax, 0),
                ecart=fmt_pct(ecart_fiche, 1),
                valeur=p.vmp * p.imp,
                limite=p.pmax,
                unite="W",
                champs=("pv.fiche",),
            )
        )

    # Températures de conception.
    t_bas, t_haut = C.T_AMB_PLAGE_C
    if (
        e.t_amb_min_c >= e.t_amb_max_c
        or not t_bas <= e.t_amb_min_c <= t_haut
        or not t_bas <= e.t_amb_max_c <= t_haut
    ):
        messages.append(
            msg(
                "PV-A02",
                t_min=e.t_amb_min_c,
                t_max=e.t_amb_max_c,
                champs=("pv.t_amb_min_c", "pv.t_amb_max_c"),
            )
        )

    t_cell_min, t_cell_max = temperatures_cellule(e, p.noct)
    u_ref, _ = tension_reference(e, p, t_cell_min)

    # --- F-11 : nombre minimal de panneaux ---
    n_min = ceil_safe(pc_retenue_kwc * 1000.0 / p.pmax)

    # --- F-13 et F-14 : configuration automatique ---
    if e.mode_config == "manuel":
        if (
            e.ns_manuel is None
            or e.np_manuel is None
            or e.ns_manuel < 1
            or e.np_manuel < 1
        ):
            messages.append(
                msg("PV-E05", champs=("pv.ns_manuel", "pv.np_manuel"))
            )
            return None, messages
        ns, np_ = e.ns_manuel, e.np_manuel
    else:
        ns = floor_safe(us_v / u_ref) if u_ref > 0 else 0
        if ns < 1:
            messages.append(
                msg(
                    "PV-E02",
                    us=us_v,
                    u_ref=u_ref,
                    valeur=us_v,
                    limite=u_ref,
                    unite="V",
                    champs=("production.tension_systeme_v", "pv.tension_reference_ns"),
                )
            )
            return None, messages
        np_ = max(ceil_safe(n_min / ns), 1)

    n_total = ns * np_

    # --- F-12 et F-15 : grandeurs du champ ---
    pc_installee = n_total * p.pmax / 1000.0
    u_dc = ns * p.vmp
    i_dc = np_ * p.imp
    i_cc_dc = np_ * p.isc
    u_co = ns * p.voc

    # --- F-16 et F-17 : tensions aux températures extrêmes ---
    voc_max = tension_corrigee(u_co, p.coef_voc, t_cell_min)
    vmp_min = tension_corrigee(u_dc, p.coef_vmp, t_cell_max)
    vmp_max = tension_corrigee(u_dc, p.coef_vmp, t_cell_min)

    voc_unitaire_froid = tension_corrigee(p.voc, p.coef_voc, t_cell_min)

    # --- Étape 11 : vérifications ---
    if u_dc > us_v:
        messages.append(
            msg(
                "PV-E03",
                u_dc=u_dc,
                us=us_v,
                ns_max=fmt_entier(floor_safe(us_v / p.vmp)),
                valeur=u_dc,
                limite=us_v,
                unite="V",
                champs=("pv.ns_manuel",),
            )
        )

    if voc_max > p.vsys_max:
        messages.append(
            msg(
                "PV-E04",
                voc=voc_max,
                vsys_max=fmt(p.vsys_max, 0),
                ns_max=fmt_entier(ns_maximal_sous(p.vsys_max, voc_unitaire_froid)),
                valeur=voc_max,
                limite=p.vsys_max,
                unite="V",
                champs=("pv.ns_manuel",),
            )
        )

    # Arbitrage A-02 : en mode `voc_froid`, Us est une limite absolue ; sinon,
    # le dépassement n'est qu'un avertissement, les limites physiques étant
    # couvertes par PV-E04 et OND-E01.
    if voc_max > us_v:
        code = "PV-E06" if e.tension_reference_ns == "voc_froid" else "PV-A04"
        messages.append(
            msg(
                code,
                voc=voc_max,
                us=us_v,
                ns_max=fmt_entier(ns_maximal_sous(us_v, voc_unitaire_froid)),
                valeur=voc_max,
                limite=us_v,
                unite="V",
                champs=("pv.ns_manuel", "pv.tension_reference_ns"),
            )
        )

    if vmp_max > us_v:
        messages.append(
            msg(
                "PV-A05",
                vmp=vmp_max,
                us=us_v,
                valeur=vmp_max,
                limite=us_v,
                unite="V",
                champs=("pv.ns_manuel",),
            )
        )

    if pc_installee < pc_retenue_kwc:
        messages.append(
            msg(
                "PV-A01",
                pc_installee=pc_installee,
                pc_retenue=pc_retenue_kwc,
                couverture=fmt_pct(pc_installee / pc_retenue_kwc, 1),
                valeur=pc_installee,
                limite=pc_retenue_kwc,
                unite="kWc",
                champs=("pv.np_manuel",),
            )
        )

    if n_total > n_min:
        messages.append(
            msg(
                "PV-I01",
                ajoutes=fmt_entier(n_total - n_min),
                n_total=fmt_entier(n_total),
                n_min=fmt_entier(n_min),
            )
        )

    taux_utilisation = u_dc / us_v if us_v > 0 else 0.0
    if taux_utilisation < TAUX_UTILISATION_FAIBLE:
        messages.append(
            msg(
                "PV-I02",
                taux=fmt_pct(taux_utilisation, 1),
                valeur=taux_utilisation,
                champs=("pv.ns_manuel",),
            )
        )

    valeurs = PvValeurs(
        n_min=n_min,
        ns=ns,
        np=np_,
        n_total=n_total,
        pc_installee_kwc=pc_installee,
        u_dc_v=u_dc,
        i_dc_a=i_dc,
        i_cc_dc_a=i_cc_dc,
        u_co_v=u_co,
        t_cell_min_c=t_cell_min,
        t_cell_max_c=t_cell_max,
        voc_max_v=voc_max,
        vmp_min_v=vmp_min,
        vmp_max_v=vmp_max,
        u_ref_v=u_ref,
        taux_utilisation_us=taux_utilisation,
    )
    return valeurs, messages


def message_courant_eleve(
    pv: PvValeurs, onduleurs_repartissent: bool
) -> list[Message]:
    """PV-I03, émis seulement si aucun onduleur ne répartit le courant.

    Sans cette condition, le message serait permanent au-delà d'environ
    600 kWc et deviendrait du bruit (anomalie A-06).
    """
    if onduleurs_repartissent or pv.i_dc_a <= C.I_DC_CHAMP_ELEVE_A:
        return []
    return [
        msg(
            "PV-I03",
            i_dc=pv.i_dc_a,
            valeur=pv.i_dc_a,
            limite=C.I_DC_CHAMP_ELEVE_A,
            unite="A",
        )
    ]
