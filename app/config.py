"""
Application configuration settings.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./adaptiva.db"
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", 
        "dev-secret-key-change-in-production-minimum-32-chars!"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Anonymous Rate Limiting
    ANONYMOUS_DAILY_LIMIT: int = 3
    GLOBAL_ANONYMOUS_DAILY_LIMIT: int = 1000
    BURST_LIMIT_PER_MINUTE: int = 10
    ANONYMOUS_SESSION_SECRET: str = os.getenv(
        "ANONYMOUS_SESSION_SECRET",
        "anon-session-secret-change-in-production!"
    )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra env vars like OPENAI_API_KEY, PORT
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
