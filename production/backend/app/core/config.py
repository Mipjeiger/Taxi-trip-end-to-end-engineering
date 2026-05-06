from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering.parquet'
MODEL_PATH = BASE_DIR / 'backend' / 'models'

class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4002", "http://localhost"]
    REDIS_URL: str = "redis://localhost:6379"

    # Match to .env postgresql
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "postgres" # Ensure service name matches with docker
    DB_PORT: int = 5432
    DB_NAME: str
    USE_ASYNC_PG: bool = True

    # LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "groq" 
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_BASE_URL: Optional[str] = None 

    @property
    def DATABASE_URL(self) -> str:
        """Asyncrhonous database connection string."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Synchronous database connection string for migrations or scripts."""
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Pydantic V2 Configuration Style
    model_config = SettingsConfigDict(
        env_file=".env", # Still supports local .env if exists
        env_file_encoding="utf-8",
        case_sensitive=False,  # Important: DB_USER matches db_user
        extra="ignore",
        populate_by_name=True
    )
    
settings = Settings() # Singleton instance

DB_CONNECTION_STRING = settings.DATABASE_URL # For backward compatibility