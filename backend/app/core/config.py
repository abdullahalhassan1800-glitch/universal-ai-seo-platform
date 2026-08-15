"""Application settings loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    app_name: str = "Universal AI SEO Platform"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./seo_dev.db"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    crawler_user_agent: str = "UniversalAI_SEO_Bot/1.0 (+https://example.com/bot)"
    crawler_max_pages: int = 100
    crawler_delay: float = 0.5
    crawler_render: str = "httpx"
    crawler_render_timeout: float = 15.0

    ai_provider: str = "none"
    ai_model: str = ""
    ai_small_model: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
