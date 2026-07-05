from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ecommerce-platform"
    environment: str = "development"
    debug: bool = False

    database_url: str
    redis_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    stripe_secret_key: str
    stripe_webhook_secret: str

    s3_endpoint_url: str | None = None
    s3_bucket: str
    s3_access_key: str
    s3_region: str = "us-east-1"
    s3_secret_key: str

    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    platform_base_domain: str = "localhost"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
