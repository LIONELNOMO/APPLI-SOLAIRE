"""Schémas Pydantic d'entrée et de sortie du moteur (§11 d'ARCHITECTURE.md).

Source unique des types : ces modèles servent l'API, la base de données,
l'export et la génération des types TypeScript.

Pydantic ne valide que les types et les structures. Les bornes métier
(0 à 700 V, 0 à 60 MWc, …) sont vérifiées par le moteur sous forme de
messages, pour que l'interface puisse toujours afficher les résultats
partiels (principe P3).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .messages import Message, Statut

Materiau = Literal["cuivre", "aluminium"]
Mode = Literal["auto", "manuel"]
Critere = Literal["chute", "echauffement", "minimum"]
VERSION_MOTEUR = "1.0.0"
VERSION_SCHEMA = 1


# ======================================================================
# Fiches d'équipement
# ======================================================================
class Panneau(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    fabricant: str = ""
    technologie: str = ""
    pmax: float
    vmp: float
    voc: float
    imp: float
    isc: float
    coef_voc: float
    coef_vmp: float
    coef_pmax: float = 0.0
    noct: float = 45.0
    vsys_max: float = 1000.0
    source: Literal["systeme", "utilisateur"] = "systeme"


class Onduleur(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    fabricant: str = ""
    pnom_ac: float
    """Puissance nominale alternative, en kW (clé du cahier des charges)."""
    vmppt_min: float
    vmppt_max: float
    vabs_max: float
    i_max_per_mppt: float
    nb_mppt: int
    strings_per_mppt: int
    u_ac: float = 400.0
    phases: Literal[1, 3] = 3
    isc_max_per_mppt: float | None = None
    ratio_dc_ac_max_fab: float = 1.5
    source: Literal["systeme", "utilisateur"] = "systeme"


class Batterie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    fabricant: str = ""
    technologie: Literal["lithium", "plomb"] = "lithium"
    u_nom: float
    capacite_ah: float
    dod_recommandee: float
    dod_max: float
    cycles: int
    i_nom: float
    rendement: float
    u_charge_max: float
    u_decharge_min: float
    ns_max: int = 1
    np_max: int | None = None
    source: Literal["systeme", "utilisateur"] = "systeme"


class Equipement(BaseModel):
    """Fiche de la bibliothèque d'appareils (§8.4)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    appareil: str
    categorie: str = ""
    puissance_w: float
    quantite_defaut: int = 0
    heures_j: float
    ks: float = 1.0
    source: Literal["systeme", "utilisateur"] = "systeme"


# ======================================================================
# Entrées
# ======================================================================
class PotentielEntree(BaseModel):
    ghi_valeur: float = 192.625
    ghi_unite: Literal["w_m2_moy24h", "kwh_m2_j", "kwh_m2_an"] = "w_m2_moy24h"
    """Arbitrage A-01 : lecture par défaut en irradiance moyenne sur 24 h."""
    profil_mensuel_kwh_m2_j: list[float] | None = None
    source_ghi: str = "Cahier des charges (à confirmer)"
    surface_valeur: float | None = None
    surface_unite: Literal["m2", "ha", "km2"] = "m2"
    taux_occupation: float = 0.50
    rendement_module: float = 0.21


class LigneEquipement(BaseModel):
    actif: bool = True
    nom: str
    categorie: str = ""
    puissance_w: float
    quantite: int
    heures_j: float
    ks: float = 1.0
    ref_bibliotheque: str | None = None


class ProfilAbonnes(BaseModel):
    id: str = "profil-1"
    nom: str = "Ménage type"
    nb_abonnes: int = 0
    lignes: list[LigneEquipement] = Field(default_factory=list)


class BilanEntree(BaseModel):
    profils: list[ProfilAbonnes] = Field(default_factory=list)


class ProductionEntree(BaseModel):
    taux_couverture: float = 1.0
    performance_ratio: float = 0.75
    critere_ir: Literal["moyenne_annuelle", "mois_defavorable"] = "moyenne_annuelle"
    mode_pc: Literal["calculee", "imposee"] = "calculee"
    pc_imposee_kwc: float | None = None
    tension_systeme_v: float = 600.0


class PvEntree(BaseModel):
    fiche: Panneau | None = None
    mode_config: Mode = "auto"
    tension_reference_ns: Literal["vmp", "voc", "voc_froid"] = "vmp"
    """Arbitrage A-02 : Vmp par défaut, règle de l'art."""
    ns_manuel: int | None = None
    np_manuel: int | None = None
    t_amb_min_c: float = 10.0
    t_amb_max_c: float = 35.0
    g_ref_w_m2: float = 1000.0


class OnduleurEntree(BaseModel):
    fiche: Onduleur | None = None
    mode_nombre: Mode = "auto"
    nb_manuel: int | None = None
    ratio_dc_ac_max: float = 1.20
    limiter_courant_mppt: bool = False
    cos_phi: float = 0.90


