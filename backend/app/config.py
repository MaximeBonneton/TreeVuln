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

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # API
    api_v1_prefix: str = "/api/v1"

    # Batch processing
    max_batch_size: int = 50000
    batch_chunk_size: int = 5000


settings = Settings()
