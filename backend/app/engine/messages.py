"""Messages de vérification du moteur (§2.4 du cahier des charges).

Chaque message porte un code dont la lettre donne le niveau : E erreur,
A avertissement, I information. Les nombres sont formatés en fr-FR par le
moteur, sans dépendre de la locale du système.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Statut = Literal["ok", "avertissement", "erreur", "non_calcule"]

ESPACE_FINE = " "
"""Espace insécable fine, séparateur de milliers en français."""


class Niveau(StrEnum):
    ERREUR = "erreur"
    AVERTISSEMENT = "avertissement"
    INFO = "info"


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    niveau: Niveau
    module: str
    titre: str
    message: str
    suggestion: str | None = None
    valeur: float | None = None
    limite: float | None = None
    unite: str | None = None
    champs: tuple[str, ...] = ()


def fmt(x: float, dec: int = 2) -> str:
    """Format fr-FR indépendant de la locale : 1 687,40.

    L'arrondi est demi-haut, et non bancaire : `f"{1687.395:.2f}"` donnerait
    « 1 687,39 », car le flottant vaut en réalité 1687,39499…
    """
    quantum = Decimal(1).scaleb(-dec)
    arrondi = Decimal(repr(x)).quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{arrondi:,f}".replace(",", ESPACE_FINE).replace(".", ",")


def fmt_entier(x: float) -> str:
    """Format fr-FR sans décimale : 1 582."""
    return fmt(x, 0)


def fmt_pct(ratio: float, dec: int = 1) -> str:
    """Ratio sans unité affiché en pourcentage : 0,978 → « 97,8 »."""
    return fmt(ratio * 100.0, dec)


# code : (niveau, module, titre, modèle de message, modèle de suggestion)
_Entree = tuple[Niveau, str, str, str, str | None]

CATALOGUE: dict[str, _Entree] = {
    # ------------------------------------------------------------------
    # Module 1 — Potentiel solaire (§4.5)
    # ------------------------------------------------------------------
    "POT-E01": (
        Niveau.ERREUR, "potentiel", "GHI invalide",
        "Le GHI doit être strictement positif.",
        "Saisir la valeur issue de PVGIS ou NASA POWER",
    ),
    "POT-E02": (
        Niveau.ERREUR, "potentiel", "Surface invalide",
        "La surface de la zone doit être strictement positive.",
        None,
    ),
    "POT-E03": (
        Niveau.ERREUR, "potentiel", "Profil mensuel incomplet",
        "Le profil mensuel doit contenir 12 valeurs strictement positives.",
        "Compléter les 12 mois ou supprimer le profil",
    ),
    "POT-A01": (
        Niveau.AVERTISSEMENT, "potentiel", "Irradiation invraisemblable",
        "L'irradiation convertie ({h} kWh/m²/j) sort de la plage plausible "
        "[{h_min} ; {h_max}].",
        "Vérifier l'unité du GHI",
    ),
    "POT-A02": (
        Niveau.AVERTISSEMENT, "potentiel", "Profil et valeur unique divergents",
        "La moyenne du profil mensuel ({moyenne} kWh/m²/j) diffère de la valeur "
        "unique ({unique} kWh/m²/j) de {ecart} %.",
        "Le profil est utilisé pour les calculs ; mettre à jour la valeur unique",
    ),
    "POT-A03": (
        Niveau.AVERTISSEMENT, "potentiel", "Irradiation annuelle hors plage",
        "L'irradiation annuelle ({h_an} kWh/m²/an) sort de la plage plausible "
        "pour l'Afrique centrale [{h_min} ; {h_max}].",
        "Vérifier l'unité du GHI : une erreur d'unité fausse tous les résultats",
    ),
    "POT-I01": (
        Niveau.INFO, "potentiel", "Valeur inhabituelle pour Yaoundé",
        "L'irradiation ({h} kWh/m²/j) sort de la plage habituelle de Yaoundé "
        "[{h_min} ; {h_max}].",
        "Vérifier la source de la donnée",
    ),
    "POT-I02": (
        Niveau.INFO, "potentiel", "GHI à confirmer",
        "La source du GHI mentionne « à confirmer » : les résultats sont provisoires.",
        "Données gratuites couvrant Yaoundé : PVGIS et NASA POWER",
    ),
    "POT-I03": (
        Niveau.INFO, "potentiel", "Surface inconnue",
        "Surface non renseignée : le potentiel de la zone n'est pas calculé.",
        "Les onglets 2 à 4 restent utilisables",
    ),
    "POT-I04": (
        Niveau.INFO, "potentiel", "Irradiation dans le plan horizontal",
        "Hypothèse H-01 : l'irradiation retenue est celle d'un plan horizontal.",
        "Acceptable à 3,9° de latitude avec des modules inclinés de 5 à 10°",
    ),
    # ------------------------------------------------------------------
    # Module 2 — Bilan énergétique (§5.6)
    # ------------------------------------------------------------------
    "BIL-E01": (
        Niveau.ERREUR, "bilan", "Puissance invalide",
        "La puissance de « {nom} » doit être strictement positive.",
        None,
    ),
    "BIL-E02": (
        Niveau.ERREUR, "bilan", "Quantité négative",
        "La quantité de « {nom} » ne peut pas être négative.",
        None,
    ),
    "BIL-E03": (
        Niveau.ERREUR, "bilan", "Temps de fonctionnement invalide",
        "Le temps de fonctionnement de « {nom} » ({heures} h/j) doit être compris "
        "entre 0 et 24 h.",
        None,
    ),
    "BIL-E04": (
        Niveau.ERREUR, "bilan", "Coefficient Ks invalide",
        "Le coefficient Ks de « {nom} » ({ks}) doit être compris entre 0 et 1.",
        None,
    ),
    "BIL-E05": (
        Niveau.ERREUR, "bilan", "Nombre d'abonnés négatif",
        "Le nombre d'abonnés de « {nom} » ne peut pas être négatif.",
        None,
    ),
    "BIL-E06": (
        Niveau.ERREUR, "bilan", "Consommation nulle",
        "Aucune consommation calculée : le dimensionnement est impossible.",
        "Saisir au moins un appareil et un nombre d'abonnés",
    ),
    "BIL-A01": (
        Niveau.AVERTISSEMENT, "bilan", "Puissance très élevée",
        "Puissance très élevée pour « {nom} » ({puissance} W).",
        "Vérifier l'unité : la saisie attend des watts, non des kilowatts",
    ),
    "BIL-A02": (
        Niveau.AVERTISSEMENT, "bilan", "Fonctionnement continu à pleine puissance",
        "« {nom} » fonctionne 24 h sur 24 à pleine puissance ({puissance} W).",
        "Vérifier le temps de fonctionnement et le coefficient Ks",
    ),
    "BIL-I01": (
        Niveau.INFO, "bilan", "Catégorie ignorée",
        "La catégorie « {nom} » est ignorée : elle compte 0 abonné.",
        None,
    ),
    # ------------------------------------------------------------------
    # Module 3 — Production et puissance crête (§6.3)
    # ------------------------------------------------------------------
    "PROD-E01": (
        Niveau.ERREUR, "production", "Puissance imposée hors plage",
        "La puissance imposée ({pc} kWc) doit être comprise entre 0 et "
        "{pc_max} kWc.",
        None,
    ),
    "PROD-E02": (
        Niveau.ERREUR, "production", "Tension du système hors plage",
        "La tension du système ({us} V) doit être comprise entre 0 et {us_max} V.",
        None,
    ),
    "PROD-E03": (
        Niveau.ERREUR, "production", "Puissance nécessaire au-delà de la limite",
        "La puissance nécessaire ({pc} MWc) dépasse la limite de l'outil "
        "({limite_mwc} MWc).",
        "Réduire le taux de couverture ou découper le projet en tranches",
    ),
    "PROD-E04": (
        Niveau.ERREUR, "production", "Performance ratio hors plage",
        "Le performance ratio ({pr}) doit être compris entre 0 et 1.",
        None,
    ),
    "PROD-E05": (
        Niveau.ERREUR, "production", "Taux de couverture hors plage",
        "Le taux de couverture ({taux} %) doit être compris entre 0 et 150 %.",
        None,
    ),
    "PROD-E06": (
        Niveau.ERREUR, "production", "Puissance imposée manquante",
        "Le mode « puissance imposée » exige une valeur de puissance.",
        "Saisir la puissance d'injection, ou revenir au mode calculé",
    ),
    "PROD-A01": (
        Niveau.AVERTISSEMENT, "production", "Puissance imposée insuffisante",
        "La puissance imposée couvre seulement {couverture} % du besoin.",
        "Augmenter la puissance imposée ou réduire le taux de couverture",
    ),
    "PROD-A02": (
        Niveau.AVERTISSEMENT, "production", "Surface insuffisante",
        "La surface disponible ne permet d'installer que {pc_max} kWc, "
        "pour {pc} kWc retenus.",
        "Augmenter la surface ou réduire la puissance",
    ),
    "PROD-A03": (
        Niveau.AVERTISSEMENT, "production", "Performance ratio inhabituel",
        "Performance ratio inhabituel ({pr}).",
        "Valeur courante en climat chaud : 0,75 à 0,80",
    ),
    "PROD-I01": (
        Niveau.INFO, "production", "Production excédentaire",
        "Production excédentaire de {exces} % disponible pour l'injection.",
        None,
    ),
    "PROD-I02": (
        Niveau.INFO, "production", "Calcul non effectué",
        "Calcul non effectué : {cause}.",
        "Compléter l'onglet 1 (irradiation) ou l'onglet 2 (consommation)",
    ),
    # ------------------------------------------------------------------
    # Module 3 — Champ photovoltaïque (§6.11)
    # ------------------------------------------------------------------
    "PV-E01": (
        Niveau.ERREUR, "pv", "Aucun panneau valide",
        "Aucun panneau valide n'est sélectionné.",
        "Choisir un panneau dans le catalogue",
    ),
    "PV-E02": (
        Niveau.ERREUR, "pv", "Tension du système trop faible",
        "La tension du système ({us} V) est inférieure à la tension de référence "
        "d'un panneau ({u_ref} V).",
        "Augmenter la tension du système, ou choisir un panneau de tension plus faible",
    ),
    "PV-E03": (
        Niveau.ERREUR, "pv", "Tension du champ au-delà de Us",
        "La tension du champ ({u_dc} V) dépasse la tension du système ({us} V).",
        "Réduire le nombre en série à {ns_max}, ou augmenter Us",
    ),
    "PV-E04": (
        Niveau.ERREUR, "pv", "Tension à vide au-delà du panneau",
        "La tension à vide par temps froid ({voc} V) dépasse la tension maximale "
        "admise par le panneau ({vsys_max} V).",
        "Réduire le nombre en série à {ns_max} au maximum",
    ),
    "PV-E05": (
        Niveau.ERREUR, "pv", "Configuration manuelle invalide",
        "Ns et Np doivent être des entiers supérieurs ou égaux à 1.",
        None,
    ),
    "PV-E06": (
        Niveau.ERREUR, "pv", "Tension à vide au-delà de Us",
        "La tension à vide par temps froid ({voc} V) dépasse la tension du "
        "système ({us} V).",
        "Réduire le nombre en série à {ns_max} au maximum",
    ),
    "PV-A01": (
        Niveau.AVERTISSEMENT, "pv", "Puissance installée insuffisante",
        "Puissance installée insuffisante : {pc_installee} kWc au lieu de "
        "{pc_retenue} kWc, soit une couverture de {couverture} %.",
        "Augmenter le nombre de chaînes en parallèle",
    ),
    "PV-A02": (
        Niveau.AVERTISSEMENT, "pv", "Températures de conception incohérentes",
        "Températures de conception incohérentes : minimale {t_min} °C, "
        "maximale {t_max} °C.",
        "La température minimale doit être inférieure à la maximale, "
        "dans la plage [−20 ; 60] °C",
    ),
    "PV-A03": (
        Niveau.AVERTISSEMENT, "pv", "Fiche de panneau incohérente",
        "Fiche incohérente : Vmp × Imp = {produit} W pour une Pmax de {pmax} W, "
        "soit un écart de {ecart} %.",
        "Vérifier la fiche technique du fabricant",
    ),
    "PV-A04": (
        Niveau.AVERTISSEMENT, "pv", "Tension à vide supérieure à Us",
        "La tension à vide par temps froid ({voc} V) dépasse la tension du "
        "système ({us} V).",
        "Vérifier la tenue en tension du matériel, ou passer la référence de Ns "
        "en mode « Voc par temps froid »",
    ),
    "PV-A05": (
        Niveau.AVERTISSEMENT, "pv", "Tension de fonctionnement au-delà de Us",
        "La tension de fonctionnement par temps froid ({vmp} V) dépasse la "
        "tension du système ({us} V).",
        "Réduire le nombre en série, ou augmenter la tension du système",
    ),
    "PV-I01": (
        Niveau.INFO, "pv", "Panneaux ajoutés",
        "{ajoutes} panneaux ajoutés pour former des chaînes complètes "
        "({n_total} au total pour {n_min} nécessaires).",
        None,
    ),
    "PV-I02": (
        Niveau.INFO, "pv", "Tension du système sous-utilisée",
        "La tension du champ n'utilise que {taux} % de la tension du système.",
        "Augmenter le nombre en série pour réduire les pertes dans les câbles",
    ),
    "PV-I03": (
        Niveau.INFO, "pv", "Courant total élevé",
        "Courant total du champ élevé ({i_dc} A).",
        "Répartir le champ sur plusieurs onduleurs",
    ),
    # ------------------------------------------------------------------
    # Module 3 — Onduleurs (§6.13.4)
    # ------------------------------------------------------------------
    "OND-E01": (
        Niveau.ERREUR, "onduleur", "Tension à vide trop élevée",
        "La tension à vide de la chaîne par temps froid ({voc} V) dépasse la "
        "tension maximale admissible de l'onduleur ({vabs_max} V).",
        "Réduire le nombre en série à {ns_max} au maximum",
    ),
    "OND-E02": (
        Niveau.ERREUR, "onduleur", "Tension sous la plage MPPT",
        "La tension de fonctionnement par forte chaleur ({vmp_min} V) est "
        "inférieure à la plage MPPT de l'onduleur ({vmppt_min} V).",
        "Augmenter le nombre en série à {ns_min} au minimum, ou choisir un autre onduleur",
    ),
    "OND-E03": (
        Niveau.ERREUR, "onduleur", "Trop de chaînes par MPPT",
        "{n_mppt} chaînes par MPPT dépassent la capacité de l'onduleur "
        "({n_cap} chaînes).",
        "Prévoir au moins {n_e} onduleurs",
    ),
    "OND-E04": (
        Niveau.ERREUR, "onduleur", "Courant de court-circuit par MPPT dépassé",
        "Le courant de court-circuit par MPPT ({i_cc} A) dépasse la limite de "
        "l'onduleur ({i_cc_max} A).",
        "Réduire le nombre de chaînes par MPPT",
    ),
    "OND-E05": (
        Niveau.ERREUR, "onduleur", "Ratio DC/AC au-delà du maximum fabricant",
        "Le ratio DC/AC de l'onduleur le plus chargé ({ratio}) dépasse le "
        "maximum du fabricant ({ratio_max}).",
        "Augmenter le nombre d'onduleurs",
    ),
    "OND-E06": (
        Niveau.ERREUR, "onduleur", "Fiche d'onduleur invalide",
        "La fiche de l'onduleur est incomplète ou incohérente.",
        "Vérifier les tensions MPPT, le nombre d'entrées et la tension alternative",
    ),
    "OND-E07": (
        Niveau.ERREUR, "onduleur", "Une seule chaîne dépasse le courant admis",
        "Une seule chaîne ({imp} A) dépasse le courant admis par MPPT "
        "({i_max} A).",
        "Choisir un panneau de courant plus faible, ou un autre onduleur",
    ),
    "OND-E08": (
        Niveau.ERREUR, "onduleur", "Calcul impossible",
        "Calcul impossible : {cause}.",
        "Choisir un onduleur et configurer le champ photovoltaïque",
    ),
    "OND-E09": (
        Niveau.ERREUR, "onduleur", "Nombre d'onduleurs invalide",
        "Le nombre d'onduleurs doit être un entier supérieur ou égal à 1.",
        None,
    ),
    "OND-A01": (
        Niveau.AVERTISSEMENT, "onduleur", "Onduleurs surdimensionnés",
        "Ratio DC/AC faible ({ratio}) : les onduleurs sont surdimensionnés.",
        "Réduire le nombre d'onduleurs, ou augmenter la puissance du champ",
    ),
    "OND-A02": (
        Niveau.AVERTISSEMENT, "onduleur", "Tension au-dessus de la plage MPPT",
        "La tension de fonctionnement par temps froid ({vmp_max} V) dépasse la "
        "plage MPPT de l'onduleur ({vmppt_max} V).",
        "Réduire le nombre en série à {ns_max}",
    ),
    "OND-A03": (
        Niveau.AVERTISSEMENT, "onduleur", "Courant par MPPT dépassé",
        "Le courant par MPPT ({i_mppt} A) dépasse la limite de l'onduleur "
        "({i_max} A) de {exces} % : écrêtage à prévoir.",
        "Réduire le nombre de chaînes par MPPT",
    ),
    "OND-A04": (
        Niveau.AVERTISSEMENT, "onduleur", "Ratio DC/AC élevé",
        "Ratio DC/AC élevé ({ratio}) : écrêtage important aux heures de forte "
        "production.",
        "Augmenter le nombre d'onduleurs",
    ),
    "OND-A05": (
        Niveau.AVERTISSEMENT, "onduleur", "Facteur de puissance hors plage",
        "Le facteur de puissance ({cos_phi}) doit être compris entre 0 et 1.",
        None,
    ),
    "OND-A06": (
        Niveau.AVERTISSEMENT, "onduleur", "Puissance nominale inatteignable",
        "La puissance nominale n'est pas atteignable : {p_racc} kWc raccordables "
        "pour {pnom} kW de puissance nominale.",
        "Augmenter la tension du système, ou choisir un onduleur de puissance plus faible",
    ),
    "OND-I01": (
        Niveau.INFO, "onduleur", "Répartition inégale des chaînes",
        "Répartition inégale : {r} onduleurs reçoivent {q_plus} chaînes, "
        "{autres} en reçoivent {q}.",
        None,
    ),
    "OND-I02": (
        Niveau.INFO, "onduleur", "Courant de court-circuit non renseigné",
        "Le courant de court-circuit maximal par MPPT n'est pas renseigné : "
        "ce critère n'est pas vérifié.",
        "Compléter la fiche de l'onduleur",
    ),
    "OND-I03": (
        Niveau.INFO, "onduleur", "Entrées libres",
        "{entrees} entrées de chaîne restent libres.",
        None,
    ),
    "OND-I04": (
        Niveau.INFO, "onduleur", "Plage de Ns compatible",
        "Nombre en série compatible avec cet onduleur : de {ns_min} à {ns_max}.",
        None,
    ),
    # ------------------------------------------------------------------
    # Module 3 — Batteries (§6.14.5)
    # ------------------------------------------------------------------
    "BAT-E01": (
        Niveau.ERREUR, "batteries", "Calcul impossible",
        "Calcul impossible : {cause}.",
        "Choisir une batterie et vérifier l'énergie de base",
    ),
    "BAT-E02": (
        Niveau.ERREUR, "batteries", "Tension du parc hors plage",
        "La tension du parc ({u_parc} V) doit être comprise entre 0 et "
        "{u_max} V.",
        "Réduire le nombre de batteries en série",
    ),
    "BAT-E03": (
        Niveau.ERREUR, "batteries", "Plage de tension incompatible",
        "La plage de tension du parc ({u_min}–{u_max} V) sort de la plage de "
        "l'onduleur-chargeur ({conv_min}–{conv_max} V).",
        "Modifier le nombre en série, ou choisir un autre onduleur-chargeur",
    ),
    "BAT-E04": (
        Niveau.ERREUR, "batteries", "Tension visée inatteignable",
        "Ce modèle ne permet pas d'obtenir {u_visee} V : le parc atteint "
        "{u_parc} V, soit un écart de {ecart} %.",
        "Choisir une batterie de tension nominale compatible",
    ),
    "BAT-E05": (
        Niveau.ERREUR, "batteries", "Profondeur de décharge excessive",
        "La profondeur de décharge demandée ({dod} %) dépasse le maximum du "
        "fabricant ({dod_max} %).",
        None,
    ),
    "BAT-E06": (
        Niveau.ERREUR, "batteries", "Trop de batteries en série",
        "{ns} batteries en série dépassent le maximum de ce modèle ({ns_max}).",
        "Choisir une batterie de tension nominale plus élevée",
    ),
    "BAT-E07": (
        Niveau.ERREUR, "batteries", "Paramètre hors plage",
        "Paramètre hors plage : {detail}.",
        None,
    ),
    "BAT-E08": (
        Niveau.ERREUR, "batteries", "Configuration manuelle invalide",
        "Ns et Np doivent être des entiers supérieurs ou égaux à 1.",
        None,
    ),
    "BAT-E09": (
        Niveau.ERREUR, "batteries", "Parc irréalisable en basse tension",
        "Parc irréalisable en basse tension : le courant de décharge atteint "
        "{i_dech} A.",
        "Réduire l'énergie stockée, ou prévoir un stockage haute tension "
        "(catalogue de la version 2)",
    ),
    "BAT-A01": (
        Niveau.AVERTISSEMENT, "batteries", "Courant de décharge supérieur au nominal",
        "Le courant de décharge ({i_dech} A) dépasse le courant nominal du parc "
        "({i_parc} A).",
        "Augmenter le nombre de branches en parallèle",
    ),
    "BAT-A02": (
        Niveau.AVERTISSEMENT, "batteries", "Courant de décharge élevé",
        "Courant de décharge élevé ({i_dech} A) pour un parc de {u_parc} V.",
        "Prévoir plusieurs onduleurs-chargeurs et des jeux de barres "
        "dimensionnés, ou choisir la base « un abonné »",
    ),
    "BAT-A03": (
        Niveau.AVERTISSEMENT, "batteries", "Branches parallèles au plomb",
        "{np} branches en parallèle de batteries au plomb : risque de "
        "déséquilibre de charge.",
        "Limiter à 4 branches, ou choisir une technologie lithium",
    ),
    "BAT-A04": (
        Niveau.AVERTISSEMENT, "batteries", "Branches parallèles au-delà du maximum",
        "{np} branches en parallèle dépassent le maximum de ce modèle "
        "({np_max}).",
        "Prévoir plusieurs groupes, chacun avec son propre BMS",
    ),
    "BAT-A05": (
        Niveau.AVERTISSEMENT, "batteries", "Tension manuelle différente de la recommandation",
        "La tension saisie ({u_visee} V) diffère de la tension recommandée "
        "({u_reco} V) pour une puissance appelée de {p_base} W.",
        None,
    ),
    "BAT-A06": (
        Niveau.AVERTISSEMENT, "batteries", "Autonomie très longue",
        "Autonomie de {jours} jours : le coût du stockage devient important.",
        "Une autonomie de 1 à 3 jours est usuelle en site raccordé",
    ),
    "BAT-I01": (
        Niveau.INFO, "batteries", "Mise à l'échelle sur la zone",
        "{n_zone} batteries au total pour les {n_abonnes} abonnés de la catégorie.",
        None,
    ),
    "BAT-I02": (
        Niveau.INFO, "batteries", "Batteries ajoutées",
        "{ajoutes} batteries ajoutées pour compléter les branches "
        "({n_total} au total pour {n_min} nécessaires).",
        None,
    ),
    "BAT-I03": (
        Niveau.INFO, "batteries", "Stockage désactivé",
        "Stockage désactivé : les étapes 15 à 19 et 21 ne sont pas calculées.",
        None,
    ),
    "BAT-I04": (
        Niveau.INFO, "batteries", "Durée de vie estimée",
        "Durée de vie estimée : {annees} ans, à raison d'un cycle par jour "
        "({cycles} cycles).",
        None,
    ),
    # ------------------------------------------------------------------
    # Câbles (§6.15.4), communs au continu et à l'alternatif
    # ------------------------------------------------------------------
    "CAB-E01": (
        Niveau.ERREUR, "cables", "Longueur invalide",
        "{cable} : la longueur doit être strictement positive.",
        None,
    ),
    "CAB-E02": (
        Niveau.ERREUR, "cables", "Chute de tension hors plage",
        "{cable} : la chute de tension ({epsilon} %) doit être comprise entre "
        "0 et 5 %.",
        None,
    ),
    "CAB-E03": (
        Niveau.ERREUR, "cables", "Facteur de correction invalide",
        "{cable} : facteur de correction invalide ({k}).",
        "Valeur attendue dans la plage ]0 ; 1,2]",
    ),
    "CAB-E04": (
        Niveau.ERREUR, "cables", "Courant trop élevé pour ce câble",
        "{cable} : le courant ({i} A) est trop élevé, même avec "
        "{n_max} conducteurs en parallèle.",
        "Répartir sur plus d'onduleurs, ou augmenter la tension",
    ),
    "CAB-A01": (
        Niveau.AVERTISSEMENT, "cables", "Longueur hors de la plage du cahier",
        "{cable} : longueur de {l} m, hors de la plage prévue par le cahier "
        "des charges.",
        "Le calcul reste valable ; vérifier le tracé réel",
    ),
    "CAB-A02": (
        Niveau.AVERTISSEMENT, "cables", "Chute de tension personnalisée",
        "{cable} : chute de tension personnalisée ({epsilon} %).",
        "Le cahier des charges prévoit 1 % ou 2 %",
    ),
    "CAB-A03": (
        Niveau.AVERTISSEMENT, "cables", "Conducteurs en parallèle",
        "{cable} : {n} conducteurs de {section} mm² en parallèle sont nécessaires.",
        "Vérifier les raccordements et le facteur de groupement",
    ),
    "CAB-A04": (
        Niveau.AVERTISSEMENT, "cables", "Chute de tension continue totale élevée",
        "Chute de tension continue totale élevée ({epsilon} %).",
        "Augmenter les sections, ou réduire les longueurs",
    ),
    "CAB-I01": (
        Niveau.INFO, "cables", "Section imposée par l'échauffement",
        "{cable} : section imposée par l'échauffement ({iz} A admissibles pour "
        "{i_b} A d'emploi), non par la chute de tension.",
        None,
    ),
    "CAB-I02": (
        Niveau.INFO, "cables", "Section minimale appliquée",
        "{cable} : section minimale appliquée ({section} mm²).",
        None,
    ),
    "CAB-I03": (
        Niveau.INFO, "cables", "Courant admissible estimé",
        "{cable} : courant admissible du câble solaire en aluminium estimé "
        "(0,78 × la valeur cuivre).",
        "À confirmer sur la fiche du fabricant",
    ),
    "CAB-I04": (
        Niveau.INFO, "cables", "Fusibles de chaîne nécessaires",
        "{n} chaînes en parallèle sur le câble principal : des fusibles de "
        "chaîne sont nécessaires.",
        "Les protections continues sont hors périmètre de la version 1",
    ),
    "CAB-I05": (
        Niveau.INFO, "cables", "Calcul non effectué",
        "Calcul non effectué : {cause}.",
        "Compléter les étapes précédentes",
    ),
    # ------------------------------------------------------------------
    # Module 4 — Injection (§7.6)
    # ------------------------------------------------------------------
    "INJ-E01": (
        Niveau.ERREUR, "injection", "Puissance du transformateur hors plage",
        "La puissance unitaire du transformateur ({s_n} kVA) doit être comprise "
        "entre 0 et {s_max} kVA.",
        None,
    ),
    "INJ-E02": (
        Niveau.ERREUR, "injection", "Transformateur surchargé",
        "Transformateur surchargé côté basse tension : {i_bt} A pour "
        "{i_n} A nominaux.",
        "Augmenter la puissance du transformateur, ou répartir les onduleurs",
    ),
    "INJ-E03": (
        Niveau.ERREUR, "injection", "Onduleur plus puissant que le transformateur",
        "Un seul onduleur ({s_ond} kVA) dépasse la puissance du transformateur "
        "({s_n} kVA).",
        "Choisir un transformateur de puissance plus élevée",
    ),
    "INJ-E04": (
        Niveau.ERREUR, "injection", "Calcul non effectué",
        "Calcul non effectué : {cause}.",
        "Corriger d'abord le dimensionnement des onduleurs (onglet 3)",
    ),
    "INJ-E05": (
        Niveau.ERREUR, "injection", "Aucun calibre de disjoncteur ne convient",
        "Aucun calibre normalisé ne convient pour {i_requis} A.",
        "Prévoir plusieurs départs en parallèle",
    ),
    "INJ-E06": (
        Niveau.ERREUR, "injection", "Paramètre hors plage",
        "Paramètre hors plage : {detail}.",
        None,
    ),
    "INJ-A01": (
        Niveau.AVERTISSEMENT, "injection", "Tension alternative différente de 400 V",
        "La tension alternative des onduleurs est de {u_ac} V : un enroulement "
        "basse tension adapté est nécessaire.",
        "Vérifier la disponibilité d'un transformateur {u_ac} V / HTA",
    ),
    "INJ-A02": (
        Niveau.AVERTISSEMENT, "injection", "Transformateurs surdimensionnés",
        "Taux de charge global de {taux} % : les transformateurs sont "
        "surdimensionnés.",
        "Choisir une puissance unitaire plus faible",
    ),
    "INJ-A03": (
        Niveau.AVERTISSEMENT, "injection", "Nombre de transformateurs élevé",
        "{n_tr} transformateurs sont nécessaires.",
        "Des unités de 1 000 kVA ou plus seraient préférables ; la limite de "
        "400 kVA vient du cahier des charges",
    ),
    "INJ-A04": (
        Niveau.AVERTISSEMENT, "injection", "Injection nette négative",
        "Injection nette négative en {mois} : les pertes dépassent la production.",
        "Vérifier les pertes à vide des transformateurs et le taux "
        "d'autoconsommation",
    ),
    "INJ-I01": (
        Niveau.INFO, "injection", "Pertes alternatives non déduites",
        "Les pertes des câbles alternatifs sont affichées mais non déduites : "
        "le performance ratio les inclut déjà.",
        None,
    ),
    "INJ-I02": (
        Niveau.INFO, "injection", "Pertes du transformateur par défaut",
        "Pertes du transformateur issues de la table de référence : "
        "P0 {p0} W et Pk {pk} W.",
        "Valeurs indicatives du règlement UE 548/2014 ; à remplacer par la "
        "fiche du fabricant",
    ),
    "INJ-I03": (
        Niveau.INFO, "injection", "Indicateurs économiques non calculés",
        "Tarif d'achat ou facteur d'émission non renseigné : recettes et CO₂ "
        "évité non calculés.",
        None,
    ),
    "INJ-I04": (
        Niveau.INFO, "injection", "Points à valider avec le gestionnaire du réseau",
        "À valider avec le gestionnaire du réseau : tension HTA, puissance de "
        "court-circuit, facteur de puissance, protection de découplage, "
        "comptage et couplage du transformateur.",
        None,
    ),
}


def msg(
    code: str,
    *,
    champs: tuple[str, ...] | list[str] | None = None,
    valeur: float | None = None,
    limite: float | None = None,
    unite: str | None = None,
    **params: Any,
) -> Message:
    """Construit un message du catalogue.

    Les paramètres flottants sont formatés en fr-FR ; passer une chaîne déjà
    formatée (par `fmt_entier` ou `fmt_pct`) pour contrôler les décimales.
    """
    try:
        niveau, module, titre, modele, suggestion = CATALOGUE[code]
    except KeyError:
        raise KeyError(f"Code de message inconnu : {code!r}") from None

    rendus = {
        cle: fmt(val) if isinstance(val, float) else val
        for cle, val in params.items()
    }
    return Message(
        code=code,
        niveau=niveau,
        module=module,
        titre=titre,
        message=modele.format(**rendus),
        suggestion=suggestion.format(**rendus) if suggestion else None,
        valeur=valeur,
        limite=limite,
        unite=unite,
        champs=tuple(champs or ()),
    )


def statut(messages: list[Message], calcule: bool = True) -> Statut:
    """Statut d'un module : erreur, puis non calculé, puis avertissement, puis ok."""
    niveaux = {m.niveau for m in messages}
    if Niveau.ERREUR in niveaux:
        return "erreur"
    if not calcule:
        return "non_calcule"
    return "avertissement" if Niveau.AVERTISSEMENT in niveaux else "ok"


def statut_global(messages: list[Message]) -> Statut:
    """Statut de l'ensemble du projet, selon la même règle."""
    return statut(messages, calcule=True)
