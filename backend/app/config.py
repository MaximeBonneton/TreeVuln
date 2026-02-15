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

    # Database
    database_url: str = "postgresql+asyncpg://treevuln:treevuln@localhost:5432/treevuln"

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

    # API
    api_v1_prefix: str = "/api/v1"

    # Batch processing
    max_batch_size: int = 50000
    batch_chunk_size: int = 5000


settings = Settings()
