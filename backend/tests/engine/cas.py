"""Fabrique des entrées des cas de référence R-01 à R-11 (§9 du cahier)."""

from __future__ import annotations

from app.engine.modeles import (
    Batterie,
    BatteriesEntree,
    BilanEntree,
    CableAcEntree,
    CableEntree,
    CablesEntree,
    InjectionEntree,
    LigneEquipement,
    Onduleur,
    OnduleurEntree,
    Panneau,
    PotentielEntree,
    ProductionEntree,
    ProfilAbonnes,
    ProjetEntree,
    PvEntree,
)

# --- Fiches des cas de référence ---------------------------------------
CANADIAN_550 = Panneau(
    id="canadian-550-mono",
    nom="Canadian Solar 550Wp - Mono",
    fabricant="Canadian",
    technologie="mono",
    pmax=550,
    vmp=41.9,
    voc=49.9,
    imp=13.13,
    isc=13.97,
    coef_voc=-0.29,
    coef_vmp=-0.34,
    coef_pmax=-0.34,
    noct=45,
    vsys_max=1500,
)

HUAWEI_100K = Onduleur(
    id="huawei-sun2000-100ktl-m2",
    nom="Huawei SUN2000-100KTL-M2",
    fabricant="Huawei",
    pnom_ac=100,
    vmppt_min=200,
    vmppt_max=1000,
    vabs_max=1100,
    i_max_per_mppt=26,
    nb_mppt=10,
    strings_per_mppt=2,
    u_ac=400,
    phases=3,
    isc_max_per_mppt=40,
    ratio_dc_ac_max_fab=1.5,
)

LITHIUM_12V8_100 = Batterie(
    id="lithium-12v8-100",
    nom="Lithium standard 12,8 V – 100 Ah",
    fabricant="Générique",
    technologie="lithium",
    u_nom=12.8,
    capacite_ah=100,
    dod_recommandee=0.80,
    dod_max=0.90,
    cycles=3000,
    i_nom=50,
    rendement=0.95,
    u_charge_max=14.6,
    u_decharge_min=10.0,
    ns_max=4,
    np_max=4,
)

# --- Profil « Ménage test » de R-02 ------------------------------------
# Modèle de référence : jamais utilisé directement, toujours copié en
# profondeur par `projet_reference`, sinon un test qui modifie une ligne
# corromprait les cas suivants.
_LIGNES_R02_MODELE = [
    LigneEquipement(
        nom="Ampoule LED", categorie="Éclairage",
        puissance_w=10, quantite=6, heures_j=5, ks=1.0,
    ),
    LigneEquipement(
        nom="Réfrigérateur", categorie="Froid",
        puissance_w=150, quantite=1, heures_j=24, ks=0.5,
    ),
    LigneEquipement(
        nom="Télévision", categorie="Audiovisuel",
        puissance_w=100, quantite=1, heures_j=4, ks=1.0,
    ),
    LigneEquipement(
        nom="Smartphone", categorie="Communication",
        puissance_w=10, quantite=4, heures_j=2.5, ks=1.0,
    ),
    LigneEquipement(
        nom="Fer à repasser", categorie="Électroménager",
        puissance_w=1000, quantite=1, heures_j=0.5, ks=0.8,
    ),
]


def projet_reference(cas: str) -> ProjetEntree:
    """Entrée complète du cas de référence demandé.

    Les cas s'enchaînent : R-04 contient R-01 à R-03, R-10 contient tout.
    """
    projet = ProjetEntree()
    projet.meta.nom = f"Cas de référence {cas}"
    # Les fiches d'équipement sont copiées pour la même raison que les lignes.
    panneau = CANADIAN_550.model_copy(deep=True)
    onduleur = HUAWEI_100K.model_copy(deep=True)
    batterie = LITHIUM_12V8_100.model_copy(deep=True)

    # R-01 : potentiel. La surface d'un hectare sert de référence.
    projet.potentiel = PotentielEntree(
        ghi_valeur=192.625,
        ghi_unite="w_m2_moy24h",
        surface_valeur=1,
        surface_unite="ha",
        taux_occupation=0.50,
        rendement_module=0.21,
    )

    # R-02 : bilan.
    projet.bilan = BilanEntree(
        profils=[
            ProfilAbonnes(
                id="profil-1",
                nom="Ménage test",
                nb_abonnes=1000,
                lignes=[ligne.model_copy(deep=True) for ligne in _LIGNES_R02_MODELE],
            )
        ]
    )

    # R-03 : production.
    projet.production = ProductionEntree(
        taux_couverture=1.0,
        performance_ratio=0.75,
        critere_ir="moyenne_annuelle",
        mode_pc="calculee",
        tension_systeme_v=600,
    )

    # R-04 : champ photovoltaïque.
    projet.pv = PvEntree(
        fiche=panneau,
        mode_config="auto",
        tension_reference_ns="vmp",
        t_amb_min_c=10,
        t_amb_max_c=35,
        g_ref_w_m2=1000,
    )

    # R-05 : onduleurs.
    projet.onduleur = OnduleurEntree(
        fiche=onduleur,
        mode_nombre="auto",
        ratio_dc_ac_max=1.20,
        limiter_courant_mppt=False,
        cos_phi=0.90,
    )

    # R-06 : batteries, base « un abonné ».
    projet.batteries = BatteriesEntree(
        actif=True,
        fiche=batterie,
        base_energie="abonne",
        profil_id="profil-1",
        part_stockee=1.0,
        jours_autonomie=1.0,
        rendement_onduleur=0.96,
        marge=1.0,
        mode_tension="auto",
    )

    # R-07 : câbles continus.
    projet.cables = CablesEntree(
        rho_mode="cahier",
        dc_principal=CableEntree(materiau="cuivre", longueur_m=25, epsilon=0.01),
        dc_chaine=CableEntree(materiau="cuivre", longueur_m=10, epsilon=0.01),
        dc_batteries=CableEntree(materiau="cuivre", longueur_m=2, epsilon=0.01),
    )

    # R-08 à R-10 : injection.
    projet.injection = InjectionEntree(
        transfo_mode="auto",
        transfo_marge=0.0,
        u_hta_kv=15,
        cable_ac=CableAcEntree(
            materiau="cuivre", longueur_m=30, epsilon=0.01, formule="cahier"
        ),
        k_disjoncteur=1.25,
        mode="totale",
        pertes_ac_incluses_pr=False,
    )

    if cas == "R-04b":
        projet.pv.tension_reference_ns = "voc_froid"
    elif cas == "R-06b":
        projet.batteries.base_energie = "zone"

    return projet
