"""Module 4 — Injection au réseau (F-26 à F-30)."""

from __future__ import annotations

import math

from . import constantes as C
from .arrondis import ceil_safe, floor_safe, normaliser
from .cables import calculer_cable_ac
from .messages import Message, fmt, fmt_entier, fmt_pct, msg
from .modeles import (
    BilanMensuelInjection,
    InjectionEntree,
    InjectionValeurs,
    Onduleur,
    OnduleurValeurs,
    RepartitionOnduleur,
)

TAUX_CHARGE_FAIBLE = 0.50
N_TR_ELEVE = 10
U_AC_ATTENDUE_V = 400.0


def _repartir_transfos(
    n_ond: int, n_tr: int
) -> tuple[list[RepartitionOnduleur], int]:
    """Répartition des onduleurs entre transformateurs."""
    q, r = divmod(n_ond, n_tr)
    repartition: list[RepartitionOnduleur] = []
    if r > 0:
        repartition.append(RepartitionOnduleur(chaines=q + 1, nombre=r))
    if n_tr - r > 0:
        repartition.append(RepartitionOnduleur(chaines=q, nombre=n_tr - r))
    return repartition, (q + 1 if r > 0 else q)


def calculer_injection(
    e: InjectionEntree,
    onduleur: OnduleurValeurs | None,
    o: Onduleur | None,
    prod_installee_mensuel_kwh: list[float] | None,
    e_zone_wh_j: float,
    cos_phi: float,
    rho_mode: str,
    rho_perso_cu: float | None = None,
    rho_perso_al: float | None = None,
) -> tuple[InjectionValeurs | None, list[Message]]:
    """Transformateur, câble alternatif, disjoncteur et bilan d'injection."""
    messages: list[Message] = []

    if onduleur is None or o is None:
        messages.append(
            msg("INJ-E04", cause="les onduleurs ne sont pas dimensionnés")
        )
        return None, messages

    # --- Contrôles des paramètres ---
    details: list[str] = []
    if not 0 <= e.transfo_marge <= 0.5:
        details.append(f"marge de {fmt_pct(e.transfo_marge, 0)} %")
    if not 1.0 <= e.k_disjoncteur <= 1.5:
        details.append(f"coefficient du disjoncteur de {fmt(e.k_disjoncteur, 2)}")
    if not 0 <= e.taux_autoconsommation <= 1:
        details.append(
            f"taux d'autoconsommation de {fmt_pct(e.taux_autoconsommation, 0)} %"
        )
    if e.u_hta_kv <= 0:
        details.append("tension HTA")
    if (e.p0_w is not None and e.p0_w < 0) or (e.pk_w is not None and e.pk_w < 0):
        details.append("pertes du transformateur")
    if details:
        messages.append(msg("INJ-E06", detail=", ".join(details), champs=("injection",)))
        return None, messages

    if abs(o.u_ac - U_AC_ATTENDUE_V) > 1e-9:
        messages.append(
            msg(
                "INJ-A01",
                u_ac=fmt(o.u_ac, 0),
                valeur=o.u_ac,
                limite=U_AC_ATTENDUE_V,
                unite="V",
                champs=("onduleur.fiche",),
            )
        )

    # --- F-26 : transformateurs ---
    s_ond = onduleur.s_ond_kva
    s_unitaire_marge = s_ond * (1.0 + e.transfo_marge)
    s_requise = onduleur.n_ond * s_unitaire_marge

    if e.transfo_mode == "manuel":
        if e.transfo_s_kva is None or not 0 < e.transfo_s_kva <= C.S_TRANSFO_MAX_KVA:
            messages.append(
                msg(
                    "INJ-E01",
                    s_n=e.transfo_s_kva or 0.0,
                    s_max=fmt(C.S_TRANSFO_MAX_KVA, 0),
                    valeur=e.transfo_s_kva or 0.0,
                    limite=C.S_TRANSFO_MAX_KVA,
                    unite="kVA",
                    champs=("injection.transfo_s_kva",),
                )
            )
            return None, messages
        s_n = e.transfo_s_kva
        n_max = floor_safe(s_n / s_unitaire_marge) if s_unitaire_marge > 0 else 0
    else:
        n_max = (
            floor_safe(C.S_TRANSFO_MAX_KVA / s_unitaire_marge)
            if s_unitaire_marge > 0
            else 0
        )
        s_n = 0.0

    if n_max < 1:
        messages.append(
            msg(
                "INJ-E03",
                s_ond=s_ond,
                s_n=fmt(s_n or C.S_TRANSFO_MAX_KVA, 0),
                valeur=s_ond,
                limite=s_n or C.S_TRANSFO_MAX_KVA,
                unite="kVA",
                champs=("injection.transfo_s_kva",),
            )
        )
        return None, messages

    n_tr = max(ceil_safe(onduleur.n_ond / n_max), 1)
    repartition_tr, n_tr_max = _repartir_transfos(onduleur.n_ond, n_tr)

    if e.transfo_mode != "manuel":
        normalisee = normaliser(n_tr_max * s_unitaire_marge, C.PUISSANCES_TRANSFOS)
        if normalisee is None:
            messages.append(
                msg(
                    "INJ-E01",
                    s_n=n_tr_max * s_unitaire_marge,
                    s_max=fmt(C.S_TRANSFO_MAX_KVA, 0),
                    valeur=n_tr_max * s_unitaire_marge,
                    limite=C.S_TRANSFO_MAX_KVA,
                    unite="kVA",
                )
            )
            return None, messages
        s_n = normalisee

    # --- Pertes ---
    p0_defaut, pk_defaut = C.pertes_transfo(s_n)
    p0 = e.p0_w if e.p0_w is not None else p0_defaut
    pk = e.pk_w if e.pk_w is not None else pk_defaut
    if e.p0_w is None or e.pk_w is None:
        messages.append(
            msg("INJ-I02", p0=fmt(p0, 0), pk=fmt(pk, 0), champs=("injection.p0_w",))
        )

    # --- Grandeurs dérivées ---
    s_installee = n_tr * s_n
    taux_charge_max = n_tr_max * s_ond / s_n if s_n > 0 else 0.0
    taux_charge = onduleur.n_ond * s_ond / s_installee if s_installee > 0 else 0.0
    racine3 = math.sqrt(3.0)
    i_n_bt = s_n * 1000.0 / (racine3 * o.u_ac)
    i_bt_max = n_tr_max * onduleur.iac_a
    i_n_hta = s_n / (racine3 * e.u_hta_kv)

    if i_bt_max > i_n_bt:
        messages.append(
            msg(
                "INJ-E02",
                i_bt=fmt(i_bt_max, 1),
                i_n=fmt(i_n_bt, 1),
                valeur=i_bt_max,
                limite=i_n_bt,
                unite="A",
                champs=("injection.transfo_s_kva",),
            )
        )
    if taux_charge < TAUX_CHARGE_FAIBLE:
        messages.append(
            msg(
                "INJ-A02",
                taux=fmt_pct(taux_charge, 1),
                valeur=taux_charge,
                limite=TAUX_CHARGE_FAIBLE,
                champs=("injection.transfo_s_kva",),
            )
        )
    if n_tr > N_TR_ELEVE:
        messages.append(
            msg("INJ-A03", n_tr=fmt_entier(n_tr), valeur=float(n_tr))
        )

    # --- F-27 : disjoncteur, avant le câble pour la coordination ---
    i_requis = e.k_disjoncteur * onduleur.iac_a
    calibre = normaliser(i_requis, C.CALIBRES_DISJONCTEURS)
    if calibre is None:
        messages.append(
            msg(
                "INJ-E05",
                i_requis=fmt(i_requis, 1),
                valeur=i_requis,
                limite=C.CALIBRES_DISJONCTEURS[-1],
                unite="A",
                champs=("injection.k_disjoncteur",),
            )
        )

    # --- §7.4 : câble alternatif, dimensionné avec I_B = In ---
    cable_ac = None
    if calibre is not None:
        cable_ac, messages_cable = calculer_cable_ac(
            nom="Câble AC BT",
            e=e.cable_ac,
            i_a=onduleur.iac_a,
            i_b_a=calibre,
            u_v=o.u_ac,
            phases=o.phases,
            cos_phi=cos_phi,
            rho_mode=rho_mode,
            rho_perso_cu=rho_perso_cu,
            rho_perso_al=rho_perso_al,
        )
        messages.extend(messages_cable)

    valeurs = InjectionValeurs(
        s_requise_kva=s_requise,
        n_max_par_tr=n_max,
        n_tr=n_tr,
        repartition_tr=repartition_tr,
        s_n_kva=s_n,
        s_installee_kva=s_installee,
        taux_charge_max=taux_charge_max,
        taux_charge=taux_charge,
        i_n_bt_a=i_n_bt,
        i_bt_max_a=i_bt_max,
        i_n_hta_a=i_n_hta,
        p0_w=p0,
        pk_w=pk,
        cable_ac=cable_ac,
        in_disjoncteur_a=calibre,
    )

    # --- F-29 et F-30 : bilan de l'injection ---
    if prod_installee_mensuel_kwh is None:
        messages.append(msg("INJ-I04"))
        return valeurs, messages

    # Hypothèse H-02 : la production est l'énergie alternative en sortie
    # d'onduleur. Le facteur de pertes est rapporté à la puissance nominale,
    # ce qui majore les pertes (elles valent P_J au point nominal seulement).
    f_ac = 0.0
    if cable_ac is not None and o.pnom_ac > 0:
        f_ac = cable_ac.p_joule_w / (o.pnom_ac * 1000.0)
    if e.pertes_ac_incluses_pr:
        messages.append(msg("INJ-I01", champs=("injection.pertes_ac_incluses_pr",)))

    e_zone_kwh_j = e_zone_wh_j / 1000.0
    bilan: list[BilanMensuelInjection] = []
    # Puissance nominale active d'un transformateur, pour les pertes en charge.
    p_n_kw = s_n * cos_phi

    for index, (e_prod, jours) in enumerate(
        zip(prod_installee_mensuel_kwh, C.JOURS_MOIS, strict=True)
    ):
        e_cable = 0.0 if e.pertes_ac_incluses_pr else f_ac * e_prod
        e_bt = e_prod - e_cable

        e_auto = 0.0
        if e.mode == "surplus":
            e_auto = min(e_bt, e.taux_autoconsommation * e_zone_kwh_j * jours)
        e_tr = e_bt - e_auto

        e_p0 = n_tr * p0 * 24.0 * jours / 1000.0
        e_pk = 0.0
        if n_tr > 0 and p_n_kw > 0:
            # Majorant : Pk × Σ(P/Pn)² × Δt ≤ Pk × (P_max/Pn) × (E/Pn).
            e_pk = (
                (pk / 1000.0)
                * onduleur.p_ac_total_kw
                * e_tr
                / (n_tr * p_n_kw**2)
            )
        e_inj = e_tr - e_p0 - e_pk

        if e_inj < 0:
            messages.append(msg("INJ-A04", mois=C.MOIS_NOMS[index]))

        bilan.append(
            BilanMensuelInjection(
                mois=index + 1,
                e_prod=e_prod,
                e_cable_ac=e_cable,
                e_auto=e_auto,
                e_tr=e_tr,
                e_p0=e_p0,
                e_pk=e_pk,
                e_inj=e_inj,
            )
        )

    e_prod_an = sum(prod_installee_mensuel_kwh)
    e_inj_an = sum(b.e_inj for b in bilan)
    e_auto_an = sum(b.e_auto for b in bilan)
    e_zone_an_kwh = e_zone_kwh_j * C.JOURS_AN

    valeurs.bilan_mensuel = bilan
    valeurs.e_inj_an_kwh = e_inj_an
    valeurs.taux_injection = e_inj_an / e_prod_an if e_prod_an > 0 else None
    valeurs.h_eq = (
        e_inj_an / onduleur.p_ac_total_kw if onduleur.p_ac_total_kw > 0 else None
    )
    if valeurs.h_eq is not None:
        valeurs.facteur_charge = valeurs.h_eq / C.HEURES_AN
    if e_zone_an_kwh > 0:
        if e.mode == "totale":
            valeurs.couverture_zone = e_inj_an / e_zone_an_kwh
        else:
            valeurs.part_autoconsommee = e_auto_an / e_zone_an_kwh

    if e.tarif_fcfa_kwh is not None:
        valeurs.recettes_fcfa_an = e_inj_an * e.tarif_fcfa_kwh
    if e.facteur_co2_kg_kwh is not None:
        valeurs.co2_evite_t_an = e_inj_an * e.facteur_co2_kg_kwh / 1000.0
    if e.tarif_fcfa_kwh is None or e.facteur_co2_kg_kwh is None:
        messages.append(msg("INJ-I03", champs=("injection.tarif_fcfa_kwh",)))

    messages.append(msg("INJ-I04"))
    return valeurs, messages
