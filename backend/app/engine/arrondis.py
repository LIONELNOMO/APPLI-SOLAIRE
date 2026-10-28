"""Arrondis tolérants aux erreurs de représentation des flottants.

Voir §2.2 du cahier des charges. Sans tolérance, `79_200 / 550` vaut
`144.00000000000003` et `ceil` renverrait 145 au lieu de 144.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

EPS = 1e-9
"""Tolérance relative : un écart inférieur est considéré comme nul."""


def _entier_proche(x: float) -> int | None:
    """Renvoie l'entier dont `x` est indistinguable, ou None."""
    n = round(x)
    return n if abs(x - n) <= EPS * max(1.0, abs(x)) else None


def ceil_safe(x: float) -> int:
    """Arrondi supérieur. Nombres de panneaux, batteries, onduleurs, chaînes."""
    n = _entier_proche(x)
    return n if n is not None else math.ceil(x)


def floor_safe(x: float) -> int:
    """Arrondi inférieur. Nombre de panneaux en série (F-13)."""
    n = _entier_proche(x)
    return n if n is not None else math.floor(x)


def arrondi_demi_haut(x: float) -> int:
    """Arrondi au plus proche, 0,5 vers le haut : 2,5 → 3 et 3,5 → 4.

    `round()` de Python arrondit 2,5 à 2 (arrondi bancaire), ce qui donnerait
    3 batteries en série au lieu de 4 pour un parc 48 V en 12,8 V (F-22).
    """
    n = _entier_proche(x)
    return n if n is not None else math.floor(x + 0.5)


def normaliser(x: float, serie: Sequence[float]) -> float | None:
    """Plus petite valeur de `serie` supérieure ou égale à `x`.

    `serie` est triée par ordre croissant. La tolérance évite de sauter au
    calibre suivant pour un courant calculé à 63,0000000001 A.
    """
    seuil = x * (1 - EPS) if x > 0 else x
    return next((v for v in serie if v >= seuil), None)
