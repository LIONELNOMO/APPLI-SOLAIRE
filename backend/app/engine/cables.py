"""Étapes 20 et 21, et câble alternatif — Câbles (F-24, F-25, F-28)."""

from __future__ import annotations

import math

from . import constantes as C
from .arrondis import normaliser
from .messages import Message, fmt, fmt_entier, fmt_pct, msg
from .modeles import (
    BatteriesValeurs,
    CableAcEntree,
    CableEntree,
    CablesEntree,
    CablesValeurs,
    CableValeurs,
    Critere,
    Materiau,
    OnduleurValeurs,
    Panneau,
    PvValeurs,
)

EPSILON_MAX = 0.05
K_MAX = 1.2
L_DC_MAX_M = 25.0
L_AC_PLAGE_M = (5.0, 50.0)
EPSILONS_CAHIER = (0.01, 0.02)


def rho(
    mode: str,
    materiau: Materiau,
    perso_cu: float | None = None,
    perso_al: float | None = None,
) -> float:
    """Résistivité retenue, en Ω·mm²/m."""
    if mode == "personnalise":
        valeur = perso_cu if materiau == "cuivre" else perso_al
        if valeur is not None and valeur > 0:
            return valeur
        mode = "cahier"
    return C.RHO.get(mode, C.RHO["cahier"])[materiau]


def _verifier_parametres(nom: str, e: CableEntree, est_ac: bool) -> list[Message]:
    """Contrôles communs à tous les câbles (§6.15.4)."""
    messages: list[Message] = []
    if e.longueur_m <= 0:
        messages.append(
            msg("CAB-E01", cable=nom, valeur=e.longueur_m, unite="m")
        )
    if not 0 < e.epsilon <= EPSILON_MAX:
        messages.append(
            msg(
                "CAB-E02",
                cable=nom,
                epsilon=fmt_pct(e.epsilon, 2),
                valeur=e.epsilon,
                limite=EPSILON_MAX,
            )
        )
    if not 0 < e.k_correction <= K_MAX:
        messages.append(
            msg("CAB-E03", cable=nom, k=fmt(e.k_correction, 2), valeur=e.k_correction)
        )

    if est_ac:
        bas, haut = L_AC_PLAGE_M
        if e.longueur_m > 0 and not bas <= e.longueur_m <= haut:
            messages.append(
                msg("CAB-A01", cable=nom, l=fmt(e.longueur_m, 1), valeur=e.longueur_m)
            )
    elif e.longueur_m > L_DC_MAX_M:
        messages.append(
            msg(
                "CAB-A01",
                cable=nom,
                l=fmt(e.longueur_m, 1),
                valeur=e.longueur_m,
                limite=L_DC_MAX_M,
            )
        )

    if e.epsilon > 0 and not any(
        abs(e.epsilon - valeur) < 1e-9 for valeur in EPSILONS_CAHIER
    ):
        messages.append(
            msg("CAB-A02", cable=nom, epsilon=fmt_pct(e.epsilon, 2), valeur=e.epsilon)
        )
    return messages


def dimensionner_cable(
    nom: str,
    i_a: float,
    i_b_a: float,
    u_v: float,
    l_m: float,
    resistivite: float,
    epsilon: float,
    table: dict[float, float],
    k: float = 1.0,
    s_min: float = 1.5,
    s_max: float = 300.0,
    facteur_chute: float = 2.0,
    triphase: bool = False,
    n_max: int = C.N_CONDUCTEURS_MAX,
) -> CableValeurs | None:
    """F-24 et F-25 — Section par la chute de tension, puis par l'échauffement.

    `facteur_chute` vaut 2 pour la formule du cahier (aller-retour), ou
    √3 × cos φ pour la formule triphasée exacte (F-28).
    """
    if min(i_a, u_v, l_m, resistivite, epsilon, k) <= 0:
        return None

    s_calc = facteur_chute * resistivite * l_m * i_a / (epsilon * u_v)
    sections_table = tuple(s for s in C.SECTIONS if s in table)

    for n in range(1, n_max + 1):
        s_chute = normaliser(s_calc / n, sections_table)
        s_thermique = next(
            (s for s in sections_table if n * k * table[s] >= i_b_a), None
        )
        if s_chute is None or s_thermique is None:
            continue

        section = max(s_chute, s_thermique, s_min)
        if section > s_max or section not in table:
            continue

        # Priorité en cas d'égalité : chute, puis échauffement, puis minimum.
        critere: Critere
        if section == s_chute:
            critere = "chute"
        elif section == s_thermique:
            critere = "echauffement"
        else:
            critere = "minimum"

        epsilon_reel = (
            facteur_chute * resistivite * l_m * i_a / (n * section * u_v)
        )
        # Pertes Joule : 2 conducteurs en continu et monophasé, 3 en triphasé.
        coef_joule = 3.0 if triphase else 2.0
        p_joule = coef_joule * resistivite * l_m * i_a**2 / (n * section)

        return CableValeurs(
            nom=nom,
            i_a=i_a,
            u_v=u_v,
            s_calc_mm2=s_calc,
            n_conducteurs=n,
            section_mm2=section,
            critere=critere,
            i_b_a=i_b_a,
            iz_a=n * k * table[section],
            epsilon_reel=epsilon_reel,
            delta_u_v=epsilon_reel * u_v,
            p_joule_w=p_joule,
        )
    return None


