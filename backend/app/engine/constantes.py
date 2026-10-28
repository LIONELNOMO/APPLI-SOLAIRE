"""Constantes et tables de référence (§8.6 à §8.8 du cahier des charges).

Les tables Iz et les pertes des transformateurs sont des valeurs indicatives,
à faire valider avant tout usage professionnel (question ouverte Q-10).
"""

from __future__ import annotations

from typing import Final, Literal

Materiau = Literal["cuivre", "aluminium"]

# --- Conditions de référence STC ---
G_STC_W_M2: Final = 1000.0
T_STC_C: Final = 25.0

# --- Calendrier : année de 365 jours, sans année bissextile ---
JOURS_MOIS: Final[tuple[int, ...]] = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
JOURS_AN: Final = 365
HEURES_AN: Final = 8760

MOIS_NOMS: Final[tuple[str, ...]] = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)

# --- Résistivités, en Ω·mm²/m ---
RHO: Final[dict[str, dict[Materiau, float]]] = {
    # Valeurs du cahier des charges, à 20 °C.
    "cahier": {"cuivre": 0.018, "aluminium": 0.028},
    # Conducteur à sa température de service : 1,25 × ρ20 (guide UTE C 15-105).
    "service": {"cuivre": 0.0225, "aluminium": 0.036},
}

# --- Séries normalisées ---
SECTIONS: Final[tuple[float, ...]] = (
    1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300,
)

CALIBRES_DISJONCTEURS: Final[tuple[float, ...]] = (
    6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250,
    320, 400, 500, 630, 800, 1000, 1250, 1600,
)

# --- Courants admissibles Iz, en ampères (Q-10) ---
# T-IZ-PV : câble solaire EN 50618 (H1Z2Z2-K), un câble à l'air libre, 60 °C.
IZ_PV_CUIVRE: Final[dict[float, float]] = {
    1.5: 30, 2.5: 41, 4: 55, 6: 70, 10: 98, 16: 132, 25: 176, 35: 218,
    50: 276, 70: 347, 95: 416, 120: 488, 150: 566, 185: 644, 240: 775,
}

# T-IZ-PR2 et T-IZ-PR3 : IEC 60364-5-52, méthode E (câble multiconducteur à
# l'air libre), isolant PR/XLPE, 30 °C ; 2 ou 3 conducteurs chargés.
IZ_PR2_CUIVRE: Final[dict[float, float]] = {
    1.5: 26, 2.5: 36, 4: 49, 6: 63, 10: 86, 16: 115, 25: 149, 35: 185,
    50: 225, 70: 289, 95: 352, 120: 410, 150: 473, 185: 542, 240: 641, 300: 741,
}

IZ_PR3_CUIVRE: Final[dict[float, float]] = {
    1.5: 23, 2.5: 32, 4: 42, 6: 54, 10: 75, 16: 100, 25: 127, 35: 158,
    50: 192, 70: 246, 95: 298, 120: 346, 150: 399, 185: 456, 240: 538, 300: 621,
}

# L'aluminium n'est pas proposé sous 16 mm² (tenue mécanique).
IZ_PR2_ALUMINIUM: Final[dict[float, float]] = {
    16: 90, 25: 116, 35: 144, 50: 175, 70: 224, 95: 271, 120: 314,
    150: 363, 185: 415, 240: 490, 300: 565,
}

IZ_PR3_ALUMINIUM: Final[dict[float, float]] = {
    16: 77, 25: 97, 35: 120, 50: 146, 70: 187, 95: 227, 120: 263,
    150: 304, 185: 347, 240: 409, 300: 471,
}

FACTEUR_IZ_PV_ALUMINIUM: Final = 0.78
"""Approximation pour le câble solaire en aluminium (message CAB-I03)."""

IZ_PV_ALUMINIUM: Final[dict[float, float]] = {
    s: round(iz * FACTEUR_IZ_PV_ALUMINIUM, 1)
    for s, iz in IZ_PV_CUIVRE.items()
    if s >= 16
}


def table_iz(famille: Literal["pv", "pr2", "pr3"], materiau: Materiau) -> dict[float, float]:
    """Table de courants admissibles pour une famille de câble et un matériau."""
    tables: dict[tuple[str, str], dict[float, float]] = {
        ("pv", "cuivre"): IZ_PV_CUIVRE,
        ("pv", "aluminium"): IZ_PV_ALUMINIUM,
        ("pr2", "cuivre"): IZ_PR2_CUIVRE,
        ("pr2", "aluminium"): IZ_PR2_ALUMINIUM,
        ("pr3", "cuivre"): IZ_PR3_CUIVRE,
        ("pr3", "aluminium"): IZ_PR3_ALUMINIUM,
    }
    return tables[(famille, materiau)]


