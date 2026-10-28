"""Nommage des fichiers téléchargés.

Un en-tête HTTP ne transporte que de l'ASCII : « Yaoundé Ouest.pdf » doit
donc être encodé selon la RFC 6266, sinon le téléchargement échoue.
"""

from __future__ import annotations

import unicodedata
from urllib.parse import quote

AUTORISES = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. ")


def _translitere(nom: str) -> str:
    """Remplace les caractères accentués par leur équivalent ASCII."""
    decompose = unicodedata.normalize("NFKD", nom)
    sans_accent = "".join(c for c in decompose if not unicodedata.combining(c))
    propre = "".join(c if c in AUTORISES else "-" for c in sans_accent)
    # Les tirets consécutifs sont réduits à un seul.
    while "--" in propre:
        propre = propre.replace("--", "-")
    return propre.strip("-. ") or "rapport"


def entete_fichier(nom: str, extension: str) -> dict[str, str]:
    """En-tête `Content-Disposition` conforme à la RFC 6266.

    Deux formes : `filename` en ASCII pour les clients anciens, et
    `filename*` en UTF-8 encodé pour les navigateurs modernes.
    """
    base = nom.rsplit(f".{extension}", 1)[0]
    ascii_ = f"{_translitere(base)}.{extension}"
    utf8 = quote(f"{base}.{extension}", safe="")
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_}"; filename*=UTF-8\'\'{utf8}'
        )
    }
