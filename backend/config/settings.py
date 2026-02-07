"""
Application settings loaded from environment variables / .env file.

Uses pydantic-settings so every field is validated at startup.  If a
required variable is missing the server will refuse to start with a
clear error message.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """All configuration consumed by the backend."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Azure Map Services ---------------------------------------------------
    azure_maps_subscription_key: str
    azure_maps_client_id: str
    azure_maps_base_url: str = "https://atlas.microsoft.com"

    # -- Azure Communication Service -----------------------------------------
    azure_communication_connection_string: str

    # -- Truly Functional Alternatives ---------------------------------------
    jwt_secret: str = "ruparked-hackathon-secret-2026-xyz"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./ruparked.db"

    ntfy_topic: str = "ruparked-alerts-hackathon-2026"
    analytics_enabled: bool = True

    # -- Server --------------------------------------------------------------
    port: int = 4000
    """Port the Uvicorn server listens on."""

    cors_origins: str = "http://localhost:3000"
    """Comma-separated list of allowed frontend origins."""

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list of trimmed strings."""
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()  # type: ignore[call-arg]