class BatteriesEntree(BaseModel):
    actif: bool = True
    fiche: Batterie | None = None
    base_energie: Literal["abonne", "zone", "personnalisee"] = "abonne"
    profil_id: str | None = None
    energie_perso_kwh_j: float | None = None
    puissance_perso_w: float | None = None
    part_stockee: float = 1.0
    jours_autonomie: float = 1.0
    dod: float | None = None
    """None : la profondeur recommandée de la fiche est retenue."""
    rendement_batterie: float | None = None
    rendement_onduleur: float = 0.96
    marge: float = 1.0
    mode_tension: Mode = "auto"
    tension_parc_v: float | None = None
    tension_max_v: float = 48.0
    """Arbitrage A-03 : borne du cahier des charges, négociable."""
    u_conv_min_v: float | None = None
    u_conv_max_v: float | None = None
    mode_config: Mode = "auto"
    ns_manuel: int | None = None
    np_manuel: int | None = None


class CableEntree(BaseModel):
    materiau: Materiau = "cuivre"
    longueur_m: float = 10.0
    """Longueur aller simple ; le facteur 2 de F-24 compte l'aller-retour."""
    epsilon: float = 0.01
    k_correction: float = 1.0


class CableAcEntree(CableEntree):
    longueur_m: float = 20.0
    formule: Literal["cahier", "triphasee_exacte"] = "cahier"


class CablesEntree(BaseModel):
    rho_mode: Literal["cahier", "service", "personnalise"] = "cahier"
    rho_perso_cu: float | None = None
    rho_perso_al: float | None = None
    dc_principal: CableEntree = Field(default_factory=CableEntree)
    dc_chaine: CableEntree = Field(default_factory=CableEntree)
    dc_batteries: CableEntree = Field(
        default_factory=lambda: CableEntree(longueur_m=2.0)
    )


class InjectionEntree(BaseModel):
    transfo_mode: Mode = "auto"
    transfo_s_kva: float | None = None
    transfo_marge: float = 0.0
    u_hta_kv: float = 15.0
    p0_w: float | None = None
    pk_w: float | None = None
    cable_ac: CableAcEntree = Field(default_factory=CableAcEntree)
    k_disjoncteur: float = 1.25
    mode: Literal["totale", "surplus"] = "totale"
    taux_autoconsommation: float = 0.40
    pertes_ac_incluses_pr: bool = False
    tarif_fcfa_kwh: float | None = None
    facteur_co2_kg_kwh: float | None = None


class Meta(BaseModel):
    nom: str = "Nouveau projet"
    zone: str = "Yaoundé Ouest"
    auteur: str = ""
    notes: str = ""
    version_schema: int = VERSION_SCHEMA


class ProjetEntree(BaseModel):
    meta: Meta = Field(default_factory=Meta)
    potentiel: PotentielEntree = Field(default_factory=PotentielEntree)
    bilan: BilanEntree = Field(default_factory=BilanEntree)
    production: ProductionEntree = Field(default_factory=ProductionEntree)
    pv: PvEntree = Field(default_factory=PvEntree)
    onduleur: OnduleurEntree = Field(default_factory=OnduleurEntree)
    batteries: BatteriesEntree = Field(default_factory=BatteriesEntree)
    cables: CablesEntree = Field(default_factory=CablesEntree)
    injection: InjectionEntree = Field(default_factory=InjectionEntree)


# ======================================================================
# Sorties
# ======================================================================
class PotentielValeurs(BaseModel):
    h_kwh_m2_j: float
    h_an_kwh_m2_an: float
    g_moy_w_m2: float
    h_mensuel_kwh_m2_j: list[float]
    h_min_kwh_m2_j: float
    mois_defavorable: int
    """Index de 1 à 12 du mois le plus défavorable."""
    surface_m2: float | None = None
    e_pot_j_kwh: float | None = None
    e_pot_mensuel_kwh: list[float] | None = None
    e_pot_an_kwh: float | None = None
    pc_max_surface_kwc: float | None = None
    e_tech_an_kwh: float | None = None


class LigneBilanValeurs(BaseModel):
    nom: str
    categorie: str = ""
    e_wh_j: float
    part_pct: float


class ProfilBilanValeurs(BaseModel):
    id: str
    nom: str
    nb_abonnes: int
    e_cons_wh_j: float
    p_inst_w: float
    p_app_w: float
    e_profil_zone_wh_j: float
    lignes: list[LigneBilanValeurs]


class RepartitionCategorie(BaseModel):
    categorie: str
    e_wh_j: float
    part_pct: float


class BilanValeurs(BaseModel):
    profils: list[ProfilBilanValeurs]
    e_zone_wh_j: float
    e_zone_mensuel_kwh: list[float]
    e_zone_an_kwh: float
    p_inst_zone_w: float
    p_app_zone_w: float
    repartition_categories: list[RepartitionCategorie]


