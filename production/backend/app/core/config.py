from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Env file path
ENV_PATH = BASE_DIR.parent / 'production' / '.env'
if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / '.env'  # Fallback to root .env if not found in production
    print(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

class Settings(BaseSettings):
    """Application configuration loaded from environment variables with Pydantic validation."""

    # API Configuration
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4002", "http://localhost"]

    # Redis Configuration
    try:
        REDIS_URL: str = "redis://Redis:6379"
        print(f"✅ Redis URL set to: {REDIS_URL}")
    except ImportError:
        REDIS_URL: str = "redis://localhost:6379"  # Fallback for local development
        print(f"⚠️ Redis URL not found in environment, using fallback: {REDIS_URL}")

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"

    # Supabase - External PostgreSQL for FastAPI app
    SUPABASE_USER: str
    SUPABASE_PASSWORD: str
    SUPABASE_HOST: str
    SUPABASE_PORT: int = 6543
    SUPABASE_DB: str
    USE_ASYNC_PG: bool = True

    # PostgreSQL (Docker) - Internal for Airflow, analytics, data pipeline, monitoring tools
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    # Databricks Configuration
    DATABRICKS_HOST: Optional[str] = None
    DATABRICKS_TOKEN: Optional[str] = None
    DATABRICKS_HTTP_PATH: Optional[str] = None
    DATABRICKS_WAREHOUSE_ID: Optional[str] = None

    # Evidently AI Configuration
    EVIDENTLY_API_KEY: Optional[str] = None

    # LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "groq" 
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_BASE_URL: Optional[str] = None 

    # Qdrant Configuration
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None


    # ---- File paths -----
    # These were module-level variables before — now proper Settings fields
    PARQUET_PATH: str = str(BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering_2.parquet')
    MODEL_PATH: str = str(BASE_DIR / 'backend' / 'models')
    DATABASE_FEATURES_PATH: str = str(BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering_2_features.parquet')
    DATABASE_SCALED_PATH: str = str(BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering_2_scaled.parquet')

    # --- Computed Properties ---

    @property
    def DATABASE_URL(self) -> str:
        """Async connection string → Supabase transaction pooler (FastAPI)."""
        return (
        f"postgresql+asyncpg://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}"
        f"@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DB}"
      )
        
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Synchronous database connection string for migrations or scripts."""
        return f"postgresql+psycopg2://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DB}?sslmode=require"

    @property
    def POSTGRES_URL(self) -> str:
        """Asynchronous Connection string -> internal Docker PostgreSQL """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def POSTGRES_URL_SYNC(self) -> str:
        """Synchronous connection string for internal Docker PostgreSQL."""
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

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

# Backward compatibility for code that imports DATABASE_URL directly
DB_CONNECTION_STRING = settings.DATABASE_URL        # Supabase async
POSTGRES_CONNECTION_STRING = settings.POSTGRES_URL  # Internal Docker async
DATABASE_PATH = Path(settings.PARQUET_PATH)
if not DATABASE_PATH.exists():
    fallback_parquet = BASE_DIR / 'database' / 'taxi_trip_engineering_2.parquet'
    if fallback_parquet.exists():
        DATABASE_PATH = fallback_parquet
    else:
        print(f"⚠️ Parquet file not found at {DATABASE_PATH} or {fallback_parquet}")

# Resolve the Model path safely
MODEL_PATH = Path(settings.MODEL_PATH)
if not MODEL_PATH.exists():
    fallback_model = BASE_DIR / 'models'
    if fallback_model.exists():
        MODEL_PATH = fallback_model

# Add database features and scaled for DATABASE
DATABASE_FEATURES_PATH = (Path(settings.DATABASE_FEATURES_PATH))
if not DATABASE_FEATURES_PATH.exists():
    fallback_features = BASE_DIR / 'database' / 'taxi_trip_engineering_2_features.parquet'
    if fallback_features.exists():
        DATABASE_FEATURES_PATH = fallback_features
    else:
        print(f"⚠️ Features Parquet file not found at {DATABASE_FEATURES_PATH} or {fallback_features}")

DATABASE_SCALED_PATH = (Path(settings.DATABASE_SCALED_PATH))
if not DATABASE_SCALED_PATH.exists():
    fallback_scaled = BASE_DIR / 'database' / 'taxi_trip_engineering_2_scaled.parquet'
    if fallback_scaled.exists():
        DATABASE_SCALED_PATH = fallback_scaled
    else:
        print(f"⚠️ Scaled Parquet file not found at {DATABASE_SCALED_PATH} or {fallback_scaled}")