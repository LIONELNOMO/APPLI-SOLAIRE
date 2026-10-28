"""Gestion des projets et export/import (§11.5 d'ARCHITECTURE.md)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.modeles import EquipementDb, Projet
from ..engine.modeles import (
    BilanEntree,
    LigneEquipement,
    ProfilAbonnes,
    ProjetEntree,
    ResultatsProjet,
)
from ..engine.pipeline import calculer_projet

FORMAT_EXPORT = "dimsolaire-projet"
VERSION_FORMAT = 1
VERSION_LOGICIEL = "1.0.0"


class ResumeProjet(BaseModel):
    id: str
    nom: str
    zone: str
    statut_global: str | None = None
    pc_installee_kwc: float | None = None
    n_panneaux: int | None = None
    cree_le: datetime
    modifie_le: datetime


def empreinte(entree: ProjetEntree) -> str:
    """SHA-256 du JSON canonique de l'entrée (clés triées, sans espaces)."""
    charge = entree.model_dump(mode="json")
    canonique = json.dumps(charge, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonique.encode("utf-8")).hexdigest()


def projet_par_defaut(session: Session | None = None) -> ProjetEntree:
    """Projet neuf, avec le profil « Ménage type » de la bibliothèque."""
    entree = ProjetEntree()
    lignes: list[LigneEquipement] = []

    if session is not None:
        requete = (
            select(EquipementDb)
            .where(EquipementDb.actif.is_(True))
            .order_by(EquipementDb.categorie, EquipementDb.nom)
        )
        for ligne in session.scalars(requete):
            fiche = ligne.fiche
            lignes.append(
                LigneEquipement(
                    nom=fiche["appareil"],
                    categorie=fiche.get("categorie", ""),
                    puissance_w=fiche["puissance_w"],
                    quantite=fiche.get("quantite_defaut", 0),
                    heures_j=fiche["heures_j"],
                    ks=fiche.get("ks", 1.0),
                    ref_bibliotheque=fiche["id"],
                )
            )

    entree.bilan = BilanEntree(
        profils=[
            ProfilAbonnes(
                id="profil-1", nom="Ménage type", nb_abonnes=0, lignes=lignes
            )
        ]
    )
    return entree


def lister(session: Session, proprietaire_id: str | None = None) -> list[ResumeProjet]:
    requete = select(Projet).order_by(Projet.modifie_le.desc())
    if proprietaire_id is not None:
        requete = requete.where(Projet.proprietaire_id == proprietaire_id)

    resumes: list[ResumeProjet] = []
    for projet in session.scalars(requete):
        resultats = projet.resultats or {}
        pv = (resultats.get("pv") or {}).get("valeurs") or {}
        resumes.append(
            ResumeProjet(
                id=projet.id,
                nom=projet.nom,
                zone=projet.zone,
                statut_global=resultats.get("statut_global"),
                pc_installee_kwc=pv.get("pc_installee_kwc"),
                n_panneaux=pv.get("n_total"),
                cree_le=projet.cree_le,
                modifie_le=projet.modifie_le,
            )
        )
    return resumes


def creer(
    session: Session,
    entree: ProjetEntree,
    proprietaire_id: str | None = None,
) -> tuple[Projet, ResultatsProjet]:
    resultats = calculer_projet(entree)
    projet = Projet(
        nom=entree.meta.nom,
        zone=entree.meta.zone,
        entree=entree.model_dump(mode="json"),
        resultats=resultats.model_dump(mode="json"),
        version_schema=entree.meta.version_schema,
        proprietaire_id=proprietaire_id,
    )
    session.add(projet)
    session.flush()
    return projet, resultats


def enregistrer(
    session: Session, projet: Projet, entree: ProjetEntree
) -> ResultatsProjet:
    """Enregistre une entrée et met à jour le cache des résultats."""
    resultats = calculer_projet(entree)
    projet.nom = entree.meta.nom
    projet.zone = entree.meta.zone
    projet.entree = entree.model_dump(mode="json")
    projet.resultats = resultats.model_dump(mode="json")
    projet.version_schema = entree.meta.version_schema
    session.flush()
    return resultats


def dupliquer(session: Session, projet: Projet) -> Projet:
    entree = ProjetEntree.model_validate(projet.entree)
    entree.meta.nom = f"{projet.nom} (copie)"
    copie, _ = creer(session, entree, projet.proprietaire_id)
    return copie


def exporter(projet: Projet) -> dict[str, Any]:
    """Fichier `.dimsolaire.json` autoporteur (principe P2)."""
    entree = ProjetEntree.model_validate(projet.entree)
    return {
        "format": FORMAT_EXPORT,
        "version_format": VERSION_FORMAT,
        "version_logiciel": VERSION_LOGICIEL,
        "exporte_le": datetime.now(timezone.utc).isoformat(),
        "projet": entree.model_dump(mode="json"),
        "resultats": projet.resultats,
        "empreinte": empreinte(entree),
    }


class ResultatImport(BaseModel):
    entree: ProjetEntree
    empreinte_valide: bool
    avertissements: list[str] = []


def importer(charge: dict[str, Any]) -> ResultatImport:
    """Valide un fichier importé. Son contenu n'est jamais exécuté."""
    avertissements: list[str] = []

    if charge.get("format") != FORMAT_EXPORT:
        raise ValueError(
            f"Format inattendu : « {charge.get('format')} » au lieu de « {FORMAT_EXPORT} »"
        )

    version = charge.get("version_format")
    if not isinstance(version, int) or version < 1:
        raise ValueError("Version de format absente ou invalide")
    if version > VERSION_FORMAT:
        raise ValueError(
            f"Fichier produit par une version plus récente (format {version}). "
            "Mettre DimSolaire à jour."
        )

    brut = charge.get("projet")
    if not isinstance(brut, dict):
        raise ValueError("Le fichier ne contient aucun projet")

    try:
        entree = ProjetEntree.model_validate(brut)
    except ValidationError as erreur:
        premiere = erreur.errors()[0]
        champ = ".".join(str(p) for p in premiere["loc"])
        raise ValueError(f"Projet invalide : {champ} — {premiere['msg']}") from erreur

    attendue = charge.get("empreinte")
    calculee = empreinte(entree)
    empreinte_valide = attendue == calculee
    if attendue and not empreinte_valide:
        avertissements.append(
            "L'empreinte du fichier ne correspond pas à son contenu : "
            "le projet a peut-être été modifié hors de DimSolaire."
        )

    return ResultatImport(
        entree=entree,
        empreinte_valide=empreinte_valide,
        avertissements=avertissements,
    )


def nom_unique(session: Session, nom: str) -> str:
    """Ajoute « (importé) » si le nom existe déjà."""
    existe = session.scalar(select(Projet).where(Projet.nom == nom))
    if existe is None:
        return nom
    candidat = f"{nom} (importé)"
    index = 2
    while session.scalar(select(Projet).where(Projet.nom == candidat)) is not None:
        candidat = f"{nom} (importé {index})"
        index += 1
    return candidat
