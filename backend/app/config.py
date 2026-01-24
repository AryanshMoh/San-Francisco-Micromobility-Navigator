"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "SF Micromobility Navigation API"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://micromobility:devpassword@localhost:5432/micromobility_nav"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Valhalla Routing Engine
    valhalla_url: str = "http://localhost:8002"

    # External APIs
    mapbox_access_token: str = ""
    sf_opendata_app_token: str = ""
    openweather_api_key: str = ""

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # San Francisco Bounding Box
    sf_min_lon: float = -122.52
    sf_min_lat: float = 37.70
    sf_max_lon: float = -122.35
    sf_max_lat: float = 37.82

    # Data directories
    data_dir: str = "/app/data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
