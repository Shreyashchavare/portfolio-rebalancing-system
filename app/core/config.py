"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    APP_NAME: str = "portfolio-rebalancing-system"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL component settings (optional metadata)
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_PORT: Optional[int] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Database URL is strictly required when Settings is initialized
    DATABASE_URL: str

    # Policy RAG configuration
    POLICY_DOCUMENTS_DIR: str = "policy_documents"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    LOCAL_LLM_URL: Optional[str] = "http://localhost:11434"

    # Authentication security configuration
    ENABLE_DEV_MOCK_AUTH: bool = False


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Alias property for database URL."""
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the cached Settings instance (used primarily during testing)."""
    get_settings.cache_clear()
