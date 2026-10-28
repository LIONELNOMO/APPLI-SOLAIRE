"""Modèles SQLAlchemy (§11.4 d'ARCHITECTURE.md)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB sur PostgreSQL, JSON ailleurs : indexable d'un côté, portable de l'autre.
TypeJson = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Projet(Base):
    __tablename__ = "projets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    zone: Mapped[str] = mapped_column(String(200), default="Yaoundé Ouest")
    entree: Mapped[dict[str, Any]] = mapped_column(TypeJson, nullable=False)
    resultats: Mapped[dict[str, Any] | None] = mapped_column(TypeJson, nullable=True)
    """Cache du dernier calcul ; toujours recalculé à la lecture si absent."""
    version_schema: Mapped[int] = mapped_column(Integer, default=1)
    proprietaire_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_maintenant)
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_maintenant, onupdate=_maintenant
    )


class _FicheBase:
    """Colonnes communes aux quatre catalogues."""

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    fabricant: Mapped[str] = mapped_column(String(100), default="")
    fiche: Mapped[dict[str, Any]] = mapped_column(TypeJson, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="systeme")
    proprietaire_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class PanneauDb(_FicheBase, Base):
    __tablename__ = "panneaux"

    # Colonnes dupliquées hors du JSON pour permettre le filtrage et le tri.
    technologie: Mapped[str] = mapped_column(String(40), default="")
    pmax: Mapped[float] = mapped_column(Float, default=0.0)
    vmp: Mapped[float] = mapped_column(Float, default=0.0)
    imp: Mapped[float] = mapped_column(Float, default=0.0)


class OnduleurDb(_FicheBase, Base):
    __tablename__ = "onduleurs"

    pnom_ac: Mapped[float] = mapped_column(Float, default=0.0)
    u_ac: Mapped[float] = mapped_column(Float, default=400.0)
    nb_mppt: Mapped[int] = mapped_column(Integer, default=1)


class BatterieDb(_FicheBase, Base):
    __tablename__ = "batteries"

    technologie: Mapped[str] = mapped_column(String(40), default="lithium")
    u_nom: Mapped[float] = mapped_column(Float, default=0.0)
    capacite_ah: Mapped[float] = mapped_column(Float, default=0.0)


class EquipementDb(_FicheBase, Base):
    __tablename__ = "equipements"

    categorie: Mapped[str] = mapped_column(String(80), default="")
    puissance_w: Mapped[float] = mapped_column(Float, default=0.0)


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    mot_de_passe_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nom: Mapped[str] = mapped_column(String(200), default="")
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_maintenant)


class MetaDb(Base):
    __tablename__ = "meta"

    cle: Mapped[str] = mapped_column(String(80), primary_key=True)
    valeur: Mapped[str] = mapped_column(Text, default="")


TABLES_CATALOGUE: dict[str, type[Base]] = {
    "panneaux": PanneauDb,
    "onduleurs": OnduleurDb,
    "batteries": BatterieDb,
    "equipements": EquipementDb,
}
