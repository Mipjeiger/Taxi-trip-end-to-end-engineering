from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering.parquet'
MODEL_PATH = BASE_DIR / 'backend' / 'models'

# Env file path
ENV_PATH = BASE_DIR / '.env'

class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4002", "http://localhost"]
    REDIS_URL: str = "redis://localhost:6379"

    # Match to .env postgresql - Supabase external postgresql configuration
    SUPABASE_USER: str
    SUPABASE_PASSWORD: str
    SUPABASE_HOST: str
    SUPABASE_PORT: int = 6543
    SUPABASE_DB: str
    USE_ASYNC_PG: bool = True

    # LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "groq" 
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_BASE_URL: Optional[str] = None 

    @property
    def DATABASE_URL(self) -> str:
        """Asyncrhonous database connection string for Supabase. Includes ssl=require which is mandatory for many cloud providers."""
        return f"postgresql+asyncpg://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DB}"
        
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Synchronous database connection string for migrations or scripts."""
        return f"postgresql+psycopg2://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DB}?sslmode=require"

    # Pydantic V2 Configuration Style
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,  # Important: DB_USER matches db_user
        extra="ignore",
        populate_by_name=True
    )
    
# Singleton instance    
settings = Settings()
DB_CONNECTION_STRING = settings.DATABASE_URL # For backward compatibility