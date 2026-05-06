from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./copinvest.db"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"
    secret_key: str  # No default -- forces explicit config
    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "qwen3-embedding:8b"
    access_token_expire_minutes: int = 1440  # 24h
    debug: bool = False

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