class ProductionSerie(BaseModel):
    mensuel_kwh: list[float]
    an_kwh: float
    j_kwh: float
    y_kwh_kwc: float
    """Productible spécifique, en kWh/kWc/an."""


class ProductionValeurs(BaseModel):
    ir_kwh_m2_j: float
    e_cible_kwh_j: float
    pc_calculee_kwc: float | None = None
    pc_retenue_kwc: float
    prod_theorique: ProductionSerie | None = None
    prod_installee: ProductionSerie | None = None
    taux_couverture_effectif: float | None = None


class PvValeurs(BaseModel):
    n_min: int
    ns: int
    np: int
    n_total: int
    pc_installee_kwc: float
    u_dc_v: float
    i_dc_a: float
    i_cc_dc_a: float
    u_co_v: float
    t_cell_min_c: float
    t_cell_max_c: float
    voc_max_v: float
    vmp_min_v: float
    vmp_max_v: float
    u_ref_v: float
    taux_utilisation_us: float


class RepartitionOnduleur(BaseModel):
    chaines: int
    nombre: int
    """Nombre d'onduleurs recevant ce nombre de chaînes."""


class OnduleurValeurs(BaseModel):
    n_p: int
    n_e: int
    n_cap: int
    n_ond: int
    repartition: list[RepartitionOnduleur]
    n_ond_max: int
    n_mppt_max: int
    ratio_dc_ac: float
    p_dc_ond_kwc: float
    ratio_ond: float
    p_racc_max_kwc: float
    i_dc_ond_a: float
    i_mppt_a: float
    i_cc_mppt_a: float
    ns_min: int
    ns_max: int
    entrees_libres: int
    iac_a: float
    iac_total_a: float
    s_ond_kva: float
    p_ac_total_kw: float
    s_ac_total_kva: float


class BatteriesValeurs(BaseModel):
    e_base_wh_j: float
    p_base_w: float
    tension_recommandee_v: int
    u_parc_visee_v: float
    e_bat_wh: float
    c_bat_ah: float
    ns: int
    n_min: int
    np: int
    n_total: int
    u_parc_v: float
    i_parc_a: float
    c_parc_ah: float
    e_inst_wh: float
    e_util_wh: float
    autonomie_j: float
    i_dech_a: float
    u_parc_min_v: float
    u_parc_max_v: float
    duree_vie_ans: float
    n_total_zone: int | None = None


class CableValeurs(BaseModel):
    nom: str
    i_a: float
    u_v: float
    s_calc_mm2: float
    n_conducteurs: int
    section_mm2: float
    critere: Critere
    i_b_a: float
    iz_a: float
    epsilon_reel: float
    delta_u_v: float
    p_joule_w: float


class CablesValeurs(BaseModel):
    dc_principal: CableValeurs | None = None
    dc_chaine: CableValeurs | None = None
    dc_batteries: CableValeurs | None = None
    epsilon_dc_total: float | None = None
    i_dc_champ_a: float | None = None


class BilanMensuelInjection(BaseModel):
    mois: int
    e_prod: float
    e_cable_ac: float
    e_auto: float
    e_tr: float
    e_p0: float
    e_pk: float
    e_inj: float


class InjectionValeurs(BaseModel):
    s_requise_kva: float
    n_max_par_tr: int
    n_tr: int
    repartition_tr: list[RepartitionOnduleur]
    s_n_kva: float
    s_installee_kva: float
    taux_charge_max: float
    taux_charge: float
    i_n_bt_a: float
    i_bt_max_a: float
    i_n_hta_a: float
    p0_w: float
    pk_w: float
    cable_ac: CableValeurs | None = None
    in_disjoncteur_a: float | None = None
    bilan_mensuel: list[BilanMensuelInjection] | None = None
    e_inj_an_kwh: float | None = None
    taux_injection: float | None = None
    h_eq: float | None = None
    facteur_charge: float | None = None
    couverture_zone: float | None = None
    part_autoconsommee: float | None = None
    recettes_fcfa_an: float | None = None
    co2_evite_t_an: float | None = None


class SortieModule[T](BaseModel):
    statut: Statut
    valeurs: T | None = None


class ResultatsProjet(BaseModel):
    version_moteur: str = VERSION_MOTEUR
    horodatage: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    statut_global: Statut
    messages: list[Message] = Field(default_factory=list)
    potentiel: SortieModule[PotentielValeurs]
    bilan: SortieModule[BilanValeurs]
    production: SortieModule[ProductionValeurs]
    pv: SortieModule[PvValeurs]
    onduleur: SortieModule[OnduleurValeurs]
    batteries: SortieModule[BatteriesValeurs]
    cables: SortieModule[CablesValeurs]
    injection: SortieModule[InjectionValeurs]
