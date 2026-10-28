"""Conversions d'unités centralisées (principe P4 du cahier des charges)."""

from __future__ import annotations

from typing import Literal

from .constantes import JOURS_AN

UniteGhi = Literal["w_m2_moy24h", "kwh_m2_j", "kwh_m2_an"]
UniteSurface = Literal["m2", "ha", "km2"]

FACTEURS_SURFACE: dict[str, float] = {"m2": 1.0, "ha": 10_000.0, "km2": 1_000_000.0}


def ghi_vers_h_kwh_m2_j(valeur: float, unite: UniteGhi) -> float:
    """F-01 — Conversion du GHI en irradiation journalière moyenne H.

    L'interprétation par défaut est l'irradiance moyenne sur 24 heures
    (correction C-01, arbitrage A-01) : 192,625 W/m² donne 4,623 kWh/m²/j.
    """
    if unite == "w_m2_moy24h":
        return valeur * 24.0 / 1000.0
    if unite == "kwh_m2_j":
        return valeur
    if unite == "kwh_m2_an":
        return valeur / JOURS_AN
    raise ValueError(f"Unité de GHI inconnue : {unite!r}")


def h_vers_irradiance_moy24h_w_m2(h_kwh_m2_j: float) -> float:
    """Irradiance moyenne sur 24 h correspondant à une irradiation journalière."""
    return h_kwh_m2_j * 1000.0 / 24.0


def surface_vers_m2(valeur: float, unite: UniteSurface) -> float:
    """Conversion d'une surface en mètres carrés."""
    try:
        return valeur * FACTEURS_SURFACE[unite]
    except KeyError:
        raise ValueError(f"Unité de surface inconnue : {unite!r}") from None


def kwc_vers_w(pc_kwc: float) -> float:
    return pc_kwc * 1000.0


def w_vers_kwc(p_w: float) -> float:
    return p_w / 1000.0


def wh_vers_kwh(e_wh: float) -> float:
    return e_wh / 1000.0


def kwh_vers_wh(e_kwh: float) -> float:
    return e_kwh * 1000.0


def mettre_a_echelle_energie(e_wh: float) -> tuple[float, str]:
    """Valeur et unité lisibles pour une énergie en Wh (seuil de 1 000)."""
    for seuil, facteur, unite in (
        (1e9, 1e9, "GWh"),
        (1e6, 1e6, "MWh"),
        (1e3, 1e3, "kWh"),
    ):
        if abs(e_wh) >= seuil:
            return e_wh / facteur, unite
    return e_wh, "Wh"


def mettre_a_echelle_puissance(p_w: float) -> tuple[float, str]:
    """Valeur et unité lisibles pour une puissance en W (seuil de 1 000)."""
    for seuil, facteur, unite in (
        (1e6, 1e6, "MW"),
        (1e3, 1e3, "kW"),
    ):
        if abs(p_w) >= seuil:
            return p_w / facteur, unite
    return p_w, "W"


def mettre_a_echelle_crete(pc_kwc: float) -> tuple[float, str]:
    """Puissance crête en kWc ou MWc (seuil de 1 000 kWc)."""
    if abs(pc_kwc) >= 1000.0:
        return pc_kwc / 1000.0, "MWc"
    return pc_kwc, "kWc"


def lire_nombre(texte: str) -> float:
    """Lecture d'un nombre saisi avec la virgule ou le point (§2.3).

    Accepte « 192,625 », « 192.625 », « 1 687,40 » et « 1 687.40 ».
    """
    nettoye = (
        texte.strip()
        .replace(" ", "")
        .replace(" ", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    if not nettoye:
        raise ValueError("Valeur vide")
    return float(nettoye)
