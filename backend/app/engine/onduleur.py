"""Module 3, étapes 12 à 14 — Onduleurs (F-19, F-20)."""

from __future__ import annotations

import math

from . import constantes as C
from .arrondis import ceil_safe, floor_safe
from .champ_pv import tension_corrigee
from .messages import Message, fmt, fmt_entier, fmt_pct, msg
from .modeles import (
    Onduleur,
    OnduleurEntree,
    OnduleurValeurs,
    Panneau,
    PvValeurs,
    RepartitionOnduleur,
)


def fiche_onduleur_valide(o: Onduleur) -> bool:
    """Validation d'une fiche d'onduleur (§8.5)."""
    if o.pnom_ac <= 0 or o.i_max_per_mppt <= 0:
        return False
    if not 0 < o.vmppt_min < o.vmppt_max <= o.vabs_max:
        return False
    if o.nb_mppt < 1 or o.strings_per_mppt < 1:
        return False
    if not 0 < o.u_ac <= 1000:
        return False
    if o.isc_max_per_mppt is not None and o.isc_max_per_mppt < o.i_max_per_mppt:
        return False
    return o.ratio_dc_ac_max_fab >= 1.0


def plage_ns(
    o: Onduleur,
    p: Panneau,
    t_cell_min: float,
    t_cell_max: float,
    us_v: float,
    u_ref_v: float,
) -> tuple[int, int]:
    """Plage de Ns compatible avec l'onduleur et la tension du système (OND-I04).

    Ns_max est borné par la tension absolue de l'onduleur et par Us ;
    Ns_min par le bas de la plage MPPT, atteint par forte chaleur.
    """
    voc_froid = tension_corrigee(p.voc, p.coef_voc, t_cell_min)
    vmp_chaud = tension_corrigee(p.vmp, p.coef_vmp, t_cell_max)

    ns_max = 0
    if voc_froid > 0 and u_ref_v > 0:
        ns_max = min(
            floor_safe(o.vabs_max / voc_froid),
            floor_safe(us_v / u_ref_v),
        )
    ns_min = ceil_safe(o.vmppt_min / vmp_chaud) if vmp_chaud > 0 else 0
    return max(ns_min, 1), max(ns_max, 0)


def _repartir(np_total: int, n_ond: int) -> tuple[list[RepartitionOnduleur], int, int, int]:
    """Répartition des chaînes entre onduleurs : (répartition, n_max, q, r)."""
    q, r = divmod(np_total, n_ond)
    repartition: list[RepartitionOnduleur] = []
    if r > 0:
        repartition.append(RepartitionOnduleur(chaines=q + 1, nombre=r))
    if n_ond - r > 0:
        repartition.append(RepartitionOnduleur(chaines=q, nombre=n_ond - r))
    n_max = q + 1 if r > 0 else q
    return repartition, n_max, q, r