# --- Sections minimales et maximales par type de câble (§6.15.1) ---
S_MIN: Final[dict[str, dict[Materiau, float]]] = {
    "pv": {"cuivre": 4.0, "aluminium": 16.0},
    "batteries": {"cuivre": 1.5, "aluminium": 16.0},
    "ac": {"cuivre": 1.5, "aluminium": 16.0},
}

S_MAX: Final[dict[str, float]] = {"pv": 240.0, "batteries": 300.0, "ac": 300.0}

# --- Transformateurs T-TR : pertes maximales du règlement UE 548/2014,
# niveau 1, transformateurs immergés (Q-10) ---
TRANSFOS: Final[dict[float, tuple[float, float]]] = {
    # S_n (kVA): (P0 en W, Pk en W)
    25: (70, 900),
    50: (90, 1100),
    100: (145, 1750),
    160: (210, 2350),
    250: (300, 3250),
    315: (360, 3900),
    400: (430, 4600),
}

PUISSANCES_TRANSFOS: Final[tuple[float, ...]] = tuple(sorted(TRANSFOS))
S_TRANSFO_MAX_KVA: Final = 400.0
"""Borne du cahier des charges, par transformateur (correction C-15)."""


def pertes_transfo(s_n_kva: float) -> tuple[float, float]:
    """Pertes (P0, Pk) du transformateur normalisé le plus proche par excès."""
    for s in PUISSANCES_TRANSFOS:
        if s >= s_n_kva:
            return TRANSFOS[s]
    return TRANSFOS[PUISSANCES_TRANSFOS[-1]]


# --- Bornes métier et seuils ---
PC_MAX_KWC: Final = 60_000.0
US_MAX_V: Final = 700.0
TENSION_PARC_MAX_V: Final = 48.0

RATIO_DC_AC_REFERENCE: Final = 1.15
"""Cible de tri des onduleurs dans la liste de choix."""
RATIO_DC_AC_MIN: Final = 0.80
RATIO_DC_AC_MAX: Final = 1.30

I_DECH_AVERT_A: Final = 500.0
"""Au-delà : BAT-A02, parc basse tension difficile (arbitrage A-03)."""
I_DECH_ERREUR_A: Final = 2000.0
"""Au-delà : BAT-E09, parc irréalisable en basse tension (arbitrage A-03)."""

I_DC_CHAMP_ELEVE_A: Final = 1000.0
"""Au-delà, et sans onduleur pour répartir : PV-I03."""

EPSILON_DC_TOTAL_MAX: Final = 0.03
"""Chute de tension continue totale au-delà de laquelle CAB-A04 est émis."""
ECART_TENSION_PARC_MAX: Final = 0.10
"""Écart relatif toléré entre tension obtenue et tension visée (BAT-E04)."""
N_CONDUCTEURS_MAX: Final = 10
COEF_SECURITE_ISC: Final = 1.25
"""Courant d'emploi des protections et câbles continus : 1,25 × Isc."""

SEUILS_TENSION_PARC: Final[tuple[tuple[float, int], ...]] = (
    (1000.0, 12),
    (3000.0, 24),
)
"""(puissance appelée maximale, tension recommandée). Au-delà : 48 V."""

PLAGES_CONVERTISSEUR: Final[tuple[tuple[float, float, float], ...]] = (
    # (tension visée maximale, u_conv_min, u_conv_max)
    (18.0, 10.0, 15.5),
    (36.0, 20.0, 31.0),
    (float("inf"), 40.0, 62.0),
)

# --- Plages de vraisemblance (avertissements) ---
H_PLAGE_VRAISEMBLABLE: Final = (2.0, 7.5)
"""kWh/m²/j, hors de quoi POT-A01 est émis."""
H_PLAGE_YAOUNDE: Final = (4.0, 5.5)
"""kWh/m²/j, hors de quoi POT-I01 est émis."""
H_AN_PLAGE_PLAUSIBLE: Final = (1200.0, 2200.0)
"""kWh/m²/an, hors de quoi POT-A03 est émis (anomalie A-04)."""
PR_PLAGE_USUELLE: Final = (0.60, 0.90)
T_AMB_PLAGE_C: Final = (-20.0, 60.0)
