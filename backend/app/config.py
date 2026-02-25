import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "TreeVuln API"
    debug: bool = False

    # Authentication — clé obligatoire pour les endpoints de gestion
    admin_api_key: str = ""

    # Database
    database_url: str = ""

    # CORS — accepte JSON array ou CSV
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "DATABASE_URL doit être configuré. "
                "Exemple : postgresql+asyncpg://user:pass@host:5432/db"
            )
        return v

    # API
    api_v1_prefix: str = "/api/v1"

    # Batch processing
    max_batch_size: int = 50000
    batch_chunk_size: int = 5000

    # Upload limits (bytes) — 50 MB par défaut
    max_upload_size: int = 50 * 1024 * 1024

    # Session
    session_cookie_name: str = "treevuln_session"
    session_max_age: int = 86400  # 24 heures


settings = Settings()
