"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://fintech:fintech_dev_only@localhost:5432/fintech"
    )

    # Auth
    secret_key: str = Field(default="dev-only-secret-please-replace-32-bytes-minimum")
    session_ttl_hours: int = Field(default=720, ge=1, le=8760)
    cookie_name: str = Field(default="bb_session")
    cookie_secure: bool = Field(default=False)
    reset_token_ttl_hours: int = Field(default=1, ge=1, le=48)

    # LLM / provider settings
    llm_provider: str = Field(default="disabled")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o-mini")
    llm_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    # CORS
    frontend_origin: str = Field(default="http://localhost:3000")

    @model_validator(mode="before")
    @classmethod
    def _sync_llm_settings(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        llm_api_key = data.get("llm_api_key") or ""
        openai_api_key = data.get("openai_api_key") or ""
        if not llm_api_key and openai_api_key:
            data["llm_api_key"] = openai_api_key
        if not openai_api_key and llm_api_key:
            data["openai_api_key"] = llm_api_key

        llm_base_url = data.get("llm_base_url") or ""
        openai_base_url = data.get("openai_base_url") or ""
        if not llm_base_url and openai_base_url:
            data["llm_base_url"] = openai_base_url
        if not openai_base_url and llm_base_url:
            data["openai_base_url"] = llm_base_url

        llm_model = data.get("llm_model") or ""
        openai_model = data.get("openai_model") or ""
        if not llm_model and openai_model:
            data["llm_model"] = openai_model
        if not openai_model and llm_model:
            data["openai_model"] = llm_model

        return data

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid log level: {v}")
        return v

    @property
    def llm_enabled(self) -> bool:
        provider = (self.llm_provider or "").strip().lower()
        if provider in {"", "disabled", "off", "none", "false"}:
            return False
        api_key = (self.llm_api_key or self.openai_api_key or "").strip()
        return bool(api_key)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()