def messages_resultat_cable(
    valeurs: CableValeurs, materiau: Materiau, famille: str
) -> list[Message]:
    """Messages d'information issus du dimensionnement d'un câble."""
    messages: list[Message] = []
    if valeurs.n_conducteurs > 1:
        messages.append(
            msg(
                "CAB-A03",
                cable=valeurs.nom,
                n=fmt_entier(valeurs.n_conducteurs),
                section=fmt(valeurs.section_mm2, 0),
            )
        )
    if valeurs.critere == "echauffement":
        messages.append(
            msg(
                "CAB-I01",
                cable=valeurs.nom,
                iz=fmt(valeurs.iz_a, 0),
                i_b=fmt(valeurs.i_b_a, 1),
            )
        )
    elif valeurs.critere == "minimum":
        messages.append(
            msg("CAB-I02", cable=valeurs.nom, section=fmt(valeurs.section_mm2, 1))
        )
    if famille == "pv" and materiau == "aluminium":
        messages.append(msg("CAB-I03", cable=valeurs.nom))
    return messages


def calculer_cables_dc(
    e: CablesEntree,
    pv: PvValeurs | None,
    onduleur: OnduleurValeurs | None,
    batteries: BatteriesValeurs | None,
    p: Panneau | None,
) -> tuple[CablesValeurs | None, list[Message]]:
    """Câbles continus des étapes 20 et 21."""
    messages: list[Message] = []
    valeurs = CablesValeurs()

    if pv is None or p is None:
        messages.append(
            msg("CAB-I05", cause="le champ photovoltaïque n'est pas configuré")
        )
    else:
        valeurs.i_dc_champ_a = pv.i_dc_a

        # --- Étape 20 : câble principal ---
        # Avec plusieurs onduleurs, chacun a son propre câblage (C-21) :
        # on retient l'onduleur le plus chargé, par excès.
        chaines = onduleur.n_ond_max if onduleur else pv.np
        nom_principal = "Câble principal DC"
        messages.extend(
            _verifier_parametres(nom_principal, e.dc_principal, est_ac=False)
        )
        table_pv = C.table_iz("pv", e.dc_principal.materiau)
        resultat = dimensionner_cable(
            nom=nom_principal,
            i_a=chaines * p.imp,
            i_b_a=C.COEF_SECURITE_ISC * chaines * p.isc,
            u_v=pv.u_dc_v,
            l_m=e.dc_principal.longueur_m,
            resistivite=rho(
                e.rho_mode, e.dc_principal.materiau, e.rho_perso_cu, e.rho_perso_al
            ),
            epsilon=e.dc_principal.epsilon,
            table=table_pv,
            k=e.dc_principal.k_correction,
            s_min=C.S_MIN["pv"][e.dc_principal.materiau],
            s_max=C.S_MAX["pv"],
        )
        if resultat is None:
            messages.append(
                msg(
                    "CAB-E04",
                    cable=nom_principal,
                    i=fmt(chaines * p.imp, 1),
                    n_max=fmt_entier(C.N_CONDUCTEURS_MAX),
                )
            )
        else:
            valeurs.dc_principal = resultat
            messages.extend(
                messages_resultat_cable(resultat, e.dc_principal.materiau, "pv")
            )
            if chaines > 2:
                messages.append(msg("CAB-I04", n=fmt_entier(chaines)))

        # --- Câble de chaîne ---
        nom_chaine = "Câble de chaîne"
        messages.extend(_verifier_parametres(nom_chaine, e.dc_chaine, est_ac=False))
        table_chaine = C.table_iz("pv", e.dc_chaine.materiau)
        resultat_chaine = dimensionner_cable(
            nom=nom_chaine,
            i_a=p.imp,
            i_b_a=C.COEF_SECURITE_ISC * p.isc,
            u_v=pv.u_dc_v,
            l_m=e.dc_chaine.longueur_m,
            resistivite=rho(
                e.rho_mode, e.dc_chaine.materiau, e.rho_perso_cu, e.rho_perso_al
            ),
            epsilon=e.dc_chaine.epsilon,
            table=table_chaine,
            k=e.dc_chaine.k_correction,
            s_min=C.S_MIN["pv"][e.dc_chaine.materiau],
            s_max=C.S_MAX["pv"],
        )
        if resultat_chaine is None:
            messages.append(
                msg(
                    "CAB-E04",
                    cable=nom_chaine,
                    i=fmt(p.imp, 1),
                    n_max=fmt_entier(C.N_CONDUCTEURS_MAX),
                )
            )
        else:
            valeurs.dc_chaine = resultat_chaine
            messages.extend(
                messages_resultat_cable(resultat_chaine, e.dc_chaine.materiau, "pv")
            )

        # Chute continue totale : les deux chutes se rapportent à la même U_DC.
        if valeurs.dc_principal and valeurs.dc_chaine:
            total = (
                valeurs.dc_principal.epsilon_reel + valeurs.dc_chaine.epsilon_reel
            )
            valeurs.epsilon_dc_total = total
            if total > C.EPSILON_DC_TOTAL_MAX:
                messages.append(
                    msg(
                        "CAB-A04",
                        epsilon=fmt_pct(total, 2),
                        valeur=total,
                        limite=C.EPSILON_DC_TOTAL_MAX,
                    )
                )

    # --- Étape 21 : câble des batteries ---
    if batteries is None:
        messages.append(
            msg("CAB-I05", cause="le parc de batteries n'est pas dimensionné")
        )
    else:
        nom_batteries = "Câble batteries"
        messages.extend(
            _verifier_parametres(nom_batteries, e.dc_batteries, est_ac=False)
        )
        table_batteries = C.table_iz("pr2", e.dc_batteries.materiau)
        resultat_batteries = dimensionner_cable(
            nom=nom_batteries,
            i_a=batteries.i_parc_a,
            i_b_a=max(batteries.i_parc_a, batteries.i_dech_a),
            u_v=batteries.u_parc_v,
            l_m=e.dc_batteries.longueur_m,
            resistivite=rho(
                e.rho_mode, e.dc_batteries.materiau, e.rho_perso_cu, e.rho_perso_al
            ),
            epsilon=e.dc_batteries.epsilon,
            table=table_batteries,
            k=e.dc_batteries.k_correction,
            s_min=C.S_MIN["batteries"][e.dc_batteries.materiau],
            s_max=C.S_MAX["batteries"],
        )
        if resultat_batteries is None:
            messages.append(
                msg(
                    "CAB-E04",
                    cable=nom_batteries,
                    i=fmt(batteries.i_parc_a, 1),
                    n_max=fmt_entier(C.N_CONDUCTEURS_MAX),
                )
            )
        else:
            valeurs.dc_batteries = resultat_batteries
            messages.extend(
                messages_resultat_cable(
                    resultat_batteries, e.dc_batteries.materiau, "batteries"
                )
            )

    if (
        valeurs.dc_principal is None
        and valeurs.dc_chaine is None
        and valeurs.dc_batteries is None
    ):
        return None, messages
    return valeurs, messages


