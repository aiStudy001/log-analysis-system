"""
Configuration management

Loads environment variables and provides application settings
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database Configuration
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "logs_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "password"
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 10

    # LLM Configuration
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL_ANTHROPIC: str = "claude-sonnet-4-5-20250929"
    LLM_MODEL_OPENAI: str = "gpt-4"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001

    # Cache Configuration (Feature #1)
    CACHE_TTL_SECONDS: int = 300     # 5 minutes
    CACHE_MAX_SIZE: int = 100        # Maximum cache entries

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


settings = Settings()
