from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./copinvest.db"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"
    secret_key: str  # No default -- forces explicit config
    openai_api_key: str = ""  # Unused — kept for backwards compat
    deepseek_api_key: str
    openroute_api_key: str
    voyage_api_key: str
    access_token_expire_minutes: int = 1440  # 24h
    debug: bool = False
    telegram_bot_token: str = ""
    telegram_user_map: str = "{}"  # JSON string mapping telegram_user_id (str) -> {"user_id": str, "role": str}

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