def dimensionner_onduleurs(
    e: OnduleurEntree,
    pv: PvValeurs | None,
    p: Panneau | None,
    us_v: float,
) -> tuple[OnduleurValeurs | None, list[Message]]:
    """Nombre d'onduleurs, répartition des chaînes et courant alternatif."""
    messages: list[Message] = []
    o = e.fiche

    if o is None:
        messages.append(
            msg("OND-E08", cause="aucun onduleur n'est sélectionné", champs=("onduleur.fiche",))
        )
        return None, messages
    if not fiche_onduleur_valide(o):
        messages.append(msg("OND-E06", champs=("onduleur.fiche",)))
        return None, messages
    if pv is None or p is None:
        messages.append(
            msg("OND-E08", cause="le champ photovoltaïque n'est pas configuré")
        )
        return None, messages

    if not 0 < e.cos_phi <= 1:
        messages.append(
            msg(
                "OND-A05",
                cos_phi=e.cos_phi,
                valeur=e.cos_phi,
                limite=1.0,
                champs=("onduleur.cos_phi",),
            )
        )
    cos_phi = e.cos_phi if 0 < e.cos_phi <= 1 else 0.90

    # --- F-19 : capacité par MPPT ---
    n_cap = o.strings_per_mppt
    if e.limiter_courant_mppt:
        n_cap = min(n_cap, floor_safe(o.i_max_per_mppt / p.imp))
    if n_cap < 1:
        messages.append(
            msg(
                "OND-E07",
                imp=p.imp,
                i_max=o.i_max_per_mppt,
                valeur=p.imp,
                limite=o.i_max_per_mppt,
                unite="A",
                champs=("onduleur.fiche", "pv.fiche"),
            )
        )
        return None, messages

    # --- F-19 : nombre d'onduleurs ---
    n_p = ceil_safe(pv.pc_installee_kwc / (e.ratio_dc_ac_max * o.pnom_ac))
    n_e = ceil_safe(pv.np / (o.nb_mppt * n_cap))

    if e.mode_nombre == "manuel":
        if e.nb_manuel is None or e.nb_manuel < 1:
            messages.append(msg("OND-E09", champs=("onduleur.nb_manuel",)))
            return None, messages
        n_ond = e.nb_manuel
    else:
        n_ond = max(n_p, n_e, 1)

    n_ond = min(n_ond, pv.np) if pv.np >= 1 else n_ond

    repartition, n_ond_max, q, r = _repartir(pv.np, n_ond)
    n_mppt_max = ceil_safe(n_ond_max / o.nb_mppt)

    # --- Grandeurs de l'onduleur le plus chargé ---
    ratio_global = pv.pc_installee_kwc / (n_ond * o.pnom_ac)
    p_dc_ond = n_ond_max * pv.ns * p.pmax / 1000.0
    ratio_ond = p_dc_ond / o.pnom_ac
    p_racc_max = o.nb_mppt * n_cap * pv.ns * p.pmax / 1000.0
    i_dc_ond = n_ond_max * p.imp
    i_mppt = n_mppt_max * p.imp
    i_cc_mppt = n_mppt_max * p.isc
    entrees_libres = n_ond * o.nb_mppt * o.strings_per_mppt - pv.np

    ns_min, ns_max = plage_ns(
        o, p, pv.t_cell_min_c, pv.t_cell_max_c, us_v, pv.u_ref_v
    )

    # --- Étape 13 : les neuf critères ---
    if pv.voc_max_v > o.vabs_max:
        messages.append(
            msg(
                "OND-E01",
                voc=pv.voc_max_v,
                vabs_max=fmt(o.vabs_max, 0),
                ns_max=fmt_entier(ns_max),
                valeur=pv.voc_max_v,
                limite=o.vabs_max,
                unite="V",
                champs=("pv.ns_manuel",),
            )
        )
    if pv.vmp_min_v < o.vmppt_min:
        messages.append(
            msg(
                "OND-E02",
                vmp_min=pv.vmp_min_v,
                vmppt_min=fmt(o.vmppt_min, 0),
                ns_min=fmt_entier(ns_min),
                valeur=pv.vmp_min_v,
                limite=o.vmppt_min,
                unite="V",
                champs=("pv.ns_manuel", "onduleur.fiche"),
            )
        )
    if pv.vmp_max_v > o.vmppt_max:
        messages.append(
            msg(
                "OND-A02",
                vmp_max=pv.vmp_max_v,
                vmppt_max=fmt(o.vmppt_max, 0),
                ns_max=fmt_entier(ns_max),
                valeur=pv.vmp_max_v,
                limite=o.vmppt_max,
                unite="V",
                champs=("pv.ns_manuel",),
            )
        )
    if n_mppt_max > n_cap:
        messages.append(
            msg(
                "OND-E03",
                n_mppt=fmt_entier(n_mppt_max),
                n_cap=fmt_entier(n_cap),
                n_e=fmt_entier(n_e),
                valeur=float(n_mppt_max),
                limite=float(n_cap),
                champs=("onduleur.nb_manuel",),
            )
        )
    if i_mppt > o.i_max_per_mppt:
        exces = i_mppt / o.i_max_per_mppt - 1.0
        messages.append(
            msg(
                "OND-A03",
                i_mppt=i_mppt,
                i_max=o.i_max_per_mppt,
                exces=fmt_pct(exces, 1),
                valeur=i_mppt,
                limite=o.i_max_per_mppt,
                unite="A",
                champs=("onduleur.limiter_courant_mppt",),
            )
        )
    if o.isc_max_per_mppt is None:
        messages.append(msg("OND-I02", champs=("onduleur.fiche",)))
    elif i_cc_mppt > o.isc_max_per_mppt:
        messages.append(
            msg(
                "OND-E04",
                i_cc=i_cc_mppt,
                i_cc_max=o.isc_max_per_mppt,
                valeur=i_cc_mppt,
                limite=o.isc_max_per_mppt,
                unite="A",
                champs=("onduleur.limiter_courant_mppt",),
            )
        )
    if ratio_ond > o.ratio_dc_ac_max_fab:
        messages.append(
            msg(
                "OND-E05",
                ratio=ratio_ond,
                ratio_max=o.ratio_dc_ac_max_fab,
                valeur=ratio_ond,
                limite=o.ratio_dc_ac_max_fab,
                champs=("onduleur.nb_manuel",),
            )
        )
    if ratio_global < C.RATIO_DC_AC_MIN:
        messages.append(
            msg(
                "OND-A01",
                ratio=ratio_global,
                valeur=ratio_global,
                limite=C.RATIO_DC_AC_MIN,
                champs=("onduleur.nb_manuel",),
            )
        )
    elif ratio_global > C.RATIO_DC_AC_MAX:
        messages.append(
            msg(
                "OND-A04",
                ratio=ratio_global,
                valeur=ratio_global,
                limite=C.RATIO_DC_AC_MAX,
                champs=("onduleur.nb_manuel",),
            )
        )
    if p_racc_max < o.pnom_ac:
        messages.append(
            msg(
                "OND-A06",
                p_racc=p_racc_max,
                pnom=fmt(o.pnom_ac, 0),
                valeur=p_racc_max,
                limite=o.pnom_ac,
                unite="kWc",
                champs=("production.tension_systeme_v",),
            )
        )

    if r > 0:
        messages.append(
            msg(
                "OND-I01",
                r=fmt_entier(r),
                q_plus=fmt_entier(q + 1),
                autres=fmt_entier(n_ond - r),
                q=fmt_entier(q),
            )
        )
    if entrees_libres > 0:
        messages.append(msg("OND-I03", entrees=fmt_entier(entrees_libres)))

    messages.append(
        msg("OND-I04", ns_min=fmt_entier(ns_min), ns_max=fmt_entier(ns_max))
    )

    # --- F-20 : courant alternatif de sortie ---
    denominateur = o.u_ac * cos_phi
    if o.phases == 3:
        denominateur *= math.sqrt(3.0)
    iac = o.pnom_ac * 1000.0 / denominateur

    s_ond = o.pnom_ac / cos_phi
    p_ac_total = n_ond * o.pnom_ac

    valeurs = OnduleurValeurs(
        n_p=n_p,
        n_e=n_e,
        n_cap=n_cap,
        n_ond=n_ond,
        repartition=repartition,
        n_ond_max=n_ond_max,
        n_mppt_max=n_mppt_max,
        ratio_dc_ac=ratio_global,
        p_dc_ond_kwc=p_dc_ond,
        ratio_ond=ratio_ond,
        p_racc_max_kwc=p_racc_max,
        i_dc_ond_a=i_dc_ond,
        i_mppt_a=i_mppt,
        i_cc_mppt_a=i_cc_mppt,
        ns_min=ns_min,
        ns_max=ns_max,
        entrees_libres=entrees_libres,
        iac_a=iac,
        iac_total_a=n_ond * iac,
        s_ond_kva=s_ond,
        p_ac_total_kw=p_ac_total,
        s_ac_total_kva=p_ac_total / cos_phi,
    )
    return valeurs, messages
