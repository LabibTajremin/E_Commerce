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
    # Some S3-compatible providers (notably Cloudflare R2) serve public reads
    # from a different host than the S3 API endpoint used for writes — e.g.
    # R2's API lives at <account>.r2.cloudflarestorage.com but public objects
    # are served from a distinct pub-<hash>.r2.dev or custom domain. When
    # set, uploaded-file URLs are built from this instead of s3_endpoint_url.
    s3_public_base_url: str | None = None

    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # Every tenant gets its own storefront/admin origin (acme.myshop.com,
    # bramble.myshop.com, ...), so a fixed allowlist can't cover them all —
    # combined with allow_credentials=True, CORSMiddleware also can't fall
    # back to "*". This regex is matched against the Origin header in
    # addition to cors_allowed_origins; e.g.
    # ^https://[a-z0-9-]+\.(myshop\.com|admin\.myshop\.com)$
    cors_allowed_origin_regex: str | None = None
    platform_base_domain: str = "localhost"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
