from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering.parquet'
MODEL_PATH = BASE_DIR / 'backend' / 'models'

# Try multiple locations for .env for flexibility
ENV_PATHS = [ BASE_DIR / 'production' / '.env',
            BASE_DIR / '.env',
            Path.cwd() / '.env'
            ]

ENV_PATH = next((path for path in ENV_PATHS if path.exists()), None)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    REDIS_URL: str = "redis://localhost:6379"

    # Match to .env postgresql
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str

    # Optional: support for async
    USE_ASYNC_PG: bool = True

    # LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    LLM_PROVIDER_GROQ: str = "groq" 
    LLM_PROVIDER_GEMINI: str = "gemini"
    LLM_MODEL_GROQ: str = "llama-3.1-8b-instant"
    LLM_MODEL_GEMINI: str = "gemini-2.5-pro"
    LLM_BASE_URL: Optional[str] = None 

    @property
    def DATABASE_URL(self) -> str:
        if self.USE_ASYNC_PG:
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Synchronous database URL (for alembic, scripts)"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        if ENV_PATH:
            env_file = str(ENV_PATH)
            env_file_encoding = 'utf-8'

        # Case insensitive environment variables
        case_sensitive = False

        extra = "ignore" # Ignore extra fields in .env that are not defined in Settings

        # Allow populating by field name
        populate_by_name = True

settings = Settings() # Singleton instance

DATABASE_PATH = settings.DATABASE_URL # For backward compatibility