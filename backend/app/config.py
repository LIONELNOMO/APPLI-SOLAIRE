"""Configuration par variables d'environnement (§5 d'ARCHITECTURE.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["dev", "desktop", "web"]

ORIGINES_TAURI = (
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIMSOLAIRE_", env_file=".env", extra="ignore"
    )

    mode: Mode = "dev"
    token: str = ""
    # Mot de passe unique protégeant la version hébergée. Vide = accès
    # libre, ce qui ne convient qu'en local.
    mot_de_passe: str = ""
    cors: str = "http://localhost:5173"
    secret_key: str = ""
    static_dir: str = "./static"
    log_file: str | None = None

    def origines_cors(self) -> list[str]:
        """Origines autorisées, selon le mode d'exécution."""
        if self.mode == "desktop":
            return list(ORIGINES_TAURI)
        if self.mode == "web":
            # Même origine : aucune requête croisée à autoriser.
            return [o.strip() for o in self.cors.split(",") if o.strip()]
        return [o.strip() for o in self.cors.split(",") if o.strip()] or ["*"]

    @property
    def jeton_requis(self) -> bool:
        return self.mode == "desktop" and bool(self.token)

    @property
    def mot_de_passe_requis(self) -> bool:
        """Vrai si la version hébergée doit demander le mot de passe."""
        return self.mode == "web" and bool(self.mot_de_passe)


class ParamsBase(BaseSettings):
    """`DATABASE_URL` n'a pas de préfixe, par convention."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dimsolaire.db"

    def chemin_sqlite(self) -> Path | None:
        if not self.database_url.startswith("sqlite"):
            return None
        chemin = self.database_url.split("///", 1)[-1]
        return Path(chemin).resolve()
