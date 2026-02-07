"""
Application settings loaded from environment variables / .env file.

Uses pydantic-settings so every field is validated at startup.  If a
required variable is missing the server will refuse to start with a
clear error message.
"""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """All configuration consumed by the backend."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Azure Maps ----------------------------------------------------------
    azure_maps_subscription_key: str
    """Azure Maps subscription key for route / matrix API calls."""

    azure_maps_client_id: str
    """Azure Maps client ID (used for token-based auth / map control)."""

    azure_maps_base_url: str = "https://atlas.microsoft.com"
    """Base URL for the Azure Maps REST API (v1)."""

    # -- Azure Communication Service -----------------------------------------
    azure_communication_connection_string: str
    """Full connection string for Azure Communication Service."""

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
