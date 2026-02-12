"""Application configuration using pydantic-settings with security hardening."""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Security Notes:
    - All sensitive values MUST be set via environment variables in production
    - Default values are for development only
    - The application will refuse to start in production mode with default secrets
    """

    # Application
    app_name: str = "SF Micromobility Navigation API"
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = False

    # Security - MUST be set in production
    secret_key: str = Field(
        default="dev-only-change-in-production",
        description="Secret key for signing tokens. MUST be changed in production.",
        min_length=32
    )

    # API Key Authentication
    api_key_header: str = "X-API-Key"
    api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys. Empty allows unauthenticated access in dev."
    )
    api_key_required: bool = Field(
        default=True,
        description="Whether API key is required. Set to False only for local development."
    )

    # Database - MUST use secure credentials in production
    database_url: str = Field(
        default="postgresql+asyncpg://micromobility:devpassword@localhost:5432/micromobility_nav",
        description="PostgreSQL connection URL. Use environment variable in production."
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per window")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window in seconds")
    rate_limit_burst: int = Field(default=20, description="Burst allowance above limit")

    # JWT Authentication
    jwt_enabled: bool = Field(default=False, description="Enable JWT authentication")
    jwt_access_expire_minutes: int = Field(default=30, description="Access token expiry in minutes")
    jwt_refresh_expire_days: int = Field(default=7, description="Refresh token expiry in days")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_issuer: str = Field(default="sf-micromobility-api", description="JWT issuer claim")
    jwt_audience: str = Field(default="sf-micromobility-client", description="JWT audience claim")

    # Valhalla Routing Engine
    valhalla_url: str = "http://localhost:8002"

    # External APIs - Optional, set via environment
    mapbox_access_token: str = ""
    sf_opendata_app_token: str = ""
    openweather_api_key: str = ""

    # CORS - Restrict in production
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"]

    # San Francisco Bounding Box
    sf_min_lon: float = -122.52
    sf_min_lat: float = 37.70
    sf_max_lon: float = -122.35
    sf_max_lat: float = 37.82

    # Data directories
    data_dir: str = "/app/data"

    # Logging
    log_level: str = "INFO"
    log_requests: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Ensure secret key is secure in production."""
        # This will be checked at startup, not during validation
        return v

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        """Parse and validate API keys format."""
        if v:
            keys = [k.strip() for k in v.split(",") if k.strip()]
            # Validate each key has minimum length
            for key in keys:
                if len(key) < 32:
                    raise ValueError(f"API key must be at least 32 characters: {key[:8]}...")
        return v

    def get_api_keys_list(self) -> List[str]:
        """Get list of valid API keys."""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"

    def validate_production_settings(self) -> List[str]:
        """Validate settings are secure for production. Returns list of errors."""
        errors = []

        if self.is_production():
            # Check secret key
            if self.secret_key == "dev-only-change-in-production":
                errors.append("SECRET_KEY must be changed from default in production")
            if len(self.secret_key) < 64:
                errors.append("SECRET_KEY should be at least 64 characters in production")

            # Check database URL
            if "devpassword" in self.database_url:
                errors.append("DATABASE_URL contains default password - use secure credentials")

            # Check API key requirement
            if not self.api_key_required:
                errors.append("API_KEY_REQUIRED should be True in production")

            # Check CORS origins
            if any("localhost" in origin for origin in self.cors_origins):
                errors.append("CORS_ORIGINS should not include localhost in production")

            # Check debug mode
            if self.debug:
                errors.append("DEBUG must be False in production")

        return errors


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Clear cache and reload
get_settings.cache_clear()
settings = get_settings()
