from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OpsMesh API"
    api_prefix: str = "/api/v1"
    debug: bool = False
    allowed_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://opsmesh:opsmesh@localhost:5432/opsmesh"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    jwt_secret: str = "change-me-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    photon_api_key: str = ""
    photon_webhook_secret: str = "dev-photon-secret"
    feature_messaging_sms: bool = True
    feature_messaging_whatsapp: bool = True
    feature_messaging_imessage: bool = True
    feature_messaging_snapchat: bool = False
    enable_inbound_auto_reply: bool = False
    messaging_transport_mode: str = "photon_sdk"
    photon_bridge_url: str = "http://127.0.0.1:8787"
    photon_bridge_token: str = "dev-bridge-token"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