def facteur_chute_ac(formule: str, phases: int, cos_phi: float) -> tuple[float, bool]:
    """Facteur de la formule de chute alternative et indicateur triphasé.

    La formule du cahier conserve le facteur 2 ; la formule exacte retient
    √3 × cos φ en triphasé (correction C-14, vérifiée en A-01).
    """
    triphase = phases == 3
    if formule == "triphasee_exacte":
        return (math.sqrt(3.0) * cos_phi if triphase else 2.0 * cos_phi), triphase
    return 2.0, triphase


def calculer_cable_ac(
    nom: str,
    e: CableAcEntree,
    i_a: float,
    i_b_a: float,
    u_v: float,
    phases: int,
    cos_phi: float,
    rho_mode: str,
    rho_perso_cu: float | None = None,
    rho_perso_al: float | None = None,
) -> tuple[CableValeurs | None, list[Message]]:
    """Câble alternatif basse tension, onduleur vers transformateur (§7.4)."""
    messages = _verifier_parametres(nom, e, est_ac=True)
    facteur, triphase = facteur_chute_ac(e.formule, phases, cos_phi)
    table = C.table_iz("pr3", e.materiau)

    resultat = dimensionner_cable(
        nom=nom,
        i_a=i_a,
        i_b_a=i_b_a,
        u_v=u_v,
        l_m=e.longueur_m,
        resistivite=rho(rho_mode, e.materiau, rho_perso_cu, rho_perso_al),
        epsilon=e.epsilon,
        table=table,
        k=e.k_correction,
        s_min=C.S_MIN["ac"][e.materiau],
        s_max=C.S_MAX["ac"],
        facteur_chute=facteur,
        triphase=triphase,
    )
    if resultat is None:
        messages.append(
            msg(
                "CAB-E04",
                cable=nom,
                i=fmt(i_a, 1),
                n_max=fmt_entier(C.N_CONDUCTEURS_MAX),
            )
        )
        return None, messages

    messages.extend(messages_resultat_cable(resultat, e.materiau, "ac"))
    return resultat, messages
