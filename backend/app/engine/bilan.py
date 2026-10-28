"""Module 2 — Bilan énergétique (onglet 2, formules F-05 à F-08)."""

from __future__ import annotations

from collections import defaultdict

from . import constantes as C
from .messages import Message, fmt_entier, msg
from .modeles import (
    BilanEntree,
    BilanValeurs,
    LigneBilanValeurs,
    LigneEquipement,
    ProfilAbonnes,
    ProfilBilanValeurs,
    RepartitionCategorie,
)
from .unites import wh_vers_kwh

SEUIL_PUISSANCE_ELEVEE_W = 10_000.0
SEUIL_CONTINU_W = 500.0


def _verifier_ligne(
    index: int, ligne: LigneEquipement, champ_base: str
) -> list[Message]:
    """Contrôles d'une ligne d'équipement active (§5.6)."""
    messages: list[Message] = []
    champ = f"{champ_base}.lignes[{index}]"

    if ligne.puissance_w <= 0:
        messages.append(
            msg(
                "BIL-E01",
                nom=ligne.nom,
                valeur=ligne.puissance_w,
                unite="W",
                champs=(f"{champ}.puissance_w",),
            )
        )
    if ligne.quantite < 0:
        messages.append(
            msg(
                "BIL-E02",
                nom=ligne.nom,
                valeur=float(ligne.quantite),
                champs=(f"{champ}.quantite",),
            )
        )
    if not 0 <= ligne.heures_j <= 24:
        messages.append(
            msg(
                "BIL-E03",
                nom=ligne.nom,
                heures=ligne.heures_j,
                valeur=ligne.heures_j,
                limite=24.0,
                unite="h/j",
                champs=(f"{champ}.heures_j",),
            )
        )
    if not 0 <= ligne.ks <= 1:
        messages.append(
            msg(
                "BIL-E04",
                nom=ligne.nom,
                ks=ligne.ks,
                valeur=ligne.ks,
                limite=1.0,
                champs=(f"{champ}.ks",),
            )
        )

    if ligne.puissance_w > SEUIL_PUISSANCE_ELEVEE_W:
        messages.append(
            msg(
                "BIL-A01",
                nom=ligne.nom,
                puissance=fmt_entier(ligne.puissance_w),
                valeur=ligne.puissance_w,
                limite=SEUIL_PUISSANCE_ELEVEE_W,
                unite="W",
                champs=(f"{champ}.puissance_w",),
            )
        )
    if (
        ligne.puissance_w > SEUIL_CONTINU_W
        and ligne.heures_j >= 24
        and ligne.ks >= 1
    ):
        messages.append(
            msg(
                "BIL-A02",
                nom=ligne.nom,
                puissance=fmt_entier(ligne.puissance_w),
                champs=(f"{champ}.heures_j", f"{champ}.ks"),
            )
        )
    return messages


def _calculer_profil(
    profil: ProfilAbonnes, index_profil: int
) -> tuple[ProfilBilanValeurs, list[Message], dict[str, float]]:
    """Consommation et puissances d'un profil d'abonnés (F-05, F-06, F-08)."""
    messages: list[Message] = []
    champ_base = f"bilan.profils[{index_profil}]"

    if profil.nb_abonnes < 0:
        messages.append(
            msg(
                "BIL-E05",
                nom=profil.nom,
                valeur=float(profil.nb_abonnes),
                champs=(f"{champ_base}.nb_abonnes",),
            )
        )

    lignes_valeurs: list[LigneBilanValeurs] = []
    par_categorie: dict[str, float] = defaultdict(float)
    e_cons_wh_j = 0.0
    p_inst_w = 0.0
    p_app_w = 0.0

    for index, ligne in enumerate(profil.lignes):
        if not ligne.actif:
            continue
        # Une quantité nulle est l'état normal d'un appareil de la bibliothèque
        # absent du ménage : aucun contrôle, aucun message.
        if ligne.quantite > 0:
            messages.extend(_verifier_ligne(index, ligne, champ_base))

        # F-05 : énergie journalière d'une ligne.
        e_ligne = (
            max(ligne.puissance_w, 0.0)
            * max(ligne.quantite, 0)
            * max(ligne.heures_j, 0.0)
            * max(ligne.ks, 0.0)
        )
        e_cons_wh_j += e_ligne

        # F-08 : puissances installée et appelée.
        p_ligne = max(ligne.puissance_w, 0.0) * max(ligne.quantite, 0)
        p_inst_w += p_ligne
        p_app_w += p_ligne * max(ligne.ks, 0.0)

        categorie = ligne.categorie or "Divers"
        par_categorie[categorie] += e_ligne
        lignes_valeurs.append(
            LigneBilanValeurs(
                nom=ligne.nom,
                categorie=categorie,
                e_wh_j=e_ligne,
                part_pct=0.0,
            )
        )

    if e_cons_wh_j > 0:
        for valeur in lignes_valeurs:
            valeur.part_pct = valeur.e_wh_j / e_cons_wh_j * 100.0

    nb = max(profil.nb_abonnes, 0)
    if nb == 0:
        messages.append(
            msg("BIL-I01", nom=profil.nom, champs=(f"{champ_base}.nb_abonnes",))
        )

    valeurs = ProfilBilanValeurs(
        id=profil.id,
        nom=profil.nom,
        nb_abonnes=nb,
        e_cons_wh_j=e_cons_wh_j,
        p_inst_w=p_inst_w,
        p_app_w=p_app_w,
        e_profil_zone_wh_j=e_cons_wh_j * nb,
        lignes=lignes_valeurs,
    )
    # Les catégories sont pondérées par le nombre d'abonnés pour la zone.
    categories_zone = {cat: e * nb for cat, e in par_categorie.items()}
    return valeurs, messages, categories_zone


def calculer_bilan(e: BilanEntree) -> tuple[BilanValeurs | None, list[Message]]:
    """Consommation de la zone (F-05 à F-08)."""
    messages: list[Message] = []
    profils: list[ProfilBilanValeurs] = []
    categories_zone: dict[str, float] = defaultdict(float)

    for index, profil in enumerate(e.profils):
        valeurs, messages_profil, categories = _calculer_profil(profil, index)
        profils.append(valeurs)
        messages.extend(messages_profil)
        for categorie, energie in categories.items():
            categories_zone[categorie] += energie

    # F-07 : consommation de la zone.
    e_zone_wh_j = sum(p.e_profil_zone_wh_j for p in profils)
    p_inst_zone_w = sum(p.p_inst_w * p.nb_abonnes for p in profils)
    p_app_zone_w = sum(p.p_app_w * p.nb_abonnes for p in profils)

    if e_zone_wh_j <= 0:
        messages.append(msg("BIL-E06", champs=("bilan.profils",)))
        return None, messages

    repartition = [
        RepartitionCategorie(
            categorie=categorie,
            e_wh_j=energie,
            part_pct=energie / e_zone_wh_j * 100.0,
        )
        for categorie, energie in sorted(
            categories_zone.items(), key=lambda item: item[1], reverse=True
        )
        if energie > 0
    ]

    zone = BilanValeurs(
        profils=profils,
        e_zone_wh_j=e_zone_wh_j,
        e_zone_mensuel_kwh=[
            wh_vers_kwh(e_zone_wh_j * jours) for jours in C.JOURS_MOIS
        ],
        e_zone_an_kwh=wh_vers_kwh(e_zone_wh_j * C.JOURS_AN),
        p_inst_zone_w=p_inst_zone_w,
        p_app_zone_w=p_app_zone_w,
        repartition_categories=repartition,
    )
    return zone, messages
